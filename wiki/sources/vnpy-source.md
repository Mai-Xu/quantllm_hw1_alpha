---
tags: [source, vnpy, framework]
created: 2026-09-16
updated: 2026-09-24
sources: [raw/vnpy]
---

# 来源：vnpy 主框架源码

- 位置：`raw/vnpy`（Gitee main 分支快照，**4.4.0**，与 Gitee 逐文件一致，仅 CRLF/LF 差异）
- 结构：`vnpy/vnpy/` 下子包 —— `event`（事件引擎）、`trader`（交易核心）、`chart`（K线图表）、`rpc`（ZeroMQ RPC）、`alpha`（机器学习 Alpha 因子研究）；另有 `examples/`、`docs/`、`tests/`
- 核心依赖：事件驱动全部解耦；技术指标依赖 `talib`；数据库/数据服务通过插件模块 `vnpy_<name>` 动态加载（`database.py`、`datafeed.py` 中 `import_module`）

## 关键结论
- vnpy 本体只是一个**骨架**：所有交易能力（网关 vnpy_ctp、应用 vnpy_ctastrategy、数据库 vnpy_sqlite、数据服务 vnpy_datayes 等）都是独立 pip 包，通过 `add_gateway` / `add_app` / `get_database` 动态装配
- `MainEngine` 是装配中心：持有 gateways / engines / apps 三个 dict，并把 OmsEngine 的 get_xxx 方法**直接绑定为实例属性**（`raw/vnpy/vnpy/trader/engine.py#MainEngine.init_engines` L145-163）——IDE 跳转找不到定义是正常现象
- 配置与数据目录：优先当前目录的 `.vntrader/`，否则用户主目录（`utility.py#_get_trader_dir`）；`MainEngine.__init__` 会 `os.chdir(TRADER_DIR)`（相对路径 IO 会「莫名」落到交易目录）
- 内置 4 引擎：LogEngine / OmsEngine / EmailEngine / **WechatEngine**（4.x 新增企业微信 iLink 推送，队列+限频，协议在 `wechat.py`）
- 数据对象含 **QuoteData 双边报价**路径（期权做市）：`send_quote`/`cancel_quote`/`on_quote`，与 Order 路径平行
- 事件**双发**：每条 tick/order/trade 等会 `put` 两次（全局 `eTick.` + 精确 `eTick.`+vt_symbol），见 [[event-driven-architecture]]

## 4.4.0 相对旧认知的增量
- `vnpy.alpha` 成熟：`register_functions` 自定义表达式算子、`process_replace_inf/ts_norm/drop_feature/cs_fill_na` 处理函数、DataProxy 反向运算/取模/幂/不等
- `MainEngine.send_notification` 统一邮件+微信
- 新增 `vnpy_questdb` 存储选项（生态包）

## 2026-09-24 精读补遗（高价值坑）
1. 数据对象无 `frozen=True`，「推入回调后不可变」是**约定非强制**；OMS 存引用，原地改字段会污染全局缓存
2. 枚举值大量本地化中文（`Direction.LONG.value=="多"`）→ `vt_positionid` 随 locale 变化
3. `Exchange.EUREX.value=="EUX"`，不能用 `"EUREX"` 反解
4. `BaseDatafeed` **不是 ABC**：未配置时静默返回空列表，回测可能 0 条数据而不报错
5. `converter.py#convert_order_request_net` L292 `volume_left -= pos_available` 疑似应为 `close_volume`（逻辑雷）
6. `MainEngine.close` 先停 EventEngine → 退出瞬间未处理回报直接丢弃
7. gateway_name 含 `.` 会拆错 `vt_orderid`（converter L66）

## 已建相关页面
[[main-engine]] · [[event-engine]] · [[oms-engine]] · [[base-gateway]] · [[data-objects]] · [[bar-synthesis]] · [[offset-conversion]] · [[optimize-engine]] · [[rpc-module]] · [[alpha-dataset]] · [[alpha-lab]]
