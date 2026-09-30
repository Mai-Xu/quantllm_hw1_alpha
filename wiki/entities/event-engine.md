---
tags: [entity, module]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy/vnpy/event/engine.py]
---

# 实体：EventEngine / Event（vnpy.event）

整个框架的的消息总线，仅 146 行，无任何 vnpy 依赖，可独立使用。

- `Event(type: str, data: Any)`：type 用于分发，data 携带任意负载
- 两个线程：`_run`（Queue 消费+分发，`get(timeout=1)` 便于优雅退出）、`_run_timer`（每 interval 秒投递 `EVENT_TIMER`）
- `_process` 先分发给该 type 的 handler 列表，再分发给 general handlers
- `register/unregister` 保证同一 handler 对同一 type 只注册一次；type 无 handler 后从 dict 清除
- `stop()` 先置 `_active=False` 再 join 两个线程（timer 最多 1 秒后退出）

注意：handler 在事件线程**同步串行**执行——任何阻塞调用都会拖垮全系统，这是写策略时最重要的约束。

相关：[[event-driven-architecture]] · [[main-engine]]
