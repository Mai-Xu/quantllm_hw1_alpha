---
tags: [alpha, factor-mining, llm-driven, vnpy-alpha]
created: 2026-09-16
updated: 2026-09-19
sources: [raw/alpha_researcher/auto_researcher/mine.py, raw/vnpy/vnpy/alpha/dataset/template.py]
---

# alpha_mining_demo：LLM 驱动的自动化因子挖掘 DEMO 设计笔记

## 定位

参考 [[wiki/sources/alpha-researcher]]（vnag + OpenRouter 外接 LLM 的 agent 流水线），改为 **ZCode 会话本身担任挖掘大脑**：LLM 生成公式 → 本地脚本用 vnpy.alpha 评估 → LLM 读指标反思 → 迭代 ≤10 轮（早停：连续 2 轮最优 Rank-IR 提升 <5% 且无新方向）→ 落地 `runs/final/factors.json` + `report.md`。

## 架构

- `projects/alpha_mining_demo/eval_factors.py`：轮次评估。输入 candidates JSON → AlphaDataset（`raw/alpha_researcher/lab/csi300` 859 只沪深300 日线，路径经 `config.json` 的 `lab_path` 绝对引用）→ `prepare_data` 并行算因子 → 按日截面算 IC/Rank-IC/IR/Rank-IR/方向胜率 → 输出 metrics.json。
- `projects/alpha_mining_demo/final_report.py`：终局报告（唯一报告脚本）。对 runs/final/factors.json 的留存因子一次 `prepare_data`，每因子经 `analyze_factor` 一次分组产出两张中间表（日度截面 IC 序列 + 十分组日收益表），分段指标与四张图全部由这两张表派生；另有换手×成本估算与三因子 test 段多空对比图。
- 验证分段随方向演进（以 `config.json` 为准）：前三族 train 2008–2014 / valid 2015–2016 / test 2017–2020.08；**2026-09-18 跳空方向起升级**为 train 2008–2016 / valid 2017–2018 / test 2019–2020.08（挖掘期 `eval_test=false` 隐藏）/ lockbox 2020.09–2024（见"第四次实测"节）。
- 指标用 pandas 按日 groupby 相关实现，不依赖 alphalens；因子/标签计算全部走 vnpy.alpha 表达式引擎。
- label：`ts_delay(close,-3)/ts_delay(close,-1)-1`（T+1→T+3 收益）。

## 产物留存现状（2026-09-19 lint 核查）

本页各实测节记录的产物路径为**当时的工作区状态**，与当前留存不一致：

| 方向 | 文中路径 | 当前状态 |
|---|---|---|
| 量价共振（第一次） | `runs/round_00..07/`、`runs/final_vp/` | 均已不在（原始工作区亦删除） |
| 反转（第二次） | `runs/rev_round_01..07/`、`runs/rev_protocol.md`、`runs/final_rev/` | 工作区已删除；`final_rev/` 在 D 盘原工作区 git HEAD 中仍可恢复 |
| 动量（第三次） | `runs/mom_round_01..06/`、`runs/mom_protocol.md`、`runs/final_mom/` | ✅ 在 |
| 跳空（第四次，当前） | `runs/gap_round_01..04/`、`runs/gap_protocol.md`、`runs/final/` | ✅ 在 |

即：当前工作区只保留最近两方向（跳空 `final/` + 动量 `final_mom/`）的完整产物，
更早两方向只剩本页与 [[log]] 中的数字记录。数据源 `raw/alpha_researcher` 亦只在
D 盘原工作区（见 [[wiki/sources/alpha-researcher]]）。


## 关键决策

1. **raw/ 只读红线**：`AlphaLab.save_dataset` / filters pickle 会写入 lab 目录，改为缓存到本项目 `runs/cache/`。
2. 去掉 vnag/agent 层与论文解析阶段——方向由用户直接给，轮次反思笔记（notes.md）即 trace。
3. Windows 下 `prepare_data` 用 spawn 进程池，脚本必须 `if __name__ == "__main__"` 保护。
4. 依赖安装：`pip install "vnpy[alpha]" --index=https://pypi.vnpy.com`（带来 polars/alphalens-reloaded/torch 等）。

## 冒烟结果（round_00）

- `ts_corr(close, volume, 5)`：train RankIR -0.25，valid -0.28（量价相关为反向信号，样本外稳定）
- `-ts_delta(close,3)/close`：train RankIR +0.34，valid +0.21（短反转，方向延续）

## 完整实测（2026-09-16，量价共振方向）

- 7 轮 × 134 候选，早停于第 7 轮（增益 <1%）；核心发现：**A股短线量价同动是反向信号**（情绪过热），`VP_ANTI_RES5 = -corr(日收益, 日量变化, 5)` 三段 RankIR 0.35/0.40/0.28
- 产物：`runs/round_00..07/`（candidates+metrics+notes）、`runs/final/factors.json`（3 个留存因子）、`runs/final/report.md`（叙事报告）、`runs/final/performance_report.md`（final_report.py 生成的表+图）

