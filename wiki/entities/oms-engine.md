---
tags: [entity, module]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy/vnpy/trader/engine.py, raw/vnpy/vnpy/trader/converter.py]
---

# 实体：OmsEngine（订单管理系统）

`raw/vnpy/vnpy/trader/engine.py:360`。订阅全部业务事件，维护内存中的全量缓存，是"当前市场/账户状态"的单一数据源。

## 状态缓存（全部 dict，key 为 vt_ 前缀 ID）
`ticks / orders / trades / positions / accounts / contracts / quotes`，另有 `active_orders` / `active_quotes`（只保留活动单：order 事件中 `is_active()` 判断进出）。提供 get_xxx / get_all_xxx 查询。

## 附带职责：OffsetConverter 管理
- 每收到新合约事件即为该网关建一个 `OffsetConverter`（按 gateway_name 索引，因为开平规则跟柜台/合约有关）
- order/trade/position 事件同步喂给 converter 维护仓位簿记（用于自动拆平今平昨）
- 对外暴露 `convert_order_request` / `update_order_request`，MainEngine 再转绑

注意：OMS 缓存**不持久化**——重启后依赖网关 connect 时重新查询（CTP 网关连接后查合约/资金/持仓重建）。

相关：[[main-engine]] · [[offset-conversion]] · [[data-objects]]
