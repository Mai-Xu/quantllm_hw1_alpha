---
tags: [entity, cta, template]
created: 2026-09-16
updated: 2026-09-24
sources: [raw/vnpy_ctastrategy/vnpy_ctastrategy/template.py]
---

# 实体：CtaTemplate / TargetPosTemplate（策略模板）

`raw/vnpy_ctastrategy/vnpy_ctastrategy/template.py`。策略唯一需要继承的基类，同一份代码跑实盘与回测（cta_engine 注入谁就是谁）。

## CtaTemplate
- 核心状态：`inited / trading / pos`（pos 由引擎维护，策略不应手改）
- 类属性 `parameters`（可配置参数名列表，写入 json）/ `variables`（监控变量名列表，构造时自动插入 inited/trading/pos）
- 回调：`on_init/on_start/on_stop/on_tick/on_bar/on_trade/on_order/on_stop_order`（只有 on_init 是 abstract）
- 交易便捷方法：`buy(开多)/sell(平多)/short(开空)/cover(平空)`，参数 `stop/lock/net`；内部都走 `send_order`，**trading=False 时静默返回空列表**（初始化阶段只计算不下单）
- 引擎代理：`get_pricetick/get_size/get_engine_type/load_bar/load_tick/write_log/put_event/sync_data/send_notification`

## CtaSignal
轻量信号类：只有 `signal_pos` 目标仓位概念 + on_bar/on_tick，用于多信号组合策略（如 multi_signal_strategy）。

## TargetPosTemplate（目标仓位模板）
"只声明目标仓位，模板负责执行"：
- `set_target_pos(n)` → trade()：有活动单先撤光（cancel_orderids 防重复撤），无单则补差
- **回测 vs 实盘分叉**（template.py L471-498）：回测一次 `buy`/`short` 全量 `abs(pos_change)`；实盘严格先平后开（cover/sell 再 buy/short）且有在途单就跳过——回测无开平/平今约束是失真源
- 挂单价 = 对手价 ± tick_add，并夹在涨跌停范围内；只有 bar 则 `close ± tick_add`

## 标准策略骨架（参考 atr_rsi_strategy.py）
```
on_init: 建 BarGenerator/ArrayManager，load_bar(10) 预热
on_tick: bg.update_tick(tick)
on_bar:  am.update_bar → 指标计算 → 仓位决策 → 下单/撤单 → put_event()
```
示例策略教学意图对照见 [[vnpy-ctastrategy-source]]（8 个策略各自演示的模式）。

相关：[[cta-engine]] · [[backtesting-engine]] · [[bar-synthesis]]
