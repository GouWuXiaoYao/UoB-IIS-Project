# A2 governance prototype implementation plan

> Status: **approved 2026-11-14**. Follows [docs/SPEC.md](SPEC.md). The implementation order is in §9; every step is accepted independently.
> This round's delivery (by **SPEC module number**): MUST = M1/M3/M4/M5/M6/M7/M8/M11; SIM = M2; PLAN = M9 (analysis pipeline); N/A = M10 (participant management).
> M0–M11 in this file are **milestone numbers**, a different set from the SPEC module numbers: milestone M9 = Web UI, already implemented (see that row in §9).

## 1. Goal and definition of done

Turn the MUST modules of [docs/SPEC.md](SPEC.md) into runnable code that passes acceptance: the author can self-test the whole path "requirement → impact card → ticking → gate → generation → review → log", and can replay the same recordings along two paths, C0 direct and C1 gated.

**Definition of done** (the six items in SPEC 3.11):

| # | Completion condition | Acceptance command |
|---|---|---|
| 1 | One command runs the tests | `python -m unittest discover -s tests -q` |
| 2 | One command self-checks | `python -m govern.run --dry-run` → `ok: 6 tasks, 6 cards` |
| 3 | One command reproduces | clone → `python -m govern.run --batch --schedule config/schedule.json` → results table |
| 4 | Zero magic numbers | every threshold lives in `config/config.json`; a test scans for literals |
| 5 | No keys, no endpoints | `python tools/scan_secrets.py` reports zero findings |
| 6 | Provenance can be checked | `python -m govern.provenance --check` |

**Not done** (SPEC M9: analysis pipeline and the H1–H7 statistics; marked PLAN per Q8, so this round has no data-analysis script). **Not implemented** (N/A): the participant-management module of SPEC M10. No human data is collected.

## 2. Measured environment constraints (these facts drive the choices below)

| Fact | How it was probed | Effect on the plan |
|---|---|---|
| Python **3.15.0** | `python --version` | standard library only, so no third-party package lags behind a new release |
| **pytest not installed** | `python -m pytest --version` → `No module named pytest` | the runtime still uses only the standard-library `unittest`; for testing, pytest 9.2.0 is installed separately into `.venv/` (pip does not work in the sandbox, so the wheel is unpacked by hand), and both runners work |
| **git not installed / not on PATH** | `git --version` → command not found | **resolved 2026-11-14**: the portable MinGit 2.56.1 is unpacked to `_tools/git` (not committed), and prepending PATH before the command yields a real commit; the `SHA256SUMS` snapshot is kept as second evidence (see risk R7) |
| `pandas`/`statsmodels`/`jsonschema` **all absent**, `scipy` present | `importlib.util.find_spec` | M9 is PLAN anyway; schema validation is hand-written, `jsonschema` is not pulled in |
| the workspace holds only `docs/`, `参考代码库/` and two docx files | `Get-ChildItem` | `govern/`, `corpus/` and `tests/` are built from scratch; no legacy to carry |

## 3. Directory layout

```
AGENTS.md                    project constitution (the six items in SPEC 3.11 + workflow conventions)
README.md                    six sections: status / stack / how to run / development record / AI use / other files
config/
  config.json                model name, temperature, seed, τ_review, 800ms, pair tolerance, sample size
  rules.json                 six static rule families + severity + weight
  schedule.json              randomised schedule (frozen after generation)
corpus/
  index.json                 6 task definitions
  T-L01a/{repo/,gold.patch,tests_hidden/,intent.md,impact_labels.json}
  T-L01b/ T-L02a/ T-L02b/ T-L03a/ T-L03b/   (as above, 3 strata × 2)
recordings/
  <model_id>/<request_sha256>.json          M3 replay cache
runs/<run_id>/
  logs/<participant_id>/<session_id>.jsonl  M7 single data source
  state/<session_id>.json                   M2 checkpoint
govern/                     all source (flat package, `python -m govern.run` works directly)
  config.py tasks.py corpus.py impact.py card.py gate.py
  llm.py log.py score.py session.py web.py provenance.py run.py
tools/
  make_repo.py              corpus template generator (parameterised smell injection)
  scan_secrets.py           sk-/endpoint/token scan
tests/                      unittest, one file per module
docs/  SPEC.md PLAN.md PROVENANCE.md rubric-mapping.md
参考代码库/                  read-only reference, never modified
```

