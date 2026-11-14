# 交付物对照检查（A2 Project Report）

本文件把课程评分说明逐条对到仓库里的实际证据，并单独检查四项横切要求：**伦理**、**可复现**、**数据泄漏**、**依赖锁定**。

- 检查对象：提交 `HEAD` 的工作树（提交前 148 个入库文件，本次检查新增 2 个），本机 Python 3.15.0，pytest 9.2.0，19 个 commit。
- 判定只有三种：**满足** / **部分满足** / **不满足**。"部分满足"一律写明**缺的是哪一半**，否则这个判定没有用。
- 每条结论都配一条可复现的命令或一个文件位置。凡是我没能验证的，写在第 7 节，不混进判定里。

---

## 0. 一句话结论

**工程交付物是完整的，被评的报告本体还不存在。**

四个评分项里，三个的实质证据都在（设计决策、交互实现与截图、架构与接口、开发溯源），但评分说明打分的是**报告**：abstract、约 1,000 词的 rationale、system diagram、references 目前都不存在。因此：

| 评分项 | 分值 | 判定 | 缺的那一半 |
|---|---|---|---|
| Design reasoning and scope | /30 | **部分满足** | 决策与取舍的证据齐全，但没有报告章节与 rationale 四列表；且**未点名 W1–4 的课程概念** |
| Developed interaction | /30 | **部分满足** | 有 3 张真实截图与 22 条接口测试，但没有报告里的交互说明；storyboard 未覆盖"拒绝建议/中途放弃"路径 |
| Architecture and technical reasoning | /20 | **部分满足** | 模块、接口、数据流、依赖都有文字与代码，但**没有 system diagram 图** |
| Development evidence and authorship | /20 | **满足** | 无（见 2.4 的证据清单） |

交付物清单：storyboards 与 repository/README 满足，其余五项（abstract、rationale、system diagram、references、首页词数）不满足。

---

## 1. 判定总览

| # | 要求 | 来源 | 判定 | 证据 |
|---|---|---|---|---|
| 1 | Abstract ≤ 300 词 | 评分说明 | **不满足** | 不存在 |
| 2 | Design rationale 约 1,000 词（上限 1,100） | 评分说明 | **不满足** | 素材在 `docs/SPEC.md`、`docs/PLAN.md`、`docs/rubric-mapping.md`，但无报告章节 |
| 3 | rationale 四列表（Design choice / Why / Evidence / Status） | 评分说明 | **部分满足** | `docs/rubric-mapping.md` §5 是"偏差表"，`README.md:109` 是开发记录；两者都不是课程要的那张表 |
| 4 | System diagram（盒子+箭头，标 implemented/simulated/planned） | 评分说明 | **不满足** | 有文字数据流（`docs/PLAN.md` §5），无图 |
| 5 | Storyboards，2–3 个使用实例 | 评分说明 | **满足** | `storyboards/1-c1-gate-closed.png`、`2-c1-gate-open.png`、`3-c0-baseline.png` + `storyboards/README.md` |
| 6 | Repository + README + 提交的 commit/release + 开发记录 | 评分说明 | **满足** | 19 个 commit；`README.md:84` 双版本标识；`README.md:109` 开发记录 |
| 7 | References（含复用材料致谢） | 评分说明 | **不满足** | 报告无 references；A1 的 11 条书目可复用；代码复用记录在 `docs/PROVENANCE.md` |
| 8 | 首页写总词数 | 评分说明 | **不满足** | 无报告 |
| 9 | README 说明 AI 使用 | 评分说明 | **满足** | `README.md:128` |
| 10 | 标注占位/未完成，不得把 planned 说成 implemented | 评分说明红线 | **满足** | `docs/SPEC.md` §3.0 状态表（MUST/SIM/PLAN/N/A）；`README.md` Project status 三分法 |

---

## 2. Rubric 四项逐条

### 2.1 Design reasoning and scope（/30）— 部分满足

