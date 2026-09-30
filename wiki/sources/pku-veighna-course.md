---
tags: [source, course, veighna, agent]
created: 2026-09-19
updated: 2026-09-19
sources: [raw/pku-veighna-course.pdf]
---

# 来源：北大课程《VeighNa 量化平台 — Agent 时代下的交易系统开发》

- 位置：`raw/pku-veighna-course.pdf`（19 页 PPT，约 0.97 MB）
- 讲者：陈晓优（VeighNa 作者，上海韦纳软件科技）
- 场合：北京大学《当代量化交易系统的原理与实现》，2026-09-18
- 原始文件在上层目录 `北大-VeighNa量化平台.pdf`（课件原件，不入 raw 重复存放以外的修改）

## 一页纸课程地图

| 页 | 主题 | wiki 落点 |
|---|---|---|
| 1–3 | VeighNa 公司/平台/生态概况 | 本页「平台概况」 |
| 4 | 量化交易系统架构一览 | 本页「系统架构」→ [[event-driven-architecture]]、[[main-engine]] |
| 5 | Agent 时代学习工具（Studio / ZCode / Obsidian） | 本页「工具链」 |
| 6–7 | AI Harness（学术 vs 业界定义） | [[ai-harness]] |
| 8–10 | LLM-Wiki 知识库方法论 | `llm-wiki.md`（理念原文）+ 本仓库即实例 |
| 11–12 | 最小化 Demo：连接 → 订阅 → 下单 | [[ctp-demo-notes]]、[[ctp-breakout-demo-notes]] |
| 13–14 | 策略引擎：为何一份代码覆盖回测实盘 | [[cta-engine]]、[[cta-template]]、[[backtesting-engine]] |
| 15–17 | 截面选股演进 + 表达式因子 + ts/cs 算子 | [[factor-expression-ops]] |
| 18 | AI Agent 因子挖掘闭环 | [[alpha-mining-demo-notes]]、[[factor-overfitting]] |
| 19 | 社区资源 | 本页「延伸」 |

## 平台概况

- **组织**：上海韦纳软件科技有限公司（2017-08 成立）；开源产品 VeighNa（曾用名 vn.py，因商标抢注更名），仓库 `github.com/vnpy/vnpy`
- **商业**：C 端 VeighNa Elite / Fusion；B 端 VeighNa Flow / Nexus；另有定制开发、咨询、培训
- **发展**：2015-03 首次发布 → 2018 后商业开发 → 2019 起全球开源量化平台排名领先
- **覆盖**：交易通道（股票/期货/期权/黄金/固收/资管/外盘）；策略功能（CTA、投组、价差套利、期权波动率、做市报价）
- **体量**（课件数据）：GitHub Star 45.4k / Fork 12.5k；社区注册 91.7k / 发帖 42.5k

## 系统架构（课件图）

课件给出一张与 vnpy 实现同构的总览图，自上而下：

```
柜台行情服务器 ──行情API──┐
                          ├──► 内部消息总线 ──► 事前交易风控
柜台交易服务器 ──交易API──┘         │
                                    ├──► 量化策略引擎（策略实例 A/B/C…）
                                    ├──► 交易员管理 UI
                                    ├──► 持久化数据库
                                    └──► 旁路监控服务
```

与源码精读的对应关系：
- 「内部消息总线」→ [[event-engine]] / [[event-driven-architecture]]
- 「策略引擎 + 策略实例」→ [[cta-engine]] / [[cta-template]]（一策略一实例，三张映射表管理）
- 「行情/交易 API」→ [[base-gateway]] / [[ctp-gateway]]（Md/Td 双 API）
- 「数据标准化、指令路由、OMS 缓存」（课件 p.13 中层）→ [[oms-engine]] / [[data-objects]] / [[vt-symbol-naming]]
- 「持久化」→ vnpy.trader.database 插件（本 wiki 尚未单独建页，见 [[vnpy-source]]）

