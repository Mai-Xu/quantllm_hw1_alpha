---
tags: [source, alpha, factor-mining, llm-driven]
created: 2026-09-19
updated: 2026-09-19
sources: [raw/alpha_researcher/auto_researcher/mine.py]
---

# 来源：alpha_researcher（vnag 自动因子挖掘项目）

> **存根页**（2026-09-19 lint 时补建）：本来源从未正式 ingest，一直只作为
> [[wiki/code/alpha-mining-demo-notes]] 的参考资料被引用。原始资料不在当前
> 工作区副本中（见下），本文仅记录已确证的事实，待完整 ingest 后扩充。

## 已确证事实

- 是一个外部开源/参考项目：**vnag + OpenRouter 外接 LLM 的 agent 流水线**，
  自动解析论文 → 生成因子 → 评估迭代（`raw/alpha_researcher/auto_researcher/mine.py`）
- `alpha_mining_demo` 的定位即"参考它的流水线，改由 ZCode 会话本身担任挖掘大脑"，
  并改进了其"全区间算 IC、无 train/valid 划分"的验证缺陷
- 其附属数据 `raw/alpha_researcher/lab/csi300`（859 只沪深 300 日线，含
  open/high/low/close/volume/turnover/vwap 字段）是 `alpha_mining_demo` 的数据源，
  `config.json` 的 `lab_path` 以绝对路径引用

## 位置注意（当前工作区副本缺口）

- 当前工作区（`C:\Users\admin\Desktop\pku_demo`）是原始工作区（`D:\pku_demo`，
  git 仓库）的副本，**raw/ 只拷贝了 vnpy 三仓库**；`raw/alpha_researcher`
  与 `raw/assets` 仅存在于 D 盘原工作区
- 影响：在本副本上运行 `eval_factors.py` 依赖 D 盘路径可访问（`lab_path` 为绝对路径，
  恰好仍指向 D 盘原位置）；本页 sources 路径亦只在 D 盘成立

## 相关页面
[[wiki/code/alpha-mining-demo-notes]] · [[wiki/concepts/factor-overfitting]]
