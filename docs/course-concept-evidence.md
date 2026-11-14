# 课程概念证据核对（W1–W4，一手材料版）

用途：为报告 §Design rationale 提供**可核实**的课程概念依据。本文件只核对证据，不改代码、不写报告。

## 0. 用了哪些材料，页码怎么数

一手材料在 `modules/`：`W1/`–`W4/` 各含当周讲义 PDF 与当周汇总 docx；另有 `modules/IIS_W1-4_概念与知识点汇总.docx`（跨周总册）与 `modules/.work/txt/*.txt`（讲义 PDF 的逐页文本提取，页界标记为 `===== PAGE n =====`）。

**页码口径**：下文 `p.n` 指讲义 PDF 的**第 n 页**，也即幻灯片的第 n 张（含标题页）。核对方式是对 `modules/.work/txt/` 的逐页文本做定位，再回读 PDF 页序，因此可复现。

**已确认可引用的一手讲义**：W1 L01/L02/L03、W2 L04/L05/L06、W3 L07/L08/L09、W4 L10/L11/L12、W2 `examples_projects.pdf`（示例项目册）。
**未提供方法论文本的两份**：`W2/exp.pdf` 实测是"First Hand (Meta Quest 3) 观片指南"（26 页，视频分段时间轴 + L1–L6 概念对照），**不含评估方法论**；`IIS_W1-4_概念与知识点汇总.docx` 的 §05「三种效度 / 指标菜单 / 四句 evaluation 段落」在这批 PDF 里找不到对应页（见 §4）。

**证据强度**：**强** = 该页明确命名概念且给出机制/补救，而实现正是那个机制；**中** = 概念已命名，但把它挂到具体决策上需要一步解释；**弱** = 只有主题相似；**误配** = 同名不同义。

---

## 1. 可用的一手对应（按强度排序）

| 设计决策 | 可核实的课程概念 | 课程材料位置 | 该概念如何影响决策 | 证据强度 |
|---|---|---|---|---|
| C1：未逐项确认就不生成代码（`Session.generate()` 抛 `GateClosed`） | 「**The model proposes; your system disposes**」+ 执行前五项检查的 **confirmation** | W4 L12 **p.5**（提议≠执行）、**p.8**（五项检查逐项说明） | 确认被做成**应用侧的前置检查**，不是提示词里的礼貌请求：模型只产出提议，生成这一步由系统按检查结果放行 | **强** |
| 卡上展示"这次会碰到哪些模块/契约"（5 项影响集），而不是一个 yes/no | 可逆性 × 可见性矩阵：「**Irreversible but visible: confirm, with the arguments shown**」 | W4 L12 **p.16**（两问：能否撤销、人是否会注意到；四格处置）；p.15 是同一判断的课堂练习 | 决定了卡的**内容**：确认必须带可判断的参数，否则"确认"退化为点击 | **强** |
| 确认界面写具体对象（"billing.state.remember→PRICE_CACHE 在请求处理期间被写入"），不写"这次改动" | 「**Name the object: 'Project review', six attendees, not 'the meeting'**」 | W4 L12 **p.12**（"What the person sees before it runs"） | 直接决定了 `labelFor()` 把 `item_id` 映射成**具名对象**；这条是"写陈述句"的最硬一手依据 | **强** |
| 拦截提示用陈述句说明系统理解了什么 | L06 三种错误要**不同补救**：「**show what was heard, confirm risky actions, and expose the system's model**」 | W2 L06 **p.10**（slip / mistake / system inference error 各配补救）；p.9 是三者定义 | 拦截文案复述"系统听到了什么"，因为错在**系统推断的目标**，不在用户操作 | **强** |
| 未勾满时 `Generate` 禁用，并写明还缺哪几项 | **signifier**（可感知的行动提示）与**两道鸿沟**（execution / evaluation）；slip 的补救 = 约束/确认/撤销 | W2 L06 **p.4**（affordance vs signifier）、**p.5**（suggestion chips 是强 signifier）、**p.6**（两鸿沟）、**p.10**（slip 补救） | 决定用"约束 + 意符"（禁用 + 缺项清单）拦在执行之前，而不是提交后报错 | **强** |
| 拦截时把可选动作摊开，不要求用户重说 | L07 四类修复轮之 **clarify**：「**present the options the system has, and do not ask for clearer input**」 | W3 L07 **p.12**（"Four repair turns should be specified before any other dialogue is written"） | 缺项提示列出"还差哪三项"，而不是"请补充更多信息" | **强** |
| 不招真人：replay + 脚本化会话 + 合成数据 + 计时（Q1） | 示例项目的四个共同点之三「**Evaluation without participants**: replays, scripted conversations, synthetic data and timing answer a focused question」 | W2 `examples_projects` **p.19**（四共同点）；p.20 的追问「What could you measure alone, without participants?」；p.6/p.12/p.15/p.16 是四个示例各自的 replay 评估 | Q1 的课程依据：课程自己把"无被试评估"列为可接受做法，报告据此说明取舍而不是道歉 | **强** |
| 三个状态（implemented / simulated / planned）必须分别标注 | 同页第四条「**Honest scope**: implemented, simulated and planned parts are labelled」 | W2 `examples_projects` **p.19** | 与评分说明的红线同向；决定了 README、报告、storyboard 三处都写清三分 | **强** |
| 日志是唯一数据源，指标只能由 JSONL 重算 | 「**Keep the steps in a schema field for logs, tests and debugging**」；「**prompt log recording version, change made and score**」 | W3 L09 **p.9**（为什么进日志而不是界面：printed reasoning persuades whether or not it is correct）、**p.10**（一次只改一处，记录版本/改动/分数） | 支撑"所有运行写 JSONL"这条硬规则；也为 manifest（model/temperature/seed/app_version）提供依据 | **强** |
| 五项复选框**从不预勾选** | 「**Recognition beats recall**」：再认是识别**已经可见**的选项，回忆才是无线索产出 | W2 L05 **p.8**（Norman 2013 的"knowledge in the world/head"）；p.9（suggestion chips、shown sources 把线索移进世界） | 支持"把候选项摊开让人再认"这一半；**不支持**"避免机械确认"（见 §2） | **中** |
| C0 无卡时的空态文案 | 「**Make the system's limits visible so people can revise their mental model**」（G1–G6 让能力边界与处境可见） | W1 L03 **p.12**（expectation gulf）、p.7（G1–G6 揭示 capability envelope） | 让"这个条件没有卡"成为可读状态，而不是看起来像坏了 | **中** |
| 把"可逆"和"可见"当作设计维度（背景动机） | 「第二个转变让**系统状态可见、动作可逆**，两者都是刻意的设计选择」 | W1 L01 **p.10** | 说明为什么卡同时要"可退回"与"可见"，为 L12 矩阵提供历史脉络 | **中**（历史叙事，不是规范） |

