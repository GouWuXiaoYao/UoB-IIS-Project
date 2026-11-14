# 开发溯源台账（SPEC M11）

本文件是**数据**，不是叙述：每行一条可核查的记录，`python -m govern.provenance --check` 逐行校验。
规则（见 `docs/SPEC.md` M11）：

- `module` 必须是 M1–M11 之一，且每个模块至少一行；
- `origin` 只能取 `original` / `reused` / `assisted`，三者都要出现——全填 original 视为没真的区分；
- `assisted` 行必须同时有 `decision`（为什么留下它）与 `check`（怎么验证的）；
- `reused` 行的 `source` 必须指向工作区内真实存在的路径。

**两个如实声明**：

1. 本项目的代码草稿大量由 AI 编程助手生成，因此 `assisted` 行占比最高，这不是谦虚也不是免责——A2 要求区分三种来源，这里就是区分本身。
2. `original` 行记录的是**作者本人的裁定与规则**（Q1–Q8 的范围决策、产品红线），`reused` 行记录取自 `参考代码库/` 的结构；`assisted` 行记录 AI 起草后经作者审阅改动的部分。

| item_id | module | origin | source | decision | check | commit |
|---|---|---|---|---|---|---|
| P-001 | M1 | original | - | 六个种子仓库自建，不使用真实开源仓库（Q4 裁定）：真实仓库给不出 gold patch、隐藏测试、影响集标签三件齐备的对照，无法判分 | `python -m govern.corpus --check` 输出 `ok: 6 tasks, gold 6/6, pairs 3/3 within 20%` | f93cac4 |
| P-002 | M1 | reused | external:参考代码库/mock_model.py | 借用其 `--selftest` 约定：每个模块一条自检命令，输出 `ok: ...` 并返回 0 | 六个模块的 `--selftest` 均可直接运行并返回 0 | b10face |
| P-003 | M1 | assisted | - | 语料工厂草稿由 AI 生成；审阅时发现 `.format()` 会把老代码里的 `{}` 当占位符，改为 `__TOKEN__` 占位符 + `_fill()` | `python tools/make_repo.py --selftest` → `ok: 61 corpus files match the factory`；`tests/test_corpus.py::test_the_factory_is_byte_stable` | f93cac4 |
| P-004 | M2 | original | - | 每人每任务只出现一次、同一 PAIR 跨被试覆盖两种条件、AB/BA 顺序平衡——这是 Q2（N=10 便利样本）留下的唯一可执行部分 | `govern.session --selftest` → `C0=300 C1=300 chi2 p=1.000`；`tests/test_session.py::test_every_pair_appears_in_both_conditions` | 0073b7c |
| P-005 | M2 | assisted | - | 分配与模拟代码由 AI 起草；审阅发现 `Session.state()` 的相位来自内存而 `rebuild_state()` 来自日志，`card_shown` 之后立刻不一致，改为相位单一来源 | `tests/test_session.py::test_state_matches_rebuild_after_every_step`（SPEC M2 验收 4） | 0073b7c |
| P-006 | M3 | original | - | 交付默认 `replay`（无网络、无密钥），`live` 只作可选路径；这是 Q3 的落地方式，也是"一条命令复现"的前提 | `tests/test_llm.py::test_default_mode_is_replay_without_network` | 2f4ac7c |
| P-007 | M3 | assisted | - | replay 客户端由 AI 起草；审阅补了一条 AI 没写的校验：录制里的 `model_id` 必须与 `config` 一致，否则换模型也能"复现" | `tests/test_llm.py::test_a_recording_from_another_model_is_refused` | 2f4ac7c |
| P-008 | M4 | assisted | - | 影响分析器由 AI 起草；审阅把"跨模块契约"的操作化定义写进 docstring（同一顶层值被 ≥2 个模块读取），再据此调类别判定 | `govern.impact --selftest` → `recall=1.00 precision=1.00 on 6 tasks` | 6d12b52 |
| P-009 | M5 | original | - | 评估卡永不预勾选：预勾选等于把 A1 §4 说的 mechanical checking 做进界面，治理就失效了 | `tests/test_card.py::test_html_never_renders_a_pre_ticked_checkbox` | 73a9610 |
| P-010 | M5 | reused | external:参考代码库/index.html | 左右两栏骨架与 `say()` 追加气泡的写法取自该文件，只加复选框、确认按钮与未勾满拦截 | `storyboards/1-c1-gate-closed.png` 等三帧 | 8662f36 |
| P-011 | M6 | assisted | - | 门控对象由 AI 起草；审阅发现"勾选变化后旧令牌仍有效"的绕过路径，改为任何勾选变化即失效 | `tests/test_gate.py::test_a_token_dies_when_a_box_changes` | 73a9610 |
| P-012 | M6 | original | - | 未开门就请求生成时，必须照样落一条 `gate_decision(blocked=true)`：否则"有多少次试图绕过门"在数据上无解 | `tests/test_web.py::test_a_refused_generation_is_still_logged` | 8662f36 |
| P-013 | M7 | original | - | 日志只存正文的 hash 与长度，不落盘原文，保留 90 天（Q7 裁定） | `govern.log --scan`；`tests/test_log.py::test_the_validator_rejects_body_fields` | c66361f |
| P-014 | M7 | assisted | - | 日志器草稿由 AI 生成；审阅改了撕尾行后的 seq 复用与 `purge` 无条件清理 `.jsonl.tmp`——这两处决定了崩溃后能否续跑 | `tests/test_log.py::test_a_torn_tail_does_not_break_the_next_sequence` | c66361f |
| P-015 | M8 | assisted | - | 六类规则检测器由 AI 起草；审阅时发现隐藏测试套件依赖 pytest，违反"一条命令跑测试"，改为标准库子进程运行器 `govern/hidden.py` | `python -m unittest discover -s tests -q` 全绿；`tests/test_hidden.py` | 090e5a0 |
| P-016 | M8 | original | - | 规则阈值、权重、严重度全部写进 `config/rules.json`，代码里不留数字（零魔法数字） | `tests/test_score.py::test_every_rule_declares_its_thresholds` | 090e5a0 |
| P-017 | M9 | assisted | - | 页面由 AI 起草；第一版把拦截提示渲染成条目 ID（`T-L01a-side_effect-003`），审阅后改为陈述文本，否则用户只能机械勾选 | 逐张读图核对三帧；`tests/test_web.py` | 8662f36 |
| P-018 | M9 | reused | external:参考代码库/tools.py | 借用其"校验 → 要求确认 → 再执行 → 写 jsonl"的边界，对应本项目的影响卡 → 门控 → 生成 → 日志 | `storyboards/README.md` 的日志序列 | 8662f36 |
| P-019 | M10 | assisted | - | 校验器与本文档的第一版由 AI 生成；审阅后改了两处：行内格数不符必须报错（否则 assisted 行丢字段无人发现）、`reused` 的 `source` 必须真实存在 | `govern.provenance --selftest`；`tests/test_provenance.py` 全绿 | bcf9e31 |
| P-020 | M11 | original | - | 台账字段（item_id/module/origin/source/decision/check/commit）是为了让 A2 的 "distinguishes original, reused and assisted work" 可被机器检查，A2 本身未规定字段名 | `python -m govern.provenance --check` → `ok:` | bcf9e31 |
| P-021 | M8 | assisted | - | `experiments/` 编排层由 AI 起草；审阅时改了三处：条件文件只描述结构、参数一律留在 `config/`（否则同一阈值有两处定义）、失败必须写 `failures.jsonl` 而不是只打印（否则"单条失败不中断"会变成静默丢数据）；YAML 支持收窄为"子集之外一律报错"而不是猜 | `python -m experiments.run --config conditions.yaml --dry-run`；`tests/test_experiments.py` 全绿 | f31ce4d |
| P-022 | M10 | assisted | - | `analysis/` 统计层由 AI 起草；审阅时改了四处：`paired_t` 在零方差时返回"未定义"而不是 0/0 的伪统计量、`wilcoxon` 必须印出前提与"n<6 时精确 p 不可能低于 0.05"、`gate_latency_ms`/`blocked_attempts` 因 baseline 恒为 0 而从多重比较家族排除并标 `structural zero in baseline`、混合模型在单参与者时直接说明"共线"而不硬拟合 | `python -m analysis.run --runs runs --run-id E-SIM-01 --out analysis`；`tests/test_analysis.py` 全绿（32 条，含已知答案与 2^n 枚举核对） | 432688c |
| P-023 | M10 | original | - | README 的字数自称必须可机器核对：手写的 "210 words" 是手算错值（实测近四倍），规则改为明文并加 `--check`，与 `tests/test_end_to_end.py` 绑定；台账这里刻意不抄具体数字，否则它自己会过期 | `python tools/word_count.py --check` → `ok: README.md states N prose words and has N` | 432688c |
| P-024 | M10 | assisted | - | `docs/compliance-check.md` 由 AI 起草；审阅时改了三处：把"没有人类被试"从"伦理不适用"改成"机制已实现、文书缺失（部分满足）"而不是给满分；补上"重跑实验后统计输出会变"这一条可复现性反例；把无法验证的五项单列第 8 节，不混进判定 | `python -m govern.provenance --check`；文档第 6 节列出的五条修复各自的测试 | b8f1ea2 |
| P-025 | M10 | original | - | 报告本体不进代码路径，但必须可核词数、可重建：`tools/make_report.py` 用标准库写 docx（不引入 python-docx，与 AGENTS 1 的零运行时依赖一致），`tools/word_count.py` 新增 `--docx` 模式按样式分类计数并核对首页所写数字；三个上限 300/1100/1400 取自 SPEC | `python tools/word_count.py --docx=docs/A2_Report_3138100.docx --check` → `ok: the stated counts match the text and are within the limits` | 9073f15 |
| P-026 | M10 | assisted | - | 报告正文由 AI 起草；审阅时改了四处：删掉会随提交数过期的自指数字（原先写"twenty-five commits"）、把候选概念 1（从不预勾选）如实降级为"依据是测量设计而非课程概念"、把墙钟指标写成 p 从 0.058 漂到 0.035 的不稳定量而不是发现、表 1 的 Status 列逐行标 implemented/simulated/planned | `python tools/word_count.py --docx=docs/A2_Report_3138100.docx --check`；`docs/course-concept-evidence.md` §1 的 12 行页码核对 | c181a6b |
| P-027 | M10 | assisted | - | 系统图由 AI 起草；审阅时改了三处：第一版把 `CLIENT.GENERATE` 整框标成 simulated（它其实是已实现代码、只是输出被回放），改为实线框 + `MODE=REPLAY` 注明，避免"把 implemented 标错"；边 17（analysis→gate）语义不成立，删除；`--check` 改为逐个核对图上每个框在源码里的符号是否还存在，图不能比代码活得久 | `python tools/make_diagram.py --check` → `ok: 13 stages match the source`；`tests/test_diagram.py`（6 条，含重建字节一致） | a26bab7 |
| P-028 | M9 | assisted | - | 第 4 帧（拒绝建议）由 AI 起草；审阅时改了三处：① 第一版只截图不给证据，无法证明"拒绝后工作树没变"，改为在截图前对工作副本逐文件哈希、并把前后摘要与日志事件写进 `4-c1-reject.promises.txt`；② 页面在 `?playback=1` 下看不到被拒的那条建议（只显示卡），改为 `card_view` 暴露待处理建议 + `showSuggestion()` 共用渲染，否则"用户动作/系统响应"只剩一句话；③ 新增的测试最初只比文件名（沿用旧 `test_rejecting_leaves_the_worktree_alone` 的弱断言），改为逐字节哈希 + 日志计数 | `python tools\make_storyboard.py --check` → `ok: 4 storyboard frame(s) …, refusal evidenced in 4-c1-reject.promises.txt`；`tests/test_storyboard.py`（5 条）；`tests/test_web.py::RejectPathTests`（4 条） | 71e3267 |
| P-029 | M5 | assisted | - | `device` 由自由文本改为受控枚举由 AI 起草；审阅时改了三处：① 枚举值放在 `config/config.json`（`device_kinds` + `device`）而不是写进 `log.py`，否则 AGENTS §2.4 的"零魔法数字"立刻被违反；② 发现 `validate()` 对 `session_start` 提前返回，导致该事件的字段从未被校验——`device` 恰在这个事件上，不删这个提前返回就等于改了枚举也没生效；③ 词表项限制为 `^[a-z0-9]+(?:-[a-z0-9]+)*$` 的 slug，从形状上排除主机名/用户名/公司名，而不只是靠"约定不要填" | `pytest tests/test_log.py tests/test_smoke.py`；`log.validate()` 拒绝 `DESKTOP-3F2A9C`、`alice-laptop`、`acme corp laptop`、`AUTHOR-WORKSTATION`、`""` | 13aae2f |
| P-030 | M11 | assisted | - | `tools/reproduce.ps1`（一条命令复现）由 AI 起草；审阅时改了四处：① 第一版 `Join-Path $RunRoot $RunId "logs"` 传了三个位置参数，PS 5.1 报 `PositionalParameterNotFound` 却不中断，等于成功标志可能是假的——改成嵌套 `Join-Path`，并把每步的 `$LASTEXITCODE` 作为唯一判据；② `Save-Summary` 用 `Set-Content -Encoding UTF8` 在 PS 5.1 下写 BOM，`reproduce.json` 于是不是合法 JSON，改用 .NET 无 BOM 写出；③ 每步没有固定工作目录，`conditions.yaml` 与 `config.DEFAULT_PATH` 这类相对路径会随调用者的 cwd 漂移，改成 `Push-Location $Root` 并把 `DEFAULT_PATH` 变绝对路径；④ 失败注入一开始选"删 corpus/index.json"，实测不触发失败（`--selftest` 不读它），换成破坏 `config/config.json` 才真正验证到"第 N 步失败即停" | `powershell -NoProfile -ExecutionPolicy Bypass -File tools\reproduce.ps1` → `ok: 6 of 6 steps passed`（干净导出树）；破坏配置 → `FAILED at step 1 … exit 1`；重复 `-OutDir` 与 `-OutDir runs\x` 均 `refused … exit 2`；`python tools\word_count.py --check` → `ok: README.md states 1122 prose words` | 7fa6702 |
| P-031 | M1 | assisted | - | `requirements-dev.txt` 的哈希固定由 AI 起草；审阅时改了四处：① 只钉 pytest 是假的安全——`pytest 9.2.0` 还要求 iniconfig/packaging/pluggy/pygments（以及 win32 的 colorama、<3.11 的 exceptiongroup/tomli/typing-extensions），漏一个 `--require-hashes` 就整文件不可用，故九个全钉并按 pytest 自己的环境标记区分；② 只列 wheel 的哈希不够：没有匹配 wheel 的机器会去下 sdist，所以两种产物都列；③ 注释初稿写了字面的协议头加索引地址，触发本仓库自己的"无端点"扫描——改的是措辞（不写协议头），不是给文件开豁免，否则等于为方便削弱一条真规则；④ 没有把任何运行时包写进这个文件，并新增测试断言"被钉住的包名与 `govern/analysis/experiments/tools` 的导入集不相交" | 已做：9 个发布、81 个文件（wheel 与 sdist）逐个下载并与索引公布的摘要比对，81/81 相等、无 yanked；本机 `.venv` 中 512 个已安装文件与这些 wheel 逐字节相同；`python -m pip install --dry-run --no-index --require-hashes -r requirements-dev.txt` 通过解析与钉住检查（仅因 `--no-index` 无包可装）。可复跑：`pip download --require-hashes -r requirements-dev.txt -d tmp-downloads`；`pytest tests/test_dependencies.py` 13 条 | 待填 |


