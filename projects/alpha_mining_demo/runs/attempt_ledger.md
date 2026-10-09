# 因子挖掘试验台账（全部尝试，不只报最优项）

记录本项目所有方向、所有轮次的候选数量与产物留存情况。
评审要求「保留全部尝试，不只报最优项」，本台账即该要求的落实——**含证伪方向与全部支线**。

## 总览

| 方向 | 轮次 | 候选数 | 主推结果 | test RankIR | 产物留存 |
|---|---|---|---|---|---|
| VP 量价共振 | 7 | ~134 | PV_ANTI_TRIPLE | 0.28 | ❌ 轮次产物已删（仅 log 记录） |
| REV 反转 | 7 | 106 | REV_TRIPLE | 0.205 | ❌ 轮次产物已删（final_rev 曾可恢复） |
| MOM 动量 | 6 | 84 | **证伪** → 转向共振反向族 | — | ✅ `mom_round_01..06/` |
| GAP 跳空 | 4 | 56 | GAP_DIFF4_TURN | 0.200 | ✅ `gap_round_01..04/` |
| VOLPOS 波动位置 | 4 | 51 | REV4_TURN_HIGHPOS | 0.154 | ✅ `volpos_round_01..04/` |
| **合计** | **28** | **~431** | — | — | — |

## 逐方向明细

### VP 量价共振（2026-09-16，7 轮 ~134 候选）
- 结论：**量价同动为反向信号**。最优单因子 `-corr(ret,dvol,5)`（train/valid/test RankIR 0.35/0.40/0.28）；
  组合 `A5+0.5·B12+0.7·D10`（0.39/0.51/0.28）样本外被单因子追平 → **过拟合教科书案例**（见 `wiki/concepts/factor-overfitting`）
- 第 6–7 轮增益 <1.2% 触发早停
- 产物：`runs/final_vp/` 与 `round_00..07/` 均已不在仓库中

### REV 反转（2026-09-16，7 轮 106 候选）
- 结论：裸 4 日反转 test 多空 Sharpe −0.87；「趋势内回调」结构才有效 →
  `REV_TRIPLE = −Δ4×cs_rank(turnover)×amp5×(close>MA20)`，三段 0.477/0.478/**0.205**
- 协议事前声明：`runs/rev_protocol.md`（**该文件当前不在仓库中**）
- 警示：2023–2024 RankIC 衰减至 ~0/−0.13

### MOM 动量（2026-09-16，6 轮 84 候选）
- **证伪**：前两轮 24 个候选（裸动量/52周新高/放量确认/缩量/UVOL/MFI/OBV/水平共振/突破×量/
  趋势内追涨/vwap 趋势/量冲击/超短共振）valid **全负**（−0.011 ~ −0.372）
- 转向共振反向族后产出新最优 `PV_ANTI_TRIPLE = −corr(ret,dvol,5)×cs_rank(turnover)×amp5`
  （0.408/**0.519**/0.344，test 多空 Sharpe 2.53）
- 协议：`runs/mom_protocol.md`（✅ 在）

### GAP 跳空（2026-09-18，4 轮 56 候选，预算 80）
- **裸跳空动量证伪**（train 无信号）；真发现 = **隔夜-日内分解**：
  `GAP_DIFF4 = Σ₄(隔夜收益 − 日内收益)`，train/valid/test 0.379/0.276/0.198
- 唯一正动量读数 `g4_08`（train −0.152/valid −0.119）低于门槛 → 仅作机制注脚
- 证伪支线：缩量跳空延续、隔夜收益占比（反号）、趋势门控（有害）、vwap 族（三次皆弱）、
  1 日窗（valid 死亡）、隔夜波动/绝对跳空（双段负 = 彩票型，方向兑现）
- 协议：`runs/gap_protocol.md`（✅ 在）

### VOLPOS 波动位置（2026-09-30，4 轮 51 候选，预算 80）
- 逐轮 18 / 11 / 12 / 10；核心结论见 `report.html`、`report.md`
- **证伪支线**：裸位置（pos20/pos60/dist_high/dist_low）、裸波动（vol20）、裸振幅（amp1/amp5）、
  区间宽度、位置×换手（无反转项）——|valid RankIR| 均 <0.12，**均无独立 alpha**
- 减法的三个反例：`rev4_highpos`（无换手）0.248、`turn_highpos`（无反转）−0.087、
  `rev4_turn_lowdist_z`（cs_scale 变换）0.239
- 未采纳的候选（简形式纪律）：四件套 `rev4_turn_pos20_amp` valid 0.309（复杂度扣分）、
  `rev4_turn_lowdist60` 0.284（与主推同值，取更简表达）
- 协议：`runs/volpos_protocol.md`（✅ 在）

## 试次消耗与多重检验

| 段 | 累计次数的使用情况 |
|---|---|
| 旧 valid（2015–2016） | 被 VP/REV/MOM 三族消耗 ~1130 次后**弃用** |
| 新 valid（2017–2018） | GAP 56 次 + VOLPOS 51 次 = **107 次** |
| test（2019–2020.08） | 挖掘期隐藏，各方向终局各观察 1 次 |
| lockbox（2020.09–） | 留存冻结后仅展示 |

噪声锚点：N=80 → √(2·ln 80) ≈ 2.96；有效样本 ≈244 → |RankIR| 门槛 ≈ 0.19。

## 产物索引

| 路径 | 内容 | 在库 |
|---|---|---|
| `runs/mom_round_01..06/` | candidates + metrics + notes | ✅ |
| `runs/mom_protocol.md` | 动量方向协议 | ✅ |
| `runs/gap_round_01..04/` | 跳空轮次（含 orthogonality.py） | ✅ |
| `runs/gap_protocol.md` | 跳空协议 | ✅ |
| `runs/volpos_round_01..04/` | 波动位置轮次 | ✅ |
| `runs/volpos_protocol.md` | 波动位置协议 | ✅ |
| `runs/final_mom/`、`runs/final_gap/` | 历史方向终局归档 | ✅ |
| `runs/final/` | 当前方向（VOLPOS）终局 + 摩擦报告 + 冻结清单 | ✅ |
| VP / REV 轮次产物 | — | ❌ 已丢失，仅存 log 与笔记记录 |
