# Rubric mapping — 评分项 → 证据追溯表

> **这个文件不是什么。** 它不推断分数，也不复述评分标准。A2 评分细则的档位描述语原文见
> [SPEC.md](SPEC.md) 0.2；这里只做一件事：**把每个评分项落到仓库里可被第三方复核的证据上**
> （文件:行号、测试名、可复现命令）。没有证据的行一律标 `待补`，不写"已完成"。

当前覆盖：**M0（骨架）、M1（语料工厂）、M2（中/高难度两对）、M3（影响分析器 = SPEC M4）、M4（评估卡 + 门控 = SPEC M5/M6）**。
后续里程碑每完成一个，补对应行。
行号会随代码改动漂移，**以测试名为主键**，行号只作快速定位。
最后更新：2026-11-14。

---

## 1. 四个评分项 → 证据

| 评分项（A2） | 本项目落点 | 证据（文件:行号 / 测试名） | 状态 |
|---|---|---|---|
| **Design reasoning and scope** | SPEC 1–2 章（RQ / 假设 / 设计）+ 每次范围收缩的记录 | `docs/SPEC.md` 6.0 决议表（Q1–Q8 八条拍板）；`docs/SPEC.md` 3.0 交付集表（MUST / SIM / PLAN / N/A 四态）；`docs/PLAN.md` 里程碑 M0–M11 | M0–M8 已落地，M9 为 PLAN，M10 为 N/A |
| **Developed interaction** | SPEC 第 3 章模块清单；M4 评估卡、M5 渲染、M6 门控、M7 日志、M8 会话编排 | `govern/session.py:216` `Session` 把"提示 → 卡 → 勾选 → 门 → 生成 → 应用 → 测试 → 评分"串成一条真实链路，每一步落 JSONL：`start()`/`submit_prompt()`/`toggle()`/`confirm()`/`generate()`/`act()`/`end()`；`govern/run.py:165` `single()` 与 `:202` `batch()` 是它的终端入口；卡与门见 `govern/card.py:65`、`govern/gate.py:57` | 编排器、卡、门、日志、LLM 客户端、评估器均已落地并接线；**浏览器界面（M9）未做**，`--port` 明确返回 not implemented，故 storyboard 里的界面属 planned |
| **Architecture and technical reasoning** | `govern/` 模块边界 + 零运行时依赖约束 | `AGENTS.md` §2 六条硬规则；`govern/patch.py:102` `apply_unified_diff()`（不依赖 git/patch 的离线打补丁）；`govern/corpus.py:79` `_run_hidden()`（隐藏测试在副本中执行，语料只读）；`govern/impact.py:170` `analyze()`（纯 `ast`，无模型、无网络，见 `tests/test_impact.py:122` 的跨进程哈希一致性）；`govern/gate.py:35` 的门会校验卡（`required_ids` 与 `n_required` 不符即拒绝） | M0–M4 已落地 |
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

## 2c. 评估卡与门控验收 → 证据（SPEC M5 四条 + M6 五条，PLAN 里程碑 M4）

验收命令：`python -m govern.gate --selftest`（PLAN 第 249 行把"未勾满被拒、勾满解锁、绕过接口的负向测试必须失败"定为判据）。

| # | 验收标准 | 证据 | 覆盖测试 |
|---|---|---|---|
| M5-1 | 无凭空条目：每个 `affected_symbol` 必须能在 `impact_set` 里找到来源 | `govern/card.py:65` `build()` 只从 `impact_set.items` 逐条映射，不生成任何新符号；`evidence_ref` 指回 `impact.item_id` | `test_no_item_without_a_source_in_the_impact_set`（`tests/test_card.py:41`）、`test_evidence_points_at_a_real_impact_item`（`:48`） |
| M5-2 | 每张卡 ≥ 3 条、每条 ≤ 120 字符、必须含具体符号名 | 上限读 `config/config.json` 的 `card_item_max_chars`（不写死在代码里）；`_statement()`（`govern/card.py:57`）在超限时退化为"符号 + 类别"，保证仍含符号 | `test_every_card_has_at_least_three_items`（`:29`）、`test_statements_are_short_and_name_a_symbol`（`:34`） |
| M5-3 | 确定性渲染 | 纯函数：无时间戳、无随机、无遍历序依赖；`test_impact.py:122` 已证明上游 `impact_hash` 跨进程稳定 | `test_building_twice_gives_the_same_card`（`:69`）、`test_rendering_twice_gives_the_same_html`（`:76`） |
| M5-4 | **确认前界面不出现 diff 内容** | `to_html()`（`govern/card.py:108`）只渲染 statement / 类别 / 符号，无 `<pre>`、无 `@@`、无新增行文本 | `test_html_does_not_contain_any_added_line_from_the_gold_patch`（`:92`，逐条断言 gold patch 的每个新增行都不在 HTML 里）、`test_html_has_no_code_block_or_patch_hunk`（`:122`） |
| M6-1 | 不变量：`n_confirmed < n_required` 时任何生成请求被拒 | `govern/gate.py:72` `decide()` 每次重新计算，不缓存判定结果；`issue_token()`（`:87`）在 `blocked` 时返回 `None` | `test_a_fresh_gate_blocks`（`tests/test_gate.py:39`）、`test_partial_confirmation_still_blocks`（`:46`） |
| M6-2 | 正向路径：勾满解锁，`blocked=false`、`confirmed=true` | 同上；`open()`（`govern/gate.py:82`）= `not decide().blocked` | `test_full_confirmation_unlocks`（`:55`）、`test_unticking_locks_again`（`:66`） |
| M6-3 | **不可绕过**：不存在绕过门的公开入口 | 门内状态全为私有；构造时校验卡（`required_ids` 与 `n_required` 不符、或 `required_ids` 含卡外条目 → `ValueError`）；确认状态不跨实例继承；令牌一次性且任何勾选变化即失效 | `test_a_new_gate_does_not_inherit_confirmations`（`:131`）、`test_a_card_that_understates_what_is_required_is_rejected`（`:140`）、`test_a_card_that_inflates_the_required_count_is_rejected`（`:146`）、`test_a_required_id_that_is_not_on_the_card_is_rejected`（`:152`）、`test_there_is_no_attribute_that_unlocks_the_gate`（`:158`）、`test_token_is_single_use`（`:107`）、`test_changing_an_answer_invalidates_the_live_token`（`:117`） |
| M6-4 | C0 同接口、`blocked=false` 恒成立 | `PassThroughGate`（`govern/gate.py:105`）只覆写 `decide()`，其余方法全部继承 | `test_passthrough_never_blocks`（`:168`）、`test_passthrough_still_reports_the_card_shape`（`:175`）、`test_passthrough_exposes_the_same_interface`（`:180`） |
| M6-5 | 回退：拒绝/关闭卡片后可重新提问，不死锁 | 门无"终止"状态：`toggle()` 可随时反向，`decide()` 是纯查询；重新确认会作废旧令牌而不是锁死 | `test_unticking_locks_again`（`:66`）、`test_changing_an_answer_invalidates_the_live_token`（`:117`） |

**一条不是验收项、但必须写下来的设计决定**：卡片的复选框**从不预勾选**（`required` 只渲染成 `required` 徽标 + `data-required="true"`）。
预勾选等于把 A1 自己指出的失败模式（confirmation fatigue → 机械确认）做进了界面，所以 `test_html_never_renders_a_pre_ticked_checkbox`（`tests/test_card.py:108`）把这条钉死。

---

## 2d. 遥测日志器验收 → 证据（SPEC M7 七条，PLAN 里程碑 M5）

验收命令：`python -m govern.log --selftest` → `ok: 16 event types, seq from 1, atomic append, purge clean`。

| # | 验收标准 | 证据 | 覆盖测试 |
|---|---|---|---|
| M7-1 | 每行合法 JSON 且过 schema；校验失败**拒绝写入并抛出**，不静默丢弃、不写半行 | `validate()`（`govern/log.py:260`）返回错误清单；`emit()`（`:380`）在 `:405` 调用它，`SchemaError`（`:220`）在写盘**之前**抛出 | `test_unknown_event_type_is_rejected`（`tests/test_log.py:176`）、`test_missing_private_field_is_rejected`（`:182`）、`test_wrong_type_is_rejected`（`:190`）、`test_invalid_enum_value_is_rejected`（`:224`）、`test_unknown_field_is_rejected_unless_prefixed`（`:217`）、`test_nothing_written_when_a_body_field_is_refused`（`:255`） |
| M7-2 | `(session_id, seq)` 唯一且严格递增；`ts` 带时区偏移且会话内不倒退 | `_repair_and_count()`（`:356`）从最后一条完整行续号；`_stamp()` 保证毫秒级单调（同毫秒内 +1 ms） | `test_first_line_has_seq_one_and_a_uuid`（`:111`）、`test_seq_increases_by_one`（`:121`）、`test_ts_has_milliseconds_and_an_offset`（`:129`）、`test_timestamps_never_go_backwards`（`:137`） |
| M7-3 | 无 PII：正则扫描不得出现姓名/邮箱/学号样式，**测试含正例与反例** | `scan_pii()`（`:447`）扫每一行里的每个字符串（含嵌套），扫描前先剥掉 UUID 与 ≥32 位十六进制块，避免把 `event_id` 里的 8 位数字段误报 | 反例：`test_a_real_log_scans_clean`（`:377`，把 16 类事件全写一遍后零命中）；正例：`test_identifiers_are_found_in_a_synthetic_file`（`:384`，邮箱/学号/姓名三行各被抓到）、`test_scan_catches_a_nested_value`（`:397`） |
| M7-4 | 原子性：写一行中途被杀，最后一行要么完整要么不存在 | 单次 `os.open(O_APPEND)` + 一次 `os.write` + `fsync`（`:414-419`，不留 `.tmp` 中转文件）；重开时 `_repair_and_count()`（`:356`）把撕裂的尾段截掉 | `test_a_torn_last_line_is_repaired_on_reopen`（`:302`）、`test_seq_continues_from_the_last_complete_line`（`:317`）、`test_no_tmp_file_is_left_behind`（`:332`） |
| M7-5 | 单行 ≤ 4 KB；数组 ≤ 20 项，超出截断并另记总数 | `MAX_LINE_BYTES = 4096`（`:26`）在 `emit()` `:411` 处拒绝超长行；`MAX_ARRAY_ITEMS = 20`（`:27`），截断时写入 `x_<field>_total`（`:387`）——`x_` 前缀是 4.5 条给"附加元数据"留的通道 | `test_oversized_line_is_refused`（`:279`）、`test_long_arrays_are_truncated_with_a_running_total`（`:285`） |
| M7-6 | 原文不落盘（Q7）：schema 无正文字段；校验器**拒绝** `text`/`content`/`body`/`prompt_raw` 类字段 | `ENVELOPE`（`:70`）与 `EVENT_FIELDS`（`:91`）只声明 id/枚举/计数/`sha256`/`length`；`validate()` 对正文字段（含 `_text`/`_body` 后缀变体）一律报错 | `test_body_fields_are_refused`（`:234`）、`test_body_field_suffixes_are_refused_too`（`:241`）、`test_hash_and_length_are_the_accepted_alternative`（`:248`） |
| M7-7 | 保留期可执行：`purge --before <date>`，删除后无 `.jsonl`/`.jsonl.tmp`/备份残留，并输出删除清单 | `purge()`（`:480`）按 mtime 删 `logs/**/*.jsonl`，并**无条件**删除 `*.jsonl.tmp`（它们只存在于"崩溃"与"下次打开"之间）；CLI 在 `:558` | `test_purge_removes_old_sessions_and_keeps_recent_ones`（`:341`）、`test_purge_leaves_no_jsonl_or_tmp_behind`（`:356`）、`test_purge_reports_what_it_removed`（`:367`） |

**M7-7 的后半句尚未满足，如实记录**：SPEC 要求"重跑 `analysis/` 时须显式报告哪些结论依赖已删除数据"，而 `analysis/`（SPEC M10）按 Q8 拍板是 **N/A**，本期不存在重算脚本。
所以本期只交付"删除清单"这一半；这条缺口在 §6 单列，不当作已实现。

---

## 2e. LLM 客户端验收 → 证据（SPEC M3 六条，PLAN 里程碑 M6）

验收命令：`python -m govern.llm --selftest` → `ok: 6 recordings, 10 replays each, 6/6 identical, no network used`；`python tools/scan_secrets.py` → `ok: 0 finding(s) in 110 files`。

