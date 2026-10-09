# Log

## [2026-09-16] init | 初始化 wiki
建立目录结构（raw/、wiki/、projects/），编写 schema（AGENTS.md），创建 overview.md、index.md、log.md。主题：基于 VeighNa 的量化交易系统开发。

## [2026-09-16] ingest | 下载 vnpy / vnpy_ctp / vnpy_ctastrategy 源码快照
从 Gitee（vnpy 官方镜像）下载三个仓库最新分支快照（无 git 历史），放入 raw/：
- raw/vnpy（主框架，main 分支）
- raw/vnpy_ctp（CTP 网关，版本 6.7.11.4）
- raw/vnpy_ctastrategy（CTA 策略应用）
尚未阅读/建页，待首次 ingest 分析。

## [2026-09-16] ingest | 首轮源码精读，建立 wiki 骨架
精读三个仓库核心源码并建页：
- 精读范围：vnpy/event/engine.py、vnpy/trader/{engine,gateway,object,constant,converter,utility,app,event,database,datafeed}.py、vnpy_ctp/gateway/ctp_gateway.py、vnpy_ctastrategy/{base,template,engine,backtracking}.py（全部）、strategies/atr_rsi_strategy.py
- 新建 3 来源页（vnpy/vnpy_ctp/vnpy_ctastrategy 概览）、6 概念页（事件驱动、vt_命名、开平转换、K线合成、停止单、回测模型）、9 实体页（EventEngine、MainEngine、OmsEngine、BaseGateway、数据对象、CtpGateway、CtaEngine、CtaTemplate、BacktestingEngine）
- 更新 index/overview：主线问题 1-4 已解答，标记下一步为环境搭建与首个策略回测
- 未覆盖：ui/chart/rpc/alpha 模块、ctastrategy/ui、ctp api 生成层

## [2026-09-16] dev | ctp_demo：最小化 CTP 底层 API DEMO（SimNow 实测跑通）
projects/ctp_demo/demo.py：直接继承 vnpy_ctp.api 的 MdApi/TdApi，完成 连接/认证/登录 → 订阅 → 行情打印。实测收到 au2612/rb2610 实时推送。踩坑：super().__init__ 必调、subscribeMarketData 单合约签名、摘牌合约订阅无错误回报。笔记 wiki/code/ctp-demo-notes.md。

## [2026-09-16] dev | ctp_breakout_demo：突破触发下单闭环（SimNow 实测成交）
projects/ctp_breakout_demo/demo.py：行情突破阈值 → 限价买开 → 委托/成交回报打印。TdApi 补全 认证→登录→结算单确认 前置链路。实测 au2612 买开 1 手 @938.8 全部成交。踩坑：结算单确认是下单前置、回报为全账户流需按 FrontID_SessionID_OrderRef 过滤、OrderStatus 状态流多次推送。笔记 wiki/code/ctp-breakout-demo-notes.md。

## [2026-09-16] dev | alpha_mining_demo：LLM 驱动自动化因子挖掘 DEMO 基建完成
projects/alpha_mining_demo/：eval_factors.py 基于 vnpy.alpha（AlphaDataset + ts/cs 算子）评估候选因子，train/valid 分段 IC/Rank-IR 指标，数据复用 raw/alpha_researcher/lab/csi300（只读，缓存到 runs/cache/ 绕开 AlphaLab 写 raw/ 的问题）。冒烟测试跑通（round_00 两因子指标合理）。待用户给方向后开始 ≤10 轮迭代。笔记 wiki/code/alpha-mining-demo-notes.md。

## [2026-09-16] dev | alpha_mining_demo：量价共振方向 7 轮自动挖掘完成（早停）
方向"量价共振"，7 轮 134 个候选，全部由 LLM 生成公式、vnpy.alpha 计算、train/valid 分段评估、test 终验。核心发现：量价同动为反向信号。最优单因子 -corr(ret,dvol,5)（train/valid/test RankIR = 0.35/0.40/0.28）；最优组合 A5+0.5·B12+0.7·D10（0.39/0.51/0.28）。第 6-7 轮增益 <1.2% 触发早停。产物 runs/final/{factors.json,report.md}。经验：短窗优先、跨骨架线性加权有效；cs_rank/条件化/平滑均无效。笔记 wiki/code/alpha-mining-demo-notes.md。