## 过拟合核查（2026-09-16，问题驱动）

**问题**：留存公式是否太复杂 → 过拟合风险？

**核查 1：成分冗余度**。用 `final_report.compute_factors` 单独计算 combo 三个成分因子，按日截面 Spearman 相关取日均（3952 天）：

|  | A5 反共振 | B12 趋势反转 | D10 振幅量能 |
|---|---|---|---|
| A5 反共振 | 1.00 | 0.23 | 0.07 |
| B12 趋势反转 | 0.23 | 1.00 | 0.03 |
| D10 振幅量能 | 0.07 | 0.03 | 1.00 |

三项近正交 → 复杂度不是"信息冗余"问题。

**核查 2：样本外是否兑现**。valid 上的优势在 test 完全消失，且最简单的单因子全面占优：

| 因子 | train RankIR | valid RankIR | test RankIR | test 多空 Sharpe |
|---|---|---|---|---|
| VP_ANTI_RES5（单一项） | 0.35 | 0.40 | 0.28 | **1.81** |
| VP_COMBO（三项加权） | 0.39 | 0.51 | 0.28 | 1.42 |
| VP_COMBO_CONS | 0.39 | 0.50 | 0.28 | 1.44 |

对比图（`charts/comparison_ls_cum.png`）形态佐证：test 段 2017–2019 单因子（蓝）全程在组合上方，组合 2020 年后才追平。

**结论**：过拟合向量不是项数，而是**参数**——权重 0.5/0.7、窗口 5/12/3/10 由 134 个候选在 7 轮迭代中于同一段 valid（仅 488 天）上选出，属于选择偏差（与 report.md 局限性第 3 条自承一致）。combo 保留作教学对照组：**样本内最漂亮（valid 0.51）的因子，样本外不如最简因子**——主推结论用 primary。

**缓解方向**（供教学展开）：参数网格化后看平台（plateau）而非最优点；嵌套/滚动验证；限制每轮候选预算；多市场或更长 valid；正交成分等权组合代替调权重。

系统化的防治框架、量化锚点与样本消耗审计见 [[wiki/concepts/factor-overfitting]]。

## 第二次实测：反转方向（2026-09-16，7 轮 × 106 候选，早停）

- **跨会话衔接**：round 01–02 由上一中断会话完成（候选+指标已存在），本会话补写反思 notes
  后续跑 round 03–07；协议（预算/早停/纪律/台账）在 round_03 前事前声明于 `runs/rev_protocol.md`。
- 核心发现：**裸 4 日反转样本外几乎不赚钱（test 多空 Sharpe −0.87），限"趋势内回调"才有效**——
  `REV_TRIPLE = −Δ4 × cs_rank(turnover) × amp5 × (close>MA20)`，三段 RankIR 0.477/0.478/0.205，
  test 多空 Sharpe 1.57，17/18 年 RankIC 为正。留存 3 因子构成复杂度消融链
  （BARE 0.300→GATE 0.397→TRIPLE 0.478 valid 单调，test 同序）——与量价共振项目"最简者胜"
  相反，这次每个结构成分都有样本外增益。
- **过拟合防治首次全流程落地**：参数平台扫描（全部邻域 ±5% 内）、4 次跨轮复跑逐位一致、
  噪声锚点核验（t≈7.5 远超 √(2ln106)≈3.2）、简形式纪律（valid 最高 0.490 的平滑变体因
  +2.5%<噪声不采纳）、试验台账（本会话 106 + 前项目 ~940 次同段 valid）。
- **单轮耗时**（用户要求记录）：稳态 90–111s/轮（12–15 候选）；含 `ts_decay_linear` 候选时
  膨胀至 312s（rolling 回退实现单算子 ~192s，已弃用）；终局报告 59s；LLM 设计/反思与计算异步。
- 警示数据：2023–2024 RankIC 衰减至 ~0/−0.13（反转拥挤），regime 依赖强。
- 产物：`runs/rev_round_01..07/`、`runs/final/{factors.json,report.md,performance_report.md}`；
  量价共振产物归档至 `runs/final_vp/`。

## 第三次实测：动量/量价共振方向（2026-09-16，6 轮 × 84 候选，早停）

- **动量被证伪**：前两轮 24 个候选覆盖裸动量/52 周新高/放量确认/缩量/UVOL/MFI/OBV/
  水平共振/突破×量/趋势内追涨/vwap 趋势/量冲击/超短共振，valid 全负（−0.011~−0.372）。
  A 股 T+3 视界上量价共振只有反向语义；"动量"仅以趋势内回调形态存在（= REV_TRIPLE）。