| # | 验收标准 | 证据 | 覆盖测试 |
|---|---|---|---|
| M3-1 | `replay` 逐字节相同：同一次请求跑 10 次，`content_hash()` 全等 | `Client._replay()`（`govern/llm.py:266`）只读 `recordings/<slug>/<request_sha256>.json`；`Suggestion.content_hash()`（`:168`）对内容而非时间取摘要；`_selftest()`（`:397`）对 6 任务各跑 10 次比对 | `test_replay_is_byte_identical_across_ten_calls`（`tests/test_llm.py:119`）、`test_the_hash_is_stable_for_the_same_content`（`:340`）、`test_the_hash_does_not_depend_on_the_absolute_path`（`:347`） |
| M3-2 | 录制完整可复现：`live` 写下的录制，`replay` 能逐字节还原；缺录制时**报错而非静默降级** | `_record()`（`:349`）写 `format/source/request_sha256/model_id/temperature/seed/latency_ms/response`；`_replay()` 先校验 `format`、`request_sha256`、`model_id` 三道闸，异常分别抛 `SchemaViolation`/`RecordingMissing` | `test_live_writes_a_recording_that_replay_reproduces`（`:239`）、`test_the_recording_says_it_came_from_live`（`:247`）、`test_missing_recording_raises_with_a_code`（`:144`）、`test_a_recording_for_another_request_is_refused`（`:151`）、`test_a_malformed_recording_is_refused`（`:163`）、`test_a_recording_with_an_unparseable_patch_is_refused`（`:172`） |
| M3-3 | 无魔法数字：`model`/`temperature`/`seed` 只在 `config/config.json` | `Client` 全部从 `config` 取值（`:221-235`）；录制里回写的也是 config 值（`:349`） | `test_no_temperature_or_seed_literals_outside_config`（`:362`，扫 `govern/*.py` 与 `tools/*.py`）、`test_the_model_id_comes_from_config`（`:287`） |
| M3-4 | 无密钥与端点入库：密钥前缀、`api_key` 赋值、`token` 赋值、https 端点字面量，交付态零命中（与 SPEC 3.11 第 5 条同一脚本） | `tools/scan_secrets.py`：`_PATTERNS`（`:38`）四组，片段拼装以免自匹配；密钥只从 `A2_API_KEY`、端点只从 `A2_API_BASE` 读（`govern/llm.py:285-290`） | `test_no_endpoint_or_key_literal_in_the_code`（`:372`）、`test_the_repository_is_clean`（`tests/test_secrets.py:45`）、四条正例 `:19/:23/:27/:30`、反例 `:37`、`test_loopback_http_is_allowed`（`:33`） |
| M3-5 | 非法返回：写 `integrity_event(kind="schema_violation")` 并**继续会话** | `generate()`（`:246`）捕获 `SchemaViolation` 后调 `_integrity()`（`:384`），仍照常写 `generation_request`；异常再抛给调用方 | `test_a_schema_violation_also_writes_an_integrity_event`（`:305`）、`test_the_session_continues_after_a_schema_violation`（`:316`）、`test_a_malformed_reply_raises_with_a_code`（`:230`） |
| M3-6 | 每次调用恰一条 `generation_request`，`mode` 如实，`model_id` 为真实模型名 | `_log_request()`（`:369`）在成功/失败路径上只调用一次；`mode` 取 `self.mode`（`:277` 测试钉死）；`model_id` 由日志元数据给出，且 `_replay` 现在**拒绝**来自其它模型的录制（`:271-275`） | `test_exactly_one_generation_request_per_successful_replay`（`:258`）、`test_exactly_one_generation_request_per_failed_call`（`:268`）、`test_the_mode_field_is_truthful`（`:277`）、`test_a_recording_from_another_model_is_refused`（`:297`）、`test_the_request_hash_is_logged`（`:328`） |
| 附 | 录制是**作者模拟**的，不是模型输出 | `tools/make_recordings.py` 从 gold patch 去掉最后一个文件段，即"修了主模块、漏了一个消费者"；每条录制 `"source": "sim"` | `test_the_shipped_recordings_match_the_factory`（`:393`）、`test_every_shipped_suggestion_omits_at_least_one_consumer`（`:405`）、`test_shipped_recordings_declare_their_source`（`:387`） |

**为什么录制必须"少修一处"**：如果 replay 直接回放 gold patch，C0 与 C1 的隐藏测试都会通过，实验就没有区分度。少修一处正是 A1 §4 指出的跨模块副作用盲区，也是评估卡要显形的东西。录制里 `source: "sim"` 如实标注，报告与 README 都按"模拟建议"表述。

---

## 2f. 结果评估器验收 → 证据（SPEC M8 六条，PLAN 里程碑 M7）

验收命令：`python -m govern.score --selftest` → `ok: 6 rules (complexity, duplication, bare_except, hardcoded_secret, eval_usage, sql_concat) with positive and negative fixtures, gold 6/6, clean repository 0 debt (score/1.0.0+sha256:5cbf3...)`；`python -m govern.hidden --selftest` → `ok: hidden suite runner reports pass/fail in a child interpreter`。

| # | 验收标准 | 证据 | 覆盖测试 |
|---|---|---|---|
| M8-1 | 打上 gold patch 后隐藏测试全过；未改动的仓库即基线（不改仓库 = 不产生正确性收益） | `govern/score.py:352` `baseline()` 在种子仓库上跑一次隐藏套件；`:392` `evaluate()` 在提交副本上重跑；实测 H 层基线 `n_fail=5`、gold 后 `tests_pass=True` | `test_gold_patch_passes_the_hidden_suite`（`tests/test_score.py:226`）、`test_an_unmodified_repository_fails_the_hidden_suite`（`:237`）、`test_baseline_reports_the_starting_state`（`:217`） |
| M8-2 | 指标是"提交后 − 开始前"，且确定性、与文件遍历顺序无关 | `:373` `_line_delta()` 用 `difflib` 逐文件比对；`:317` `scan_repo()` 与 `:304` `_python_files()` 都按路径排序后遍历；`:332` `counts()` 先铺满六类再累加，缺项不缺失 | `test_deltas_are_after_minus_before`（`:247`）、`test_line_counts_describe_the_change`（`:259`）、`test_counts_are_deterministic`（`:148`） |
| M8-3 | `scorer_version` 与 `rules.json` 的 hash 写进每条 `task_end` / `suggestion_scored` | `:102` `rules_hash()` 对 canonical JSON 取 SHA-256；`:108` `scorer_version()` = `score/1.0.0+sha256:…`；`:422` `scored_event()` 把它放进 `suggestion_scored` 负载 | `test_the_version_carries_the_rules_hash`（`:206`）、`test_a_different_rules_file_changes_the_version`（`:210`）、`test_the_scored_event_matches_the_log_schema`（`:319`，经真实 `Logger.emit()` 写出后 `log.validate()` 为空） |
| M8-4 | 隐藏测试在子进程沙箱里跑，超时**强杀**，不拖垮会话 | `govern/hidden.py:49` `run()` 用 `Popen` + `communicate(timeout=…)`，超时 `kill()` 后 `communicate()` 收尾并关闭管道；`:343` `run_hidden_tests()` 是其唯一调用方；超时上限来自 `config.test_timeout_s` | `test_a_hanging_suite_is_killed_and_reported`（`:289`）、`test_a_failing_test_is_named`（`:307`）、`tests/test_hidden.py` 的 IsolationTests（挂死 2 s 被强杀、空套件算错误、import 爆炸被捕获、`sys.exit` 被捕获） |
| M8-5 | 六类规则各有正例 + 反例测试；缺一条即视为该规则未实现 | `config/rules.json` 六条规则各带 `rule_id/category/severity/weight` 与阈值（complexity 40 行/4 层、duplication 6 行、裸 `except`、硬编码密钥、`eval`/`exec`、SQL 拼接）；实现见 `govern/score.py:137-270` | 每组两条以上：`test_a_long_function_is_flagged`/`test_a_short_function_is_clean`（`:35`/`:40`）、`test_a_repeated_block_is_flagged_once_per_extra_copy`/`test_a_single_copy_is_clean`（`:62`/`:68`）、`test_a_bare_except_is_flagged`/`test_a_typed_except_is_clean`（`:74`/`:78`）、`test_a_key_literal_is_flagged`/`test_an_environment_lookup_is_clean`（`:83`/`:91`）、`test_eval_is_flagged`/`test_literal_eval_is_not_flagged`（`:99`/`:107`）、`test_concatenated_sql_is_flagged`/`test_a_parameterised_query_is_clean`（`:112`/`:120`） |
| M8-6 | `is_correct` 的判据必须**写在文档里**，不能只藏在代码里 | `govern/score.py:416` `is_correct()` 的实现在 docstring 里逐字写明："correct iff applying it reduces the number of failing hidden tests (`after.n_fail < before.n_fail`)"；模块 docstring 顶部同样陈述 | `test_is_correct_requires_an_improvement`（`:269`：少失败一条即正确、失败数不变即不正确） |

**两条如实记录（属于"计划内但有代价"的取舍）**

1. **轻层任务的 `debt_delta` 结构上恒为 0**：六类规则量的是复杂度/重复/异常/密钥/`eval`/SQL 拼接，而 L 层语料的坏味道是"浮点金额 + 模块级缓存 + 报告重复推导税额"（见第 3 节递进表）。实测 L=0、M=3、H=8 加权债。因此债务指标只在 M/H 层有区分度；L 层的正确性收益由隐藏测试与 `lines_added/removed` 承载。这条写进了第 6 节，报告里也不得声称"每层都能测出债务下降"。
2. **`debt_delta` 以 float 写入日志**：`Outcome.debt_delta` 是整数加权计数之差，但 SPEC 4.3 的 `task_end.debt_delta` 字段类型是 float，`govern/log.py` 会按 float 校验，故在 `evaluate()` 里显式 `float(...)`（`:392`）。这不是精度需要，而是 schema 一致性。

---

## 2g. 编排器与 CLI 验收 → 证据（SPEC M2 五条，PLAN 里程碑 M8）

验收命令：`python -m govern.run --selftest` → `ok: 6 tasks, 6 cards`；`python -m govern.session --selftest` → `ok: 10 participants, 6 slots each, deterministic, C0=300 C1=300 chi2 p=1.000`；`python -m govern.run --simulate 100` → `ok: simulated 100 assignments, C0=300 C1=300 chi2 p=1.000 (balanced at alpha=0.05), every pair in both conditions: yes`。

| # | 验收标准 | 证据 | 覆盖测试 |
|---|---|---|---|
| M2-1 | 条件分配是**确定**的（同一被试重跑得到同一序列），且每个 PAIR 在跨被试层面两条件都出现 | `govern/session.py:83` `assign()` 用 `random.Random(f"{seed}:{participant}")` 播种、pair 顺序洗牌、成员按 `task_id` 排序；`config/schedule.json` 的 `orders`（AB/BA 交替）决定条件；`:126` `simulate()` 把 n 个被试展开成 6n 个 slot | `test_assignment_is_deterministic`（`tests/test_session.py:68`）、`test_every_pair_appears_in_both_conditions`（`:84`）、`test_each_task_runs_in_one_condition_only`（`:92`）、`test_simulation_is_balanced`（`:134`）、`test_simulation_sees_both_conditions_for_every_pair`（`:140`） |
| M2-2 | 100 次模拟两条件均衡（卡方 p > α），且每个 PAIR 的两条件都出现过 | `govern/session.py:114` `chi_square_p()` = `erfc(sqrt(chi2/2))`（df=1 闭式）；`:126` `simulate()` 返回 `counts/chi2/p/alpha/balanced/pairs_both_conditions`；阈值 `alpha_sim` 来自 `config/config.json`，不写死 | `test_chi_square_of_a_perfect_split_is_close_to_one`（`:123`）、`test_chi_square_detects_an_unbalanced_split`（`:126`）、`test_chi_square_matches_the_closed_form_for_one_degree_of_freedom`（`:129`）、`test_simulation_counts_every_slot`（`:151`）、`test_simulate_prints_the_balance_and_writes_a_report`（`tests/test_run.py:56`） |
| M2-3 | 断点续跑：`--resume` 后 `seq` 连续（不跳号、不重号） | `govern/session.py:216` `Session.checkpoint()` 写 `state/<session_id>.json`；`resume()` 从 `rebuild_state()` 恢复后由 `Logger` 的 `_repair_and_count()` 续号；`:165` `rebuild_state()` 只读日志 | `test_checkpoint_then_resume_continues_the_sequence`（`tests/test_session.py:335`）、`test_resume_finishes_a_checkpointed_session`（`tests/test_run.py:139`，逐行断言 `seq == 1..n`） |
| M2-4 | 状态**只从日志**就能重建，且与内存中的状态一致 | `govern/session.py:165` `rebuild_state()`（card_id/confirmed_ids/gate_open/phase/ended/n_events 全部由事件重放得出）；`Session.state()` 的 `phase` 取"最后一条事件的 phase"（`_where()` 同步 `_last_phase`），因此与重放结果同源 | `test_state_can_be_rebuilt_from_the_log`（`:327`，逐键比较 `state()` 与 `rebuild_state()`）、`test_state_ahead_of_the_log_is_a_conflict`（`:375`，`StateConflict`） |
| M2-5 | 没有知情同意就不许启动（且不留日志） | `govern/session.py:216` `Session.start()` 先校验 `consent_given`，失败抛 `ConsentError` 且不发出任何事件；CLI 的 `--no-consent` 直接把 `consent=None` | `test_a_session_without_consent_refuses_to_start`（`:157`，断言日志文件 0 字节）、`test_a_started_session_records_the_consent`（`:165`）、`test_without_consent_the_session_is_refused`（`tests/test_run.py:87`，退出码非 0 且无日志） |

