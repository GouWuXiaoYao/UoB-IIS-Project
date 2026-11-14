# SPEC — AI 辅助遗留代码重构中的交互治理：实验程序规格

| 项目 | 值 |
|---|---|
| 文档版本 | 1.0（初版，待评审） |
| 状态 | Draft — 第 6 节 8 条未决问题拍板后转 Frozen |
| 研究对象 | "架构与约束评估卡（Assessment Card）+ 强制确认清单（Mandatory Confirmation Checklist）"的前置治理门控 |
| 上游文档 | `A1 Literature Review 3138100 V1.docx`（724 词正文 + 354 词参考文献）、`Assignment 2 Course scoring instructions.docx`（5 页） |
| 下游文档 | `docs/PLAN.md`（实现方案）、`docs/rubric-mapping.md`（需求→证据追踪） |
| 交付路径 | 本文件只定义"做什么、怎么算通过"，不含实现代码 |

---

## 0. 依据与标注约定

### 0.1 标注记号

全文每个关键论断都带来源标记，便于评审时逐条回溯：

| 记号 | 含义 |
|---|---|
| `[A1]` | 直接来自 A1 文献综述的原文表述 |
| `[A2]` | 直接来自课程评分说明的原文表述（唯一"符合要求"的判据） |
| `[REF]` | 来自工作区参考资料（`参考代码库/` 的课程 lab 代码、`DSH-实验程序工作流.md` 项目约定） |
| `[假设]` | **本文推导**，课程文档未写；依据见第 7 节 |
| `[待定]` | 依赖第 6 节你的拍板，未定前不写死 |

### 0.2 必须原样遵守的硬事实

**A2 字数与截断规则** `[A2]`：

- Abstract ≤ 300 词；Design rationale & project explanation 约 1,000 词、**上限 1,100 词**。
- 正文 + 摘要合计 ≤ 1,400 词；**超过 1,300 计数词后停止阅读**。
- 不计入：figures、diagrams、storyboards 及其短标签/图注；references、仓库链接、README 内容。
- 首页写总词数；rationale 表格内文字计入总词数。
- 禁止把解释性段落塞进图表来规避字数上限。

**A2 四项评分** `[A2]`：Design reasoning and scope **/30**、Developed interaction **/30**、Architecture and technical reasoning **/20**、Development evidence and authorship **/20**。

**A2 规定报告必须包含** `[A2]`：Abstract、Design rationale（含"A possible rationale-table layout"四列：Design choice / Why it suits the problem / Supporting evidence or reference / Status）、System diagram（组件、连接、信息或控制流，**含 AI 行为**，并标出 implemented / simulated / planned）、Storyboards and illustrated interaction（**2–3 个**使用实例，含用户动作、系统响应、反馈或控制）、Repository and development evidence（公开 GitHub + README + 提交的 commit 或 release + 指向开发记录）、References。

**A2 规定 README 必须说明** `[A2]`：Project status（做了什么、能跑/被模拟/未完成）、Technology stack（含所用 AI 工具或模型，各自作用与未定选择）、Running or inspecting the work（依赖与启动）、Development record（重要变更、为什么、检查了什么、相关 commit）、AI assistance（用了什么工具、让它做什么、你怎么改的、怎么验证的）、Additional files。README 要短，顶部写 prose 词数，**禁止提交 API key**。

**A2 对"developed work"的界定** `[A2]`：可以是 implementation、prototype、simulation，或已开发屏幕/状态的 walkthrough；占位物必须标注并说明代表什么；**视觉精致度与功能数量不是重点**；"只列 planned 功能不等于 developed work"。

**A2 四档描述语（2026-11-14 更新版 docx，第 5–6 页）** `[A2]`：四项标准各有四档——Convincingly demonstrated / Demonstrated / Partly demonstrated / Not yet demonstrated。其中三条对本规格有强制力，不是风格建议：

1. **不得把 planned 或 simulated 说成 implemented。** `Developed interaction` 的 "Not yet demonstrated" 档原文：*"materially misrepresents planned or simulated behaviour as implemented"*。这是红线。
2. **必须显式区分 developed 与 planned，并解释 scope 取舍。** `Design reasoning and scope` 的 "Convincingly" 档要求 *"clearly identifies which choices concern developed work and which concern planned features"*，且要求 justify *"compromises in scope"*。
3. **必须区分 original / reused / assisted。** `Development evidence and authorship` 的 "Convincingly" 档要求 *"distinguishes original, reused and assisted work, with relevant examples of reviewing and adapting AI output"*。

其余可执行的要求：`Architecture` 的 "Convincingly" 档要求图与解释说明"组件、流、依赖如何支撑交互，**含智能行为**"，且技术选择与边界与提交物一致；该维度 "Partly" 档的失分点是"只列组件与技术而不解释连接或作用、差异未解释"。

> 仍缺的只有**档位 → 分值的映射**：docx 只给每项满分（/30、/30、/20、/20），没给四档各占多少分 `[假设]` A-15。因此本规格按"四档描述语是否被满足"验收，**不预测分数**。

### 0.3 本规格对"实验程序"的界定

"实验程序"= 以下四件东西合起来，缺一不可验收：

1. **可运行的治理原型**（M1–M6）：能把"生成前必须先看影响、必须勾确认"这件事真正做出来——这是 A2 `Developed interaction /30` 的落点。
2. **可复现的实验编排**（M2、M3、M7）：条件、任务、顺序、模型全部由配置与预生成 schedule 决定，任何一次运行都能重放。
3. **可计算的结构化日志**（M7）：第 4 节的 JSONL 是唯一数据源，第 5 节所有指标必须能只从日志算出。
4. **可追溯的分析管线**（M8、M9，按 Q8 为 SIM/PLAN）：一条命令从 `runs/` 得到结果表的**能力**要有，但不作为本期交付的主证据。

A2 本身**不要求**统计检验或人类被试 `[A2]`（全文未出现 experiment / statistics / participant 要求）。实验设计来自 A1 §4 的贡献点与局限 `[A1]`。第 6 节 Q1/Q2/Q4/Q5/Q8 已于 2026-11-14 拍板（见 6.0）：**做治理原型 + 作者自测，不做人类研究；N=10 设计只留档；语料自建 6 个种子仓库；不实现 C2**。因此本规格的**可验收部分**是 M1/M3/M4/M5/M6/M7/M8/M11 的 MUST 验收；M2 为 SIM，M9 为 PLAN，M10 为 N/A。H1–H7 保留为计划假设，**无观测数据**。

---

## 1. 研究问题、假设与变量

### 1.1 从 A1 的缺口推导 RQ（推导链，务必保留）

A1 的判断链 `[A1]`：

1. 遗留（brownfield）重构中，AI 把开发者拖进"prompt–response–implement"循环，短期提速但损害概念理解；Shihab 等报告 **34.9% 更快**但理解受损。
2. 无治理时短期效率收益伴随**技术债高 37%、安全漏洞高 41%**（Roy 等，β=0.48）。
3. 现有 XAI 只在**事后** code review 阶段校准信任（Gao 等，中等解释深度同意率 89.22%；更深解释触发审视但不增加时间）。
4. 两个缺口：**(i) 缺乏宏观架构意图映射**——现有方法停留在输出或 token 级，不映射到仓库级依赖；**(ii) 缺乏前置治理**——没有在生成之前挡住"盲 prompt-response"的上游防线。
5. 贡献提案：生成前强制输出结构化的 **"Architecture and Constraint Assessment Card"**（影响说明 + 复选框），**只有显式确认后才授权生成代码**（例如确认全局变量、跨模块接口契约）。
6. 作者自陈的两个局限：**(a) 交互摩擦**降低例行任务速度；**(b) 缺乏按任务复杂度自适应粒度时，高频交互导致 "Confirmation Fatigue"**，退化为机械勾选，反而削弱审视。

RQ 直接把 5 与 6 变成可测命题：有效性（5 是否成立）、代价（6a）、机制（是校准还是单纯变慢）、理解（1 的负面是否被抵消）、疲劳（6b）。

### 1.2 研究问题

| ID | 研究问题 | 源自 |
|---|---|---|
| **RQ1**（安全有效性） | 在遗留代码重构任务中，加入"评估卡 + 强制确认清单"的前置门控，相对于无门控的 baseline，是否降低**未审查即接受**的比例与**下游质量风险**（隐藏测试逃逸缺陷、技术债增量、安全告警增量）？ | `[A1]` §3 缺口 ii、§4 提案 |
| **RQ2**（代价） | 该门控对**任务完成时间**与**主观摩擦**（认知负荷）的代价有多大？代价是否集中在例行/低复杂度任务上？ | `[A1]` §4 局限 a |
| **RQ3**（机制） | 门控是否提升**信任校准质量**——即"接受/拒绝"决策对建议真实正确性的**判别力**上升，而不是靠整体少接受（过度不信任）换来的表面安全？ | `[A1]` §2 Camp C、§4 |
| **RQ4**（理解） | 门控是否改善重构者对**受影响模块架构**的理解（跨模块契约、全局状态、副作用）？ | `[A1]` §2 Camp B（理解受损） |
| **RQ5**（疲劳与粒度） | 在治理条件下，确认行为是否随会话推进**退化为机械勾选**？按任务复杂度**自适应粒度**能否在不牺牲 RQ1 收益的前提下降低 RQ2 代价？ | `[A1]` §4 局限 b |

### 1.3 假设

方向性假设，均以"同参与者内配对"为检验框架（见 2.3）。H7 为条件假设，且按 Q5 拍板**不实现 C2**，故 H7 只作 planned 论证对象。

> **状态：全部为计划假设（PLAN）。** 按 6.0 的 Q1/Q2 拍板，本期不采集人类数据，因此 H1–H7 没有观测值，只作为预注册设计与后续研究的接口。报告中不得出现"实验表明"式表述（见 A-16 与 8.1b）。