## 4. Module boundaries and interfaces

Each module has one responsibility and calls the others only through the signatures below; no module may touch another module's private attributes.

**`govern/config.py`**
```python
@dataclass(frozen=True)
class Config: model_id: str; temperature: float; seed: int
              tau_review_ms: int; mech_dwell_ms: int
              pair_tolerance: float; app_version: str
def load(path="config/config.json") -> Config
```
The only place where threshold literals may appear; `app_version` comes from `app_version.txt` (written by the build script when there is no git).

**`govern/tasks.py`**
```python
@dataclass(frozen=True)
class Task: task_id; pair_id; stratum; repo: Path; intent: str
            hidden_tests: Path; gold_patch: Path; labels: dict
def load_index(root="corpus") -> list[Task]
def by_id(tasks, task_id) -> Task
```

**`govern/corpus.py`** — M1 acceptance checker
```python
@dataclass
class Check: task_id; gold_green: bool; labels_ok: bool; leak_free: bool; baseline_fail_reason: str
def check_task(task) -> Check     # run the hidden tests after applying gold
def check_all(root="corpus") -> list[Check]
```

**`govern/impact.py`** — M4
```python
@dataclass(frozen=True)
class ImpactItem: item_id; category; symbol; files: tuple; detail: str
@dataclass(frozen=True)
class ImpactSet: items: tuple[ImpactItem, ...]
def analyze(repo: Path, intent: str) -> ImpactSet    # static ast analysis, no LLM
def recall_precision(impact: ImpactSet, labels: dict) -> tuple[float, float]
```
`category ∈ {global_var, cross_module_contract, side_effect, test_impact, other}`, matching the log enumeration.

**`govern/card.py`** — M5
```python
@dataclass(frozen=True)
class Card: card_id; version; items; required_ids; n_items; n_required
def build(impact: ImpactSet, task: Task, condition: str) -> Card
def to_html(card: Card) -> str      # no diff included (SPEC 2.1 constraint)
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
C0 uses the same interface and always returns `blocked=False` (SPEC M6 acceptance 4).

**`govern/llm.py`** — M3
```python
@dataclass(frozen=True)
class Suggestion: suggestion_id; patch_diff; rationale_text; touched_symbols; layers
class Client:
    def __init__(self, config: Config, mode: str = "replay",
                 recordings="recordings", api_key_env="A2_API_KEY")
    def generate(self, ctx: "Context") -> Suggestion   # raises SchemaViolation / AuthMissing on failure
```
`live` reads the key from the environment variable and writes `recordings/<model_id>/<request_sha256>.json`; `replay` only reads that directory, **no network, no key**.

**`govern/log.py`** — M7
```python
SCHEMA_VERSION = "1.0.0"
EVENT_FIELDS: dict[str, dict[str, type]]        # the 14 event types of SPEC 4.3
class Logger:
    def __init__(self, run_dir: Path, session_meta: dict)   # seq starts at 1, atomic append
    def emit(self, event_type: str, **fields) -> str        # returns the event_id
def validate(ev: dict) -> list[str]                       # returns the list of errors, does not raise
def purge(run_dir: Path, before: date) -> list[str]       # returns the list of deletions
```
Rejecting body fields (`text/content/body/prompt_raw`) is implemented by `validate`; `purge` also deletes leftover `.jsonl.tmp` files.

**`govern/score.py`** — M8
```python
@dataclass(frozen=True)
class Outcome: tests_pass; n_fail; failing_tests; debt_delta; vuln_delta
               lines_added; lines_removed; scorer_version
def baseline(task) -> dict
def evaluate(task, repo_after: Path, base: dict) -> Outcome
def run_hidden_tests(task, repo: Path, timeout_s: int) -> tuple[bool, list[str]]
```

**`govern/session.py`** — M2 orchestration (state machine)
```python
class Session:
    def __init__(self, run_dir, task: Task, condition: str, participant: str, logger: Logger)
    def submit_prompt(self, text: str) -> Card
    def toggle(self, item_id: str) -> tuple[bool, GateDecision]
    def confirm(self) -> GateDecision                  # not fully ticked -> blocked, and this must be logged
    def generate(self) -> Suggestion                   # raises GateClosed when the gate is shut (no bypass)
    def act(self, suggestion_id, action, dwell_ms, edit_lines=None)
    def end(self, submitted: bool, timeout: bool = False)
    def checkpoint(self, path: Path) / @classmethod resume(cls, path)