评分说明的 Convincingly 档要求四件事：① 把设计连到问题；② 用证据论证**主要选择**；③ 论证**重大变更**与**范围妥协**；④ **清楚区分** developed 与 planned。

| 要求 | 现状 | 证据 |
|---|---|---|
| ① 设计←→问题 | 有 | `docs/SPEC.md` §1（RQ/H1–Hn）、§2（C0/C1 两条件）；A1 文献里"盲信 vs 前置治理"的 gap 被直接映射成 C1 的强制确认卡 |
| ② 主要选择有证据 | 有 | `docs/rubric-mapping.md` 逐条"评分项→要求→证据→测试名"；每个模块的验收命令与实测输出都留着 |
| ③ 重大变更与范围妥协 | 有，且**很强** | 八条拍板记录在 `docs/SPEC.md` §6.0（Q1–Q8）；Q8 的"原型优先"就是一次显式的范围妥协；`docs/rubric-mapping.md` §5 逐条记录与计划的偏差及理由（含 `Check.detail`、`summarise(tolerance)`、`recordings/<slug>` 这类不得不改的地方） |
| ④ developed/planned 区分 | 有 | `docs/SPEC.md` §3.0；`README.md` Project status |
| **评分说明要的那份东西** | **没有** | 无 abstract、无 1,000 词 rationale、无四列表 |
| **点名 W1–4 概念** | **没有** | 全仓库检索 `week 1-4`/`lecture`/`mental model`/`affordance`/`gulf of execution` **零命中** |

**这是最贵的一个缺口**：评分说明明确写 "Name the concept or guideline and explain how it informed your decision rather than simply listing terms"。我们现在只有工程理由（"因为不加门就能绕过"），没有把理由挂到课程概念上。

**补做**：写 rationale，并对至少三个决策点名课程概念。可用的映射（我建议，不是评分说明里的）：

| 决策 | 可对应的概念（需你确认是 W1–4 讲过的） |
|---|---|
| 卡上五项**从不预勾选** | 默认效应 / 机械确认（confirmation fatigue）；识别优于回忆 |
| 拦截时不列 item_id 而列**陈述文本** | 系统状态可见性、错误信息用用户语言 |
| 门未开时 `Generate` **禁用** + 说明原因 | 防错优于纠错；执行鸿沟 |
| C0 无卡时的空态文案 | 状态可见性、避免"看起来像坏了" |

### 2.2 Developed interaction（/30）— 部分满足

Convincingly 档要求：提交物与 storyboard 呈现**连贯的用户动作 / 系统响应 / 反馈或控制**，并**清楚区分 implemented / simulated / unfinished**。Not yet 的红线是"把 planned 或 simulated 说成 implemented"。

| 要求 | 现状 |
|---|---|
| 真实可交互的提交物 | **有**。`static/index.html` + `govern/web.py`；22 条测试打真实 loopback（`tests/test_web.py`） |
| storyboard 2–3 个实例 | **有**。三帧由 `tools/make_storyboard.py` 驱动**真实服务端**走完 C1 拦截→放行与 C0 直通后截图，不是手绘示意 |
| 逐帧的动作/响应/日志序列 | **有**。`storyboards/README.md` 帧帧对应日志事件号 |
| implemented/simulated/unfinished 区分 | **有**。页面顶部常驻 "Author self-test run (simulated)"；README 与 SPEC 状态表三分 |
| 红线风险 | **无**。没有把重放说成真模型、没有把脚本操作者说成被试 |
| **缺口 1** | 报告里没有对应章节（同上，报告本体不存在） |
| **缺口 2** | storyboard 只覆盖"勾满→放行"和"C0 直通"，**没有覆盖拒绝建议、中途放弃（`withdrawn`）与控制流**。评分说明要 "relevant feedback **or control**"，而"用户能否拒绝"正是本设计的控制面 |

**补做**：补第 4 帧（点击 Reject 后的 `suggestion_action(action=reject)` 与工作树不变），或把 `_close(withdrawn=True)` 的路径也截一帧。

