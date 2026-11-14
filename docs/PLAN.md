# A2 治理原型实现方案

> 状态：**2026-11-14 已批准**。依据 [docs/SPEC.md](SPEC.md)。实施顺序见 §9，每步独立验收。
> 本期交付 MUST：M1/M3/M4/M5/M6/M7/M8/M11；M2 为 SIM；M9 为 PLAN；M10 为 N/A。

## 1. 目标与完成定义

把 [docs/SPEC.md](SPEC.md) 的 MUST 模块落成可运行、可验收的代码：作者自测可走完"需求 → 评估卡 → 勾选 → 门控 → 生成 → 审阅 → 日志"，并能用同一份录制数据以 C0 直通 / C1 门控两种路径回放。

**完成定义**（对应 SPEC 3.11 六条）：

| # | 完成条件 | 验收命令 |
|---|---|---|
| 1 | 一条命令跑测试 | `python -m unittest discover -s tests -q` |
| 2 | 一条命令自检 | `python -m govern.run --dry-run` → `ok: 6 tasks, 6 cards` |
| 3 | 一条命令复现 | clone → `python -m govern.run --batch --schedule config/schedule.json` → 结果表 |
| 4 | 零魔法数字 | 阈值全部在 `config/config.json`，测试扫描常量 |
| 5 | 无密钥无端点 | `python tools/scan_secrets.py` 零命中 |
| 6 | 溯源可校验 | `python -m govern.provenance --check` |

**不做**（PLAN）：M9 分析管线与 H1–H7 统计。**不实现**（N/A）：M10 参与者管理。不采集任何人类数据。

## 2. 实测环境约束（这些事实决定了下面的选型）

| 事实 | 探测方式 | 对方案的影响 |
|---|---|---|
| Python **3.15.0** | `python --version` | 只用标准库，避免第三方包对新版本兼容滞后 |
| **pytest 未安装** | `python -m pytest --version` → `No module named pytest` | 运行时仍只用标准库 `unittest`；测试期另装 pytest 9.2.0 到 `.venv/`（沙箱内 pip 不可用，用 wheel 手工解包），两种 runner 都能跑 |
| **git 未安装/不在 PATH** | `git --version` → 命令不存在 | **2026-11-14 已解决**：MinGit 2.56.1 便携版解压到 `_tools/git`（不入库），命令前前插 PATH 即得真实 commit；`SHA256SUMS` 快照保留为第二证据（见风险 R7） |
| `pandas`/`statsmodels`/`jsonschema` **均无**，`scipy` 有 | `importlib.util.find_spec` | M9 反正属 PLAN；schema 校验自己写，不引 `jsonschema` |
| 工作区只有 `docs/`、`参考代码库/`、两个 docx | `Get-ChildItem` | 从零建 `govern/`、`corpus/`、`tests/`；无历史包袱 |

## 3. 目录结构

```
AGENTS.md                    项目宪法（SPEC 3.11 六条 + 工作流约定）
README.md                    六项内容：status / stack / 运行 / 开发记录 / AI 使用 / 其他文件
config/
  config.json                模型名、温度、seed、τ_review、800ms、配对容差、样本量
  rules.json                 六类静态规则 + severity + weight
  schedule.json              随机化 schedule（生成后冻结）
corpus/
  index.json                 6 条任务定义
  T-L01a/{repo/,gold.patch,tests_hidden/,intent.md,impact_labels.json}
  T-L01b/ T-L02a/ T-L02b/ T-L03a/ T-L03b/   （同上，3 层 × 2）
recordings/
  <model_id>/<request_sha256>.json          M3 回放缓存
runs/<run_id>/
  logs/<participant_id>/<session_id>.jsonl  M7 唯一数据源
  state/<session_id>.json                   M2 断点
govern/                     全部源码（平铺包，`python -m govern.run` 直接可用）
  config.py tasks.py corpus.py impact.py card.py gate.py
  llm.py log.py score.py session.py web.py provenance.py run.py
tools/
  make_repo.py              语料模板生成器（参数化植入坏味道）
  scan_secrets.py           sk-/endpoint/token 扫描
tests/                      unittest，按模块一文件
docs/  SPEC.md PLAN.md PROVENANCE.md rubric-mapping.md
参考代码库/                  只读参考，不改动
```

## 4. 模块边界与接口

每个模块单一职责，只通过下面这些签名互相调用；跨模块不得访问对方私有属性。

