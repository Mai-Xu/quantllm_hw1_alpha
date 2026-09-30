---
tags: [entity, gateway, ctp]
created: 2026-09-16
updated: 2026-09-16
sources: [raw/vnpy_ctp/vnpy_ctp/gateway/ctp_gateway.py]
---

# 实体：CtpGateway（CTP 期货网关）

`raw/vnpy_ctp/vnpy_ctp/gateway/ctp_gateway.py`，继承 [[base-gateway]]。default_name = "CTP"，支持 CFFEX/SHFE/CZCE/DCE/INE/GFEX 六大期货交易所。

## 双 API 结构
- `CtpMdApi(MdApi)`：行情线。连接→登录→（重连后自动重订阅 `subscribed` 集合）；`onRtnDepthMarketData` 组装 TickData（ActionDay+UpdateTime 毫秒拼时间戳，大商所特殊用本地日期；adjust_price 把 MAX_FLOAT 异常价归 0；仅 1 档时省略 2-5 档字段）
- `CtpTdApi(TdApi)`：交易线，状态机推进：
  1. `onFrontConnected` → 有 auth_code 先 `reqAuthenticate`（认证失败 ErrorID=63 则不再重试）
  2. `onRspUserLogin` → 记录 FrontID/SessionID → **自动确认结算单**
  3. `onRspSettlementInfoConfirm` → while 循环重试 `reqQryInstrument`（对抗流控）
  4. `onRspQryInstrument` 逐个 on_contract 并填 `symbol_contract_map`（模块级全局缓存）；`last=True` 后置 contract_inited，**再补发此前缓存的 order/trade 推送**（order_data/trade_data 队列，保证推送时合约信息已就绪）

## 下单/撤单
- orderid 格式 `{frontid}_{sessionid}_{order_ref}`，order_ref 自增
- 委托类型映射为三元组 (PriceType, TimeCondition, VolumeCondition)：LIMIT→(限价,GFD,AV)、MARKET→(市价,GFD,AV)、FAK→(限价,IOC,AV)、FOK→(限价,IOC,CV)
- 撤单从 orderid 拆回三段填 FrontID/SessionID/OrderRef
- `onRspOrderInsert`（场内拒单）造 REJECTED 状态的 OrderData 回推

## 持仓/资金查询
- EVENT_TIMER 每 2 秒轮流查（`init_query` 注册 query_functions 轮转）
- 持仓回报按 (合约, 方向) 累加（CTP 拆多条回报），SHFE/INE 昨仓特殊处理（YdPosition 且无今仓时直接取）；均价用"总成本/总量"加权

## 已知细节/坑
- 行情服务器只支持第一交易所时区时间戳（CHINA_TZ 硬编码）
- 沙盒/测试环境切换：setting "柜台环境" → production_mode 传给底层 API
- `symbol_contract_map` 是模块级全局变量，多网关实例共享（同进程多份 CTP 网关会有键覆盖风险，实践上可接受）

相关：[[vnpy-ctp-source]] · [[base-gateway]] · [[offset-conversion]]
