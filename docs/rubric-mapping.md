# Rubric mapping — 评分项 → 证据追溯表

> **这个文件不是什么。** 它不推断分数，也不复述评分标准。A2 评分细则的档位描述语原文见
> [SPEC.md](SPEC.md) 0.2；这里只做一件事：**把每个评分项落到仓库里可被第三方复核的证据上**
> （文件:行号、测试名、可复现命令）。没有证据的行一律标 `待补`，不写"已完成"。

当前覆盖：**M0（骨架）、M1（语料工厂）、M2（中/高难度两对）、M3（影响分析器 = SPEC M4）**。
后续里程碑每完成一个，补对应行。
行号会随代码改动漂移，**以测试名为主键**，行号只作快速定位。
最后更新：2026-11-14。

---

## 1. 四个评分项 → 证据

| 评分项（A2） | 本项目落点 | 证据（文件:行号 / 测试名） | 状态 |
|---|---|---|---|
| **Design reasoning and scope** | SPEC 1–2 章（RQ / 假设 / 设计）+ 每次范围收缩的记录 | `docs/SPEC.md` 6.0 决议表（Q1–Q8 八条拍板）；`docs/SPEC.md` 3.0 交付集表（MUST / SIM / PLAN / N/A 四态）；`docs/PLAN.md` 里程碑 M0–M11 | M0–M2 已落地，其余按里程碑推进 |
| **Developed interaction** | SPEC 第 3 章模块清单；M4 评估卡、M5 渲染、M6 门控 | `govern/corpus.py:126` `check_task()` 产出的可运行仓库，是"用户任务"的输入侧；影响分析（卡的原料）已由 `govern/impact.py:170` `analyze()` 提供 | `待补`（交互侧 M4–M6，卡与门控尚未实现） |
| **Architecture and technical reasoning** | `govern/` 模块边界 + 零运行时依赖约束 | `AGENTS.md` §2 六条硬规则；`govern/patch.py:102` `apply_unified_diff()`（不依赖 git/patch 的离线打补丁）；`govern/corpus.py:79` `_run_hidden()`（隐藏测试在副本中执行，语料只读）；`govern/impact.py:170` `analyze()`（纯 `ast`，无模型、无网络，见 `tests/test_impact.py:122` 的跨进程哈希一致性） | M0–M3 已落地 |
| **Development evidence and authorship** | 里程碑即提交单元；每个验收都有命令与输出 | `docs/rubric-mapping.md` 本文件第 2 节；`git log` 每次提交对应一个里程碑；证据命令见第 4 节 | 持续维护 |

---

## 2. 语料验收标准 → 证据（SPEC M1 五条 + M2 的两条加严）

M2 之后验收对象是 **6 个任务 / 3 对 / 三层难度**，下表逐条给证据。

| # | 验收标准（SPEC） | 证据 | 覆盖测试 |
|---|---|---|---|
| 1 | 初始状态基线被显式记录，失败原因须是"重构未做"而非环境缺依赖 | `govern/corpus.py:94` `_failure_reason()`；6/6 实测基线原因均为 `AssertionError: total must return integer minor units, got float` | `test_baseline_fails_for_refactor_reason`（`tests/test_corpus.py:75`，显式拒绝 `ImportError` / `ModuleNotFoundError` / `no tests ran` / `ERROR`） |
| 2 | 应用 gold patch 后隐藏测试全绿，6/6 成立 | `govern/corpus.py:126` `check_task()` 在副本上打补丁后重跑；`govern/patch.py:102`；CLI 实测 `gold 6/6` | `test_gold_patch_turns_hidden_tests_green`（`tests/test_corpus.py:70`） |
| 3 | 每个实例至少 1 个全局可变状态 + 1 个跨模块隐式契约，且都在 `impact_label_set` 中 | `corpus/T-L01*/impact_labels.json`（1 全局 + 1 契约）；`corpus/T-L02*`（1 全局 + 2 契约：report / export）；`corpus/T-L03*`（**2 全局**：cache + `LEDGER`，2 契约：export / audit）。生成逻辑 `tools/make_repo.py:653` `_labels()` | `test_each_task_has_global_state_and_contract`（`tests/test_corpus.py:98`）、`test_labels_are_complete`（`:83`） |
| 4 | 同 `pair_id` 两实例在"改动文件数 / 需修改函数数 / 隐藏测试数"上差异 ≤ 20% | 实测 `pairs 3/3 within 20%`（同模板生成，差异恒为 0）；阈值来自 `config/config.json` 的 `pair_tolerance`，不写死在代码里 | `test_every_pair_is_matched_within_tolerance`（`tests/test_corpus.py:105`）、`test_check_command_prints_summary`（`:134`） |
| 5 | 仓库内不得出现指向答案的注释、TODO 或测试名泄漏 | `govern/corpus.py:53` `scan_leaks()`（扫 `gold` / `solution` / `fixme` / `todo` / `oracle` / `hidden test`）；6/6 实测 `leak_free=True` | `test_repositories_do_not_leak_the_answer`（`tests/test_corpus.py:88`） |
| 6 | **M2 加严**：难度阶梯必须真实存在（不是同一套代码改个名字） | 变更文件数 3 → 4 → 5，层内成对相同：L 只有 `state/core/reports`；M 加 `export.py` 与裸 `except`；H 再加 `audit.py`、`eval()` 折扣表达式、可变默认参数 `LEDGER` | `test_higher_strata_touch_more_files`（`tests/test_corpus.py:127`）、`test_strata_cover_low_medium_high`（`:47`） |
| 7 | **M2 加严**：配对结构必须可核对（一对两任务同层、同规模） | `tools/make_repo.py:628` `STRATUM_SHAPE` 是唯一真源；`files_to_change` 由 diff 实测得出（`tools/make_repo.py:707` `build_corpus()` 内 `len(patch.changed_files(diff))`），不是手写常数 | `test_each_pair_has_two_tasks_of_one_stratum`（`tests/test_corpus.py:39`）、`test_declared_file_count_matches_patch`（`:120`） |

