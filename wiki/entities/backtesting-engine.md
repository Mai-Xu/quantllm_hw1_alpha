---
tags: [entity, backtesting]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy_ctastrategy/vnpy_ctastrategy/backtesting.py]
---

# 实体：BacktestingEngine（回测引擎）

`raw/vnpy_ctastrategy/vnpy_ctastrategy/backtesting.py:46`。独立于 MainEngine/EventEngine 的**单合约单策略**回测器，通过实现与 CtaEngine 相同的方法集（send_order/load_bar/get_pricetick/...）让 CtaTemplate 无感切换。

## 使用流程
```python
engine = BacktestingEngine()
engine.set_parameters(vt_symbol, interval, start, rate, slippage,
                      size, pricetick, capital, end, mode)
engine.add_strategy(MyStrategy, {})
engine.load_data()          # 从数据库分批加载（进度条）
engine.run_backtesting()    # 逐条回放
engine.calculate_result()   # 逐日盯市 DailyResult
engine.calculate_statistics()
engine.show_chart()         # plotly 四联图
```

## 回放循环（new_bar）
每根 bar：`cross_limit_order` → `cross_stop_order` → `strategy.on_bar(bar)` → `update_daily_close`。先撮合后推送，保证策略看到当根 bar 时挂单已处理。

## 与实盘引擎的行为差异（写策略需注意）
| 方面 | 回测 | 实盘 |
|---|---|---|
| 撮合 | 下一根 bar 一次性全量成交 | 部分成交/排队/未成交 |
| 停止单 | bar 高低价穿越 | tick last_price 触发+涨跌停限价追单 |
| pos 维护 | 撮合时直接 ± | trade 事件驱动 |
| sync_data/通知/put_event | 空操作 | json 持久化/推送 |
| load_bar | 从 start 往前取 N 天 | 网关/datafeed/数据库 |

## DailyResult
按日聚合 trades，计算 holding_pnl（盯市）/ trading_pnl / commission / slippage / net_pnl，`calculate_result` 串起逐日链（start_pos = 前日 end_pos）。

## 参数优化
`run_bf_optimization`（穷举）/ `run_ga_optimization`（遗传算法，deap）；`evaluate` 在子进程中独立建引擎跑完整回测返回 (setting, target_value, statistics)；`load_bar_data` 用 lru_cache 缓存数据库读取。

相关：[[cta-template]] · [[backtesting-model]] · [[stop-order]]
