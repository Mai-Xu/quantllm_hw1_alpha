---
tags: [entity, cta, engine]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy_ctastrategy/vnpy_ctastrategy/engine.py]
---

# 实体：CtaEngine（CTA 实盘引擎）

`raw/vnpy_ctastrategy/vnpy_ctastrategy/engine.py`，以 App（"CtaStrategy"）形式挂到 MainEngine。

## 三张核心映射表
- `symbol_strategy_map: vt_symbol → [strategy]`：tick 事件分发入口
- `orderid_strategy_map: vt_orderid → strategy`：order/trade 事件回溯到策略
- `strategy_orderid_map: strategy_name → set(vt_orderid)`：撤全部单/移除策略
- 另有 `stop_orders`（本地停止单池）与 `classes`（策略类注册表）

## 事件处理链
- **tick**：先 `check_stop_order(tick)` 检查所有本地停止单 → 逐个调用订阅策略的 on_tick（仅 inited 的）
- **trade**：`vt_tradeids` 集合去重；**先更新 `strategy.pos`（±volume）再调 on_trade**；随后 `sync_strategy_data`（变量持久化到 cta_strategy_data.json，恢复时用于重启还原仓位等变量）并 put_strategy_event 刷新 UI
- **order**：非活动单移出映射；服务器停止单类型映射回 StopOrder 再回调 on_stop_order

## 下单链路（策略视角）
`strategy.buy/sell/short/cover` → `CtaEngine.send_order`：取合约 → 价格/数量按 pricetick/min_volume 取整 → stop 参数分流（本地停止单 vs 限价/服务器停止单）→ `send_server_order` 构造 OrderRequest（reference 填 "CtaStrategy_策略名"）→ **经 OffsetConverter 转换拆单** → 逐笔 MainEngine.send_order 并登记映射。

## 策略生命周期
add → init（`init_executor` 单线程池排队执行，防多策略同时 load_bar 阻塞事件线程；on_init → 恢复 data → 订阅行情 → inited=True）→ start（on_start → trading=True）→ stop（on_stop → trading=False → cancel_all → sync）→ remove（必须先 stop）。

## 其他要点
- 策略类加载：包内 strategies/ 目录 + **当前工作目录 strategies/**（py/pyd/so），importlib.reload 保证热更新
- `call_strategy_func` 捕获一切异常：置 trading=False、inited=False（策略出错自动熔断停止）
- 设置持久化：cta_strategy_setting.json（参数）/ cta_strategy_data.json（变量）
- `load_bar` 数据源优先级：网关历史接口（contract.history_data）→ datafeed 数据服务 → 本地数据库

相关：[[cta-template]] · [[stop-order]] · [[offset-conversion]] · [[event-driven-architecture]]
