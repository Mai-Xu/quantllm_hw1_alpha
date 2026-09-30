---
tags: [concept, order, risk]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy_ctastrategy/vnpy_ctastrategy/base.py, raw/vnpy_ctastrategy/vnpy_ctastrategy/engine.py]
---

# 概念：本地停止单（Stop Order）

CTP 柜台不支持止损单，vnpy 在 CTA 引擎内用软件模拟，是策略风控的关键机制。

## 三种实现路径（`CtaEngine.send_order`，`stop=True` 时）
1. **服务器停止单**：合约 `stop_supported=True` 的网关直接发 `OrderType.STOP`；CTP 不支持
2. **本地停止单**（默认路径）：`send_local_stop_order` 创建 `StopOrder` 对象存入 `stop_orders` dict，id 格式 `STOP.{n}`（`STOPORDER_PREFIX`），不经过柜台
3. **回测停止单**：`BacktestingEngine` 同样本地模拟

## 触发逻辑（实盘 `CtaEngine.check_stop_order`，每个 tick 检查）
- 多头止损：`tick.last_price >= stop_order.price` 触发；空头相反
- 触发后立刻发**限价单**：多头用涨停价（无涨停用 ask_price_5）、空头用跌停价（bid_price_5）——近似市价单保证立即成交
- 触发价被 `round_to(price, pricetick)` 取整过，注意 tick 可能跳空穿越触发价

## 与回测的差异
回测 bar 模式下 `cross_stop_order` 用 bar 的 high/low 判断穿越，成交价取 `max(stop_price, bar.open)`——跳空时按更差价格成交，模拟合理；但实盘触发后按涨跌停限价追单，成交价取决于盘口，两者行为可能不一致（回测偏乐观/悲观取决于场景）。

## StopOrder 对象（base.py）
dataclass：vt_symbol/direction/offset/price/volume/stop_orderid/strategy_name/datetime/lock/net/vt_orderids/status；状态只有 WAITING/CANCELLED/TRIGGERED 三种。

相关：[[cta-engine]] · [[backtesting-engine]]
