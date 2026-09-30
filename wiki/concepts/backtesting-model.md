---
tags: [concept, backtesting]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy_ctastrategy/vnpy_ctastrategy/backtesting.py]
---

# 概念：回测撮合与绩效模型

## 撮合模型（`cross_limit_order` / `cross_stop_order`）
每根新 bar/tick 先撮合旧挂单，再调用策略 on_bar/on_tick（顺序重要）。

**限价单（bar 模式）**：
- 多单可成交：`order.price >= bar.low_price`；空单：`order.price <= bar.high_price`
- 成交价 `min(order.price, bar.open_price)`（多头）——对投资者有利的假设：开盘价优于限价按开盘价成交
- **整单立即全量成交**，无排队/部分成交模拟，这是与实盘最大的偏差

**tick 模式**：用 ask_1/bid_1 判断与成交，更精细。

**停止单**：bar 高低价穿越触发，成交价 `max(stop_price, bar.open)`。

## 成本模型（DailyResult.calculate_pnl）
- 手续费：`turnover * rate`（比例费率，不支持固定每手费用）
- 滑点：`volume * size * slippage`（每手固定滑点金额，需按合约换算）
- 逐日盯市：`holding_pnl = start_pos * (close - pre_close) * size`；`trading_pnl` 按当日成交与收盘价计算；`net_pnl = trading + holding - commission - slippage`

## 绩效指标（calculate_statistics）
- 日收益用 **对数收益** `log(balance/pre_balance)`；爆仓（balance<=0）直接判定无法计算
- Sharpe：日频年化 `√240`；EWM Sharpe：半衰期（默认120日）指数加权的版本，更重视近期表现
- RGR Ratio（新指标）：`(log收益增益 × 稳定性 × 偏度因子 × 峰度惩罚) / (0.5×下行风险 + 0.3×最大回撤 + 0.2×CVa95)`

## 参数优化
穷举（`run_bf_optimization`）与遗传算法（`run_ga_optimization`）均通过 multiprocessing 并行，`evaluate` 函数独立构造 BacktestingEngine；数据库加载用 `lru_cache` 避免重复读库。

## 相关页面
[[backtesting-engine]] · [[stop-order]]