- **转向产出新最优**：`PV_ANTI_TRIPLE = −corr(ret,dvol,5) × cs_rank(turnover) × amp5`，
  三段 RankIR 0.408/0.519/0.344，**test 多空 Sharpe 2.53、18/18 年 RankIC 正、2024 年 +0.103**
  ——三方向主推中样本外最稳（对比 REV_TRIPLE test 1.57 / 2024 −0.13）。
  活跃度乘法器从反转项目移植成功（+30% valid），VP 项目主推（裸 −corr5，0.401）被全面超越。
- **结构性发现**：趋势门控在共振族三次确认**有害**（与反转族相反）——反转换"线上回调"、
  反共振要"全场过热"，两族机制不同；换手>量第四次确认；相关型>计数型>分解型。
- 过拟合纪律同前：6 轮 84 候选台账（同段 valid 累计 ~1130 次）、参数死平台
  （amp 窗 5–20 valid 0.519–0.530）、5 次跨轮复跑逐位一致、噪声锚点 t≈8.1 ≫ 3.2、
  简形式纪律（valid 最高的 amp10 版因 +2.1%<噪声不采纳）。
- 单轮耗时 88–118s，6 轮合计 625s；终局报告 58s。
- 产物：`runs/mom_round_01..06/`、`runs/final/{factors.json,report.md,performance_report.md}`；
  归档链：`runs/final_vp/`（量价共振）→ `runs/final_rev/`（反转）→ `runs/final/`（本方向）。

## 第四次实测：跳空方向（2026-09-18，4 轮 × 56 候选，早停+预算上限同达）

用户方向"动量 × 开盘跳空"。**验证设计全套升级**（落实 [[wiki/concepts/factor-overfitting]]
2026-09-18 审计建议，首个实测）：弃用已被前三族消耗 ~1130 次的 2015–2016 valid，
分段后移为 train 2008–2016 / valid 2017–2018 / test 2019–2020.08（挖掘期间
`eval_test=false` 隐藏）/ **lockbox 2020.09–2024**（留存冻结后才由分年表观察）。
协议 `runs/gap_protocol.md` 事前声明（预算 80、噪声门槛 0.19、成本三档条款、复跑一致性）。

- **裸跳空动量证伪**（gap1/5/20 train 无信号，valid 正读数属选择诱饵形态）；
- **真发现是隔夜-日内分解**：`GAP_DIFF4 = Σ₄(隔夜收益 − 日内收益)`，高开低走型跑赢——
  把三项目"A 股短线反向"细化到**反转活在日内、隔夜豁免**。主推
  `GAP_DIFF4_TURN = diff4 × cs_rank(turnover)`，三段 0.372/0.292/0.200；
- 结构边界：**换手乘法器有效、振幅无效**（amp 窗 3–10 死平台 0.279–0.288）；
  与 PV_ANTI 族日均截面 Spearman 仅 0.32–0.46，但等权组合无增量（+0.013<0.02）
  → 定位"新采样 + 机制细化"而非替代；唯一正动量读数 g4_08（跳空不回补→弱延续，
  低于噪声门槛，仅作机制注脚）；
- 终局一次性确认（不回改留存）：test 存活（0.19–0.20），**lockbox 2023 归零、
  2024 转负（−0.04~−0.07）**——反转族跨族拥挤衰减（对照 PV_ANTI_TRIPLE 2024 +0.103）；
  成本三档排序不变，但 0.10% 档 test 净多空 bare 24.1% vs turn 7.1%
  （多空+扣费口径更支持 bare；主推按冻结纪律仍为 turn，分歧如实记录）；
- 耗时：4 轮 eval ~390s（122/105/93/70）+ 复跑 95s + 正交性 28s + 终局 59s×2；
- 工程坑复现：orthogonality.py 缺 `if __name__ == "__main__"` 保护，Windows spawn
  下卡死 16min（本页关键决策 3 的坑），加 main() 后 28s；
- 产物：`runs/gap_round_01..04/`、`runs/final/{retention.md,factors.json,report.md,
  performance_report.md,perf_detail.json,charts/}`；动量方向产物归档 `runs/final_mom/`。

## 终局报告路线取舍（2026-09-16）

曾尝试用 vnpy.alpha 内置的 `AlphaDataset.show_feature_performance`（[[raw/vnpy/vnpy/alpha/dataset/template.py]] 的 `get_clean_factor_and_forward_returns` + `create_full_tear_sheet`）出终局报告，**最终从 demo 代码中移除，只保留自写 `final_report.py`**。理由：

