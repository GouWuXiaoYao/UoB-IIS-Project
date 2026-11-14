# Rubric mapping — 评分项 → 证据追溯表

> **这个文件不是什么。** 它不推断分数，也不复述评分标准。A2 评分细则的档位描述语原文见
> [SPEC.md](SPEC.md) 0.2；这里只做一件事：**把每个评分项落到仓库里可被第三方复核的证据上**
> （文件:行号、测试名、可复现命令）。没有证据的行一律标 `待补`，不写"已完成"。

当前覆盖：**M0（骨架）、M1（语料工厂）**。后续里程碑每完成一个，补对应行。
最后更新：2026-11-14。

---

## 1. 四个评分项 → 证据

| 评分项（A2） | 本项目落点 | 证据（文件:行号 / 测试名） | 状态 |
|---|---|---|---|
| **Design reasoning and scope** | SPEC 1–2 章（RQ / 假设 / 设计）+ 每次范围收缩的记录 | `docs/SPEC.md` 6.0 决议表（Q1–Q8 八条拍板）；`docs/SPEC.md` 3.0 交付集表（MUST / SIM / PLAN / N/A 四态）；`docs/PLAN.md` 里程碑 M0–M11 | M0–M1 已落地，其余按里程碑推进 |
| **Developed interaction** | SPEC 第 3 章模块清单；M4 评估卡、M5 渲染、M6 门控 | `govern/corpus.py:126` `check_task()` 产出的可运行仓库，是"用户任务"的输入侧；交互侧待 M4–M6 | `待补`（M4–M6） |
| **Architecture and technical reasoning** | `govern/` 模块边界 + 零运行时依赖约束 | `AGENTS.md` §2 六条硬规则；`govern/patch.py:102` `apply_unified_diff()`（不依赖 git/patch 的离线打补丁）；`govern/corpus.py:79` `_run_hidden()`（隐藏测试在副本中执行，语料只读） | M0–M1 已落地 |
| **Development evidence and authorship** | 里程碑即提交单元；每个验收都有命令与输出 | `docs/rubric-mapping.md` 本文件第 2 节；`git log` 每次提交对应一个里程碑；证据命令见第 4 节 | 持续维护 |

---

## 2. M1 五条验收标准 → 证据（SPEC 第 265 行起）

| # | 验收标准（SPEC） | 证据 | 覆盖测试 |
|---|---|---|---|
| 1 | 初始状态基线被显式记录，失败原因须是"重构未做"而非环境缺依赖 | `govern/corpus.py:94` `_failure_reason()`；实测基线原因：`AssertionError: total must return integer minor units, got float` | `tests/test_corpus.py:58` `test_baseline_fails_for_refactor_reason`（显式拒绝 `ImportError` / `ModuleNotFoundError` / `no tests ran` / `ERROR`） |
| 2 | 应用 gold patch 后隐藏测试全绿，6/6 成立 | `govern/corpus.py:126` `check_task()` 在副本上打补丁后重跑；`govern/patch.py:102` | `tests/test_corpus.py:53` `test_gold_patch_turns_hidden_tests_green`；CLI 输出 `gold 2/2` |
| 3 | 每个实例至少 1 个全局可变状态 + 1 个跨模块隐式契约，且都在 `impact_label_set` 中 | `corpus/T-L01a/impact_labels.json`（`billing.state.PRICE_CACHE`、`billing.core → billing.reports` 契约）；`corpus/T-L01b/impact_labels.json` 同构 | `tests/test_corpus.py:84` `test_each_task_has_global_state_and_contract` |
| 4 | 同 `pair_id` 两实例在"改动文件数 / 需修改函数数 / 隐藏测试数"上差异 ≤ 20% | `tools/make_repo.py:232` `_labels()` 由同一模板生成三组计数；实测 3 / 3 / 3 | `tests/test_corpus.py:91` `test_pair_is_matched_within_twenty_percent` |
| 5 | 仓库内不得出现指向答案的注释、TODO 或测试名泄漏 | `govern/corpus.py:53` `scan_leaks()`（扫描 `gold` / `solution` / `fixme` / `todo` / `oracle` / `hidden test`） | `tests/test_corpus.py:71` `test_repositories_do_not_leak_the_answer` |

**语料只读性**（本里程碑的额外保证）：`tests/test_corpus.py:76` `test_check_all_is_read_only`
对整个 `corpus/` 做 SHA-256 树摘要，检查前后必须一致 —— 检查器不得污染材料。

---

## 3. 模块级证据

| 模块 | 状态 | 关键入口 | 自检 / 测试 |
|---|---|---|---|
| `govern/patch.py` | 新增（M1） | `parse()` `govern/patch.py:37`；`apply_unified_diff()` `:102`；`changed_files()` `:91` | `tests/test_patch.py`（5 条：单 hunk、多文件、新建文件、上下文不匹配、目标目录缺失） |
| `govern/corpus.py` | 新增（M1） | `check_task()` `:126`；`check_all()` `:158`；`summarise()` `:162` | `tests/test_corpus.py`（13 条）；`python -m govern.corpus --check` → `ok: 2 tasks, gold 2/2, labels 2/2` |
| `tools/make_repo.py` | 新增（M1） | `build_corpus()` `:263`；`write_corpus()` `:294`；确定性自检 `:310` | `python tools/make_repo.py --selftest` → `ok: 19 corpus files match the factory` |
| `corpus/` | 数据 | `corpus/index.json`；两任务 `T-L01a`（`billing`）/ `T-L01b`（`loans`），同属 `PAIR-01`、层 `L` | `tests/test_corpus.py:28` `test_index_holds_one_pair`；`:34` `test_every_task_directory_is_complete` |

---

## 4. 复现命令（评审者用）

```powershell
# 全量测试（pytest 与 unittest 都能跑；本机用 .venv 里的 pytest 9.2.0）
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m unittest discover -s tests -q

# 语料验收（M1 的对外命令）
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

---

## 6. 明确没有做的（避免把 planned 说成 implemented）

- 没有采集任何人类被试数据；`M2` 是 **SIM**，`M10` 是 **N/A**（SPEC 3.0）。
- 没有真实 LLM 调用（M3 在 M1 阶段尚未实现，`corpus/` 与 `recordings/` 均无模型交互）。
- 跨模块分析器（M4）尚未实现，`impact_labels.json` 目前是**人工标注的金标准**，不是 M4 的输出。