**M2 顺带覆盖的三条流程不变量**（SPEC M6 的"门"在真实编排里没有被绕过）

1. 门未开时 `generate()` 抛 `GateClosed`，且 `gate_decision(blocked=true)` 已落日志 —— `test_generation_stays_closed_until_every_item_is_confirmed`（`:230`）、`test_a_partial_confirmation_is_logged_as_blocked`（`:239`）。
2. 提示词正文不落盘，只有 `prompt_sha256` —— `test_the_prompt_body_is_not_logged_only_its_hash`（`:199`）。
3. 一次会话产出的**每一条**事件都通过 `log.validate()` —— `test_every_emitted_event_passes_the_schema_validator`（`:305`）。

**如实记录（M8 的边界）**：`--session` / `--batch` 都是**作者自测**（SIM）路径——确认角色是终端，不是招募来的被试。SPEC 0.2 的红线在这里最容易踩：报告与 README 都不得把这些运行写成"人类被试实验"。当前没有真实被试数据，`runs/` 也不入库（Q7）。

---

## 2h. Web UI 验收 → 证据（PLAN 里程碑 M9）

验收命令：`python -m govern.web --selftest` → `ok: 6 routes wired, card rendered from session state`；`python tools/make_storyboard.py --check` → `ok: 3 storyboard frame(s)`。

| # | PLAN M9 的要求 | 证据 | 覆盖测试 |
|---|---|---|---|
| M9-1 | 页面来自 `static/index.html`，左对话 / 右卡片，原生 JS，`http.server` 提供 | `govern/web.py:53` `index()` 只读 `static/index.html`（262 行，无构建步骤）；`Handler`（`:207`）与 `GovernServer`（`:259`）；`make_server()`（`:269`） | `test_the_page_is_served_from_static`（`tests/test_web.py:131`）、`test_the_page_declares_the_backend_it_talks_to`（`:137`） |
| M9-2 | 卡片带复选框，勾选与取消都落日志，计数与"还差哪些"实时更新 | `web.py:104` `toggle()` 返回 `checked/gate_open/missing`；`static/index.html:166` `toggle()` 把返回的 `missing` 写回 `state` | `test_prompt_returns_every_card_item_unchecked`（`:146`）、`test_toggle_returns_the_running_count_and_the_missing_items`（`:159`）、`test_an_unknown_item_is_a_400`（`:167`） |
| M9-3 | 未勾满时**拦截**生成：HTTP 409 + 日志里留下 `gate_decision(blocked=true)` | `web.py:136` 捕获 `session.GateClosed` → 409 `gate_closed` 附 `missing`；`govern/session.py:362` 在抛之前先 `emit("gate_decision", blocked=True, …)`，否则"有多少次想绕过门"在数据上无解 | `test_generating_before_confirming_is_refused`（`:175`）、`test_generating_after_a_partial_confirmation_is_refused`（`:182`）、`test_a_blocked_decision_is_logged_as_blocked`（`:199`） |
| M9-4 | C0 基线**没有卡、也不设门**（对照臂必须真的无门，而不是把卡禁用） | `web.py:56` `card_view()` 对 C0 返回 `n_items=0`；`Gate` 在 C0 用 `PassThroughGate`（`govern/gate.py:105`） | `test_the_baseline_condition_shows_no_card`（`:210`）、`test_the_baseline_condition_generates_without_confirming`（`:216`） |
| M9-5 | 手工走完 C1 与 C0，产出 3 张 storyboard 截图 | `storyboards/1-c1-gate-closed.png`、`2-c1-gate-open.png`、`3-c0-baseline.png`、`4-c1-reject.png`：由 `tools/make_storyboard.py` 启动**真实**服务器、按人手的调用顺序驱动、再用无头 Chrome 拍照；`storyboards/README.md` 记录每帧的动作/响应/日志序列 | `python tools/make_storyboard.py --check`（四帧存在且非空，并核对第 4 帧的证据文件）；`test_port_serves_the_session_it_started`（`tests/test_run.py:118`）证明 CLI 的 `--port` 走的是同一个 `Session` |
| M9-6 | 控制路径：拒绝建议后工作树不变、拒绝进入日志 | `storyboards/4-c1-reject.png` + `storyboards/4-c1-reject.promises.txt`（5 个文件逐字节哈希前后一致、`work tree identical: True`、`seq 13 suggestion_action action=reject accepted_after_gate=True`、`seq 16 task_end submitted=False n_accepted=0 n_rejects=1 n_fail=2`）；拒绝走 `POST /api/act {"action":"reject"}`，结束走 `POST /api/end {"submitted":false}`，均为真实 HTTP 路径 | `RejectPathTests`（`tests/test_web.py`：逐字节哈希不变、日志里恰一条 reject 且 `task_end` 计数正确、重载页面仍能显示被拒的建议）；`tests/test_storyboard.py`（5 条，核对 `--check` 与证据文件的自述） |

**页面上的两条安全性质（`tests/test_web.py` HygieneTests）**

1. 只绑 `127.0.0.1`（`make_server` 的默认 host），不对外监听 —— `test_the_server_binds_loopback_only`（`:299`）。
2. 复选框**从不预勾选**：`static/index.html:117` 的 `box.checked = !!item.checked` 只从服务端状态同步，首次渲染必为未勾选 —— `test_the_page_never_ships_a_pre_ticked_checkbox`（`:323`）。这条与 `tests/test_card.py:108` 是同一个断言的两个层（HTML 字符串 / 真实 DOM 属性），因为 M4 时曾经写错过一次（渲染成 `checked disabled`，等于把 A1 说的"机械勾选"失败模式做进界面）。

**如实记录（M9 的边界）**

- 三帧都是**作者自测**驱动出的界面，`runs/` 不入库，页面里没有任何人类被试数据。
- 帧里的左栏是空的：请求正文不落盘（Q7 只存 hash + 长度），所以从服务端状态重绘的页面**重放不出**当时输入了什么。`static/index.html:257` 的 `?playback=1` 分支把这句话直接写在气泡里，而不是编一段对话。
- 没有浏览器自动化测试：`tests/test_web.py` 测的是 HTTP 契约与页面源码，交互后的视觉效果由 `tools/make_storyboard.py` 的三帧静态覆盖；点击后的 JS 行为不在这套自动化里。

---

## 2i. 开发溯源台账验收 → 证据（SPEC M11 四条，PLAN 里程碑 M10）

验收命令：`python -m govern.provenance --check` → `ok: 21 rows, 11 modules covered (original=8, reused=3, assisted=10)`；`python -m govern.provenance --selftest` → `ok: 11 modules, 3 origins, assisted rows must carry decision + check`。

台账本体是 `docs/PROVENANCE.md`（20 行，M1–M11 全覆盖）。**它是数据，不是叙述**：`govern/provenance.py:78` 的 `parse()` 只认表格行，行内格数不符直接报错（`LedgerError`），`check()`（`:118`）逐条判定。

| # | SPEC M11 验收标准 | 证据 | 覆盖测试 |
|---|---|---|---|
| M11-1 | 每个模块至少 1 行，且 `origin` 三个取值都至少出现一次；全填 original 视为未通过 | `govern/provenance.py:41` `MODULES`（M1–M11）与 `:44` `ORIGINS`；`check()` `:127` 报缺模块、`:139` 报"某 origin 从未出现"。实测 `original=8, reused=3, assisted=9` | `test_the_shipped_ledger_covers_every_module`（`tests/test_provenance.py:109`）、`test_a_missing_must_module_is_reported`（`:115`）、`test_a_ledger_with_only_original_rows_is_reported`（`:122`） |
| M11-2 | 所有 `origin=assisted` 行的 `decision` 与 `check` 均非空，缺一即失败 | `check()` `:150-154`；**markdown 表格用 `-` 表示空**，所以 `_filled()`（`:64`）把 `-`/`—` 也当空——否则一个装饰性横线就能混过"审阅过 AI 输出"的判定 | `test_an_assisted_row_without_a_check_is_reported`（`:131`）、`test_an_assisted_row_without_a_decision_is_reported`（`:136`）、`test_a_dash_does_not_count_as_evidence`（`:141`） |
| M11-3 | 所有 `origin=reused` 行的 `source` 必须指向工作区内真实存在的路径 | `_source_exists()`（`:104`）按 `root` 解析；`reused` 的 3 行分别指向 `参考代码库/mock_model.py`、`参考代码库/index.html`、`参考代码库/tools.py` | `test_a_reused_row_pointing_at_a_missing_path_is_reported`（`:153`）、`test_a_reused_row_may_point_at_a_directory`（`:160`） |
| M11-4 | 失败时退出码非 0，且能一行命令在提交前跑 | `main()` `:243`：`0` 通过 / `1` 台账有错 / `2` 台账读不出（不崩栈）。故意删掉 P-003 的 `check` 单元格后实测：`fail: 1 problem(s) … P-003: assisted work needs a check`，`exit=1` | `test_check_exits_zero_on_the_shipped_ledger`（`:174`）、`test_check_exits_non_zero_on_a_broken_ledger`（`:180`）、`test_a_missing_ledger_is_reported_not_crashed`（`:190`） |

**另外两条结构性检查（不在 SPEC 四条内，但缺了台账就能糊弄）**

- `item_id` 重复 → 报错（`check()` `:133`）：否则同一件事可以拆成两行，凑够"三值齐全"。
- `origin` / `module` 必须是枚举值（`check()` `:145-148`）：否则写 `ai`、`M12` 也能过。

**如实记录（M10 的边界）**

- 台账的 9 条 `assisted` 行如实承认代码草稿由 AI 生成；`decision` 写的是**为什么留下它**，`check` 写的是**怎么验证的**（多数是可复跑的命令或具名测试），不是"已审阅"三个字。
- `original` 的 8 行记录的是作者本人的裁定与产品红线（Q1–Q8、预勾选禁令、`replay` 唯一交付模式、阈值全部进 config），不是"这行代码我打的字"。
- 台账里 `P-019`、`P-020` 的 `commit` 列在本提交时尚未有值（台账无法在自己的提交里引用自己的 hash）；由紧随其后的一次文档提交补齐——这一条本身就是"记录要能追溯"的代价，写在这里而不是藏起来。

---

## 2j. 全链路冻结 → 证据（PLAN 里程碑 M11，对应 SPEC 3.11 六条完成定义）

六条完成定义在 `docs/PLAN.md:13-20`。它们不是"设计意图"，而是六条能当场跑的命令；`tests/test_end_to_end.py` 把每一条都写成了测试，所以回归时不会再悄悄退化。

| # | 完成定义（PLAN §1） | 实测输出（2026-11-14） | 覆盖测试 |
|---|---|---|---|
| 1 | `python -m unittest discover -s tests -q` 全绿 | `Ran 328 tests … OK`（exit 0，裸 Python，无 pytest） | `test_1_the_test_command_runs_the_suite`（`tests/test_end_to_end.py:46`，用 `-p test_smoke.py` 证明发现命令可用，避免套件自递归） |
| 2 | `python -m govern.run --dry-run` → `ok: 6 tasks, 6 cards` | `ok: 6 tasks, 6 cards` / `dry run: no logs written, no network used` | `test_2_one_command_self_test`（`:52`）、`test_a_frozen_tree_writes_no_session_data_to_the_repository`（`:124`，断言 dry run 连 `runs/` 都不新建） |
| 3 | clone → `python -m govern.run --batch --schedule config/schedule.json` 出结果表 | `ok: batch P01 ran 6 of 6 slots in runs\R-DEMO`，六个 slot 各一行 | `test_3_one_command_reproduces_a_batch_without_network_or_key`（`:56`，断言 6 个 jsonl、首尾为 `session_start`/`session_end`、每条都过 `log.validate`） |
| 4 | 零魔法数字：阈值只在 `config/config.json` | `tests/test_config_discipline.py` 用 `dataclasses.replace` 改五个参数，行为随之改变 | `test_the_card_statement_limit_comes_from_config`（`:43`）、`test_the_hidden_suite_timeout_comes_from_config`（`:52`）、`test_the_pair_tolerance_comes_from_config`（`:57`）、`test_the_simulation_alpha_comes_from_config`（`:66`）、`test_the_metric_thresholds_are_read_from_config`（`:75`）、`test_no_parameter_is_written_into_the_code`（`:93`） |
| 5 | `python tools/scan_secrets.py` 零命中 | `ok: 0 finding(s) in 220 files` | `test_5_no_secret_or_endpoint_is_committed`（`:89`） |
| 6 | `python -m govern.provenance --check` | `ok: 21 rows, 11 modules covered (original=8, reused=3, assisted=10)` | `test_6_the_provenance_ledger_checks_out`（`:94`） |