| ID | 假设（方向） | 操作化读数 | 对应 RQ |
|---|---|---|---|
| **H1** | 治理条件 C1 的**盲接受率 OTI 低于** baseline C0 | `OTI = 盲接受建议数 / 建议动作总数`（定义见 1.5） | RQ1 |
| **H2** | C1 的**逃逸缺陷率低于** C0，且**技术债增量、安全告警增量更低** | `task_end.tests_pass` 为假即逃逸；`debt_delta`、`vuln_delta` | RQ1 |
| **H3** | C1 的**任务完成时间长于** C0，**主观摩擦更高**（预期代价，方向明确） | `task_end.elapsed_ms`；NASA-TLX mental demand / effort / frustration | RQ2 |
| **H4** | C1 的**校准判别力 AUC 高于** C0，且该提升**不能**由"接受率整体下降"完全解释 | 每参与者 AUC(accept 决策 vs 建议真实正确性)；同时报告接受率 | RQ3 |
| **H5** | C1 的**理解测验得分高于** C0 | `comprehension_item.correct` 的均值 | RQ4 |
| **H6** | C1 内部**存在疲劳趋势**：确认延迟随 `task_index` 下降、勾选交互数随 `task_index` 下降 | 会话内 `gate_latency_ms` 与 `card_item_toggle` 计数对 `task_index` 的斜率 | RQ5 |
| **H7** | （**PLAN，不实现**）自适应粒度 C2 相对 C1 **降低时间与摩擦**，且 OTI **非劣**于 C1 | C2 vs C1 的 `elapsed_ms`、TLX、OTI | RQ5 |

零假设 H0-1…H0-7 分别为上述各量的无差异/无非劣。H6 是"存在性"假设，其零假设为斜率 ≥ 0（无退化）`[假设]`。

> 为什么把 H3 写成"预期代价"而不是"无差异" `[假设]`：A1 §4 明确承认"强制前置确认会引入交互摩擦、略降低例行任务速度"。若数据显示无代价，反而说明门控没有真正生效（门被绕过），需回查 `gate_decision.blocked` 日志。**H3 因此兼具操纵检查（manipulation check）功能**。

### 1.4 变量

**自变量（IV）**

| 变量 | 水平 | 类型 | 说明 |
|---|---|---|---|
| IV1 条件 | C0 baseline / C1 governance（C2 adaptive 仅 PLAN，不进入设计，见 Q5） | 被试内，配对 | 见 2.1 |
| IV2 任务复杂度 | 低 / 中 / 高（3 层） | 被试内，分层因子 | 用于检验 RQ2 的"代价是否集中在低复杂度任务" |
| IV3 会话内任务序号 | 0 / 1 | 被试内，时间因子 | 疲劳与学习效应 |

**因变量（DV）**

| 类别 | 指标 | 日志来源 |
|---|---|---|
| 主 DV | 盲接受率 OTI、逃逸缺陷率、任务完成时间 | 4.3 / 5.2 |
| 次 DV（质量） | 技术债增量、安全告警增量、隐藏测试失败数 | `task_end` |
| 次 DV（校准） | 接受率、编辑率、拒绝率、判别力 AUC、解释展开率 | `suggestion_action`、`explanation_open`、`suggestion_scored` |
| 次 DV（主观） | NASA-TLX 三维、SUS、单题摩擦评分 | `survey_response` |
| 次 DV（理解） | 理解测验正确率 | `comprehension_item` |
| 次 DV（过程） | 确认延迟、勾选交互数、机械确认率、门控拦截次数 | `gate_decision`、`card_item_toggle` |

**控制变量（测量并记录，尽量固定）**

- 参与者：编程年限（`prior_years`）、LLM 工具使用频率（`llm_freq`）、该遗留仓库语言的熟悉度（`lang_familiarity`，1–5）。
- 材料：任务对（`pair_id` 匹配难度）、任务呈现顺序（ABBA 平衡）。
- 系统：模型 ID 与版本、温度、seed、prompt 模板版本、`app_version`—全部来自配置并写入日志，代码内不得出现魔法数字 `[REF]`。
- 环境：操作系统大类、浏览器/IDE、单次会话时长上限、是否允许外部搜索（默认禁止）。
- 评分侧：隐藏测试套件与静态规则集版本固定（`scorer_version`），无人工评分者，故无评分者效应。

**混淆变量（只能测量、不能完全控制，需在报告中明说）**

- 学习效应：第二个任务受益于第一个任务（由 ABBA + 独立任务对缓解，不能消除）。
- 疲劳：会话内后段表现下降（IV3 直接建模）。
- 新奇效应：首次使用治理界面。
- 实现者即研究者：无法双盲（见 2.6）。
- 任务对之间仍可能不等价（`[假设]` A-4 给出可比性判据）。

### 1.5 关键量的精确定义（先定义，后测量）

| 量 | 定义 | 备注 |
|---|---|---|
| **建议动作总数** | 具备 `suggestion_action` 事件的不同 `suggestion_id` 计数 | 重试产生的重复建议按 `suggestion_id` 去重 |
| **盲接受** | 该建议的 `action = accept` **且** `explanation_open` 无对应记录（或 `accepted_after_gate = false`）**且** `review_dwell_ms < τ_review` | `τ_review` 默认 **2000 ms** `[假设]` A-3，需做 1s/2s/5s 敏感性分析 |
| **OTI** | `盲接受数 / 建议动作总数`，范围 0–1，越低越安全 | 主 DV |
| **逃逸缺陷** | `task_end` 时对**隐藏**测试套件运行后 `tests_pass = false` | 隐藏测试对参与者不可见，防针对性修改 |
| **技术债增量** | 提交后规则集命中数 − 任务开始时命中数（同一规则集版本） | 计数型，偏态 |
| **安全告警增量** | 同上，安全规则子集（硬编码密钥、`eval`/`exec`、不安全反序列化、字符串拼接 SQL） | 计数型 |
| **判别力 AUC** | 以 `accept` 为 1、`edit`/`reject` 为 0 作为预测，以 `suggestion_scored.is_correct` 为真值，计算每参与者 ROC 曲线下面积 | 单类别时缺失，见 5.3 |
| **机械确认** | 一次 `gate_decision` 的 `confirmed = true`，且其所有 `card_item_toggle` 的 `dwell_ms` 中位数 < 800 ms `[假设]` A-6，且 `n_confirmed = n_required` 无回退 | 疲劳的行为代理 |
| **理解测验得分** | 会话末对"本任务受影响模块"的 5 题选择题正确率 `[假设]` A-5 | 只考架构/契约，不考语法 |

---

## 2. 实验条件、随机化与配对

> **本节状态：计划协议（PLAN）+ 一项已执行的技术演示。** 2.1–2.6 描述的是**若做真人研究**的完整协议，本期不执行（Q1）。本期真正执行的是其中最小的可演示部分：用同一份录制数据分别回放 C0 直通与 C1 门控，证明"门确实拦截、勾选确实解锁"这条因果链；这一步属于技术验收，不产生 H1–H7 的数据。

### 2.1 条件定义

三组共享**同一套 UI 骨架、同一任务集、同一日志接口**，只在"生成前是否设门"上不同——这是保证可比性的核心约束。

| 维度 | **C0 baseline** | **C1 governance** | **C2 adaptive（PLAN，不实现）** |
|---|---|---|---|
| 交互形态 | 输入重构需求 → 直接得到完整建议（diff + 说明文字） | 输入需求 → 先得到**评估卡**（影响说明 + 复选框）→ 勾满必需项 → 才解锁生成 | 同 C1，但卡的条目数与必需项按任务复杂度/风险等级自动缩放 |
| 生成前是否阻塞 | 否 | **是**（`gate_decision.blocked` 可复现） | 是 |
| 建议内容可见性 | 立即显示 diff | 确认前**只显示影响与契约，不显示 diff** | 同 C1 |
| 治理粒度 | 无 | 固定：影响集全量入卡 | 自适应：低风险任务只出跨模块契约项，高风险任务出全量 |
| 是否允许绕过 | — | 不允许（唯一入口） | 不允许 |
| 日志路径 | 同 M7，同 schema | 同 M7，同 schema | 同 M7，同 schema |

> C0 必须是"同一系统的门被设为直通"，**不是另一个产品** `[假设]` A-7。理由：若 C0 用真实商用 copilot 而 C1 用自研原型，任何差异都无法归因于治理本身（界面、延迟、建议质量全部混淆）。A1 引用的 Peng 等、Shihab 等均为"同一工具 vs 无工具"或"同一界面不同条件"，支持这一做法。

> **C2 的状态（Q5，2026-11-14 拍板）：不实现。** 上表保留 C2 列，是因为它承担两个用途：一是说明设计空间（固定粒度只是自适应粒度的特例，这一取舍要在 rationale 里论证）；二是满足 A2 "清楚区分哪些是 developed、哪些是 planned" 的要求 `[A2]`。**但 C2 不得出现在任何 implemented 的 storyboard 或 demo 里**，也不产生数据；H7 因而不被检验（见 5.2 表注）。

### 2.2 任务集与分层

- 规模（Q4 拍板：**自建**，不用真实开源仓库）：**6 个自建种子仓库 = 6 个任务实例 = 3 个难度层 × 2 个实例**；同层内的两个实例互为"等价实例"（同一 `pair_id`），共 3 对。选自建的理由：只有自建才能同时提供 **gold patch + 隐藏测试 + 影响集标签**（M1 验收标准 2 与 M8 可判分性都依赖它们）；真实开源仓库没有 gold，无法自动判分。代价是外部效度低，须写入 2.6 的限制。
- 每个实例是一个可离线运行的小型遗留 Python 仓库（约 200–600 行、3–6 个模块），植入已知坏味道：全局单例/全局可变状态、跨模块隐式契约、重复逻辑、裸 `except`。
- 每个实例附带：需求说明（refactor intent）、**隐藏测试套件**、**gold patch**、**影响集标签**（该任务真正的全局变量与跨模块契约清单）。
- 参与者每次会话只做 **2 个任务**（每条件 1 个，来自同一 `pair_id`），以确保配对可比且会话控制在 90 分钟内 `[假设]` A-8。

