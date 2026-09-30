---
tags: [code, ctp, demo]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy_ctp/vnpy_ctp/gateway/ctp_gateway.py, projects/ctp_demo/demo.py]
---

# Code 笔记：ctp_demo（最小化 CTP 底层 API DEMO）

`projects/ctp_demo/demo.py`：绕过 vnpy 框架层，直接继承 `vnpy_ctp.api.MdApi/TdApi`，验证柜台连接/登录/订阅/行情打印四件事。**已在 SimNow 实测跑通**（2026-09-16 14:09，收到 au2612/rb2610/au2706 实时行情，交易交易日 20260916）。

## 与 CtpGateway 的对照
本 DEMO 是 [[ctp-gateway]] 的极简版，去掉的三层：
- 事件引擎推送（on_xxx → event_engine.put）——直接 print
- ContractData 翻译与 `symbol_contract_map` 依赖——直接用原始 dict
- 结算单确认、合约/持仓/资金查询、流控重试——只保留握手最小路径

## 踩坑记录（重要）
1. **`super().__init__()` 必须调用**：pybind11 扩展类，不调直接 `TypeError`
2. **`subscribeMarketData` 签名**：已装 6.7.11.3 绑定一次只接受 `str`（单合约）；raw 源码 6.7.11.4 的 gateway 用法相同（逐个订阅）
3. **摘牌合约订阅无错误回报**：au2512/rb2510（2025 年合约）订阅后 `onRspSubMarketData` 不报错、`onRtnDepthMarketData` 也无推送——写程序时合约列表需要动态获取（正式做法：TdApi 登录后 `reqQryInstrument` 全量查询，见 CtpGateway 的合约缓存机制）
4. **回调线程与主线程并发**：print 交错（日志中两条消息黏行），正式实现需队列或锁——这正是 vnpy 用事件队列单线程分发的原因（见 [[event-driven-architecture]]）
5. SimNow 交易前置必须先终端认证（AppID + AuthCode），ErrorID=63（授权码错）后不应重试

## 下一步候选
- 演示下单：TdApi `reqOrderInsert`（需先 `reqSettlementInfoConfirm` 确认结算单）
- 演示合约查询 `reqQryInstrument` 替代硬编码合约列表
- 对比封装层：同样逻辑用 MainEngine + CtpGateway 重写一遍

## 代码取舍记录（2026-09-16 质量优化）
对照评审做了一轮精简，**以下是故意不写的防御代码及理由**：
- **不订阅私有/公有流**（`subscribePrivateTopic/PublicTopic`）：那是需要接收委托/成交推送的正式网关（CtpGateway、demo2）才需要的概念，本 demo 只读行情
- **`subscribe()` 不做"已登录再补发"分支**：main 在 connect 后立即调 subscribe，登录回调在 CTP 线程异步执行，该分支恒为死代码；正确的时序是"登记列表 → onRspUserLogin 统一订阅"（顺带覆盖断线重连恢复订阅）
- **不调 `sys.exit(0)`**：KeyboardInterrupt 后 main 自然返回即可
- 两个 API 的登录请求体逐字相同 → 抽 `make_login_req()`，这一点本身就是知识点
- `FLOW_PATH` 全程用 `Path`、模块级 `mkdir`；订阅列表用 list（打印顺序确定，便于运行间对比）
- `log()` 统一 `flush=True`（固化"回调线程 print 默认缓冲会黏行"的教训）
- 2026-09-16 二轮简化（用户要求）：常量全部行内注释（连续块 # 对齐）、全部类/方法补一行 docstring

## 相关页面
[[ctp-gateway]] · [[base-gateway]] · [[event-driven-architecture]] · [[vnpy-ctp-source]] · [[ctp-breakout-demo-notes]]
