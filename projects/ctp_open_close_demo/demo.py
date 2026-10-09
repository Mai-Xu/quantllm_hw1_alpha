"""
CTP 交易 DEMO 3（可验证闭环版）：1 手开仓 → 1 手平仓 → 持仓归零，全程 fail-closed。

与早期版本的关键差别（针对「只能证明平仓单已发出」的反馈）：

1. 开仓意图持久化：发单前先把 intent 写入 evidence/journal_*.jsonl，
   进程崩溃后可从 journal 复原「当时打算做什么」。
2. 委托/成交归属收紧：
   - 委托：必须同时满足 FrontID + SessionID + OrderRef ∈ 本会话已登记集合；
   - 成交：CTP 成交回报不含 FrontID/SessionID，因此
     (a) OrderRef 必须在本会话登记集合内；
     (b) 若回报带 OrderSysID，必须已由本会话的委托回报登记过，否则拒收；
     (c) 方向必须与对应委托一致。
   多会话并行时，其他会话的成交会被明确拒绝并计数，不进入统计。
3. 平仓成交：以「归属后的成交数量」判定，而非「平仓单已发出」。
4. 最终校验：查询持仓 + 本会话委托状态——
   - 持仓：多空均为 0（目标持仓 = 0）
   - 委托：本会话无活动委托（全部为终态）
   任一不满足即判失败并返回非 0 退出码。
5. fail-closed：断线 / 拒单 / 超时 / 状态未知未收敛，一律判失败退出，绝不打印「成功」。

退出码：
  0  校验通过（已平仓、持仓归零、无活动委托）
  2  配置缺失（环境变量未设置）
  3  连接 / 认证 / 登录 / 结算确认失败
  4  委托被柜台拒绝
  5  等待成交超时
  6  终态校验失败（持仓非 0 或存在活动委托）
  7  中途断线

用法（值全部来自环境变量，源码不含任何账号）：
  export Mai_SimNow_userid=xxx / Mai_SimNow_password=xxx / Mai_SimNow_brokerid=9999
  python demo.py
配置样例见 config.sample.json（无值）。
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from time import sleep

from vnpy_ctp.api import MdApi, TdApi

# ----------------------------------------------------------------------------
# 配置：全部来自环境变量（源码与仓库不含任何账号值）
# ----------------------------------------------------------------------------

ENV_KEYS = {
    "userid":     ("Mai_SimNow_userid", "Mai_SimNow_userID"),
    "password":   ("Mai_SimNow_password", "Mai_SimNow_passward"),
    "brokerid":   ("Mai_SimNow_brokerid",),
    "td_address": ("Mai_SimNow_td_address",),
    "md_address": ("Mai_SimNow_md_address",),
    "appid":      ("Mai_SimNow_appid",),
    "auth_code":  ("Mai_SimNow_auth_code",),
}

# 非机密的默认值（SimNow 公开约定，非凭据）
DEFAULTS = {
    "brokerid":   "9999",
    "td_address": "tcp://182.254.243.31:30001",   # 盘中；夜盘实测为 40001
    "md_address": "tcp://182.254.243.31:30011",
    "appid":      "simnow_client_test",
    "auth_code":  "0000000000000000",
}


def _read_env(names: tuple[str, ...]) -> str:
    """只从环境变量读取凭据（不从注册表兜底：来源明确、可离线测试、fail-closed 确定）。

    注意：用 SetEnvironmentVariable 设置的用户级变量需在**新开的终端**中才可见。
    """
    for key in names:
        v = os.environ.get(key)
        if v:
            return v
    return ""


def load_setting() -> dict[str, str]:
    """装载配置；缺失必需项则退出码 2（fail-closed）。"""
    setting: dict[str, str] = {}
    for field, names in ENV_KEYS.items():
        setting[field] = _read_env(names) or DEFAULTS.get(field, "")
    missing = [f for f in ("userid", "password") if not setting.get(f)]
    if missing:
        print(f"[FATAL] 缺少必需的环境变量（对应字段: {', '.join(missing)}）；"
              f"参考 config.sample.json 配置后重试", flush=True)
        sys.exit(2)
    return setting


SETTING = load_setting()

SYMBOL =          "au2612"   # 交易合约（上期所黄金，当前挂牌）
SYMBOL_EXCHANGE = "SHFE"     # 交易所
VOLUME =          1          # 手数（统一补交标准：仅 1 手）
PRICE_TICK =      0.02       # au 最小变动价位
AGGRESS_TICKS =   5          # 超价跳数：买开 = 卖一 + N 跳；卖平 = 买一 − N 跳
FILL_TIMEOUT =    30         # 单笔委托等待成交上限（秒），超时判失败
TOTAL_TIMEOUT =   90         # 全流程上限（秒）

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
EVIDENCE_DIR = Path(__file__).parent / "evidence"
EVIDENCE_DIR.mkdir(exist_ok=True)
JOURNAL_PATH = EVIDENCE_DIR / f"journal_{RUN_ID}.jsonl"

FLOW_PATH = Path(__file__).parent / "flow"
FLOW_PATH.mkdir(exist_ok=True)

# CTP 委托状态码 → 语义（active=仍在场内）
STATUS_MAP = {
    "a": ("已提交", True),
    "0": ("全部成交", False),
    "1": ("部分成交", True),
    "2": ("部分成交不在队列", True),
    "3": ("未成交", True),
    "4": ("未成交不在队列", True),
    "5": ("已撤单", False),
}

TERMINAL_ORDER_STATUS = {"0", "5"}     # 全成 / 已撤 视为终态
REJECTED_ORDER_STATUS = {"5"}          # 撤单需再看 SubmitStatus


def mask(v: str) -> str:
    """脱敏：只保留长度示意，不泄漏账号。"""
    if not v:
        return ""
    return "*" * len(v)


def now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(msg: str) -> None:
    print(f"[{now()}] {msg}", flush=True)


def journal(event: str, **fields) -> None:
    """追加一条持久化事件（开仓意图、成交、校验结果等）。账号字段一律脱敏。"""
    rec = {"ts": datetime.now().isoformat(timespec="milliseconds"),
           "run_id": RUN_ID, "event": event}
    for k, v in fields.items():
        rec[k] = mask(v) if k in ("userid", "investor_id") else v
    with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class VerifiedTdApi(TdApi):
    """交易 API：认证 → 登录 → 结算确认 → 开仓 → 平仓 → 持仓归零校验。"""

    def __init__(self) -> None:
        super().__init__()
        self.reqid = 0
        self.order_ref = 0
        self.frontid = 0
        self.sessionid = 0
        self.connect_status = False
        self.login_status = False
        self.settlement_confirmed = False

        # 归属登记：本会话发出过的 OrderRef / 由本会话委托回报建立的 OrderSysID 映射
        self.my_order_refs: set[int] = set()
        self.ref_meta: dict[int, dict] = {}          # OrderRef -> {tag, direction, offset, volume}
        self.sysid_to_ref: dict[str, int] = {}       # OrderSysID -> OrderRef（仅本会话）
        self.status: dict[int, str] = {}             # OrderRef -> 最新 CTP 状态码
        self.traded_volume: dict[int, int] = {}      # OrderRef -> 已成交手数
        self.trade_volume: dict[int, int] = {}       # OrderRef -> 归属后的成交累计

        # 事件与失败态（fail-closed）
        self.fatal = False
        self.fatal_reason = ""
        self.rejected = False
        self.reject_msg = ""
        self.foreign_trade_rejected = 0              # 被拒收的他人成交计数（可复核证据）

        self.ready_hook: Callable[[], None] | None = None
        self.position_rows: list[dict] = []
        self.position_queried = False

    # ---------------- 连接与握手 ----------------

    def connect(self) -> None:
        if not self.connect_status:
            self.createFtdcTraderApi(str(FLOW_PATH / "Td").encode("GBK"), True)
            self.subscribePrivateTopic(0)
            self.subscribePublicTopic(0)
            self.registerFront(SETTING["td_address"])
            self.init()
            self.connect_status = True

    def authenticate(self) -> None:
        self.reqid += 1
        self.reqAuthenticate({
            "UserID": SETTING["userid"],
            "BrokerID": SETTING["brokerid"],
            "AppID": SETTING["appid"],
            "AuthCode": SETTING["auth_code"],
        }, self.reqid)

    def login(self) -> None:
        self.reqid += 1
        self.reqUserLogin({
            "UserID": SETTING["userid"],
            "Password": SETTING["password"],
            "BrokerID": SETTING["brokerid"],
        }, self.reqid)

    def confirm_settlement(self) -> None:
        self.reqid += 1
        self.reqSettlementInfoConfirm({
            "BrokerID": SETTING["brokerid"],
            "InvestorID": SETTING["userid"],
        }, self.reqid)

    def query_position(self) -> None:
        """查询投资者持仓（终态校验用）。"""
        self.position_rows = []
        self.position_queried = False
        self.reqid += 1
        self.reqQryInvestorPosition({
            "BrokerID": SETTING["brokerid"],
            "InvestorID": SETTING["userid"],
        }, self.reqid)

    # ---------------- 发单 ----------------

    def send_order(self, direction: str, offset: str, price: float, volume: int, tag: str) -> bool:
        """发出限价单；返回是否成功提交到柜台（≠ 成交）。"""
        self.order_ref += 1
        ref = self.order_ref
        self.my_order_refs.add(ref)
        self.ref_meta[ref] = {"tag": tag, "direction": direction,
                              "offset": offset, "volume": volume,
                              "price": price}
        self.status[ref] = "a"
        self.traded_volume[ref] = 0
        self.trade_volume[ref] = 0

        # 意图持久化：先落盘再发单（崩溃后可复原意图）
        journal("order_intent", tag=tag, order_ref=ref, instrument=SYMBOL,
                direction=direction, offset=offset, price=price, volume=volume)

        req = {
            "InstrumentID": SYMBOL,
            "ExchangeID": SYMBOL_EXCHANGE,
            "LimitPrice": price,
            "VolumeTotalOriginal": volume,
            "OrderPriceType": "2",        # 限价
            "Direction": direction,
            "CombOffsetFlag": offset,
            "OrderRef": str(ref),
            "InvestorID": SETTING["userid"],
            "UserID": SETTING["userid"],
            "BrokerID": SETTING["brokerid"],
            "CombHedgeFlag": "1",
            "ContingentCondition": "1",
            "ForceCloseReason": "0",
            "IsAutoSuspend": 0,
            "TimeCondition": "3",
            "VolumeCondition": "1",
            "MinVolume": 1,
        }
        self.reqid += 1
        n = self.reqOrderInsert(req, self.reqid)
        if n != 0:
            # 流控/字段错误：fail-closed
            self.fatal = True
            self.fatal_reason = f"{tag} 委托未提交，返回码 {n}"
            log(f"!! {self.fatal_reason}")
            journal("order_send_failed", tag=tag, order_ref=ref, ret=n)
            return False
        log(f">> 已提交[{tag}] {'买' if direction == '0' else '卖'}"
            f"{'开' if offset == '0' else '平'} {SYMBOL} {volume}手 @ {price} OrderRef={ref}")
        return True

    # ---------------- 归属判定（收紧） ----------------

    def order_is_mine(self, d: dict) -> bool:
        """委托归属：三段全匹配且 OrderRef 在登记集合内。"""
        try:
            ref = int(d.get("OrderRef") or -1)
        except ValueError:
            return False
        return (d.get("FrontID") == self.frontid
                and d.get("SessionID") == self.sessionid
                and ref in self.my_order_refs)

    def trade_ref(self, d: dict) -> int | None:
        """
        成交归属：返回本会话 OrderRef，否返回 None（拒收）。

        收紧点：(a) OrderRef 必须已登记；(b) 带 OrderSysID 时必须已登记为本会话委托；
        (c) 方向必须与对应委托一致。多会话并行时其他会话的成交在这里被拒。
        """
        try:
            ref = int(d.get("OrderRef") or -1)
        except ValueError:
            return None
        if ref not in self.my_order_refs:
            return None
        sysid = (d.get("OrderSysID") or "").strip()
        if sysid:
            known = self.sysid_to_ref.get(sysid)
            if known is None:
                return None               # 带系统号但非本会话 → 拒收
            if known != ref:
                return None               # 系统号与单号不自洽 → 拒收
        meta = self.ref_meta.get(ref)
        if meta and d.get("Direction") != meta["direction"]:
            return None                   # 方向不符 → 拒收
        return ref

    # ---------------- 回报 ----------------

    def onFrontConnected(self) -> None:
        log("交易前置连接成功，开始终端认证")
        self.authenticate()

    def onFrontDisconnected(self, reason: int) -> None:
        # 断线即 fail-closed（不重试、不假装成功）
        self.login_status = False
        self.settlement_confirmed = False
        if not self.fatal:
            self.fatal = True
            self.fatal_reason = f"交易前置断开 reason={reason}"
        log(f"!! 交易前置断开，原因码 {reason} → 判定失败")
        journal("td_disconnected", reason=reason)

    def onRspAuthenticate(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        if not error["ErrorID"]:
            log("终端认证成功，开始登录")
            self.login()
        else:
            self.fatal = True
            self.fatal_reason = f"终端认证失败 {error['ErrorID']} {error['ErrorMsg']}"
            log(f"!! {self.fatal_reason}")

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        if not error["ErrorID"]:
            self.login_status = True
            self.frontid = data["FrontID"]
            self.sessionid = data["SessionID"]
            log(f"交易登录成功（FrontID={self.frontid} SessionID={self.sessionid}），确认结算单")
            journal("td_login", frontid=self.frontid, sessionid=self.sessionid,
                    userid=SETTING["userid"])
            self.confirm_settlement()
        else:
            self.fatal = True
            self.fatal_reason = f"交易登录失败 {error['ErrorID']} {error['ErrorMsg']}"
            log(f"!! {self.fatal_reason}")

    def onRspSettlementInfoConfirm(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        if not error["ErrorID"]:
            self.settlement_confirmed = True
            log("结算单确认成功，交易通道就绪")
            journal("settlement_confirmed")
            if self.ready_hook:
                self.ready_hook()
        else:
            self.fatal = True
            self.fatal_reason = f"结算单确认失败 {error['ErrorID']} {error['ErrorMsg']}"
            log(f"!! {self.fatal_reason}")

    def onRspOrderInsert(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        if error["ErrorID"]:
            self.rejected = True
            self.reject_msg = f"{error['ErrorID']} {error['ErrorMsg']}"
            self.fatal = True
            self.fatal_reason = f"委托被柜台拒绝：{self.reject_msg}"
            log(f"!! {self.fatal_reason}")
            journal("order_rejected", error_id=error["ErrorID"], error_msg=error["ErrorMsg"])

    def onRtnOrder(self, data: dict) -> None:
        if not self.order_is_mine(data):
            return
        ref = int(data["OrderRef"])
        sysid = (data.get("OrderSysID") or "").strip()
        if sysid:
            self.sysid_to_ref[sysid] = ref           # 建立本会话 OrderSysID 映射
        status = data["OrderStatus"]
        self.status[ref] = status
        traded = int(data.get("VolumeTraded") or 0)
        self.traded_volume[ref] = traded
        name, _ = STATUS_MAP.get(status, (status, True))
        log(f"[委托] Ref={ref} SystemID={sysid or '-'} "
            f"{'买' if data['Direction'] == '0' else '卖'}{data['VolumeTotalOriginal']}手 "
            f"已成{traded}手 状态={name} ({data['StatusMsg']})")
        journal("order_update", order_ref=ref, sysid=sysid, status=status,
                traded=traded, status_msg=data["StatusMsg"])

    def onRtnTrade(self, data: dict) -> None:
        if data["InstrumentID"] != SYMBOL:
            return
        ref = self.trade_ref(data)
        if ref is None:
            # 非本会话成交：明确拒收并留证
            self.foreign_trade_rejected += 1
            journal("trade_rejected_not_mine",
                    order_ref=str(data.get("OrderRef")),
                    sysid=(data.get("OrderSysID") or "").strip(),
                    trade_id=str(data.get("TradeID", "")).strip())
            return

        vol = int(data["Volume"])
        self.trade_volume[ref] = self.trade_volume.get(ref, 0) + vol
        log(f"[成交] Ref={ref} {'买' if data['Direction'] == '0' else '卖'}{vol}手 "
            f"@{data['Price']} Offset={data.get('OffsetFlag')} TradeID={data['TradeID']}")
        journal("trade", order_ref=ref, volume=vol, price=data["Price"],
                offset=data.get("OffsetFlag"), trade_id=str(data["TradeID"]).strip(),
                tag=self.ref_meta.get(ref, {}).get("tag", ""))

        # 开仓全部成交 → 触发平仓
        meta = self.ref_meta.get(ref, {})
        if meta.get("tag") == "open" and self.trade_volume[ref] >= VOLUME:
            log("开仓已成交 → 触发超价平仓")
            if self.ready_hook:
                self.ready_hook()

    def onRspQryInvestorPosition(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        if error and error["ErrorID"]:
            self.fatal = True
            self.fatal_reason = f"持仓查询失败 {error['ErrorID']} {error['ErrorMsg']}"
            log(f"!! {self.fatal_reason}")
            return
        if data:
            self.position_rows.append({
                "instrument": data.get("InstrumentID", ""),
                "direction": data.get("PosiDirection", ""),
                "position": int(data.get("Position") or 0),
                "yd": int(data.get("YdPosition") or 0),
                "today": int(data.get("TodayPosition") or 0),
            })
        if last:
            self.position_queried = True
            log(f"持仓查询完成，共 {len(self.position_rows)} 行")
            journal("position_query", rows=self.position_rows)

    # ---------------- 终态判定 ----------------

    def open_filled(self) -> bool:
        return self.trade_volume.get(1, 0) >= VOLUME

    def close_filled(self) -> bool:
        refs = [r for r, m in self.ref_meta.items() if m.get("tag") == "close"]
        return bool(refs) and sum(self.trade_volume.get(r, 0) for r in refs) >= VOLUME

    def active_orders(self) -> list[int]:
        """本会话仍在场内的委托（未到终态）。"""
        return [r for r, s in self.status.items() if s not in TERMINAL_ORDER_STATUS]

    def symbol_positions(self) -> list[dict]:
        return [r for r in self.position_rows if r["instrument"] == SYMBOL and r["position"] != 0]

    def verify_flat(self) -> tuple[bool, str]:
        """终态校验：平仓成交 + 持仓归零 + 无活动委托。"""
        if not self.close_filled():
            return False, f"平仓未全部成交（已成交 {sum(self.trade_volume.values())} 手，需 {VOLUME} 手）"
        if not self.position_queried:
            return False, "持仓查询未返回（无法证明空仓）"
        pos = self.symbol_positions()
        if pos:
            return False, f"目标持仓未归零：{pos}"
        active = self.active_orders()
        if active:
            return False, f"存在活动委托：{active}"
        return True, "平仓成交 + 持仓归零 + 无活动委托"


class SimpleMdApi(MdApi):
    """行情 API：登录 → 订阅 → 缓存盘口（用于超价计算）。"""

    def __init__(self, td_api: VerifiedTdApi) -> None:
        super().__init__()
        self.td_api = td_api
        self.reqid = 0
        self.login_status = False
        self.connect_status = False
        self.bid1 = 0.0
        self.ask1 = 0.0
        self.tick_count = 0

    def connect(self) -> None:
        if not self.connect_status:
            self.createFtdcMdApi(str(FLOW_PATH / "Md").encode("GBK"), True)
            self.registerFront(SETTING["md_address"])
            self.init()
            self.connect_status = True

    def onFrontConnected(self) -> None:
        log("行情前置连接成功，开始登录")
        self.reqid += 1
        self.reqUserLogin({
            "UserID": SETTING["userid"],
            "Password": SETTING["password"],
            "BrokerID": SETTING["brokerid"],
        }, self.reqid)

    def onFrontDisconnected(self, reason: int) -> None:
        self.login_status = False
        if not self.td_api.fatal:
            self.td_api.fatal = True
            self.td_api.fatal_reason = f"行情前置断开 reason={reason}"
        log(f"!! 行情前置断开 reason={reason}")

    def onRspUserLogin(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        if not error["ErrorID"]:
            self.login_status = True
            log(f"行情登录成功，订阅 {SYMBOL}")
            self.subscribeMarketData(SYMBOL)
        else:
            self.td_api.fatal = True
            self.td_api.fatal_reason = f"行情登录失败 {error['ErrorID']} {error['ErrorMsg']}"
            log(f"!! {self.td_api.fatal_reason}")

    def onRtnDepthMarketData(self, d: dict) -> None:
        self.tick_count += 1
        self.bid1 = d.get("BidPrice1") or 0.0
        self.ask1 = d.get("AskPrice1") or 0.0
        if self.tick_count <= 3 or self.tick_count % 100 == 0:
            log(f"[盘口] 最新={d.get('LastPrice')} 买一={self.bid1} 卖一={self.ask1}")

        td = self.td_api
        if td.fatal or not td.settlement_confirmed:
            return
        # 开仓：超价买 = 卖一 + N 跳
        if not td.ref_meta:
            if self.ask1 > 0:
                px = round(self.ask1 + AGGRESS_TICKS * PRICE_TICK, 2)
                if td.send_order("0", "0", px, VOLUME, "open"):
                    td.ready_hook = self._close_if_open_filled
            return
        self._close_if_open_filled()

    def _close_if_open_filled(self) -> None:
        """开仓成交后平仓（上期所今仓用 CLOSETODAY='3'）。"""
        td = self.td_api
        if td.fatal:
            return
        if td.open_filled() and not td.close_filled() and not td.active_orders():
            if any(m.get("tag") == "close" for m in td.ref_meta.values()):
                return                                  # 平仓单已发出，等成交
            if self.bid1 > 0:
                px = round(self.bid1 - AGGRESS_TICKS * PRICE_TICK, 2)
                td.send_order("1", "3", px, VOLUME, "close")


def wait_until(pred: Callable[[], bool], timeout: float, what: str) -> bool:
    """轮询等待；超时返回 False（调用方 fail-closed）。"""
    deadline = datetime.now().timestamp() + timeout
    while datetime.now().timestamp() < deadline:
        if pred():
            return True
        sleep(0.2)
    log(f"!! 等待超时：{what}（{timeout}s）")
    return False


def main() -> int:
    td = VerifiedTdApi()
    md = SimpleMdApi(td)

    log(f"RUN_ID={RUN_ID} 目标：{SYMBOL} 开 {VOLUME} 手 → 平 {VOLUME} 手（超价 {AGGRESS_TICKS} 跳）")
    journal("run_start", instrument=SYMBOL, volume=VOLUME,
            userid=SETTING["userid"], brokerid=SETTING["brokerid"],
            td_address=SETTING["td_address"])

    td.connect()
    md.connect()

    try:
        # 1) 通道就绪
        if not wait_until(lambda: td.settlement_confirmed and md.login_status, 30, "通道就绪"):
            return 3
        # 2) 等首个盘口 → 已由行情回调发开仓单
        if not wait_until(lambda: bool(td.ref_meta), FILL_TIMEOUT, "开仓委托提交"):
            return 5
        # 3) 等开仓成交（fail-closed：拒单/断线立即退出）
        if not wait_until(lambda: td.fatal or td.open_filled(), FILL_TIMEOUT, "开仓成交"):
            journal("timeout", stage="open_fill")
            return 5
        if td.fatal:
            return 4 if td.rejected else 7
        # 4) 等平仓成交
        if not wait_until(lambda: td.fatal or td.close_filled(), FILL_TIMEOUT, "平仓成交"):
            journal("timeout", stage="close_fill")
            return 5
        if td.fatal:
            return 4 if td.rejected else 7

        # 5) 终态校验：查持仓 + 验无活动委托
        td.query_position()
        if not wait_until(lambda: td.position_queried or td.fatal, 15, "持仓查询"):
            return 6
    finally:
        ok, reason = td.verify_flat() if not td.fatal else (False, td.fatal_reason)
        journal("verify_result", passed=ok, reason=reason,
                open_filled=td.open_filled(), close_filled=td.close_filled(),
                active_orders=td.active_orders(), positions=td.symbol_positions(),
                foreign_trade_rejected=td.foreign_trade_rejected)
        log("=" * 68)
        log(f"开仓成交: {td.open_filled()}  平仓成交: {td.close_filled()}")
        log(f"本会话活动委托: {td.active_orders()}")
        log(f"{SYMBOL} 剩余持仓: {td.symbol_positions()}")
        log(f"拒收的他会话成交: {td.foreign_trade_rejected} 笔")
        log(f"校验结果: {'PASS' if ok else 'FAIL'} — {reason}")
        log(f"证据日志: {JOURNAL_PATH}")
        log("=" * 68)
        td.exit()
        md.exit()

    if td.fatal:
        log(f"!! 失败：{td.fatal_reason}")
        return 4 if td.rejected else 7
    if not ok:
        return 6
    log("闭环验证通过：已平仓、持仓归零、无活动委托")
    return 0


if __name__ == "__main__":
    sys.exit(main())