**语料只读性**：`test_check_all_is_read_only`（`tests/test_corpus.py:93`）对整个 `corpus/`
做 SHA-256 树摘要，检查前后必须一致 —— 检查器不得污染材料。

**可重建性**：`test_factory_is_deterministic`（`tests/test_corpus.py:147`）要求工厂两次调用字节相等；
`test_committed_corpus_matches_factory`（`:158`）要求提交的 `corpus/` 与工厂输出逐字节一致 ——
语料是**生成物**，不允许手工编辑。

---

## 2b. 影响分析器验收 → 证据（SPEC M4 五条，被 PLAN 编为里程碑 M3）

命名提醒：**SPEC 的 M4 就是 PLAN 的 M3**（PLAN 第 248 行把"影响分析器（M4）"排在里程碑 M3）。
验收命令：`python -m govern.impact --selftest`。

| # | 验收标准（SPEC M4） | 证据 | 覆盖测试 |
|---|---|---|---|
| 1 | 6 个 gold patch 上 `recall = 1.0`、精确率 ≥ 0.8（A-9） | `govern/impact.py:284` `recall_precision()`；实测 6/6 任务 `recall=1.00 precision=1.00`；阈值来自 `config/config.json` 的 `impact_recall_min` / `impact_precision_min` | `test_recall_is_perfect_on_every_task`（`tests/test_impact.py:64`）、`test_precision_meets_the_configured_floor`（`:71`） |
| 2 | 区分度：仅改函数内部 vs 改变跨模块契约，`risk_level` 必须不同 | `govern/impact.py:272` `risk_level()`：有契约 → `high`，只有全局/副作用 → `medium`，都没有 → `low`；两个构造用例内联在测试里 | `test_contract_change_is_high_risk`（`:150`）、`test_internal_only_change_is_low_risk`（`:156`）、`test_the_two_cases_differ`（`:162`） |
| 3 | 健壮性：空 patch、语法错误文件、单文件仓库都不抛未捕获异常，返回明确错误码 | `govern/impact.py:143` `_load()` 把 `SyntaxError` 转成 `category="other"` 条目；`analyze()` 对不存在的目录返回 `other` 条目而不是抛异常 | `test_empty_repository_returns_an_empty_set`（`:170`）、`test_syntax_error_is_reported_not_raised`（`:177`）、`test_single_file_repository_is_fine`（`:185`）、`test_missing_repository_returns_an_other_item`（`:191`） |
| 4 | 交互可接受：单次分析 < 2 s（最大实例上测） | 实测最大实例（H 层）单次 **4.4 ms**，5 次平均断言 < 2 s | `test_analysis_is_under_two_seconds_on_the_largest_task`（`:199`） |
| 5 | 输出确定性：同一输入两次运行 `impact_set_hash` 相同 | `govern/impact.py:265` `impact_hash()` 对已排序条目做 SHA-256；条目排序键为 `(category, symbol, files, detail)`，与文件遍历顺序无关 | `test_same_input_same_hash`（`:116`）、`test_hash_is_stable_across_processes`（`:122`，子进程重算，抓 set/dict 迭代序） |

