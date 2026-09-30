# AGENTS.md — LLM Wiki Schema (VeighNa 量化交易学习)

本项目是一个基于 llm-wiki.md 模式的个人知识库（wiki），主题为 **基于 VeighNa (vnpy) 的量化交易系统开发**。本文件是 wiki 的 schema：规定目录结构、约定和工作流。任何 LLM 会话在操作本仓库前必须先阅读本文件。

## 目标

- 系统性学习 VeighNa 量化交易框架（架构、模块、网关、策略引擎、回测、CTA/价差/算法等应用）
- 沉淀源码阅读笔记、概念页、实体页，形成互相链接的知识网络
- 同时开发自己的量化程序，代码与学习笔记互相印证

## 目录结构

```
pku_demo/
├── AGENTS.md          # 本文件：schema，LLM 的工作规范
├── llm-wiki.md        # 原始理念文档（只读，勿修改）
├── raw/               # 原始资料层：源码、文档、文章、图片（IMMUTABLE，LLM 只读不写）
│   └── assets/        # 图片附件
├── wiki/              # wiki 层：LLM 生成并维护的 markdown 页面
│   ├── overview.md    # 全局总览：当前知识状态、主线问题、下一步计划
│   ├── index.md       # 内容索引：所有页面的分类目录，每次 ingest 后更新
│   ├── log.md         # 时间日志：append-only，记录 ingest/query/lint/开发事件
│   ├── sources/       # 每个原始资料一页摘要页（文件名与 raw/ 中来源对应）
│   ├── concepts/      # 概念页：事件驱动引擎、OMS、回测撮合、Bar 合成等
│   ├── entities/      # 实体页：vnpy 核心模块（vnpy.event, vnpy.trader, CtaTemplate…）、类与数据结构
│   └── code/          # 自己开发程序的设计笔记、架构决策（代码本身在 projects/）
└── projects/          # 自己开发的量化程序（普通代码目录，git 管理）
```

## 约定

### 页面格式

- 每个页面带 YAML frontmatter：`tags`、`created`、`updated`、必要时 `sources`（引用的 raw 来源列表）。
- 使用 `[[wiki/.../页面名]]` Obsidian 风格双向链接（以 `wiki/` 内相对链接为宜，保持 Obsidian 与 git 均可导航）。
- 引用源码时给出 `raw/` 中的路径及相对行号或函数名，如 `raw/vnpy/trader/engine.py#MainEngine`。
- 中文写作，代码/标识符保留英文。
- 文件名用小写英文加连字符，如 `event-engine.md`。

### log.md 格式

条目使用可 grep 的统一前缀：

```
## [YYYY-MM-DD] ingest | <来源标题>
## [YYYY-MM-DD] query | <问题摘要>
## [YYYY-MM-DD] lint | <检查摘要>
## [YYYY-MM-DD] dev    | <开发内容摘要>
```

### index.md 格式

按分类（sources / concepts / entities / code）列出：链接 + 一行简介 + 更新日期。

## 工作流

### Ingest（摄入资料）

1. 用户把资料放入 `raw/`，说明来源
2. 阅读资料，与用户讨论要点
3. 在 `wiki/sources/` 写摘要页
4. 创建/更新相关 concepts、entities 页面，维护交叉引用
5. 更新 `index.md`、`overview.md`，追加 `log.md`

### Query（查询）

1. 先读 `index.md` 定位相关页面，再深入阅读
2. 综合回答，引用具体 wiki 页面
3. 有价值的分析/对比/连接 → 写回 wiki 成为新页面，并记录到 log

### Lint（健康检查）

定期检查：页面间矛盾、被新资料取代的过时结论、孤儿页、被提及但缺页的概念、缺失的交叉引用。产出修复 + lint 报告页或 log 条目。

### Dev（开发程序）

- 代码放 `projects/<项目名>/`，遵循其内 README/规范
- 架构决策、设计笔记写 `wiki/code/`，与 concepts/entities 互链
- 完成后追加 `## [YYYY-MM-DD] dev | ...` 到 log

## 红线

- `raw/` 与 `llm-wiki.md` 永不修改
- `log.md` 只追加，不删改历史
- 不确定时先读 `overview.md` 和 `index.md` 了解当前状态