课件 p.13–14 的分层强调两点：
1. **底层接口**做数据结构标准化 + 业务流程标准化（开平/撤单/查询轮转等），上层策略不感知柜台差异
2. **策略引擎**统一「状态初始化 / 历史数据 / 缓存状态 / 外部推送 / 主动请求」四类入口，使**一份策略代码同时覆盖回测与实盘**——这是 [[backtesting-engine]] 与 [[cta-engine]] 共享 [[cta-template]] 回调约定的根本原因

## 工具链（Agent 时代学习环境）

| 工件 | 用途 | 课件建议 |
|---|---|---|
| VeighNa Studio | 集成 Python 环境，傻瓜安装 | 初学者首选；高手可自管环境 |
| ZCode | AI 开发 Harness（性价比） | 也可用 Claude Code / Kimi Code / Deepseek Harness 等 |
| Obsidian | 阅读结构化 Markdown wiki | 几乎无替代；VS Code 预览勉强可用 |

本仓库工作流即「Agent（写 wiki）+ Obsidian（读 wiki）」——与 `llm-wiki.md` 的实践建议一致。

## LLM-Wiki 方法论（课件 p.8–10）

课件直接引用 Andrej Karpathy 的 LLM-Wiki 思路（原文 gist：`karpathy/442a6bf555914893e9891c11519de94f`）：
用 LLM 维护**可以持续成长**的结构化知识库，由 LLM 承担全部重复「体力活」（摘要、交叉引用、归档、记账）。

课件给出的消化第一份资料四步：
1. 初始化知识库（`llm-wiki.md` → schema）
2. 放入原始材料（vnpy 源码）
3. 执行初步解析（阅读总结架构）
4. 提问创建页面（如「消息总线实现」）

本仓库 2026-09-16 的建库过程与该四步一一对应；Obsidian 侧只需打开 wiki 目录，用 [[index]] 导航、[[log]] 查变更。

## 与本仓库实战路径的对应

课件 p.11–12「上手最小化 Demo」三步（连接登录 → 订阅行情 → 打印推送，再扩展到 TD 下单与突破策略），已在 `projects/` 完整落地：

1. **底层 Python 交易 API**（基于 vnpy_ctp）→ [[ctp-demo-notes]]：MdApi 连接/认证/登录/订阅/打印推送
2. **对接交易下单**（引入 TD API）→ [[ctp-breakout-demo-notes]]：认证→登录→结算单确认→限价买开
3. **实现策略逻辑**（超过价格下单）→ 同上突破触发闭环，SimNow 实测成交

课件 p.18「AI Agent 因子挖掘」四步闭环（给出方向 → 生成公式 → 评估绩效 → 判断是否继续），即 [[alpha-mining-demo-notes]] 的 ZCode 会话挖掘协议；表达式与算子层见 [[factor-expression-ops]]，防过拟合纪律见 [[factor-overfitting]]。

## 关键结论

- 课件是**路线图**，不是实现细节：架构图/学习路径/工具选择均可在本 wiki 的源码页与 code 笔记中找到对应实现与踩坑记录
- Agent 时代的学习形态已经跑通：ZCode（或任意 Harness）+ LLM-Wiki + Obsidian + VeighNa Studio
- 截面选股从人工到 ML 的演进（p.15）与表达式算子（p.16–17）共同构成 Agent 因子挖掘的**表达层**——没有可组合的 ts/cs 算子，LLM 就无法「生成公式」

## 延伸

- 社区公众号 `vnpy-community`：入门教程、进阶经验、公告
- 原始理念文档：`llm-wiki.md`（只读）
- 工具落地笔记：[[wiki/code/ctp-demo-notes]]、[[wiki/code/ctp-breakout-demo-notes]]、[[wiki/code/alpha-mining-demo-notes]]

## 相关页面
[[ai-harness]] · [[factor-expression-ops]] · [[event-driven-architecture]] · [[cta-engine]] · [[alpha-mining-demo-notes]] · [[index]]