```

**`govern/run.py`** — the only CLI entry point
```
python -m govern.run --selftest
python -m govern.run --dry-run [--tasks 6]
python -m govern.run --session S-001 --participant P01 --condition C1 --task T-L01a --port 8000
python -m govern.run --batch --schedule config/schedule.json --run-id R-001
python -m govern.run --resume runs/R-001/state/S-001.json
python -m govern.run --simulate 100        # virtual-assignment balance check
```

**`govern/web.py`** — reuses the skeleton of `参考代码库/index.html` (conversation on the left / card on the right, plain JS, `http.server`), adding only "checkboxes + a confirm button + a blocking prompt when items are not all ticked".

## 5. Data flow

```
[UI] prompt ────► Session.submit_prompt
                  ├─ impact.analyze(repo, intent)        pure AST, no model
                  ├─ card.build(impact, task, condition)
                  ├─ log: prompt_submit
                  └─ log: card_shown {n_items, n_required, impact_set_hash}
[UI] tick ──────► Gate.toggle ──► log: card_item_toggle {dwell_ms}
[UI] confirm ───► Gate.decide
                  ├─ not all ticked → log: gate_decision{blocked=true} → the UI shows which items are missing (generation refused)
                  └─ all ticked     → log: gate_decision{blocked=false}
