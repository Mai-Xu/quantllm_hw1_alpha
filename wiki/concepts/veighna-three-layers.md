---
tags: [concept, architecture, veighna, learning-path]
created: 2026-09-30
updated: 2026-09-30
sources: [raw/vnpy, raw/vnpy_ctp, raw/vnpy_ctastrategy, raw/pku-veighna-course.pdf]
---

# 概念：VeighNa 三层交易系统架构

课件 p.13 的分层图，是理解整套框架的总纲。本页把三层九块与源码实体一一对应，并标注本仓库消化程度。

## 总览图

```
┌─────────────────────────────────────────────────────────┐
│  策略应用层                                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │ 单标的时序策略 │ │ 多标的投组策略 │ │ 价差套利类策略 │      │
│  │  CtaTemplate  │ │ Portfolio…   │ │  Spread…     │      │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘      │
├─────────┼────────────────┼────────────────┼──────────────┤
│  中层引擎 │                │                │              │
│  ┌──────┴───────┐ ┌──────┴───────┐ ┌──────┴───────┐      │
│  │ 事件引擎总线  │ │ OMS 数据缓存  │ │ 交易指令路由  │      │
│  │ EventEngine  │ │  OmsEngine   │ │ CtaEngine…   │      │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘      │
├─────────┼────────────────┼────────────────┼──────────────┤
│  底层接口 │                │                │              │
│  ┌──────┴───────┐ ┌──────┴───────┐                      │
│  │ 数据结构标准化│ │ 业务流程标准化│                      │
│  │ object/const │ │ BaseGateway  │                      │
│  └──────────────┘ └──────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

---

## 一、底层接口

### 1.1 数据结构标准化（`object.py` + `constant.py`）

**问题**：上期 CTP、中泰 XTP、华鑫 TORA……每家柜台字段名、枚举值、回报语义都不同。

**解法**：定义一套**与柜台无关的统一数据对象**，网关负责翻译。

| 对象 | 主键 | 作用 |
|---|---|---|
| `TickData` | `vt_symbol` | 行情快照（5 档、涨跌停、OHLC） |
| `BarData` | `vt_symbol` + interval | K 线 |
| `OrderData` | `vt_orderid` | 委托状态（含 `is_active()`） |
| `TradeData` | `vt_tradeid` | 成交（一单多笔） |
| `PositionData` | `vt_positionid` | 持仓（含 `yd_volume` 昨仓） |
| `AccountData` | `vt_accountid` | 资金（`available = balance - frozen`） |
| `ContractData` | `vt_symbol` | 合约规格（乘数、最小变动、`net_position`） |
| `QuoteData` | `vt_quoteid` | 双边报价（期权做市） |

**命名体系 `vt_*`**（见 [[vt-symbol-naming]]）：
- `vt_symbol = symbol.exchange.value`（如 `au2612.SHFE`）→ 跨网关唯一
- `vt_orderid = gateway_name.orderid`；orderid 本身在 CTP 是 `{frontid}_{sessionid}_{order_ref}`
- `vt_positionid` 拼入 `direction.value`（注意：枚举值本地化，中文环境下是「多/空」）

**常量枚举**（`constant.py`）：`Direction` / `Offset`（开/平/平今/平昨）/ `Status`（6 态）/ `OrderType`（LIMIT/MARKET/FAK/FOK…）/ `Exchange` / `Interval`。

**请求对象**（不含 gateway_name，由网关补充）：`SubscribeRequest` / `OrderRequest` / `CancelRequest` / `HistoryRequest` / `QuoteRequest`。`OrderRequest.create_order_data()` 是工厂方法。

### 1.2 业务流程标准化（`BaseGateway` 契约）

**问题**：柜台的连接、认证、登录、结算确认、查询流控、下单撤单流程各不相同。

**解法**：`BaseGateway` 定义**统一命令面 + 统一回报面**，子类只做协议适配。

**下行命令**（策略/引擎 → 网关）：
```
connect(setting) → close()
subscribe(req) 
send_order(req) -> str   # 必须回 vt_orderid，失败返回 ""
cancel_order(req)
query_account() / query_position()
send_quote / cancel_quote / query_history  # 可选
```

**上行回报**（网关 → 事件总线，**双发**）：
```
on_tick(tick)      → EVENT_TICK     + "eTick." + vt_symbol
on_order(order)    → EVENT_ORDER    + "eOrder." + vt_orderid
on_trade(trade)    → EVENT_TRADE    + "eTrade." + vt_symbol
on_position/account/contract/quote/log …
```

**标准化流程要点**：
1. **数据对象不可变约定**：推入 `on_xxx` 后视为常量，要改先 `copy`（契约，非强制）
2. **断线自动重连**、线程安全、方法非阻塞
3. **开平仓转换**（[[offset-conversion]]）：国内期货特有，`OffsetConverter` 在 OMS 层自动把一笔平仓拆成 `CLOSETODAY + CLOSEYESTERDAY`，支持锁仓/净仓模式
4. **CTP 实现对照**（[[ctp-gateway]]）：认证→登录→结算确认→查合约→下单；查询流控 while 重试；今昨仓按 SHFE/INE 特殊处理

**我们 demo 的印证**（[[ctp-open-close-demo-notes]]）：
- 同一笔 `reqOrderInsert`，上期所今仓平仓必须 `CombOffsetFlag='3'`
- 委托状态流 `提交→未成交→部分→全部/撤` 是序列不是单条
- 全账户回报流必须按 `FrontID_SessionID_OrderRef` 过滤

---

## 二、中层引擎

### 2.1 事件引擎总线（`EventEngine`，[[event-engine]] / [[event-driven-architecture]]）

**问题**：行情线程、交易回调线程、策略、UI 互相调用会死锁、阻塞、耦合。

**解法**：**一切跨模块通信走事件队列**。

```
任意线程 put(Event) → Queue → 单消费者线程 _process
                              ├─ type 专属 handlers
                              └─ general handlers（广播）