### 2.3 Architecture and technical reasoning（/20）— 部分满足

Convincingly 档要求：图与解释说明**组件、流、依赖**如何支撑交互（**含智能行为**），且技术选择与边界与提交物一致。

| 要求 | 现状 | 证据 |
|---|---|---|
| 组件与接口 | 有 | `docs/PLAN.md` §4 每个模块的签名；`govern/` 11 个模块职责 |
| 数据流 | 有（文字） | `docs/PLAN.md` §5：任务→影响集→卡→门→建议→评分→JSONL |
| 依赖与理由 | 有 | 零第三方运行时依赖；`requirements-dev.txt` 只固定 pytest |
| 智能行为在哪 | 有 | `govern/llm.py` 双模式（replay/live）、录制按请求 sha 索引、模型一致性校验 |
| **system diagram** | **没有** | 这是评分说明点名要的图，文字数据流替代不了 |

**补做**：一张图即可（盒子+箭头+短标签）。建议分层画：`corpus/` → `impact` → `card`+`gate` → `llm` → `score` → `log` → `experiments`/`analysis`，虚线框标 simulated，灰框标 planned（`analysis` 的 purge 重算）。

### 2.4 Development evidence and authorship（/20）— 满足

Convincingly 档要求：开发记录把重大变更连到**学生的决策与检查**，区分 **original / reused / assisted**，并给出**审阅并改写 AI 输出**的实例。

| 要求 | 现状 | 证据 |
|---|---|---|
| 把变更连到决策与检查 | 有 | 19 个 commit，信息写"改了什么+为什么"；`README.md:109` 开发记录 |
| original/reused/assisted 三分 | 有，且**逐行强制** | `docs/PROVENANCE.md` 23 行，`original=9 / reused=3 / assisted=11`；`govern/provenance.py` 校验 assisted 行必须有 decision + check，`-` 不算数 |
| 审阅并改写 AI 输出的实例 | 有多个 | 见下表 |
| 来源可核 | 有 | `reused` 行指向 `参考代码库/` 的真实路径，校验器会检查文件存在 |

**已经记录在案的自纠实例**（这是这一项最强的证据，不是事后包装）：

1. 卡片复选框第一版渲染成 `checked disabled`——等于把 A1 说的"机械确认"失败模式做进界面 → 改为从不预勾选，并用 `test_html_never_renders_a_pre_ticked_checkbox` 钉死。
2. `corpus._run_hidden` 依赖 pytest，导致裸 Python 违反"一条命令跑测试" → 抽出 `govern/hidden.py` 子进程运行器。
3. `provenance._filled()` 把 markdown 的 `-` 当内容，"删掉 check 仍通过" → 判为空，加测试。
4. README 自称 210 词（手算错值，实测 886）→ 加 `tools/word_count.py --check` 并由 `tests/test_end_to_end.py` 覆盖。
5. `_statement()` 回落后仍超 120 字符上限 → 硬截断。

**判定为"满足"的前提**：这一项的证据在 README 与 PROVENANCE 里，报告只需**引用**它们，不必重写。

---

## 3. 横切检查一：伦理

### 3.1 知情同意

| 检查点 | 结果 | 证据 |
|---|---|---|
| 无同意则拒绝开始 | **满足** | `govern/session.py` 的 `Session.start()` 抛 `ConsentError`；测试 `tests/test_session.py::ConsentTests` |
| 同意状态入日志 | **满足** | `session_start` 记 `consent_given: true` 与 `consent_version: "SIM-AUTHOR"` |
| 同意**文本**与流程 | **不满足** | 仓库里没有同意书、没有信息页、没有退出机制说明 |
| 伦理审批 | **不适用/未记录** | 本期无人类被试，因此没有审批；但**若报告不写清，读图的人会以为有真人** |

