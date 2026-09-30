---
tags: [source, cta, strategy, backtesting]
created: 2026-09-16
updated: 2026-09-24
sources: [raw/vnpy_ctastrategy]
---

# 来源：vnpy_ctastrategy 源码

- 位置：`raw/vnpy_ctastrategy`（Gitee main，**1.4.1**）
- 结构：`base.py`（58 行，StopOrder/事件）、`template.py`（498 行，CtaTemplate/CtaSignal/TargetPosTemplate）、`engine.py`（970 行，CtaEngine）、`backtesting.py`（1269 行，BacktestingEngine+DailyResult+RGR）、`strategies/`（8 示例+Test）、`ui/`（CtaManager/RolloverTool）
- 挂载：`CtaStrategyApp(BaseApp)` → `engine_class=CtaEngine`

## 关键结论
- 实盘与回测共用同一套 `CtaTemplate` 接口（鸭子类型：策略只调 `cta_engine` 方法），见 [[cta-template]]
- 实盘三张映射表：`symbol_strategy_map` / `orderid_strategy_map` / `strategy_orderid_map`，见 [[cta-engine]]
- 本地停止单 `STOP.n`：tick 扫描触发后以 **ask5/bid5 或涨跌停价**转激进限价；柜台 `stop_supported` 则走 `OrderType.STOP`
- 回测撮合：**先撮旧单再跑策略**（防前视）；限价穿越 bar 高低价、最优价取 open（跳空让利）；停止单触发即全成（跳空取不利价）；**一律全成、无部分成交**
- 绩效：Sharpe / **EWM Sharpe**（halflife=120 时变）/ **RGR**（1.4.0 新增，1.4.1 去 empyrical 依赖）/ 收益回撤比等 27 项
- 策略异常熔断：`call_strategy_func` 捕获后 `trading=inited=False` 紧急自停

## 8 示例策略教学意图
| 策略 | 演示 |
|---|---|
| double_ma | 入门金叉死叉 + 先平后开 |
| atr_rsi | 趋势过滤 + 百分比 trailing 止损 + 每 bar cancel_all 重挂 |
| boll_channel | 多周期 BG（1m→15m）+ 突破停止单 + ATR 止损 |
| dual_thrust | 日内区间突破 + 尾盘时间退出 + 防重复开仓 |
| king_keltner | 手工 OCO 双边挂单 + 显式 orderid 管理 |
| turtle_signal | 唐奇安 + ATR 金字塔 4 层 + 成交反馈设 2N 止损 |
| multi_signal | **TargetPosTemplate** + CtaSignal 组件投票 |
| multi_timeframe | 双 BG/双 AM，大周期定方向小周期择时 |
| test | 网关连通性/延迟压测（市价/限价/撤单/停止单） |

## 2026-09-24 精读补遗
- **TargetPosTemplate 回测 vs 实盘分叉**（`template.py:471-498`）：回测一次 buy/short 全量；实盘严格先平后开且有在途单就跳过——回测无开平/平今约束是失真源
- 回测忽略 `lock/net`；忽略 min_volume；`annual_return` 线性外推非 CAGR
- RGR 中 downside 年化用 **252** 而 `annual_days=240`（口径不一致）
- 实盘 init 走 `ThreadPoolExecutor(max_workers=1)` 串行；回测同步
- `RolloverTool`：先移仓（反向平旧+同向开新）再移策略状态（pos 写回 + sync_data）
- 配置文件：`cta_strategy_setting.json` / `cta_strategy_data.json`（trade 后与 stop 时落盘；回测空实现）

## 已建相关页面
[[cta-engine]] · [[cta-template]] · [[backtesting-engine]] · [[backtesting-model]] · [[stop-order]] · [[bar-synthesis]] · [[optimize-engine]]