**`govern/config.py`**
```python
@dataclass(frozen=True)
class Config: model_id: str; temperature: float; seed: int
              tau_review_ms: int; mech_dwell_ms: int
              pair_tolerance: float; app_version: str
def load(path="config/config.json") -> Config
```
唯一允许出现阈值字面量的地方；`app_version` 取自 `app_version.txt`（无 git 时由构建脚本写入）。

**`govern/tasks.py`**
```python
@dataclass(frozen=True)
class Task: task_id; pair_id; stratum; repo: Path; intent: str
            hidden_tests: Path; gold_patch: Path; labels: dict
def load_index(root="corpus") -> list[Task]
def by_id(tasks, task_id) -> Task
```

**`govern/corpus.py`** — M1 验收器
```python
@dataclass
class Check: task_id; gold_green: bool; labels_ok: bool; leak_free: bool; baseline_fail_reason: str
def check_task(task) -> Check     # 应用 gold 后跑隐藏测试
def check_all(root="corpus") -> list[Check]
```

**`govern/impact.py`** — M4
```python
@dataclass(frozen=True)
class ImpactItem: item_id; category; symbol; files: tuple; detail: str
@dataclass(frozen=True)
class ImpactSet: items: tuple[ImpactItem, ...]
def analyze(repo: Path, intent: str) -> ImpactSet    # ast 静态分析，无 LLM
def recall_precision(impact: ImpactSet, labels: dict) -> tuple[float, float]
```
`category ∈ {global_var, cross_module_contract, side_effect, test_impact, other}`，与日志枚举一致。

**`govern/card.py`** — M5
```python
@dataclass(frozen=True)
class Card: card_id; version; items; required_ids; n_items; n_required
def build(impact: ImpactSet, task: Task, condition: str) -> Card
def to_html(card: Card) -> str      # 不含 diff（SPEC 2.1 约束）
```

**`govern/gate.py`** — M6
```python
@dataclass(frozen=True)
class GateDecision: blocked: bool; confirmed: bool; n_required: int; n_confirmed: int
class Gate:
    def __init__(self, card: Card)
    def toggle(self, item_id: str) -> tuple[bool, int]   # (checked, dwell_ms)
    def decide(self) -> GateDecision
    def open(self) -> bool
```
C0 用同一接口、恒返回 `blocked=False`（SPEC M6 验收 4）。

**`govern/llm.py`** — M3
```python
@dataclass(frozen=True)
class Suggestion: suggestion_id; patch_diff; rationale_text; touched_symbols; layers
class Client:
    def __init__(self, config: Config, mode: str = "replay",
                 recordings="recordings", api_key_env="A2_API_KEY")
    def generate(self, ctx: "Context") -> Suggestion   # 失败抛 SchemaViolation / AuthMissing
```
`live` 从环境变量取 key 并写 `recordings/<model_id>/<request_sha256>.json`；`replay` 只读该目录，**无网络、无 key**。

**`govern/log.py`** — M7
```python
SCHEMA_VERSION = "1.0.0"
EVENT_FIELDS: dict[str, dict[str, type]]        # SPEC 4.3 的 14 类事件
class Logger:
    def __init__(self, run_dir: Path, session_meta: dict)   # seq 从 1，原子追加
    def emit(self, event_type: str, **fields) -> str        # 返回 event_id
def validate(ev: dict) -> list[str]                       # 返回错误清单，不抛
def purge(run_dir: Path, before: date) -> list[str]       # 返回删除清单
```
拒绝正文字段（`text/content/body/prompt_raw`）由 `validate` 实现；`purge` 后删除 `.jsonl.tmp`。

**`govern/score.py`** — M8
```python
@dataclass(frozen=True)
class Outcome: tests_pass; n_fail; failing_tests; debt_delta; vuln_delta
               lines_added; lines_removed; scorer_version
def baseline(task) -> dict
def evaluate(task, repo_after: Path, base: dict) -> Outcome
def run_hidden_tests(task, repo: Path, timeout_s: int) -> tuple[bool, list[str]]
```

**`govern/session.py`** — M2 编排（状态机）
```python
class Session:
    def __init__(self, run_dir, task: Task, condition: str, participant: str, logger: Logger)
    def submit_prompt(self, text: str) -> Card
    def toggle(self, item_id: str) -> tuple[bool, GateDecision]
    def confirm(self) -> GateDecision                  # 未勾满 -> blocked，且必须落日志
    def generate(self) -> Suggestion                   # 门未开则抛 GateClosed（不可绕过）
    def act(self, suggestion_id, action, dwell_ms, edit_lines=None)
    def end(self, submitted: bool, timeout: bool = False)
    def checkpoint(self, path: Path) / @classmethod resume(cls, path)
```

