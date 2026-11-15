# SPEC — Interaction governance in AI-assisted legacy-code refactoring: experiment programme specification

| Item | Value |
|---|---|
| Document version | 1.0 (first draft, for review) |
| Status | Draft — becomes Frozen once the eight open questions in §6 are decided |
| Subject of study | The pre-generation governance gate formed by the "Architecture and Constraint Assessment Card" plus the "Mandatory Confirmation Checklist" |
| Upstream documents | `A1 Literature Review 3138100 V1.docx` (724-word body + 354-word reference list), `Assignment 2 Course scoring instructions.docx` (5 pages) |
| Downstream documents | `docs/PLAN.md` (implementation plan), `docs/rubric-mapping.md` (requirement → evidence trace) |
| Delivery route | This file defines only "what to build and how passing is judged"; it contains no implementation code |

---

## 0. Basis and labelling conventions

### 0.1 Notation

Every key claim in this document carries a source marker, so that a reviewer can trace each one back item by item:

| Marker | Meaning |
|---|---|
| `[A1]` | Wording taken directly from the A1 literature review |
| `[A2]` | Wording taken directly from the course scoring instructions (the only criterion of "meets the requirement") |
| `[REF]` | From workspace reference material (the course lab code in `参考代码库/`, and the project conventions in the workspace `DSH-*` workflow note) |
| `[assumption]` | **Derived in this document**, not written in the course documents; the basis is in §7 |
| `[TBD]` | Depends on your decision in §6; not fixed until then |

### 0.2 Hard facts that must be followed literally

**A2 word limits and truncation rules** `[A2]`:

- Abstract ≤ 300 words; Design rationale & project explanation about 1,000 words, **hard cap 1,100 words**.
- Body plus abstract together ≤ 1,400 words; **reading stops after 1,300 counted words**.
- Not counted: figures, diagrams, storyboards and their short labels or captions; references, repository links, README content.
- The total word count goes on the first page; text inside the rationale table counts towards the total.
- Do not stuff explanatory paragraphs into figures to evade the word limit.

**The four A2 scored criteria** `[A2]`: Design reasoning and scope **/30**, Developed interaction **/30**, Architecture and technical reasoning **/20**, Development evidence and authorship **/20**.

**A2 requires the report to contain** `[A2]`: Abstract; Design rationale (including the four columns of "A possible rationale-table layout": Design choice / Why it suits the problem / Supporting evidence or reference / Status); System diagram (components, connections, information or control flow, **including AI behaviour**, marked implemented / simulated / planned); Storyboards and illustrated interaction (**2–3** usage instances, with user action, system response, and feedback or control); Repository and development evidence (public GitHub + README + the commits or release submitted + a pointer to the development record); References.

**A2 requires the README to state** `[A2]`: Project status (what was built, what runs / is simulated / is unfinished); Technology stack (including the AI tools or models used, what each does, and choices still open); Running or inspecting the work (dependencies and start-up); Development record (important changes, why, what was checked, the relevant commits); AI assistance (which tools were used, what they were asked to do, how you changed the result, how you verified it); Additional files. The README must be short, must give the prose word count at the top, and **must never commit an API key**.

**A2's definition of "developed work"** `[A2]`: it may be an implementation, a prototype, a simulation, or a walkthrough of screens or states that have been developed; placeholders must be labelled and their meaning explained; **visual polish and feature count are not the point**; "listing only planned features does not equal developed work".

**A2's four descriptor bands (updated docx of 2026-11-14, pages 5–6)** `[A2]`: each of the four criteria has four bands — Convincingly demonstrated / Demonstrated / Partly demonstrated / Not yet demonstrated. Three of them bind this specification; they are not style advice:

1. **Never present planned or simulated work as implemented.** The "Not yet demonstrated" band of `Developed interaction` says, verbatim: *"materially misrepresents planned or simulated behaviour as implemented"*. This is the red line.
2. **Developed and planned work must be explicitly separated, and scope trade-offs explained.** The "Convincingly" band of `Design reasoning and scope` requires that the work *"clearly identifies which choices concern developed work and which concern planned features"*, and requires the author to justify *"compromises in scope"*.
3. **Original / reused / assisted must be distinguished.** The "Convincingly" band of `Development evidence and authorship` requires *"distinguishes original, reused and assisted work, with relevant examples of reviewing and adapting AI output"*.

The remaining enforceable requirements: the "Convincingly" band of `Architecture` requires the diagram and the explanation to show "how components, flows and dependencies support the interaction, **including intelligent behaviour**", and requires the technical choices and boundaries to match the submission. The "Partly" band of that criterion loses marks for "listing components and technologies without explaining connections or roles, and leaving differences unexplained".

> The only thing still missing is the **band → mark mapping**: the docx gives only the maximum for each criterion (/30, /30, /20, /20), not how many marks each of the four bands carries `[assumption]` A-15. This specification therefore accepts work on "is the band descriptor satisfied" and **does not predict marks**.

### 0.3 What this specification means by "experiment programme"

An "experiment programme" is the following four things taken together; none can be dropped without failing acceptance:

1. **A runnable governance prototype** (M1–M6): it must actually do the thing — show the impact before generation, and require the confirmation ticks. This is where A2's `Developed interaction /30` lands.
2. **Reproducible experiment orchestration** (M2, M3, M7): conditions, tasks, order and model are all fixed by configuration and a pre-generated schedule, so any run can be replayed.
3. **Computable structured logs** (M7): the JSONL of §4 is the only data source, and every metric in §5 must be computable from the log alone.
4. **A traceable analysis pipeline** (M8, M9; SIM/PLAN under Q8): the **capability** to get a results table from `runs/` in one command must exist, but it is not the primary evidence delivered this round.

A2 itself **does not require** statistical tests or human participants `[A2]` (the words experiment, statistics and participant never appear as a requirement anywhere in it). The experimental design comes from the contribution and the limitations in A1 §4 `[A1]`. Questions Q1/Q2/Q4/Q5/Q8 in §6 were decided on 2026-11-14 (see 6.0): **build the governance prototype plus author self-testing, do no human study; keep the N=10 design on record only; build six seed repositories as the corpus; do not implement C2**. The **acceptable part** of this specification is therefore the MUST acceptance criteria of M1/M3/M4/M5/M6/M7/M8/M11; M2 is SIM, M9 is PLAN and M10 is N/A. H1–H7 remain planned hypotheses, with **no observational data**.

---

## 1. Research questions, hypotheses and variables

### 1.1 Deriving the RQs from A1's gaps (the derivation chain — keep it)

A1's chain of argument `[A1]`:

1. In legacy (brownfield) refactoring, AI pulls developers into a "prompt–response–implement" loop that speeds work up in the short term but damages conceptual understanding; Shihab et al. report **34.9% faster** work with understanding impaired.
2. Without governance, the short-term efficiency gain comes with **37% more technical debt and 41% more security vulnerabilities** (Roy et al., β=0.48).
3. Existing XAI calibrates trust only **after the fact**, at the code-review stage (Gao et al.: agreement rate 89.22% at medium explanation depth; deeper explanations trigger scrutiny but add no time).
4. Two gaps: **(i) no macro-level architectural intent mapping** — existing methods stay at output or token level and do not map onto repository-level dependencies; **(ii) no pre-generation governance** — there is no upstream line of defence that stops blind prompt-response before generation.
5. Proposed contribution: before generation, force the system to emit a structured **"Architecture and Constraint Assessment Card"** (impact statements plus checkboxes), and **authorise code generation only after explicit confirmation** (for example confirming global variables and cross-module interface contracts).
6. Two limitations the author states: **(a) interaction friction** slows routine tasks; **(b) without granularity that adapts to task complexity, frequent interaction produces "Confirmation Fatigue"**, which degrades into mechanical ticking and so weakens scrutiny instead.

The RQs turn items 5 and 6 into testable propositions: effectiveness (does 5 hold), cost (6a), mechanism (is it calibration or just slowing down), understanding (is the harm in 1 offset), fatigue (6b).

### 1.2 Research questions

| ID | Research question | Source |
|---|---|---|
| **RQ1** (safety effectiveness) | In legacy-code refactoring tasks, does adding the "assessment card + mandatory confirmation checklist" gate before generation reduce, relative to an ungated baseline, the proportion of **acceptances without review** and **downstream quality risk** (defects that escape the hidden tests, technical-debt delta, security-warning delta)? | `[A1]` §3 gap ii, §4 proposal |
| **RQ2** (cost) | How large is the cost of that gate in **task completion time** and **subjective friction** (cognitive load)? Is the cost concentrated in routine or low-complexity tasks? | `[A1]` §4 limitation a |
| **RQ3** (mechanism) | Does the gate improve **trust calibration** — that is, does the **discriminative power** of accept/reject decisions over the true correctness of a suggestion rise, rather than a surface safety bought by accepting less overall (over-distrust)? | `[A1]` §2 Camp C, §4 |
| **RQ4** (understanding) | Does the gate improve the refactorer's understanding of the **architecture of the affected modules** (cross-module contracts, global state, side effects)? | `[A1]` §2 Camp B (understanding impaired) |
| **RQ5** (fatigue and granularity) | Under the governance condition, does confirming **degrade into mechanical ticking** as the session goes on? Can **adaptive granularity** by task complexity reduce the RQ2 cost without giving up the RQ1 benefit? | `[A1]` §4 limitation b |

### 1.3 Hypotheses

Directional hypotheses, all tested within the framework of "pairing inside the same participant" (see 2.3). H7 is a conditional hypothesis, and since Q5 decided **not to implement C2**, H7 is only an object of planned argument.

> **Status: all of them are planned hypotheses (PLAN).** Under the Q1/Q2 decisions in 6.0, no human data is collected this round, so H1–H7 have no observations and serve only as pre-registered design and as an interface for later research. The report must not contain "experiments show" style wording (see A-16 and 8.1b).