1. **交互式设计**：tear sheet 假设在 Jupyter/交互环境弹窗看图；headless 落盘要打补丁捕获图窗（GridFigure.close 会先关图窗，Agg 后端无法事后 savefig）。
2. **pandas 3.0 兼容**：alphalens 0.4.6 内部写死 `mean_information_coefficient(by_time="M")`，pandas 3.0 已更名 `"ME"`，不打补丁直接报错。
3. **产出不适合课程材料**：图命名 fig_01..04 无语义、控制台统计是一堵文字墙。
4. **教学上自写版更优**：每个数字都有可见的 10 行 pandas 代码（日度截面相关 → IC；qcut → 分组；Q10−Q1 → 多空），学生先算懂原理，再知道框架有一键版。

若将来要用官方版，两个兼容补丁存档（适用于 alphalens-reloaded 0.4.6 + pandas 3.x）：

```python
# 补丁1：pandas 3.0 月度频率 "M" -> "ME"
from alphalens import performance, tears
_orig = performance.mean_information_coefficient
def _compat(fd, group_adjust=False, by_group=False, by_time=None):
    if by_time == "M":
        by_time = "ME"
    return _orig(fd, group_adjust, by_group, by_time)
performance.mean_information_coefficient = _compat
tears.perf.mean_information_coefficient = _compat

# 补丁2：GridFigure.close 前先 savefig（Agg 后端下图窗关闭即丢失）
FIG_DIR = Path("out")
_orig_close = tears.GridFigure.close
def _close_compat(self):
    if self.fig is not None:
        n = len(list(FIG_DIR.glob("fig_*.png"))) + 1
        self.fig.savefig(FIG_DIR / f"fig_{n:02d}.png", dpi=120, bbox_inches="tight")
    _orig_close(self)
tears.GridFigure.close = _close_compat
```

## 后续

- ~~待用户给挖掘方向后启动正式 10 轮迭代~~ 已完成四方向：量价共振（7 轮）、反转（7 轮）、
  动量/共振（6 轮，动量证伪）、跳空（4 轮，裸跳空动量证伪 → 隔夜-日内分解），笔记见上各节。
- 四方向综合：A 股 T+3 反向仍是唯一存活方向，但反转信息**集中在日内成分**（隔夜豁免）；
  通用结构 = 换手乘法器 + 4–5 日窗（振幅乘法器仅共振/反转族有效，不跨族）；跳空族与
  PV 族中等相关（0.32–0.46）且组合无增量；**反转族 2023–2024 跨族衰减转负**（REV 与 GAP
  同衰，PV_ANTI_TRIPLE 独存）——实盘化前必须做近三年滚动 RankIC 监控。
  可选增强：行业/市值中性化、扣费后组合回测、point-in-time 池与涨跌停可交易性核查、
  ts_decay_linear 算子性能优化。

## 相关页面
[[wiki/concepts/factor-overfitting]] · [[wiki/concepts/factor-expression-ops]] · [[wiki/concepts/ai-harness]] · [[wiki/sources/alpha-researcher]] · [[wiki/sources/pku-veighna-course]]

## 第五次实测：波动状态与价格位置（VOLPOS，2026-09-30）

延续动量/反转思路，从「涨跌方向」转向「价格位置 + 波动状态」。协议 runs/volpos_protocol.md，
4 轮 × 51 候选（r1 18 / r2 11 / r3 12 / r4 10），同 gap 分段，test 挖掘期隐藏。

### 结论速览
- **裸位置/裸波动无 alpha**（|valid RankIR|<0.12）——只能做调制不能做信号
- **真发现：高位加权的换手反转** REV4_TURN_HIGHPOS = −Δ₄×cs_rank(turnover)×pos20
  （pos20=close 在 20 日高低区间的位置）：train +0.486 / valid +0.284 / test +0.154
- **位置符号**：高位加权 0.284 ≫ 低位加权 0.214；「远离低点」比「贴近高点」更本质
- **简形式** REV4_TURN = −Δ₄×turn：valid 0.239；与 REV_TRIPLE 最近亲（仅 amp5→pos20）
- **四件套** ×pos20×amp20：valid 0.309 最高，简形式纪律下作观察项
- **复跑** highpos 与 _r2 逐位一致；rev3/4/5 与 pos10/20/60 均为可接受平台

### 衰减警示（与 REV/GAP 同模式，第三次确认）
test RankIR 0.284→0.154（低于 0.19）；分年 16/18 为正但 **2023 −0.004、2024 −0.102**。
多头换手 67.7%>60% 成本门槛，扣费后全样本多空年化 73%→40%。

### 产物
runs/volpos_round_01..04/、runs/final/{factors.json,retention.md,performance_report.md,report.md,charts/}
（gap 产物已归档 runs/final_gap/）

### 五方向全景
VP 0.51/0.28 → REV 0.48/0.21 → MOM 证伪 → GAP 0.29/0.20 → **VOLPOS 0.28/0.15**。
A 股 T+3 反转的每个调制维度都在样本内成立、样本外衰减；主推记录为结构知识，实盘化需滚动监控。