### 2.3 设计与配对

**设计**：被试内（within-subject）**2 条件（C0 / C1）× 2 顺序（AB / BA）交叉**，配对单元 = 参与者。C2 不进入设计（Q5）。

- **配对方式 1（统计配对）**：同一参与者的 C0 与 C1 观测成对出现，用配对检验消除个体差异（编程水平差异通常是最大方差来源）。
- **配对方式 2（材料配对）**：同一 `pair_id` 的两个实例在"需改动文件数、需修改函数数、隐藏测试数"上差异 ≤ 20% `[假设]` A-4，一个分给 C0、一个分给 C1。
- **配对方式 3（顺序平衡）**：条件顺序按 **ABBA** 在参与者块内平衡；任务对按 PAIR-01→02→03 循环轮换。每位参与者的两任务顺序随机（由 schedule 固定，非现场决定）。

**为什么用被试内** `[假设]`：A1 引用的两项最贴近本研究的研究（Shihab 等 N=10、Gao 等 N=34）都是 within-subjects。被试内能用较小 N 得到可检验的配对比较，这对课程项目是唯一现实的选择；代价是学习效应与疲劳，用 ABBA + IV3 建模处理。

**样本分配单位**：`(participant, task)` 观测为分析单位；参与者为随机效应/配对单位。

### 2.4 随机化程序

1. 数据收集前生成 **`randomization_schedule.json`**：`block size = 4`（每块含 2 个 AB、2 个 BA 顺序），PAIR 轮换预排到每个 slot，条件标签预绑定到具体实例 ID。
2. 参与者按到达顺序取下一个未使用 slot（**简单随机化于块内**，不做事后调整）。schedule 一经生成即冻结并提交到仓库，作为可复现证据。
3. 会话运行时**只读 schedule**，不做现场随机——避免实验者选择性分配（这是最容易被质疑的偏倚点，必须用机制消除）。
4. schedule 生成需可复现：给定 `seed` 与 `N` 输出确定的分配表；附录保留生成参数。
5. 若中途有人退出，其 slot 不复用（保持块内平衡），并在日志 `withdrawn = true` 中记录。

> 验收要求（写进 M2）：对同一 schedule 做 N=100 次"虚拟参与者"模拟分配，两条件出现次数必须均衡（卡方 p > 0.05），且每个 PAIR 在两个条件下都出现过。

### 2.5 单次会话流程（时间线）

| 阶段 | 时长 | 参与者做什么 | 系统产物（日志事件） |
|---|---|---|---|
| 0 同意与筛选 | 5 min | 阅读知情同意、勾选、填人口学与经验问卷 | `session_start`（含 `consent_given`） |
| 1 环境熟悉 | 10 min | 在**非实验仓库**上完整走一遍界面（两种条件各 2 分钟） | `session_start` 后续的 `prompt_submit`（标记 `task_id = TUTORIAL`，不计入分析） |
| 2 任务 1 | ≤ 30 min | 读需求 → 提问 → （C1：看卡、勾选、确认）→ 审阅建议 → 接受/编辑/拒绝 → 自测 → 提交 | `prompt_submit`…`task_end` |
| 3 缓冲 + 任务 1 后测 | 5 min | NASA-TLX（三维）、SUS、5 题理解测验 | `survey_response`、`comprehension_item` |
| 4 任务 2 | ≤ 30 min | 同上，另一条件 | 同上 |
| 5 任务 2 后测 | 5 min | 同上 + 开放题（对门控的主观评价） | `survey_response` |
| 6 收尾 | 2 min | 可选半结构访谈（录音另存，不入日志） | `session_end` |

超时处理：任务 1 / 任务 2 各 30 min 硬上限，超时自动收尾并写 `timeout = true`（该观测仍保留，按 5.3 处理）。

### 2.6 偏倚控制与"能做到/做不到"的诚实边界

**做到的**：预生成 schedule 消除分配偏倚；隐藏测试防针对性修改；单一日志 schema 保证两组可比；预注册分析计划（5.2 表）防止事后挑指标；`τ_review` 等阈值做敏感性分析；自动评估器（M8）替代人工评分，消除评分者效应。

**做不到的**（必须写进 A2 报告的限制）：实现者即研究者，无法双盲；同一位研究者也不可能不知道条件，因此**不能声称"消除期望效应"**；被试多为同学便利样本，外部效度有限；语料为自建的 6 个种子仓库（Q4），坏味道系人为植入，真实遗留系统的混乱程度未被覆盖；单次会话时长短，无法观察长期技术债演化，只能用**短线代理指标**（规则集计数）代替。

---

## 3. 软件模块清单

### 3.0 范围与状态标注

对齐 A2 "implemented / simulated / planned" 的要求 `[A2]`，每个模块标注状态：

| 状态 | 含义 | A2 要求 |
|---|---|---|
| **MUST**（implemented） | 必须真正实现并通过验收 | 报告中标 implemented，需 storyboard 演示 |
| **SIM**（simulated） | 用固定/录制数据替代真实后端，接口与日志真实 | 报告中标 simulated，须说明替代了什么 |
| **PLAN**（planned） | 只在设计中出现，不实现 | 报告中标 planned，不得计入 developed work |
| **N/A**（不适用） | 因 Q1 拍板不做真人研究而不实现 | 只作为"若做真人研究会怎么做"的设计说明出现，同样**不得**说成 implemented |

**本期交付集（按 2026-11-14 Q8 拍板）**：

| 模块 | 状态 | 说明 |
|---|---|---|
| M1、M3、M4、M5、M6、M7、M8、M11 | **MUST（implemented）** | 构成"任务 → 评估卡 → 勾选 → 门控 → 生成 → 审阅 → 日志"闭环，是 `Developed interaction /30` 的落点；M3 走 live + replay，M8 用六类 JSON 规则集 |
| M2 | **SIM（simulated）** | 由作者自测 + 录制回放驱动，不做真人会话 |
| M9 | **PLAN（planned）** | 分析管线只留接口约定，不接数据 |
| M10 | **N/A** | Q1 决定不招募真人，合规流程不实现 |

> 闭环的演示方式因此改变：不再是"被试走一遍"，而是**作者自测 + 录制回放**——用同一份录制数据分别以 C0 直通与 C1 门控回放，展示两种交互路径的差别。报告里必须写明这是 simulated `[A2]`（见 A2 红线 1）。

---

### M1 · 任务语料库与种子遗留仓库 — **MUST**

- **目的**：提供同一难度层次上可互换、可自动判分的实验材料。按 Q4 拍板为**自建**，不使用真实开源仓库。
- **输入**：任务定义文件（每个实例一条），字段包含 `task_id`、`pair_id`、`stratum`、`repo_path`、`intent_text`、`hidden_tests_path`、`gold_patch_path`、`impact_label_set`（全局变量与跨模块契约清单）。
- **输出**：6 个可离线运行的仓库快照 + 6 套隐藏测试 + 6 个 gold patch + 6 份影响集标签；一份 `tasks/index.json`。
- **依赖**：仅 `pytest`；不得联网；不得引入运行时服务。
- **验收标准**：
  1. 每个仓库在初始状态下 `pytest -q` 结果被**显式记录**为基线（预期为失败，失败原因须是"重构未做"，不是环境缺依赖）。
  2. 应用对应 gold patch 后隐藏测试**全绿**——这一条必须对 6/6 实例成立，否则该实例作废。
  3. 每个实例至少含 **1 个全局可变状态**与 **1 个跨模块隐式契约**，且二者都出现在 `impact_label_set` 中。
  4. 同一 `pair_id` 的两实例在"改动文件数 / 需修改函数数 / 隐藏测试数"上两两差异 ≤ 20%。
  5. 仓库内不得出现任何指向答案的注释、TODO 或测试名泄漏（自动扫描 `gold`/`fix`/`solution` 等词）。

---

### M2 · 会话编排器 — **SIM**（作者自测 + 录制回放；真人会话版本为 PLAN）

- **目的**：把"谁、按什么顺序、做哪个任务、在哪个条件"变成不可现场更改的数据。
- **输入**：`randomization_schedule.json`、`participant_id`（伪名）、同意记录、`session_config`（时间上限、条件集合）。
- **输出**：`session_id`、任务序列（含每任务的 `condition` / `task_id` / `task_index`）、会话状态机状态；写 `session_start` 与 `session_end` 事件。
- **依赖**：M1、M7；M10 为 **N/A**（Q1 不招人），SIM 模式下同意步骤以固定值 `consent_version = "SIM-AUTHOR"` 代替，不阻塞启动。
- **验收标准**：
  1. 给定 schedule + participant，分配结果**确定**：同输入跑 2 次得到完全相同的任务序列。
  2. 100 次虚拟分配模拟：两条件计数均衡（卡方 p > 0.05）；每个 PAIR 在两条件下均出现。
  3. **断点续跑**：杀掉进程后重启，已结束任务不重复、未结束任务可从断点继续，序列与日志 `seq` 不跳号、不重号。
  4. 任意一次分配的完整状态可**只从日志重建**（提供重建校验：重算结果与运行时内存状态一致）。
  5. 无有效同意（`consent_given = false`）时拒绝启动，并给出明确错误而非静默失败。

---

