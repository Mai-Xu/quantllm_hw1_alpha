"""
最小化 CTP 交易 DEMO：从底层 Python 交易 API 开始（vnpy_ctp.api，非 CtpGateway）。

流程：
1. 连接交易前置（TdApi）：发起网络连接 -> 终端认证 -> 登录账号
2. 连接行情前置（MdApi）：发起网络连接 -> 登录账号
3. 订阅合约行情（subscribeMarketData）
4. 打印每一条行情推送（onRtnDepthMarketData）

CTP 是纯异步回调驱动的 API：所有 req 只负责发出请求，
结果通过对应的 onRsp/onRtn 回调（CTP 内部线程）返回。

用法：python demo.py
"""

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
    # 新开终端才有该变量；从注册表兜底读取
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


# SimNow 模拟账号配置（端口随交易时段切换：盘中 30001/30011，夜盘实测为 40001/40011）
# 本账号为用户自注册 SimNow（昵称 maimai，投资者代码 <INVESTOR_ID>）
SETTING = {
    "userid":     "<INVESTOR_ID>",                      # 资金账号（InvestorID，6 位数字）
    "password":   _load_password(),              # 登录密码（读自环境变量 Mai_SimNow_passward）
    "brokerid":   "9999",                        # 经纪商代码（SimNow 固定 9999）
    "td_address": "tcp://182.254.243.31:30001",  # 交易前置（盘中 30001；夜盘/另一套为 40001）
    "md_address": "tcp://182.254.243.31:30011",  # 行情前置（盘中 30011；夜盘/另一套为 40011）
    "appid":      "simnow_client_test",          # 产品名称（终端认证用，SimNow 通用）
    "auth_code":  "0000000000000000",            # 授权编码（终端认证用，SimNow 通用 16 个 0）
}

# 订阅的合约列表（须为当前挂牌月份；摘牌合约订阅无任何错误回报，只是收不到行情）
SUBSCRIBED_SYMBOLS = ["au2612", "au2706", "ag2612", "rb2610", "cu2612"]

