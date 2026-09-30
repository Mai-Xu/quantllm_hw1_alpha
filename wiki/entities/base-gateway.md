---
tags: [entity, module, gateway]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy/vnpy/trader/gateway.py]
---

# 实体：BaseGateway（网关抽象基类）

`raw/vnpy/vnpy/trader/gateway.py:33`。所有柜台接口（CTP、股票、外盘等）的统一契约，实现"翻译官"角色：外部柜台协议 ⇄ vnpy 统一事件。

## 实现要求（docstring 明确约定）
- **线程安全**、所有方法**非阻塞**、断线**自动重连**
- 回调 `on_tick/on_trade/on_order/on_position/on_account/on_contract` 必须手动调用；传入的 Data 对象视为不可变（缓存需 copy）

## 事件推送模式（关键设计）
每个 on_xxx 推**两条**事件：全局事件（`EVENT_TICK`）+ 精确事件（`EVENT_TICK + vt_symbol`），让消费者可按合约订阅。唯一例外 on_contract 只推全局。

## 抽象方法
`connect(setting) / close() / subscribe(req) / send_order(req) / cancel_order(req) / query_account() / query_position()`；可选实现 `send_quote/cancel_quote`（双边报价）和 `query_history`（历史K线）。

## send_order 契约
用 `req.create_order_data(orderid, gateway_name)` 造 OrderData；发出成功置 SUBMITTING、失败置 REJECTED 并回调 on_order；返回 vt_orderid。

类属性：`default_name`（网关名）、`default_setting`（连接配置字段，GUI 自动生成表单）、`exchanges`（支持的交易所列表）。

相关：[[ctp-gateway]] · [[data-objects]] · [[event-driven-architecture]]
