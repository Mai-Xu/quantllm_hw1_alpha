---
tags: [concept, architecture]
created: 2026-09-16
updated: 2026-09-24
sources: [raw/vnpy/vnpy/event/engine.py, raw/vnpy/vnpy/trader/event.py, raw/vnpy/vnpy/trader/gateway.py]
---

# 概念：事件驱动架构

VeighNa 整个系统的解耦核心。所有模块通过 `EventEngine` 通信，互相不直接调用。

## 数据流
```
网关回调线程 (on_tick/on_order/...)
   ↓ event_engine.put()
事件队列 Queue（单线程消费）
   ↓ _process: 按事件类型分发
已注册的 handlers（OmsEngine、CtaEngine、UI、LogEngine…）
```

## 事件类型设计（`trader/event.py`）
- 全局事件带尾缀点号：`EVENT_TICK = "eTick."`；网关推送时额外发一条**带 vt_symbol 后缀的专属事件**（`EVENT_TICK + tick.vt_symbol`），订阅者可精确订阅单一合约，避免收到全部行情再过滤
- **双发机制（2026-09-24 精读确认）**：`BaseGateway.on_tick` 等每次 `put` **两个** Event（全局 + 精确），不是过滤器而是两个独立 type；算队列吞吐要 ×2。只 `unregister(EVENT_TICK, h)` 不会摘掉 `"eTick."+symbol` 上的注册
- `EVENT_LOG` / `EVENT_CONTRACT` **不带尾点**、无 per-id 变体；`EVENT_TIMER` 每秒触发一次，用于轮询查询（CTP 网关的资金/持仓查询、UI 刷新）
- 本版新增 `EVENT_QUOTE`（双边报价，期权做市）

## 设计要点
- 单线程分发：所有 handler 在同一个事件线程里同步执行，因此 handler 内不能阻塞（会卡死整个系统）；策略的 on_bar/on_tick 实际运行在事件线程中
- 双通道注册：`register(type, handler)` 按类型注册，`register_general(handler)` 监听所有事件；`register` 对同函数同类型去重
- 无优先级/无背压/无丢弃：慢 handler = 全总线阻塞
- 事件驱动 ≠ 异步：handler 抛异常只会打印 traceback（`_process` 外层由调用方捕获），CtaEngine 用 `call_strategy_func` 包一层并停掉异常策略

## 相关页面
[[event-engine]] · [[main-engine]] · [[cta-engine]] · [[ctp-gateway]] · [[wiki/sources/pku-veighna-course]]
