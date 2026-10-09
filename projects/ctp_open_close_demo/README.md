# ctp_open_close_demo — 可验证的 1 手开平闭环

在 SimNow 上完成 **1 手开仓 → 1 手平仓 → 持仓归零**，并对结果做**可复核的终态校验**。

本目录是对「只能证明平仓单已发出」这一评审意见的重写版本。

## 与早期版本的差别

| 维度 | 早期版本 | 本版本 |
|---|---|---|
| 开仓意图 | 无持久化 | 发单**前**写 `evidence/journal_*.jsonl`（崩溃可复原意图） |
| 委托归属 | FrontID + SessionID + OrderRef | 同上，且 OrderRef 必须在**本会话登记集合**内 |
| 成交归属 | OrderRef 范围比较（不严密） | OrderRef 登记 + **OrderSysID 自洽** + 方向一致；他会话成交**明确拒收并计数** |
| 平仓判定 | `close_sent`（已发出） | `close_filled`（**归属后的成交数量** ≥ 1 手） |
| 终态校验 | 无 | `reqQryInvestorPosition` 查持仓归零 + 本会话无活动委托 |
| 失败处理 | 打印日志继续 | **fail-closed**：断线/拒单/超时/状态未收敛 → 非 0 退出码 |

## 目录

```
demo.py                 # 主程序（仅从环境变量读凭据）
config.sample.json      # 无值配置样例（含环境变量说明）
tests/test_offline.py   # 离线测试：归属过滤 / 终态校验 / fail-closed（不联网）
evidence/               # 运行证据（journal_*.jsonl，账号字段脱敏）
```

## 配置（源码与本仓库不含任何账号值）

必需的环境变量：

| 变量 | 说明 |
|---|---|
| `Mai_SimNow_userid` | 投资者代码 InvestorID（必填） |
| `Mai_SimNow_password` | 登录密码（必填） |

可选（未设则用 SimNow 公开默认值，非凭据）：`Mai_SimNow_brokerid`（默认 `9999`）、
`Mai_SimNow_td_address`（默认 `tcp://182.254.243.31:30001`）、
`Mai_SimNow_md_address`（默认 `tcp://182.254.243.31:30011`）、
`Mai_SimNow_appid`、`Mai_SimNow_auth_code`。

```powershell
# 仅当前会话有效
$env:Mai_SimNow_userid = '<你的投资者代码>'
$env:Mai_SimNow_password = '<你的密码>'
```

> **注意**：本程序**只**从环境变量读取凭据，不从注册表兜底（来源明确、fail-closed 可测）。
> 用 `[Environment]::SetEnvironmentVariable(...,'User')` 设置的变量需在**新开的终端**中才可见。

## 运行

```powershell
cd projects/ctp_open_close_demo
& "<VeighNa 环境的 python.exe>" demo.py
```

前置端口随交易时段切换：盘中 `30001/30011`，夜盘实测 `40001/40011`。
非交易时段前置会拒绝连接（此时以退出码 3/5 收场，属预期）。

## 退出码

| 码 | 含义 |
|---|---|
| `0` | **闭环验证通过**：平仓成交 + 持仓归零 + 无活动委托 |
| `2` | 配置缺失（环境变量未设置） |
| `3` | 连接 / 认证 / 登录 / 结算确认失败 |
| `4` | 委托被柜台拒绝 |
| `5` | 等待成交超时 |
| `6` | 终态校验失败（持仓非 0 或存在活动委托） |
| `7` | 中途断线 |

**只有 `0` 代表成功**；任何非 0 都应视为闭环未达成。

## 离线测试（不联网、不下单）

```powershell
python tests/test_offline.py
```

覆盖：委托三段归属、成交 OrderSysID 自洽与他会话拒收、方向一致性、
终态校验四种失败路径、脱敏、缺配置 fail-closed。预期 **17/17 passed**。

## 证据（脱敏）

运行后 `evidence/journal_<RUN_ID>.jsonl` 记录逐事件：

```
run_start → td_login → settlement_confirmed
→ order_intent(open) → order_update(s) → trade(open)
→ order_intent(close) → order_update(s) → trade(close)
→ position_query → verify_result
```

账号字段经 `mask()` 处理后落盘（如 `******`），不含 UserID / 密码 / 资金快照。
`verify_result` 一条即闭环结论，含 `passed`、`close_filled`、`active_orders`、
`positions`、`foreign_trade_rejected` 字段，可脱离聊天记录独立复核。

## 已知边界（如实声明）

- 只验证**本合约、本会话**的闭环；账户其他持仓不在校验范围。
- SimNow 为模拟环境，成交回报时序与真实柜台存在差异。
- 未做撤单路径（本流程以超价保证成交，不撤单）；若长时间不成交则以超时码 `5` 失败退出。
- 未做资金/保证金校验；仅 1 手且为模拟盘，取最小暴露。