### M3 · AI 建议引擎（单一 LLM 客户端） — **MUST**（live 调真实 API + 交付态离线回放）

- **目的**：把所有模型调用收敛到一个可替换、可锁定、可回放的边界后面。
- **输入**：仓库快照、`intent_text`、上下文包（文件片段 + 符号表 + 调用图子图）、运行模式 `live` / `replay`、模型配置（`model_id`、`temperature`、`seed`、`max_tokens`）。
- **输出**：结构化建议对象 `{suggestion_id, patch_diff, rationale_text, touched_symbols[], rationale_layers{}}`；以及每次调用的 `generation_request` 事件（请求 hash、延迟、token 数、模式）。
- **依赖**：单一 client 模块（项目约定 `[REF]`：所有 LLM 调用集中，模型名/温度/seed 只从 config 读取，代码内禁止硬编码）；`recordings/` 回放缓存。
- **两种模式（按 Q3 拍板）**：
  - `live`：**真实调用外部 API**。密钥只从环境变量读，**永不入库**；每次调用把请求 hash 与返回原文写入 `recordings/`。
  - `replay`：**交付态默认模式**，从 `recordings/` 回放，无需网络与密钥，保证 3.11 第 3 条"一条命令复现"仍成立。
- **交付态要求（Q3 附加）**：提交前删除仓库内所有 API endpoint、密钥与账号标识；README 说明评审者如何自备 key 启用 `live`，并说明默认 `replay` 即可完整复现。依据 A2 原文：*"Never commit API keys… explain how a reviewer can supply their own without including your key"* `[A2]`。
- **验收标准**：
  1. **确定性（replay）**：同一输入回放返回**逐字节相同**的建议；连续 10 次调用输出 hash 全等。
  2. **录制完整**：`live` 每次调用把请求 hash 与返回原文写入 `recordings/`，`replay` 能复现同一次的建议对象。
  3. **无魔法数字**：仓库内 grep `model`、`temperature`、`seed` 常量，除 config 文件外零命中。
  4. **无密钥与端点入库**：交付态扫描 `sk-`、`api_key`、`token=`、`https://` 端点等模式零命中（与 3.11 第 5 条共用同一扫描脚本）。
  5. **非法返回不崩溃**：返回不符合 schema 时写 `integrity_event(kind = "schema_violation")` 并返回明确错误码，会话继续（对应 `参考代码库` 里 `malformed.txt` 的处理思路 `[REF]`）。
  6. 每次调用都产生且仅产生一条 `generation_request` 事件，`mode` 字段如实标注 `live` / `replay`，`model_id` 填录制时的真实模型名。

---

### M4 · 约束与影响分析器 — **MUST**

- **目的**：这就是 A1 缺口 (i)"宏观架构意图映射"的最小可运行版本 `[A1]`：把"改这个函数会动到哪些全局状态与跨模块契约"算出来。
- **输入**：仓库快照、`intent_text`、候选 patch（可为空——确认前就要能出卡）。
- **输出**：`impact_set {global_vars[], cross_module_contracts[], side_effects[], affected_tests[], risk_level}`；`impact_set_hash`。
- **依赖**：Python `ast`（标准库）；至多 1 个第三方静态分析库（需在 `requirements.txt` 说明理由）。
- **验收标准**：
  1. 对 M1 全部 6 个 gold patch，`impact_set` 对 `impact_label_set` 的 **recall = 1.0**（不许漏掉真正的全局变量/跨模块契约），精确率 ≥ 0.8 `[假设]` A-9。
  2. **区分度**：仅改函数内部的 patch 与改变跨模块契约的 patch，`risk_level` 必须不同（用 2 个构造用例断言）。
  3. **健壮性**：空 patch、语法错误文件、单文件仓库三种输入都不抛未捕获异常，返回明确错误码。
  4. **交互可接受**：单次分析 < 2 s（在 M1 最大实例上测）`[假设]` A-10。
  5. 输出确定性：同一输入两次运行 `impact_set_hash` 相同。

---

### M5 · 评估卡渲染器 — **MUST**

- **目的**：把 `impact_set` 变成人能做决定的东西——这是 A1 §4 "Assessment Card" 的直接实现 `[A1]`。
- **输入**：`impact_set`、建议摘要（**不含 diff**）、条件配置（本期只有 C1 固定全量；C2 自适应为 PLAN）。
- **输出**：`card_view {card_id, items[]{item_id, statement, category, affected_symbol, evidence_ref, required}}` + 渲染后的界面片段。
- **依赖**：M4；模板层（Jinja 或原生 HTML）。
- **验收标准**：
  1. **无凭空条目**：每个 `item.affected_symbol` 必须能在 `impact_set` 中找到来源（自动断言 100% 可追溯）。
  2. **条目规格**：每张卡 ≥ 3 条 item，每条 ≤ 120 字符，且**必须包含具体的符号名**（不许写"可能影响其他模块"这类空话）。
  3. **确定性渲染**：同一 `impact_set` 两次渲染输出一致。
  4. **关键治理属性可测**：确认前界面**不得**出现 diff 内容——用"渲染输出中不包含 patch 的任一新增行文本"作为断言。这条是 C1 与 C0 的本质区别，必须机器可验证。
  5. （PLAN）C2 模式下低风险任务的 `n_items` 必须**严格小于**高风险任务——本期不实现，此条不验收。

---

### M6 · 强制确认门与清单 — **MUST**

- **目的**：让"没确认就不能生成"成为**系统不变量**，而不是使用者的自觉 `[A1]`。
- **输入**：`card_view.items`、用户勾选状态、阈值配置（`n_required`、是否每次生成都重新过门）。
- **输出**：`gate_state ∈ {blocked, unlocked}`、授权令牌（一次性）、`gate_decision` 事件。
- **依赖**：M7；M5。
- **验收标准**：
  1. **不变量**：`n_confirmed < n_required` 时，任何生成请求被拒绝，且**每次都写** `gate_decision(blocked = true)`；接口级测试须覆盖该路径。
  2. **正向路径**：勾满后解锁，生成成功，`blocked = false`、`confirmed = true`。
  3. **不可绕过**：不存在绕过门的公开入口（代码审查 + 一条"尝试直接调生成"的负向测试须失败）。
  4. **C0 同接口**：baseline 条件下门为直通，但**走同一个接口、写同一 schema 的事件**（`condition = "C0"`，`blocked = false` 恒成立）——保证两组日志结构与指标定义完全一致。
  5. **回退**：拒绝或关闭卡片后，可修改需求重新提问，状态机不进入死锁（有测试覆盖）。

---

### M7 · 遥测日志器 — **MUST**

- **目的**：成为第 5 节所有指标的唯一数据源。
- **输入**：事件对象（见第 4 节）、`schema_version`。
- **输出**：`runs/<run_id>/logs/<participant_id>/<session_id>.jsonl`，逐行追加。
- **依赖**：标准库 `json`；无第三方依赖。
- **验收标准**：
  1. 每行是合法 JSON，且通过 schema 校验；**校验失败时拒绝写入并抛出**（禁止静默丢弃或写半行）。
  2. `(session_id, seq)` 唯一且严格递增；`ts` 均带时区偏移且会话内不倒退。
  3. **无 PII**：对全部日志做正则扫描，不得出现姓名/邮箱/学号样式字符串（测试用例内含正例与反例）。
  4. **原子性**：模拟进程在写一行中途被杀，日志文件最后一行要么完整要么不存在（不得有半个 JSON）。
  5. 单行 ≤ 4 KB；数组字段 ≤ 20 项，超出须截断并另记总数。
  6. **原文不落盘（Q7）**：schema 中不存在任何正文字段；凡需引用代码或 prompt 处，只写 `sha256` + `length`。校验器须**拒绝**含 `text` / `content` / `body` / `prompt_raw` 类字段的事件，并有对应测试。
  7. **保留期可执行（Q7）**：提供 `purge --before <date>` 命令，删除早于该日期的 run 目录并输出删除清单；提交后 90 天清理即由它执行。删除后目录内不得残留 `.jsonl`、`.jsonl.tmp` 或备份文件，且重跑 `analysis/` 时须显式报告"哪些结论依赖已删除数据"。

---

### M8 · 结果评估器 — **MUST**（离线轻量 JSON 规则集）

- **目的**：把"这段重构好不好"变成机器判定，消除人工评分。
- **输入**：提交时的仓库快照、隐藏测试套件、`rules.json`、任务开始时的同一份指标基线。
- **输出**：`outcome {tests_pass, n_fail, failing_tests[], debt_delta, vuln_delta, lines_added, lines_removed, scorer_version}`；追加 `suggestion_scored` 事件（后验正确性标签）。
- **规则集（按 Q6 拍板，六类固定）**：`complexity`（函数过长 / 分支过深）、`duplication`（重复块）、`bare_except`、`hardcoded_secret`、`eval_usage`、`sql_concat`。每条规则带 `rule_id`、`severity`、`weight`；`debt_delta` 为加权计数差，`vuln_delta` 只统计后三类（`hardcoded_secret` / `eval_usage` / `sql_concat`）。
- **依赖**：M1 的隐藏测试；`rules.json`；子进程沙箱。
- **验收标准**：
  1. 对 gold patch 输出 `tests_pass = true`；对未修改仓库输出基线结果（**禁止**出现"连 gold patch 都不过"的情况，否则测试本身有问题）。
  2. 指标为"提交后 − 任务开始"，同仓库重复计算完全一致（确定性），且与文件遍历顺序无关。
  3. `scorer_version` 与 `rules.json` 的 hash 写入每条 `task_end` 与 `suggestion_scored`。
  4. **执行隔离**：只在容器/子进程沙箱内运行被测仓库测试，超时强制终止并记录（不得挂死会话）。
  5. **每条规则都要有正例与反例测试**：在植入坏味道的样本上该规则命中、`debt_delta` 为正；在干净样本上为 0。缺这对测试的规则视为未实现（防止规则形同虚设）。
  6. `suggestion_scored.is_correct` 的判定规则固定为"应用该建议后隐藏测试是否改善"，且该规则写在文档中而非隐含在代码里。