| ID | Hypothesis (direction) | Operational reading | RQ |
|---|---|---|---|
| **H1** | **Blind-acceptance rate OTI is lower** under the governance condition C1 than under baseline C0 | `OTI = blind acceptances / total suggestion actions` (defined in 1.5) | RQ1 |
| **H2** | **Escaped-defect rate is lower** under C1 than C0, and so are the **technical-debt delta and the security-warning delta** | `task_end.tests_pass` false counts as an escape; `debt_delta`, `vuln_delta` | RQ1 |
| **H3** | **Task completion time is longer** under C1 than C0, and **subjective friction is higher** (the expected cost; direction is clear) | `task_end.elapsed_ms`; NASA-TLX mental demand / effort / frustration | RQ2 |
| **H4** | **Calibration AUC is higher** under C1 than C0, and the gain **cannot** be fully explained by "the acceptance rate falling overall" | per-participant AUC (accept decision vs true correctness of the suggestion); report the acceptance rate as well | RQ3 |
| **H5** | **Comprehension quiz score is higher** under C1 than C0 | mean of `comprehension_item.correct` | RQ4 |
| **H6** | **A fatigue trend exists inside** C1: gate latency falls with `task_index`, and the number of tick interactions falls with `task_index` | slope of `gate_latency_ms` and of the `card_item_toggle` count against `task_index` within a session | RQ5 |
| **H7** | (**PLAN, not implemented**) adaptive granularity C2 **reduces time and friction** relative to C1, and its OTI is **non-inferior** to C1 | `elapsed_ms`, TLX and OTI for C2 vs C1 | RQ5 |

The null hypotheses H0-1…H0-7 are, respectively, no difference / no non-inferiority in the quantities above. H6 is an "existence" hypothesis; its null is a slope ≥ 0 (no degradation) `[assumption]`.

> Why H3 is stated as an "expected cost" rather than "no difference" `[assumption]`: A1 §4 explicitly concedes that "forced pre-generation confirmation introduces interaction friction and slightly slows routine tasks". If the data showed no cost, that would suggest the gate never really took effect (it was bypassed), and the `gate_decision.blocked` log would need re-checking. **H3 therefore doubles as a manipulation check**.

### 1.4 Variables

**Independent variables (IV)**

| Variable | Levels | Type | Notes |
|---|---|---|---|
| IV1 Condition | C0 baseline / C1 governance (C2 adaptive is PLAN only and is not in the design, see Q5) | Within-subject, paired | See 2.1 |
| IV2 Task complexity | low / medium / high (3 levels) | Within-subject, stratification factor | Used to test RQ2's "is the cost concentrated in low-complexity tasks" |
| IV3 Task index within session | 0 / 1 | Within-subject, time factor | Fatigue and learning effects |

**Dependent variables (DV)**

| Category | Metric | Log source |
|---|---|---|
| Primary DV | Blind-acceptance rate OTI, escaped-defect rate, task completion time | 4.3 / 5.2 |
| Secondary DV (quality) | Technical-debt delta, security-warning delta, number of hidden-test failures | `task_end` |
| Secondary DV (calibration) | Acceptance rate, edit rate, rejection rate, discriminative AUC, explanation-open rate | `suggestion_action`, `explanation_open`, `suggestion_scored` |
| Secondary DV (subjective) | NASA-TLX three dimensions, SUS, single-item friction rating | `survey_response` |
| Secondary DV (understanding) | Comprehension quiz accuracy | `comprehension_item` |
| Secondary DV (process) | Gate latency, tick interactions, mechanical-confirmation rate, number of gate blocks | `gate_decision`, `card_item_toggle` |

**Control variables (measured and recorded, held fixed where possible)**

- Participant: years of programming (`prior_years`), LLM-tool use frequency (`llm_freq`), familiarity with the legacy repository's language (`lang_familiarity`, 1–5).
- Material: task pairs (`pair_id` matched for difficulty), task presentation order (ABBA balanced).
- System: model ID and version, temperature, seed, prompt-template version, `app_version` — all taken from configuration and written to the log; no magic numbers in code `[REF]`.
- Environment: operating-system family, browser/IDE, per-session time cap, whether external search is allowed (forbidden by default).
- Scoring side: the hidden test suite and the static rule-set versions are fixed (`scorer_version`); there is no human rater, hence no rater effect.

**Confounders (can only be measured, not fully controlled; must be stated in the report)**

- Learning effect: the second task benefits from the first (mitigated by ABBA plus independent task pairs; not eliminated).
- Fatigue: performance falls later in the session (modelled directly by IV3).
- Novelty effect: first use of the governance interface.
- Implementer as researcher: double blinding is impossible (see 2.6).
- Task pairs may still not be equivalent (`[assumption]` A-4 gives the comparability criterion).

### 1.5 Precise definitions of the key quantities (define first, measure second)

| Quantity | Definition | Notes |
|---|---|---|
| **Total suggestion actions** | Count of distinct `suggestion_id` values that have a `suggestion_action` event | Duplicate suggestions from retries are de-duplicated by `suggestion_id` |
| **Blind acceptance** | The suggestion's `action = accept` **and** no matching `explanation_open` record (or `accepted_after_gate = false`) **and** `review_dwell_ms < τ_review` | `τ_review` defaults to **2000 ms** `[assumption]` A-3; 1 s / 2 s / 5 s sensitivity analyses are required |
| **OTI** | `blind acceptances / total suggestion actions`, range 0–1, lower is safer | Primary DV |
| **Escaped defect** | `tests_pass = false` after running the **hidden** test suite at `task_end` | The hidden tests are invisible to participants, which prevents targeted edits |
| **Technical-debt delta** | rule-set hits after submission − hits at task start (same rule-set version) | Count data, skewed |
| **Security-warning delta** | As above, for the security rule subset (hardcoded secrets, `eval`/`exec`, unsafe deserialisation, string-concatenated SQL) | Count data |
| **Discriminative AUC** | Treat `accept` as 1 and `edit`/`reject` as 0 as the prediction, `suggestion_scored.is_correct` as the truth, and compute the area under the ROC curve per participant | Undefined for a single class; see 5.3 |
| **Mechanical confirmation** | A `gate_decision` with `confirmed = true` whose `card_item_toggle` events have a median `dwell_ms` < 800 ms `[assumption]` A-6, and `n_confirmed = n_required` with no un-ticking | Behavioural proxy for fatigue |
| **Comprehension quiz score** | accuracy on the 5 multiple-choice items at the end of the session about "the affected modules of this task" `[assumption]` A-5 | Tests architecture and contracts only, not syntax |

---

## 2. Experiment conditions, randomisation and pairing

> **Status of this section: planned protocol (PLAN) plus one technical demonstration that has been executed.** 2.1–2.6 describe the full protocol **if a human study were run**; this round does not run it (Q1). What does run this round is the smallest demonstrable part of it: the same recorded data replayed once as C0 pass-through and once as C1 gated, showing the causal chain "the gate does block, the ticks do unlock". That step is technical acceptance and produces no data for H1–H7.

### 2.1 Condition definitions

All three groups share **the same UI skeleton, the same task set and the same logging interface**, and differ only in whether a gate is placed before generation — this is the core constraint that makes them comparable.

| Dimension | **C0 baseline** | **C1 governance** | **C2 adaptive (PLAN, not implemented)** |
|---|---|---|---|
| Interaction shape | Enter a refactoring request → get the full suggestion directly (diff + explanatory text) | Enter the request → get the **assessment card** first (impact statements + checkboxes) → tick all required items → generation unlocks only then | Same as C1, but the number of card items and required items scales automatically with task complexity / risk level |
| Blocked before generation | No | **Yes** (`gate_decision.blocked` is reproducible) | Yes |
| Suggestion visibility | The diff is shown immediately | Before confirmation, **only the impact and contracts are shown, not the diff** | Same as C1 |
| Governance granularity | None | Fixed: the whole impact set goes on the card | Adaptive: low-risk tasks get cross-module contract items only, high-risk tasks get the full set |
| Bypass allowed | — | No (single entry point) | No |
| Log path | Same as M7, same schema | Same as M7, same schema | Same as M7, same schema |

> C0 must be "the same system with the gate set to pass-through", **not another product** `[assumption]` A-7. Reason: if C0 were a real commercial copilot and C1 a self-built prototype, no difference could be attributed to governance itself (interface, latency and suggestion quality would all be confounded). The studies A1 cites — Peng et al., Shihab et al. — are all "same tool vs no tool" or "same interface, different conditions", which supports this choice.

> **C2's status (Q5, decided 2026-11-14): not implemented.** The C2 column stays in the table because it serves two purposes: it shows the design space (fixed granularity is only a special case of adaptive granularity, and that trade-off must be argued in the rationale); and it meets A2's requirement to "clearly distinguish which parts are developed and which are planned" `[A2]`. **But C2 must not appear in any implemented storyboard or demo**, and it produces no data; H7 is therefore not tested (see the table note in 5.2).

### 2.2 Task set and stratification

