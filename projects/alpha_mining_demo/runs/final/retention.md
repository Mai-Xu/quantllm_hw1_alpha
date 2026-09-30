# VOLPOS 留存决策（冻结于 final_report 之前，2026-09-30）

三票制：① |valid RankIR|>0.19（噪声锚点）② 经济机制 ③ 最简形式（统计不可区分时取简）
符号：train/valid 一致为正（值越大 → 预期反弹越强），保持原符号。

## 留存

| 角色 | 名称 | 表达式 | train | valid | 三票 |
|---|---|---|---|---|---|
| **主推** | REV4_TURN_HIGHPOS | −Δ₄×cs_rank(turnover)×pos20 | +0.486 | **+0.284** | 3/3 |
| 简形式对照 | REV4_TURN | −Δ₄×cs_rank(turnover) | +0.399 | +0.239 | 3/3 |
| 增强观察 | REV4_TURN_POS20_AMP | 上式×cs_rank(amp5→amp20) | +0.491 | +0.309 | 2/3（复杂度扣一票） |

pos20 = (close − ts_min(close,20)) / (ts_max(close,20) − ts_min(close,20))

## 投票理由

**REV4_TURN_HIGHPOS（主推）**
1. |valid 0.284| > 0.19 ✓（绝对优势）
2. 机制：高位（远离近期低点）的高换手下跌股反弹更强——注意力/彩票型反转被位置放大；
   与「T+3 反转存活」「换手乘法器有效」兼容 ✓
3. 简形式：3 项；pos 窗口平台 10/20/60 = 0.280/0.284/0.300（平台非峰）；
   rev 窗口 3/4/5 = 0.228/0.284/0.229（rev4 峰）✓

**REV4_TURN（简形式）**：两件套核心，valid 0.239 > 0.19；作对照与降级备份。

**REV4_TURN_POS20_AMP（观察）**：valid 0.309 最高，但 4 项；vs highpos 差 0.025>0.02 可区分，
简形式纪律下不主推。amp 调制与 REV_TRIPLE 同源，若终局成本可行可升主推。

## 平台与复跑证据

- rev 窗（带 highpos）：rev3 0.228 / rev4 0.284 / rev5 0.229
- pos 窗（带 rev4_turn）：10 0.280 / 20 0.284 / 60 0.300；lowdist10/20/60 = 0.265/0.270/0.284（同向）
- 复跑：rev4_turn_highpos 与 _r2 **逐位一致**（train 0.486 / valid 0.284）✓
- 减法拆解：rev4_highpos（无 turn）0.248；turn_highpos（无 rev）−0.087 → 三因子乘法结构成立

## 与既有主推的关系（截面相关待终局后补算，此处先声明结构关系）

- PV_ANTI_TRIPLE = −corr×turn×amp5：同为「反转×换手」族，位置项不同 → 预期中等相关
- GAP_DIFF4_TURN = 隔夜−日内分解×turn：机制不同（隔夜 vs 日内反转）→ 预期较低相关
- REV_TRIPLE = −Δ4×turn×amp5：**最近亲**，仅 amp5 → pos20 之差；同源信号必须声明

## 成本与可交易性保留意见（终局报告验证）

- 多头为「高换手下跌股」，换手可能 >60% → 三档成本检验见 performance_report
- 高位反转天然暴露于涨跌停/停牌极值，一字板无法成交

## 台账

volpos 51 / 80（r1 18 + r2 11 + r3 12 + r4 10；r3 首跑 cs_zscore 崩溃不计）
valid 消耗：gap 56 + volpos 51 = 107（同段累计）