**`govern/run.py`** — 唯一 CLI 入口
```
python -m govern.run --selftest
python -m govern.run --dry-run [--tasks 6]
python -m govern.run --session S-001 --participant P01 --condition C1 --task T-L01a --port 8000
python -m govern.run --batch --schedule config/schedule.json --run-id R-001
python -m govern.run --resume runs/R-001/state/S-001.json
python -m govern.run --simulate 100        # 虚拟分配均衡性检验
```

**`govern/web.py`** — 复用 `参考代码库/index.html` 的骨架（左对话 / 右卡片，原生 JS，`http.server`），只加"复选框 + 确认按钮 + 未勾满时的拦截提示"。

## 5. 数据流

```
[UI] prompt ──► Session.submit_prompt
                 ├─ impact.analyze(repo, intent)        纯 AST，无模型
                 ├─ card.build(impact, task, condition)
                 ├─ log: prompt_submit
                 └─ log: card_shown {n_items, n_required, impact_set_hash}
[UI] 勾选 ────► Gate.toggle ──► log: card_item_toggle {dwell_ms}
[UI] 确认 ────► Gate.decide
                 ├─ 未勾满 → log: gate_decision{blocked=true} → UI 显示还缺哪几项（生成被拒）
                 └─ 勾满   → log: gate_decision{blocked=false}
[UI] 生成 ────► Client.generate ──► log: generation_request{mode,latency} + suggestion_shown
[UI] 审阅 ────► Session.act ─────► log: suggestion_action{action,review_dwell_ms,accepted_after_gate}
[UI] 提交 ────► score.evaluate ──► log: test_run + task_end + suggestion_scored
[CLI] 收尾 ───► log: session_end
```
C0 走完全相同的路径，只有 `Gate.decide` 恒 `blocked=false`——保证两组日志 schema 与指标定义完全一致（SPEC M6 验收 4）。

## 6. 第三方依赖及理由

**运行时：零第三方依赖。** 只用 `json / ast / hashlib / uuid / datetime / pathlib / subprocess / http.server / unittest`。

理由按重要性排序：
1. `pytest` 在本机未安装，而"一条命令跑测试"必须能离线执行 → 用 `unittest`，装不装都不影响。
2. 评分要求"评审者能在自己机器上跑起来"；零依赖把环境问题降到只剩 Python 本身。
3. Python 3.15 很新，第三方包兼容性不可控；`jsonschema` 的能力用 60 行自写校验替代（且我们必须**拒绝**未知字段，通用库反而不好表达）。

**开发期：也无需安装任何东西。**（若你希望装 pytest/black，属可选项，不进入交付路径。）

**M9 分析管线（PLAN）** 需要 `pandas`/`matplotlib`，本机缺 `pandas`，留到实现 M9 时再定，不阻塞本期。

## 7. 实验运行方式

| 场景 | 命令 | 说明 |
|---|---|---|
| 作者自测单次 | `python -m govern.run --session S-001 --condition C1 --task T-L01a --port 8000` | 起本地 UI，走完整闭环；结束写 `session_end` |
| 录制一份 live 素材 | `set A2_API_KEY=...&& python -m govern.run --session S-000 --condition C1 --task T-L01a --live` | 只在需要新素材时执行；密钥不落盘 |
| 批量（无 UI） | `python -m govern.run --batch --schedule config/schedule.json --run-id R-001` | 按 schedule 顺序跑所有 slot，逐会话落日志；用于 N=10 协议的**空跑验证** |
| 断点续跑 | `python -m govern.run --resume runs/R-001/state/S-001.json` | 读 state + 日志末条 `seq`，跳过已结束任务；`seq` 续接不重号 |
| 分配均衡性 | `python -m govern.run --simulate 100` | 100 次虚拟分配，输出两条件计数与卡方 p；写 `runs/_sim/sim.json` |
| 复现结果表 | `python -m govern.run --batch ... --run-id R-REPRO` | 同 schedule + 同 recordings → 同 `impact_set_hash` 与同事件序列 |
| 清理 | `python -m govern.log --purge --before 2027-02-01` | 输出删除清单，处理 90 天保留期 |

**断点续跑的实现要点**（决定成败）：每个事件写入后，`state/<session>.json` 记录 `{seq, task_index, phase, card_id, confirmed_ids[], gate_open}`；恢复时以日志末条 `seq` 为唯一权威，state 只作快速投影，二者冲突时报错而非猜测。