# 流文件目录（CTP 底层要求一个可写的本地目录存放流文件）
FLOW_PATH = Path(__file__).parent / "flow"
FLOW_PATH.mkdir(exist_ok=True)


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
    """交易 API：演示 连接 -> 认证 -> 登录 的完整握手状态机。"""

    def __init__(self) -> None:
        """初始化请求计数与连接/登录状态。"""
        super().__init__()                 # 必须调用：C++ 扩展对象初始化
        self.reqid: int = 0                # 请求编号，每次请求自增
        self.login_status: bool = False    # 是否登录成功
        self.connect_status: bool = False  # 是否已发起过连接（防重复连接导致崩溃）

    def connect(self) -> None:
        """发起网络连接（非阻塞，结果在 onFrontConnected 回调返回）。"""
        if not self.connect_status:
            self.createFtdcTraderApi(str(FLOW_PATH / "Td").encode("GBK"), True)
            self.registerFront(SETTING["td_address"])
            self.init()
            self.connect_status = True

    def authenticate(self) -> None:
        """发起终端认证（SimNow 要求，需 AppID + AuthCode）。"""
        req = {
            "UserID": SETTING["userid"],
            "BrokerID": SETTING["brokerid"],
            "AppID": SETTING["appid"],
            "AuthCode": SETTING["auth_code"],
        }
        self.reqid += 1
        self.reqAuthenticate(req, self.reqid)

    def login(self) -> None:
        """发起登录请求。"""
        self.reqid += 1
        self.reqUserLogin(make_login_req(), self.reqid)

    def onFrontConnected(self) -> None:
        """回报：前置连接成功，接着走认证。"""
        log("交易前置连接成功，开始终端认证")
        self.authenticate()

    def onFrontDisconnected(self, reason: int) -> None:
        """回报：前置连接断开。"""
        log(f"交易前置连接断开，原因码 {reason}")

    def onRspAuthenticate(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """回报：终端认证结果，成功则接着登录。"""
        if not error["ErrorID"]:
            log("终端认证成功，开始登录")
            self.login()
        else:
            log(f"终端认证失败：{error['ErrorID']} {error['ErrorMsg']}")

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """回报：登录结果。"""
        if not error["ErrorID"]:
            self.login_status = True
            log(f"交易账号登录成功，交易日 {data.get('TradingDay')}")
        else:
            log(f"交易登录失败：{error['ErrorID']} {error['ErrorMsg']}")


class SimpleMdApi(MdApi):
    """行情 API：连接 -> 登录 -> 订阅 -> 打印推送。"""

    def __init__(self) -> None:
        """初始化请求计数、连接/登录状态与订阅列表。"""
        super().__init__()                 # 必须调用：C++ 扩展对象初始化
        self.reqid: int = 0                # 请求编号，每次请求自增
        self.login_status: bool = False    # 是否登录成功
        self.connect_status: bool = False  # 是否已发起过连接
        self.subscribed: list = []         # 已登记的订阅合约列表

    def connect(self) -> None:
        """发起网络连接（非阻塞，结果在 onFrontConnected 回调返回）。"""
        if not self.connect_status:
            self.createFtdcMdApi(str(FLOW_PATH / "Md").encode("GBK"), True)
            self.registerFront(SETTING["md_address"])
            self.init()
            self.connect_status = True

    def login(self) -> None:
        """发起登录请求。"""
        self.reqid += 1
        self.reqUserLogin(make_login_req(), self.reqid)

    def subscribe(self, symbols: list) -> None:
        """登记订阅列表；实际订阅在登录回报 onRspUserLogin 中统一执行。"""
        self.subscribed.extend(symbols)

    def onFrontConnected(self) -> None:
        """回报：前置连接成功，接着登录。"""
        log("行情前置连接成功，开始登录")
        self.login()

    def onFrontDisconnected(self, reason: int) -> None:
        """回报：前置连接断开。"""
        self.login_status = False
        log(f"行情前置连接断开，原因码 {reason}")

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """回报：登录成功后统一订阅（断线重连时也会走到这里，恢复订阅）。"""
        if not error["ErrorID"]:
            self.login_status = True
            log(f"行情账号登录成功，交易日 {data.get('TradingDay')}，开始订阅 {self.subscribed}")
            for symbol in self.subscribed:  # 本绑定版本一次只接受一个合约，逐个订阅
                self.subscribeMarketData(symbol)
        else:
            log(f"行情登录失败：{error['ErrorID']} {error['ErrorMsg']}")

    def onRspSubMarketData(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        """回报：订阅结果（仅失败时打印）。"""
        if error and error["ErrorID"]:
            log(f"订阅失败 {data.get('InstrumentID')}：{error['ErrorID']} {error['ErrorMsg']}")

    def onRtnDepthMarketData(self, data: dict) -> None:
        """行情推送：CTP 主动推送的深度行情快照，逐条打印。"""
        print(
            f"[{now()}] {data['InstrumentID']}"
            f" 最新={data['LastPrice']:.1f}"
            f" 买一={data['BidPrice1']:.1f}x{data['BidVolume1']}"
            f" 卖一={data['AskPrice1']:.1f}x{data['AskVolume1']}"
            f" 成交量={data['Volume']} 持仓量={data['OpenInterest']}"
            f" 时间={data['UpdateTime']}.{data['UpdateMillisec']}",
            flush=True,
        )


def main() -> None:
    """主流程：连接交易/行情前置 -> 登记订阅 -> 等待推送。"""
    td_api = SimpleTdApi()
    md_api = SimpleMdApi()

    log("发起交易前置连接...")
    td_api.connect()
    log("发起行情前置连接...")
    md_api.connect()

    md_api.subscribe(SUBSCRIBED_SYMBOLS)

    log("主线程进入等待，Ctrl+C 退出")
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        log("退出")
        td_api.exit()
        md_api.exit()


if __name__ == "__main__":
    main()