**为什么 recall=1.00 不等于"背答案"**

- 标签 `impact_labels.json` 是在 **M2** 写下的，分析器是 **M3** 才有的，且 `analyze()` 只读仓库 AST，从不读标签文件。
- 契约的操作化定义写在模块 docstring 里：**某个模块的顶层"值"（不是函数）被 ≥ 2 个包内模块读取，则这些读取者对同一份假设构成契约**；锚点是其余读取者实际调用的那个模块。
- 反向证据：`test_an_extra_reader_adds_a_contract_and_costs_precision`（`tests/test_impact.py:96`）往真实仓库里加一个读取 `state.TAX_RATE` 的新模块，断言分析器**新增**一条未标注契约、精确率随之降到 1.0 以下 —— 说明输出确实由代码驱动。

**精度口径（诚实声明）**：`recall_precision()` 只在标签列出的两类（`global_var`、`cross_module_contract`）上算分母；
`side_effect` / `test_impact` / `other` 是为评估卡（M4/M5）服务的咨询性条目，标签从未打算穷举它们，把它们计入分母只会惩罚分析器的有用性。

---

## 3. 模块级证据

| 模块 | 状态 | 关键入口 | 自检 / 测试 |
|---|---|---|---|
| `govern/patch.py` | 新增（M1） | `parse()` `:37`；`changed_files()` `:91`；`apply_unified_diff()` `:102` | `tests/test_patch.py`（5 条：单 hunk、多文件、新建文件、上下文不匹配、目标目录缺失） |
| `govern/corpus.py` | 扩展（M2） | `check_task()` `:126`；`check_all()` `:158`；新增 `_pair_summary()` `:165`、`summarise()` `:187`（多输出 `pairs N/N within X%`） | `tests/test_corpus.py`（17 条）；`python -m govern.corpus --check` → `ok: 6 tasks, gold 6/6, pairs 3/3 within 20%` |
| `tools/make_repo.py` | 扩展（M2） | `DOMAINS` `:29`（6 个域）；`_files()` `:577` 按层分派；`_labels()` `:653` 从 diff 反算文件数；`build_corpus()` `:707` | `python tools/make_repo.py --selftest` → `ok: 61 corpus files match the factory` |
| `govern/impact.py` | 新增（M3 = SPEC M4） | `analyze()` `:170`；`recall_precision()` `:284`；`impact_hash()` `:265`；`risk_level()` `:272` | `tests/test_impact.py`（18 条：recall/precision、负对照、风险分层、健壮性、确定性、性能、CLI）；`python -m govern.impact --selftest` → `ok: recall=1.00 precision=1.00 on 6 tasks (min recall 1.00, min precision 0.80)` |
| `corpus/` | 数据 | `corpus/index.json`；`PAIR-01`=`T-L01a`(billing)/`T-L01b`(loans) 层 L；`PAIR-02`=`T-L02a`(ticketing)/`T-L02b`(payroll) 层 M；`PAIR-03`=`T-L03a`(inventory)/`T-L03b`(fleet) 层 H | `test_index_holds_three_pairs`（`tests/test_corpus.py:34`）、`test_every_task_directory_is_complete`（`:51`） |

**三层坏味道的递进（这是"难度"的操作化定义）**

| 层 | 坏味道 | 隐藏测试数 |
|---|---|---|
| L | 浮点金额、模块级缓存、报告重复推导税额 | 3 |
| M | + 三处重复的舍入、裸 `except:`、CSV 导出与报告各算一套 | 4 |
| H | + `eval()` 执行折扣表达式、可变默认参数 `LEDGER` 累积、审计模块用 `int()` 截断代替四舍五入 | 6 |

---

## 4. 复现命令（评审者用）

```powershell
# 全量测试（pytest 与 unittest 都能跑；本机用 .venv 里的 pytest 9.2.0）
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m unittest discover -s tests -q

# 语料验收（M1/M2 的对外命令）
.\.venv\Scripts\python.exe -m govern.corpus --check

# 语料可重建性
.\.venv\Scripts\python.exe tools\make_repo.py --selftest

# 影响分析器验收（M3 = SPEC M4）
.\.venv\Scripts\python.exe -m govern.impact --selftest

# 项目自检
.\.venv\Scripts\python.exe -m govern.run --selftest
```