## [2026-09-16] dev | alpha_mining_demo：留存因子终局绩效报告（final_report.py，含图表）
新增 projects/alpha_mining_demo/final_report.py：对 3 个留存因子做深度绩效分析（vnpy.alpha 计算因子，pandas 分组统计）——10 分组收益、多空年化/Sharpe/回撤、分年 RankIC、换手率，matplotlib 出图 3×3 张。关键结论：18/18 年 RankIC 为正（含 2021-2024 挖掘期外数据）、分组严格单调、等权零成本多空 Sharpe ~2.5，但日均换手 60%+ 且最大回撤 ~-48%，2021/2023 强度明显衰减。报告 runs/final/performance_report.md。

## [2026-09-16] dev | alpha_mining_demo：绩效报告图表重做（分组累计收益+累积IC）
按用户反馈将 final_report.py 图表改为标准 alpha 研究格式：每因子四图（Q1~Q10 分组累计净值、累积 RankIC 曲线、多空累计收益、分年 RankIC），并新增分段多空绩效表（train LS Sharpe 3.5 → test 1.8，alpha 衰减但仍显著为正）。

## [2026-09-16] dev | 两个 CTP demo 代码质量优化（外部评审采纳）
按外部评审清单修改 ctp_demo 与 ctp_breakout_demo（alpha_mining_demo 有程序在跑，暂不动）：
- demo1（215→208 行）：删 subscribePrivateTopic/PublicTopic（非交易 demo 不需要）、subscribe() 死分支、sys.exit；抽 make_login_req()；FLOW_PATH 统一 Path；订阅列表 set→list；log 统一 flush
- demo2（350→341 行）：删 onRspOrderAction 死回调、`or 0.0`/`or 0` 冗余防护；SYMBOL_EXCHANGE 挪顶部；on_ready → ready_hook 并修正类型 Callable[[], None] | None；同样抽 make_login_req/Path/去 sys.exit
- 取舍理由（含"故意不写的防御代码"）记入 wiki/code/ 两篇笔记的"代码取舍记录"节；两 demo 保持单文件独立（不抽公共模块，diff 即教学材料）
- 验证：py_compile + 离线实例化通过；SimNow 第一套服务器非交易时段（17:22）拒绝 TCP 连接（WinError 10061），无法实测行情，待夜盘（21:00 后）可复验
- alpha_mining_demo 的修改项（删 sys.path.insert/死分支、围栏压缩、import 归位、gitignore 例外、缓存提示）已确认采纳，等程序跑完再执行

## [2026-09-16] dev | 两个 CTP demo 二轮简化（用户要求）
- 移除全部环境变量参数加载，策略配置只以脚本顶部常量存在（验证链路时临时改 TRIGGER_OFFSET 为负值）
- 所有常量/状态字段补行内注释，连续注释块内 # 列对齐（脚本自动对齐 + AST 验证）
- 全部类与方法补一行 docstring（含 4 个 __init__）
- 验证：docstring 覆盖 100%、注释块对齐 0 违例、无 os.environ、py_compile + 离线实例化通过

## [2026-09-16] dev | alpha_mining_demo 终局报告收敛为单脚本（final_report.py 重构）
- 数据流收敛：analyze_factor 一次分组产出两张中间表（日度截面 IC 序列 + 十分组日收益表），分段指标与四张图全部按日期切片派生，消除 2~3 倍重复计算；分段区间与图表底色统一从 config.json 读
- 新增：因子总览表（别名 + 三轮 RankIR + test 多空 Sharpe）、三因子 test 段多空净值对比图（comparison_ls_cum.png，图例带 test RankIR）、多空表下换手×成本估算提示行
- 修复：markdown 围栏 bug（开三闭二）、import 归位顶部、删冗余 sys.path.insert、244 交易日命名常量、matplotlib 中文字体（默认 DejaVu 无 CJK 字形，图例中文变方框）
- 移除 alphalens 路线：删 alphalens_report.py 与 runs/final/alphalens{,_report.md}；show_feature_performance（alphalens tear sheet）交互式设计 + pandas 3.0 需双补丁 + 产出无语义命名，不适合课程；补丁代码存档于 wiki/code/alpha-mining-demo-notes.md
- 验证：完整跑通，performance_report.md 221 行 + 13 张 PNG + perf_detail.json，指标与重构前逐位一致（train RankIR 0.353 / 多空 Sharpe 2.44 等）

