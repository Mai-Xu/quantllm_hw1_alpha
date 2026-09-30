---
tags: [concept, alpha, factor, operators, polars]
created: 2026-09-19
updated: 2026-09-24
sources: [raw/pku-veighna-course.pdf, raw/vnpy/vnpy/alpha/dataset]
---

# 概念：表达式因子与 ts/cs 算子

来源：[[wiki/sources/pku-veighna-course]] p.15–17。这是 Agent 能「生成因子公式」的表达层基础，也是 [[alpha-mining-demo-notes]] 中 vnpy.alpha 计算引擎的接口面。

## 截面选股策略的演进（p.15）

| 阶段 | 方法 | 特征 |
|---|---|---|
| 人工主观选股 | 基本面、经验 | 不可规模化 |
| 单因子选股 | PE、动量、反转 | 可回测，容量有限 |
| 多因子打分 | 标准化、加权合成 | 需要合成规则 |
| OLS 线性回归 | 线性组合、因子权重 | 权重由回归定 |
| ML 机器学习 | 非线性、模型融合 | 表达力最强、最易过拟合 |

课件把这条演进线放在「AI Agent 因子挖掘」之前，意在说明：**Agent 挖掘的主战场仍是「单因子 → 多因子打分」这一层的表达式组合**，而非直接上端到端 ML——与本仓库四方向实测「相关型表达式 + 等权组合」的结论一致（见 [[alpha-mining-demo-notes]]）。

## 两种表达式写法（p.16）

同一因子 `kmid = (close - open) / open`：

1. **纯数学表达式**——写起来最简单，性能一般  
   `(close – open) / open`
2. **Polars 表达式**——Polars 内部执行，性能极高  
   `(pl.col("close") – pl.col("open")) / pl.col("open")`

vnpy.alpha 的表达式引擎走的是可编译/可向量化的路线（ts_/cs_ 算子组合），兼顾「LLM 好写」与「计算快」。`eval_factors.py` 里候选公式的字符串即这类表达式。

## 两类算子（p.17）

| 类别 | 语义 | 示例 |
|---|---|---|
| **时序算子 ts_** | 同一合约代码下的不同时间戳 | `ts_delay` 取固定时间之前的值；`ts_mean` 滚动窗口均值 |
| **截面算子 cs_** | 同一时间戳下的不同合约代码 | `cs_rank` 截面排序返回序号；`cs_mean` 截面平均 |

本仓库实测中常用的完整清单（超出课件，来自 vnpy.alpha 与四方向挖掘）：
- 时序：`ts_delay`、`ts_delta`、`ts_mean`、`ts_std`、`ts_corr`、`ts_rank`、`ts_sum`、`ts_max`/`ts_min`、`ts_slope`/`ts_rsqaure`/`ts_resi`（OLS 闭式）等 22 个
- 截面：`cs_rank`、`cs_zscore`、`cs_mean`、`cs_std`、`cs_sum`、`cs_scale` 等
- 技术：`ta_rsi`、`ta_atr`；数学：`quesval`/`quesval2` 条件分支、`pow1`/`pow2`（负底数）
- 慎用：`ts_decay_linear`（单算子耗时可到 ~192s/候选，见 [[wiki/code/alpha-mining-demo-notes]] 耗时台账）

实现细节与 `register_functions` 扩展点见 [[alpha-dataset]]（求值=eval、spawn 子进程需顶层注册）。

## 与 Agent 因子挖掘的关系

课件 p.18 的闭环「给出挖掘方向 → 生成因子公式 → 评估因子绩效 → 判断是否继续」中，**「生成因子公式」一步完全依赖本页的表达式词汇表**：

- LLM 只在 ts_/cs_ 算子代数里组合，不会写出不可计算的伪代码
- 评估侧（[[alpha-mining-demo-notes]] 的 `eval_factors.py`）用 AlphaDataset + `prepare_data` 批量求值
- 纪律侧（[[factor-overfitting]]）限制的是「在这套表达式上搜索多少候选」——表达式越丰富，候选预算越要收紧

**直觉**：表达式算子是「因子的汇编语言」；Agent 因子挖掘是在这门汇编上做程序搜索，过拟合防治则是对搜索次数与验证样本的记账。

## 相关页面
[[wiki/sources/pku-veighna-course]] · [[alpha-dataset]] · [[alpha-lab]] · [[alpha-mining-demo-notes]] · [[factor-overfitting]] · [[ai-harness]]