判定：**部分满足**。机制做对了，文书没有。因为 Q1 决定不招真人，实际风险为零；但评分说明的 Developed interaction 明确禁止"把 simulated 说成 implemented"，所以报告必须一句话说清：三张截图来自**作者自测的脚本会话**，`consent_version=SIM-AUTHOR` 就是标记。

### 3.2 匿名化

| 检查点 | 结果 | 证据 |
|---|---|---|
| 被试标识为伪名 | **满足** | `participant_id` 只有 `P01`…`P10` |
| 无直接标识（姓名/邮箱/IP/UA） | **满足** | 日志字段全集见 4.1；扫描器 12/12 干净 |
| 无"伪名↔身份"映射文件 | 满足（不存在），但**无书面声明** | 建议在报告里写一句"不保存映射，因此无法回溯到个人" |
| 删除入口与保留期 | **满足** | `python -m govern.log --purge --before <date>`；`retention_days: 90` |

判定：**满足**（对现有数据），附一条声明建议。

---

## 4. 横切检查二：数据泄漏（被试信息是否进日志）

### 4.1 日志里到底有什么

`runs/E-SIM-01/logs/P01/S-baseline-P01-T-L01a-r0.jsonl` 第 1 行的完整字段：

```
schema_version event_id(随机 UUID) seq ts phase event_type
session_id(S-<condition>-<participant>-<task>-r<n>) participant_id(P01) condition(C0|C1)
app_version model_id model_temperature seed
task_id(null) task_index(null) pair_id(null)          ← 会话级事件不重复任务字段
consent_version("SIM-AUTHOR") consent_given(true)
prior_years(0.0) llm_freq("never") lang_familiarity(5)  ← 自评协变量
schedule_id("EXP-E-SIM-01") device("author-workstation")
```

**没有**：姓名、邮箱、学号、IP、User-Agent、窗口标题、剪贴板、自由文本（提示词只存 sha256 与长度）。

### 4.2 实测扫描

```
python -m govern.log --scan <每个 jsonl>      → 12/12 文件 "ok: 0 identifying string(s)"
python -m govern.log --validate <某文件>      → "ok: 11 line(s) checked, 0 invalid"
python tools\scan_secrets.py                 → "ok: 0 finding(s) in 154 files"
```

判定：**满足**。

### 4.3 两条加固建议

1. ~~`device` 是**自由文本**~~ → **已修**。`device` 现在是受控枚举：取值只能来自 `config/config.json` 的 `device_kinds`（`author-workstation` / `reviewer-workstation` / `lab-workstation` / `unknown`），每项必须是 `^[a-z0-9]+(?:-[a-z0-9]+)*$` 的 slug，`config.load()` 与 `log.validate()` 双重拒绝列表外的值（含主机名 `DESKTOP-3F2A9C`、用户名 `alice-laptop`、公司名、大小写不符、空串）。顺带修掉一个真缺陷：`validate()` 原先对 `session_start` 提前返回，导致该事件的字段从未被校验——`device` 恰好在这个事件上，不修就等于没生效。见 SPEC 4.2/4.5 第 4、9 条与 M7 验收 8；证据 `DeviceKindTests`、`SessionStartCoverageTests`、`DeviceVocabularyTests`。
2. `prior_years`/`llm_freq`/`lang_familiarity` 是自评协变量，属"准标识"（配合小样本可能反推个人）。本期全为常数、无风险；转真人研究时应降到区间化取值。

---

## 5. 横切检查三：可复现（一条命令从零复现）

### 5.1 实测方法

`git clone` 在本机沙箱**不可用**（`sh.exe: fatal error - couldn't create signal pipe, Win32 error 5`），所以改用等价路径：`git archive --format=zip` 导出 `HEAD` 的完整树（185 个条目、**无 `.git`**）解压到干净目录，再用**裸 `python`**（不是 `.venv`）跑：

```
python -m govern.run --selftest
python -m experiments.run --config conditions.yaml
python -m analysis.run --runs runs --run-id E-SIM-01 --out analysis
```

