# Rubric mapping — 评分项 → 证据追溯表

> **这个文件不是什么。** 它不推断分数，也不复述评分标准。A2 评分细则的档位描述语原文见
> [SPEC.md](SPEC.md) 0.2；这里只做一件事：**把每个评分项落到仓库里可被第三方复核的证据上**
> （文件:行号、测试名、可复现命令）。没有证据的行一律标 `待补`，不写"已完成"。

当前覆盖：**M0（骨架）、M1（语料工厂）、M2（中/高难度两对）**。后续里程碑每完成一个，补对应行。
行号会随代码改动漂移，**以测试名为主键**，行号只作快速定位。
最后更新：2026-11-14。

---

## 1. 四个评分项 → 证据

| 评分项（A2） | 本项目落点 | 证据（文件:行号 / 测试名） | 状态 |
|---|---|---|---|
| **Design reasoning and scope** | SPEC 1–2 章（RQ / 假设 / 设计）+ 每次范围收缩的记录 | `docs/SPEC.md` 6.0 决议表（Q1–Q8 八条拍板）；`docs/SPEC.md` 3.0 交付集表（MUST / SIM / PLAN / N/A 四态）；`docs/PLAN.md` 里程碑 M0–M11 | M0–M2 已落地，其余按里程碑推进 |
| **Developed interaction** | SPEC 第 3 章模块清单；M4 评估卡、M5 渲染、M6 门控 | `govern/corpus.py:126` `check_task()` 产出的可运行仓库，是"用户任务"的输入侧；交互侧待 M4–M6 | `待补`（M4–M6） |
| **Architecture and technical reasoning** | `govern/` 模块边界 + 零运行时依赖约束 | `AGENTS.md` §2 六条硬规则；`govern/patch.py:102` `apply_unified_diff()`（不依赖 git/patch 的离线打补丁）；`govern/corpus.py:79` `_run_hidden()`（隐藏测试在副本中执行，语料只读） | M0–M2 已落地 |
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

## 3. 模块级证据

| 模块 | 状态 | 关键入口 | 自检 / 测试 |
|---|---|---|---|
| `govern/patch.py` | 新增（M1） | `parse()` `:37`；`changed_files()` `:91`；`apply_unified_diff()` `:102` | `tests/test_patch.py`（5 条：单 hunk、多文件、新建文件、上下文不匹配、目标目录缺失） |
| `govern/corpus.py` | 扩展（M2） | `check_task()` `:126`；`check_all()` `:158`；新增 `_pair_summary()` `:165`、`summarise()` `:187`（多输出 `pairs N/N within X%`） | `tests/test_corpus.py`（17 条）；`python -m govern.corpus --check` → `ok: 6 tasks, gold 6/6, pairs 3/3 within 20%` |
| `tools/make_repo.py` | 扩展（M2） | `DOMAINS` `:29`（6 个域）；`_files()` `:577` 按层分派；`_labels()` `:653` 从 diff 反算文件数；`build_corpus()` `:707` | `python tools/make_repo.py --selftest` → `ok: 61 corpus files match the factory` |
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

---

## 6. 明确没有做的（避免把 planned 说成 implemented）

- 没有采集任何人类被试数据；`M2` 是 **SIM**，`M10` 是 **N/A**（SPEC 3.0）。
- 没有真实 LLM 调用（`govern/llm.py` 属 M6，尚未实现，`corpus/` 与 `recordings/` 均无模型交互）。
- 跨模块分析器（M4）尚未实现，`impact_labels.json` 目前是**人工标注的金标准**，不是 M4 的输出。
- 六个种子仓库是**自建语料**（Q4 拍板的结果），不是真实开源仓库的历史；它们只用于让"影响分析 recall / precision"可判分。