---

### M9 · 分析管线 — **PLAN**（Q8：只留接口约定，不接数据）

- **目的**：一条命令从原始日志复现论文里的表与图。
- **输入**：`runs/**/*.jsonl`、预注册分析计划（5.2 表）、`schema_version`。
- **输出**：`analysis/metrics.csv`（逐观测）、`analysis/results.xlsx`（汇总表）、PNG 图、`analysis/report.md`（含 n、检验名、效应量、CI、p）。
- **依赖**：`pandas`、`scipy`、`statsmodels`（或 `pingouin`）；离线安装。
- **验收标准**：
  1. **逐格一致**：从原始日志重算，结果与论文表格数值一致（容差 1e-9）。
  2. **可审计**：每个统计结论都带 `n`、检验名、效应量、95% CI、p 值、缺失处理说明。
  3. **缺失与异常显式**：输出的报告里必须列出被排除的观测及原因，不允许静默 dropna。
  4. 不依赖任何运行时外部状态（网络、时钟、随机数未设种子）。

---

### M10 · 参与者与合规管理 — **N/A**（Q1：不招募真人，不实现；保留设计供日后使用）

- **目的**：把同意、匿名化、撤回做成可验证流程，而不是一句承诺。
- **输入**：知情同意（版本化勾选）、撤回请求、人口学问卷。
- **输出**：同意记录（版本 + 时间戳 + 布尔）、伪名映射表（独立受限目录）、撤回执行报告。
- **依赖**：无网络；与 M7 隔离（日志只写伪名）。
- **验收标准**：
  1. 无同意记录时 M2 拒绝启动会话（有测试）。
  2. 日志与问卷中不出现可识别信息（与 M7 第 3 条共用同一扫描测试）。
  3. 撤回可在 1 条命令内完成，并输出"删除了哪些文件、标记了哪些行"的可核对报告。
  4. 映射表与日志物理分离（不同目录、不同访问权限）。

---

### M11 · 开发溯源台账与校验器 — **MUST**

- **目的**：直接兑现 `Development evidence and authorship /20` 的 "Convincingly" 档——"distinguishes original, reused and assisted work, with relevant examples of reviewing and adapting AI output" `[A2]`。这一项是**唯一不与代码质量相关、纯靠记账就能拿分**的维度，因此单独立模块，而不是散落在 README 里。
- **输入**：`docs/PROVENANCE.md`（人工维护的台账）、`git log`、`参考代码库/` 的复用清单。
- **输出**：校验报告（终端摘要 `ok: <n> rows, <n> modules covered`）+ 台账本身。
- **台账字段**（每行一条）：`item_id`、`module`（M1–M11）、`origin`（original / reused / assisted）、`source`（reused/assisted 时填：仓库路径或工具名）、`decision`（我为什么这样选）、`check`（我怎么验证的）、`commit`。
- **依赖**：仅本地文本与 git 历史；不联网。
- **验收标准**：
  1. 每个 MUST 模块（M1/M4/M5/M6/M7）至少 1 行，且 `origin` 三个取值**都至少出现一次**——全部填 original 视为未通过（说明没真的区分）。
  2. 所有 `origin=assisted` 行的 `decision` 与 `check` 均非空，缺一即失败（对应 "reviewing and adapting AI output"）。
  3. 所有 `origin=reused` 行的 `source` 必须指向工作区内真实存在的路径，否则失败。
  4. 校验器失败时退出码非 0，且能在提交前一行命令运行。

---

### 3.11 模块依赖与全局验收

依赖方向（无环）：

`M10 → M2 → M1 / M7`；`M1 → M4 → M5 → M6 → M7`；`M3 → M5`；`M6 → M3`（仅在解锁后调用）；`M1 / M8 → M9`；`git log + 台账 → M11`（M11 只读，无出边）。

全局验收（所有模块共同遵守，直接复用为 A2 的"development evidence" `[A2]`）：

1. **一条命令跑测试**：全仓库一个固定命令（如 `pytest -q`）通过。
2. **一条命令自检**：`--dry-run` 模式在不调用真实模型、不写真实日志的前提下走通"任务→卡→门→建议"全链路，输出 `ok: <n> tasks, <n> cards`（沿用 `参考代码库` 各文件 `--selftest` 的约定 `[REF]`）。
3. **一条命令复现**：从零 clone → 装依赖 → 一条命令 → 得到结果表。
4. **零魔法数字**：模型名、阈值（`τ_review`、`800 ms`、`20%`）、样本量全部在配置文件中。
5. **无密钥、无端点入库**：仓库内无 API key、无 endpoint、无账号标识（`[A2]` 明令禁止；交付态须扫描零命中）。
6. **溯源可校验**：M11 台账校验通过（见 M11 验收）。

---

## 4. 日志 schema

### 4.1 文件与写入规则

- 格式：**JSON Lines**，UTF-8 无 BOM，一行一个 JSON 对象，行尾 `\n`。
- 路径：`runs/<run_id>/logs/<participant_id>/<session_id>.jsonl`。
- 只追加（append-only）。**任何后验标签都不能修改历史行，只能作为新事件追加**——这是 `suggestion_scored` 存在的原因。
- `schema_version` 参与比较：分析管线遇到不认识的版本必须报错，不得猜测。

### 4.2 公共信封字段（每行都有）

| 字段 | 类型 | 必填 | 取值 / 示例 | 说明 |
|---|---|---|---|---|
| `schema_version` | string | 是 | `"1.0.0"` | 语义化版本 |
| `event_id` | string | 是 | `"9f1c0b7e-2a44-4c1e-9b1f-0d6a3e5c7b21"` | UUID v4，全局唯一 |
| `seq` | integer | 是 | `21` | 会话内从 1 严格递增 |
| `ts` | string | 是 | `"2026-11-20T10:14:32.418+00:00"` | ISO-8601，**毫秒 + 时区偏移** |
| `session_id` | string | 是 | `"S-01J9Z7K3"` | 会话标识 |
| `participant_id` | string | 是 | `"P07"` | **伪名**，禁止学号/邮箱/姓名 |
| `condition` | string | 是 | `"C0"` / `"C1"` | 枚举；`"C2"` 只在 PLAN 文档中出现，**不得出现在日志里**（Q5） |
| `task_id` | string / null | 是 | `"T-L02a"` / `null` | `setup`、`end` 阶段为 null |
| `task_index` | integer / null | 是 | `0` | 会话内序号，0 起 |
| `pair_id` | string / null | 是 | `"PAIR-02"` | 配对材料标识 |
| `phase` | string | 是 | `setup` / `prompt` / `card` / `gate` / `generate` / `review` / `test` / `quiz` / `survey` / `end` | 枚举 |
| `event_type` | string | 是 | 见 4.3 | 枚举 |
| `app_version` | string | 是 | `"0.3.1+9c2a1f"` | git describe |
| `model_id` | string / null | 是 | `"qwen2.5-coder:7b"` | `replay` 模式必须填录制时的真实模型名；仅手写 mock 才允许 null（本期不采用） |
| `model_temperature` | number / null | 是 | `0.2` | 从 config 读取 |
| `seed` | integer / null | 是 | `42` | 从 config 读取 |

### 4.3 事件类型与私有字段

| `event_type` | 私有字段（类型 / 取值） |
|---|---|
| `session_start` | `consent_version` string；`consent_given` boolean；`prior_years` number；`llm_freq` enum(never/monthly/weekly/daily)；`lang_familiarity` integer 1–5；`schedule_id` string；`device` string（OS 大类 + 浏览器，不含 UA 全串） |
| `prompt_submit` | `prompt_id` string；`prompt_len_chars` integer；`prompt_sha256` string；`attached_files` array<string>（≤20） |
| `generation_request` | `suggestion_id` string/null；`request_sha256` string；`mode` enum(mock/live)；`latency_ms` integer；`tokens_in` integer/null；`tokens_out` integer/null |
| `suggestion_shown` | `suggestion_id` string；`suggestion_seq` integer；`n_files` integer；`n_lines_changed` integer；`n_hunks` integer；`rationale_len_chars` integer |
| `card_shown` | `card_id` string；`card_version` string；`n_items` integer；`n_required` integer；`latency_from_prompt_ms` integer；`impact_set_hash` string |
| `card_item_toggle` | `card_id` string；`item_id` string；`item_category` enum(global_var/cross_module_contract/side_effect/test_impact/other)；`checked` boolean；`dwell_ms` integer |
| `gate_decision` | `card_id` string；`confirmed` boolean；`blocked` boolean；`n_required` integer；`n_confirmed` integer；`gate_latency_ms` integer |
| `explanation_open` | `suggestion_id` string；`layer` enum(L1/L2)；`dwell_ms` integer |
| `suggestion_action` | `suggestion_id` string；`action` enum(accept/edit/reject/regenerate)；`review_dwell_ms` integer；`edit_distance_lines` integer/null；`accepted_after_gate` boolean |
| `suggestion_scored` | `suggestion_id` string；`is_correct` boolean/null；`gold_patch_match` boolean；`scored_by` enum(hidden_tests/gold_diff/manual)；`scorer_version` string |
| `test_run` | `task_id` string；`suite` enum(visible/hidden)；`n_pass` integer；`n_fail` integer；`failing_tests` array<string>（≤20） |
| `task_end` | `elapsed_ms` integer；`submitted` boolean；`timeout` boolean；`tests_pass` boolean；`n_fail` integer；`debt_delta` number；`vuln_delta` integer；`lines_added` integer；`lines_removed` integer；`n_suggestions` integer；`n_accepted` integer；`n_edits` integer；`n_rejects` integer |
| `comprehension_item` | `quiz_id` string；`item_id` string；`answer` string；`correct` boolean；`response_ms` integer |
| `survey_response` | `instrument` enum(NASA_TLX/SUS/custom)；`item_id` string；`value` number；`scale_min` number；`scale_max` number；`response_ms` integer |
| `session_end` | `total_elapsed_ms` integer；`n_tasks_completed` integer；`completed_all` boolean；`withdrawn` boolean |
| `integrity_event` | `kind` enum(mock_mismatch/schema_violation/crash_recovered/timeout_kill)；`detail_len` integer；`ref_event_id` string/null |