> 说明：`.venv/` 只是本机开发工具链（pytest 属**测试期**依赖，不进入运行时）；
> 交付代码在 `govern/` 与 `tools/` 内，只用标准库，`python -m govern.corpus --check` 在裸 Python 3.11+ 上同样可用。

---

## 5. 与 `docs/PLAN.md` 的接口偏差（主动记录）

| 偏差 | 原因 | 影响 |
|---|---|---|
| `Check` 增加 `detail: str = ""` | 失败时要能一眼看出是"补丁打不上"还是"隐藏测试没过"，否则验收输出无法自证 | 纯附加字段，带默认值，不破坏 PLAN 的构造约定 |
| `govern/corpus.py:105` 增加 `changed_files()` 包装 | 测试需要"补丁改了几个文件"，避免测试直接依赖 `govern.patch` 的内部对象 | 只读包装，无新语义 |
| 新增模块 `govern/patch.py` | PLAN 只写了"gold patch 要能应用"，未指定实现方式；引入 `git`/`patch` 会违反"零运行时依赖" | 提供 `parse` / `apply_unified_diff` / `changed_files` 三个公开函数，并有独立测试 |
| `summarise()` 增加可选参数 `tolerance`（M2） | PLAN 的验收命令要求输出 `pairs 3/3 within 20%`，20% 必须来自 `config/config.json` 而非代码字面量；测试需要注入不同阈值来验证判定逻辑 | 默认值 `None` 时自行读 config，旧调用 `summarise(checks)` 行为不变 |
| `--check` 的汇总行文本改变（M2） | 同上，PLAN 第 247 行把该行定为 M2 的验收判据：`ok: 6 tasks, gold 6/6, pairs 3/3 within 20%` | 仅影响 stdout 文本；原有的逐任务 `ok/FAIL` 行保留 `labels=` 字段不变 |
| 新增 `govern/impact.py` 的 `risk_level()`（M3） | SPEC M4 验收 2 要求 `impact_set` 带"风险等级"，但 PLAN 的 `ImpactSet` 数据类只有 `items` 一个字段；往冻结数据类加字段会改动 PLAN 定的接口 | 纯附加的模块级函数 `risk_level(ImpactSet) -> str`，`ImpactSet` 本身不变 |
| 新增 `impact_hash()`（M3） | SPEC 4.3 的 `card_shown` 事件与 2.3 的复现性判据都需要 `impact_set_hash`，PLAN 的接口清单里没有提供函数 | 纯附加函数，返回 `sha256:...`，不改任何已有签名 |
| 新增 `ImpactSet.of(category)`（M3） | 按类别取条目在测试、`recall_precision()` 与后续卡片里反复出现，作为方法比三处重复列表推导更清楚 | 冻结数据类的只读辅助方法，不增加状态 |
| `analyze(repo, intent)` 不使用 `intent`（M3） | 若让任务措辞影响输出，同一快照会给出不同 `impact_set_hash`，破坏 SPEC 2.3 的复现性；措辞只在卡片层用于排序 | 签名按 PLAN 保留，参数被显式丢弃并写在 docstring 里，有 `test_hash_ignores_intent_wording` 兜底 |
| `recall_precision()` 只在两类标签上算精度（M3） | 标签文件只标注全局变量与跨模块契约（SPEC M4 验收 1 与 A-9 的原话），`side_effect`/`test_impact` 属咨询性条目 | 精度口径变窄，但在文档与 docstring 里写明；负对照测试保证精度仍会随代码变化 |

---

## 6. 明确没有做的（避免把 planned 说成 implemented）

- 没有采集任何人类被试数据；`M2` 是 **SIM**，`M10` 是 **N/A**（SPEC 3.0）。
- 没有真实 LLM 调用（`govern/llm.py` 属 M6，尚未实现，`corpus/` 与 `recordings/` 均无模型交互）。
- 影响分析器（SPEC M4 / PLAN M3）**已实现**，但它只做静态分析：不做语义推断、不读 diff、不调模型。
  它能识别的"契约"是"被 ≥ 2 个包内模块读取的顶层值"这一操作化定义（见 `govern/impact.py` docstring），
  因此它**不会**发现"两个模块各自实现同一算法"这类纯语义重复。
- 评估卡、门控、日志、LLM 客户端（M4–M7）尚未实现，所以"用户动作 → 系统响应"的交互链路目前不可演示。
- 六个种子仓库是**自建语料**（Q4 拍板的结果），不是真实开源仓库的历史；它们只用于让"影响分析 recall / precision"可判分。
