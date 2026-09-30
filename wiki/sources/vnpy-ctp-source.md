---
tags: [source, gateway, ctp, futures]
created: 2026-09-16
updated: 2026-09-24
sources: [raw/vnpy_ctp]
---

# 来源：vnpy_ctp 网关源码

- 位置：`raw/vnpy_ctp`（Gitee main，**6.7.11.4**，对应 CTP API 6.7.11；与 Gitee 内容一致）
- 结构：`gateway/ctp_gateway.py`（904 行，全部业务逻辑）；`api/` 为 pybind11 C++ 扩展 `vnctpmd`/`vnctptd` + 生成层 `generator/`；预编译各平台 `.dll/.so/.framework`
- 构建：meson-python + MSVC（`/MT` 静态 CRT）链接上期技术 thost 库

## 关键结论
- 网关拆两条连接：`CtpMdApi`（行情：连接→登录→订阅）与 `CtpTdApi`（交易：连接→**认证**→登录→**结算单确认**→查合约→下单/查询），见 [[ctp-gateway]]
- TD 状态机必须先穿透式认证（AppID+AuthCode）；ErrorID=63（授权码错）→ `auth_failed` **终态**，重连也不再试
- 登录成功自动 `reqSettlementInfoConfirm`，回调里 **while 流控重试** `reqQryInstrument`；合约就绪前 order/trade 回报进缓冲、MD tick **直接丢弃**
- 委托类型是**三元组** `(OrderPriceType, TimeCondition, VolumeCondition)`：LIMIT/MARKET/FAK/FOK，反查失败静默丢弃
- orderid 三段式 `{frontid}_{sessionid}_{order_ref}`；撤单靠 `split("_")` 还原
- 定时查询：EVENT_TIMER 每 2 秒轮转资金/持仓（防 CTP 查询流控）

## 字段映射速查（`ctp_gateway.py:67-129`）
| vnpy | CTP |
|---|---|
| Offset.OPEN/CLOSE/CLOSETODAY/CLOSEYESTERDAY | OFEN_ `0/1/3/4` |
| Status.SUBMITTING/NOTTRADED/PARTTRADED/ALLTRADED/CANCELLED | OST_ `a/3/1/0/5` |
| **REJECTED** | `OST_Canceled`+`OSS_InsertRejected`（**6.7.11.4 新特判**） |
| Direction.LONG/SHORT（委托） | D_ Buy/Sell `0/1` |
| Direction.LONG/SHORT（持仓） | PD_ Long/Short `2/3` |

## 2026-09-24 精读补遗（18 坑精选）
1. **MAX_FLOAT 脏价**：无效价填 DBL_MAX，`adjust_price` 置 0——但 **limit_up/down 未处理**
2. **DCE 时间戳**：ActionDay 空或大商所一律取本地日期（DCE 的 ActionDay 是交易日）
3. **SHFE/INE 昨仓**：`YdPosition and not TodayPosition` 时 yd=Position；其他所 `yd=Position-TodayPosition`
4. **RESTART 私有流**（`subscribePrivateTopic(0)`）：断线重连会重放当日全部 onRtnOrder/Trade，靠 OMS/`vt_tradeids` 幂等消化
5. **Windows 流路径 GBK**：`createFtdc*Api(path.encode("GBK"))`，路径含中文依赖 GBK；分隔符硬编码 `\\`
6. 持仓 key 怪写法 `f"{(InstrumentID, PosiDirection)}"`（tuple 的 repr）
7. `close()` 不反注册 EVENT_TIMER → 反复 add/remove gateway 会泄漏回调
8. 合约缓存 `symbol_contract_map` 是**模块级全局**，同进程多网关互相污染

## 生成层一句话
`api/generator/` 三脚本解析 CTP 头文件 → 产出「SPI 回调入队 → 工作线程 switch → C 结构转 dict → PYBIND11_OVERLOAD 回 Python」及反向 `dict→C 结构→ReqXxx` 的全套胶水 C++，meson 编译进 `vnctpmd`/`vnctptd`。

## 官方测试
`test/test_md.py` / `test_td.py`：Condition 同步、SimNow 参数（BrokerID 9999，AppID `simnow_client_test`，AuthCode 16 个 0）；TD 测试用 `subscribePrivateTopic(2)=QUICK`（与网关 RESTART 不同）。

## 已建相关页面
[[ctp-gateway]] · [[base-gateway]] · [[data-objects]] · [[offset-conversion]] · [[ctp-demo-notes]] · [[ctp-breakout-demo-notes]]
