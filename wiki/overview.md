---
tags: [overview]
created: 2026-09-16
updated: 2026-09-24
---

# Overview — VeighNa 量化交易学习 wiki

## 目标
系统学习基于 VeighNa (vnpy) 的量化交易系统开发：框架架构、核心模块、策略开发、回测与实盘，并在此基础上开发自己的量化程序。

学习路线以北大课程《VeighNa 量化平台 · Agent 时代下的交易系统开发》（2026-09-18，见 [[pku-veighna-course]]）为纲，源码精读与自研实践为两翼。

## 当前状态
- **三模块源码二次精读完成**（2026-09-24）：与 Gitee main 逐文件核对（vnpy 4.4.0 / ctp 6.7.11.4 / cta 1.4.1）；覆盖 event/trader 全部、ctp_gateway 全文、ctastrategy 全文、**alpha/rpc/chart/ui**（此前缺口）
  - 新建实体页：[[alpha-dataset]]、[[alpha-lab]]、[[optimize-engine]]、[[rpc-module]]
  - 修正/补遗：[[event-driven-architecture]]（双发）、[[offset-conversion]]（SHFE CLOSE=平昨 + net 隐患）、[[cta-template]]（回测/实盘分叉）、三来源页全面重写
- **课程路线图已 ingest**（2026-09-19）：[[pku-veighna-course]]；概念页 [[ai-harness]]、[[factor-expression-ops]]
- **自研程序 3 个**（`projects/`）：ctp_demo / ctp_breakout_demo（SimNow 实测）、alpha_mining_demo（四方向 + lockbox 纪律）
- 注意：当前工作区是 D 盘原工作区副本，缺 `.git`、`raw/alpha_researcher`、`raw/assets`（见 [[wiki/sources/alpha-researcher]]）
- 环境：可用 Python 为 `D:\VeighNa_TradeDesk\abc\python.exe`（VeighNa Studio，已装 vnpy_ctp 4.x 与 vnpy 4.4.0）

## 课程路线图对照

| 课件 | 主题 | 状态 | 落点 |
|---|---|---|---|
| p.4 | 量化交易系统架构 | ✅ | [[event-driven-architecture]]、[[main-engine]] |
| p.6–7 | AI Harness | ✅ | [[ai-harness]] |
| p.8–10 | LLM-Wiki 方法论 | ✅ | `llm-wiki.md` + 本仓库 |
| p.11–12 | 最小化 Demo → 下单 | ✅ | [[ctp-demo-notes]]、[[ctp-breakout-demo-notes]] |
| p.13–14 | 策略引擎分层 | ✅ | [[cta-engine]]、[[cta-template]]、[[backtesting-engine]] |
| p.15–17 | 截面选股 / 表达式 / ts·cs | ✅ | [[factor-expression-ops]]、[[alpha-dataset]] |
| p.18 | Agent 因子挖掘闭环 | ✅ | [[alpha-mining-demo-notes]]、[[factor-overfitting]] |
| — | **CtaTemplate 正式策略 + 回测** | 🔶 未做 | 主线问题 5 收尾项 |

## 主线问题
1. ✅ vnpy 整体架构 → [[event-driven-architecture]]、[[main-engine]]
2. ✅ 网关层如何对接柜台 → [[base-gateway]]、[[ctp-gateway]]（+ 底层 API 直连实测）
3. ✅ CTA 策略引擎 → [[cta-engine]]、[[cta-template]]
4. ✅ 回测系统 → [[backtesting-engine]]、[[backtesting-model]]（2026-09-24 补 RGR/撮合细节）
5. 🔶 如何构建自己的交易系统？已走通：底层 API 直连 ×2、因子研究闭环；**尚未做**：CtaTemplate 正式策略 + 回测
6. 🔶 因子研究方法论：防治框架已成型（[[factor-overfitting]]），落地项见其"剩余盲点"节

## 下一步
- [ ] 在 projects/ 写第一个 CtaTemplate 策略 + BacktestingEngine 回测（主线问题 5 收尾）
- [ ] SimNow 连接实测（环境已就绪；2026-09-24 晚探测 182.254.243.31:30001/30011 拒绝连接、180.168.146.187 超时——待交易时段/换备用前置复测）
- [ ] D 盘原工作区收尾 git，并决定 C/D 两副本主从
- [ ] alpha 可选增强：行业/市值中性化、扣费后组合回测、近三年滚动 RankIC
- [ ] 精读 chart/ui 细节（按需；职责边界已记 [[vnpy-source]]）

## 相关页面
- [[index]] · [[log]] · [[pku-veighna-course]]