## [2026-09-16] dev | alpha_mining_demo eval_factors.py 四项小清理 + report.md 长尾观察补记
- eval_factors.py：删 vestigial sys.path.insert（vnpy 在 site-packages，项目目录无被 import 模块）、删 load_dataset 死分支（lab/csi300/dataset/ 为空，load_dataset 恒 None）及 config.json 的 task_name 字段、```json 围栏剥离压缩为 removeprefix/removesuffix 一行、copy/pandas 函数内 import 归位顶部；顺带删除四个未用 import（Segment/to_datetime/query_by_time/datetime，保留用户加的 eval_test 分支与 config 的 eval_test: true）
- 缓存提示：base_dataset.pkl 命中时打印"修改过区间/成分请删除重建"，消除静默失效陷阱
- 根 .gitignore 加 !projects/**/config.json 例外：config.json（区间/label 定义）纳入 git，runs/ 产物继续忽略
- report.md 增补"test 之后的延续观察（2020.09–2023.12）"节：累积 RankIC 图显示 test 段后约 3 年斜率未见明显衰减，作为更长的样本外旁证（附可交易性未校验的保留意见）；产物索引补终局绩效报告链路
- 验证：py_compile + 围栏解析 4 例冒烟通过；round_00 真实评估跑通，train/valid/test 三段输出数值与 wiki 冒烟记录一致（RankIR -0.248/-0.281）

## [2026-09-16] dev | 累计收益图去复利 artifact（cumprod→cumsum）+ 过拟合核查入 wiki
- 图1（十分组累计）/图3（多空累计）/总览对比图改为 cumsum：原实现把 T+1→T+3 三日前瞻收益逐日复利，漂移重复计入约 3 倍、全组系统性抬升（Q10 达 ~170x），与 alphalens 一日口径组合净值不可比；改后底部组为负、顶部为正、组间序严格单调（即 alphalens quantile returns 形态），图题注明 "3d fwd daily sum"
- 指标表口径未动：ls_stats 内仍 cumprod 计回撤；报告中年化/Sharpe 等收益类数字为 3 日窗口口径（约为 1 日口径的 3 倍），IC/RankIR 不受影响——解读报告数字时注意
- wiki/code/alpha-mining-demo-notes.md 新增"过拟合核查"节：combo 三成分近正交（日均截面 Spearman 0.23/0.07/0.03），过拟合向量是在单一 valid 上 134 候选 × 7 轮迭代选出的权重/窗口参数（选择偏差）；证据 = valid 优势 test 消失（0.51→0.28 打平）+ test 多空 Sharpe 单因子最高（1.81 vs 1.42/1.44）+ 对比图 2017–2019 形态；combo 定位教学对照组，主推 primary
- 验证：重跑 final_report.py，新图形态正常（十分组图 -2.8 ~ +6.8 扇形单调展开，对比图相对排序不变）

## [2026-09-16] query | 因子挖掘如何避免过拟合（基于 alpha_mining_demo 实证）
- 新建 concepts/factor-overfitting.md：核心教训 = 过拟合向量是参数（134 候选 × 7 轮在 488 天 valid 上的选择偏差），不是因子项数；valid 0.51 → test 0.28 被 0.40→0.28 的最简单因子追平
- 防治按四阶段展开：搜索（候选预算、参数平台、复杂度惩罚）/ 验证（嵌套、滚动、Deflated Sharpe、多宇宙）/ 组合（正交成分等权，不调权重——COMBO vs CONS test 1.42 vs 1.44 证明调权无样本外增益）/ 评估（扣费硬约束、分年度、IC 时序稳定性）
- 给出 demo 可落地的 5 条最小改动：预算入 config、参数邻域敏感性表、valid 一分为二、combo 等权、报告标注尝试总次数
- index.md 同步收录

## [2026-09-16] query | 因子过拟合二次分析：四个放大器与噪声锚点
- 复读 alpha-mining-demo-notes 过拟合核查节 + factor-overfitting 概念页，二次 query 深化：在四阶段防治框架上补"放大器与量化锚点"节
- 量化锚点：940 次噪声尝试的最优 |t| ≈ √(2·ln 940) ≈ 3.7；单因子 valid RankIR 0.40 的 t≈8.8（重叠折减后 ≈6）远超上限 → 与 test 存活一致；combo 相对单因子增量 0.11（t≈1.7）在选择噪声射程内 → 与 test 归零一致。判别式：区分绝对优势与增量优势
- 四个放大器：重叠 label 压缩有效样本（488 → ≈244，Hansen–Hodrick）；LLM 逐轮反思 = 自适应相依试验（Bonferroni 低估，宜 White's RC / Romano–Wolf）；valid 是消耗品（跨 run 累积选择偏差，需试验台账）；数据侧隐性抬升（point-in-time、涨跌停可交易性）
- 最小改动清单扩至 8 条（新增：试验台账、Newey–West t 值口径、留存三分之二多数规则）

## [2026-09-16] dev | alpha_mining_demo：反转方向 7 轮自动挖掘完成（早停，含耗时台账）
- 方向"短期反转"，7 轮 106 候选（round 01–02 衔接上一中断会话并补写反思，03–07 本会话执行）；协议事前声明（runs/rev_protocol.md：预算/早停/选择纪律/台账）
- 核心发现：裸 4 日反转 test 多空 Sharpe −0.87，"趋势内回调"结构才有效——REV_TRIPLE = −Δ4×cs_rank(turnover)×amp5×(close>MA20)，三段 RankIR 0.477/0.478/0.205，test 多空 Sharpe 1.57，17/18 年 RankIC 为正；留存 BARE/GATE/TRIPLE 消融链（与量价共振"最简者胜"相反：本次每个结构成分均有样本外增益）
- 过拟合防治全流程落地：平台扫描（邻域全 ±5% 内）、4 次跨轮复跑逐位一致、噪声锚点核验（t≈7.5 ≫ √(2ln106)≈3.2）、简形式纪律（valid 最高 0.490 的平滑变体因增益<噪声不采纳）、试验台账（本会话 106 + 前项目 ~940 次同段 valid）
- 耗时台账（用户要求）：稳态单轮 90–111s（12–15 候选）；ts_decay_linear 候选致 round_03 膨胀至 312s（单算子 ~192s，弃用）；终局报告 59s
- 产物：runs/rev_round_01..07、runs/final/{factors.json,report.md,performance_report.md}；量价共振旧产物归档 runs/final_vp/；wiki/code/alpha-mining-demo-notes.md 增补"第二次实测"节
- 警示：2023–2024 RankIC 衰减至 ~0/−0.13，反转拥挤度上升，regime 依赖强

## [2026-09-16] dev | alpha_mining_demo：动量方向 6 轮挖掘完成（动量证伪 → 共振反向族新最优）
- 方向"动量（价格×成交量共振）"，6 轮 84 候选，协议早停（连续两轮 <5%）；协议事前声明 runs/mom_protocol.md（含证伪友好条款与台账 ~1130 次累计消耗）
- 动量证伪：前两轮 24 候选（裸动量/52 周新高/放量确认/缩量/UVOL/MFI/OBV/水平共振/突破×量/趋势内追涨/vwap 趋势/量冲击/超短共振）valid 全负（−0.011~−0.372）
- 转向共振反向族并产出新最优：PV_ANTI_TRIPLE = −corr(ret,dvol,5)×cs_rank(turnover)×amp5，三段 0.408/0.519/0.344，test 多空 Sharpe 2.53、18/18 年 RankIC 正、2024 +0.103——三方向主推中样本外最稳；活跃度乘法器跨方向迁移成功（+30% valid），超越 VP 项目主推（0.401）
- 结构性发现：趋势门控在共振族有害（与反转族相反，三次独立确认）；换手>量第四次确认；相关型>计数型>分解型
- 纪律：amp 窗 5–20 死平台（0.519–0.530）、5 次跨轮复跑逐位一致、噪声锚点 t≈8.1≫3.2、简形式纪律（amp10 版 +2.1% 不采纳）；耗时台账：单轮 88–118s，6 轮 625s，终局 58s
- 产物：runs/mom_round_01..06、runs/final/{factors.json,report.md,performance_report.md}；归档 final_vp（量价共振）→ final_rev（反转）→ final（本方向）；wiki/code/alpha-mining-demo-notes.md 增补"第三次实测"节

## [2026-09-18] query | alpha 挖掘过拟合：test 段消耗审计与三个剩余盲点（三次 query）
- 复读 [[wiki/code/alpha-mining-demo-notes]] 并核对 runs/final 实测产物与 config，发现选择偏差正向三个新出口转移（纪律未失效，而是被流程成功推到未覆盖处）：
- ① test 段被跨方向比较慢性消耗：三方向终局确认已三次观察同段 2017–2020.08；"PV_ANTI_TRIPLE test 2.53 最稳、2024 +0.103"的排序本身是发生在 test（及 2020.09–2024 分年数据）上的选择 → test 已是第二个 valid。对策 lockbox：2017-01 起数据对一切选择只读、确认不理想不回头改选择；2020.09–2024（lab 数据实际到 2024，config end 仅约束 eval）为仅存未选择样本，留作项目级 lockbox
- ② 无成本 IC 口径：多头日换手 54.8%、单边 0.1% 年化拖累 ~26.7%（58.4%→31.7%），而平台/锚点/简形式纪律全建在无成本 RankIR 上；涨跌停可交易性与 859 只池 point-in-time 未核查 → 留存门槛加三档成本敏感性、剔除一字板
- ③ 因子衰减：PV_ANTI_TRIPLE 分年 RankIC 由 0.05–0.065 降至 2021–2023 的 0.02–0.04，而 train/valid/test 全在 2020.08 前——"样本外"是四年前的市场；"18/18 年为正"含 8 个 train 年，样本外证据应只数 2017 起（8/8）
- 产出：concepts/factor-overfitting.md 增"样本消耗审计与剩余盲点"节（含修订优先级：lockbox > valid 半分/滚动 > 成本门槛 > 池子口径 > Romano–Wolf）；alpha-mining-demo-notes 补交叉引用并 bump updated；index 同步

## [2026-09-18] dev | alpha_mining_demo：跳空方向 4 轮挖掘完成（防过拟合纪律全套升级的首个实测）
- 用户方向"动量 × 开盘跳空"，4 轮 56 候选（预算 80），早停与预算上限同达；协议 runs/gap_protocol.md 事先声明
- 验证设计升级落地（上条 query 审计建议）：弃用消耗 ~1130 次的 2015–16 valid，分段后移 train 08–16 / valid 17–18 / test 19–20.08（挖掘期 eval_test=false 隐藏）/ lockbox 2020.09–24；留存决策冻结（runs/final/retention.md，含三票理由与正交性数字）先于 final_report 运行
- 结论：裸跳空动量证伪（train 无信号）；真发现 = 隔夜-日内分解——反转活在日内、隔夜豁免，主推 GAP_DIFF4_TURN = Σ₄(隔夜−日内)×cs_rank(turnover)，三段 0.372/0.292/0.200；换手乘法器有效、振幅无效（amp 3–10 死平台）；与 PV_ANTI 截面相关 0.32–0.46 但等权组合无增量（+0.013<0.02）→ 定位"新采样+机制细化"；唯一正动量读数 g4_08（跳空不回补弱延续）低于 0.19 门槛仅作注脚
- 终局一次性确认（不回改留存）：test 存活（0.19–0.20，LS Sharpe bare 2.53>turn 1.62）；lockbox 分年 2023 归零、2024 转负（−0.04~−0.07）——反转族跨族拥挤衰减（REV 同衰、PV_ANTI_TRIPLE 独存）；成本三档排序不变，但 0.10% 档 test 净多空 bare 24.1% vs turn 7.1%，多空+扣费口径更支持 bare（主推按冻结纪律仍 turn，分歧如实记录）
- 纪律执行：台账 56/80、噪声锚 √(2ln56)≈2.84 vs 主推折半 t≈4.6、round_03 双跑 md5 逐位一致、PV 基线跨轮复现、简形式拒绝组合与 amp 乘法器
- 耗时：4 轮 eval ~390s（122/105/93/70）+ 复跑 95s + 正交性 28s + 终局 59s×2；踩坑：orthogonality.py 缺 if __name__=="__main__" 保护致 spawn 卡死 16min（关键决策 3 复现）
- 产物：runs/gap_round_01..04、runs/final/{retention.md,factors.json,report.md,performance_report.md,perf_detail.json,charts/}；动量方向产物归档 runs/final_mom/；wiki/code/alpha-mining-demo-notes.md 增"第四次实测"节并更新四方向综合


## [2026-09-19] lint | 全库健康检查：断链/缺页/过时页修复 + 副本缺口披露
- 断链修复 ×3：vnpy-source、vnpy-ctastrategy-source 的 `[[bar-generator-array-manager]]` → `[[bar-synthesis]]`（目标页 09-16 建库时即名为 bar-synthesis，链接从未指对）
- 补缺页：wiki/sources/alpha-researcher.md（存根）——alpha-mining-demo-notes 引用它但一直未建页，且 raw/alpha_researcher 只在 D 盘原工作区
- 过时对齐：overview.md 重写当前状态（7 概念页、3 自研项目、四方向挖掘，主线问题 5 改 🔶）、alpha-mining-demo-notes 架构节补分段演进说明（config 现为 train 08–16/valid 17–18/test 19–20.08 + lockbox）、alpha_mining_demo README（四方向 + 实际 runs 目录 + lab_path 绝对路径注记）；index/notes frontmatter bump
- 产物留存核查：runs/ 仅存跳空（final/）与动量（final_mom/）两方向产物；VP 的 round_00..07/final_vp、REV 的 rev_round_01..07/rev_protocol.md/final_rev 均已不在——D 盘原工作区 git HEAD 中 final_rev 仍可恢复，notes 新增"产物留存现状"表
- 副本缺口披露：当前工作区为 D:/pku_demo（git 仓库）的副本，缺 .git / raw/alpha_researcher / raw/assets；D 盘另有未提交变更（gap 方向产物、final_rev 等旧产物删除）——待用户在 D 盘收尾 git 并定主从
- 清理：删 3 个 __pycache__、2 个 .gitkeep；根 .gitignore 补 `projects/*/runs/`（落实 log 09-16 "runs/ 产物继续忽略"的既定意图，此前仅 *.json/*.pkl 生效，md/png/charts 会入库）

## [2026-09-19] ingest | 北大课程《VeighNa 量化平台 · Agent 时代下的交易系统开发》
- 来源：上层目录课件 PDF（陈晓优，2026-09-18，19 页 PPT），复制为 raw/pku-veighna-course.pdf
- 新建 wiki/sources/pku-veighna-course.md：平台概况、系统架构图（与 event/main/oms/gateway 对应）、工具链（VeighNa Studio / ZCode / Obsidian）、LLM-Wiki 四步、与 projects/ 三个 demo 的路径对照
- 新建概念页 ×2：ai-harness（Model/Harness/Agent + 工具-技能-知识资产包，映射本仓库结构）、factor-expression-ops（截面选股演进、纯数学 vs Polars 表达式、ts/cs 算子清单与 Agent 挖掘表达层关系）
- 交叉引用：factor-overfitting 关联节补 [[factor-expression-ops]]/[[ai-harness]]；event-driven-architecture 相关页面补课程页；alpha-mining-demo-notes 补「相关页面」节
- index 收录 1 来源 + 2 概念；overview 重写（课程路线图对照表、来源页计数 4/概念 9）
- 验证：PDF 文本层完整（19/19 页可提取，非扫描件）；新页 frontmatter/链接格式符合 AGENTS.md 约定

## [2026-09-24] ingest | vnpy / vnpy_ctp / vnpy_ctastrategy 三模块源码二次精读
- 版本核对：raw/ 三模块与 Gitee main 逐文件一致（vnpy 4.4.0 / vnpy_ctp 6.7.11.4 / vnpy_ctastrategy 1.4.1），差异仅 CRLF/LF，无需重下
- 精读范围（相对 09-16 补齐）：event/trader 全部扩展点（database/datafeed/setting/optimize/wechat/logger/app）、ctp 状态机+字段映射+生成层+官方 test、ctastrategy 全文（template/engine/backtesting + 8 示例 + UI/移仓）、**vnpy.alpha 全部**（dataset 表达式引擎/processor/model/lab/strategy 回测）、rpc/chart/ui
- 新建实体页 ×4：alpha-dataset（表达式引擎、register_functions、spawn 陷阱）、alpha-lab（存储布局、价格归一化、成分 filters、信号契约）、optimize-engine（BF/GA、import 副作用）、rpc-module（双通道、pickle、心跳）
- 重写来源页 ×3：补版本、状态机/映射表/示例意图/坑清单（ctp 18 坑、主框架 7 坑、回测失真清单）
- 修正概念/实体：event-driven-architecture 补事件双发与 unregister 陷阱；offset-conversion 补 SHFE/INE CLOSE=平昨语义与 net 分支 volume_left 隐患；cta-template 补 TargetPosTemplate 回测/实盘分叉；factor-expression-ops 补完整算子族并链 alpha-dataset
- index/overview 同步（实体页 9→13）；SimNow 连接线索记入 overview 下一步（当晚端口探测失败详情见会话）

## [2026-09-28] dev | SimNow 账号全链路登录成功（账号值已脱敏）
- 账号：用户自注册 SimNow；投资者代码与密码均走环境变量（`Mai_SimNow_userid` / `Mai_SimNow_password`），源码与仓库不含任何值
- 前置端口规律（重要）：30001/30011 与 40001/40011 随交易时段切换——09-24 夜盘 40001/40011 开、30001/30011 拒；09-28 盘中反过来。两 demo 已改回 30001/30011 并注明夜盘用 40001/40011
- 实测（2026-09-28 10:16）：终端认证成功 → TD 登录成功→ MD 登录并订阅 au2612/au2706/ag2612/rb2610/cu2612 持续推送
- 踩坑：① 首次注册未改密时 TD 报 ErrorID=3「不合法的登录」而 MD 可登录（SimNow 改密规则主要卡交易通道）；② 环境变量名拼写 passward；③ 前置端口按时段切换，写死一组会在另一时段连不上
- 老师示范账号（000300）已替换为用户自己的账号；密码不入库

## [2026-09-28] dev | ctp_open_close_demo：超价开 + 超价平各一次（SimNow 实测成交）
- projects/ctp_open_close_demo/demo.py：超价买开（卖一+5跳）→ 成交回报触发超价卖平（买一-5跳），au2612 一手开平闭环
- 关键：上期所今仓平仓用 CombOffsetFlag='3'(CLOSETODAY)，成交回报 Offset=3 验证通过
- 实测（10:33）：买开成交 913.86/913.98（委托价 913.94/914.08，价格改善），卖平今成交 913.76/913.88；状态流 报单已提交→全部成交
- 踩坑：成交回报无 FrontID/SessionID，多会话并行会看到别人的 TradeID（账户级流水），只能按 OrderRef 范围过滤；盘口 double 价需 round 到最小变动价位
- 笔记 wiki/code/ctp-open-close-demo-notes.md；index 同步

## [2026-09-28] dev | ctp_open_close_demo：超价开 + 超价平各一次（SimNow 实测成交）
- 新建 projects/ctp_open_close_demo/demo.py：超价买开（卖一+5跳）→ 成交回报触发超价卖平（买一-5跳）
- 关键：au 是 SHFE，平今仓用 CombOffsetFlag='3'(CLOSETODAY) 而非 '1'(CLOSE)；成交回报 Offset=3 验证通过
- 实测（10:33）：买开 1 手成交 @913.86（委托 913.94，价格改善）→ 卖平今 1 手成交 @913.76（委托 913.70）；状态流 报单已提交→全部成交
- 踩坑：① 成交回报无 FrontID/SessionID，多会话并行会看到别人的 TradeID（账户级流水），只能按 OrderRef 范围过滤；② 盘口 double 价（913.9200000000001）超价计算后要 round 到最小变动价位
- 笔记 wiki/code/ctp-open-close-demo-notes.md；index 收录

## [2026-09-30] query | 三层交易系统架构系统展开（底层接口 / 中层引擎 / 策略应用）
- 新建 concepts/veighna-three-layers.md：把课件 p.13 三层九块映射到源码实体
- 底层：数据结构标准化（object/constant/vt_*）+ 业务流程标准化（BaseGateway 契约、开平转换、CTP 状态机）
- 中层：事件引擎总线（单线程心脏+双发）+ OMS 缓存 + 交易指令路由（CtaEngine 三张映射表+本地停止单）
- 策略：CTA 单标的已精读；投组/价差仅概念层——vnpy_portfoliostategy / vnpy_spreadtrading 源码未 ingest
- 附「一笔交易的完整生命周期」串三层；建议先打穿 CTA 纵切面再补投组/价差源码
- index 收录

## [2026-09-30] dev | alpha_mining_demo：波动状态与价格位置方向 4 轮挖掘完成（第五方向 VOLPOS）
- 方向「波动状态与价格位置」（延续动量/反转思路的正交新角度），4 轮 51 候选（协议 volpos_protocol.md）
- 依赖修复：补装 polars / alphalens-reloaded / pyarrow（raw/alpha_researcher 不在本机，用 runs/cache/base_dataset.pkl 234MB 缓存跑通）
- 核心发现：裸位置/波动无 alpha；真发现 = REV4_TURN_HIGHPOS（−Δ₄×换手×高位权重 pos20）train/valid/test 0.486/0.284/0.154；位置符号确认高位≫低位（0.284 vs 0.214）；简形式 REV4_TURN 0.239
- 终局：test 存活但衰减（0.154<0.19）；分年 16/18 正但 2024 −0.102（反转族拥挤衰减第三次确认）；多头换手 67.7% 扣费后年化 73%→40%
- 复跑 highpos 逐位一致；rev/pos 窗均为平台；四件套 amp 增强 valid 0.309 作观察项
- 产物 runs/volpos_round_01..04 + runs/final（gap 归档至 final_gap/）；wiki/code/alpha-mining-demo-notes.md 增「第五次实测」节
- 台账 volpos 51/80；同段 valid 累计 gap 56 + volpos 51 = 107

## [2026-09-30] dev | 项目整理并发布 GitHub
- 清理：删 23 个 wiki 备份、demo 备份、__pycache__、CTP flow 流文件目录
- 补足：顶层 README.md（学习主线/快速开始/复现指引）；.gitignore 重写（raw/ 与 runs/cache 224MB pkl 排除，挖掘报告/协议/笔记/图表入库）；index 链入 VOLPOS 报告
- 发布：git init + 初始提交 68513df（165 文件）→ 公开仓库 https://github.com/Mai-Xu/quantllm_hw1_alpha
- 认证：winget 安装 gh 2.102.0；网络走本机代理 127.0.0.1:7890；账号 Mai-Xu（HTTPS 协议）
- 机密核查：入库文件无密码字面量；SimNow 密码仍走环境变量 Mai_SimNow_passward

## [2026-10-09] dev | 按评审反馈加固：可验证开平闭环 + 凭据清理出源码与历史

针对「开平代码只能证明平仓单已发出」与「源码/历史含 UserID」两项反馈的整改：

- **交易闭环重写**（projects/ctp_open_close_demo/demo.py）：
  1) 开仓意图持久化——发单前写 `evidence/journal_*.jsonl`，崩溃可复原
  2) 归属收紧——委托按 FrontID+SessionID+登记 OrderRef 三段匹配；成交额外要求 OrderSysID 自洽
     且方向一致，他会话成交**明确拒收并计数**（早期版本用 OrderRef 范围比较，不严密）
  3) 平仓以**归属后成交数量**判定，不再以「已发出」判定
  4) 终态校验——`reqQryInvestorPosition` 查持仓归零 + 本会话无活动委托
  5) fail-closed——断线/拒单/超时/未收敛一律非 0 退出码（0/2/3/4/5/6/7 语义见 README）
- **离线测试** 17 例（tests/test_offline.py，不联网）：三段归属、OrderSysID 自洽与他会话拒收、
  方向一致性、终态校验四条失败路径、脱敏、缺配置 fail-closed
- **凭据清理**：三个 demo 与 log 中的 InvestorID 全部移出，改为环境变量
  （`Mai_SimNow_userid` / `Mai_SimNow_password`）；新增无值 `config.sample.json`；
  去掉注册表兜底（来源明确、可离线测试）
- **git 历史重写**：`filter-branch` 清除全部历史中的 ID 与密码字面量，删除 refs/original 与 reflog 后 gc；
  复核 `git log --all -S` 三个敏感串均为空
- **实测**：2026-10-09 12:42 于午间休市时段运行，程序在无行情下按预期以退出码 5 fail-closed 收场
  （非误报成功），证据 `evidence/journal_20261009_124221.jsonl`（账号字段已脱敏为 `******`）
- 待办：下午/夜盘时段复跑以取得 0 退出码的完整闭环证据；因子研究侧另行补 HAC/成本等

## [2026-10-09] dev | 因子研究侧整改：冻结清单 / 试验台账 / 真实摩擦 / 可复现

按评审「因子研究」「真实摩擦」「可复现」三项反馈的整改：

- **冻结清单**（`runs/final/freeze.md` + `data_fingerprint.json`）：固化数据指纹
  （SHA-256 `4248f100…1465`，234,857,524 字节，2,668,723 行，819 标的）、股票池与存续区间、
  复权口径**未核实的如实声明**、信号（T 日收盘）与成交（T+1 收盘）时点、区间与停止规则；
  并给出「协议早于候选、留存决策早于终局报告」的文件时间戳证据
- **试验台账**（`runs/attempt_ledger.md`）：28 轮约 431 个候选全量登记，含 MOM 证伪方向与
  GAP/VOLPOS 的全部证伪支线；如实披露 VP/REV 两方向轮次产物已丢失
- **真实摩擦**（`friction_report.py` → `friction_report.md`）：
  毛/净收益（三档费用：双边佣金 + 印花税 + 过户费 + 滑点）、换手、最大回撤、容量；
  建仓日剔除停牌与涨停；**融券约束**明确（A 股个股不可做空 → 多头为准，多空仅参照）；
  **重叠收益**用 HAC(Newey–West) t 值与平稳区块 bootstrap 置信区间，
  年化/回撤改用**非重叠 3 日块**（修正三日前瞻收益重复计入的老问题）
- **关键结论修正**：多头组扣费后年化为负（base 情景 −29.6%，bootstrap CI 全负），
  多空毛 Sharpe 1.40；test 段 RankIC t≈2.43、CI 下沿贴近 0 —— 与「IC ≠ 可落袋收益」一致
- **可复现**：`requirements.lock.txt` + `pip-freeze.txt`（300 包精确版本）、
  `REPRODUCE.md`（实际命令、真实退出码含失败案例、脱敏日志、离线测试）；
  明确「`py_compile` 通过 ≠ 运行成功」

## [2026-10-09] dev | 交易闭环取得退出码 0 的可复核证据

- 盘中 13:33 运行 `ctp_open_close_demo/demo.py`：**退出码 0，闭环验证 PASS**
- 证据链（`evidence/journal_20261009_133314.jsonl`，账号字段脱敏 `******`）：
  意图持久化 → OrderSysID(398916/398924) 自洽归属 → 开仓成交 908.66 → 平今成交 908.74（offset=3）
  → 持仓查询 au2612 position=0 → verify_result passed
- 对照：同日 12:42 午间休市运行以退出码 5 fail-closed 收场（无行情时不误报成功）