＋ 定时器线程：每 interval 秒 put(EVENT_TIMER)
```

**设计要点**：
- 事件仅 `type: str` + `data: Any`，无优先级/背压
- **单线程心脏**：任何 handler 阻塞 = 全系统卡死（策略重计算要自己丢线程）
- **双发机制**：精确订阅 `"eTick." + vt_symbol` 是独立 type，不是过滤器；unregister 只摘全局不摘精确
- `EVENT_TIMER` 驱动查询轮转（CTP 每 2 秒查资金/持仓）

### 2.2 OMS 数据缓存（`OmsEngine`，[[oms-engine]]）

**问题**：策略/UI 随时要查「当前持仓、活跃委托、最新 tick」，不能每次都打柜台。

**解法**：**内存字典全量缓存 + 事件回写**。

| 字典 | key | 维护时机 |
|---|---|---|
| `ticks / contracts` | vt_symbol | on_tick / on_contract |
| `orders / active_orders` | vt_orderid | on_order（活跃进出） |
| `trades` | vt_tradeid | on_trade |
| `positions` | vt_positionid | on_position |
| `accounts` | vt_accountid | on_account |
| `offset_converters` | gateway_name | 首次见该网关合约时惰性创建 |

**附加职责**：
- `update_order_request()`：本地假单登记（网关回执前预扣冻结）
- `convert_order_request(lock, net)`：开平拆单（见 1.2）
- `get_all_active_orders()`：撤单/对账用

**MainEngine 门面**：把 OmsEngine 的 `get_tick/get_order/...` **直接绑定为实例属性**（IDE 跳转找不到定义是正常现象）。

### 2.3 交易指令路由（`CtaEngine` 等 App 引擎，[[cta-engine]]）

**问题**：一笔委托的回报要回到**发单的那个策略**；一只票的 tick 要广播给**所有订阅它的策略**；停止单是本地条件单，要和真实委托分流。

**解法**：**三张映射表 + 事件链**。

```
symbol_strategy_map   : vt_symbol → [strategy]     # tick 广播
orderid_strategy_map  : vt_orderid → strategy      # order/trade 回调路由
strategy_orderid_map  : strategy_name → {orderid ∪ stop_orderid}  # cancel_all
```

**下单路径**：
```
CtaTemplate.buy/sell/short/cover(stop, lock, net)
  → CtaEngine.send_order
      ├─ stop=True + contract.stop_supported → 柜台条件单 (OrderType.STOP)
      ├─ stop=True + 否则 → 本地停止单 STOP.n（tick 扫描触发后转激进限价）
      └─ stop=False → send_limit_order
            → MainEngine.convert_order_request（开平拆单）
            → gateway.send_order
            → 登记 orderid_strategy_map / strategy_orderid_map