## 8. 测试策略

| 层次 | 内容 | 在哪 |
|---|---|---|
| 单元 | 每个模块的纯函数（config 解析、impact 分析、规则命中、schema 校验） | `tests/test_<module>.py` |
| 契约 | 14 类事件字段齐全、类型正确、必填无 null | `tests/test_log_schema.py`（表驱动，直接从 SPEC 4.3 抄一份期望表） |
| 负向 | 门不可绕过、未勾满必被拒、非法 JSON 不写半行、正文字段被拒、`purge` 无残留、`sk-` 扫描命中 | 每模块至少 1 条 |
| 确定性 | replay 同输入 10 次 → 建议对象 hash 全等；`impact_set_hash` 与文件遍历顺序无关 | `tests/test_determinism.py` |
| 语料 | 6/6 gold 后隐藏测试全绿；基线必须因"重构未做"失败而非环境问题；同 `pair_id` 三项指标差异 ≤20% | `tests/test_corpus.py` |
| 端到端 | `--dry-run` 全链路不联网不写真实日志；`--batch` 两会话产物结构一致 | `tests/test_e2e.py` |

测试夹具：`tests/fixtures/` 放 2 个微型仓库（一脏一净）给规则与影响分析用，不依赖 `corpus/` 的 6 个真实任务。所有测试**不得**访问网络。

## 9. 里程碑（每步 ≤2h，均可独立验收）

| # | 内容 | 交付物 | 验收命令（必须通过） | 估时 |
|---|---|---|---|---|
| M0 | 骨架与工具链 | `govern/` 空包、`config/config.json`、`AGENTS.md`、`.gitignore`、1 个样本测试 | `python -m govern.run --selftest` → `ok: 0 tasks, 0 cards`；`python -m unittest discover -s tests -q` | 1.5h |
| M1 | 语料工厂（低难度一对） | `tools/make_repo.py` + `T-L01a`/`T-L01b`（含坏味道、gold、隐藏测试、标签）、`index.json` | `python -m govern.corpus --check` → `ok: 2 tasks, gold 2/2, labels 2/2` | 2h |
| M2 | 中/高难度两对 | `T-L02a/b`、`T-L03a/b` | 同上 → `ok: 6 tasks, gold 6/6, pairs 3/3 within 20%` | 1.5h |
| M3 | 影响分析器（M4） | `govern/impact.py` | `python -m govern.impact --selftest` → `recall=1.00 precision>=0.80 on 6 tasks` | 2h |
| M4 | 卡片 + 门（M5、M6） | `govern/card.py`、`govern/gate.py` | `python -m govern.gate --selftest` → 未勾满被拒、勾满解锁、**绕过接口的负向测试必须失败**。**已完成（2026-11-14）**：`ok: 6 cards, blocked until every item is confirmed, C0 passthrough, min dwell 800 ms`；负向测试见 `tests/test_gate.py:131-165` | 2h |
| M5 | 日志器（M7） | `govern/log.py` + schema 表 | `python -m govern.log --selftest` → **16** 类事件校验通过（PLAN 原写"14 类"，以 SPEC 4.3 为准）；正文类字段被拒；`purge` 无残留。**已完成（2026-11-14）**：`ok: 16 event types, seq from 1, atomic append, purge clean`；证据见 `docs/rubric-mapping.md` §2d | 2h |
| M6 | LLM 客户端（M3） | `govern/llm.py`、`recordings/` | `python -m govern.llm --selftest` → replay 10 次 hash 全等、无网络；`scan_secrets` 零命中 | 2h |
| M7 | 评估器（M8） | `govern/score.py`、`config/rules.json` | `python -m govern.score --selftest` → gold 全绿、干净样本 0、六类规则各有正反例 | 2h |
| M8 | 编排 + CLI（M2） | `govern/session.py`、`govern/run.py` | `--simulate 100` 卡方 p>0.05；杀进程后 `--resume` 的 `seq` 连续 | 2h |
| M9 | Web UI 集成 | `govern/web.py`、`static/index.html` | 手工走完 C1 与 C0 两条路径，产出 3 张 storyboard 截图 | 2h |
| M10 | 溯源与文档 | `docs/PROVENANCE.md`、`govern/provenance.py`、README | `python -m govern.provenance --check`；故意删一条 assisted 的 check 字段 → 必须非零退出 | 1h |
| M11 | 端到端冻结 | `--dry-run`、`--batch` 全通；ZIP + `SHA256SUMS` | 六条完成定义逐条跑一遍 | 1h |