三条全部通过，产出 `runs/E-SIM-01/`（12 条 JSONL + `manifest.json` + `config.snapshot.json` + `metrics.json`）、`analysis/results.xlsx`、`analysis/captions.md`、4 张 PNG。**无网络、无 API key、无第三方运行时依赖。**

### 5.2 但"可复现"要分层说，否则是假话

| 层次 | 可复现？ | 说明 |
|---|---|---|
| 流程（三步命令能跑通） | **是** | 5.1 实测 |
| 漏斗计数（事件数、勾选数、失败测试数、债务/漏洞计数） | **是** | 重放录制是确定性的 |
| 字节级日志 | **否** | `ts`、`event_id`(UUID)、`elapsed_ms`(墙钟) 每次都不同 |
| 统计输出（同一 run） | **是** | 同一份日志重算，`results.xlsx` 字节相同（已测） |
| 统计输出（重跑实验后） | **否** | 实测：原 `runs/` 得 `Task time` 差 −2.33、p=0.058、0 个存活；导出树重跑得 −5.00、p=0.035、1 个存活 |

**这条必须写进报告**：在这套装置里 `elapsed_ms` 是脚本的墙钟开销，重跑会漂，所以**不能**把"任务时长的显著性"当成发现来报。稳定的是漏斗类指标——而它们在本期由构造决定（两个条件收到同一份重放建议），所以差值恒为 0。

### 5.3 另一处可复现性缺口

`--batch --participant P01` 每个 pair 只给一个条件，6 条会话全部 unpaired。此前它会打印空表并 `exit 0`，看起来像"跑完了没差异"。**本次检查中已修**（见第 6 节）。

### 5.4 一条命令（P2 已补）