**冻结产物**：`python tools/make_release.py --build` → `dist/a2-1.0.0.zip`（123 个条目，410,797 字节），`dist/SHA256SUMS` 记 `2f2ea5d269f260d03bd8b942b3cac8ec41383b6266e8824e94b5944b772590c4`。`--verify` 复核通过，且**同一棵树重建两次字节相同**（实测第二次构建 hash 与第一次完全一致）——否则"快照"标识的是构建机器，不是这份工作。归档排除规则由 `tools/make_release.py:34` 的 `SKIP_DIRS`/`SKIP_SUFFIXES`/`SKIP_NAMES`/`SKIP_PREFIXES` 定义，实测 123 个条目中不含 `runs/`、`_tools/`、`.venv/`、`参考代码库/`、`.pyc`、`.docx`、`DSH-`、`A2_API_KEY*`。

**如实记录（M11 的边界与代价）**

- **第 3 条的结果里六个 slot 全是 `tests_pass=False`**：随附的模拟建议**故意**删掉 gold patch 的最后一个文件段（`test_every_shipped_suggestion_omits_at_least_one_consumer`，`tests/test_llm.py:405`），所以每个任务都留下逃逸缺陷。这条命令证明的是"管线能跑通并如实判负"，不是"治理组更好"——后者需要真人数据，本期是 `planned`（见 §6）。
- `dist/` **不入库**（`.gitignore` 已加）。归档可重建且字节可复现，把 400 KB 二进制放进 Git 只会让"哪个才是提交版"变模糊；摘要写进 `README.md` 与 `docs/PLAN.md` 的 M11 行。
- `app_version` 从 `0.0.0-draft` 升到 `1.0.0`，仅作为冻结标识，不代表功能变化；它会出现在每条日志事件的 `app_version` 字段里，便于区分"冻结前采集"与"冻结后采集"的数据。
- 第 4 条里 `tau_review_ms` 与 `mech_dwell_ms` 在冻结时点**没有行为消费者**（它们是 SPEC 5.2 的指标阈值：盲接受、机械确认），分析管线按 Q8 为 N/A，所以那次只验证到"从 config 读出并如实报告"（`gate.threshold_summary()`）。**这条缺口在 §2k 的实验编排层已被补上**：`experiments/metrics.py:82`、`:99` 现在真的用这两个阈值判定盲接受与机械确认，`tests/test_experiments.py:181`、`:195` 有正反例。
- 顺带修掉的真缺陷：`card._statement()` 在模板超长时回落到 `symbol (category)`，而回落后**可能仍超过 `card_item_max_chars`**（实测 24 字符上限下返回 53 字符）——SPEC M5 的上限形同虚设。现已硬截断加省略号，由 `test_the_card_statement_limit_comes_from_config` 钉住。

---

## 2k. 实验编排层 → 证据（`experiments/`，冻结后追加的一层）

`govern/` 是仪器（一次一个会话），`experiments/` 是机架：读实验文件 → 展开成 cell → 有并发上限地跑 → 失败隔离 → 可续跑 → 从日志重算指标。它不直接碰模型，每个会话仍走 `govern.session`，所以日志 schema 与 SPEC 4.2 完全一致，没有第二套格式。

| # | 需求 | 证据 | 覆盖测试 |
|---|---|---|---|
| 1 | 条件配置化，同一任务集跑两组 | `conditions.yaml`：`baseline→C0`、`governance→C1`；`experiments/spec.py` 的 `validate()`（`:276`）拒绝缺 `baseline`、拒绝 `C0/C1` 之外的码，`cells()`（`:241`）按"条件 × 参与者 × 任务 × 重复"展开且顺序确定 | `test_conditions_map_to_the_two_condition_codes`（`tests/test_experiments.py:64`）、`test_a_missing_baseline_is_rejected`（`:69`）、`test_an_unknown_condition_code_is_rejected`（`:75`）、`test_cells_cover_every_condition_and_task_once`（`:81`）、`test_cell_order_is_deterministic`（`:89`） |
| 2 | 模型 / temperature / seed / 任务顺序全部记录 | `runner.write_manifest()`（`experiments/runner.py:108`）写 `model_id/model_temperature/seed/mode/task_order/n_cells`；`task_order` 是排程实际使用的顺序（按 `pairs` 列出的先后），不是隐含的 | `test_a_run_writes_the_snapshot_logs_and_metrics`（`tests/test_experiments.py:103`，断言 `model_id/model_temperature/seed/task_order` 四个键都在） |
| 3 | `runs/<run_id>/` 含 config 快照、逐条 JSONL、`metrics.json` | `write_snapshot()`（`:91`）写实验文件 + 生效配置全量；`logs/<participant>/<session>.jsonl` 由 `govern/log.py` 写；`metrics.json` 由 `metrics.rebuild()` 从日志算出（`experiments/metrics.py:236`） | 同上；`test_metrics_are_recomputed_from_the_logs_on_disk`（`:139`，删掉 `metrics.json` 也能得到同一份 `conditions` 块） |
| 4 | 断点续跑、并发上限、单条失败不中断 | 续跑判定只看"日志最后一条是不是 `session_end`"（`runner.is_done()` `:67`），崩溃在会话中途的 cell 会被重跑而不是记成完成；`ThreadPoolExecutor(max_workers=…)` 的上限来自 `concurrency.max_parallel`；失败写 `failures.jsonl`（cell/task/condition/error/message，fsync 落盘）后继续 | `test_resume_skips_sessions_that_already_ended`（`:117`）、`test_a_failing_cell_does_not_stop_the_batch`（`:126`，注入必失败的模拟器 → `n_failed == n_total` 且每行含 6 个键） |
| 5 | `python -m experiments.run --config conditions.yaml --dry-run` 自检 | `experiments/run.py:69`：校验文件 → 解析任务集 → 打印计划 → 不写任何文件 | `test_dry_run_plans_without_writing`（`:212`，断言输出含 `dry run`/`sessions` 且 `tmp` 下没有 `.jsonl`） |
| 6 | README 说明"一条命令复现一张结果表" | `experiments/README.md`：命令、实测表、目录结构、指标定义；实测输出见下 | `test_a_real_run_prints_a_table_and_writes_metrics`（`:224`） |

**实测（`runs/E-SIM-01`，12 个会话，2 并发，1.5 s）**

```
$ python -m experiments.run --config conditions.yaml
| condition | sessions | escape rate | mean debt Δ | OTI | mechanical |
|---|---|---|---|---|---|
| C0 | 6 | 1.00 | -3.67 | 0.00 | 0.00 |
| C1 | 6 | 1.00 | -3.67 | 0.00 | 1.00 |

ok: 12 ran, 0 skipped, 0 failed of 12 → runs\E-SIM-01
$ python -m experiments.run --config conditions.yaml --resume
ok: 0 ran, 12 skipped, 0 failed of 12 → runs\E-SIM-01      # 同一张表
```

**如实记录（这一层的边界）**

- **表里的行为指标是退化的，别当结论读**：操作者是脚本，一次性勾满所有复选框、接受建议、从不打开解释。所以 `escape rate = 1.00` 来自"随附建议故意漏掉一个 consumer"（`tests/test_llm.py:405`），`OTI = 0.00` 来自 `review_dwell_ms` 恰好等于 `tau_review_ms`（盲接受要求严格小于）。这两列证明的是"指标能从日志算出来"，不是"治理有效"。要让人读得懂的数字，必须有真人操作者（`--port`，仍是 `planned`）。
- `C0` 的 `mechanical = 0.00` 是口径的结果而非发现：C0 无卡、无勾选，`confirmations` 计到 6 次但没有任何 `dwell_ms`，所以按 SPEC 5.2 的"中位数 < 阈值"判定不成立。
- **YAML 是子集不是全量**：只支持嵌套映射、块/行内列表、注释、引号、`int/float/bool/null`；Tab 缩进、锚点、多行字符串一律报 `SpecError`（`test_a_tab_indent_is_rejected_rather_than_guessed`，`tests/test_experiments.py:48`）。引入 PyYAML 会违反 AGENTS §1 的零依赖；JSON 可直接读（`test_json_is_accepted_directly`）。
- 参数不重复定义：`conditions.yaml` 只描述结构，`model_id/temperature/seed/阈值` 仍只在 `config/config.json`（AGENTS §2.4）。代价是"实验文件本身不自足"，要看参数必须打开快照。
- 这一层让 `tau_review_ms` 与 `mech_dwell_ms` **第一次有了消费者**（`experiments/metrics.py:82`、`:99`）。§6 里原先"这两个参数没有行为消费者"的说法因此更新：它们仍不影响生成行为，但已参与指标计算，并有正反例测试。

---

## 2l. 分析层 → 证据（`analysis/`，从日志读出统计结论）

日志是唯一数据源（AGENTS §2.6），所以 `analysis/` 只读 `runs/<run_id>/logs/*.jsonl`，不改 `govern/`、不重新跑实验、不引入第三方库（AGENTS §1：本机 `pip` 不可用，也没有 `pandas`/`scipy`/`openpyxl`/`matplotlib`）。xlsx 与 PNG 都是本仓库自己写的最小写出器。

| # | 需求 | 证据 | 覆盖测试 |
|---|---|---|---|
| 1 | 描述统计 + 效应量 + 置信区间 | `stats.summarise()` 给 n/mean/sd/median/q1/q3/min/max 与 **t 分布** 95% 均值区间（无方差时明写 `undefined (no variance)`，不打印一个假区间）；`stats.cohens_dz()`、`stats.hedges_g()`（配对设计用小样本校正，比 `dz` 略小）；`stats.bootstrap_ci()` 用固定 seed 的百分位自举作为 t 区间的稳健性对照。落到 `Descriptives` 工作表（17 行 × 13 列） | `test_paired_t_matches_published_values`、`test_t_distribution_matches_the_table`、`test_summary_ci_uses_the_t_quantile`、`test_hedges_g_is_smaller_than_dz`、`test_bootstrap_ci_is_deterministic`（`tests/test_analysis.py:102`–`:158`） |
| 2 | 组间比较：配对 t / Wilcoxon / 混合效应模型，说明选择理由与前提 | 三种都实现并**同时给出**，不做"选一个看起来显著的"：`stats.paired_t()`（前提：差值近似正态、无零差分）、`stats.wilcoxon()`（无并列走精确 DP，有并列走正态近似 + 并列校正 + 连续性校正；`n<6` 时提示精确 p 不可能低于 0.05）、`stats.mixed_model()`（随机截距、REML、单参数 λ 黄金分割；样本内只有一组截距时返回"共线"而不是硬拟合）。前提检查在 `checks.assumption_notes()`，逐条写进 `Paired tests` 的 `Note` 列 | `test_wilcoxon_exact_p_matches_brute_force`（用 2^n 枚举核对 DP 结果）、`test_wilcoxon_is_undefined_when_nothing_changes`、`test_wilcoxon_reports_a_tie_corrected_approximation`、`test_mixed_model_recovers_the_within_group_difference`、`test_mixed_model_refuses_one_group`（`:117`–`:172`）、`test_planted_difference_is_recovered`（假 run 里植入 C1−C0 = −1，检验被复原） |
| 3 | `analysis/results.xlsx` + PNG 图，图注可直接进论文 | `xlsx.write()` 写 7 个工作表（README / Descriptives / Paired tests / Multiplicity / Checks / Figures / Sessions），`[Content_Types].xml` + `styles.xml` 手写，`ZipInfo.date_time` 固定 → 同样输入两次构建字节相同；`png.Canvas` 写 IHDR+IDAT+IEND。四张图：`fig1_outcome_bars`（均值 + 95% CI 误差棒）、`fig2_paired_slope`（按任务的配对斜率）、`fig3_events_per_session`（卡带来了多少交互 = 操纵检查，不是结局）、`fig4_distribution`（每会话任务时长的散点 + 均值线）。`captions_markdown()` → `analysis/captions.md`，每条注记都把 n、检验名与"这不是什么"写全 | `test_output_is_byte_identical_for_the_same_cells`、`test_round_trip_keeps_text_and_numbers`、`test_png_header_and_dimensions`、`test_text_changes_pixels_and_is_deterministic`、`test_end_to_end_outputs`（`:216`–`:234`、`:326`） |
| 4 | 单独检查：数据缺失 / 异常值 / 多重比较校正 | `checks.missing()`：预期 cell 数 vs 实际日志数、未结束会话、缺 `task_end`、配对缺一侧、坏行数——**坏行计数而不吞掉**；`checks.outliers()`：中位数 + MAD，`|z|>3.5` 标记，`MAD==0` 时不报异常并写明理由（否则 0/0 会把每个点都标成离群）；`checks.multiplicity()`：Holm 与 BH **都印**，因为相关指标下两者都不严格正确；`STRUCTURAL = {"gate_latency_ms","blocked_attempts"}` 从家族里排除（见下） | `test_bad_lines_are_counted_not_swallowed`、`test_pairing_keeps_only_complete_pairs`、`test_missing_cell_is_reported`、`test_outlier_flag_finds_the_planted_value`、`test_outliers_are_not_computed_when_mad_is_zero`、`test_multiplicity_needs_p_values`、`test_holm_and_bh_against_hand_computation`（`:252`–`:261`、`:301`–`:321`、`:177`） |

