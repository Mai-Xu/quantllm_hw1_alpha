---
tags: [index]
created: 2026-09-16
updated: 2026-09-24
---

# Index — wiki 目录

## Sources（资料摘要）
- [[vnpy-source]] — vnpy 主框架 4.4.0：骨架+插件装配、4 内置引擎、Quote/Wechat、精读坑清单（2026-09-24）
- [[vnpy-ctp-source]] — vnpy_ctp 6.7.11.4：TD 状态机、三元组委托类型、字段映射、18 坑、生成层（2026-09-24）
- [[vnpy-ctastrategy-source]] — vnpy_ctastrategy 1.4.1：模板/引擎/回测、8 示例意图、回测失真清单（2026-09-24）
- [[alpha-researcher]] — alpha_researcher 参考项目存根页：vnag+LLM 流水线、csi300 数据源位置说明（2026-09-19）
- [[pku-veighna-course]] — 北大课程《VeighNa 量化平台 · Agent 时代下的交易系统开发》（2026-09-19）

## Concepts（概念）
- [[veighna-three-layers]] — 三层交易系统架构：底层接口/中层引擎/策略应用全景（2026-09-30）
- [[event-driven-architecture]] — 事件驱动架构：双发机制、单线程心脏（2026-09-24）
- [[vt-symbol-naming]] — vt_ 前缀统一命名体系
- [[offset-conversion]] — 开平仓转换：SHFE/INE CLOSE=平昨、三模式、net 隐患（2026-09-24）
- [[bar-synthesis]] — BarGenerator K线合成与 ArrayManager
- [[stop-order]] — 本地停止单：实盘触发逻辑与回测差异
- [[backtesting-model]] — 回测撮合与绩效模型
- [[factor-overfitting]] — 因子挖掘过拟合防治
- [[ai-harness]] — AI Harness：Model/Harness/Agent
- [[factor-expression-ops]] — 表达式因子与 ts/cs 算子（2026-09-24 补算子清单）

## Entities（模块 / 类）
- [[event-engine]] — EventEngine 事件总线
- [[main-engine]] — MainEngine 装配中心与门面
- [[oms-engine]] — OmsEngine 订单管理与内存缓存
- [[base-gateway]] — BaseGateway 网关抽象契约
- [[data-objects]] — 核心数据对象与常量枚举
- [[ctp-gateway]] — CtpGateway：Md/Td 双 API、状态机、查询轮转
- [[cta-engine]] — CtaEngine 实盘引擎
- [[cta-template]] — CtaTemplate / TargetPosTemplate（2026-09-24 补回测/实盘分叉）
- [[backtesting-engine]] — BacktestingEngine 回测引擎
- [[alpha-dataset]] — AlphaDataset 与表达式因子引擎（2026-09-24 新建）
- [[alpha-lab]] — AlphaLab 存储与组合回测（2026-09-24 新建）
- [[optimize-engine]] — 参数寻优 BF/GA（2026-09-24 新建）
- [[rpc-module]] — ZeroMQ RPC（2026-09-24 新建）

## Code（自研程序设计笔记）
- [[ctp-demo-notes]] — ctp_demo：最小化 CTP DEMO
- [[ctp-breakout-demo-notes]] — ctp_breakout_demo：突破触发下单闭环
- [[ctp-open-close-demo-notes]] — ctp_open_close_demo：超价开 + 超价平完整闭环（2026-09-28）
- [[alpha-mining-demo-notes]] — alpha_mining_demo：LLM 因子挖掘五方向（VP/REV/MOM/GAP/VOLPOS）
- 报告：`projects/alpha_mining_demo/runs/final/report.html` — VOLPOS 研究报告（含图表）

## Meta
- [[overview]] — 全局总览与计划
- [[log]] — 时间日志