---

## 2. 对 `docs/compliance-check.md` §2.1 四个候选的判定（一手材料核对后）

| §2.1 原候选 | 判定 | 一手依据 |
|---|---|---|
| 从不预勾选 ↔ **默认效应 / 机械确认（confirmation fatigue）**；识别优于回忆 | **前半仍不支持；后半有一手锚点** | W1–W4 全部讲义 PDF 里没有"default effect"或"confirmation fatigue"。该说法出自 A1 引用的 Shihab et al. (2025)，属**文献**依据。"识别优于回忆"可引 W2 L05 **p.8**，但那只解释了"为什么摊开选项"，解释不了"为什么不预勾选"——预勾选的问题在于**替人做了判断**，这一点在本批材料里没有直接论述 |
| 拦截时列陈述文本 ↔ 系统状态可见性、错误信息用用户语言 | **升为强（换锚点）** | W4 L12 **p.12**（点名对象）+ W2 L06 **p.10**（show what was heard）。原候选里"错误信息用用户语言"没有对应页；Grice `manner`（W3 L07）是**会话准则**，不是错误文案原则 |
| 禁用 + 说明原因 ↔ 防错优于纠错；执行鸿沟 | **升为强（换措辞）** | W2 L06 **p.6**（两鸿沟）、p.10（slip 补救）、**p.4/p.5**（signifier）、W3 L07 **p.12**（clarify）。"防错优于纠错"不是讲义措辞，应写成"**用 signifier 与约束把错误拦在执行前**" |
| 空态文案 ↔ 状态可见性 | **中** | W1 L03 **p.12**「让系统的限制可见，以便人们修正心智模型」——可引，但只支持"状态要可见"，不专门支持"空态要写文案" |

**结论**：四条候选里，第 2、3 条在一手材料上可升为**强**（但要换锚点/换措辞），第 1 条的前半必须撤（改标文献依据），第 4 条保持中。

---

## 3. 两条必须避开的误配

| 不要这样写 | 为什么 | 正确说法 |
|---|---|---|
| 把 `docs/PROVENANCE.md`（开发溯源台账：original / reused / assisted）说成 L11 的 **Provenance** | L11 **p.10** 的四项要求是「**Resolvable / Specific and honest about coverage / Dated / Reportable**」——讲的是**答案的引文能否被点开到段落**。台账讲的是**工作的来源**。同名不同义 | 若要挂 L11，挂的是"答案可核查性"；台账本身挂 W1 的 accountability 与 W4 的 audit log（L12 讲 least privilege / complete mediation 那页） |
| 把"confirmation fatigue / 机械确认"写成课程概念 | 该词不在 W1–W4 任何一页 | 写成"**A1 文献依据（Shihab et al., 2025）**"，与课程概念分开列 |

---

## 4. 还缺什么（不影响上面 9 条强证据）

1. **§05 的"三种效度 / 指标菜单 / 四句 evaluation 段落"**：这批 PDF 里没有对应页。`W2/exp.pdf` 是观片指南（视频分段时间轴 + L1–L6 对照），不是评估方法论。要用这两条，需要评估方法论的讲义页（或在报告里改引 W3 L09 p.9–p.10 的"日志/版本/改动/分数"，那条是一手的）。
2. **G1–G18 全条目**：W1 L03 p.7–p.8 已按 G1–G6 / G7–G11 / G12–G18 分组说明，可直接引；若要逐条原文，需 L03 原始讲义（当前 PDF 即原始讲义，p.7–p.8 可读，够用）。
3. **L12 五项检查的逐项原文**：W4 L12 p.8 已逐项给出（shape / permission / precondition / confirmation / idempotency），够用。
