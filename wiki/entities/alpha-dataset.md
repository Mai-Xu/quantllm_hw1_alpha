---
tags: [entity, alpha, dataset, expression, polars]
created: 2026-09-24
updated: 2026-09-24
sources: [raw/vnpy/vnpy/alpha/dataset, raw/vnpy/vnpy/alpha/model]
---

# 实体：AlphaDataset 与表达式因子引擎

`raw/vnpy/vnpy/alpha/dataset/`——Agent 因子挖掘的**表达层与评估底座**。列约定：`[0]=datetime, [1]=vt_symbol, [2:-1]=特征, [-1]=label`。

## AlphaDataset 数据流（`dataset/template.py`）

```
df (datetime, vt_symbol, OHLCV/vwap...)
 ├─ add_feature(name, expression|result)   # str / pl.Expr / 预计算 DF
 ├─ set_label(expression)                  # 可含负向 shift=未来收益
 ├─ add_processor("infer"|"learn", fn)
 ▼ prepare_data(filters, max_workers)      # L90-157
 │  多进程 spawn Pool：每条表达式一任务 calculate_feature
 │  filters=成分存续区间（防幸存者偏差）
 ▼ process_data()                          # L159-172
 │  infer 队列 → infer_df；learn 队列 → learn_df（可 append 链式）
 ▼ fetch_raw/infer/learn(Segment)          # TRAIN/VALID/TEST 切片
```

## 表达式引擎（`dataset/utility.py`）—— Agent 关键接口

- **求值 = Python `eval`**（`calculate_by_expression` L203-255）：局部 import 全部算子 → merge `EXPRESSION_FUNCTIONS` → 列名绑定 `DataProxy` → `eval(expr, {}, d)`。官方声明仅限本地受信用户（`docs/info/alpha.md`）。
- **`register_functions`**（L10-16，4.4.0）：注册自定义算子进 `EXPRESSION_FUNCTIONS`。**spawn 兼容陷阱**：子进程重新 import，注册必须在可 import 的模块顶层完成，否则并行求值 NameError。
- **双通道**：`str` 走 DataProxy+eval；`pl.Expr` 走 `calculate_by_polars`（L258-264）原生 polars。
- **DataProxy**（L19-200）：包装 `pl.DataFrame[datetime,vt_symbol,data]`，重载算术/比较（比较→Int32）。

### 算子清单
| 族 | 语义 | 函数 |
|---|---|---|
| **ts_*** `over("vt_symbol")` | 时序 | delay/min/max/argmax/argmin/rank/sum/mean/std/slope/quantile/rsquare/resi/corr/less/greater/log/abs/delta/cov/decay_linear/product（22） |
| **cs_*** `over("datetime")` | 截面 | rank/mean/std/sum/scale |
| **ta_*** | 技术 | ta_rsi/ta_atr（pandas↔talib↔polars 桥） |
| math | 标量 | less/greater/log/abs/sign/quesval/quesval2/pow1/pow2 |

性能注意：slope/rsquare/resi 已 OLS 闭式优化；argmax/rank/quantile/decay_linear 等仍走 `rolling_map` UDF，大窗口是热点。

## processor（`dataset/processor.py`）
作用列默认 `df.columns[2:-1]`：
- 旧：`process_drop_na` / `process_fill_na` / `process_cs_norm` / `process_cs_rank_norm` / `process_robust_zscore_norm`
- **4.4.0 新增**：`process_replace_inf` / `process_ts_norm`（可指定拟合区间）/ `process_drop_feature` / `process_cs_fill_na`

## 模型接口（`alpha/model/`）
`AlphaModel` 三方法：`fit(dataset)` / `predict(dataset, segment)` / `detail()`。
- `LassoModel`：TRAIN+VALID 合并拟合，系数=重要性
- `LgbModel`：mse + early_stopping，split/gain 重要性
- `MlpModel`：PyTorch MLP（Dropout+BN+LeakyReLU），扰动法重要性

## 内置因子库
- `datasets/alpha_101.py`：WorldQuant 101（表达式字符串定义，可作 LLM few-shot 语料）
- `datasets/alpha_158.py`：Qlib 158

## 与 [[alpha-mining-demo-notes]] 的对接
`eval_factors.py` 即 `add_feature(str_expr)` + `prepare_data` + 自算 IC/Rank-IR；label 用 `ts_delay(close,-3)/ts_delay(close,-1)-1`。[[factor-expression-ops]] 是本页算子的课程视角概述。

## 相关页面
[[alpha-lab]] · [[factor-expression-ops]] · [[factor-overfitting]] · [[alpha-mining-demo-notes]] · [[vnpy-source]]