[UI] generate ──► Client.generate ────► log: generation_request{mode,latency} + suggestion_shown
[UI] review ────► Session.act ────────► log: suggestion_action{action,review_dwell_ms,accepted_after_gate}
[UI] submit ────► score.evaluate ─────► log: test_run + task_end + suggestion_scored
[CLI] end ──────► log: session_end
```
C0 walks exactly the same path, except that `Gate.decide` always returns `blocked=false` — which keeps the log schema and the metric definitions identical across the two groups (SPEC M6 acceptance 4).

## 6. Third-party dependencies and the reasoning

**Runtime: zero third-party dependencies.** Only `json / ast / hashlib / uuid / datetime / pathlib / subprocess / http.server / unittest` are used.

Reasons, in order of importance:
1. `pytest` is not installed on this machine, and "one command runs the tests" must work offline → use `unittest`, which works whether pytest is installed or not.
2. The marking asks that "a reviewer can run it on their own machine"; zero dependencies cut environment problems down to Python itself.
3. Python 3.15 is very new and third-party compatibility is unpredictable; the `jsonschema` capability is replaced by 60 lines of hand-written validation (and we must **reject** unknown fields, which general-purpose libraries express poorly).

**Development: nothing needs installing either.** (Installing pytest/black is optional and does not enter the delivery path.)

**The M9 analysis pipeline (PLAN)** needs `pandas`/`matplotlib`; `pandas` is missing here, so it is left until M9 is implemented and does not block this round.

## 7. How to run the experiments

| Scenario | Command | Notes |
|---|---|---|
| Author single self-test | `python -m govern.run --session S-001 --condition C1 --task T-L01a --port 8000` | starts the local UI and walks the full loop; writes `session_end` at the end |
| Record one live sample | `set A2_API_KEY=...&& python -m govern.run --session S-000 --condition C1 --task T-L01a --live` | run only when new material is needed; the key never touches disk |
| Batch (no UI) | `python -m govern.run --batch --schedule config/schedule.json --run-id R-001` | runs every slot in schedule order and logs each session; used for the **dry run** of the N=10 protocol |
| Resume from a checkpoint | `python -m govern.run --resume runs/R-001/state/S-001.json` | reads state + the last `seq` in the log and skips finished tasks; `seq` continues without reuse |
| Assignment balance | `python -m govern.run --simulate 100` | 100 virtual assignments; prints the count per condition and the chi-square p; writes `runs/_sim/sim.json` |
| Reproduce the results table | `python -m govern.run --batch ... --run-id R-REPRO` | same schedule + same recordings → same `impact_set_hash` and the same event sequence |
| Cleanup | `python -m govern.log --purge --before 2027-02-01` | prints the deletion list; applies the 90-day retention period |

**Resume implementation points** (these decide whether it works): after each event is written, `state/<session>.json` records `{seq, task_index, phase, card_id, confirmed_ids[], gate_open}`; on resume the last `seq` in the log is the single authority and state is only a fast projection — a conflict is an error, never a guess.

## 8. Test strategy

| Layer | Content | Where |
|---|---|---|
| Unit | the pure functions of each module (config parsing, impact analysis, rule hits, schema validation) | `tests/test_<module>.py` |
| Contract | all fields of the 14 event types present, correctly typed, required fields never null | `tests/test_log_schema.py` (table-driven, with an expected table copied straight from SPEC 4.3) |
| Negative | the gate cannot be bypassed, incomplete ticking is always rejected, invalid JSON writes no partial line, body fields are rejected, `purge` leaves nothing, `sk-` scanning hits | at least 1 per module |
| Determinism | replay the same input 10 times → identical suggestion hashes; `impact_set_hash` is independent of file traversal order | `tests/test_determinism.py` |
| Corpus | 6/6 hidden tests green after gold; the baseline must fail because "the refactor is not done", not for environment reasons; the three metrics differ by ≤20% within a `pair_id` | `tests/test_corpus.py` |
| End to end | the whole `--dry-run` path uses no network and writes no real log; the two `--batch` session outputs have the same structure | `tests/test_e2e.py` |

Test fixtures: `tests/fixtures/` holds 2 tiny repositories (one dirty, one clean) for the rules and the impact analysis, so they do not depend on the 6 real tasks in `corpus/`. No test **may** touch the network.

## 9. Milestones (each ≤2h, each independently acceptable)

| # | Content | Deliverable | Acceptance command (must pass) | Estimate |
|---|---|---|---|---|
| M0 | Skeleton and toolchain | empty `govern/` package, `config/config.json`, `AGENTS.md`, `.gitignore`, 1 sample test | `python -m govern.run --selftest` → `ok: 0 tasks, 0 cards`; `python -m unittest discover -s tests -q` | 1.5h |
| M1 | Corpus factory (one low-difficulty pair) | `tools/make_repo.py` + `T-L01a`/`T-L01b` (with smells, gold, hidden tests, labels), `index.json` | `python -m govern.corpus --check` → `ok: 2 tasks, gold 2/2, labels 2/2` | 2h |
| M2 | The medium and high difficulty pairs | `T-L02a/b`, `T-L03a/b` | as above → `ok: 6 tasks, gold 6/6, pairs 3/3 within 20%` | 1.5h |
| M3 | Impact analyser (M4) | `govern/impact.py` | `python -m govern.impact --selftest` → `recall=1.00 precision>=0.80 on 6 tasks` | 2h |
| M4 | Card + gate (M5, M6) | `govern/card.py`, `govern/gate.py` | `python -m govern.gate --selftest` → incomplete ticking is rejected, full ticking unlocks, **a negative test that bypasses the interface must fail**. **done (2026-11-14)**: `ok: 6 cards, blocked until every item is confirmed, C0 passthrough, min dwell 800 ms`; the negative tests are in `tests/test_gate.py:131-165` | 2h |
| M5 | Logger (M7) | `govern/log.py` + the schema table | `python -m govern.log --selftest` → **16** event types validate (PLAN originally said "14 types"; SPEC 4.3 governs); body fields are rejected; `purge` leaves nothing. **done (2026-11-14)**: `ok: 16 event types, seq from 1, atomic append, purge clean`; evidence in `docs/rubric-mapping.md` §2d | 2h |
| M6 | LLM client (M3) | `govern/llm.py`, `recordings/`, `tools/scan_secrets.py`, `tools/make_recordings.py` | `python -m govern.llm --selftest` → 10 replays give identical hashes and no network is used; `scan_secrets` reports zero findings. **done (2026-11-14)**: `ok: 6 recordings, 10 replays each, 6/6 identical, no network used`, `ok: 0 finding(s) in 105 files`; the recordings are author simulations (`source: "sim"`), evidence in `docs/rubric-mapping.md` §2e | 2h |
| M7 | Scorer (M8) | `govern/score.py`, `govern/hidden.py`, `config/rules.json` | `python -m govern.score --selftest` → gold all green, the clean sample scores 0, each of the six rule families has a positive and a negative case. **done (2026-11-14)**: `ok: 6 rules (complexity, duplication, bare_except, hardcoded_secret, eval_usage, sql_concat) with positive and negative fixtures, gold 6/6, clean repository 0 debt`; the hidden suite now runs through a standard-library subprocess runner (`ok: hidden suite runner reports pass/fail in a child interpreter`), so `corpus --check` no longer depends on pytest; evidence in `docs/rubric-mapping.md` §2f | 2h |
| M8 | Orchestration + CLI (M2) | `govern/session.py`, `govern/run.py`, `config/schedule.json` | chi-square p>0.05 for `--simulate 100`; after the process is killed, `--resume` keeps `seq` contiguous. **done (2026-11-14)**: `ok: simulated 100 assignments, C0=300 C1=300 chi2 p=1.000 (balanced at alpha=0.05), every pair in both conditions: yes`; `govern.session --selftest` → `ok: 10 participants, 6 slots each, deterministic, C0=300 C1=300 chi2 p=1.000`; resume is asserted line by line on `seq` by `test_checkpoint_then_resume_continues_the_sequence` and `test_resume_finishes_a_checkpointed_session`; evidence in `docs/rubric-mapping.md` §2g | 2h |
| M9 | Web UI integration | `govern/web.py`, `static/index.html`, `tools/make_storyboard.py` | **done**: the manual path is walked by a script instead — a real server plus headless Chrome, `python tools/make_storyboard.py --check` → `ok: 3 storyboard frame(s)`; `python -m govern.web --selftest` → `ok: 6 routes wired, card rendered from session state` | 2h |
| M10 | Provenance and documentation | `docs/PROVENANCE.md`, `govern/provenance.py`, README | `python -m govern.provenance --check`; deleting one `check` field from an assisted row on purpose → must exit non-zero. **done (2026-11-14)**: `ok: 21 rows, 11 modules covered (original=8, reused=3, assisted=10)`; the measured negative case `fail: 1 problem(s) … P-003: assisted work needs a check`, `exit=1`; the README is rewritten to cover the six sections "status / stack / how to run / development record / AI use / additional files" with a word count of 210; evidence in `docs/rubric-mapping.md` §2i | 1h |
| M11 | End-to-end freeze | both `--dry-run` and `--batch` pass; ZIP + `SHA256SUMS` | run all six definition-of-done items one by one. **done (2026-11-14)**: all six pass (`328 tests OK`, `ok: 6 tasks, 6 cards`, `ok: batch P01 ran 6 of 6 slots`, `ok: 0 finding(s) in 220 files`, `ok: 21 rows, 11 modules covered`, and zero magic numbers proved by `tests/test_config_discipline.py`); the frozen archive `dist/a2-1.0.0.zip` (123 files) has `sha256:2f2ea5d269f260d03bd8b942b3cac8ec41383b6266e8824e94b5944b772590c4`, the same hash from two builds. **The final audit (evening of 2026-11-14) re-ran all six on the then-current HEAD and rebuilt the archive**: `Ran 446 tests … OK (skipped=2)`, `ok: 6 tasks, 6 cards`, `ok: batch P01 ran 6 of 6 slots`, `ok: 0 finding(s) in 176 files`, `ok: 31 rows, 11 modules covered (original=10, reused=3, assisted=18)`, `ok: 6 of 6 steps passed` (`tools/reproduce.ps1`); the archive became **161 entries, 696,791 bytes, `sha256:07651cd4ac339adc4a23104abb5541b5591dda4883bf7fffce2464989266b40c` (the tree of commit `d616cd9`)**, `--verify` passes and two builds give the same hash. The M11 row records the numbers at freeze time, the audit line records the numbers at delivery time; the reason for the difference is written in `docs/rubric-mapping.md` §2j. Evidence in `docs/rubric-mapping.md` §2j. After the delivery was rewritten in English the archive of `228e92b` is 161 entries with `sha256:a7a399c0b20c9bab3a8bcd71f9bc9ef1c1892349878ddf2bb707b2dcf3a54767`, rebuilt from that commit | 1h |
| M12 | Experiment orchestration (added after the freeze) | `experiments/spec.py`, `runner.py`, `metrics.py`, `run.py`, `conditions.yaml`, `README.md` | `python -m experiments.run --config conditions.yaml --dry-run` prints the plan and writes nothing; a real run of 12 cells produces one table and writes `runs/E-SIM-01/{config.snapshot.json,manifest.json,logs/,metrics.json}`; `--resume` skips everything. **done (2026-11-14)**: `ok: 2 conditions × 6 tasks × 1 participant(s) × 1 repetition(s) = 12 sessions (concurrency 2)`; measured `escape rate C0=1.00 C1=1.00`, `OTI=0.00`, `C1 mechanical=1.00` (a degenerate metric caused by a scripted operator, noted in `experiments/README.md` and §2k as "not evidence that governance works"); `--resume` → `ok: 0 ran, 12 skipped, 0 failed`; the full test count rises from 328 to **352**; the rebuilt archive is 131 files `sha256:b2fbc3783fa57ab3a58c8d94f9ba49ff1aa0e5478f55c64a0f7a47f11ea31b50` (the 123-file hash of M11 is the `govern/` freeze point, earlier than this layer); evidence in `docs/rubric-mapping.md` §2k | 1.5h |
| M13 | Analysis layer (added after the freeze) | `analysis/{load,checks,stats,report,run,xlsx,png}.py`, `analysis/README.md`, `tools/word_count.py` | `python -m analysis.run --runs runs --run-id E-SIM-01 --out analysis` produces, in one command, `results.xlsx` (7 sheets) + 4 PNG files + `captions.md`; `--selftest` checks the statistics, the workbook and the canvas against known answers. **done (2026-11-14)**: `missing: expected 12, found 12 sessions, 12 ended, 12 with an outcome`, `multiplicity: 1 tests, 0 survive Holm at alpha=0.05`, `ok: 12 session logs, 4 figures`; the only metric entering the family, `elapsed_ms`, differs by −2.33 ms, t(5)=−2.44, p=0.0578 (not significant after Holm); the 7 outcome metrics differ by exactly 0 per pair, and t/Wilcoxon return `n/a` rather than a fabricated small p; `gate_latency_ms`/`blocked_attempts` are marked `structural zero in baseline` and excluded from the family. **One old mistake is corrected here too**: the README's "210 words" was a hand-calculated wrong value (the measurement is nearly four times that), so `tools/word_count.py --check` is added and wired into `tests/test_end_to_end.py` to stop drift; the body text now quotes only that tool's current output and the document no longer copies specific numbers; the full test count goes 352 → **384** (385 after the analysis layer); evidence in `docs/rubric-mapping.md` §2l | 2h |

Total about **21h**. M1's 2h only delivers "the template + one pair", because the template is where the cost of the following 5 repositories is amortised; if templating fails, M2 degrades to 3×2h (see R1).

## 10. Risks and failure modes

| # | Risk | Trigger signal | Mitigation |
|---|---|---|---|
| R1 | Work on the 6 seed repositories explodes | M2 overruns 3h | generate parametrically with `make_repo.py` first (smell combinations + size); humans only review "is there a real cross-module contract" |
| R2 | AST impact analysis never reaches recall 1.0 | M3 misses 100% of target | recall is a correctness requirement for governance (a miss is a failure) → if it cannot be met, switch to "the label set is generated by the analyser + manually reviewed" and say so in the report; lowering the threshold quietly is not allowed. **In the measurement M3 reached `recall=1.00 precision=1.00` on 6/6, so that fallback was not used**; the cost is that the contract had to be defined more narrowly (only "a top-level value read by ≥2 modules inside the package"; see the `govern/impact.py` docstring), recorded in section 6 of `docs/rubric-mapping.md` |
| R3 | The real API is rate-limited or unavailable, or the model drifts | M6 recording fails | `replay` is the delivery default; recordings are made once, then frozen, and the report states the model snapshot date. **M6 status**: there are no credentials on this machine, so the 6 recordings are **simulated** suggestions derived by the factory (`source: "sim"`, the gold patch with one consumer removed); there is therefore no "real call" that could drift; the `live` path is covered only by a loopback stub in the tests |
| R4 | No pytest → inconsistent with the workflow document convention | M0 | switch explicitly to `unittest`, write that into AGENTS.md and explain why in the README; the two coexist (pytest discovers unittest cases) |
| R5 | Python 3.15 is incompatible with some library | any `import` fails | zero third-party runtime dependencies removes the risk |
| R6 | The UI becomes a time sink | M9 overruns 2h | edit `参考代码库/index.html` directly (a 49-line skeleton already known to work), no framework, no visual polish | **not triggered**: M9 finished within 2h, no framework was added; the storyboard is captured by a script rather than by hand |
| R7 | **No git → no commit/release possible** | M0 | **handled (2026-11-14)**: both winget and the official installer failed inside the sandbox on this machine (winget exit code `-1978335231`, the Inno silent install left no files), so the **portable MinGit 2.56.1** is used instead, unpacked to `_tools/git` (excluded by `.gitignore`) and invoked only by prepending `$env:PATH`; the repository therefore has real commits. **The ZIP + `SHA256SUMS` snapshot is kept as well**, and the README states both side by side faithfully |
| R8 | The gate is bypassed (the most fatal; a direct hit on the red line) | M4 negative test fails | the generation path accepts only `Gate.open() == True`; the interface layer has no public bypass; there are dedicated negative tests. **M4 verified**: all gate state is private, the card is validated at construction (a mismatch between `required_ids` and `n_required` raises `ValueError`), confirmation does not carry across instances, and the token is single-use and invalidated as soon as the ticking changes; the five `BypassTests` cases in `tests/test_gate.py` cover this |
| R9 | The log gets a partial line or loses an event | M5 | one-line `write` + `flush` + `fsync`; the test that kills the process midway must pass at M5. **verified**: `tests/test_log.py:302` simulates a torn last line, and after reopening the truncated tail is cut off and seq is reused; the implementation uses a single `os.write` with `O_APPEND` plus `fsync`, with no `.tmp` staging |
| R10 | Resume double-writes | M8 | the last `seq` in the log is the single authority; a conflict between state and log stops with an error. **verified**: `StateConflict` has a test (`test_state_ahead_of_the_log_is_a_conflict`), and the fix is "state is only written, never read back to decide; every read-back follows the log replay" |
| R11 | Planned analysis gets written up as measured | when writing the report | the SPEC section 5 banner + the 8.1b self-check table; "experiment shows" is banned in the report |
| R12 | The rule set cannot detect the smells in the light-stratum corpus, so the debt metric is always 0 at stratum L | M7 measurement | measured L=0 / M=3 / H=8 (weighted); the gap is that the stratum-L smells are "floating-point money + module-level cache + a semantically duplicated tax derivation", which none of the six rule families covers. **Decision: the corpus is not changed** (the corpus is referenced byte for byte by M2 acceptance and by the 6 recordings, so changing it invalidates replay). Delivery claim: a debt reduction is claimed only at strata M/H, with hidden tests and line counts used for stratum L; this is written in `docs/rubric-mapping.md` §2f and section 6 |

## 11. Open items for you to confirm (they do not block starting)

1. **Git**: **settled (2026-11-14)** — the system install is blocked by the sandbox, so the portable MinGit (`_tools/git`, not committed) provides real commits; the `SHA256SUMS` snapshot is kept as second evidence, and the README states both identifiers side by side.
2. **UI form**: a local web page by default (`http.server` + plain JS, editing the reference skeleton). If you would rather have a pure CLI, M9 saves 1.5h, but producing storyboard images gets harder.

## 12. First step after approval

1. Write this plan into `docs/PLAN.md` as it stands (with the milestones and the acceptance commands).
2. Do **M0**: create the directories, write `config/config.json` and `AGENTS.md`, and get the `--selftest` and `unittest discover` commands passing first.
3. Then proceed in the order M1→M11, run that row's acceptance command at the end of each milestone and paste the result to you, **without doing everything first and reporting only at the end**.
