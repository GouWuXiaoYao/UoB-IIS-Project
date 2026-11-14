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
| **Design reasoning and scope** | SPEC 1–2 章（RQ / 假设 / 设计）+ 每次范围收缩的记录 | `docs/SPEC.md` 6.0 决议表（Q1–Q8 八条拍板）；`docs/SPEC.md` 3.0 交付集表（MUST / SIM / PLAN / N/A 四态）；`docs/PLAN.md` 里程碑 M0–M11 | M0–M2 已落地，其余按里程碑推进 |
| **Developed interaction** | SPEC 第 3 章模块清单；M4 评估卡、M5 渲染、M6 门控 | `govern/corpus.py:126` `check_task()` 产出的可运行仓库，是"用户任务"的输入侧；卡与门已落地：`govern/card.py:65` `build()`、`:108` `to_html()`、`govern/gate.py:57` `toggle()`、`:72` `decide()`；日志器 `govern/log.py:320` `Logger` 已能写 16 类事件 | 卡、门、日志、LLM 客户端、评估器均已落地；**界面（M9）与会话控制器（M8）未做**，故交互链路目前只能在单测与 `--selftest` 里演示 |
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

## 3. 模块级证据

| 模块 | 状态 | 关键入口 | 自检 / 测试 |
|---|---|---|---|
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
```

> 说明：`.venv/` 只是本机开发工具链（pytest 属**测试期**依赖，不进入运行时）；
> 交付代码在 `govern/` 与 `tools/` 内，只用标准库。隐藏测试套件自 M7 起由
> `govern/hidden.py` 用标准库在子解释器里跑（不再需要 pytest），所以
> `python -m govern.corpus --check` 与 `python -m govern.score --selftest`
> 在裸 Python 3.11+ 上同样可用；`python -m unittest discover -s tests -q` 也已实测可用（202 条）。

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
| 新增 `tools/make_recordings.py` 与 `recordings/`（M6） | 本机没有任何 API 凭据，若等真实调用就永远没有可复现的 replay；SPEC M3 验收 2 要求"录制完整可复现" | 录制由工厂从 gold patch 派生并标 `source: "sim"`，可逐字节重建（`--selftest` 校验）；这是**模拟**建议，不是模型输出，报告里如实说明 |
| `Client.__init__` 增加可选 `logger`（M6） | `generation_request` / `integrity_event` 必须有地方写；PLAN 的构造签名没有日志参数 | 关键字参数默认 `None`（不写日志），`Client(config, mode, recordings, api_key_env)` 调用方式不变 |
| 端点从 `A2_API_BASE` 读取（M6） | PLAN 只规定密钥从环境变量取，没说端点从哪来；写进 config 就违反了"无端点入库" | 与 `A2_API_KEY` 同一策略：只有环境变量，`EndpointMissing` 有单独错误码与测试 |
| 新增 `govern/hidden.py`（M7） | 隐藏套件原来由 `govern/corpus.py` 用 `python -m pytest` 跑（需要 `.venv`）。AGENTS §1.1 要求"零第三方运行时依赖"，且硬规则 1 的验收命令是裸 `python -m unittest discover`——实测在裸 Python 上 `corpus --check` 直接失败（`No module named pytest`） | 抽出标准库子解释器运行器，`corpus` 与 `score` 共用；pytest 回归为**仅测试期**工具。副作用：`corpus --check` 的 `baseline=` 原因文本变长为 `test_x.py::test_y: AssertionError: …`（更精确，汇总行不变） |
| `corpus._run_hidden()` 改为调用 `hidden.run()`（M7） | 同上；另外 pytest 的退出码含义与"套件挂死/读不出报告"混在一起，超时也无法区分 | 返回码语义变成 `0 通过 / 1 有失败 / 2 未完成`；`_failure_reason()` 未改动，仍能从失败清单里取第一行 |
| `debt_delta` 以 float 写入（M7） | SPEC 4.3 的 `task_end.debt_delta` 是 float，`log.validate()` 按 float 校验；整数加权计数之差在 schema 上会被判类型错 | `Outcome.debt_delta: float`，`evaluate()` 里显式 `float(...)`；`vuln_delta` 仍是 int |

---

## 6. 明确没有做的（避免把 planned 说成 implemented）

- 没有采集任何人类被试数据；`M2` 是 **SIM**，`M10` 是 **N/A**（SPEC 3.0）。
- **没有真正调用过任何外部模型 API**：`govern/llm.py` 的 `live` 路径只在测试里的回环 stub 上验证过（`tests/test_llm.py:68` 的 `_Stub`），`recordings/` 里 6 条录制全部是 `source: "sim"` 的作者模拟。报告与 README 一律按"模拟建议"表述，不得写成"模型输出"。
- 影响分析器（SPEC M4 / PLAN M3）**已实现**，但它只做静态分析：不做语义推断、不读 diff、不调模型。
  它能识别的"契约"是"被 ≥ 2 个包内模块读取的顶层值"这一操作化定义（见 `govern/impact.py` docstring），
  因此它**不会**发现"两个模块各自实现同一算法"这类纯语义重复。
- 评估卡与门控（SPEC M5/M6 / PLAN M4）**已实现**，但还**没有接线到一次真正的会话**：现在只能通过 `python -m govern.card` 渲染、通过 `python -m govern.gate --selftest` 复演不变量。
- 遥测日志器（SPEC M7 / PLAN M5）**已实现**，但**还没有任何真实会话给它写事件**：`runs/` 下的日志目前只由测试与 `--selftest` 产生。
- LLM 客户端（SPEC M3 / PLAN M6）**已实现**，但只交付 `replay` 模式：`live` 需要 `A2_API_BASE` + `A2_API_KEY`，本机没有，故从未对真实服务发起过请求。
- 结果评估器（SPEC M8 / PLAN M7）**已实现**，但**没有跑过任何一次会话**：`baseline()`/`evaluate()` 只在 6 个种子仓库与测试里的构造样本上验证过，`debt_delta`/`vuln_delta`/`lines_added` 还没有一条来自真实会话的数据。
  - 已实测的覆盖缺口：六类规则**测不到**轻层语料的坏味道（浮点金额、模块级缓存、语义重复的税额推导），L 层 `debt=0`，M=3，H=8（加权）。因此"债务下降"只在 M/H 层可测；L 层靠隐藏测试与行数指标。这一条不得在报告里含糊成"每层都能测出债务下降"。
- 端到端指标重算（SPEC M10 `analysis/`）是 **N/A**（SPEC 3.0 交付集），所以"由日志重算全部指标"这条链路**没有实现**；`govern.log --purge` 之后无法重算依赖已删数据的结论，这一点在 SPEC M7 验收 7 里已如实降级记录。
- 会话控制器与 Web 界面（SPEC M8/M9，PLAN 的 M8/M9）尚未实现，所以"用户动作 → 系统响应"的交互链路、以及由真实会话日志重算的指标，目前**都不可演示**，不得声称可演示。
- M7 验收 7 的**后半句**（重算 `analysis/` 时报告哪些结论依赖已删除数据）未实现：`analysis/`（SPEC M10）按 Q8 是 **N/A**，本期没有重算脚本，因此 `purge` 只交付"删除清单"这一半。
- 六个种子仓库是**自建语料**（Q4 拍板的结果），不是真实开源仓库的历史；它们只用于让"影响分析 recall / precision"可判分。