```

**事件链**：
```
EVENT_TICK  → check_stop_order → 广播 on_tick
EVENT_ORDER → 按 orderid 路由 on_order；非活跃单出表
EVENT_TRADE → vt_tradeids 去重 → 先改 pos → on_trade → sync_data
异常熔断：call_strategy_func 捕获 → trading=inited=False 紧急自停
```

**其他中层引擎**（同一抽象）：`LogEngine` / `EmailEngine` / `WechatEngine`——都是 `BaseEngine`，挂事件、做旁路服务。

---

## 三、策略应用

### 3.1 单标的时序策略（CTA，[[cta-template]]）

**定位**：一个策略盯一个合约，用时序信号（突破/均线/通道）决定开平。

**核心抽象 `CtaTemplate`**：
- 状态三元组：`inited / trading / pos`（pos 是引擎的账本，策略不手改）
- 回调：`on_init / on_start / on_stop / on_tick / on_bar / on_order / on_trade / on_stop_order`
- 下单四件套：`buy(开多) / sell(平多) / short(开空) / cover(平空)`，支持 `stop / lock / net`
- 门闩：`trading=False` 时资金动作静默返回

**行情工具**：`BarGenerator`（tick→1m→Xm/Xh/日）+ `ArrayManager`（定长序列 + TA-Lib 指标）——与事件系统零耦合，策略自己喂。

**执行抽象 `TargetPosTemplate`**：只声明 `target_pos`，模板负责「把 pos 调到目标」：
- 有在途单先撤，无在途单补差
- 实盘严格先平后开；回测直接 buy/short（失真点）

**一份代码覆盖回测实盘**：策略只调 `cta_engine` 的 duck-typed API，`CtaEngine`（实盘）与 `BacktestingEngine`（回测）各自实现同一套接口。

**示例策略教学光谱**（8 个，见 [[vnpy-ctastrategy-source]]）：
double_ma（入门）→ atr_rsi（trailing）→ boll（多周期）→ dual_thrust（日内+时间退出）→ king_keltner（OCO）→ turtle（金字塔）→ multi_signal（TargetPos）→ multi_timeframe（双周期）

### 3.2 多标的投组策略（PortfolioStrategy）

**定位**：一次决策覆盖**一篮子标的**（截面选股、行业轮动、多因子打分），按目标权重/数量批量调仓。

**与 CTA 的本质区别**：

| 维度 | CTA 单标的 | 投组多标的 |
|---|---|---|
| 信号 | 时序（自己 vs 自己的历史） | 截面（标的 vs 标的） |
| 持仓 | 1 个合约，净头寸 | N 个合约，各自目标量 |
| 调仓 | 事件驱动即时 | 定时/信号触发批量 |
| 风控 | 单品种止损 | 组合敞口、行业/市值约束 |

**生态位置**：
- 应用包 `vnpy_portfoliostategy`（**本仓库尚未 ingest 源码**，raw/ 只有 vnpy/vnpy_ctp/vnpy_ctastrategy）
- 因子研究侧同构实现：`vnpy.alpha` 的 `AlphaStrategy` + `EquityDemoStrategy`（top_k 多头、n_drop 替换、等权 round_to(100 股)）——见 [[alpha-lab]]；以及 [[alpha-mining-demo-notes]] 的因子挖掘闭环
- 课件 p.15「截面选股演进」（人工→单因子→多因子→OLS→ML）描述的正是这一层的方法谱系，表达层见 [[factor-expression-ops]]

**学习要点**：
1. 信号是**截面相对强弱**（cs_rank / cs_zscore），不是绝对涨跌
2. 调仓要处理**换手成本、涨跌停可交易性、成分股 point-in-time**（[[factor-overfitting]] 的数据侧盲点）
3. 组合回测的绩效口径是**超额收益**（vs 基准），不是单品种 Sharpe

### 3.3 价差套利类策略（SpreadTrading）

**定位**：交易**多个合约的价差**而非单腿方向，如跨期（au2612-au2706）、跨品种（卷螺）、期现。

**核心概念**：
- **价差定义**：`spread = leg1×ratio1 + leg2×ratio2 + …`（如 `1×au2612 − 1×au2706`）
- **双腿下单**：价差触发时，两条腿同时/先后发单，需处理**腿间成交不同步**（leg risk）
- **组合合约**：CTP 支持交易所组合合约（SPREAD），也可用本地合成价差 + 分腿下单

**CTP 6.7.13 新动态**（[[vnpy-ctp-source]]）：上期能源支持套利指令（`CombOffsetFlag` 两位标志，如 `'04'`=左腿开右腿平昨），以及郑商所套利确认 `ReqSpdApply` / 套保确认 `ReqHedgeCfm`。

**生态位置**：
- 应用包 `vnpy_spreadtrading`（**本仓库尚未 ingest**）
- 课件 p.13 「价差套利类策略」栏位

**学习要点**：
1. 价差均值回复 vs 价差趋势，本质是对**残差**下注
2. 腿间保证金、平今手续费差异会吃掉无风险套利空间（[[offset-conversion]] 的平今问题在这里被放大）
3. 回测必须模拟**双腿同时成交的假设**有多乐观

---

## 三层如何串起来（一笔交易的生命周期）

```
用户/策略决策
   │  buy("au2612.SHFE", 1, stop=True)
   ▼
