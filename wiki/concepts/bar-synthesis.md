---
tags: [concept, data, indicator]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy/vnpy/trader/utility.py]
---

# 概念：K线合成与指标计算

策略消费的两层工具，都在 `raw/vnpy/vnpy/trader/utility.py`。

## BarGenerator（K线合成器）
两条流水线：
1. **tick → 1分钟K**（`update_tick`）：按 tick 的分钟变化切割；用 `last_price` 更新 OHLC，同时用 tick 的当日高低价修正 high/low；volume/turnover 用 **相邻 tick 累计值之差**（负值丢弃）增量累计——因为 CTP 的 Volume 是当日累计量
2. **1分钟K → N分钟/N小时/日K**（`update_bar`）：
   - N 分钟：x 必须整除 60（2/3/5/6/10/15/20/30），按 `(minute+1) % window == 0` 切割
   - N 小时：先合成 1h bar（minute==59 或跨小时时推送），再按 window 计数合成 N 小时
   - 日K：构造时必须传 `daily_end`（每日收盘时间），收盘时间到达即推送（`Interval.DAILY` 不传会 raise）
- `generate()` 手动推送未完结的当前分钟 bar（收盘时调用）

## ArrayManager（时序数组 + 技术指标）
- 固定长度 numpy 环形数组（默认 size=100），每根 bar 左移一位追加新值；`count >= size` 后 `inited = True`（策略通常等 inited 才交易）
- 指标全部封装 talib：sma/ema/kama/wma/macd/rsi/atr/boll/keltner/donchian/aroon/stoch/sar 等 40+，每个都支持 `array=True` 返回整条序列（默认只返回最新值）
- 典型用法见 `raw/vnpy_ctastrategy/vnpy_ctastrategy/strategies/atr_rsi_strategy.py`：`bg = BarGenerator(self.on_bar)` + `am = ArrayManager()`，on_tick 喂 bg，on_bar 喂 am

## 相关页面
[[cta-template]] · [[data-objects]]
