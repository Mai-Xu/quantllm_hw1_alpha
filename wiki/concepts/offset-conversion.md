---
tags: [concept, futures, order]
created: 2026-09-16
updated: 2026-09-24
sources: [raw/vnpy/vnpy/trader/converter.py]
---

# 概念：开平仓转换（平今/平昨/锁仓）

中国期货特有问题：上期所/能源中心（SHFE/INE）平今仓手续费不同且必须显式区分平今（CLOSETODAY）平昨（CLOSEYESTERDAY）；其他交易所用统一 CLOSE。vnpy 用 `OffsetConverter` + `PositionHolding` 在 OMS 层自动拆单（`raw/vnpy/vnpy/trader/converter.py`）。

## PositionHolding（仓位簿记）
每个 vt_symbol 维护 long/short 的 `pos / td(今仓) / yd(昨仓)` 及对应 frozen，由 position/order/trade 事件增量更新：
- `update_trade`：按 offset 增减 td/yd
- `calculate_frozen`：遍历活动委托，把挂单量冻结到对应 td/yd

### SHFE/INE 语义（最容易记反）
- **SHFE/INE 的 `Offset.CLOSE` = 平昨**（`close_yd_exchanges`，converter.py L81-82/L211）
- 其他所 `CLOSE` = 优先平今，不足回补昨仓（允许 td 变负后从 yd 回补）
- 因此 `convert_order_request_shfe` 把平仓单按可用拆成 `CLOSETODAY` + `CLOSEYESTERDAY` 两笔；不够则整单拒绝返回 `[]`

## 三种转换模式（`convert_order_request(req, lock, net)`）
优先级：**lock > net > SHFE/INE 特殊 > 原样**。
1. **默认**：仅 SHFE/INE，CLOSE 按 td/yd 可用量拆两笔（`convert_order_request_shfe` L168）
2. **lock 锁仓**：有今仓且非 SHFE/INE → **反向开仓锁住**（避免平今费用）；否则先平可用昨仓、剩余开新（L202）
3. **net 净持仓**：SHFE/INE 拆 CLOSETODAY/CLOSEYESTERDAY/OPEN；其他所 CLOSE+OPEN（L242）

## 门控与链路
- `is_convert_required`（L390）：`contract.net_position == True` 时**完全跳过**转换（股票/外盘净持仓模式网关自处理）
- 链路：CTA `buy/sell/short/cover(lock,net)` → `CtaEngine.send_order` → `MainEngine.convert_order_request` → 多笔 OrderRequest
- 回测 `BacktestingEngine` **忽略 lock/net**——上期所品种回测失真点之一（见 [[cta-template]]）

## 已知隐患（2026-09-24 精读）
- `convert_order_request_net` 非 SHFE 分支 L292：`volume_left -= pos_available` 疑似应为 `-= close_volume`，当 `pos_available > volume_left` 时多减变负
- `update_order_request` 用 `vt_orderid.split(".")` 取 orderid——**gateway_name 不得含 `.`**
- 持仓 key 怪写法见 [[ctp-gateway]]（tuple repr）

相关：[[oms-engine]] · [[cta-engine]] · [[ctp-gateway]] · [[data-objects]]
