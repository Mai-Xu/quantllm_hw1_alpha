---
tags: [entity, data-model]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy/vnpy/trader/object.py, raw/vnpy/vnpy/trader/constant.py]
---

# 实体：核心数据对象（trader/object.py）

全部为 `@dataclass`，分三类：

## 数据类（继承 BaseData，带 gateway_name）
| 对象 | 说明 | 要点 |
|---|---|---|
| TickData | tick 快照 | 5 档买卖盘、涨跌停价、开高低收/昨收、持仓量；last_price 为 0 的 tick 应被过滤 |
| BarData | K线 | interval + OHLCV + turnover + open_interest |
| OrderData | 委托 | `is_active()`（SUBMITTING/NOTTRADED/PARTTRADED）；`create_cancel_request()` |
| TradeData | 成交 | 一笔委托可多次成交 |
| PositionData | 持仓 | direction + volume/frozen/price/pnl/yd_volume |
| AccountData | 账户 | available 在 post_init 自动算 = balance - frozen |
| ContractData | 合约 | pricetick/size/min_volume/stop_supported/net_position/history_data + 期权全套字段 |
| QuoteData | 双边报价 | 做市用 |

## 请求类（无基类）
`SubscribeRequest / OrderRequest / CancelRequest / HistoryRequest / QuoteRequest`。OrderRequest 有 `create_order_data()` 工厂方法。

## 常量枚举（constant.py，全部中文本地化）
- Direction: LONG/SHORT/NET；Offset: NONE/OPEN/CLOSE/CLOSETODAY/CLOSEYESTERDAY
- Status: SUBMITTING/NOTTRADED/PARTTRADED/ALLTRADED/CANCELLED/REJECTED
- OrderType: LIMIT/MARKET/STOP/FAK/FOK/RFQ
- Exchange: 中国 15 个（CFFEX/SHFE/CZCE/DCE/INE/GFEX/SSE...）+ 全球 + LOCAL/GLOBAL 兜底
- Interval: MINUTE/HOUR/DAILY/WEEKLY/TICK

详见 [[vt-symbol-naming]]（vt_ ID 生成规则）。

相关：[[base-gateway]] · [[oms-engine]]