- Scale (Q4 decision: **self-built**, no real open-source repositories): **6 self-built seed repositories = 6 task instances = 3 difficulty levels × 2 instances**; the two instances within a level are "equivalent instances" of each other (same `pair_id`), giving 3 pairs in total. Why self-built: only a self-built corpus can provide **gold patch + hidden tests + impact-set labels** at the same time (M1 acceptance 2 and M8's scorability both depend on them); a real open-source repository has no gold, so automatic scoring is impossible. The cost is low external validity, which must be written into the limitations in 2.6.
- Each instance is a small legacy Python repository that runs offline (about 200–600 lines, 3–6 modules), seeded with known bad smells: a global singleton / global mutable state, implicit cross-module contracts, duplicated logic, a bare `except`.
- Each instance ships with: a requirement statement (refactor intent), a **hidden test suite**, a **gold patch**, and **impact-set labels** (the list of global variables and cross-module contracts that the task really touches).
- A participant does **2 tasks** per session (1 per condition, from the same `pair_id`), so that the pair is comparable and the session stays within 90 minutes `[assumption]` A-8.

### 2.3 Design and pairing

**Design**: within-subject, **2 conditions (C0 / C1) × 2 orders (AB / BA), crossed**; the unit of pairing is the participant. C2 is not in the design (Q5).

- **Pairing 1 (statistical)**: the same participant's C0 and C1 observations occur as a pair; a paired test removes individual differences (skill differences are usually the largest source of variance).
- **Pairing 2 (material)**: the two instances of a `pair_id` differ by ≤ 20% on "files to change, functions to modify, number of hidden tests" `[assumption]` A-4; one goes to C0, one to C1.
- **Pairing 3 (order balance)**: condition order is balanced **ABBA** within participant blocks; task pairs rotate PAIR-01→02→03 cyclically. Each participant's two-task order is random but fixed by the schedule, not decided on the spot.

**Why within-subject** `[assumption]`: the two studies A1 cites that are closest to this one (Shihab et al. N=10, Gao et al. N=34) are both within-subjects. A within-subject design yields a testable paired comparison with a small N, which is the only realistic option for a coursework project; the cost is learning effects and fatigue, handled by ABBA plus modelling IV3.

**Unit of sample allocation**: the `(participant, task)` observation is the unit of analysis; the participant is the random-effect / pairing unit.

### 2.4 Randomisation procedure

1. Generate **`randomization_schedule.json`** before data collection: `block size = 4` (each block holds 2 AB and 2 BA orders), the PAIR rotation is pre-assigned to every slot, and condition labels are pre-bound to concrete instance IDs.
2. Each participant takes the next unused slot in arrival order (**simple randomisation within a block**, no post-hoc adjustment). Once generated, the schedule is frozen and committed to the repository as reproducibility evidence.
3. At run time the session **only reads the schedule** and does no live randomisation — this rules out selective allocation by the experimenter (the most easily questioned bias, which must be removed by mechanism).
4. Schedule generation must be reproducible: given `seed` and `N` it outputs a deterministic allocation table; the generation parameters are kept in the appendix.
5. If someone withdraws mid-way, their slot is not reused (to keep the block balanced) and `withdrawn = true` is recorded in the log.

> Acceptance requirement (written into M2): simulate N=100 "virtual participant" allocations against the same schedule; the two conditions must occur equally often (chi-square p > 0.05), and every PAIR must appear under both conditions.

### 2.5 Single-session flow (timeline)

| Stage | Duration | What the participant does | System output (log events) |
|---|---|---|---|
| 0 Consent and screening | 5 min | Read the consent form, tick, complete the demographics and experience questionnaire | `session_start` (with `consent_given`) |
| 1 Interface familiarisation | 10 min | Walk the whole interface once on a **non-experimental repository** (2 minutes per condition) | the `prompt_submit` that follows `session_start` (marked `task_id = TUTORIAL`, excluded from analysis) |
| 2 Task 1 | ≤ 30 min | Read the request → ask → (C1: view the card, tick, confirm) → review the suggestion → accept / edit / reject → self-test → submit | `prompt_submit`…`task_end` |
| 3 Buffer and task-1 post-test | 5 min | NASA-TLX (three dimensions), SUS, 5-item comprehension quiz | `survey_response`, `comprehension_item` |
| 4 Task 2 | ≤ 30 min | As above, other condition | As above |
| 5 Task-2 post-test | 5 min | As above plus free-text items (subjective view of the gate) | `survey_response` |
| 6 Wrap-up | 2 min | Optional semi-structured interview (recorded separately, not in the log) | `session_end` |

Timeout handling: tasks 1 and 2 each have a hard 30-minute cap; on timeout the session wraps up automatically and writes `timeout = true` (the observation is kept and handled as in 5.3).

### 2.6 Bias control and the honest "can / cannot" boundary

**What we can do**: a pre-generated schedule removes allocation bias; hidden tests prevent targeted edits; a single log schema keeps the two groups comparable; a pre-registered analysis plan (the 5.2 table) prevents picking metrics afterwards; thresholds such as `τ_review` get sensitivity analyses; the automatic scorer (M8) replaces human rating and removes rater effects.

**What we cannot do** (must go into the A2 report as limitations): the implementer is the researcher, so double blinding is impossible; the same researcher cannot be unaware of the condition either, so **no claim of "removing expectancy effects" can be made**; participants would mostly be convenience-sampled fellow students, so external validity is limited; the corpus is the six self-built seed repositories (Q4) with smells seeded by hand, so the messiness of real legacy systems is not covered; a single session is short, so long-run technical-debt evolution cannot be observed and only a **short-run proxy** (rule-set counts) is used instead.

---

## 3. Software module list

### 3.0 Scope and status labels

Each module carries a status label, aligning with A2's "implemented / simulated / planned" requirement `[A2]`:

| Status | Meaning | A2 requirement |
|---|---|---|
| **MUST** (implemented) | Must really be implemented and pass acceptance | Marked implemented in the report; needs a storyboard demonstration |
| **SIM** (simulated) | Fixed or recorded data replaces the real backend; the interface and the log are real | Marked simulated in the report; must say what was replaced |
| **PLAN** (planned) | Appears in the design only, not implemented | Marked planned in the report; must not count as developed work |
| **N/A** (not applicable) | Not implemented because Q1 decided against a human study | Appears only as a design note on "how it would be done in a human study", and likewise **must not** be described as implemented |

**This round's delivery set (per the Q8 decision of 2026-11-14)**:

| Module | Status | Notes |
|---|---|---|
| M1, M3, M4, M5, M6, M7, M8, M11 | **MUST (implemented)** | They form the closed loop "task → assessment card → ticks → gate → generation → review → log", which is where `Developed interaction /30` lands; M3 runs live + replay, M8 uses the six-category JSON rule set |
| M2 | **SIM (simulated)** | Driven by author self-testing plus recorded replay; no human sessions |
| M9 | **PLAN (planned)** | The analysis pipeline is not shipped as the primary evidence. Its interface was specified here only, and the data it would analyse is not part of this round. It has since been implemented in `analysis/` (see `docs/PLAN.md` M13); that does not make it primary evidence. |
| M10 | **N/A** | Q1 decided not to recruit humans; the compliance flow is not implemented |

> The way the loop is demonstrated therefore changes: it is no longer "a participant walks through it" but **author self-testing plus recorded replay** — the same recording replayed once as C0 pass-through and once as C1 gated, showing the difference between the two interaction paths. The report must state that this is simulated `[A2]` (see A2 red line 1).

---

### M1 · Task corpus and seed legacy repositories — **MUST**

- **Purpose**: provide experiment material that is interchangeable within a difficulty level and can be scored automatically. Per Q4 it is **self-built**, not real open-source repositories.
- **Input**: task definition files (one per instance) whose fields include `task_id`, `pair_id`, `stratum`, `repo_path`, `intent_text`, `hidden_tests_path`, `gold_patch_path`, `impact_label_set` (the list of global variables and cross-module contracts).
- **Output**: 6 repository snapshots that run offline + 6 hidden test suites + 6 gold patches + 6 impact-set label files; one `tasks/index.json`.
- **Dependencies**: `pytest` only; no network; no runtime services.
- **Acceptance criteria**:
  1. For every repository, the `pytest -q` result in its initial state is **explicitly recorded** as the baseline (failure is expected, and the reason must be "the refactoring is not done", not a missing dependency).
  2. After the matching gold patch is applied the hidden tests are **all green** — this must hold for 6/6 instances, otherwise the instance is void.
  3. Every instance contains at least **1 global mutable state** and **1 implicit cross-module contract**, and both appear in `impact_label_set`.
  4. The two instances of a `pair_id` differ pairwise by ≤ 20% on "files changed / functions modified / number of hidden tests".
  5. No comment, TODO or test name inside the repository may point at the answer (automatic scan for words such as `gold`/`fix`/`solution`).

---

### M2 · Session orchestrator — **SIM** (author self-testing plus recorded replay; the human-session version is PLAN)

- **Purpose**: turn "who, in what order, doing which task, under which condition" into data that cannot be changed on the spot.
- **Input**: `randomization_schedule.json`, `participant_id` (pseudonym), the consent record, `session_config` (time caps, condition set).
- **Output**: `session_id`, the task sequence (with each task's `condition` / `task_id` / `task_index`), the session state-machine state; writes `session_start` and `session_end` events.
- **Dependencies**: M1, M7; M10 is **N/A** (Q1: no recruitment). In SIM mode the consent step is replaced by the fixed value `consent_version = "SIM-AUTHOR"` and does not block start-up.
- **Acceptance criteria**:
  1. Given a schedule and a participant, the allocation is **deterministic**: the same input run twice gives exactly the same task sequence.
  2. 100 simulated virtual allocations: the two condition counts are balanced (chi-square p > 0.05); every PAIR appears under both conditions.
  3. **Resume after interruption**: after the process is killed and restarted, finished tasks are not repeated and unfinished ones continue from the break; the sequence and the log `seq` neither skip nor repeat numbers.
  4. The full state of any allocation can be **rebuilt from the log alone** (with a rebuild check: the recomputed result matches the in-memory state at run time).
  5. With no valid consent (`consent_given = false`) it refuses to start and gives a clear error rather than failing silently.

---

### M3 · AI suggestion engine (single LLM client) — **MUST** (live calls to the real API + offline replay in the delivered state)

- **Purpose**: funnel every model call behind one boundary that can be swapped, pinned and replayed.
- **Input**: repository snapshot, `intent_text`, context pack (file excerpts + symbol table + call-graph subgraph), run mode `live` / `replay`, model configuration (`model_id`, `temperature`, `seed`, `max_tokens`).
- **Output**: a structured suggestion object `{suggestion_id, patch_diff, rationale_text, touched_symbols[], rationale_layers{}}`; plus a `generation_request` event per call (request hash, latency, token counts, mode).
- **Dependencies**: a single client module (project convention `[REF]`: all LLM calls are centralised, model name / temperature / seed are read from config only, and hard-coding them in code is forbidden); the `recordings/` replay cache.
- **Two modes (per Q3)**:
  - `live`: **calls the external API for real**. The key is read from an environment variable only and **never enters the repository**; each call writes the request hash and the raw response to `recordings/`.
  - `replay`: **the default mode in the delivered state**; replays from `recordings/` with no network and no key, so that 3.11 item 3 "reproduce in one command" still holds.
- **Delivered-state requirements (Q3 addendum)**: before submission, remove every API endpoint, key and account identifier from the repository; the README explains how a reviewer can supply their own key to enable `live`, and states that the default `replay` reproduces everything. Basis, A2 verbatim: *"Never commit API keys… explain how a reviewer can supply their own without including your key"* `[A2]`.
- **Acceptance criteria**:
  1. **Determinism (replay)**: the same input replays to a **byte-identical** suggestion; 10 consecutive calls all produce the same output hash.
  2. **Complete recording**: every `live` call writes the request hash and the raw response to `recordings/`, and `replay` can reproduce that same suggestion object.
  3. **No magic numbers**: grepping the repository for `model`, `temperature` and `seed` constants gives zero hits outside config files.
  4. **No keys or endpoints committed**: in the delivered state the scan for patterns such as `sk-`, `api_key`, `token=` and `https://` endpoints gives zero hits (it uses the same scan script as 3.11 item 5).
  5. **Bad responses do not crash**: when the response does not match the schema it writes `integrity_event(kind = "schema_violation")` and returns a clear error code; the session continues (following the handling idea for `malformed.txt` in `参考代码库` `[REF]`).
  6. Every call produces exactly one `generation_request` event; the `mode` field states `live` / `replay` truthfully, and `model_id` holds the real model name at recording time.

---

### M4 · Constraint and impact analyser — **MUST**

- **Purpose**: this is the smallest runnable version of A1's gap (i), "macro-level architectural intent mapping" `[A1]`: work out "which global states and cross-module contracts this function change touches".
- **Input**: repository snapshot, `intent_text`, candidate patch (may be empty — the card must be producible before confirmation).
- **Output**: `impact_set {global_vars[], cross_module_contracts[], side_effects[], affected_tests[], risk_level}`; `impact_set_hash`.
- **Dependencies**: Python `ast` (standard library); at most 1 third-party static-analysis library (with the reason stated in `requirements.txt`).
- **Acceptance criteria**:
  1. For all 6 M1 gold patches, `impact_set` achieves **recall = 1.0** against `impact_label_set` (no real global variable or cross-module contract may be missed), with precision ≥ 0.8 `[assumption]` A-9.
  2. **Discrimination**: a patch that only changes a function body and a patch that changes a cross-module contract must get different `risk_level` values (asserted with 2 constructed cases).
  3. **Robustness**: an empty patch, a file with a syntax error and a single-file repository all return a clear error code without raising an uncaught exception.
  4. **Acceptable interactivity**: a single analysis takes < 2 s (measured on the largest M1 instance) `[assumption]` A-10.
  5. Deterministic output: two runs on the same input give the same `impact_set_hash`.

---

### M5 · Assessment-card renderer — **MUST**

- **Purpose**: turn `impact_set` into something a person can decide on — the direct implementation of A1 §4's "Assessment Card" `[A1]`.
- **Input**: `impact_set`, a suggestion summary (**without the diff**), condition configuration (this round only C1 with the full fixed set; C2 adaptive is PLAN).
- **Output**: `card_view {card_id, items[]{item_id, statement, category, affected_symbol, evidence_ref, required}}` + the rendered interface fragment.
- **Dependencies**: M4; a template layer (Jinja or plain HTML).
- **Acceptance criteria**:
  1. **No invented items**: every `item.affected_symbol` must have a source in `impact_set` (assert 100% traceability automatically).
  2. **Item specification**: each card has ≥ 3 items, each item is ≤ 120 characters, and it **must name a concrete symbol** (no empty phrases such as "may affect other modules").
  3. **Deterministic rendering**: the same `impact_set` renders identically twice.
  4. **The key governance property is testable**: before confirmation the interface **must not** show diff content — assert that "the rendered output contains no added line of the patch". This is the essential difference between C1 and C0 and must be machine-checkable.
  5. (PLAN) In C2 mode, low-risk tasks must have **strictly fewer** `n_items` than high-risk tasks — not implemented this round, so this item is not accepted.

---

### M6 · Mandatory confirmation gate and checklist — **MUST**

- **Purpose**: make "no confirmation, no generation" a **system invariant** rather than user discipline `[A1]`.
- **Input**: `card_view.items`, the user's tick state, threshold configuration (`n_required`, whether every generation must pass the gate again).
- **Output**: `gate_state ∈ {blocked, unlocked}`, an authorisation token (single use), the `gate_decision` event.
- **Dependencies**: M7; M5.
- **Acceptance criteria**:
  1. **Invariant**: when `n_confirmed < n_required`, every generation request is refused and **every time** a `gate_decision(blocked = true)` is written; an interface-level test must cover that path.
  2. **Positive path**: once all items are ticked the gate unlocks, generation succeeds, `blocked = false` and `confirmed = true`.
  3. **No bypass**: no public entry point bypasses the gate (code review plus a negative test "try to call generation directly" that must fail).
  4. **C0 uses the same interface**: under baseline the gate passes straight through, but it **goes through the same interface and writes the same event schema** (`condition = "C0"`, `blocked = false` always) — so both groups have identical log structure and metric definitions.
  5. **Fallback**: after rejecting or closing the card, the request can be edited and asked again; the state machine does not deadlock (covered by a test).

---

### M7 · Telemetry logger — **MUST**

- **Purpose**: be the only data source for every metric in §5.
- **Input**: event objects (see §4), `schema_version`.
- **Output**: `runs/<run_id>/logs/<participant_id>/<session_id>.jsonl`, appended line by line.
- **Dependencies**: the standard-library `json` module; no third-party dependencies.
- **Acceptance criteria**:
  1. Every line is valid JSON and passes schema validation; **on validation failure it refuses to write and raises** (no silent dropping, no half lines).
  2. `(session_id, seq)` is unique and strictly increasing; every `ts` carries a time-zone offset and never goes backwards within a session.
  3. **No PII**: a regex scan over all logs finds no name / email / student-number style string (the tests include both positive and negative cases).
  4. **Atomicity**: if the process is killed mid-write, the last line of the log file is either complete or absent (no half JSON).
  5. A line is ≤ 4 KB; array fields hold ≤ 20 entries, and anything beyond is truncated with the total recorded separately.
  6. **No raw text on disk (Q7)**: the schema contains no body-text field; wherever code or a prompt must be referenced, only `sha256` + `length` are written. The validator must **reject** events containing fields such as `text` / `content` / `body` / `prompt_raw`, with a matching test.
  7. **Retention is enforceable (Q7)**: a `purge --before <date>` command deletes run directories older than that date and prints the deletion list; the clean-up 90 days after submission runs through it. After deletion no `.jsonl`, `.jsonl.tmp` or backup file may remain in the directory, and re-running `analysis/` must explicitly report "which conclusions depend on deleted data".
  8. **`device` is a controlled enumeration (Q7)**: values may only come from `device_kinds` in `config/config.json`; `log.validate()` errors on a value outside that list, and the tests must cover "every legal value passes" and "host name / user name / company name / wrong case / empty string are all rejected". `session_start` fields are validated like the envelope, and are not skipped because it is the first event of the session.

---

### M8 · Outcome scorer — **MUST** (offline, lightweight JSON rule set)

- **Purpose**: turn "is this refactoring good" into a machine decision and remove human rating.
- **Input**: the repository snapshot at submission, the hidden test suite, `rules.json`, and the same metric baseline taken at task start.
- **Output**: `outcome {tests_pass, n_fail, failing_tests[], debt_delta, vuln_delta, lines_added, lines_removed, scorer_version}`; appends a `suggestion_scored` event (the post-hoc correctness label).
- **Rule set (per Q6, six fixed categories)**: `complexity` (function too long / branches too deep), `duplication` (duplicated blocks), `bare_except`, `hardcoded_secret`, `eval_usage`, `sql_concat`. Each rule has `rule_id`, `severity` and `weight`; `debt_delta` is the weighted count difference, and `vuln_delta` counts only the last three (`hardcoded_secret` / `eval_usage` / `sql_concat`).
- **Dependencies**: M1's hidden tests; `rules.json`; a subprocess sandbox.
- **Acceptance criteria**:
  1. The gold patch yields `tests_pass = true`; the unmodified repository yields the baseline result (**forbidden**: the situation where "even the gold patch fails", which would mean the tests themselves are broken).
  2. Metrics are "after submission − at task start", identical across repeated computations on the same repository (deterministic), and independent of file-walk order.
  3. `scorer_version` and the `rules.json` hash are written into every `task_end` and `suggestion_scored`.
  4. **Execution isolation**: tests of the repository under test run only inside a container / subprocess sandbox; on timeout they are killed and recorded (the session must not hang).
  5. **Every rule needs a positive and a negative test**: on a sample with the seeded smell the rule fires and `debt_delta` is positive; on a clean sample it is 0. A rule without this pair of tests counts as not implemented (so that rules cannot be decorative).
  6. The rule for `suggestion_scored.is_correct` is fixed as "do the hidden tests improve after this suggestion is applied", and that rule is written in the documentation rather than implied by the code.

---

### M9 · Analysis pipeline — **PLAN** (Q8: interface only, no data attached)

- **Purpose**: reproduce the report's tables and figures from the raw logs in one command.
- **Input**: `runs/**/*.jsonl`, the pre-registered analysis plan (the 5.2 table), `schema_version`.
- **Output**: `analysis/metrics.csv` (per observation), `analysis/results.xlsx` (summary tables), PNG figures, and `analysis/report.md` (with n, test name, effect size, CI, p).
- **Dependencies**: `pandas`, `scipy`, `statsmodels` (or `pingouin`); installed offline.
- **Acceptance criteria**:
  1. **Cell-for-cell agreement**: recomputed from the raw logs, values match the report's tables (tolerance 1e-9).
  2. **Auditable**: every statistical conclusion carries `n`, test name, effect size, 95% CI, p value and a note on missing-data handling.
  3. **Missing and unusual cases are explicit**: the output report must list excluded observations and the reason; silent dropna is not allowed.
  4. No dependence on runtime external state (network, clock, unseeded random numbers).

---

### M10 · Participant and compliance management — **N/A** (Q1: no human recruitment, not implemented; the design is kept for later use)

- **Purpose**: make consent, anonymisation and withdrawal verifiable processes rather than a promise.
- **Input**: informed consent (versioned tick), withdrawal requests, the demographics questionnaire.
- **Output**: consent records (version + timestamp + boolean), the pseudonym mapping table (in a separate restricted directory), a withdrawal execution report.
- **Dependencies**: no network; isolated from M7 (the log holds pseudonyms only).
- **Acceptance criteria**:
  1. Without a consent record M2 refuses to start the session (tested).
  2. No identifiable information appears in the logs or questionnaires (it shares the scan test with M7 item 3).
  3. Withdrawal completes in one command and prints a checkable report of "which files were deleted, which lines were flagged".
  4. The mapping table is physically separate from the logs (different directories, different access permissions).

---

### M11 · Development-provenance ledger and validator — **MUST**

- **Purpose**: deliver the "Convincingly" band of `Development evidence and authorship /20` directly — "distinguishes original, reused and assisted work, with relevant examples of reviewing and adapting AI output" `[A2]`. This is the **only criterion that does not depend on code quality and can be earned by bookkeeping alone**, so it gets its own module rather than being scattered through the README.
- **Input**: `docs/PROVENANCE.md` (a hand-maintained ledger), `git log`, the reuse list for `参考代码库/`.
- **Output**: a validation report (terminal summary `ok: <n> rows, <n> modules covered`) plus the ledger itself.
- **Ledger fields** (one per row): `item_id`, `module` (M1–M11), `origin` (original / reused / assisted), `source` (for reused/assisted: the repository path or tool name), `decision` (why I chose this), `check` (how I verified it), `commit`.
- **Dependencies**: local text and git history only; no network.
- **Acceptance criteria**:
  1. Every MUST module (M1/M4/M5/M6/M7) has at least 1 row, and all three `origin` values **appear at least once** — all rows set to original counts as a failure (it would mean no real distinction was made).
  2. Every `origin=assisted` row has a non-empty `decision` and `check`; a missing one fails (this is the "reviewing and adapting AI output" requirement).
  3. Every `origin=reused` row's `source` must point at a path that really exists in the workspace, otherwise it fails.
  4. The validator exits non-zero on failure and runs as one command before submission.

---

### 3.11 Module dependencies and global acceptance

Dependency direction (acyclic):

`M10 → M2 → M1 / M7`; `M1 → M4 → M5 → M6 → M7`; `M3 → M5`; `M6 → M3` (called only after unlocking); `M1 / M8 → M9`; `git log + ledger → M11` (M11 is read-only, with no outgoing edges).

Global acceptance (binding on every module, and reused directly as A2's "development evidence" `[A2]`):

1. **One command to run the tests**: one fixed command for the whole repository (for example `pytest -q`) passes.
2. **One command to self-check**: `--dry-run` mode runs the whole chain "task → card → gate → suggestion" without calling a real model or writing a real log, printing `ok: <n> tasks, <n> cards` (following the `--selftest` convention of the files in `参考代码库` `[REF]`).
3. **One command to reproduce**: clone from scratch → install dependencies → one command → results table.
4. **Zero magic numbers**: model names, thresholds (`τ_review`, `800 ms`, `20%`) and sample sizes all live in configuration files.
5. **No keys or endpoints committed**: the repository holds no API key, no endpoint and no account identifier (explicitly forbidden by `[A2]`; the delivered state must scan clean).
6. **Provenance is checkable**: the M11 ledger validates (see M11 acceptance).

---

## 4. Log schema

### 4.1 Files and write rules

- Format: **JSON Lines**, UTF-8 without BOM, one JSON object per line, line ending `\n`.
- Path: `runs/<run_id>/logs/<participant_id>/<session_id>.jsonl`.
- Append-only. **No post-hoc label may modify a historical line; it can only be appended as a new event** — that is why `suggestion_scored` exists.
- `schema_version` takes part in the comparison: on an unrecognised version the analysis pipeline must raise an error and must not guess.

### 4.2 Common envelope fields (present on every line)

| Field | Type | Required | Value / example | Notes |
|---|---|---|---|---|
| `schema_version` | string | yes | `"1.0.0"` | Semantic version |
| `event_id` | string | yes | `"9f1c0b7e-2a44-4c1e-9b1f-0d6a3e5c7b21"` | UUID v4, globally unique |
| `seq` | integer | yes | `21` | Strictly increasing from 1 within a session |
| `ts` | string | yes | `"2026-11-20T10:14:32.418+00:00"` | ISO-8601, **milliseconds + time-zone offset** |
| `session_id` | string | yes | `"S-01J9Z7K3"` | Session identifier |
| `participant_id` | string | yes | `"P07"` | **Pseudonym**; student number / email / name forbidden |
| `condition` | string | yes | `"C0"` / `"C1"` | Enum; `"C2"` appears only in PLAN documents and **must not appear in the log** (Q5) |
| `task_id` | string / null | yes | `"T-L02a"` / `null` | null during the `setup` and `end` phases |
| `task_index` | integer / null | yes | `0` | Index within the session, starting at 0 |
| `pair_id` | string / null | yes | `"PAIR-02"` | Paired-material identifier |
| `phase` | string | yes | `setup` / `prompt` / `card` / `gate` / `generate` / `review` / `test` / `quiz` / `survey` / `end` | Enum |
| `event_type` | string | yes | See 4.3 | Enum |
| `app_version` | string | yes | `"0.3.1+9c2a1f"` | git describe |
| `model_id` | string / null | yes | `"qwen2.5-coder:7b"` | In `replay` mode it must hold the real model name at recording time; null is allowed only for a hand-written mock (not used this round) |
| `model_temperature` | number / null | yes | `0.2` | Read from config |
| `seed` | integer / null | yes | `42` | Read from config |

### 4.3 Event types and private fields

| `event_type` | Private fields (type / values) |
|---|---|
| `session_start` | `consent_version` string; `consent_given` boolean; `prior_years` number; `llm_freq` enum(never/monthly/weekly/daily); `lang_familiarity` integer 1–5; `schedule_id` string; `device` **enum, values only from the `device_kinds` list in `config/config.json`** (default `author-workstation` / `reviewer-workstation` / `lab-workstation` / `unknown`); each entry must be a slug matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`, so a host name, user name, company name or any free-text device identifier cannot be written (Q7) |
| `prompt_submit` | `prompt_id` string; `prompt_len_chars` integer; `prompt_sha256` string; `attached_files` array<string> (≤20) |
| `generation_request` | `suggestion_id` string/null; `request_sha256` string; `mode` enum(mock/live); `latency_ms` integer; `tokens_in` integer/null; `tokens_out` integer/null |
| `suggestion_shown` | `suggestion_id` string; `suggestion_seq` integer; `n_files` integer; `n_lines_changed` integer; `n_hunks` integer; `rationale_len_chars` integer |
| `card_shown` | `card_id` string; `card_version` string; `n_items` integer; `n_required` integer; `latency_from_prompt_ms` integer; `impact_set_hash` string |
| `card_item_toggle` | `card_id` string; `item_id` string; `item_category` enum(global_var/cross_module_contract/side_effect/test_impact/other); `checked` boolean; `dwell_ms` integer |
| `gate_decision` | `card_id` string; `confirmed` boolean; `blocked` boolean; `n_required` integer; `n_confirmed` integer; `gate_latency_ms` integer |
| `explanation_open` | `suggestion_id` string; `layer` enum(L1/L2); `dwell_ms` integer |
| `suggestion_action` | `suggestion_id` string; `action` enum(accept/edit/reject/regenerate); `review_dwell_ms` integer; `edit_distance_lines` integer/null; `accepted_after_gate` boolean |
| `suggestion_scored` | `suggestion_id` string; `is_correct` boolean/null; `gold_patch_match` boolean; `scored_by` enum(hidden_tests/gold_diff/manual); `scorer_version` string |
| `test_run` | `task_id` string; `suite` enum(visible/hidden); `n_pass` integer; `n_fail` integer; `failing_tests` array<string> (≤20) |
| `task_end` | `elapsed_ms` integer; `submitted` boolean; `timeout` boolean; `tests_pass` boolean; `n_fail` integer; `debt_delta` number; `vuln_delta` integer; `lines_added` integer; `lines_removed` integer; `n_suggestions` integer; `n_accepted` integer; `n_edits` integer; `n_rejects` integer |
| `comprehension_item` | `quiz_id` string; `item_id` string; `answer` string; `correct` boolean; `response_ms` integer |
| `survey_response` | `instrument` enum(NASA_TLX/SUS/custom); `item_id` string; `value` number; `scale_min` number; `scale_max` number; `response_ms` integer |
| `session_end` | `total_elapsed_ms` integer; `n_tasks_completed` integer; `completed_all` boolean; `withdrawn` boolean |
| `integrity_event` | `kind` enum(mock_mismatch/schema_violation/crash_recovered/timeout_kill); `detail_len` integer; `ref_event_id` string/null |

### 4.4 Example lines (genuinely parseable, each line independent)

```json
{"schema_version":"1.0.0","event_id":"9f1c0b7e-2a44-4c1e-9b1f-0d6a3e5c7b21","seq":1,"ts":"2026-11-20T10:02:11.004+00:00","session_id":"S-01J9Z7K3","participant_id":"P07","condition":"C1","task_id":null,"task_index":null,"pair_id":null,"phase":"setup","event_type":"session_start","app_version":"0.3.1+9c2a1f","model_id":"qwen2.5-coder:7b","model_temperature":0.2,"seed":42,"consent_version":"2026-11-01","consent_given":true,"prior_years":3.5,"llm_freq":"weekly","lang_familiarity":4,"schedule_id":"SCHED-2026-11-A","device":"author-workstation"}
{"schema_version":"1.0.0","event_id":"4b8e2c11-77d0-4a2f-b1c9-5e3d9a0f6c12","seq":14,"ts":"2026-11-20T10:14:32.418+00:00","session_id":"S-01J9Z7K3","participant_id":"P07","condition":"C1","task_id":"T-L02a","task_index":0,"pair_id":"PAIR-02","phase":"card","event_type":"card_shown","app_version":"0.3.1+9c2a1f","model_id":"qwen2.5-coder:7b","model_temperature":0.2,"seed":42,"card_id":"CARD-0007","card_version":"1.0","n_items":4,"n_required":4,"latency_from_prompt_ms":1180,"impact_set_hash":"sha256:3f1a9c..."}
{"schema_version":"1.0.0","event_id":"c3a7d5e9-1f62-4b83-8d04-2a6b7e1f9c33","seq":15,"ts":"2026-11-20T10:14:33.006+00:00","session_id":"S-01J9Z7K3","participant_id":"P07","condition":"C1","task_id":"T-L02a","task_index":0,"pair_id":"PAIR-02","phase":"card","event_type":"card_item_toggle","app_version":"0.3.1+9c2a1f","model_id":"qwen2.5-coder:7b","model_temperature":0.2,"seed":42,"card_id":"CARD-0007","item_id":"CI-03","item_category":"cross_module_contract","checked":true,"dwell_ms":412}
{"schema_version":"1.0.0","event_id":"e2d6f4a8-3b15-4c72-9e60-7f8a1b2c3d44","seq":21,"ts":"2026-11-20T10:19:04.772+00:00","session_id":"S-01J9Z7K3","participant_id":"P07","condition":"C1","task_id":"T-L02a","task_index":0,"pair_id":"PAIR-02","phase":"review","event_type":"suggestion_action","app_version":"0.3.1+9c2a1f","model_id":"qwen2.5-coder:7b","model_temperature":0.2,"seed":42,"suggestion_id":"SUG-0007","action":"accept","review_dwell_ms":2650,"edit_distance_lines":null,"accepted_after_gate":true}
{"schema_version":"1.0.0","event_id":"7a9b3c2e-5d41-4f08-a7b6-9c0d1e2f3a55","seq":34,"ts":"2026-11-20T10:31:47.120+00:00","session_id":"S-01J9Z7K3","participant_id":"P07","condition":"C1","task_id":"T-L02a","task_index":0,"pair_id":"PAIR-02","phase":"test","event_type":"task_end","app_version":"0.3.1+9c2a1f","model_id":"qwen2.5-coder:7b","model_temperature":0.2,"seed":42,"elapsed_ms":1092512,"submitted":true,"timeout":false,"tests_pass":true,"n_fail":0,"debt_delta":-2.0,"vuln_delta":-1,"lines_added":37,"lines_removed":29,"n_suggestions":3,"n_accepted":2,"n_edits":1,"n_rejects":0}
```

### 4.5 Invariants (M7 must check them by machine)

1. Every line is valid JSON; one object per line; no nesting deeper than 3.
2. `(session_id, seq)` is unique and increases by 1.
3. `ts` always carries an offset and is non-decreasing within a session.
4. Enum values take only the lower-case values listed in 4.2/4.3; the `device` value set is given by `device_kinds` in `config/config.json`, and `log.validate()` must reject a value outside that list (including wrong case, an empty string, and free text such as a host name, user name or company name).
5. Unknown fields are allowed only with the `x_` prefix (forward compatibility).
6. Unknown values use `null`; **an empty string must not stand in for null**.
7. No source-code body and no prompt body (only `sha256` and the length); **there is no "store the raw text elsewhere" exception** (Q7); when the raw text is needed, look it up by hash.
8. A line is ≤ 4 KB; arrays hold ≤ 20 entries.
9. `session_start`'s own fields are validated like the envelope: a missing field, `null` in place of a required value, or a type mismatch must all raise (it must not be skipped for being the first event of the session).

### 4.6 Privacy boundary (Q7: store hash + length only, no raw text on disk, delete after 90 days)

- **No raw text on disk**: no source-code body, no prompt body; only `sha256` and `length` (in bytes). At schema level, fields such as `text` / `content` / `body` / `prompt_raw` are forbidden; when raw text is needed, look it up by hash in `recordings/` (M3) or in the repository snapshot, not in the log.
- **Data location**: all local; `runs/` sits outside the repository or is listed in `.gitignore` and **never enters Git**.
- **Retention**: **90 days** after submission, all run logs and recordings are deleted, executed by M7's `purge --before`, with the deletion list kept on record (so that what was deleted can be checked).
- **Pseudonyms**: the log holds only `participant_id`; the pseudonym mapping table is stored separately with its own permissions (with Q1's no-recruitment decision, the table would hold a single entry for the author). **This project has never built a mapping between pseudonyms and real identities**: `P01` is a placeholder for the script operator, not a code name for a real person; there is therefore no "mapping table leaked" risk and no identity information that could be restored.
- **Not recorded**: IP, full User-Agent, window titles, clipboard content; `device` allows only the controlled slugs in the configuration (such as `author-workstation`) and **not a host name, user name, company name or any free-text device identifier**.
- **Deletion is final**: `purge` is the only deletion entry point; after deletion no `.jsonl`, `.jsonl.tmp` or backup copy may remain.
- **The single controlled exception: `recordings/` (M3)**. Replay needs the model's raw input and output, so that directory keeps raw text; but its code and prompts all come from the **self-built corpus plus author self-testing** and contain no third-party data, so it can ship with the repository. **A recording from a human session must never enter that directory** and must be deleted the moment the session ends. This is where Q7 meets Q3/replay; if the project later turns to a human study, the decision must be retaken.

---

## 5. Metric → data → statistical method

> **Status of this section: planned analysis (PLAN).** Under the Q1/Q2 decisions, **no human data was collected**. 5.1–5.3 are the **pre-registered analysis plan**, explaining "how this would be computed if the experiment were run", and are labelled planned everywhere in the report and README `[A2]`. Only three readings are actually executable at the prototype stage, and they belong to **technical acceptance**, not to tests of H1–H7: `gate_decision.blocked` (did the gate really block generation), the comparison of `impact_set_hash` against gold (M4 acceptance), and the schema-validation pass rate (M7 acceptance).

### 5.1 Metric formulae (all depending only on §4 fields)

| Metric | Formula |
|---|---|
| Task completion time | `task_end.elapsed_ms` |
| Acceptance rate | `count(action = accept) / count(suggestion_action)` |
| Edit rate / rejection rate | the same, split by `action` |
| Blind acceptances | `count(action = accept ∧ accepted_after_gate = true ∧ review_dwell_ms < τ_review ∧ no matching explanation_open)` |
| OTI | blind acceptances / total suggestion actions |
| Discriminative AUC | `action ∈ {accept}` as 1, `{edit,reject}` as 0; `suggestion_scored.is_correct` as the label |
| Escaped-defect rate | `count(task_end.tests_pass = false ∧ submitted = true) / count(task_end)` |
| Technical-debt delta | `task_end.debt_delta` |
| Security-warning delta | `task_end.vuln_delta` |
| Comprehension score | `mean(comprehension_item.correct)` aggregated per task |
| Friction (cognitive load) | the NASA_TLX mental demand / effort / frustration dimensions in `survey_response`, rescaled to 0–100 |
| Usability | the 10 SUS items converted to 0–100 by the standard formula |
| Gate latency | `gate_decision.gate_latency_ms` |
| Tick interactions | `count(card_item_toggle)` aggregated by `card_id` |
| Mechanical-confirmation rate | `gate_decision` count meeting the 1.5 definition / total `gate_decision` count |
| Explanation-open rate | `count(explanation_open)` / `count(suggestion_shown)` |
| Gate blocks | `count(gate_decision.blocked = true)` |

### 5.2 Mapping table (pre-registered; no primary test may be added or removed afterwards)

| Metric | Data source (event.field) | Scale | Hypothesis | Statistical method | Effect size / reporting |
|---|---|---|---|---|---|
| OTI (H1) | `suggestion_action.action`, `review_dwell_ms`, `explanation_open` | per-participant proportion | paired | paired t test; if normality fails use **Wilcoxon signed-rank** (n<10 always Wilcoxon) | Cohen's d_z / rank-biserial r; 95% CI |
| Escaped defect (H2a) | `task_end.tests_pass` | paired binary | paired | **McNemar exact test** | odds ratio OR; discordant-pair count |
| Technical-debt delta (H2b) | `task_end.debt_delta` | paired counts (skewed) | paired | Wilcoxon signed-rank | median difference; r |
| Security-warning delta (H2c) | `task_end.vuln_delta` | paired counts | paired | Wilcoxon; if Poisson-like, GLMM(poisson) | rate ratio; 95% CI |
| Completion time (H3a) | `task_end.elapsed_ms` | paired continuous (right-skewed) | paired | log-transform first; paired t; otherwise Wilcoxon | geometric-mean ratio; d_z |
| Subjective friction (H3b) | `survey_response` (NASA_TLX three dimensions) | paired ordinal | paired | Wilcoxon (**never** a t test on ordinal data) | rank-biserial r; median difference |
| Discriminative AUC (H4) | `suggestion_action` × `suggestion_scored` | per-participant [0,1] | paired | paired t / Wilcoxon on AUC; report the acceptance rate as well, to test "is it merely accepting less" | ΔAUC; d_z |
| Comprehension score (H5) | `comprehension_item.correct` | per-task proportion | paired | Wilcoxon | median difference; r |
| Fatigue trend (H6) | `gate_latency_ms`, tick count × `task_index` | longitudinal | nested | **linear mixed-effects model**: fixed effect `task_index × condition`, random intercept per participant; whether the slope's 95% CI contains 0 | slope β and CI; marginal R² |
| Condition × complexity (RQ2 refinement) | `elapsed_ms` × `stratum` | longitudinal | nested | LMM interaction term; small-sample alternative **ART (aligned-rank transform) ANOVA** | interaction effect size; simple effects |
| C2 non-inferiority (H7, **not run**) | none (C2 not implemented) | — | — | **not tested**: Q5 decided against C2 | argued in the rationale only, as why it is the next step |
| Mechanical-confirmation rate (descriptive) | `gate_decision`, `card_item_toggle` | proportion | — | descriptive statistics + within-session trend plot | reported as **exploratory**, not in the primary test family |

### 5.3 Assumptions, multiple comparisons and missing data

- **Assumption checks**: Shapiro-Wilk (per group) plus homogeneity of variance (Levene); if violated, substitute a non-parametric test and mark the test actually used in the results table.
- **Multiple comparisons**: the primary test family is H1, H2a, H2b, H2c, H3a, H3b, H4, H5 (8 tests), corrected with **Holm–Bonferroni**; H6, H7 and all descriptive metrics are marked **exploratory**, reported separately, uncorrected, and explicitly labelled "exploratory".
- **Sample size and power**: see Q2. A rough calculation `[assumption]` A-11: for a paired design with two-sided α=0.05 and power=0.80, N=10 detects only a **large effect** of d_z≈0.9, while N=20 detects a **medium effect** of about d_z≈0.65; the exact values must be recomputed with a power-analysis script and written into the pre-registration.
- **Missing data**:
  - Withdrawals are kept under **ITT** for the log already produced; observations with `session_end.withdrawn = true` enter a sensitivity analysis (reported once with and once without them).
  - AUC is **undefined** when a participant shows only one decision class → record `null`; that participant does not enter H4's paired test, and the reason for the reduced `n` is reported.
  - Timed-out tasks are kept (`timeout = true`), included in the main analysis and excluded in the sensitivity analysis.
- **Outliers**: not deleted; report the sensitivity analysis with the top and bottom 5% removed.
- **What we will not do**: no p-hacking style trawling across metrics; no writing exploratory metrics up as confirmatory conclusions; if H3 shows "no cost", re-check the `gate_decision.blocked` count first (manipulation check) and only then interpret.

---

## 6. Open questions

### 6.0 Decided (2026-11-14)

| # | Decision | Direct consequence |
|---|---|---|
| **Q1** | **No human recruitment**; author self-testing plus recorded replay (SIM) instead, marked simulated in the report | M2 drops to SIM; M10 becomes **N/A**; H1–H7 are all **planned hypotheses** (no data); the report and README must not describe the work done as "subjects / participants / experiment shows" |
| **Q2** | **N=10 convenience sample**, statistics mainly Wilcoxon (the design and power are kept on record for N=10) | §5 as a whole drops to **planned analysis (PLAN)**; the 5.2 table is kept as pre-registration; the power figures in A-11 stay planned values and must not be written as measured |
| **Q3** | **Call the real API** (`live` mode), but **remove the API link, key and account at delivery and explain** how to supply your own key | M3 rises to MUST (live + replay); in the delivered state `replay` is the default and runs offline, so "reproduce in one command" is preserved; the zero-hit endpoint and key scan becomes 3.11 item 5 |
| **Q4** | **6 self-built seed repositories** (= 6 instances = 3 difficulty levels × 2, 3 `pair_id` pairs in total), no real open-source repositories | M1 delivers 6 repository snapshots + 6 hidden test suites + 6 gold patches + 6 impact-set label files; M8 can score automatically against gold; the drop in external validity must be written into the limitations in 2.6 |
| **Q5** | **Do not implement C2 adaptive granularity**; H7 is marked planned | The design reduces to **2 conditions (C0/C1) × 2 orders**; the C2 column in 2.1 stays only to show the design space and **must not appear in any implemented demo / storyboard**; in the 1,100-word rationale it appears only as "next work" |
| **Q6** | **A lightweight JSON rule set**: complexity, duplication, bare `except`, hardcoded secrets, `eval`, string-concatenated SQL — six categories | M8 rises to MUST; `debt_delta` is the weighted count difference and `vuln_delta` counts only the last three; every rule needs a positive and a negative test |
| **Q7** | **Store `sha256` + `length` only, no raw text on disk**; data stays local; **delete 90 days after submission** | 4.6 and M7 acceptance 6/7; the schema forbids body-text fields and the validator rejects them; `runs/` never enters Git; `purge --before` is the only deletion entry point |
| **Q8** | **Prototype first**: M1/M3/M4/M5/M6/M7/M8 really built; experiment orchestration and statistics marked planned | Delivery status table in 3.0; the 1,100-word rationale centres on design reasoning and scope trade-offs and **not on experiment results** |

> **Consistency note (must be stated explicitly in the report, or it becomes overclaiming)**: Q1 and Q2 taken together mean "there is an N=10 design, but no data was collected". The two do not contradict each other, but this must be explained — **N=10 is a design parameter and pre-registration basis kept on record, not a sample that was run**. Basis: the "Not yet demonstrated" band of `Developed interaction` says verbatim "materially misrepresents planned or simulated behaviour as implemented" `[A2]`. Likewise the "Convincingly" band of `Design reasoning and scope` requires the author to justify "compromises in scope" `[A2]` — "no recruitment, no C2" is exactly a scope trade-off to be argued, not a gap to be papered over.

### 6.1 Original question list (archive: all 8 decided)

The table keeps the questions as originally phrased, so that "why did we ask this" can be reviewed later. **The "default" column for all 8 is now superseded by 6.0** (Q7 was adopted from its default), and this table no longer holds an open question. If the project later turns to a human study, Q1, Q2 and Q7 must be reopened.

> Each row gave the default for "if you do not decide, this is how I will proceed", but a default is not a decision.

| # | Question | Why you must decide | Scope of impact | Default (before a decision) |
|---|---|---|---|---|
| **Q1** | **Is ethics review needed (REC / faculty approval)? Will real human participants be involved?** | A2 explicitly allows implementation / prototype / **simulation** / walkthrough as developed work `[A2]`; but recruiting real people makes it a human study, which usually needs approval, and it decides whether M10 and the whole session flow are lawful | Decides whether M2/M10 are MUST or PLAN; decides whether the §2 flow is executed | No human recruitment; author self-testing plus recorded replay (SIM), marked simulated in the report |
| **Q2** | **Sample size N and where participants come from?** | Directly decides which statistical methods are usable and whether a power analysis is possible; with N<10 only non-parametric tests plus description are possible | Decides the feasibility of 5.2 and the testability of H1–H5 | Design for N=10 (convenience sample), statistics mainly Wilcoxon |
| **Q3** | **Call a real LLM API?** Cost, model drift, data leaving the machine | Every conclusion in A1 rests on "real suggestion quality"; but real calls are not reproducible (A1 itself cites model behaviour differences) and involve keys and cost | Decides whether M3 is SIM or MUST; decides whether ecological validity can be claimed | Use record/replay: record a batch through the API first, then replay offline `[REF]` |
| **Q4** | **Task corpus: self-built seed repositories, or real open-source legacy repositories?** | Self-built is controllable (has gold patches and hidden tests) but has low external validity; a real repository has ecological validity but **no gold**, so M1 acceptance 2 cannot be met | Decides whether M1/M8 can be accepted | 6 self-built seed repositories (so scoring is possible) |
| **Q5** | **Implement C2 adaptive granularity?** | A1 §4 itself lists confirmation fatigue as a main limitation `[A1]`; implementing it answers RQ5 directly, but adds significant work and consumes rationale words | Decides whether H7 is a primary or a planned hypothesis; decides scope and the 1,100-word budget | Do not implement; mark H7 planned and argue in the rationale only why it is the next step |
| **Q6** | **Which tool or rule set for technical debt / security warnings? Is there installation permission?** | Something like SonarQube needs installation and licensing; a lightweight rule set runs offline but its validity is a proxy | Decides whether M8 acceptance 2 is achievable | A lightweight JSON rule set (complexity, duplication, bare except, hardcoded secrets, eval, string-concatenated SQL) |
| **Q7** | **Data retention and anonymisation: where do logs / screen recordings live, for how long, and may raw prompts and code be stored?** | Involves GDPR and university policy; it also decides how strictly 4.5's "no body text" is enforced | Decides M7's privacy implementation and M10's withdrawal flow | Store hash + length only, no raw text on disk, data local and deleted 90 days after submission |
| **Q8** | **A2 delivery main line: the full experiment (multiple participants + statistics), or "runnable governance prototype + simulated demonstration + experiment specification (planned)"?** | 60 of A2's marks sit in Design reasoning (30) and Developed interaction (30), and **experiment data is not a scored item** `[A2]`; spending effort in the wrong place pleases nobody | Decides whether M9 is MUST or PLAN; decides the centre of gravity of the 1,100-word rationale | Prototype first (M1/M4/M5/M6/M7 really built), experiment orchestration and statistics marked planned, with the reason written clearly in the report |

---

## 7. Assumption list (every `[assumption]` in this document, with its basis)

| ID | Assumption | Basis / consequence if overturned |
|---|---|---|
| A-1 | ~~The A2 marking rubric is not in the docx~~ **Void (2026-11-14)**: the updated docx, pages 5–6, now contains the four descriptor bands for the four criteria | 0.2 and §8 were rewritten accordingly. The only thing still missing is the band → mark mapping; see A-15 |
| A-2 | The experimental design itself is not an A2 requirement | A2 contains no experiment / statistics / participant wording `[A2]`; the experiment is a natural extension of A1 §4's contribution `[A1]` |
| A-3 | Blind-acceptance threshold `τ_review = 2000 ms` | A1 gives no threshold. 2 s was chosen because a review shorter than 2 s cannot have read a cross-module diff; 1/2/5 s sensitivity analyses reduce the risk of misclassification |
| A-4 | Paired-task comparability: the three structural metrics differ by ≤ 20% | No source; an engineering criterion for pairing validity. If a pair exceeds it, the pair is void and is rebuilt |
| A-5 | A 5-item comprehension quiz, testing architecture and contracts only | A1 is concerned with "impaired conceptual understanding" `[A1]`; 5 items are a compromise between session length and reliability, and the report must admit that reliability is unverified |
| A-6 | Mechanical-confirmation threshold: median tick dwell < 800 ms with no un-ticking | A behavioural proxy, no source; sensitivity analyses as for A-3 |
| A-7 | C0 must be "the same system with the gate switched off", not another product | Otherwise interface, latency and suggestion quality are all confounded and no difference can be attributed to governance. The comparison studies A1 cites are all the same tool under different conditions `[A1]` |
| A-8 | 2 tasks per person, one session ≤ 90 min | A feasibility compromise for a coursework project; the minimum testable within-subject configuration |
| A-9 | Impact-set recall = 1.0, precision ≥ 0.8 | recall = 1 is a governance-correctness requirement (a miss is a failure); 0.8 precision is the usability floor, so that the card is not drowned in noise |
| A-10 | A single impact analysis takes < 2 s | An empirical threshold for interactive fluency; exceeding it adds waiting and contaminates H3's time metric |
| A-11 | Rough power: N=10 → d_z≈0.9; N=20 → d_z≈0.65 | Paired t-test approximation `(z_{1−α/2}+z_{1−β})/√N`, computed by hand for two-sided α=0.05 and power=0.80; **must be recomputed with a script** before going into the pre-registration |
| A-12 | Project engineering conventions (Python 3.11+, runs offline, single LLM client, JSONL logs, `pytest` for acceptance) | Taken from the project conventions in the workspace `DSH-*` workflow note `[REF]`, **not a course requirement**; if they clash with your stack, yours wins |
| A-13 | record/replay is for **offline reproduction after delivery**, not a substitute for the real model | After Q3, live calls the real API; `replay` exists so that a reviewer can run everything with no key and no network (following the Lab 4 approach of `参考代码库/mock_model.py` + `recorded_runs/` `[REF]`) |
| A-14 | Hidden tests are invisible to participants | Otherwise a participant could edit specifically until the tests pass (Goodhart) and the escaped-defect metric would be void |
| A-15 | The four descriptor bands have **no** matching mark ranges (the docx gives only the maximum for each criterion: /30, /30, /20, /20) | The pages list only the four band texts and the maxima. Acceptance is therefore judged on "does it satisfy the Convincingly band description", with **no mark prediction**; if a mark table appears later, only the acceptance wording in §8 changes |
| A-16 | No data collection ⇒ H1–H7 have no observations and §5 is entirely planned analysis | The result of the Q1/Q2 decisions. Writing planned analysis as results hits A2's misrepresentation red line `[A2]` |

---

## 8. Traceability to the A2 scoring instructions

### 8.1 Scored criterion → Convincingly-band requirement → evidence in this project

Rewritten against the four descriptor bands in the updated docx of 2026-11-14. **Only the "Convincingly demonstrated" band is the target**, because the other three bands describe how marks are lost, not acceptance criteria.

| A2 criterion `[A2]` | Key requirement of the Convincingly band (wording in brief) | Evidence this project must produce | Section |
|---|---|---|---|
| Design reasoning and scope **/30** | Connect the design to the problem; argue the main choices, **major changes** and **scope trade-offs** with relevant evidence; **clearly separate developed from planned work** | The four-column rationale table (Design choice / Why it suits / Evidence / **Status**), every Status landing on one of implemented / simulated / planned; a separate paragraph arguing scope trade-offs (the reasons for no recruitment, no C2, no live API) | 2.1, 3.0, 6.0 |
| Developed interaction **/30** | The submission and the storyboards show a coherent "user action → system response → feedback or control"; **clearly distinguish implemented / simulated / unfinished** | 2–3 storyboards: the full C1 gated path, the C0 pass-through path, and the key branch "blocked when the required items are not all ticked"; each step marked implemented or simulated | 2.5, M5, M6 |
| Architecture and technical reasoning **/20** | The diagram and explanation show how components, flows and dependencies support the interaction, **including intelligent behaviour**; technical choices and boundaries **match the submission** | The System diagram uses M1–M11 and the 3.11 dependency directions; AI behaviour (M3/M4) is marked separately; the diagram must not show an unimplemented component without a label | 3.11, 3.0, M3, M4 |
| Development evidence and authorship **/20** | The development record connects major changes to **the student's decisions and checks**; distinguishes **original / reused / assisted** and gives examples of "reviewing and adapting AI output" | The M11 ledger (all three origin values present; assisted rows need decision + check) + the six README items + committed commits + one-command reproduction | M11, 3.11 |

### 8.1b Pre-submission self-check (each row maps to a specific way of losing marks)

| Self-check question | If the answer is "no" | Basis |
|---|---|---|
| Does every implemented described in the report actually run? | Hits the misrepresentation red line | `[A2]` Developed interaction |
| Does every simulated say "what was replaced and what the real part is"? | Judged "boundaries need clearer evidence" | `[A2]` same as above |
| Is every planned feature marked planned in the rationale? | Judged as counting planned work as developed work | `[A2]` Design reasoning |
| Is there a dedicated paragraph arguing scope trade-offs? | Judged "compromises in scope need explaining" | `[A2]` Design reasoning |
| Do the reused sources in the ledger point at real paths? Do assisted rows have decision + check? | Judged unable to separate the student's contribution from reused or assisted work | `[A2]` Development evidence |
| Do the components in the diagram match the real code boundaries? | Judged "discrepancies unexplained" | `[A2]` Architecture |

### 8.2 Word budget (hard constraint — exceeding it gets truncated)

| Part | Limit `[A2]` | Suggested allocation |
|---|---|---|
| Abstract | 300 | 250–280 |
| Design rationale | 1,100 (about 1,000) | 1,000–1,050, **keeping a 50-word buffer** |
| Total | 1,400; reading stops past 1,300 | ≤ 1,300 |
| Not counted | figures, diagrams, storyboards and their short labels / captions; references, repo links, README | Put the experiment details, schema, metric definitions and statistical methods **all in the README / repository docs**, where they cost no words |

> **One execution decision follows** `[A2]`: this SPEC (§3–5) ships as repository documentation (`docs/SPEC.md`); the A2 body says only "what choices were made, why, and where the evidence is", and points the reader to the repository. A2 explicitly allows the README to carry this material uncounted `[A2]`.

### 8.3 What is explicitly not in the scoring instructions (to prevent overfitting)

The following **does not** appear in A1 or A2 and is derived here; if questioned, cite §7 for the basis:

- The exact wording of all hypotheses H1–H7 and RQs RQ1–RQ5 (A1 has only gaps and a proposal, no formal hypotheses).
- The choice of the three primary DVs, `τ_review`, the mechanical-confirmation threshold, the pairing-comparability criterion and the impact-set acceptance thresholds.
- The statistical methods (Wilcoxon / McNemar / LMM / Holm) and α, power and the non-inferiority margin.
- Every field, event type and path rule of the log schema.
- The module split M1–M11 and its numbering (M11's ledger fields are an implementation device derived to satisfy A2's "distinguish original/reused/assisted"; A2 does not prescribe the field names).
- **The band → mark conversion**, and any judgement of the form "this earns X marks" — the docx gives the four band descriptors but no mark ranges (A-15). This specification judges only "is a band's description satisfied".

> Removed from this list: the earlier statement "the marking rubric is not in the docx" is void after the 2026-11-14 update; the four band descriptors are now `[A2]` verbatim and no longer count as derived here (see 0.2).

---

## Appendix: downstream files that must be updated in step

- `docs/PLAN.md`: the implementation plan and milestones for M1–M11, labelled MUST / SIM / PLAN / N/A (status in 3.0).
- `docs/rubric-mapping.md`: turn each row of 8.1 into an evidence row "requirement → file:line / test name", and self-check against 8.1b.
- `docs/PROVENANCE.md`: the M11 ledger itself, one row per item, recording original / reused / assisted.
- `AGENTS.md`: write the 3.11 global acceptance (one command for the tests, `--dry-run` self-check, zero magic numbers, no keys, checkable provenance) as the project constitution `[REF]`.
