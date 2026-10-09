# 复现说明

本文件给出实际执行过的命令、环境版本、退出码与日志位置。
**注意**：`py_compile` 只证明语法正确，**不等于运行成功**；本文件区分标注两者。

## 1. 环境与依赖

环境版本快照（自动生成）：[`requirements.lock.txt`](requirements.lock.txt)

| 项 | 值 |
|---|---|
| Python | 3.13.8 (CPython) |
| 平台 | Windows 11 AMD64 |
| 解释器 | `D:\VeighNa_TradeDesk\abc\python.exe`（VeighNa Studio 集成环境） |
| vnpy | 4.4.0 |
| polars | 1.44.2 |
| pandas | 2.2.3 |
| numpy | 2.2.3 |
| pyarrow | 25.0.1（polars `to_pandas` 依赖） |
| alphalens-reloaded | 0.4.6（`vnpy.alpha` 顶层导入依赖） |
| matplotlib | 3.10.9 |
| scipy / statsmodels | 1.17.1 / 0.15.0 |

完整依赖树（300 个包）见 [`pip-freeze.txt`](pip-freeze.txt)。

### 安装

```powershell
pip install "vnpy[alpha]" --index=https://pypi.vnpy.com
pip install pyarrow            # polars.to_pandas 需要
pip install alphalens-reloaded # vnpy.alpha 顶层 import 需要
```

> 实测踩坑：只装 `vnpy[alpha]` 仍会缺 `pyarrow` 与 `alphalens`，
> 分别在「因子计算成功但 to_pandas 失败」与「import vnpy.alpha 即失败」两处报错。
> 精确版本以 `pip-freeze.txt` 为准（可用 `pip install -r pip-freeze.txt` 还原）。

## 2. 数据

`runs/cache/base_dataset.pkl`（234,857,524 字节，SHA-256 见 `runs/final/data_fingerprint.json`）**不入库**。

- 若已有上游 lab 数据（`raw/alpha_researcher/lab/csi300`），删除该 pkl 后脚本会自动重建
- 重建依赖 `config.json` 的 `lab_path`（绝对路径），该路径在本机为 D 盘原工作区
- **无 lab 数据则无法从零复现**；本仓库不附带行情数据（合规与体积原因）

## 3. 实际执行过的命令与退出码

以下命令均在本机实际运行过，退出码为真实观测值。

| # | 命令 | 退出码 | 说明 | 日志 |
|---|---|---|---|---|
| 1 | `python eval_factors.py runs/volpos_round_01/candidates.json` | `0` | 18 候选，耗时 ~8.5 min | 控制台（未单独留档） |
| 2 | `python eval_factors.py runs/volpos_round_02/candidates.json` | `0` | 11 候选，~4 min | 同上 |
| 3 | `python eval_factors.py runs/volpos_round_03/candidates.json` | `0` | 12 候选；**首跑退出码 1**（`cs_zscore` 不存在），修正后 0 | `runs/volpos_round_03/eval_log.txt` |
| 4 | `python eval_factors.py runs/volpos_round_04/candidates.json` | `0` | 10 候选，~3 min | `runs/volpos_round_04/eval_log.txt` |
| 5 | `python final_report.py` | `0` | 指标表 + 13 张图 | `runs/final/report_log.txt` |
| 6 | `python friction_report.py` | `0` | 摩擦与显著性报告（评审后新增） | `runs/final/friction_log.txt` |
| 7 | `python tests/test_offline.py`（ctp_open_close_demo） | `0` | **17/17 passed**，不联网 | 控制台 |
| 8 | `python demo.py`（ctp_open_close_demo，13:33 盘中） | **`0`** | **闭环验证 PASS**：平仓成交 + 持仓归零 + 无活动委托 | `evidence/journal_20261009_133314.jsonl` |

观察到的**非零退出码**（同样如实记录）：

| 命令 | 退出码 | 原因 |
|---|---|---|
| `eval_factors.py runs/volpos_round_03/...`（首跑） | `1` | `NameError: cs_zscore not defined`（算子名错误） |
| `friction_report.py`（首跑） | `1` | `KeyError: 'turnover'`（未选入列） |
| `friction_report.py`（二跑） | `1` | 渲染时把字典当数值格式化 |
| `demo.py`（ctp_open_close_demo，午间休市运行） | `5` | 等待成交超时 → **fail-closed 生效** |

## 4. 日志（脱敏）

| 文件 | 内容 |
|---|---|
| `runs/final/friction_log.txt` | 摩擦报告运行日志 |
| `runs/final/report_log.txt` | 终局报告运行日志 |
| `runs/volpos_round_03/eval_log.txt` | 含首次崩溃的完整 traceback（保留为复现证据） |
| `runs/volpos_round_04/eval_log.txt` | 轮次评估日志 |
| `../ctp_open_close_demo/evidence/journal_*.jsonl` | 交易闭环逐事件证据，账号字段脱敏为 `******` |

## 5. 离线测试

```powershell
cd projects/ctp_open_close_demo
& "<veighna python>" tests/test_offline.py
```

覆盖：委托三段归属、成交 OrderSysID 自洽与他会话拒收、方向一致性、
终态校验四条失败路径、脱敏、缺配置 fail-closed。**预期 17/17 passed、退出码 0**。

因子侧暂无单元测试（`friction_report.py` 的 HAC/区块 bootstrap 为纯函数，可直接调用验证）。

## 6. 未验证项（不得表述为「已运行通过」）

- ~~交易闭环的 0 退出码尚未取得~~ **已于 2026-10-09 13:33（盘中）取得**：
  `demo.py` 退出码 `0`，证据 `../ctp_open_close_demo/evidence/journal_20261009_133314.jsonl`
  （开仓成交 @908.66、平今成交 @908.74、au2612 持仓查询为 0、本会话无活动委托）。
  同日 12:42（午间休市）的一次运行以退出码 `5` fail-closed 收场，同样留档为对照。
- `ctp_demo` / `ctp_breakout_demo` 的账号配置已改为环境变量，**改后未重新实盘运行**（仅 `py_compile` 通过）。
- 复权口径未核实（见 `runs/final/freeze.md` §3）。
