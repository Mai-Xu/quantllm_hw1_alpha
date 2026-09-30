# 波动状态与价格位置方向因子挖掘报告（VOLPOS，2026-09-30）

协议：`runs/volpos_protocol.md`（事前声明）。4 轮 × 51 候选（预算 80），按用户约束收尾。
延续四方向（VP/REV/MOM/GAP）动量-反转思路，但把「涨跌方向」转向「价格在自身轨迹中的位置 + 波动状态」。

## 验证设计

与 GAP 族相同（train 2008–2016 / valid 2017–2018 / test 2019–2020.08 隐藏 / lockbox 2020.09–2024）。
台账：volpos 51 次；同段 valid 累计消耗 gap 56 + volpos 51 = 107。

## 核心发现

1. **裸位置/裸波动无独立 alpha**。pos20/pos60/vol20/amp1/amp5/区间宽度的 |valid RankIR| 均 <0.12
   ——位置与波动只能做**调制**，不能做信号（与「裸动量证伪」同构）。

2. **真发现：高位加权的换手反转**（全项目第 5 个有效结构）。
   `REV4_TURN_HIGHPOS = −Δ₄ × cs_rank(turnover) × pos20`
   其中 pos20 = (close − ts_min(close,20)) / (ts_max(close,20) − ts_min(close,20))。
   train +0.486 / valid +0.284 / test +0.154；test 多空 Sharpe 0.91。
   **高位（远离近期低点）的高换手下跌股反弹更强**——注意力/彩票型反转被位置放大。

3. **位置符号确认：高位加权 > 低位加权**（本方向最重要的结构性结论）：
   - ×pos20（高位）：valid 0.284
   - ×(1−pos20)（低位）：valid 0.214（更差，不如不加）
   - ×cs_rank(close/ts_min(low,60))（远离低点）：0.284 同级
   - ×cs_rank(close/ts_max(high,20))（贴近高点）：0.224 较弱
   「远离低点」比「贴近高点」更本质；round 01 的 rev5_highpos（0.185）已预示此符号。

4. **窗口平台**（均可接受，非刀锋峰）：
   - rev 窗（带 highpos）：3→0.228 / 4→0.284 / 5→0.229
   - pos 窗（带 rev4_turn）：10→0.280 / 20→0.284 / 60→0.300
   - pure rev×turn：3→0.198 / 4→0.239 / 5→0.205

5. **简形式对照**：REV4_TURN = −Δ₄×cs_rank(turnover) 两件套即 valid 0.239，
   是本方向的「核心结构」；位置项提供 +0.045 增量。与 REV_TRIPLE（−Δ₄×turn×amp5）
   是最近亲——仅 amp5 → pos20 之差，**同源信号，合并前必须做正交性核算**。

6. **四件套增强**：REV4_TURN_POS20_AMP（再乘 amp20）valid 0.309 为全方向最高，
   但 4 项复杂度在简形式纪律下降级为观察项（与 highpos 差 0.025>0.02，可区分但不主推）。

## 终局确认（一次性观察，不回改留存）

| 因子 | train | valid | test | test LS Sharpe |
|---|---|---|---|---|
| REV4_TURN_HIGHPOS（主推） | +0.486 | +0.284 | +0.154 | 0.91 |
| REV4_TURN（简形式） | +0.399 | +0.239 | +0.154* | 0.87 |
| REV4_TURN_POS20_AMP（观察） | +0.491 | +0.309 | +0.09* | 0.65 |

（*见 performance_report.md 表格）

- **test 存活但衰减**：RankIR 0.284 → 0.154，低于 0.19 噪声门槛——与 GAP/REV 族的
  「valid 好 test 衰减」模式一致
- **分年 RankIC：16/18 年为正，但 2023 转负（−0.004）、2024 显著为负（−0.102）**
  ——反转族跨族拥挤衰减的第三次确认（REV 2023–24 转负、GAP 2023 归零 2024 转负、本族 2024 大负）
- **成本**：多头组日均换手 67.7% > 60% 门槛；按单边 0.1% 年化拖累 ~33%，
  扣费后全样本多空年化 +73% → +40%；**扣费排序下主推仍成立但优势收窄**
- 分组单调性 Q 序 Spearman = +1.00（完美单调）

## 全项目五方向位置

| 方向 | 主推 | valid | test | 状态 |
|---|---|---|---|---|
| VP 量价共振 | PV_ANTI_TRIPLE | 0.51 | 0.28 | 跨族衰减中最稳 |
| REV 反转 | REV_TRIPLE | 0.478 | 0.205 | 2023–24 转负 |
| MOM 动量 | （证伪）→ PV_ANTI 族 | — | — | 裸动量负结果 |
| GAP 跳空 | GAP_DIFF4_TURN | 0.292 | 0.200 | 2023 归零 2024 转负 |
| **VOLPOS 波动位置** | **REV4_TURN_HIGHPOS** | **0.284** | **0.154** | **2024 大负，衰减最重** |

结论：**A 股 T+3 反转的又一个调制维度（位置）被证实，但没有逃过反转族的拥挤衰减**。
位置加权在样本内（train/valid）显著提升排序能力，样本外（test/lockbox）增益消失甚至反噬。
主推降级为「样本内有效结构记录」，实盘化前必须做近三年滚动 RankIC 监控 + 成本硬门槛。

## 产物

- `runs/volpos_protocol.md` 协议
- `runs/volpos_round_01..04/` 轮次（candidates/metrics/notes）
- `runs/final/{factors.json,retention.md,performance_report.md,perf_detail.json,charts/}`
- 耗时：r1 8.5min(18) / r2 4min(11) / r3 3min(12) / r4 3min(10) / final_report 3min
