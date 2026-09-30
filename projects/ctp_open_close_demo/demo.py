"""
CTP 交易 DEMO 3：超价开仓一次 + 超价平仓一次（完整开平闭环）。

在 demo2（突破触发单笔开仓）基础上，把「平仓」补上：
1. 连接/认证/登录/确认结算单（同 demo2）
2. 等首个 tick 拿到盘口价
3. 超价买开 1 手：委托价 = 卖一价 + N 跳（吃穿盘口，保证成交）
4. 开仓成交后，超价卖平 1 手：委托价 = 买一价 - N 跳
   注意 au 是上期所：平今仓用 CombOffsetFlag='3'(CLOSETODAY)，不是 '1'(CLOSE)

用法：python demo.py
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import sleep

from vnpy_ctp.api import MdApi, TdApi


def _load_password() -> str:
    """从用户环境变量读取 SimNow 密码（兼容 password/passward 两种拼写）。"""
    import os
    for key in ("Mai_SimNow_password", "Mai_SimNow_passward"):
        v = os.environ.get(key)
        if v:
            return v
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            for key in ("Mai_SimNow_password", "Mai_SimNow_passward"):
                try:
                    v, _ = winreg.QueryValueEx(k, key)
                    if v:
                        return v
                except OSError:
                    pass
    except ImportError:
        pass
    raise RuntimeError("未找到 Mai_SimNow_password / Mai_SimNow_passward 环境变量")


# SimNow 模拟账号配置（盘中 30001/30011；夜盘实测为 40001/40011）
SETTING = {
    "userid":     "<INVESTOR_ID>",
    "password":   _load_password(),
    "brokerid":   "9999",
    "td_address": "tcp://182.254.243.31:30001",
    "md_address": "tcp://182.254.243.31:30011",
    "appid":      "simnow_client_test",
    "auth_code":  "0000000000000000",
}

SYMBOL =          "au2612"   # 交易合约（上期所黄金，当前挂牌）
SYMBOL_EXCHANGE = "SHFE"     # 交易所
VOLUME =          1          # 手数
PRICE_TICK =      0.02       # au 最小变动价位
AGGRESS_TICKS =   5          # 超价跳数：买开=卖一+5跳，卖平=买一-5跳

FLOW_PATH = Path(__file__).parent / "flow"
FLOW_PATH.mkdir(exist_ok=True)

# CTP 委托状态码 → 中文（只列会遇到的）
STATUS_MAP = {
    "a": "未知",
    "0": "全部成交",
    "1": "部分成交",
    "3": "未成交",
    "5": "已撤单",
}


def now() -> str:
    """返回当前时间字符串（精确到毫秒），用作日志前缀。"""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(msg: str) -> None:
    """带时间戳打印一行日志。"""
    print(f"[{now()}] {msg}", flush=True)


def make_login_req() -> dict:
    """构造登录请求体（两个 API 的登录请求体完全一样，共用一份）。"""
    return {
        "UserID": SETTING["userid"],
        "Password": SETTING["password"],
        "BrokerID": SETTING["brokerid"],
    }


class SimpleTdApi(TdApi):
    """交易 API：认证 → 登录 → 结算确认 → 开平两笔超价单。"""

    def __init__(self) -> None:
        """初始化请求/委托计数、会话信息与开平状态机。"""
        super().__init__()
        self.reqid: int = 0
        self.order_ref: int = 0
        self.frontid: int = 0
        self.sessionid: int = 0
        self.connect_status: bool = False
        self.login_status: bool = False
        self.settlement_confirmed: bool = False
        self.open_filled: bool = False        # 开仓是否已成交
        self.close_sent: bool = False         # 平仓单是否已发出（防重复）
        self.ready_hook: Callable[[], None] | None = None

    def connect(self) -> None:
        """发起网络连接（非阻塞）。"""
        if not self.connect_status:
            self.createFtdcTraderApi(str(FLOW_PATH / "Td").encode("GBK"), True)
            self.subscribePrivateTopic(0)     # 委托/成交推送到本会话
            self.subscribePublicTopic(0)
            self.registerFront(SETTING["td_address"])
            self.init()
            self.connect_status = True

    def authenticate(self) -> None:
        """发起终端认证（SimNow 要求）。"""
        self.reqid += 1
        self.reqAuthenticate({
            "UserID": SETTING["userid"],
            "BrokerID": SETTING["brokerid"],
            "AppID": SETTING["appid"],
            "AuthCode": SETTING["auth_code"],
        }, self.reqid)

    def login(self) -> None:
        """发起登录请求。"""
        self.reqid += 1
        self.reqUserLogin(make_login_req(), self.reqid)

    def confirm_settlement(self) -> None:
        """确认结算单（下单前置条件）。"""
        self.reqid += 1
        self.reqSettlementInfoConfirm({
            "BrokerID": SETTING["brokerid"],
            "InvestorID": SETTING["userid"],
        }, self.reqid)

    def send_order(self, direction: str, offset: str, price: float, volume: int, tag: str) -> None:
        """发出限价单。direction: '0'买/'1'卖；offset: '0'开/'1'平/'3'平今。"""
        self.order_ref += 1
        req = {
            "InstrumentID": SYMBOL,
            "ExchangeID": SYMBOL_EXCHANGE,
            "LimitPrice": price,
            "VolumeTotalOriginal": volume,
            "OrderPriceType": "2",        # 限价
            "Direction": direction,
            "CombOffsetFlag": offset,
            "OrderRef": str(self.order_ref),
            "InvestorID": SETTING["userid"],
            "UserID": SETTING["userid"],
            "BrokerID": SETTING["brokerid"],
            "CombHedgeFlag": "1",         # 投机
            "ContingentCondition": "1",   # 立即
            "ForceCloseReason": "0",      # 非强平
            "IsAutoSuspend": 0,
            "TimeCondition": "3",         # 当日有效
            "VolumeCondition": "1",       # 任何数量
            "MinVolume": 1,
        }
        self.reqid += 1
        n = self.reqOrderInsert(req, self.reqid)
        if n != 0:
            log(f"!! {tag} 委托发送失败，返回码 {n}")
        else:
            log(f">> 已发出[{tag}]：{'买入' if direction == '0' else '卖出'}"
                f"{'开仓' if offset == '0' else ('平今' if offset == '3' else '平仓')}"
                f" {SYMBOL} {volume}手 @ {price}  OrderRef={self.order_ref}")

    def send_open(self, price: float) -> None:
        """超价买开。"""
        self.send_order("0", "0", price, VOLUME, "超价买开")

    def send_close(self, price: float) -> None:
        """超价卖平今仓（上期所今仓必须用 CLOSETODAY='3'）。"""
        if self.close_sent:
            return
        self.close_sent = True
        self.send_order("1", "3", price, VOLUME, "超价卖平")

    def is_mine(self, data: dict) -> bool:
        """判断回报是否属于本会话委托（回报是全账户流，必须过滤）。"""
        return (data.get("FrontID") == self.frontid
                and data.get("SessionID") == self.sessionid)

    def onFrontConnected(self) -> None:
        """回报：前置连接成功，接着走认证。"""
        log("交易前置连接成功，开始终端认证")
        self.authenticate()

    def onFrontDisconnected(self, reason: int) -> None:
        """回报：前置连接断开。"""
        self.login_status = False
        self.settlement_confirmed = False
        log(f"交易前置连接断开，原因码 {reason}")

    def onRspAuthenticate(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """回报：终端认证结果。"""
        if not error["ErrorID"]:
            log("终端认证成功，开始登录")
            self.login()
        else:
            log(f"终端认证失败：{error['ErrorID']} {error['ErrorMsg']}")

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """回报：登录成功后记录会话信息，确认结算单。"""
        if not error["ErrorID"]:
            self.login_status = True
            self.frontid = data["FrontID"]
            self.sessionid = data["SessionID"]
            log(f"交易登录成功（FrontID={self.frontid} SessionID={self.sessionid}），确认结算单")
            self.confirm_settlement()
        else:
            log(f"交易登录失败：{error['ErrorID']} {error['ErrorMsg']}")

    def onRspSettlementInfoConfirm(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """回报：结算单确认成功即通道就绪。"""
        if not error["ErrorID"]:
            self.settlement_confirmed = True
            log("结算单确认成功，交易通道就绪")
            if self.ready_hook:
                self.ready_hook()
        else:
            log(f"结算单确认失败：{error['ErrorID']} {error['ErrorMsg']}")

    def onRspOrderInsert(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """回报：场内拒单。"""
        log(f"!! 委托被拒：{error['ErrorID']} {error['ErrorMsg']}")

    def onRtnOrder(self, data: dict) -> None:
        """委托状态流（全账户流，按会话过滤）。"""
        if data["InstrumentID"] != SYMBOL or not self.is_mine(data):
            return
        orderid = f"{data['FrontID']}_{data['SessionID']}_{data['OrderRef']}"
        status = STATUS_MAP.get(data["OrderStatus"], data["OrderStatus"])
        log(f"[委托] {orderid} {'买' if data['Direction'] == '0' else '卖'}"
            f"{data['VolumeTotalOriginal']}手 已成{data['VolumeTraded']}手 "
            f"状态={status} ({data['StatusMsg']})")

    def onRtnTrade(self, data: dict) -> None:
        """成交回报：开仓成交流 → 触发超价平仓。"""
        if data["InstrumentID"] != SYMBOL:
            return
        # 成交回报无 FrontID/SessionID，用 OrderRef 关联本会话
        try:
            if int(data["OrderRef"]) > 10**6:
                return
        except (KeyError, ValueError):
            pass
        if data.get("OrderRef") and int(data["OrderRef"]) > self.order_ref:
            return  # 不是本会话的单
        log(f"[成交] {data['InstrumentID']} {'买' if data['Direction'] == '0' else '卖'}"
            f"{data['Volume']}手 @ {data['Price']}  TradeID={data['TradeID']} "
            f"Offset={data.get('OffsetFlag')}")

        if data["Direction"] == "0" and not self.open_filled:
            self.open_filled = True
            log("开仓已成交 → 触发超价卖平（等下一次盘口，由 ready_hook/行情侧补价）")
            if self.ready_hook:
                self.ready_hook()


class SimpleMdApi(MdApi):
    """行情 API：登录 → 订阅 → 缓存盘口 → 提供超价。"""

    def __init__(self, td_api: SimpleTdApi) -> None:
        """初始化行情连接状态与盘口缓存。"""
        super().__init__()
        self.td_api = td_api
        self.reqid: int = 0
        self.login_status: bool = False
        self.connect_status: bool = False
        self.bid1: float = 0.0
        self.ask1: float = 0.0
        self.last_price: float = 0.0
        self.tick_count: int = 0

    def connect(self) -> None:
        """发起网络连接（非阻塞）。"""
        if not self.connect_status:
            self.createFtdcMdApi(str(FLOW_PATH / "Md").encode("GBK"), True)
            self.registerFront(SETTING["md_address"])
            self.init()
            self.connect_status = True

    def login(self) -> None:
        """发起登录请求。"""
        self.reqid += 1
        self.reqUserLogin(make_login_req(), self.reqid)

    def onFrontConnected(self) -> None:
        """回报：前置连接成功，登录。"""
        log("行情前置连接成功，开始登录")
        self.login()

    def onFrontDisconnected(self, reason: int) -> None:
        """回报：断开。"""
        self.login_status = False
        log(f"行情前置断开 reason={reason}")

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """回报：登录成功后订阅。"""
        if not error["ErrorID"]:
            self.login_status = True
            log(f"行情登录成功，订阅 {SYMBOL}")
            self.subscribeMarketData(SYMBOL)
        else:
            log(f"行情登录失败：{error['ErrorID']} {error['ErrorMsg']}")

    def onRtnDepthMarketData(self, d: dict) -> None:
        """缓存盘口；若通道就绪且尚未开仓则发开仓单，开仓成交后发平仓单。"""
        self.tick_count += 1
        self.bid1 = d.get("BidPrice1") or 0.0
        self.ask1 = d.get("AskPrice1") or 0.0
        self.last_price = d.get("LastPrice") or 0.0
        if self.tick_count <= 3 or self.tick_count % 50 == 0:
            log(f"[盘口] {d['InstrumentID']} 最新={self.last_price} "
                f"买一={self.bid1} 卖一={self.ask1}")

        td = self.td_api
        if not td.settlement_confirmed:
            return

        # 开仓：超价买 = 卖一 + N 跳
        if not td.open_filled and not td.close_sent and td.order_ref == 0:
            if self.ask1 > 0:
                px = round(self.ask1 + AGGRESS_TICKS * PRICE_TICK, 2)
                td.send_open(px)
                td.ready_hook = self._maybe_close  # 开仓成交后由这里补平仓价
                return

        # 平仓：开仓已成交 → 超价卖 = 买一 - N 跳
        if td.open_filled and not td.close_sent and self.bid1 > 0:
            px = round(self.bid1 - AGGRESS_TICKS * PRICE_TICK, 2)
            td.send_close(px)

    def _maybe_close(self) -> None:
        """ready_hook：开仓成交后若已有盘口则立即平仓。"""
        if self.td_api.open_filled and not self.td_api.close_sent and self.bid1 > 0:
            px = round(self.bid1 - AGGRESS_TICKS * PRICE_TICK, 2)
            self.td_api.send_close(px)


def main() -> None:
    """主流程：连接 TD/MD → 开仓 → 平仓 → 等回报。"""
    td_api = SimpleTdApi()
    md_api = SimpleMdApi(td_api)

    log(f"目标：{SYMBOL} 超价买开 {VOLUME}手 → 超价卖平 {VOLUME}手（超价 {AGGRESS_TICKS} 跳）")
    td_api.connect()
    md_api.connect()

    log("主线程进入等待，Ctrl+C 退出")
    try:
        for i in range(60):
            sleep(1)
            if td_api.open_filled and td_api.close_sent and i > 20:
                log("开+平两笔均已发出，再等 10 秒收回报后退出")
                sleep(10)
                break
    except KeyboardInterrupt:
        log("手动中断")
    finally:
        log(f"结束：开仓成交={td_api.open_filled} 平仓已发={td_api.close_sent} 行情条数={md_api.tick_count}")
        td_api.exit()
        md_api.exit()


if __name__ == "__main__":
    main()