**实测（`python -m analysis.run --runs runs --run-id E-SIM-01 --out analysis`）**

```
missing: expected 12, found 12 sessions, 12 ended, 12 with an outcome
multiplicity: 1 tests, 0 survive Holm at alpha=0.05

ok: 12 session logs, 4 figures
  workbook: analysis\results.xlsx
  captions: analysis\captions.md
```

唯一进入多重比较家族的是任务时长 `elapsed_ms`：差 −2.33 ms，t(5) = −2.44，p = 0.0578（Holm 后仍 0.0578，不显著）。七个结局指标（`debt_delta`/`vuln_delta`/`n_fail`/`lines_added`/…）**每对差值完全相同**，所以 t 与 Wilcoxon 都返回 `n/a`，并在 `Note` 列写明"标准误为 0，统计量是 0/0，不是无限证据"——把它们印成 p<0.001 会是彻头彻尾的伪造。

**如实记录（这一层的边界）**

- **这不是治理有效的证据**。操作者是脚本（`govern/run.py` 的 `_rehearse`），C0 与 C1 收到的是**同一份**重放建议，所以结局指标按设计必然相等。分析层的价值是证明"指标能从日志算出来、且算错会被抓住"，不是证明实验有发现。
- **结构性零值不能当效应比**：`gate_latency_ms` 与 `blocked_attempts` 在 baseline 里恒为 0（C0 没有卡、没有门），"常数 0 vs 一个测量值"不是组间差异。它们被标成 `structural zero in baseline` 并从多重比较家族里排除；`test_report_marks_a_structural_zero`（`:346`）钉死这个标注。
- **混合效应模型在真实数据上不可识别**：只有一个参与者、六个任务，随机截距与截距共线，函数返回说明字符串而不是硬拟合。它的数值正确性只在测试里用两组结构验证（`test_mixed_model_recovers_the_within_group_difference`）——这是"实现了"，不是"用上了"。
- **PNG 不是出版级排版**：5×7 位图字库、只画大写、900 px 宽。可读、可复现、无第三方依赖，但放进论文要用图注与表格承载细节。
- **缺失检查在真实 run 上全是零**：`E-SIM-01` 没有缺 cell、没有坏行、没有未结束会话，所以三条检查的实际触发只在构造的假 run 上验证（`StudyTests`）。这是诚实缺口，不是覆盖。
- 分析层不改 `govern/` 的任何一个字节，也不消费 `runs/` 之外的东西（`R-DEMO`、`R-ADHOC` 混进来会把 12 个会话算成 19 个，所以 `_resolve()` 要求显式 `--run-id`，`test_two_runs_need_an_explicit_choice`）。

---

| 模块 | 状态 | 关键入口 | 自检 / 测试 |
|---|---|---|---|
| `govern/provenance.py` | 新增（M10 = SPEC M11） | `MODULES` `:41`、`ORIGINS` `:44`、`Row` `:53`、`_filled()` `:64`、`parse()` `:78`、`_source_exists()` `:104`、`check()` `:118`、`summarise()` `:158`、`report()` `:171`、`_selftest()` `:186`、`main()` `:243` | `tests/test_provenance.py`（23 条：解析 6、规则 12、CLI 4、自检 1）；`python -m govern.provenance --check` → `ok: 21 rows, 11 modules covered (original=8, reused=3, assisted=10)` |
| `docs/PROVENANCE.md` | 交付物（M10） | 20 行台账，M1–M11 全覆盖；`assisted` 行带 decision + check，`reused` 行指向 `参考代码库/` 的真实路径 | `test_the_shipped_ledger_passes`（`tests/test_provenance.py:105`）、`test_the_shipped_ledger_covers_every_module`（`:109`） |
| `tools/make_release.py` | 新增（M11） | `version()` `:48`、`_skip()` `:55`、`payload()` `:70`、`archive_name()` `:84`、`build()` `:88`、`sha256_of()` `:103`、`write_manifest()` `:111`、`verify()` `:118`、`_selftest()` `:143`、`main()` `:164`；排除规则 `SKIP_DIRS` `:34`、`SKIP_SUFFIXES` `:39`、`SKIP_NAMES` `:40`、`SKIP_PREFIXES` `:43` | `tests/test_release.py`（13 条：归档 5、清单 4、CLI 4）；`python tools/make_release.py --selftest` → `ok: 123 files, 15 directory rules, 9 file rules, tree digest 2db36961aa65`；`--build` → `ok: a2-1.0.0.zip sha256:2f2ea5d2…`，`--verify` → `ok: SHA256SUMS matches the archive` |
| `experiments/spec.py` | 新增（冻结后追加） | `parse_yaml()` `:36`（YAML 子集，JSON 直读）、`load()` `:265`、`validate()` `:276`、`load_tasks()` `:338`、`Spec.cells()` `:241`、`Spec.task_order()` `:225` | `tests/test_experiments.py`（24 条：YAML 6、spec 6、runner 4、metrics 5、CLI 3）；`python -m experiments.run --config conditions.yaml --dry-run` → `ok: 2 conditions × 6 tasks … = 12 sessions (concurrency 2)` |
| `experiments/runner.py` | 新增（冻结后追加） | `plan()` `:47`、`is_done()` `:67`、`write_snapshot()` `:91`、`write_manifest()` `:108`、`execute()` `:177` | `test_a_run_writes_the_snapshot_logs_and_metrics`、`test_resume_skips_sessions_that_already_ended`、`test_a_failing_cell_does_not_stop_the_batch` |
| `experiments/metrics.py` | 新增（冻结后追加） | `read_session()` `:27`、`collect()` `:57`、`blind_accepts()` `:82`、`confirmations()` `:99`、`summarise()` `:194`、`rebuild()` `:236`、`write()` `:243` | `tests/test_experiments.py` 的 MetricsTests（5 条：逃逸率、OTI、解释打开后不盲、机械确认、配对行） |
| `experiments/run.py` + `conditions.yaml` | 新增（冻结后追加） | CLI `main()` `:69`；实验文件定义 `baseline→C0`/`governance→C1`、`pairs`、`repetitions`、`concurrency.max_parallel` | `tests/test_experiments.py` 的 CliTests（3 条） |
| `analysis/load.py` | 新增（冻结后追加） | `Session` `:24`、`session_from_file()` `:172`（`_stamp()` `:111` **跳过空值**取 `task_id`）、`load_run()` `:191`、`paired_series()` `:256` | `tests/test_analysis.py` 的 LoaderTests（`test_task_id_comes_from_the_events_that_carry_it`、`test_bad_lines_are_counted_not_swallowed`、`test_pairing_keeps_only_complete_pairs`） |
| `analysis/stats.py` | 新增（冻结后追加） | `summarise()` `:155`、`bootstrap_ci()` `:184`、`cohens_dz()` `:244`、`hedges_g()` `:251`、`paired_t()` `:261`、`wilcoxon()` `:306`、`mixed_model()` `:400`、`compare_paired()` `:501`、`holm()` `:531`、`benjamini_hochberg()` `:544` | `tests/test_analysis.py` 的 KnownAnswerTests（11 条，含 2^n 枚举核对 Wilcoxon DP） |
| `analysis/checks.py` | 新增（冻结后追加） | `missing_report()` `:46`、`outliers()` `:106`（中位数 + MAD）、`multiplicity()` `:149`、`family_rows()` `:174` | `test_missing_cell_is_reported`、`test_outlier_flag_finds_the_planted_value`、`test_outliers_are_not_computed_when_mad_is_zero`、`test_multiplicity_needs_p_values` |
| `analysis/report.py` | 新增（冻结后追加） | `METRICS` `:24`、`STRUCTURAL` `:38`、`analyse()` `:101`、`figure_bars()` `:168`、`figure_slope()` `:223`、`figure_events()` `:264`、`figure_dots()` `:306`、`_test_rows()` `:355`（Status/Note 列）、`build_outputs()` `:434` | `test_report_marks_a_structural_zero`、`test_end_to_end_outputs`、`test_planted_difference_is_recovered` |
| `analysis/xlsx.py` / `analysis/png.py` | 新增（冻结后追加） | `write()` `xlsx.py:106`（7 表、固定 `date_time`）、`read_sheets()` `:164`；`Canvas` `png.py:91`（5×7 位图字库、IHDR+IDAT+IEND） | `test_output_is_byte_identical_for_the_same_cells`、`test_round_trip_keeps_text_and_numbers`、`test_every_sheet_is_present`、`test_png_header_and_dimensions`、`test_drawing_outside_the_canvas_is_clipped` |
| `analysis/run.py` | 新增（冻结后追加） | `_table()` `:67`、`_selftest()` `:114`、`main()` `:151`（`--runs/--run-id/--out/--selftest/--json`，多 run 必须显式选一个） | CliTests（4 条）；实测 `python -m analysis.run --runs runs --run-id E-SIM-01 --out analysis` → `ok: 12 session logs, 4 figures` |
| `govern/session.py` | 新增（M8 = SPEC M2） | `load_schedule()` `:68`；`assign()` `:83`；`chi_square_p()` `:114`；`simulate()` `:126`；`rebuild_state()` `:165`；`Session` `:216`（`start/submit_prompt/toggle/confirm/generate/act/end/state/checkpoint/resume`）；`_selftest()` `:576` | `tests/test_session.py`（37 条：分配 9、模拟 7、同意 3、流程 11、续跑 4）；`python -m govern.session --selftest` → `ok: 10 participants, 6 slots each, deterministic, C0=300 C1=300 chi2 p=1.000` |
| `govern/run.py` | 重写（M8） | `log_for()` `:31`；`_rehearse()` `:87`；`selftest()` `:139`；`single()` `:165`；`batch()` `:202`；`resume()` `:242`；`simulate()` `:266`；`main()` `:315` | `tests/test_run.py`（9 条：自检/演练 2、模拟 1、单会话 3、批处理 2）；`python -m govern.run --selftest` → `ok: 6 tasks, 6 cards` |
| `config/schedule.json` | 新增（M8） | `schedule_id: SCH-01`、`seed: 42`、三对、`P01`–`P10`、`orders` AB/BA 交替 | `test_the_shipped_schedule_covers_every_pair`（`tests/test_session.py:64`）、`test_task_index_is_sequential_from_zero`（`:80`） |
| `govern/patch.py` | 新增（M1） | `parse()` `:37`；`changed_files()` `:91`；`apply_unified_diff()` `:102` | `tests/test_patch.py`（5 条：单 hunk、多文件、新建文件、上下文不匹配、目标目录缺失） |
| `govern/corpus.py` | 扩展（M2） | `check_task()` `:126`；`check_all()` `:158`；新增 `_pair_summary()` `:165`、`summarise()` `:187`（多输出 `pairs N/N within X%`） | `tests/test_corpus.py`（17 条）；`python -m govern.corpus --check` → `ok: 6 tasks, gold 6/6, pairs 3/3 within 20%` |
| `tools/make_repo.py` | 扩展（M2） | `DOMAINS` `:29`（6 个域）；`_files()` `:577` 按层分派；`_labels()` `:653` 从 diff 反算文件数；`build_corpus()` `:707` | `python tools/make_repo.py --selftest` → `ok: 61 corpus files match the factory` |
| `govern/impact.py` | 新增（M3 = SPEC M4） | `analyze()` `:170`；`recall_precision()` `:284`；`impact_hash()` `:265`；`risk_level()` `:272` | `tests/test_impact.py`（18 条：recall/precision、负对照、风险分层、健壮性、确定性、性能、CLI）；`python -m govern.impact --selftest` → `ok: recall=1.00 precision=1.00 on 6 tasks (min recall 1.00, min precision 0.80)` |
| `govern/card.py` | 新增（M4 = SPEC M5） | `build()` `:65`；`to_html()` `:108`；`CardItem` `:34`、`Card` `:44` | `tests/test_card.py`（16 条）；`python -m govern.card --selftest` → `ok: T-L01a card has 5 items, 5 required, no patch text` |
| `govern/gate.py` | 新增（M4 = SPEC M6） | `Gate.toggle()` `:57`、`decide()` `:72`、`open()` `:82`、`issue_token()` `:87`、`consume_token()` `:97`；`PassThroughGate` `:105` | `tests/test_gate.py`（19 条）；`python -m govern.gate --selftest` → `ok: 6 cards, blocked until every item is confirmed, C0 passthrough, min dwell 800 ms` |
| `govern/hidden.py` | 新增（M7 = SPEC M8 验收 4） | `RUNNER` `:21`（子解释器脚本）；`run(repo, hidden, timeout_s)` `:49`（`Popen` + 超时强杀，返回 `code/failures/n`）；`_selftest()` `:89` | `tests/test_hidden.py`（10 条：通过/失败/import 爆炸/`sys.exit`/挂死强杀/空套件/仓库内导入/噪声输出/自检）；`python -m govern.hidden --selftest` → `ok: hidden suite runner reports pass/fail in a child interpreter` |
| `govern/score.py` | 新增（M7 = SPEC M8） | `load_rules()` `:92`；`rules_hash()` `:102`；`scorer_version()` `:108`；`debt()` `:120`；`vuln()` `:125`；`scan_repo()` `:317`；`counts()` `:332`；`run_hidden_tests()` `:343`；`baseline()` `:352`；`_line_delta()` `:373`；`evaluate()` `:392`；`is_correct()` `:416`；`scored_event()` `:422` | `tests/test_score.py`（41 条：六类规则各正反例、权重、语料阶梯、确定性、版本 hash、基线/评估、隔离、事件、CLI）；`python -m govern.score --selftest` → `ok: 6 rules (…) with positive and negative fixtures, gold 6/6, clean repository 0 debt` |
| `config/rules.json` | 新增（M7，Q6 的落点） | 六条规则各带 `rule_id/category/severity/weight` 与阈值；`version 1.0.0` | `test_every_rule_declares_id_severity_and_weight`（`tests/test_score.py:134`）、`test_the_six_categories_are_exactly_the_spec_list`（`:140`） |
| `govern/log.py` | 新增（M5 = SPEC M7） | `SCHEMA_VERSION` `:25`；`ENVELOPE` `:70`；`EVENT_FIELDS` `:91`；`validate()` `:260`；`Logger` `:320`；`scan_pii()` `:447`；`purge()` `:480` | `tests/test_log.py`（34 条）；`python -m govern.log --selftest` → `ok: 16 event types, seq from 1, atomic append, purge clean` |
| `govern/llm.py` | 新增（M6 = SPEC M3） | `Context.for_task()` `:95`；`Context.sha256()` `:135`；`Suggestion.content_hash()` `:168`；`Client.generate()` `:246`；`_replay()` `:266`；`_live()` `:285`；`_record()` `:349`；`_selftest()` `:397` | `tests/test_llm.py`（38 条）；`python -m govern.llm --selftest` → `ok: 6 recordings, 10 replays each, 6/6 identical, no network used` |
| `tools/scan_secrets.py` | 新增（M6 = SPEC 3.11 第 5 条） | `_PATTERNS` `:38`；`scan_text()` `:50`；`scan_paths(paths, root=None)` `:67`；`tracked_files()` `:99`；`main()` `:123` | `tests/test_secrets.py`（14 条）；`python tools/scan_secrets.py` → `ok: 0 finding(s) in 110 files` |
| `tools/make_recordings.py` | 新增（M6，PLAN 未列） | `suggest()` `:70`；`recording()` `:91`；`build()` `:112`；`selftest()` `:129` | `python tools/make_recordings.py --selftest` → `ok: 6 recordings match the factory` |
| `recordings/` | 数据（`source: "sim"`） | `recordings/qwen2.5-coder-7b/<request_sha256>.json`，6 个任务各一条 | `test_the_repository_ships_one_recording_per_task`（`tests/test_llm.py:381`）、`test_the_shipped_recordings_match_the_factory`（`:393`） |
| `govern/web.py` | 新增（M9 = PLAN M9） | `App` `:38`（`card_view()` `:56`、`state()` `:81`、`card()` `:88`、路由表 `_GET`/`_POST` `:177`、`handle()` `:186` 永不抛）；`Handler` `:207`；`GovernServer` `:259`；`make_server()` `:269`；`serve()` `:274`；`_selftest()` `:288` | `tests/test_web.py`（22 条：页面/路由、卡片、门控、C0 基线、动作、结束、状态、卫生）；`python -m govern.web --selftest` → `ok: 6 routes wired, card rendered from session state` |
| `static/index.html` | 新增（M9） | 262 行原生 JS，无构建步骤；左 `main#transcript` / 右 `aside`；`renderCard()` `:87`、`updateCounter()` `:152`、`labelFor()` `:169`、`toggle()` `:166`；`?playback=1` 从服务端状态重绘 `:257` | `tests/test_web.py` 的 IndexTests 与 `test_the_page_never_ships_a_pre_ticked_checkbox`（`:323`） |
| `tools/make_storyboard.py` | 新增（M9 验收的取证工具） | `capture()`、`shoot()`（无头 Chrome）、`check()`；启动**真实**服务器在 `port=0`，按人手顺序打 API，再拍照 | `python tools/make_storyboard.py --check` → `ok: 3 storyboard frame(s) in storyboards` |
| `storyboards/` | 交付物（M9） | `1-c1-gate-closed.png`、`2-c1-gate-open.png`、`3-c0-baseline.png` + `README.md`（逐帧的动作/响应/日志序列，以及"这三帧不是人类被试数据"的声明） | 同上；README 里的日志序列由 `python -m govern.log --validate` 同源事件类型核对 |
| `tools/make_diagram.py` | 新增（报告第 2–3 节配图） | `NODES`（13 个框 → 源文件 + 必须仍存在的符号）、`EDGES`（15 条边 → 代码位置）、`Diagram.node/edge/badge`、`build()`、`check()`、`main()`；用 `analysis/png.py` 作画，无第三方依赖 | `tests/test_diagram.py`（6 条）；`python tools/make_diagram.py --check` → `ok: 13 stages match the source` |
| `System diagram/` | 交付物（报告引用） | `system-diagram.png`（1300x960，实线=implemented、蓝色虚线=simulated、灰=planned）+ `README.md`（框/边的证据表、控制流、刻意不画的东西、图的局限） | 同上；`test_rebuilding_reproduces_the_shipped_bytes` 保证图与生成器一致 |
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

