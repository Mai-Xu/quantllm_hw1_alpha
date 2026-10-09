# VeighNa 量化交易系统学习 Wiki

> LLM 维护的个人知识库 + 自研量化实验，主题是 **基于 VeighNa (vnpy) 的量化交易系统开发**。
> 方法论来自 [Karpathy 的 LLM-Wiki 思路](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)：
> LLM 负责摘要、交叉引用、归档与记账；人负责选资料、提问、把关。

**推荐用 [Obsidian](https://obsidian.md/) 打开 `wiki/` 目录浏览**（图谱视图看交叉引用），
从 `wiki/index.md` 进入。

---

## 这个仓库有什么

| 目录 | 内容 |
|---|---|
| `wiki/` | 知识库：概念页、实体页、来源页、自研代码笔记、时间日志 |
| `projects/` | 自研实验：CTP 下单闭环 ×3、LLM 驱动因子挖掘 ×1 |
| `AGENTS.md` | Wiki schema——目录约定、工作流（ingest / query / lint / dev）、红线 |
| `llm-wiki.md` | 方法论原文（只读） |

`raw/`（vnpy / vnpy_ctp / vnpy_ctastrategy 源码快照）不入库，是阅读原料，见 `.gitignore`。

---

## 三条学习主线

### 1. 框架源码精读 → 三层架构

vnpy 4.4.0 / vnpy_ctp 6.7.11.4 / vnpy_ctastrategy 1.4.1 全文精读，落到 wiki 实体页：

```
策略应用   CtaTemplate · 投组 · 价差
中层引擎   EventEngine · OmsEngine · 交易指令路由
底层接口   object/constant 数据标准化 · BaseGateway 流程标准化
```

总纲见 `wiki/concepts/veighna-three-layers.md`。

### 2. 从零打通 CTP 交易链路（SimNow 实测）

| 项目 | 验证内容 | 结果 |
|---|---|---|
| `ctp_demo` | 连接 / 认证 / 登录 / 订阅行情 | ✅ 实时推送 |
| `ctp_breakout_demo` | 突破触发限价开仓 | ✅ SimNow 成交 |
| `ctp_open_close_demo` | 超价开 + 超价平（平今）完整闭环 | ✅ 开平各一腿成交 |

踩坑记录（前置端口随交易时段切换、上期所平今 `CombOffsetFlag='3'`、账户级成交回报过滤等）
在 `wiki/code/ctp-*.md`。

### 3. LLM 驱动因子挖掘（五方向，28 轮约 431 个候选）

流水线：LLM 生成表达式 → `vnpy.alpha` 评估 → 读指标反思 → 迭代；
防过拟合纪律：预注册协议、噪声锚点、试验台账、test 隐藏、lockbox 冻结、三票制留存。

| 方向 | 主推结构 | valid RankIR | test RankIR |
|---|---|---|---|
| VP 量价共振 | PV_ANTI_TRIPLE | 0.51 | 0.28 |
| REV 反转 | REV_TRIPLE | 0.48 | 0.21 |
| MOM 动量 | （证伪） | — | — |
| GAP 跳空 | GAP_DIFF4_TURN | 0.29 | 0.20 |
| VOLPOS 波动位置 | REV4_TURN_HIGHPOS | 0.28 | 0.15 |

**研究纪律与可复核材料**：

| 材料 | 路径 | 内容 |
|---|---|---|
| 研究报告 | `projects/alpha_mining_demo/runs/final/report.html` | 含叙述与图表 |
| 指标表 | `runs/final/performance_report.md` | 分段 IC、分组、分年 |
| 冻结清单 | `runs/final/freeze.md` | 数据指纹 SHA-256、股票池、复权口径、信号时点、停止规则 + 时序证据 |
| 试验台账 | `runs/attempt_ledger.md` | 全部 28 轮候选与证伪支线（含已丢失产物的如实披露） |
| 摩擦报告 | `runs/final/friction_report.md` | 毛/净收益、三档费用+印花税+滑点、涨跌停停牌、容量、融券约束、HAC/区块 bootstrap |
| 复现说明 | `projects/alpha_mining_demo/REPRODUCE.md` | 依赖锁定、实际命令、退出码、脱敏日志 |
| 留存决策 | `runs/final/retention.md` | 三票制（冻结于终局报告之前） |

> **口径提醒**：label 为 T+1→T+3 的重叠收益，年化与回撤按**非重叠 3 日块**计算，
> 显著性用 HAC(Newey–West) 与平稳区块 bootstrap。多头组合扣费后（base 情景）
> 年化为负——IC 类指标与可落袋收益是两个口径，详见摩擦报告。

> 五方向合流结论：A 股 T+3 反转的每个调制维度都在样本内成立、样本外衰减；
> 可预测性存在于「方向 × 状态」交互项，而非任何一阶矩。

---

## 快速开始

### 浏览知识库

1. 安装 [Obsidian](https://obsidian.md/)，打开本仓库根目录（或仅 `wiki/`）
2. 从 `wiki/index.md` 或 `wiki/overview.md` 开始

### 运行 CTP Demo（需要 SimNow 账号）

```powershell
# 环境：VeighNa Studio Python（已含 vnpy_ctp）
# 密码放环境变量 Mai_SimNow_password（勿写入代码）
$env:VeighNa_Python = "D:\VeighNa_TradeDesk\abc\python.exe"   # 按本机路径修改

cd projects/ctp_demo
& $env:VeighNa_Python demo.py
```

SimNow 注册：<http://www.simnow.com.cn/> ｜ 经纪商 `9999` ｜ 前置端口随交易时段切换
（盘中 `30001/30011`，夜盘实测 `40001/40011`）。

### 复现因子挖掘

```powershell
pip install "vnpy[alpha]" --index=https://pypi.vnpy.com
cd projects/alpha_mining_demo
python eval_factors.py runs/volpos_round_01/candidates.json
python final_report.py
```

数据缓存 `runs/cache/base_dataset.pkl`（224MB）不入库；若你有
`raw/alpha_researcher/lab/csi300` 沪深300 日线 lab 数据，删除缓存后会自动重建。

---

## 约定（详见 `AGENTS.md`）

- `raw/` 只读，不修改；`log.md` 只追加
- wiki 页面中文书写，代码/标识符保留英文；YAML frontmatter + `[[双链]]`
- 日志条目可 grep：`## [YYYY-MM-DD] ingest|query|lint|dev | ...`
- 密码等机密走环境变量，不入库

## License

仅供学习交流。vnpy 等上游项目版权归其作者所有（MIT）。