### 4.4 示例行（真实可解析，逐行独立）

```json
{"schema_version":"1.0.0","event_id":"9f1c0b7e-2a44-4c1e-9b1f-0d6a3e5c7b21","seq":1,"ts":"2026-11-20T10:02:11.004+00:00","session_id":"S-01J9Z7K3","participant_id":"P07","condition":"C1","task_id":null,"task_index":null,"pair_id":null,"phase":"setup","event_type":"session_start","app_version":"0.3.1+9c2a1f","model_id":"qwen2.5-coder:7b","model_temperature":0.2,"seed":42,"consent_version":"2026-11-01","consent_given":true,"prior_years":3.5,"llm_freq":"weekly","lang_familiarity":4,"schedule_id":"SCHED-2026-11-A","device":"win11-chrome"}
{"schema_version":"1.0.0","event_id":"4b8e2c11-77d0-4a2f-b1c9-5e3d9a0f6c12","seq":14,"ts":"2026-11-20T10:14:32.418+00:00","session_id":"S-01J9Z7K3","participant_id":"P07","condition":"C1","task_id":"T-L02a","task_index":0,"pair_id":"PAIR-02","phase":"card","event_type":"card_shown","app_version":"0.3.1+9c2a1f","model_id":"qwen2.5-coder:7b","model_temperature":0.2,"seed":42,"card_id":"CARD-0007","card_version":"1.0","n_items":4,"n_required":4,"latency_from_prompt_ms":1180,"impact_set_hash":"sha256:3f1a9c..."}
{"schema_version":"1.0.0","event_id":"c3a7d5e9-1f62-4b83-8d04-2a6b7e1f9c33","seq":15,"ts":"2026-11-20T10:14:33.006+00:00","session_id":"S-01J9Z7K3","participant_id":"P07","condition":"C1","task_id":"T-L02a","task_index":0,"pair_id":"PAIR-02","phase":"card","event_type":"card_item_toggle","app_version":"0.3.1+9c2a1f","model_id":"qwen2.5-coder:7b","model_temperature":0.2,"seed":42,"card_id":"CARD-0007","item_id":"CI-03","item_category":"cross_module_contract","checked":true,"dwell_ms":412}
{"schema_version":"1.0.0","event_id":"e2d6f4a8-3b15-4c72-9e60-7f8a1b2c3d44","seq":21,"ts":"2026-11-20T10:19:04.772+00:00","session_id":"S-01J9Z7K3","participant_id":"P07","condition":"C1","task_id":"T-L02a","task_index":0,"pair_id":"PAIR-02","phase":"review","event_type":"suggestion_action","app_version":"0.3.1+9c2a1f","model_id":"qwen2.5-coder:7b","model_temperature":0.2,"seed":42,"suggestion_id":"SUG-0007","action":"accept","review_dwell_ms":2650,"edit_distance_lines":null,"accepted_after_gate":true}
{"schema_version":"1.0.0","event_id":"7a9b3c2e-5d41-4f08-a7b6-9c0d1e2f3a55","seq":34,"ts":"2026-11-20T10:31:47.120+00:00","session_id":"S-01J9Z7K3","participant_id":"P07","condition":"C1","task_id":"T-L02a","task_index":0,"pair_id":"PAIR-02","phase":"test","event_type":"task_end","app_version":"0.3.1+9c2a1f","model_id":"qwen2.5-coder:7b","model_temperature":0.2,"seed":42,"elapsed_ms":1092512,"submitted":true,"timeout":false,"tests_pass":true,"n_fail":0,"debt_delta":-2.0,"vuln_delta":-1,"lines_added":37,"lines_removed":29,"n_suggestions":3,"n_accepted":2,"n_edits":1,"n_rejects":0}
```

### 4.5 不变量（M7 必须机器校验）

1. 每行合法 JSON；每行一个对象；无嵌套深度 > 3。
2. `(session_id, seq)` 唯一且递增 1。
3. `ts` 必带偏移；同一 session 内非递减。
4. 枚举值只取 4.2/4.3 列出的小写值。
5. 未知字段仅允许 `x_` 前缀（前向兼容）。
6. 未知值用 `null`，**不允许空字符串代替 null**。
7. 不写源码正文、不写 prompt 正文（只写 `sha256` 与长度）；**没有"另存原文"的例外**（Q7），需要原文时凭 hash 回查。
8. 单行 ≤ 4 KB；数组 ≤ 20 项。

### 4.6 隐私边界（Q7 拍板：只存 hash + 长度，原文不落盘，90 天删除）

- **原文不落盘**：不写源码正文、不写 prompt 正文，只写 `sha256` 与 `length`（字节数）。schema 层面禁止 `text` / `content` / `body` / `prompt_raw` 这类字段；需要原文时凭 hash 回查 `recordings/`（M3）或仓库快照，而不是查日志。
- **数据位置**：全部本地；`runs/` 置于仓库外或列入 `.gitignore`，**不入 Git**。
- **保留期**：提交后 **90 天**删除全部运行日志与录制，由 M7 的 `purge --before` 执行，删除清单留档（可核对删了什么）。
- **伪名**：日志中只有 `participant_id`；伪名映射表独立存放、独立权限（Q1 不招人时，映射表里只有作者自己一条）。
- **不记录**：IP、完整 User-Agent、窗口标题、剪贴板内容。
- **删除即彻底**：`purge` 是唯一删除入口；删除后不得残留 `.jsonl`、`.jsonl.tmp` 或备份副本。
- **唯一的受控例外：`recordings/`（M3）**。回放需要模型输入输出原文，因此该目录保存原文；但其中的代码与 prompt 全部来自**自建语料 + 作者自测**，不含任何第三方数据，故可随仓库交付。**凡来自真人会话的录制一律不得进入该目录**，须在会话结束时即删除。这一条是 Q7 与 Q3/replay 的交界处，若日后转真人研究，必须重新裁决。

---

## 5. 指标 → 数据 → 统计方法

> **本节状态：计划分析（PLAN）。** 按 Q1/Q2 拍板，**没有采集人类数据**。5.1–5.3 是**预注册的分析计划**，用于说明"如果做这个实验会怎么算"，在报告与 README 中一律标 planned `[A2]`。原型阶段真正可执行的读数只有三项，且属于**技术验收**、不是 H1–H7 的检验：`gate_decision.blocked`（门是否真的拦住了生成）、`impact_set_hash` 与 gold 的比对（M4 验收）、schema 校验通过率（M7 验收）。

### 5.1 指标计算式（全部只依赖第 4 节字段）

| 指标 | 计算式 |
|---|---|
| 任务完成时间 | `task_end.elapsed_ms` |
| 接受率 | `count(action = accept) / count(suggestion_action)` |
| 编辑率 / 拒绝率 | 同理按 `action` 分列 |
| 盲接受数 | `count(action = accept ∧ accepted_after_gate = true ∧ review_dwell_ms < τ_review ∧ 无对应 explanation_open)` |
| OTI | 盲接受数 / 建议动作总数 |
| 判别力 AUC | 以 `action ∈ {accept}` 为 1、`{edit,reject}` 为 0；以 `suggestion_scored.is_correct` 为标签 |
| 逃逸缺陷率 | `count(task_end.tests_pass = false ∧ submitted = true) / count(task_end)` |
| 技术债增量 | `task_end.debt_delta` |
| 安全告警增量 | `task_end.vuln_delta` |
| 理解得分 | `mean(comprehension_item.correct)` 按任务聚合 |
| 摩擦（认知负荷） | `survey_response` 中 NASA_TLX 的 mental demand / effort / frustration 三维，0–100 标准化 |
| 可用性 | SUS 10 题按标准公式折算 0–100 |
| 确认延迟 | `gate_decision.gate_latency_ms` |
| 勾选交互数 | `count(card_item_toggle)` 按 `card_id` 聚合 |
| 机械确认率 | 满足 1.5 机械确认定义的 `gate_decision` 数 / 总 `gate_decision` 数 |
| 解释展开率 | `count(explanation_open)` / `count(suggestion_shown)` |
| 门控拦截次数 | `count(gate_decision.blocked = true)` |

### 5.2 映射表（预注册，不得事后增删主检验）