# 评估卡与门控验收（M4 = SPEC M5/M6）
.\.venv\Scripts\python.exe -m govern.card --selftest
.\.venv\Scripts\python.exe -m govern.gate --selftest

# 日志器验收（M5 = SPEC M7）；--validate / --scan 可对任意一次运行的日志复核
.\.venv\Scripts\python.exe -m govern.log --selftest
.\.venv\Scripts\python.exe -m govern.log --validate runs\<run_id>\logs\<pid>\<session>.jsonl
.\.venv\Scripts\python.exe -m govern.log --scan     runs\<run_id>\logs\<pid>\<session>.jsonl
.\.venv\Scripts\python.exe -m govern.log --purge --run-dir runs\<run_id> --before 2026-01-01

# LLM 客户端验收（M6 = SPEC M3）：6 条录制各 replay 10 次、无网络、无密钥
.\.venv\Scripts\python.exe -m govern.llm --selftest

# 录制可重建性 + 密钥/端点扫描（交付前两条闸）
.\.venv\Scripts\python.exe tools\make_recordings.py --selftest
.\.venv\Scripts\python.exe tools\scan_secrets.py

# 结果评估器验收（M7 = SPEC M8）：六类规则各带正反例、gold 6/6、干净仓库 0 债务
.\.venv\Scripts\python.exe -m govern.score --selftest
.\.venv\Scripts\python.exe -m govern.score --task T-L03a      # 打印某个任务的基线（债务/漏洞/失败测试）
.\.venv\Scripts\python.exe -m govern.hidden --selftest        # 子进程跑隐藏套件的那一层

# 项目自检
.\.venv\Scripts\python.exe -m govern.run --selftest

# 编排器验收（M8 = SPEC M2）：分配确定性、100 次模拟的卡方、续跑
.\.venv\Scripts\python.exe -m govern.session --selftest
.\.venv\Scripts\python.exe -m govern.run --simulate 100

# 一次完整的作者自测会话（SIM；写 runs/R-ADHOC/logs/<participant>/<session>.jsonl）
.\.venv\Scripts\python.exe -m govern.run --session S-001 --participant P01 --condition C1 --task T-L01a
.\.venv\Scripts\python.exe -m govern.log --validate --run-dir runs\R-ADHOC

# Web UI 验收（M9）：自检 + 真浏览器走两条路径
.\.venv\Scripts\python.exe -m govern.web --selftest
.\.venv\Scripts\python.exe -m govern.run --session S-UI1 --participant P01 --condition C1 --task T-L01a --port 8000
python tools\make_storyboard.py            # 重新生成三张 storyboard 帧（需 Chrome 或 Edge）
python tools\make_storyboard.py --check    # 只核对三帧存在且非空

# 溯源台账验收（M10 = SPEC M11）：提交前必跑
.\.venv\Scripts\python.exe -m govern.provenance --check
.\.venv\Scripts\python.exe -m govern.provenance --selftest

# 全链路冻结（M11）：六条完成定义逐条跑；批量会话无需网络与密钥
.\.venv\Scripts\python.exe -m govern.run --dry-run
.\.venv\Scripts\python.exe -m govern.run --batch --participant P01 --schedule config\schedule.json --run-id R-DEMO
python tools\make_release.py --build        # dist/a2-<version>.zip + SHA256SUMS
python tools\make_release.py --verify       # 复核摘要
python tools\make_release.py --selftest     # 核对排除规则
.\.venv\Scripts\python.exe -m pytest tests\test_end_to_end.py tests\test_config_discipline.py tests\test_release.py -q

# 实验编排（冻结后追加）：一条命令出一张表，一条命令验证不落盘
.\.venv\Scripts\python.exe -m experiments.run --config conditions.yaml --dry-run
.\.venv\Scripts\python.exe -m experiments.run --config conditions.yaml
.\.venv\Scripts\python.exe -m experiments.run --config conditions.yaml --resume   # 续跑：只剩没跑完的 cell
.\.venv\Scripts\python.exe -m pytest tests\test_experiments.py

