---
tags: [code, ctp, demo, order, open-close]
created: 2026-09-28
updated: 2026-09-28
sources: [projects/ctp_open_close_demo/demo.py]
---

# Code 笔记：ctp_open_close_demo（超价开 + 超价平各一次）

`projects/ctp_open_close_demo/demo.py`：在 [[ctp-breakout-demo-notes]] 基础上补上平仓腿，验证**开仓→平仓完整闭环**。**SimNow 实测成交**（2026-09-28 10:33，au2612 买开 1 手 + 卖平今 1 手）。

## 策略逻辑（超价 = 吃穿盘口，保证成交）

1. 开仓：`买一/卖一` 就绪后，**超价买开** = 卖一 + 5 跳（`AGGRESS_TICKS × PRICE_TICK`）
2. 平仓：开仓成交回报后，**超价卖平** = 买一 − 5 跳
3. 状态机：`order_ref==0` 时发开仓 → `open_filled` 后发平仓（`close_sent` 防重复）

## 关键实现点

- **上期所今仓必须 `CombOffsetFlag='3'`（CLOSETODAY）**，不能用 `'1'`（CLOSE，那是平昨）。成交回报 `Offset=3` 验证通过（见 [[offset-conversion]]）
- 委托回报是**全账户流**：用 `FrontID + SessionID` 过滤（`is_mine`）；成交回报没有 FrontID，只能按 OrderRef 与本会话 `order_ref` 范围过滤——多程序并行时仍可能看到别人的 TradeID
- 开仓成交 → `ready_hook` 立即用当前盘口补平仓价；若盘口未就绪则等下一个 tick

## 实测结果（2026-09-28 10:33，au2612）

| 腿 | 委托价 | 成交价 | 说明 |
|---|---|---|---|
| 超价买开 1 手 | 913.94 / 914.08 | **913.86 / 913.98** | 限价更优，实际成交更优（价格改善） |
| 超价卖平今 1 手 | 913.70 / 913.88 | **913.76 / 913.88** | `Offset=3` 平今成功 |

- 委托状态流：`报单已提交`（'a' 未知）→ `全部成交`，与 [[ctp-breakout-demo-notes]] 的状态流结论一致
- 结算单确认耗时 2~18 秒不等，通道就绪前不发单

## 踩坑补充

1. **多开会话会互相看到成交**：`onRtnTrade` 无 FrontID/SessionID，TradeID 是账户级流水；只按 InstrumentID 过滤不够，需要 OrderRef 范围 + 自己记账
2. 浮点盘口（913.9200000000001）来自 CTP double，超价计算后需 `round(price, 2)` 对齐最小变动价位
3. 平今/平昨选错会被柜台拒（`OffsetFlag` 不匹配持仓）——上期所今仓永远用 `'3'`

## 相关页面
[[ctp-demo-notes]] · [[ctp-breakout-demo-notes]] · [[offset-conversion]] · [[ctp-gateway]] · [[stop-order]]