| 指标 | 数据来源（事件.字段） | 尺度 | 假设 | 统计方法 | 效应量 / 报告 |
|---|---|---|---|---|---|
| OTI（H1） | `suggestion_action.action`, `review_dwell_ms`, `explanation_open` | 每参与者比例 | 配对 | 配对 t 检验；不满足正态用 **Wilcoxon 符号秩**（n<10 一律 Wilcoxon） | Cohen's d_z / 秩二列 r；95% CI |
| 逃逸缺陷（H2a） | `task_end.tests_pass` | 配对二元 | 配对 | **McNemar 精确检验** | 优势比 OR；不一致对计数 |
| 技术债增量（H2b） | `task_end.debt_delta` | 配对计数（偏态） | 配对 | Wilcoxon 符号秩 | 中位数差；r |
| 安全告警增量（H2c） | `task_end.vuln_delta` | 配对计数 | 配对 | Wilcoxon；若呈泊松特征用 GLMM(poisson) | 率比；95% CI |
| 完成时间（H3a） | `task_end.elapsed_ms` | 配对连续（右偏） | 配对 | 先做 log 变换；配对 t；否则 Wilcoxon | 几何均值比；d_z |
| 主观摩擦（H3b） | `survey_response`（NASA_TLX 三维） | 配对序数 | 配对 | Wilcoxon（**不得**对序数用 t 检验） | 秩二列 r；中位数差 |
| 判别力 AUC（H4） | `suggestion_action` × `suggestion_scored` | 每参与者 [0,1] | 配对 | 配对 t / Wilcoxon on AUC；同时报告接受率以检验"是否只是少接受" | ΔAUC；d_z |
| 理解得分（H5） | `comprehension_item.correct` | 每任务比例 | 配对 | Wilcoxon | 中位数差；r |
| 疲劳趋势（H6） | `gate_latency_ms`、勾选计数 × `task_index` | 纵向 | 嵌套 | **线性混合效应模型**：固定效应 `task_index × condition`，随机截距按参与者；斜率的 95% CI 是否含 0 | 斜率 β 与 CI；边际 R² |
| 条件×复杂度（RQ2 细化） | `elapsed_ms` × `stratum` | 纵向 | 嵌套 | LMM 交互项；小样本备选 **ART（对齐秩变换）ANOVA** | 交互效应量；简单效应 |
| C2 非劣（H7，**未执行**） | 无（C2 未实现） | — | — | **不检验**：Q5 拍板不做 C2 | 只在 rationale 中论证为何是下一步 |
| 机械确认率（描述） | `gate_decision`, `card_item_toggle` | 比例 | — | 描述统计 + 会话内趋势图 | 报告为**探索性**，不进主检验族 |

### 5.3 前提、多重比较与缺失

- **前提检查**：Shapiro-Wilk（每组）+ 方差齐性（Levene）；违反则用非参数替代，并在结果表中标注实际使用的检验。
- **多重比较**：主检验族 = H1、H2a、H2b、H2c、H3a、H3b、H4、H5（8 个），用 **Holm–Bonferroni** 校正；H6、H7 与所有描述性指标标为**探索性**，单独报告、不作校正、明确标注 "exploratory"。
- **样本量与功效**：见 Q2。粗算 `[假设]` A-11：双侧 α=0.05、power=0.80 的配对设计，N=10 仅能检出 d_z≈0.9 的**大效应**，N=20 约可检出 d_z≈0.65 的**中等效应**；确切值须用功效分析脚本复算并写入预注册。
- **缺失数据**：
  - 退出者按 **ITT** 保留已产生日志；`session_end.withdrawn = true` 的观测进入敏感性分析（含/不含各报一次）。
  - AUC 在参与者只出现单一决策类别时**不可定义** → 记 `null`，该参与者不进 H4 的配对检验，并报告 `n` 减少的原因。
  - 超时任务保留（`timeout = true`），主分析含入，敏感性分析排除。
- **异常值**：不删；报告不含上下 5% 的敏感性分析结果。
- **不做的事**：不做 p-hacking 式的多指标筛选；不把探索性指标写成确认性结论；H3 若显示"无代价"，先回查 `gate_decision.blocked` 计数（操纵检查），再解释。

---

## 6. 未决问题

### 6.0 已拍板（2026-11-14）

| # | 决定 | 直接后果 |
|---|---|---|
| **Q1** | **不招募真人**；改用作者自测 + 录制回放（SIM），报告中标 simulated | M2 降为 SIM；M10 改为 **N/A**；H1–H7 全部为**计划假设**（无数据）；报告与 README 中不得用"被试 / 参与者 / experiment shows"描述已做的工作 |
| **Q2** | **N=10 便利样本**，统计以 Wilcoxon 为主（设计与功效按 N=10 留档） | 第 5 节整体降为**计划分析（PLAN）**；5.2 表作为预注册保留；A-11 的功效数字保留为计划值，不得写成实测 |
| **Q3** | **调用真实 API**（`live` 模式），但**交付时删除 API 链接/密钥/账号并说明**如何自备 key | M3 升为 MUST（live + replay 双模式）；交付态 `replay` 为默认、离线可跑，保证"一条命令复现"不被破坏；仓库内 endpoint 与密钥扫描零命中纳入 3.11 第 5 条 |
| **Q4** | **自建 6 个种子仓库**（= 6 个实例 = 3 个难度层 × 2，共 3 对 `pair_id`），不使用真实开源仓库 | M1 交付 6 个仓库快照 + 6 套隐藏测试 + 6 个 gold patch + 6 份影响集标签；M8 可凭 gold 自动判分；外部效度下降须写入 2.6 的限制 |
| **Q5** | **不实现 C2 自适应粒度**；H7 标 planned | 设计退化为 **2 条件（C0/C1）× 2 顺序**；2.1 的 C2 列保留只为说明设计空间，**不得出现在任何 implemented 的 demo / storyboard 中**；1,100 词 rationale 里只以"下一步工作"形式出现 |
| **Q6** | **轻量 JSON 规则集**：复杂度、重复、裸 `except`、硬编码密钥、`eval`、拼接 SQL 六类 | M8 升为 MUST；`debt_delta` 为加权计数差，`vuln_delta` 只计后三类；每条规则必须有正例+反例测试 |
| **Q7** | **只存 `sha256` + `length`，原文不落盘**；数据存本地；**提交后 90 天删除** | 4.6 与 M7 验收 6/7；schema 禁止正文类字段并由校验器拒绝；`runs/` 不入 Git；`purge --before` 为唯一删除入口 |
| **Q8** | **原型优先**：M1/M3/M4/M5/M6/M7/M8 真做；实验编排与统计标 planned | 交付状态表见 3.0；1,100 词 rationale 的重心放在设计理由与 scope 取舍，**不放实验结果** |

> **一致性说明（必须显式写进报告，否则构成 overclaiming）**：Q1 与 Q2 并列意味着"有一个 N=10 的设计，但没有采集数据"。两者不矛盾，但必须讲清楚——**N=10 是留档的设计参数与预注册依据，不是已执行的样本**。依据：`Developed interaction` 的 "Not yet demonstrated" 档原文即是 "materially misrepresents planned or simulated behaviour as implemented" `[A2]`。同理，`Design reasoning and scope` 的 "Convincingly" 档要求 justify "compromises in scope" `[A2]`——"不招人、不做 C2"正是需要被论证的 scope 取舍，而不是需要被掩饰的缺口。

### 6.1 原始问题清单（存档：8 条全部已拍板）

下表保留原始提问方式，便于日后回看"为什么当初要问"。**8 条的"默认"列均已被 6.0 覆盖**（Q7 取材于默认值），本表不再有开放问题。若日后要转真人研究，需重开 Q1、Q2、Q7 三条。

> 每条给出"若你不拍板我会怎么走"的默认，但默认不等于决定。

| # | 问题 | 为什么必须你定 | 影响面 | 默认（未拍板时） |
|---|---|---|---|---|
| **Q1** | **是否需要伦理审查（REC / 学院审批）？是否接触真实人类被试？** | A2 明确允许用 implementation / prototype / **simulation** / walkthrough 作为 developed work `[A2]`；但一旦招募真人即构成人类研究，通常需审批，且决定 M10 与整个会话流程是否合法 | 决定 M2/M10 是 MUST 还是 PLAN；决定第 2 节流程是否执行 | 不招募真人，改用作者自测 + 录制回放（SIM），并在报告中标 simulated |
| **Q2** | **样本量 N 与参与者来源？** | 直接决定能用什么统计方法、能否做功效分析；N<10 时只能非参数 + 描述 | 决定 5.2 的可行性与 H1–H5 的可检验性 | 按 N=10 设计（便利样本），统计以 Wilcoxon 为主 |
| **Q3** | **是否调用真实 LLM API？** 成本、模型漂移、数据出境 | A1 的全部结论都建立在"真实建议质量"上；但真实调用不可复现（A1 自己也引用了模型行为差异），且涉及密钥与费用 | 决定 M3 是 SIM 还是 MUST；决定能否声称生态效度 | 采用 record/replay：先用 API 录一批，再离线回放 `[REF]` |
| **Q4** | **任务语料：自建种子仓库，还是真实开源遗留仓库？** | 自建可控（有 gold patch 与隐藏测试）但外部效度低；真实仓库有生态效度但**没有 gold**，M1 验收标准 2 无法满足 | 决定 M1/M8 是否可验收 | 自建 6 个种子仓库（保证可判分） |
| **Q5** | **是否实现 C2 自适应粒度？** | A1 §4 自己把 confirmation fatigue 列为主要局限 `[A1]`；实现它直接回答 RQ5，但显著增加工作量并占用 rationale 字数 | 决定 H7 是主假设还是 planned；决定 scope 与 1,100 词预算 | 不实现，H7 标 planned，只在 rationale 中论证为何是下一步 |
| **Q6** | **技术债 / 安全告警用什么工具或规则集？有无安装权限？** | SonarQube 之类需安装与许可；轻量规则集可离线但效度是代理 | 决定 M8 的验收标准 2 是否可实现 | 轻量 JSON 规则集（复杂度、重复、裸 except、硬编码密钥、eval、拼接 SQL） |
| **Q7** | **数据保留与匿名化：日志/录屏存哪、存多久、是否允许保存 prompt 与代码原文？** | 涉及 GDPR 与学校政策；也决定第 4.5 条"不写正文"的严格程度 | 决定 M7 的隐私实现与 M10 的撤回流程 | 只存 hash + 长度，原文不落盘，数据存本地并在提交后 90 天删除 |
| **Q8** | **A2 交付主线：完整实验（多被试 + 统计），还是"可运行治理原型 + 模拟演示 + 实验规格（planned）"？** | A2 的 60 分集中在 Design reasoning(30) 与 Developed interaction(30)，**实验数据不是评分项** `[A2]`；把力气花错地方会两头不讨好 | 决定 M9 是 MUST 还是 PLAN；决定 1,100 词 rationale 的重心 | 原型优先（M1/M4/M5/M6/M7 真做），实验编排与统计标 planned，报告里写清理由 |

