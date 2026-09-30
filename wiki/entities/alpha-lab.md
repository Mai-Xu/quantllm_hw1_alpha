---
tags: [entity, alpha, lab, storage]
created: 2026-09-24
updated: 2026-09-24
sources: [raw/vnpy/vnpy/alpha/lab.py, raw/vnpy/vnpy/alpha/strategy]
---

# 实体：AlphaLab / Alpha 回测策略

`raw/vnpy/vnpy/alpha/lab.py`（数据中枢）+ `alpha/strategy/`（组合回测）——研究到组合落地的存储与消费层。

## AlphaLab 存储布局

```
lab_path/
  daily/{vt_symbol}.parquet      # 日线
  minute/{vt_symbol}.parquet     # 分钟线
  component/{index_symbol}       # shelve: {"YYYY-MM-DD": [symbols]}
  dataset/{name}.pkl             # pickle 整个 AlphaDataset
  model/{name}.pkl               # pickle 整个 AlphaModel
  signal/{name}.parquet          # 预测信号 (datetime,vt_symbol,signal)
  contract.json                  # 费率/size/pricetick
```

## 关键行为（`lab.py`）
- **`load_bar_df` 价格归一化**（L216-224）：价格除以首日 close——表达式里 `close` 是**相对价**，`volume` 是绝对量；量纲类因子要意识到这一点
- 停牌日（行和为 0）置 NaN；自动算 `vwap=turnover/volume`
- **`load_component_filters`**（L301-347）：指数成分变化 → `symbol → [(start,end)]` 存续区间，直接喂 `prepare_data(filters=)`，**防幸存者偏差/前视成分**
- `load_contract_setttings` 拼写为源码原貌（三 t）

## Alpha 回测（`strategy/`，股票向组合回测，独立于 [[backtesting-engine]]）
- `BacktestingEngine(lab)`：`set_parameters` 从 lab 的 contract.json 读费率；`add_strategy(cls, setting, signal_df)` **直接灌入模型预测信号**
- 回放按 dt 切片 `on_bars(bars: dict[vt_symbol,BarData])`；缺 bar 用前收盘合成
- 撮合 `cross_order`：限价 vs bar 高低价；**涨跌停 ±10% 固定比例**（A 股风格，非 A 股需改）；现金/手续费实时扣减
- `AlphaStrategy`：`on_init / on_bars / on_trade`；`set_target` + `execute_trading` 自动拆 buy/cover、sell/short
- **`EquityDemoStrategy`**：top_k 多头、n_drop 替换、min_days 持有、成分过滤、等权 round_to(100 股)——Agent 信号的标准消费样例

## 信号契约
模型/因子产出固化为 `signal DF(datetime, vt_symbol, signal)` → `lab.save_signal` → 回测 `add_strategy(..., signal_df)`。**跳过 ML 直接用表达式原始值当 signal 即可单因子选股。**

## 研究流水线（examples/alpha_research/*.ipynb）
`AlphaLab` → `load_bar_df` → Alpha158/101 → `prepare_data(filters)` → `process_data` → 模型 fit → `predict(TEST)` → `save_signal` → 回测 + EquityDemoStrategy。

## 与本仓库实战
[[alpha-mining-demo-notes]] 的 `raw/alpha_researcher/lab/csi300` 即同一 lab 布局（859 只沪深300）；缓存策略见该页「raw/ 只读红线」。

## 相关页面
[[alpha-dataset]] · [[factor-expression-ops]] · [[alpha-mining-demo-notes]] · [[backtesting-model]] · [[vnpy-source]]
