# VOLPOS Round 02 反思

时间：2026-09-30 17:00–17:04（约 4 分钟，11 候选）
台账：volpos 29 / 80

## 结果排序（按 |valid RankIR|）

| 因子 | train | valid | 判定 |
|---|---|---|---|
| **rev4_turn_lowdist** | +0.437 | **+0.270** | 当前最优；−Δ4×turn×cs_rank(close/ts_min(low,20)) |
| **rev4_turn** | +0.399 | **+0.239** | 简形式最优；核心结构 |
| rev4_turn_amp_pos | +0.360 | +0.229 | 三件套（amp+pos）不如两件 |
| rev5_amp5_turn | +0.383 | +0.222 | |
| rev5_hivol_turn | +0.373 | +0.219 | |
| rev4_turn_pos60 | +0.333 | +0.218 | |
| rev5_turn_pos | +0.314 | +0.183 | 低位加权变体 |
| rev3/rev6_turn_pos | +0.27/+0.25 | +0.163/+0.157 | 窗口两侧下降 |

## 结构性发现（重要）

1. **核心结构是 rev4_turn = −Δ4 × cs_rank(turnover)**（valid 0.239）——
   位置/振幅/波动乘法器大多**无增量甚至负增量**：
   - ×(1−pos20) 低位权重：0.239 → 0.214（**变差**）
   - ×(1−pos60)：0.218（略差）
   - ×amp5×(1−pos20)：0.229（略差）
2. **例外：×cs_rank(close/ts_min(low,20))**（远离低点=高位权重）：0.239 → **0.270**（+0.031 > 0.02，可区分）
   ——与 round 01 的 rev5_highpos（valid 0.185）方向一致：**高位反转更强**
3. **窗口平台（带 pos 族）**：rev3 0.163 / rev4 0.214 / rev5 0.183 / rev6 0.157 —— rev4 是峰，
   但纯 rev4_turn 未扫平台，round 03 须补 rev3_turn/rev5_turn
4. **减法拆解**：turn_lowpos 单独 valid −0.028（无 alpha）→ 乘法结构正确
5. 数学上 close/ts_min(low,20) 与 1−pos20 的排序相关不完全一致（前者受绝对涨幅影响）

## Round 03 计划（10–12）

1. **rev4_turn 窗口平台**：rev3_turn / rev5_turn（纯两件套）
2. **高位加权符号确认**：rev4_turn × pos20（对称检验）；rev4_turn × cs_rank(close/ts_max(high,20))（贴近高点）
3. **lowdist 平台**：ts_min 窗 10 / 60
4. **降维**：cs_rank(close/ts_min(low,20)) 是否可换成 dist_low20 的 rank；cs_zscore 替代
5. 若 lowdist 平台不稳 → 简形式纪律取 **rev4_turn** 为方向主推收尾

## 台账与预算
volpos 29/80，round 03 ≈ 12 → 41，round 04 收尾用。决策看 train+valid，test/lockbox 仍隐藏。