---

## 7. 假设清单（本文档所有 `[假设]` 及依据）

| ID | 假设 | 依据 / 若被推翻的后果 |
|---|---|---|
| A-1 | ~~A2 评分细则不在 docx 中~~ **已失效（2026-11-14）**：更新版 docx 第 5–6 页已含四项标准的四档描述语 | 已据此重写 0.2 与第 8 节。仍缺的只有档位→分值映射，见 A-15 |
| A-2 | 实验设计本身不是 A2 的评分要求 | A2 全文无 experiment / statistics / participant 字样 `[A2]`；实验是 A1 §4 贡献点的自然延伸 `[A1]` |
| A-3 | 盲接受判据 `τ_review = 2000 ms` | A1 未给阈值。取 2 s 是因为短于 2 s 的审阅不可能读完一个跨模块 diff；用 1/2/5 s 做敏感性分析降低误判风险 |
| A-4 | 配对任务可比性：三个结构指标差异 ≤ 20% | 无来源，为配对效度的工程判据；若某对超出，该对作废重做 |
| A-5 | 理解测验 5 题、只考架构与契约 | A1 关注"概念理解受损" `[A1]`；5 题是会话时长与信度的折中，需在报告中承认信度未验证 |
| A-6 | 机械确认判据：勾选停留中位数 < 800 ms 且无回退 | 行为代理，无来源；与 A-3 同理做敏感性分析 |
| A-7 | C0 必须是"同一系统关闭门控"，不是另一个产品 | 否则界面/延迟/建议质量全部混淆，任何差异不可归因于治理。A1 引用的对照研究均为同一工具的不同条件 `[A1]` |
| A-8 | 每人 2 个任务、单会话 ≤ 90 min | 课程项目可行性折中；被试内设计最小可检验配置 |
| A-9 | 影响集 recall = 1.0、精确率 ≥ 0.8 | recall 必须为 1 是治理正确性要求（漏报即失守）；0.8 精确率是可用性下限，防止卡被噪声淹没 |
| A-10 | 单次影响分析 < 2 s | 交互流畅性经验阈值；超出会造成额外等待，污染 H3 的时间指标 |
| A-11 | 功效粗算：N=10 → d_z≈0.9；N=20 → d_z≈0.65 | 配对 t 检验近似 `(z_{1−α/2}+z_{1−β})/√N`，双侧 α=0.05、power=0.80 手算；**必须用脚本复算**后写入预注册 |
| A-12 | 项目工程约定（Python 3.11+、离线可运行、单一 LLM client、JSONL 日志、`pytest` 验收） | 来自工作区 `DSH-实验程序工作流.md` 的项目约定 `[REF]`，**不是课程要求**；若与你的技术栈冲突以你的为准 |
| A-13 | record/replay 用于**交付后的离线复现**，而不是替代真实模型 | Q3 拍板后 live 调用真实 API；`replay` 的作用是让评审者无 key 无网络也能跑通（沿用 `参考代码库/mock_model.py` + `recorded_runs/` 的 Lab 4 做法 `[REF]`） |
| A-14 | 隐藏测试对参与者不可见 | 否则参与者可针对性改到测试通过（Goodhart），逃逸缺陷指标失效 |
| A-15 | 四档描述语**没有**对应的分值区间（docx 只给每项满分 /30、/30、/20、/20） | 页面只列四档文本与满分。因此验收按"是否满足 Convincingly 档描述"判断，**不做分数预测**；若日后拿到分值表，只需改第 8 节的验收措辞 |
| A-16 | 不采集数据 ⇒ H1–H7 无观测值，第 5 节全部是计划分析 | Q1/Q2 拍板结果。若把计划分析写成结果，即命中 A2 的 misrepresentation 红线 `[A2]` |

---

## 8. 与 A2 评分说明的追踪

### 8.1 评分项 → Convincingly 档要求 → 本项目证据

依据 2026-11-14 更新版 docx 的四档描述语重写。**只按 "Convincingly demonstrated" 档为目标**，因为其余三档是失分画像，不是验收标准。

| A2 评分项 `[A2]` | Convincingly 档的关键要求（原文要点） | 本项目要拿出的证据 | 章节 |
|---|---|---|---|
| Design reasoning and scope **/30** | 把设计连到问题；用相关证据论证主要选择、**重大变更**与 **scope 取舍**；**清楚区分哪些是 developed、哪些是 planned** | rationale 四列表（Design choice / Why it suits / Evidence / **Status**），每行 Status 必须落在 implemented / simulated / planned 之一；单列一段 scope 取舍论证（不招人、不做 C2、不接真实 API 的理由） | 2.1、3.0、6.0 |
| Developed interaction **/30** | 提交物与 storyboard 呈现连贯的"用户动作 → 系统响应 → 反馈或控制"；**清楚区分 implemented / simulated / unfinished** | 2–3 个 storyboard：C1 完整门控路径、C0 直通路径、以及"未勾满必需项时被拦住"这条关键分支；每步标 implemented 或 simulated | 2.5、M5、M6 |
| Architecture and technical reasoning **/20** | 图与解释说明组件、流、依赖如何支撑交互，**含智能行为**；技术选择与边界**与提交物一致** | System diagram 用 M1–M11 与 3.11 的依赖方向；AI 行为（M3/M4）单独标出；图中不得出现未实现组件而不加标注 | 3.11、3.0、M3、M4 |
| Development evidence and authorship **/20** | 开发记录把重大变更连到**学生的决策与检查**；区分 **original / reused / assisted**，并给出"审阅并改写 AI 输出"的实例 | M11 台账（origin 三值齐全、assisted 行必须有 decision + check）+ README 六项 + 提交 commit + 一条命令复现 | M11、3.11 |

### 8.1b 提交前自查（每条对应一个具体失分点）

| 自查问题 | 若答"否" | 依据 |
|---|---|---|
| 报告里每处 implemented 都真的能跑起来？ | 命中 misrepresentation 红线 | `[A2]` Developed interaction |
| 每处 simulated 都写了"替代了什么、真实部分是什么"？ | 判为 "boundaries need clearer evidence" | `[A2]` 同上 |
| 每个 planned 功能都在 rationale 里标了 planned？ | 判为把 planned 计入 developed work | `[A2]` Design reasoning |
| 有没有一段专门论证 scope 取舍？ | 判为 "compromises in scope 需要解释" | `[A2]` Design reasoning |
| 台账里 reused 的来源指向真实路径？assisted 的行有 decision + check？ | 判为无法区分学生贡献与复用/辅助工作 | `[A2]` Development evidence |
| 图里的组件与代码实际边界一致？ | 判为 "discrepancies unexplained" | `[A2]` Architecture |

### 8.2 字数预算（硬约束，超了会被截断）

| 部分 | 上限 `[A2]` | 建议分配 |
|---|---|---|
| Abstract | 300 | 250–280 |
| Design rationale | 1,100（约 1,000） | 1,000–1,050，**留 50 词缓冲** |
| 合计 | 1,400；超 1,300 停止阅读 | ≤ 1,300 |
| 不计入 | figures、diagrams、storyboards 及短标签/图注；references、repo 链接、README | 把实验细节、schema、指标定义、统计方法**全部放 README / 仓库文档**，不占字数 |

> **由此得出一条执行决策** `[A2]`：本 SPEC（第 3–5 节）应作为仓库文档交付（`docs/SPEC.md`），A2 正文只写"做了什么选择、为什么、证据在哪"，并把读者指向仓库。A2 明确允许 README 承载这些内容且不计入字数 `[A2]`。

### 8.3 明确不在评分说明中的内容（防止过拟合）

以下内容**没有**出现在 A1 或 A2 中，属本文推导，若被质疑须以第 7 节说明依据：

- 全部假设 H1–H7 与 RQ1–RQ5 的具体措辞（A1 只有缺口与提案，没有形式化假设）。
- 三项主 DV 的选择、`τ_review`、机械确认阈值、配对可比性判据、影响集验收阈值。
- 统计方法（Wilcoxon / McNemar / LMM / Holm）与 α、功效、非劣 margin。
- 日志 schema 的全部字段、事件类型、路径规范。
- 模块划分 M1–M11 及其编号（M11 的台账字段是为满足 A2 "区分 original/reused/assisted" 而推导出的实现手段，A2 未规定字段名）。
- **档位 → 分值的换算**，以及任何"这样做能得 X 分"的判断——docx 给了四档描述语但没给分值区间（A-15）。本规格只判断"是否满足某档描述"。

> 已从本清单移除：原先"评分细则不在 docx 中"的说法已因 2026-11-14 更新而失效，四档描述语现属 `[A2]` 原文，不再算本文推导（见 0.2）。

---

## 附：需要同步更新的下游文件

- `docs/PLAN.md`：按 M1–M11 出实现方案与里程碑，标注 MUST / SIM / PLAN / N/A（状态见 3.0）。
- `docs/rubric-mapping.md`：把 8.1 的每一行落成"需求 → 文件:行号 / 测试名"的证据行，并按 8.1b 自查。
- `docs/PROVENANCE.md`：M11 台账本体，逐行记 original / reused / assisted。
- `AGENTS.md`：把 3.11 的全局验收（一条命令跑测试、`--dry-run` 自检、零魔法数字、无密钥、溯源可校验）写成项目宪法 `[REF]`。
