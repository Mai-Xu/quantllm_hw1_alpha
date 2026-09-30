---
tags: [entity, module]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy/vnpy/trader/engine.py]
---

# 实体：MainEngine（vnpy.trader.engine）

交易平台的装配中心与统一 API 门面（`raw/vnpy/vnpy/trader/engine.py:81`）。

## 职责
1. 启动全局唯一的 `EventEngine`
2. 装配三个容器：`gateways` / `engines` / `apps`（dict）；`add_gateway` 同时收集各网关支持的交易所
3. **门面转发**：connect/subscribe/send_order/cancel_order/query_history 等都只是"查 gateway → 记日志 → 调用对应方法"
4. `init_engines` 内置 LogEngine、OmsEngine、EmailEngine、WechatEngine；并把 OmsEngine 的全部 get_xxx **绑定成 MainEngine 自己的方法**（所以外部直接 `main_engine.get_order(...)`）

## 内置引擎
- `LogEngine`：注册 EVENT_LOG，经 loguru 写文件/控制台（受 `SETTINGS["log.active"]` 控制）
- `EmailEngine` / `WechatEngine`：后台线程 + 队列异步发送通知；`send_notification()` 同时走两个渠道；WeChat 有 60 秒限速与会话过期处理
- `BaseEngine(ABC)`：所有功能引擎的基类，约定 `main_engine/event_engine/engine_name` 三属性

## 生命周期
`close()` 顺序：先停事件引擎（防新 timer 事件）→ 逐个 engine.close → 逐个 gateway.close。上层应用（如 veighna_trader GUI）必须保证调用。

相关：[[event-engine]] · [[oms-engine]] · [[base-gateway]] · [[event-driven-architecture]]