`tools/reproduce.ps1` 把 5.1 的三条命令与 AGENTS §5 的四项自检串起来，任一步非零即停：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\reproduce.ps1
```

在 `git archive` 导出的干净树上实测：成功路径 `ok: 6 of 6 steps passed`（exit 0，12 份 JSONL、`results.xlsx`、4 张 PNG、6 份转录、`reproduce.json` 全部落在 `_repro/<时间戳>/`）；把 `config/config.json` 改成非法 JSON 后 `FAILED at step 1: self-check: standard-library test suite`（exit 1，后续步骤不跑）；同一 `-OutDir` 重跑与 `-OutDir ...\runs\x` 都被拒绝（exit 2）。**补这个脚本时暴露了三处真问题**（见第 6 节第 6–8 条）。

---

## 6. 本次检查中已顺手修掉的

| # | 问题 | 修法 | 证据 |
|---|---|---|---|
| 1 | 单侧 run 打印空表并 `exit 0`，等于把"设计错误"伪装成"没有差异" | `Analysis.paired_counts`；`run._build()` 在没有任何配对时**不写输出**；`main()` 打印 `fail: … no task ran in both conditions …` 并 `exit 1` | 测试 `tests/test_analysis.py::StudyTests::test_a_run_with_no_complete_pair_is_refused` |
| 2 | 表格里 p 与状态标记粘连（`0.035struct`） | 改成固定宽度分隔列 | `python -m analysis.run …` 表格 |
| 3 | `tools/make_storyboard.py` 带 UTF-8 BOM，`compile()` 报 `SyntaxError: invalid non-printable character U+FEFF` | 去掉 BOM；新增测试防再犯 | `tests/test_dependencies.py::SourceEncodingTests` |
| 4 | "零第三方运行时依赖"只是声明，没有测试 | 新增 `tests/test_dependencies.py`：按 AST 扫 `govern/`、`analysis/`、`experiments/`、`tools/` 的 import，只允许标准库与本地包；断言不存在 `requirements.txt` | 9 条测试全绿 |
| 5 | 测试期依赖未锁定 | 新增 `requirements-dev.txt`，`pytest==9.2.0` 精确固定，并附本机 pip 不可用时的绕行说明 | 同上 `DevRequirementsTests` |
| 6 | `govern/config.py` 的 `DEFAULT_PATH` 是**相对路径**，配置随当前目录走：在干净树里跑却读到工作区的 `config/config.json`，于是"破坏配置必定失败"的验证一开始根本没生效 | 改为 `Path(__file__).resolve().parent.parent / "config" / "config.json"`；`tools/reproduce.ps1` 每步 `Push-Location $Root` | 破坏树内配置后 `FAILED at step 1`；`python -m unittest discover` 仍 `OK` |
| 7 | `govern.provenance --check` 要求 `reused` 来源在磁盘上存在，而 `参考代码库/` 被 `.gitignore` 排除 ⇒ **干净检出上这条自检必红**（4 条测试连带红） | 新增 `external:` 前缀：显式标注"工作区外来源"，且该前缀行**必须**填 `decision`，否则报错 | `tests/test_provenance.py` 新增 3 条；干净树 `ok: 29 rows` |
| 8 | `tests/test_provenance.py` 的夹具指向 `参考代码库`（干净检出里不存在）⇒ 测试只能在本人机器上过 | 夹具改用 `docs/` 与 `docs/does_not_exist.py` | 干净树 446 条测试全绿 |

---

## 7. 补做建议（按性价比排序）

| 优先级 | 事项 | 为什么 | 验收 |
|---|---|---|---|
| **P0** | 写报告本体：abstract（≤300 词）、rationale（≈1,000 词，不超 1,100）、四列表、references、首页总词数 | 这是**唯一直接掉分**的缺口；素材已经齐了，只差组装 | 首页有总词数；`tools/word_count.py` 能核对正文长度（可扩成通用计数器） |
| **P0** | rationale 里点名 **W1–4 的课程概念**，每个决策一句"概念 → 如何影响决策" | 评分说明明文要求；现在全仓库零命中 | 至少 3 个决策各自点名一个概念 |
| **P1** | System diagram（一图） | 评分说明点名要；Architecture 项靠它拿 Convincingly | 盒子+箭头+短标签；虚线=simulated，灰=planned |
| ~~P1~~ **已完成** | 补第 4 张 storyboard：拒绝建议 / 中途放弃 | 评分说明要"feedback **or control**"；控制面目前没图 | 已做：`storyboards/4-c1-reject.png` + `4-c1-reject.promises.txt`（`suggestion_action(action=reject)`，工作树逐字节不变） |
| ~~P2~~ **已完成** | `device` 改枚举；报告写"不保存伪名映射" | 4.3 的两条硬化；转真人研究前必须做 | 已做：`config.device_kinds` + `log.validate()` 拒绝列表外取值；SPEC 4.6 明写"从未建立伪名与真实身份的映射表" |
| ~~P2~~ **已完成** | `tools/reproduce.ps1`：把 5.1 的三条命令 + 四项自检合成一条 | "一条命令复现"目前是三条 | 已做：`powershell -NoProfile -ExecutionPolicy Bypass -File tools\reproduce.ps1` → `ok: 6 of 6 steps passed`；失败在第 N 步即停并打印步骤名与退出码；拒绝已存在的 `-OutDir`、拒绝写入 `runs/` 或 `analysis/` |
| ~~P3~~ **已完成** | dev 依赖加 hash（`--require-hashes`）或 vendor 轮子 | 目前只固定 pytest 主版本，传递依赖未固定 | 已做：`requirements-dev.txt` 现在钉住 9 个包（pytest + 8 个传递依赖，按环境标记区分）并列出每个发布**全部 81 个文件**的 sha256（wheel 与 sdist 都给，因为 pip 按平台选文件）。逐个下载比对索引摘要：81/81 一致、无 yanked。**本机无法执行 `pip install --require-hashes`**（沙箱里 pip 的临时解包目录不可写，`PermissionError`），故改由三条替代证据验证：① 81 个文件的 sha256 与索引摘要逐个相等；② `.venv` 中 512 个已安装文件与这些 wheel 逐字节相同（即跑出 442 条测试的环境就是被钉住的那批包）；③ `pip install --dry-run --no-index --require-hashes -r requirements-dev.txt` 通过解析与钉住检查（只因 `--no-index` 无包可装而失败）。在能写临时目录的机器上，`pip download --require-hashes -r requirements-dev.txt -d tmp` 即为等同验证 |

---

## 8. 我没有验证的

诚实清单，避免这份文件被当成"全都验过了"：

1. **没有在干净机器上跑过**。只在本机导出树上跑通；没有第二台机器、没有 Windows 之外的系统。
2. **UI 没有真人用过**。三张截图来自无头 Chrome 驱动脚本；我没有用鼠标点过一遍，也没有做可用性观察。
3. **`live` 模式没有真调过外部模型 API**。只在 `tests/test_llm.py` 的回环 `_Stub` 服务器上验证过。
4. **没有测并发压力**。`max_parallel: 2` 只在小规模下跑过（12 会话）。
5. **评分细则的档位→分值映射未知**。评分说明只给四档描述语与总分，没有说明档位如何映射到分数，所以本文件只判断"落在哪一档"，不预测分数。

## 9. 最终交付审计（2026-11-14 晚）

交付前的最后一次运行，命令与输出逐字抄录；任何一条失败都不算通过。

| # | 项目规定的检查 | 命令 | 结果 |
|---|---|---|---|
| 1 | 标准库测试套件 | `python -m unittest discover -s tests -q` | `Ran 446 tests in 40.283s` / `OK (skipped=2)` / exit 0 |
| 2 | 一条命令自检 | `python -m govern.run --selftest` | `ok: 6 tasks, 6 cards` / exit 0 |
| 3 | 密钥与端点扫描 | `python tools/scan_secrets.py` | `ok: 0 finding(s) in 176 files` / exit 0 |
| 4 | 溯源台账 | `python -m govern.provenance --check` | `ok: 31 rows, 11 modules covered (original=10, reused=3, assisted=18)` / exit 0 |
| 5 | 一条命令复现 | `powershell -NoProfile -ExecutionPolicy Bypass -File tools\reproduce.ps1` | `ok: 6 of 6 steps passed` / exit 0（写入 `_repro/20261114-230839/`；`runs\`、`analysis\`、`dist\` 未被触碰） |

复现那一步产出的表（与仓库自带的 `runs/E-SIM-01` 不同，原因见 §5.2）：

| condition | sessions | escape rate | mean debt Δ | OTI | mechanical |
|---|---|---|---|---|---|
| C0 | 6 | 1.00 | -3.67 | 0.00 | 0.00 |
| C1 | 6 | 1.00 | -3.67 | 0.00 | 1.00 |

其中 `Task time` 的配对检验这一次给出 `diff = -16.33`、`p = 0.036`，并且 `multiplicity: 1 tests, 1 survive Holm at alpha=0.05`；仓库自带那一轮是 `p = 0.058`（0 个存活）。**同一份代码、同一份配置，只是墙钟时长的抽样不同**，所以这一项既不稳定也不可引用——报告 §4 已按这个事实改写（三次运行分别 0.058 / 0.036 / 0.035）。

交付快照：`python tools/make_release.py --build` → `dist/a2-1.0.0.zip`（161 条目、696,791 字节、`sha256:07651cd4ac339adc4a23104abb5541b5591dda4883bf7fffce2464989266b40c`，对应提交 `d616cd9` 的树），`--verify` 通过，两次构建同一 hash。记录这个 hash 的文字本身也在归档里，所以之后重建必然得到不同 hash——复核请看 `docs/rubric-mapping.md` §2j 的"自指说明"。

**仍未验证**：§8 的五条全部仍然成立（干净机器、真人使用 UI、`live` 真调 API、并发压力、档位→分值映射）；再加一条，`pip install --require-hashes` 在本机跑不了（§7 的 P3 行已写明替代证据）。**本节不声称**任何真人研究或真实模型调用已经完成。
