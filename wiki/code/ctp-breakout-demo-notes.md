---
tags: [code, ctp, demo, order]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy_ctp/vnpy_ctp/gateway/ctp_gateway.py, projects/ctp_breakout_demo/demo.py]
---

# Code 笔记：ctp_breakout_demo（突破触发下单 DEMO）

`projects/ctp_breakout_demo/demo.py`：demo2，在 [[ctp-demo-notes]] 基础上打通交易闭环。**SimNow 实测成交**（2026-09-16 14:34，au2612 买开 1 手 @ 938.8）。

## 结构
- `SimpleTdApi`：认证 → 登录 → **确认结算单** → 就绪；`send_order` 按 CtpGateway 字段模板组装 reqOrderInsert（限价/方向/开平/OrderRef 自增/GFD/AV 等必填项）
- `StrategyMdApi`：tick → 突破状态机（WAITING→TRIGGERED，只发一单）→ 调 td_api.send_order
- 双线就绪同步：突破可能早于结算单确认（SimNow 确认耗时 10~20 秒），td 就绪回调 `ready_hook` 注入策略的 `try_trigger` 用最新价重试，不丢信号

## 新踩坑
1. **结算单确认是下单前置**（`reqSettlementInfoConfirm`），否则柜台拒单——CtpGateway 在 onRspUserLogin 里立即自动确认的原因
2. **回报是全账户流**：`onRtnOrder/onRtnTrade` 推送该账号**所有程序**的委托。实测输出中出现两笔 au2612 买1手成交（session 936717771 与 947206615），后者才是本 demo 的。结论：过滤自己的委托必须比对 `FrontID_SessionID_OrderRef`，只按 InstrumentID 过滤不够。CtpGateway 用 `sysid_orderid_map` + 主动推本地 OrderData 来对账
3. **OrderStatus='a'（未知/已提交）会推送多次**，同一委托状态流是"提交→未成交→部分→全部/撤销"序列，不是单条
4. 突破阈值用首个 tick + 偏移动态设定（演示用）；正式实现应基于历史数据/前高前低

## 与 CtaEngine 的对照
本 demo 的"阈值触发"本质是 CTA 模块的**本地停止单**（[[stop-order]]）：tick 检查 → 转限价单追价（PRICE_OFFSET≈tick_add）。CtaEngine 额外做了：策略映射、异常熔断、pos 跟踪、事件引擎解耦。

## 下一步候选
- 用 OrderRef + FrontID/SessionID 精确过滤自己的回报（补 demo3）
- 对撤单（reqOrderAction）与持仓查询（reqQryInvestorPosition）
- 用 MainEngine + CtpGateway 重写同策略，对照两层实现差异

## 代码取舍记录（2026-09-16 质量优化）
- **移除 `onRspOrderAction`**：demo 没有任何撤单路径，纯死回调；做撤单教学时再加回
- **移除环境变量参数覆盖**（用户要求）：策略参数只以脚本顶部常量存在，验证下单链路时临时改 `TRIGGER_OFFSET` 为负值即可
- **`ready_hook`**（原 `on_ready`）：类型修正为 `Callable[[], None] | None`；回调注入模式保留（SimNow 结算单确认耗时长，就绪重试是实测踩坑后的设计）
- **保留私有/公有流订阅**（与 demo1 不同）：本 demo 需要接收 onRtnOrder/onRtnTrade 交易推送
- env 变量解析去掉 `or 0` 空串防护（demo 属过度设计）；`SYMBOL_EXCHANGE` 定义挪到顶部配置区；登录请求体同样抽 `make_login_req()`；`FLOW_PATH` 统一 `Path`；`sys.exit` 移除
- 2026-09-16 二轮简化（用户要求）：常量全部行内注释（连续块 # 对齐）、全部类/方法补一行 docstring、SETTING/策略参数回落为纯脚本常量
- **demo 间约 120 行样板刻意不抽公共模块**：保持单文件自足，`diff demo1 demo2` 即"demo2 多了什么"的教学材料；demo 涨到 4~5 个再考虑 `ctp_common.py`

## 相关页面
[[ctp-demo-notes]] · [[ctp-gateway]] · [[stop-order]] · [[event-driven-architecture]]
