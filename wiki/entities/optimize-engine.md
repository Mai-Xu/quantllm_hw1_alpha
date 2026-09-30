---
tags: [entity, optimize, backtesting, deap]
created: 2026-09-24
updated: 2026-09-24
sources: [raw/vnpy/vnpy/trader/optimize.py]
---

# 实体：optimize — 参数寻优（BF / GA）

`raw/vnpy/vnpy/trader/optimize.py`，回测参数优化入口；[[backtesting-engine]] 的 `run_bf_optimization` / `run_ga_optimization` 委托给它。

## OptimizationSetting（L26-80）
- `add_parameter(name, start, end=None, step=None)`：缺省 end/step = 固定参数
- `set_target(target_name)`：如 `sharpe_ratio` / `rgr_ratio`
- `generate_settings()`：`itertools.product` 笛卡尔展开

## 两种算法
| 函数 | 算法 | 要点 |
|---|---|---|
| `run_bf_optimization`（L99） | 穷举网格 | `ProcessPoolExecutor(spawn)` + tqdm，按 `key_func` 降序 |
| `run_ga_optimization`（L132） | DEAP 遗传 | `eaMuPlusLambda`+`selNSGA2`；变异=整体换一组随机参数；`Manager().dict()` 跨进程缓存 |

回调约定：`evaluate_func: Callable[[dict], dict]`，`key_func: Callable[[tuple], float]`。

## 坑
1. **import 副作用**：模块加载即 `creator.create("FitnessMax"...)`（L22-23）——重复 import/嵌套 spawn 需注意
2. Windows 必须 spawn（L114-116 已固定 `get_context("spawn")`），evaluate 闭包要可 pickle（回测里用 `wrap_evaluate` partial 冻结市场参数）
3. 与 [[factor-overfitting]] 的关系：网格/GA 本质是**多次尝试**，调参预算应计入试验台账；优先取参数平台而非峰值

## 相关页面
[[backtesting-engine]] · [[backtesting-model]] · [[factor-overfitting]] · [[vnpy-source]]
