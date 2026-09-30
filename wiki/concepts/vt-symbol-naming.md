---
tags: [concept, naming, data-model]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy/vnpy/trader/object.py]
---

# 概念：vt_ 前缀统一命名体系

vnpy 用一套自动生成的 vt_ 字段解决"多网关、多交易所、多账户同名冲突"问题。所有 Data 对象在 `__post_init__` 里自动拼接：

| 字段 | 格式 | 示例 |
|---|---|---|
| `vt_symbol` | `{symbol}.{exchange.value}` | `rb2510.SHFE` |
| `vt_orderid` | `{gateway_name}.{orderid}` | `CTP.1_42_7` |
| `vt_tradeid` | `{gateway_name}.{tradeid}` | |
| `vt_positionid` | `{gateway_name}.{vt_symbol}.{direction}` | |
| `vt_accountid` | `{gateway_name}.{accountid}` | |

- `vt_symbol` 是全系统定位合约的主键；`extract_vt_symbol()` / `generate_vt_symbol()` 是配套工具（`utility.py`）
- CTP 的原始 orderid 是 `{frontid}_{sessionid}_{order_ref}`（会话相关，重连后变化），vt_ 化后前缀 gateway_name 保证跨网关唯一
- OrderRequest/CancelRequest 等"请求对象"不继承 BaseData（没有 gateway_name），交给哪个网关由 MainEngine 的参数显式指定

相关：[[data-objects]] · [[ctp-gateway]]