# 分析层（冻结后追加）：12 个会话 → results.xlsx + 4 张图 + captions.md
.\.venv\Scripts\python.exe -m analysis.run --runs runs --run-id E-SIM-01 --out analysis
.\.venv\Scripts\python.exe -m analysis.run --selftest        # 统计/工作簿/画布对已知答案自检
.\.venv\Scripts\python.exe -m pytest tests\test_analysis.py
python tools\word_count.py --check                           # README 自称的 838 词必须与正文一致
```

> 说明：`.venv/` 只是本机开发工具链（pytest 属**测试期**依赖，不进入运行时）；
> 交付代码在 `govern/` 与 `tools/` 内，只用标准库。隐藏测试套件自 M7 起由
> `govern/hidden.py` 用标准库在子解释器里跑（不再需要 pytest），所以
> `python -m govern.corpus --check` 与 `python -m govern.score --selftest`
> 在裸 Python 3.11+ 上同样可用；`python -m unittest discover -s tests -q` 也已实测可用（384 条）。

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
| `config/config.json` 新增 `card_item_max_chars`（M4） | SPEC M5 验收 2 要求"每条 ≤ 120 字符"，而 AGENTS §2.4 禁止把这类阈值写死在代码里 | 纯附加键；`Config` 增加同名字段，`load()` 的"缺键即报错"语义不变，旧 config 会明确失败而不是静默取默认值 |
| `Gate.__init__` 增加可选 `clock`（M4） | `toggle()` 必须返回 `dwell_ms`（机械确认指标要用），而 monotonic 时钟无法在测试里断言具体毫秒数 | 关键字参数带默认值，PLAN 的 `Gate(card)` 调用方式不变 |
| 新增 `PassThroughGate(Gate)`（M4） | SPEC M6 验收 4 要求 C0 "走同一个接口、`blocked=false` 恒成立"，但 PLAN 的 `Card` 没有条件字段、`Gate` 也没有条件参数 | 子类只覆写 `decide()`，接口完全一致；C0 的卡由 `build(..., "C0")` 产出，`n_items=0` |
| 新增 `issue_token()` / `consume_token()`（M4） | SPEC M6 的输出清单要求"授权令牌（一次性）"，PLAN 的接口只列了 `toggle/decide/open` | 两个附加方法，令牌在阻塞时为 `None`、任何勾选变化即失效，单次使用后清除 |
| 新增 `CardItem` 数据类（M4） | PLAN 只写了 `Card.items`，条目形状由 SPEC M5 的输出定义（`item_id/statement/category/affected_symbol/evidence_ref/required`） | 与 SPEC 的 `card_view.items` 字段一一对应，无额外字段 |
| `EVENT_FIELDS` 实为 **16** 类事件（M5） | PLAN 第 138 行写"SPEC 4.3 的 14 类事件"，逐条数 SPEC 4.3 的表格是 **16** 类（`session_start` … `integrity_event`）；PLAN 的 14 是笔误 | 按 SPEC 实现 16 类；`test_all_sixteen_event_types_validate`（`tests/test_log.py:166`）以 SPEC 为准钉死数量 |
| 数组截断时新增 `x_<field>_total` 字段（M5） | SPEC M7 验收 5 要求"截断并另记总数"，但 4.5 条不许发明新字段 | 走 4.5 已给的 `x_` 前缀通道，`validate()` 只对 `x_` 开头的未声明字段放行；不写这个字段就等于悄悄丢数据 |
| `generation_request.mode` 增加 `replay` 取值（M5） | SPEC 4.3 的枚举写 `mock`/`live`，但 Q3 拍板后交付默认是 `replay`（回放录制、无网络无密钥），`mock` 已不再是独立模式 | 枚举变 `replay`/`live`/`mock`；如果不加这一项，默认路径无法用自己的名字记录，日志会系统性撒谎 |
| `scan_pii()` 与 `--validate`/`--scan` CLI（M5） | SPEC M7 验收 3 要求"对全部日志做正则扫描"，PLAN 的接口清单只有 `validate()` 与 `purge()` | 纯附加函数与只读子命令；`scan_pii()` 是验收 3 的执行体，`--validate`/`--scan` 让评审者能对真实运行日志复核 |
| `purge()` 额外无条件删除 `*.jsonl.tmp`（M5） | PLAN 第 145 行只要求"`purge` 后删除 `.jsonl.tmp`"；本实现不留任何 `.tmp` 中转文件，但若历史版本崩溃留下残片，仍须清理，否则"purge 干净"是空话 | 删除清单里会列出这些文件；测试 `test_purge_leaves_no_jsonl_or_tmp_behind`（`tests/test_log.py:356`）覆盖 |
| 日志目录 `logs/<participant_id>/<session_id>.jsonl`（M5） | SPEC 4.6/M7 给的是这个形状，PLAN 的 `Logger(run_dir, meta)` 未规定子目录 | `Logger` 首参是 run_dir，内部拼 `logs/<pid>/`；SPEC 的路径优先 |
| `MAX_LINE_BYTES`/`MAX_ARRAY_ITEMS` 留在代码里（M5） | 它们是 SPEC M7 验收 5 写死的 schema 上限（4 KB / 20 项），不是可调阈值：改它等于改 schema 含义，`schema_version` 也得跟着变 | 与 AGENTS §2.4 不冲突的例外——配置里放的是"实验参数"，这两个是"格式常量"；已在常量旁注释 |
| 录制目录名用 slug（M6） | PLAN 第 128 行写 `recordings/<model_id>/...`，而 `qwen2.5-coder:7b` 的 `:` 在 Windows 上是非法字符（实测 `NotADirectoryError: [WinError 267]`） | `Client._model_slug()` 把非 `[A-Za-z0-9._-]` 换成 `-`，目录为 `recordings/qwen2.5-coder-7b/`；`model_id` 字段仍写原始值，两者可对照 |
| `_replay()` 增加"模型不一致即拒绝"（M6） | SPEC M3 验收 6 要求 `model_id` 是"录制时的真实模型名"；若允许跨模型回放，日志里的模型名就会和实际产出脱钩 | 多一道 `SchemaViolation`；`test_a_recording_from_another_model_is_refused`（`tests/test_llm.py:297`）钉死 |
| `scan_paths(paths, root=None)` 增加 `root`（M6） | 忽略规则若按**绝对**路径判定，仓库一旦位于 `.scratch/` 之类的目录下就会被整体跳过（测试里恰好如此，实测 0 命中） | 传 `root` 时按相对路径判定忽略目录；不传时退回旧行为，`scan_paths(paths)` 调用方式不变 |
| 扫描器豁免 4 个文件（M6） | `AGENTS.md`、`docs/SPEC.md` 原文里就写着规则本身（密钥前缀与端点字面量），`tools/scan_secrets.py` 与 `tests/test_secrets.py` 含拼装的模式与合成样例——不豁免就变成"文档记录规则即违规" | `ALLOWED_PATHS`（`tools/scan_secrets.py:31`）只放这 4 个；README、报告、录制、`govern/` 仍全文扫描，真密钥粘贴到任何别处都会被报 |
| `Session.__init__` 增加三个**仅关键字**参数（M8） | PLAN 的 `Session(run_dir, task, condition, participant, logger)` 不足以表达 M8 需要的三件事：`mode`（replay/live）、`task_index`（日志信封的第几个任务）、`client`（测试要注入录制好的客户端） | 位置参数与 PLAN 完全一致，新参数全在 `*` 之后且带默认值，PLAN 的构造调用不改也能跑 |
| 新增 `Gate.restore()` / `confirmed_ids()`（M8） | 续跑必须能把"已勾选哪些条目"从日志恢复到门里，否则 resume 后的门状态与日志不一致（等于伪造状态） | 两个只读/恢复方法；`Gate(card)` 的行为不变，19 条门测试全绿 |
| `score.evaluate()` 增加可选 `hidden_run=`（M8） | 会话结束时已经用 `hidden.run()` 跑过一次隐藏套件（要写 `test_run` 事件），若 `evaluate()` 再跑一次，同一份提交要付两倍子进程时间，还可能因超时给出一致性差异 | 传入时直接复用 `(tests_pass, failures)`；不传时行为与 M7 完全一致 |
| `config/config.json` 新增 `alpha_sim`（M8） | 卡方判定的显著性水平属实验参数，AGENTS §2.4 禁止写进代码 | 纯附加键；`Config` 加同名字段，`load()` 仍会拒绝缺键 |
| `--selftest` 输出从 `0 cards` 改为真实卡数（M8） | M0 时卡片模块尚不存在，占位值 `0 cards` 会与 SPEC M5 的"六个任务各产出一张卡"自相矛盾 | 现输出 `ok: 6 tasks, 6 cards`；`tests/test_smoke.py` 与 `tests/test_run.py` 都以该行为准 |
| `--port` 走 `EXIT_NOT_READY`（M8）→ **已被 M9 取代** | M9 之前 Web UI 不存在；把"未实现"报成用法错误（退出码 2）会掩盖真实原因 | M8 期间新增 `_not_ready()` 并保留 `EXIT_NOT_READY = 3`；M9 落地后该分支改为真正启动服务器，`_not_ready()` 已删除 |
| `govern.run --simulate N` 只写 `runs/_sim/sim.json`（M8） | 模拟 100 次分配不应产生 600 个空会话日志（`runs/` 不入库，但也没必要写噪声） | 报告文件含 n/counts/chi2/p/alpha/balanced/pairs；`--simulate` 不写任何 `.jsonl` |
| 新增 `tools/make_recordings.py` 与 `recordings/`（M6） | 本机没有任何 API 凭据，若等真实调用就永远没有可复现的 replay；SPEC M3 验收 2 要求"录制完整可复现" | 录制由工厂从 gold patch 派生并标 `source: "sim"`，可逐字节重建（`--selftest` 校验）；这是**模拟**建议，不是模型输出，报告里如实说明 |
| `Client.__init__` 增加可选 `logger`（M6） | `generation_request` / `integrity_event` 必须有地方写；PLAN 的构造签名没有日志参数 | 关键字参数默认 `None`（不写日志），`Client(config, mode, recordings, api_key_env)` 调用方式不变 |
| 端点从 `A2_API_BASE` 读取（M6） | PLAN 只规定密钥从环境变量取，没说端点从哪来；写进 config 就违反了"无端点入库" | 与 `A2_API_KEY` 同一策略：只有环境变量，`EndpointMissing` 有单独错误码与测试 |
| 新增 `govern/hidden.py`（M7） | 隐藏套件原来由 `govern/corpus.py` 用 `python -m pytest` 跑（需要 `.venv`）。AGENTS §1.1 要求"零第三方运行时依赖"，且硬规则 1 的验收命令是裸 `python -m unittest discover`——实测在裸 Python 上 `corpus --check` 直接失败（`No module named pytest`） | 抽出标准库子解释器运行器，`corpus` 与 `score` 共用；pytest 回归为**仅测试期**工具。副作用：`corpus --check` 的 `baseline=` 原因文本变长为 `test_x.py::test_y: AssertionError: …`（更精确，汇总行不变） |
| 新增 `govern/provenance.py`（M10） | SPEC M11 定义了台账字段与四条验收，但既没说表格格式也没说解析器怎么读——不写解析器就只能靠人眼核对，"一行命令在提交前跑"（验收 4）无从谈起 | 只认 markdown 表格；行内格数不符抛 `LedgerError`（否则 assisted 行丢字段无人发现）；退出码 `0/1/2` 区分通过、台账有错、台账读不出 |
| `-`/`—` 视为空单元格（M10） | markdown 表格用横线表示"空"，第一版把它当内容，于是把某行 `check` 改成 `-` 仍能通过校验（实测 `exit=0`），这正是台账最容易被糊弄的地方 | `_filled()`（`govern/provenance.py:64`）统一判定；`test_a_dash_does_not_count_as_evidence`（`tests/test_provenance.py:141`）钉死 |
| 台账增加两条结构检查（M10） | SPEC 四条只管"有没有三值、有没有 decision/check、路径真不真"，没管 `item_id` 重复与枚举拼写——写 `ai` 或把一件事拆成两行都能混过 | `check()` 报重复 `item_id`、报非枚举的 `origin`/`module`；属加严，不改变 SPEC 的验收口径 |
| `corpus._run_hidden()` 改为调用 `hidden.run()`（M7） | 同上；另外 pytest 的退出码含义与"套件挂死/读不出报告"混在一起，超时也无法区分 | 返回码语义变成 `0 通过 / 1 有失败 / 2 未完成`；`_failure_reason()` 未改动，仍能从失败清单里取第一行 |
| `debt_delta` 以 float 写入（M7） | SPEC 4.3 的 `task_end.debt_delta` 是 float，`log.validate()` 按 float 校验；整数加权计数之差在 schema 上会被判类型错 | `Outcome.debt_delta: float`，`evaluate()` 里显式 `float(...)`；`vuln_delta` 仍是 int |
| 新增只读路由 `GET /api/card`（M9） | `GET /api/state` 只报 `card_id/confirmed_ids/gate_open/phase/ended`，**不含条目**，所以从服务端状态重绘页面时无法还原复选框与文案；storyboard 取证也需要这一点 | 纯附加只读路由，返回 `card_view()`；`/api/state` 的字段与语义不变 |
| `static/index.html` 的 `?playback=1` 分支（M9） | 页面原本只在用户操作后渲染；要让"重载后仍是同一状态"和"无人点击也能拍照"成立，必须有从服务端状态重绘的入口 | 只在带该查询参数时触发，正常访问路径的交互行为不变；顺带证明 SPEC M2 验收 4 在 UI 层也成立（状态可只从日志重建） |
| 拦截提示按**陈述**而非 item_id 列出未确认项（M9） | 第一版直接渲染服务端 `missing` 的 `item_id`（`T-L01a-side_effect-003`），人能读的字面意义为零，等于把"机械勾选"换个形式又做了一遍 | 只改前端展示（`labelFor()`）；`/api/toggle` 与 `/api/generate` 返回的 `missing` 仍是 `item_id` 列表，API 契约不变 |
| `_close()` 增加 `withdrawn` 参数（M9） | UI 模式下用户可能没点 Finish 就关掉页面；把它记成"完成"就是伪造数据 | 位置参数与默认值向后兼容；未完成时 `completed_all=false`、`withdrawn=true` |
| `--port` 要求同时给 `--session` 与 `--task`（M9） | 服务器一次只服务一个会话，缺会话就没有可展示的对象；默认值会悄悄造出一个没人确认过的会话 | 缺参数 → `EXIT_USAGE` 并说明原因；`test_port_without_a_session_is_a_usage_error`（`tests/test_smoke.py:64`） |
| `card._statement()` 增加硬截断（M11） | 模块超长时回落到 `symbol (category)`，回落结果**仍可能超过 `card_item_max_chars`**（实测上限 24 时返回 53 字符），SPEC M5 的"每条 ≤ 120 字符"因此形同虚设 | 回落后再按上限截断并加省略号；`test_the_card_statement_limit_comes_from_config`（`tests/test_config_discipline.py:43`）在 24 字符上限下断言成立 |
| 新增 `gate.threshold_summary()`（M11） | `mech_dwell_ms` 没有任何行为消费者（它是 SPEC 5.2 的指标阈值），但"读自 config"这件事仍须可测：原来这个值只在 `_selftest` 的 f-string 里出现，无法被断言 | 新函数返回同一句文本，`_selftest()` 改为调用它；**输出字符串逐字不变**（`min dwell 800 ms`），故 `tests/test_gate.py` 的既有断言不受影响 |
| `tools/make_release.py` 需要 `sys.path` 引导（M11） | 以 `python tools\make_release.py` 运行时 `sys.path[0]` 是 `tools/`，`from govern import config` 直接 `ModuleNotFoundError`（实测），与 `make_repo.py`/`make_recordings.py` 的写法一致才能跑通 | 模块顶部 `sys.path.insert(0, str(ROOT))`，与既有两个工具同款 |
| `--batch` 必须给 `--participant`（M11） | 批量会话按被试逐个分配 slot，没有被试就没有可分配的 schedule 行；给默认值会静默造出一个"P01"的假被试 | 缺参数 → `EXIT_USAGE`；`test_3_one_command_reproduces_a_batch_without_network_or_key`（`tests/test_end_to_end.py:56`）以显式 `--participant P01` 调用 |
| `app_version` 由 `0.0.0-draft` 升到 `1.0.0`（M11） | M11 是冻结里程碑，`app_version` 会写进每条日志事件的信封；冻结前采集的数据必须能与冻结后区分开 | 仅改 `config/config.json` 一个值；归档名随之变为 `a2-1.0.0.zip`，测试全部读 `CONFIG.app_version` 故不受影响 |
| `dist/` 加入 `.gitignore`（M11） | 归档可重建且字节可复现（实测两次构建同 hash），把 400 KB 二进制放进 Git 只会让"哪个才是提交版"变模糊 | 摘要写进 `README.md` 与 `docs/PLAN.md` 的 M11 行；评审者用 `make_release --build/--verify` 自重建 |
| `govern.run` 新增公开别名 `rehearse()` / `close_session()`（experiments 层） | 编排层需要"跑完一次会话并收尾"，而原实现只有下划线私有的 `_rehearse()` / `_close()`；让 `experiments/runner.py` 去碰私有名会破坏 AGENTS §3 的模块边界 | 两个别名只是转发，签名与行为不变；`_private` 仍被 `batch()`/`single()` 使用，`tests/test_run.py` 未受影响 |
| `scan_secrets.SKIP_DIRS` 增加 `runs` 与 `dist`（experiments 层） | 会话快照的 `work/` 是语料副本，跑过一次实验后扫描文件数从 137 涨到 317，且 `runs/` 本就 `.gitignore`（AGENTS §4） | 扫描器只扫会被提交的东西；实测回到 `ok: 0 finding(s) in 137 files`，注释里写明这两个目录为何跳过 |
| `experiments.run` 多给一个 `--limit N`（experiments 层） | 调试时只想跑前几个 cell；不给就只能改实验文件，那会污染"实验定义"这一层 | 只影响调度数量，不写进 `metrics.json`；`--resume` 与它并存时先按已完成跳过再截断 |
| 新增顶层包 `analysis/`（分析层） | SPEC M10 原本按 Q8 标 **N/A**（"分析管线"不在本期交付集），`govern/` 只负责产出日志。用户后续要求"基于 runs/ 的日志生成分析脚本"，于是补上这一层；让它独立于 `govern/` 是为了守住 AGENTS §2.6"日志是唯一数据源"——分析不得反过来影响被测系统 | 只读 `runs/<run_id>/logs/**/*.jsonl`，不 import `govern` 的任何模块（除了比对常量），不改 `govern/` 一个字节 |
| xlsx 与 PNG 由本仓库自己写（分析层） | AGENTS §1 要求零第三方运行时依赖，本机 `pip` 不可用（`Errno 13`），`pandas`/`scipy`/`openpyxl`/`matplotlib` 全都没有；不自己写就没有 `results.xlsx` 与图 | `analysis/xlsx.py` 与 `analysis/png.py` 各约 200 行，只用 `zipfile`/`zlib`/`struct`；输出确定性（固定 `ZipInfo.date_time`），靠往返测试与已知答案测试锁定 |
| `python -m analysis.run` 在有多个 run 时必须显式 `--run-id`（分析层） | `runs/` 下还躺着 `R-DEMO`（6 会话）与 `R-ADHOC`（1 会话），默认"全部合并"会把 12 个 cell 算成 19 个并重复计数同一任务 | 缺 `--run-id` 时打印候选并以非零退出；`test_two_runs_need_an_explicit_choice` 钉死 |
| `tools/word_count.py` + README 字数自纠（分析层同期） | README 一直写着 "210 words"，实为手算错值（实测近四倍）；评分说明虽无 README 字数上限，但一个能被轻易证伪的数字会连带削弱其余陈述的可信度 | 新增工具按**明文规则**计数，`--check` 与 `tests/test_end_to_end.py` 的 `test_the_readme_states_its_own_prose_word_count_correctly` 一起防止再漂移；README 里保留"旧值错了"的说明而不是悄悄改掉；文档正文不抄写具体数字，只指向该工具的输出 |

---

## 6. 明确没有做的（避免把 planned 说成 implemented）

- 没有采集任何人类被试数据；`M2` 是 **SIM**，`M10` 是 **N/A**（SPEC 3.0）。
- **没有真正调用过任何外部模型 API**：`govern/llm.py` 的 `live` 路径只在测试里的回环 stub 上验证过（`tests/test_llm.py:68` 的 `_Stub`），`recordings/` 里 6 条录制全部是 `source: "sim"` 的作者模拟。报告与 README 一律按"模拟建议"表述，不得写成"模型输出"。
- 影响分析器（SPEC M4 / PLAN M3）**已实现**，但它只做静态分析：不做语义推断、不读 diff、不调模型。
  它能识别的"契约"是"被 ≥ 2 个包内模块读取的顶层值"这一操作化定义（见 `govern/impact.py` docstring），
  因此它**不会**发现"两个模块各自实现同一算法"这类纯语义重复。
- 评估卡与门控（SPEC M5/M6 / PLAN M4）**已实现**，并且从 M8 起**接线到会话**：`Session.submit_prompt()` 产卡、`toggle()/confirm()` 调门、`generate()` 在门未开时抛 `GateClosed` 并落 `gate_decision(blocked=true)`。
- 遥测日志器（SPEC M7 / PLAN M5）**已实现**，并且从 M8 起**有真实写入方**：`govern/session.py` 的编排器会把一次作者自测会话写成完整 JSONL（`runs/` 下），`python -m govern.log --validate --run-dir …` 可复核。
- LLM 客户端（SPEC M3 / PLAN M6）**已实现**，但只交付 `replay` 模式：`live` 需要 `A2_API_BASE` + `A2_API_KEY`，本机没有，故从未对真实服务发起过请求。
- 结果评估器（SPEC M8 / PLAN M7）**已实现**，但**没有跑过任何一次会话**：`baseline()`/`evaluate()` 只在 6 个种子仓库与测试里的构造样本上验证过，`debt_delta`/`vuln_delta`/`lines_added` 还没有一条来自真实会话的数据。
  - 已实测的覆盖缺口：六类规则**测不到**轻层语料的坏味道（浮点金额、模块级缓存、语义重复的税额推导），L 层 `debt=0`，M=3，H=8（加权）。因此"债务下降"只在 M/H 层可测；L 层靠隐藏测试与行数指标。这一条不得在报告里含糊成"每层都能测出债务下降"。
- 端到端指标重算（SPEC M10 `analysis/`）原本是 **N/A**（SPEC 3.0 交付集），冻结后由 `experiments/metrics.py` 与 `analysis/` 补上（见本节最后一条）；`govern.log --purge` 之后无法重算依赖已删数据的结论，这一点在 SPEC M7 验收 7 里已如实降级记录。
- 会话控制器与 CLI（SPEC M8 / PLAN M8）**已实现**，但它跑的是**作者自测**会话：确认者是终端用户本人，不是招募来的被试；`--session`/`--batch` 产出的日志是 SIM 数据，不得当作被试数据汇报。
- **Web 界面（SPEC M9 / PLAN M9）已实现**：`python -m govern.run --session … --task … --port 8000` 启动本地服务器（只绑 `127.0.0.1`），页面分左右两栏，复选框从不预勾选，未勾满时生成被 409 拒绝且拒绝本身进日志，C0 走无门路径。三张 storyboard 帧是**真实服务器响应**的无头浏览器照片（`tools/make_storyboard.py`），不是绘制稿；但交互后的 JS 行为没有浏览器自动化测试覆盖——`tests/test_web.py` 测的是 HTTP 契约与页面源码。
- **UI 里的会话仍是作者自测**：`runs/` 不入库，页面里没有任何人类被试数据；帧中的左栏为空，因为请求正文按 Q7 不落盘，重绘不出当时的输入。
- M7 验收 7 的**后半句**（重算 `analysis/` 时报告哪些结论依赖已删除数据）未实现：`analysis/`（SPEC M10）按 Q8 是 **N/A**，本期没有重算脚本，因此 `purge` 只交付"删除清单"这一半。
- 六个种子仓库是**自建语料**（Q4 拍板的结果），不是真实开源仓库的历史；它们只用于让"影响分析 recall / precision"可判分。
- **溯源台账（SPEC M11 / PLAN M10）已实现并通过校验**，但要如实说明它**证明的边界**：校验器证明的是"形式合规"——每个模块有行、三种来源都出现、assisted 行有 decision 与 check、reused 路径真实存在。它**不能**证明某句 `check` 里写的测试确实覆盖了那件事，也不能证明 `decision` 是当时的真实想法。前者靠 `docs/rubric-mapping.md` 的测试名逐条对应，后者只能靠提交历史与这份文件本身的可读性。
  - 因此台账里的 `check` 列一律写成**可复跑的命令或具名测试**，不写"已审阅"这类无法验证的措辞；`original` 也不用来夸功——它只在"这是作者的裁定/红线"时使用。
  - `P-019`、`P-020` 两行的 `commit` 列由紧随其后的一次文档提交补齐（台账无法在自己的提交里引用自己的 hash）。
- **全链路冻结（M11）已完成，但"完成"指六条可跑的定义**（`docs/PLAN.md:13-20`），不含"有人类数据"：`--batch` 的六个 slot 全部 `tests_pass=False`，因为随附的模拟建议**故意**漏掉 gold patch 的最后一个文件段（`test_every_shipped_suggestion_omits_at_least_one_consumer`）。这条命令证明管线能跑通并如实判负，**不是**处理效应；不要把它写成"治理组提升了 X%"。
- `analysis/` 的**统计与绘图现已实现**（§2l）：描述统计、效应量、t 区间、配对 t / Wilcoxon / 混合模型的实现与前提检查、Holm/BH 校正、缺失/异常/多重比较三项检查、`results.xlsx` 与四张 PNG 全部可一条命令重建。仍未做的是**"删数据后报告哪些结论失效"**（`purge` 的后半句）——所以 `purge` 只交付"删除清单"这一半。
  - 同时如实说明：`analysis/` 跑出来的**不是实验结论**。操作者是脚本、两个条件收到同一份重放建议，七个结局指标每对差值恒为 0，t/Wilcoxon 因此返回 `n/a`；唯一有方差的 `elapsed_ms` 在两次运行里给出**不同**结果（原 `runs/`：差 −2.33 ms、p=0.058、0 个存活；导出树重跑：差 −5.00 ms、p=0.035、1 个存活）。这个差异本身就是"墙钟时间不可复现"的证据，因此该指标**不得**当作发现汇报。`analysis/` 证明的是"指标能从日志算出来、算错会被测试抓住"。
- **合规自查（§2m）**：`docs/compliance-check.md` 逐条把评分说明对到证据，结论是"工程交付物完整、被评的报告本体尚未存在"（四项里三项 部分满足、Development evidence 满足）；同一文件列出本次检查中修掉的 5 个问题与 7 条补做建议，并单列第 8 节写"没有验证的 5 项"。
