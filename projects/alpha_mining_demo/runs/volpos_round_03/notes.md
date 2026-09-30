# VOLPOS Round 03 反思

时间：2026-09-30 17:11（约 3 分钟，12 候选；首跑因 cs_zscore 不存在崩溃一次，不计台账）
台账：volpos 41 / 80

## 结果排序（按 |valid RankIR|）

| 因子 | train | valid | 备注 |
|---|---|---|---|
| **rev4_turn_highpos** | +0.486 | **+0.284** | −Δ4×turn×pos20，高位加权 |
| **rev4_turn_lowdist60** | +0.452 | **+0.284** | −Δ4×turn×cs_rank(close/ts_min(low,60)) |
| rev4_turn_lowdist20 | +0.437 | +0.270 | 与 rk20/half 完全同值 |
| rev4_turn_lowdist10 | +0.410 | +0.265 | |
| rev4_turn_lowdist_z | +0.402 | +0.239 | cs_scale 变换 |
| rev5_turn | +0.374 | +0.205 | 纯两件套平台 |
| rev3_turn | +0.334 | +0.198 | 纯两件套平台 |
| rev4_amp5 | +0.396 | +0.226 | |

## 结构性发现

1. **纯 rev4_turn 窗口平台**：rev3 0.198 / rev4 0.239 / rev5 0.205 —— rev4 为峰，邻域 0.20–0.24
   是可接受平台（非刀锋峰）；沿用 rev4
2. **位置符号确认：高位加权 > 低位加权**（与 round 01 一致）：
   - ×pos20（高位）0.284 ≫ ×(1−pos20)（低位）0.214
   - ×cs_rank(close/ts_min(low,60)) 0.284 同级
   - ×cs_rank(close/ts_max(high,20))（贴近高点）0.224 较弱——「远离低点」比「贴近高点」更本质
3. **lowdist 窗口平台**：10→0.265 / 20→0.270 / 60→0.284，单调缓升；60 最优但三档均 >0.26
   （平台可接受），考虑简形式取 pos20（highpos 与 lowdist60 同值 0.284，pos20 表达式更简）
4. **数学校验**：rk20 ≡ rank(close/ts_min)（减 1 不改序）；half 变换 0.5+0.5·rank 不改序 → 同 RankIR ✓
5. **经济机制**：高位（远离近期低点）的高换手下跌股反弹更强——注意力/彩票型反转在高位被放大；
   与「A 股 T+3 反转存活」+「换手乘法器有效」两结论兼容

## Round 04 计划（收尾，~10）

1. highpos 窗口平台：pos10 / pos60（对照 pos20）
2. 简形式对照：rev4_turn_highpos 的两两拆解已在 r2 完成
3. 复跑 rev4_turn_highpos（一致性验证）
4. 留存决策：候选主推 rev4_turn_highpos（或 rev4_turn_lowdist60 同值），观察项 rev4_turn
5. 冻结留存 → final_report.py

## 台账
volpos 41/80，round 04 ≈ 10 → 51。决策只用 train+valid。
