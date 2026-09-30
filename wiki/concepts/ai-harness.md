---
tags: [concept, agent, harness, llm]
created: 2026-09-19
updated: 2026-09-19
sources: [raw/pku-veighna-course.pdf]
---

# 概念：AI Harness

来源：[[wiki/sources/pku-veighna-course]] p.6–7。课程用这对术语框定「Agent 时代」量化开发的分工，也是本仓库工作流的理论外壳。

## 两层定义

**学术定义（广义）**——三元组：

| 角色 | 含义 |
|---|---|
| Model | 大模型（推理与生成） |
| Harness | 约束环境（工具、边界、可执行上下文） |
| Agent | 智能体（在 Harness 内驱动 Model 完成任务） |

**业界定义（狭义）**——Harness 是可复用的资产包，可挂到多种 Agent 上：

```
Harness
├── 工具   （如：历史回测脚本、eval_factors.py、final_report.py）
├── 技能   （如：回测如何传参、挖掘协议怎么写）
└── 知识   （如：样本内外分拆、过拟合防治 → [[factor-overfitting]]）
     └── 可运行于多种 Agent（ZCode / Claude Code / Kimi Code / …）
```

## 为什么这对概念重要

1. **Harness 与 Agent 解耦**：工具/技能/知识沉淀在仓库里，换一个 Agent 前端不丢资产。本仓库的 `projects/*/`（工具）、AGENTS.md 工作流（技能）、`wiki/`（知识）正好三分。
2. **约束环境 = 纪律的载体**：防过拟合的预算、早停、lockbox、台账之所以能执行，是因为它们被写进 config / protocol / wiki 约定，而不是靠模型「记得住」——见 [[factor-overfitting]] 的「预注册」思想。
3. **一份代码覆盖回测实盘** 的工程思想（[[cta-engine]]）与 Harness 思想同构：把易变的策略逻辑放进稳定的接口约束里。

## 本仓库的 Harness 映射

| Harness 层 | 本仓库落点 |
|---|---|
| 工具 | `projects/ctp_demo`、`projects/ctp_breakout_demo`、`projects/alpha_mining_demo/{eval_factors,final_report}.py` |
| 技能 | `AGENTS.md`（ingest/query/lint/dev 四工作流）、各 `runs/*_protocol.md` |
| 知识 | `wiki/` 全部页面；`llm-wiki.md` 为理念原文 |
| Agent | 当前会话（ZCode/Claude Code 等均可），Obsidian 只读浏览 |

## 相关页面
[[wiki/sources/pku-veighna-course]] · [[factor-overfitting]] · [[alpha-mining-demo-notes]] · [[event-driven-architecture]]