【策略应用】CtaTemplate / PortfolioStrategy / SpreadStrategy
   │  send_order → 本地停止单或限价单
   ▼
【中层路由】CtaEngine 三张映射表登记
   │  convert_order_request（开平拆单）
   ▼
【中层缓存】OmsEngine.update_order_request 预扣冻结
   │
   ▼
【底层接口】BaseGateway.send_order → CtpTdApi.reqOrderInsert
   │  数据结构：OrderRequest → CTP dict
   ▼
柜台 / 交易所
   │  onRtnOrder / onRtnTrade
   ▼
【底层接口】翻译回 OrderData/TradeData（统一结构）
   │  on_order / on_trade 双发事件
   ▼
【事件总线】EventEngine 单线程分发
   ├→ OmsEngine 回写缓存
   ├→ CtaEngine 按 orderid 路由 → 策略 on_order/on_trade → 更新 pos
   └→ UI / 日志 / 监控
```

---

## 本仓库消化状态

| 层 | 块 | 状态 | 落点 |
|---|---|---|---|
| 底层 | 数据结构标准化 | ✅ 精读 + 实测 | [[data-objects]]、[[vt-symbol-naming]] |
| 底层 | 业务流程标准化 | ✅ 精读 + 实测 | [[base-gateway]]、[[ctp-gateway]]、[[offset-conversion]]、[[ctp-open-close-demo-notes]] |
| 中层 | 事件引擎总线 | ✅ 精读 | [[event-engine]]、[[event-driven-architecture]] |
| 中层 | OMS 数据缓存 | ✅ 精读 | [[oms-engine]]、[[main-engine]] |
| 中层 | 交易指令路由 | ✅ 精读（CTA 路径） | [[cta-engine]]、[[stop-order]] |
| 策略 | 单标的时序策略 | ✅ 精读；🔶 缺自研正式策略+回测 | [[cta-template]]、[[backtesting-engine]] |
| 策略 | 多标的投组策略 | 🔶 概念已清；源码未 ingest | [[alpha-lab]]、[[factor-expression-ops]]（研究侧） |
| 策略 | 价差套利类策略 | 🔶 概念已清；源码未 ingest | 本页；CTP 6.7.13 套利指令见 [[vnpy-ctp-source]] |

## 建议学习顺序

1. **打穿 CTA 纵切面**（当前缺口）：写一个正式 `CtaTemplate` 策略 → `BacktestingEngine` 回测 → 同一份代码接 `CtaEngine` 上 SimNow。做完这一条，三层九块就有了**一条完整的纵向证据链**
2. **补投组源码**：ingest `vnpy_portfoliostategy`，对照 [[alpha-lab]] 的 EquityDemoStrategy 看「应用层 vs 研究层」同一问题的两种解法
3. **补价差源码**：ingest `vnpy_spreadtrading`，重点看腿间同步与组合合约

## 相关页面
[[pku-veighna-course]] · [[event-driven-architecture]] · [[main-engine]] · [[oms-engine]] · [[base-gateway]] · [[cta-engine]] · [[cta-template]] · [[alpha-lab]] · [[index]]