合计约 **21h**。M1 的 2h 只做出"模板 + 一对"，因为模板是后面 5 个仓库的成本摊薄点；若模板化失败，M2 会退化为 3×2h（见 R1）。

## 10. 风险与失败模式

| # | 风险 | 触发信号 | 缓解 |
|---|---|---|---|
| R1 | 6 个种子仓库工作量爆炸 | M2 超 3h | 先用 `make_repo.py` 参数化生成（坏味道组合 + 规模），人工只审"是否有真实跨模块契约" |
| R2 | AST 影响分析 recall 达不到 1.0 | M3 达不到目标的 100% | recall 是治理正确性要求（漏报即失守）→ 若达不到，改为"标签集由分析器生成 + 人工复核"并在报告中说明，不允许悄悄降低阈值。**M3 实测 6/6 达到 `recall=1.00 precision=1.00`，未启用该降级**；代价是契约的操作化定义被迫收窄（只认"被 ≥2 个包内模块读取的顶层值"，见 `govern/impact.py` docstring），已记入 `docs/rubric-mapping.md` 第 6 节 |
| R3 | 真实 API 限流/不可用/模型漂移 | M6 录制失败 | `replay` 是交付默认；录制一次性完成后冻结，报告中标明模型快照日期 |
| R4 | 无 pytest → 与工作流文档约定不一致 | M0 | 明确改用 `unittest`，写进 AGENTS.md 并在 README 说明理由；两者可共存（pytest 能发现 unittest 用例） |
| R5 | Python 3.15 与某库不兼容 | 任何 `import` 失败 | 零第三方运行时依赖，把该风险消除 |
| R6 | UI 成为时间黑洞 | M9 超 2h | 直接改 `参考代码库/index.html`（已验证可用的 49 行骨架），不引入框架、不做视觉打磨 |
| R7 | **无 git → 无法给出 commit/release** | M0 | **已处理（2026-11-14）**：winget 与官方安装器在本机沙箱内均失败（winget 退出码 `-1978335231`，Inno 静默安装无落地文件），改用 **MinGit 2.56.1 便携版**，解压在 `_tools/git`（已被 `.gitignore` 排除），仅通过 `$env:PATH` 前插调用；仓库因此有真实 commit。**同时保留 ZIP + `SHA256SUMS` 快照**，两者在 README 中如实并列说明 |
| R8 | 门被绕过（最致命，直接命中红线） | M4 负向测试失败 | 生成路径只接受 `Gate.open() == True`；接口层无公开旁路；有专门负向测试。**M4 已验证**：门的全部状态私有、构造时校验卡（`required_ids` 与 `n_required` 不符即 `ValueError`）、确认不跨实例继承、令牌一次性且勾选变化即失效；`tests/test_gate.py` 的 `BypassTests` 五条覆盖 |
| R9 | 日志被写成半行/丢事件 | M5 | 单行 `write` + `flush` + `fsync`；中途杀掉进程的测试必须在 M5 通过。**已验证**：`tests/test_log.py:302` 模拟撕裂尾行，重开后截掉残段并复用 seq；实现用 `O_APPEND` 单次 `os.write` + `fsync`，不产生 `.tmp` 中转 |
| R10 | 断点续跑双写 | M8 | 以日志末条 `seq` 为唯一权威，state 与日志冲突即报错停止 |
| R11 | 计划分析被误写成实测 | 写报告时 | SPEC 5 节横幅 + 8.1b 自查表；报告中禁用 "experiment shows" |

## 11. 需你确认的残留项（不阻塞开工）

1. **Git**：**已定（2026-11-14）**——系统安装被沙箱挡住，改用 MinGit 便携版（`_tools/git`，不入库）提供真实 commit；同时保留 `SHA256SUMS` 快照作为第二证据，README 里两种标识并列写明。
2. **UI 形态**：默认本地网页（`http.server` + 原生 JS，改参考骨架）。若你更想要纯 CLI，M9 可省 1.5h，但 storyboard 出图会更难。

## 12. 批准后的第一步

1. 把本方案原样写入 `docs/PLAN.md`（含里程碑与验收命令）。
2. 执行 **M0**：建目录、写 `config/config.json` 与 `AGENTS.md`、让 `--selftest` 与 `unittest discover` 两条命令先跑通。
3. 之后按 M1→M11 顺序推进，每个里程碑结束时跑该行验收命令并把结果贴给你，**不一次做完再汇报**。
