# Deliverable compliance check (A2 Project Report)

This file maps the course marking instructions, item by item, to the evidence in the repository, and separately checks four cross-cutting requirements: **ethics**, **reproducibility**, **data leakage** and **dependency locking**.

- Subject: the working tree submitted as `HEAD` (148 tracked files before submission, 2 added by this check), Python 3.15.0 on this machine, pytest 9.2.0, 19 commits.
- There are only three verdicts: **Satisfied** / **Partly satisfied** / **Not satisfied**. A "partly satisfied" always names the missing half; otherwise the verdict is useless.
- Every conclusion comes with a reproducible command or a file location. Anything I could not verify is in §8, not mixed into a verdict.
- Revision of 2026-11-24: the report was rebuilt around six numbered sections with Figures 1–4 inside the .docx (system diagram, three interaction frames). Counts are now abstract 219 / main report 1,080 / total 1,299, and the "diagram is a sibling file" gap recorded below is closed.

---

## 0. One-line conclusion

**The engineering deliverables are complete, and the assessed report now carries the architecture and interaction evidence inside it: Figure 1 is the system diagram and Figures 2–4 are interaction frames.**

All four criteria now have substantive evidence — the design decisions, the interaction implementation and frames, the architecture and interfaces, and development provenance — and the report supplies the abstract, the ~1,000-word rationale, the four-column table, the references and the first-page word count. The report is now six numbered sections: abstract (219 words), design rationale with Table 1 (1,080 words), the system and its two flows with Figure 1, three illustrated interactions in §4, scope, and repository evidence. Captions sit below each figure and, like the reference list, are excluded from the word count, as the instructions specify. Therefore:

| Criterion | Points | Verdict | What was / is missing |
|---|---|---|---|
| Design reasoning and scope | /30 | **Satisfied** | Previously: no report chapter, no rationale table, no course concepts. Now: `docs/A2_Report_3138100.docx` §2 (main report 1,080 words), Table 1 (7 data rows, four columns), six concept citations; `docs/course-concept-evidence.md` |
| Developed interaction | /30 | **Satisfied** | Previously: no report interaction section and no reject path. Now: report §4 shows three interactions as four frames (Figures 2–4), including the reject path with a byte-identical working copy; `storyboards/` holds the same four frames with their README |
| Architecture and technical reasoning | /20 | **Satisfied** | Report §3 embeds `System diagram/system-diagram.png` as Figure 1 and explains the components, the control and evidence flows, and the `Client` boundary where the model sits; `System diagram/README.md` carries per-box and per-edge evidence tables; `python tools/make_diagram.py --check` → `ok: 13 stages match the source` |
| Development evidence and authorship | /20 | **Satisfied** | None (see 2.4). |

Deliverable checklist: storyboards, the system diagram and the repository/README are satisfied, and the report now contains the abstract, the rationale, the four-column table, Figures 1–4, the references and the first-page word count. All seven items are present inside the report itself; the placement gap that this file recorded for §2.3 is closed.

---

## 1. Verdict overview

| # | Requirement | Source | Verdict | Evidence |
|---|---|---|---|---|
| 1 | Abstract ≤ 300 words | Marking instructions | **Satisfied** | `docs/A2_Report_3138100.docx`: abstract 219 words; `python tools/word_count.py --docx=docs/A2_Report_3138100.docx --check` → `ok: the stated counts match the text and are within the limits` |
| 2 | Design rationale ~1,000 words (limit 1,100) | Marking instructions | **Satisfied** | Report §2: main report 1,080 words including Table 1's cells, under the 1,100 limit |
| 3 | Four-column rationale table (Design choice / Why / Evidence / Status) | Marking instructions | **Satisfied** | Report Table 1: `Design choice` / `Why it fits` / `Evidence` / `Status`, 7 data rows |
| 4 | System diagram (boxes + arrows, marked implemented/simulated/planned) | Marking instructions | **Satisfied** | Figure 1 in the report is `System diagram/system-diagram.png` (1300×960), whose legend marks implemented, simulated and planned; `System diagram/README.md`; `python tools/make_diagram.py --check` → `ok: 13 stages match the source` |
| 5 | Storyboards, 2–3 use instances | Marking instructions | **Satisfied** | Report §4: three examples from `storyboards/1-c1-gate-closed.png`, `2-c1-gate-open.png` (one example, two frames), `3-c0-baseline.png` and `4-c1-reject.png`, each with caption and a stated action → response → feedback; `storyboards/README.md` |
| 6 | Repository + README + submitted commit/release + development record | Marking instructions | **Satisfied** | 19 commits; `README.md:84` dual version marker; `README.md:109` development record |
| 7 | References (including reused material) | Marking instructions | **Satisfied** | The report's `References` section has 6 entries; reused material is recorded in `docs/PROVENANCE.md` |
| 8 | Total word count on the first page | Marking instructions | **Satisfied** | The report's first page says `Word count: 1299 total (abstract 219, main report 1080)` |
| 9 | README explains AI use | Marking instructions | **Satisfied** | `README.md:128` |
| 10 | Mark placeholders/unfinished work; never describe planned work as implemented | Marking-instruction red line | **Satisfied** | `docs/SPEC.md` §3.0 status table (MUST/SIM/PLAN/N/A); `README.md` Project status three-way split |

---

## 2. The four rubric criteria

### 2.1 Design reasoning and scope (/30) — Satisfied

The marking instructions' Convincingly band asks for four things: ① connect the design to the problem; ② use evidence to justify the **main choices**; ③ justify **significant changes and compromises in scope**; ④ **clearly distinguish** developed from planned work.

| Requirement | Status | Evidence |
|---|---|---|
| ① Design ←→ problem | Present | `docs/SPEC.md` §1 (RQ/H1–Hn), §2 (C0/C1 conditions); the gap between blind trust and pre-emptive governance in the A1 literature is mapped directly onto C1's mandatory confirmation card; report §1–§2 |
| ② Main choices evidenced | Present | `docs/rubric-mapping.md` maps each rubric item to requirement, evidence and test name; the report's Table 1 gives the choice, the reason, the source and the status for seven choices |
| ③ Significant changes and scope compromises | Present, and **strong** | Eight decisions are recorded in `docs/SPEC.md` §6.0 (Q1–Q8); Q8's "prototype first" is an explicit scope compromise; `docs/rubric-mapping.md` §5 records each deviation from the plan with its reason (including `Check.detail`, `summarise(tolerance)`, `recordings/<slug>`). Report §2 and §3 carry the two scope compromises that matter: replay instead of live calls, and no human study this round |
| ④ Developed/planned distinction | Present | `docs/SPEC.md` §3.0; `README.md` Project status; report §5 and Table 1's `Status` column |
| **The artefact the marking instructions ask for** | **Present** | `docs/A2_Report_3138100.docx`: abstract 219, main report 1,080, total 1,299; Table 1 has 7 data rows in four columns; Figures 1–4 are image parts with captions; 6 references; the total word count is on the first page |
| **Naming W1–4 concepts** | **Present** | `docs/course-concept-evidence.md` maps the design decisions to lecture slides with page numbers (`W4 L12 p.5`, `p.8`, `p.12`, `p.16`, `W2 L06 p.6`, `p.10`, `W3 L07 p.12`, `W2 L05 p.8`, `W1 L03 p.12`, `W2 examples p.19`, `W3 L09 p.9`); the report cites six of them |

**This was the most expensive gap, and it is closed.** The marking instructions say "Name the concept or guideline and explain how it informed your decision rather than simply listing terms". The report now does that in §2 and Table 1 for six choices, and `docs/course-concept-evidence.md` is the page-level mapping behind them. The earlier statement that the repository had zero mentions of course concepts is no longer true. Nothing remains for this criterion: the prose, the table and the concept citations are all in the report.

The mapping that the report and the evidence file use:

| Decision | Course concept and where it is evidenced |
|---|---|
| The five card items are **never pre-ticked** | Recognition over recall (`W2 L05 p.8`); `docs/course-concept-evidence.md` marks the confirmation-fatigue half as literature-based, not lecture-based |
| The blocked alert lists **statement text**, not `item_id` | Name the object (`W4 L12 p.12`); show what was heard (`W2 L06 p.10`) |
| `Generate` is **disabled** until the gate opens, with a reason | Error prevention over correction and the gulf of execution (`W2 L06 p.4`, `p.5`, `p.6`, `p.10`); feedback (`W3 L07 p.12`) |
| The C0 empty-state copy | Make the system's limits visible (`W1 L03 p.12`) |

### 2.2 Developed interaction (/30) — Satisfied

The Convincingly band asks the submitted artefacts and storyboards to show **coherent user actions, system responses and feedback or control**, and to **clearly distinguish implemented / simulated / unfinished** behaviour. The "Not yet" red line is describing planned or simulated work as implemented.

| Requirement | Status |
|---|---|
| A genuinely interactive submission | **Present.** `static/index.html` + `govern/web.py`; 22 tests exercise a real loopback (`tests/test_web.py`) |
| Storyboard with 2–3 instances | **Present.** Four frames are generated by `tools/make_storyboard.py` from the real server: C1 blocked → C1 open → C0 baseline → C1 reject. They are not hand-drawn |
| Per-frame action / response / log sequence | **Present.** `storyboards/README.md` maps each frame to the log event numbers |
| Implemented / simulated / unfinished distinction | **Present.** The page carries a permanent "Author self-test run (simulated)" banner; `README.md` and the SPEC status table use the same three-way split |
| Red-line risk | **None.** No replay is described as a real model; no scripted operator is described as a participant |
| **Gap 1** | **Closed.** Report §4 shows the three interactions the requirement asks for: gate closed → gate open (Figures 2a and 2b), the baseline without a card (Figure 3) and the rejection (Figure 4), each caption naming the developer's action, the system's response and the feedback or control state; `storyboards/README.md` carries the frame-by-frame record |
| **Gap 2** | **Closed.** `storyboards/4-c1-reject.png` + `4-c1-reject.promises.txt` cover the refusal path: `suggestion_action(action=reject)`, with the working copy left byte-identical |

**What was missing versus what now exists.** The report chapter now exists: §4 takes a reader through three interactions with four frames, and the first paragraph states in one sentence that the frames come from sessions the script drove and that no person was involved. The rejection path has a frame and a promise file. The remaining risk is presentational only: the narrow panes in the captures are empty because nothing has been generated yet, which the Example 1 paragraph explains.

### 2.3 Architecture and technical reasoning (/20) — Satisfied

The Convincingly band asks the diagram and its explanation to show how **components, flows and dependencies** support the interaction (**including intelligent behaviour**), and to keep technical choices and boundaries consistent with the submission. The "Partly" descriptor is "lists components without explaining connections or role, or unexplained discrepancies".

| Requirement | Status | Evidence |
|---|---|---|
| Components and interfaces | Present | `docs/PLAN.md` §4 gives each module's signature; `govern/` has 15 modules with stated responsibilities |
| Data flow | Present (text) | `docs/PLAN.md` §5: task → impact set → card → gate → suggestion → score → JSONL |
| Dependencies and rationale | Present | Zero third-party runtime dependencies; `requirements-dev.txt` pins pytest only |
| Where the intelligent behaviour is | Present | `govern/llm.py` dual mode (replay/live), recordings indexed by request sha, model consistency check |
| **System diagram** | **Present inside the report** | Figure 1 of `docs/A2_Report_3138100.docx` (14.6 cm wide, `word/media/image1.png`, the same 1300×960 PNG), cited and explained by report §3; `System diagram/README.md` with per-box and per-edge evidence tables; `python tools/make_diagram.py --check` → `ok: 13 stages match the source` |

**What now exists.** The earlier gap — "no system diagram", then "diagram not in the report" — is closed twice over: the figure exists with 13 stages, its README ties each box and edge to the source, and the .docx now contains it as Figure 1 with a caption and a paragraph that names the components, the control flow (task → analyser → card → gate → client), the evidence flow (every step → JSONL → runner → analysis) and the `Client` boundary that keeps the model behind one interface. The status legend on the figure itself separates implemented, simulated and planned, so a marker reading only the .docx sees the architecture and its boundary.

### 2.4 Development evidence and authorship (/20) — Satisfied

The Convincingly band asks the development record to tie significant changes to **the student's decisions and checks**, to distinguish **original / reused / assisted**, and to give **examples of reviewing and rewriting AI output**.

| Requirement | Status | Evidence |
|---|---|---|
| Changes tied to decisions and checks | Present | 19 commits, each message saying what changed and why; `README.md:109` development record |
| original/reused/assisted three-way split | Present, enforced line by line | `docs/PROVENANCE.md` 32 rows, `original=10 / reused=3 / assisted=19`; `govern/provenance.py` requires every assisted row to have a decision + check; `-` does not count |
| Examples of reviewing and rewriting AI output | Present, several | See the list below |
| Sources can be checked | Present | `reused` rows point at real paths under `参考代码库/`; the checker requires the source to be declared, and an `external:` source must carry a decision |

**The self-corrections already on record** (this is the strongest evidence for this criterion; it is not retrospective packaging):

1. The first version of the card rendered its checkboxes as `checked disabled` — which would have built the "mechanical confirmation" failure mode from A1 into the interface → changed to never pre-ticking, and pinned with `test_html_never_renders_a_pre_ticked_checkbox`.
2. `corpus._run_hidden` depended on pytest, so bare Python violated "one command to run the tests" → extracted the `govern/hidden.py` subprocess runner.
3. `provenance._filled()` treated a markdown `-` as content, so "delete the check and it still passes" → judged it empty, and added a test.
4. The README claimed 210 words (a hand count, wrong; measured 886) → added `tools/word_count.py --check` and covered it in `tests/test_end_to_end.py`.
5. `_statement()` still exceeded the 120-character limit after falling back → hard truncation.

**Why this verdict is "Satisfied"**: the evidence lives in README and PROVENANCE; the report only needs to **cite** them, not rewrite them.

---

## 3. Cross-cutting check one: ethics

### 3.1 Informed consent

| Check | Result | Evidence |
|---|---|---|
| No consent, no start | **Satisfied** | `Session.start()` in `govern/session.py` raises `ConsentError`; `tests/test_session.py::ConsentTests` |
| Consent state in the log | **Satisfied** | `session_start` records `consent_given: true` and `consent_version: "SIM-AUTHOR"` |
| Consent **text** and process | **Not satisfied** | The repository has no consent form, no information page and no withdrawal statement |
| Ethics approval | **Not applicable / not recorded** | No human participants this round, so no approval; the report's abstract already states that the frames come from an author self-test, so a reader is not led to assume real participants |

Verdict: **Partly satisfied**. The mechanism is right; the paperwork is not. Because Q1 decided not to recruit humans, the actual risk is zero; the report now says clearly that the frames come from a scripted author self-test, and `consent_version=SIM-AUTHOR` is the marker. What is still missing: a consent text, an information page and a withdrawal statement. None is needed for this round; all three would be needed before a human study.

### 3.2 Anonymisation

| Check | Result | Evidence |
|---|---|---|
| Participant identifiers are pseudonyms | **Satisfied** | `participant_id` only ever holds `P01`…`P10` |
| No direct identifiers (name/email/IP/UA) | **Satisfied** | The full log field set is in 4.1; the scanner is 12/12 clean |
| No pseudonym↔identity mapping file | Satisfied (none exists), but **no written statement** | Recommend one sentence in the report: "no mapping is stored, so the data cannot be traced back to a person" |
| Deletion entry point and retention period | **Satisfied** | `python -m govern.log --purge --before <date>`; `retention_days: 90` |

Verdict: **Satisfied** (for the existing data), with one statement still recommended.

---

## 4. Cross-cutting check two: data leakage (do participant details enter the log?)

### 4.1 What is actually in the log

The complete field set of line 1 of `runs/E-SIM-01/logs/P01/S-baseline-P01-T-L01a-r0.jsonl`:

```
schema_version event_id(random UUID) seq ts phase event_type
session_id(S-<condition>-<participant>-<task>-r<n>) participant_id(P01) condition(C0|C1)
app_version model_id model_temperature seed
task_id(null) task_index(null) pair_id(null)          ← session-level events do not repeat task fields
consent_version("SIM-AUTHOR") consent_given(true)
prior_years(0.0) llm_freq("never") lang_familiarity(5)  ← self-reported covariates
schedule_id("EXP-E-SIM-01") device("author-workstation")
```

**Not present**: name, email, student number, IP, User-Agent, window title, clipboard, free text (the prompt is stored only as sha256 and length).

### 4.2 Measured scan

```
python -m govern.log --scan <each jsonl>      → 12/12 files "ok: 0 identifying string(s)"
python -m govern.log --validate <one file>    → "ok: 11 line(s) checked, 0 invalid"
python tools\scan_secrets.py                 → "ok: 0 finding(s) in 176 files"
```

Verdict: **Satisfied**.

### 4.3 Two hardening recommendations

1. ~~`device` is **free text**~~ → **Fixed**. `device` is now a controlled enum: its value may only come from `device_kinds` in `config/config.json` (`author-workstation` / `reviewer-workstation` / `lab-workstation` / `unknown`), and each value must be a slug matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`. `config.load()` and `log.validate()` both reject values outside the list (including the hostname `DESKTOP-3F2A9C`, the username `alice-laptop`, a company name, a case mismatch, and the empty string). This also fixed a real defect: `validate()` used to return early for `session_start`, so that event's fields were never validated — and `device` sits on exactly that event, so without the fix the rule would not have taken effect. See SPEC 4.2/4.5 items 4 and 9 and M7 acceptance 8; evidence: `DeviceKindTests`, `SessionStartCoverageTests`, `DeviceVocabularyTests`.
2. `prior_years` / `llm_freq` / `lang_familiarity` are self-reported covariates and therefore quasi-identifiers (with a small sample they could help re-identify a person). This round they are constant, so the risk is zero; a human study should bucket them into ranges.

---

## 5. Cross-cutting check three: reproducibility (one command from zero)

### 5.1 How it was measured

`git clone` is **unavailable** in this machine's sandbox (`sh.exe: fatal error - couldn't create signal pipe, Win32 error 5`), so I used the equivalent path: export the full tree of `HEAD` with `git archive --format=zip` (185 entries, **no `.git`**), unpack it into a clean directory, and run with **bare `python`** (not `.venv`):

```
python -m govern.run --selftest
python -m experiments.run --config conditions.yaml
python -m analysis.run --runs runs --run-id E-SIM-01 --out analysis
```

All three passed, producing `runs/E-SIM-01/` (12 JSONL files + `manifest.json` + `config.snapshot.json` + `metrics.json`), `analysis/results.xlsx`, `analysis/captions.md`, and 4 PNGs. **No network, no API key, no third-party runtime dependency.**

### 5.2 But "reproducible" has to be layered, or it is a lie

| Layer | Reproducible? | Why |
|---|---|---|
| Process (the three commands run) | **Yes** | Measured in 5.1 |
| Funnel counts (events, ticks, failed tests, debt/vulnerability counts) | **Yes** | Replaying the recordings is deterministic |
| Byte-level log | **No** | `ts`, `event_id` (UUID) and `elapsed_ms` (wall clock) differ every time |
| Statistical output (same run) | **Yes** | Recomputed from the same log; `results.xlsx` is byte-identical (tested) |
| Statistical output (after re-running the experiment) | **No** | Measured: the original `runs/` gives a `Task time` difference of −2.33, p=0.058, 0 survive; the exported tree gives −5.00, p=0.035, 1 survives |

**This must go into the report**: in this setup `elapsed_ms` is the script's wall-clock overhead, so it drifts on a re-run, and the significance of task time must **not** be reported as a finding. What is stable is the funnel metrics — and this round they are fixed by construction (both conditions receive the same replayed suggestion), so the difference is always 0.

### 5.3 Another reproducibility gap

`--batch --participant P01` gives one condition per pair, so all six sessions are unpaired. It used to print an empty table and `exit 0`, which looked like "it finished and found no difference". **Fixed during this check** (see §6).

### 5.4 One command (P2 is done)

`tools/reproduce.ps1` strings the three commands from 5.1 and the four self-checks from AGENTS §5 together, stopping at the first non-zero step:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\reproduce.ps1
```

Measured on the clean tree exported by `git archive`: the success path prints `ok: 6 of 6 steps passed` (exit 0; 12 JSONL files, `results.xlsx`, 4 PNGs, 6 transcripts and `reproduce.json` all land under `_repro/<timestamp>/`); after making `config/config.json` invalid JSON it prints `FAILED at step 1: self-check: standard-library test suite` (exit 1, later steps do not run); re-running into the same `-OutDir`, or into `-OutDir ...\runs\x`, is refused (exit 2). **Adding this script exposed three real problems** (see §6 rows 6–8).

---

## 6. What this check fixed along the way

| # | Problem | Fix | Evidence |
|---|---|---|---|
| 1 | A one-sided run printed an empty table and `exit 0`, disguising a design error as "no difference" | `Analysis.paired_counts`; `run._build()` writes no output when there is no pair; `main()` prints `fail: … no task ran in both conditions …` and `exit 1` | `tests/test_analysis.py::StudyTests::test_a_run_with_no_complete_pair_is_refused` |
| 2 | In the table, p and the status marker stuck together (`0.035struct`) | Fixed-width separator column | `python -m analysis.run …` table |
| 3 | `tools/make_storyboard.py` carried a UTF-8 BOM, so `compile()` raised `SyntaxError: invalid non-printable character U+FEFF` | Removed the BOM; added a test to prevent recurrence | `tests/test_dependencies.py::SourceEncodingTests` |
| 4 | "Zero third-party runtime dependencies" was only a claim, with no test | Added `tests/test_dependencies.py`: an AST scan of imports in `govern/`, `analysis/`, `experiments/`, `tools/` allows only the standard library and local packages; asserts there is no `requirements.txt` | 9 tests green |
| 5 | Test-time dependencies were not locked | Added `requirements-dev.txt`, pinning `pytest==9.2.0` exactly, with a workaround note for machines where pip is unavailable | Same `DevRequirementsTests` |
| 6 | `DEFAULT_PATH` in `govern/config.py` was a **relative path**, so the config followed the current directory: the clean-tree run read the workspace's `config/config.json`, and the "break the config and it must fail" check had never actually taken effect | Changed it to `Path(__file__).resolve().parent.parent / "config" / "config.json"`; `tools/reproduce.ps1` does `Push-Location $Root` in every step | Breaking the config inside the tree gives `FAILED at step 1`; `python -m unittest discover` still `OK` |
| 7 | `govern.provenance --check` required every `reused` source to exist on disk, but `参考代码库/` is excluded by `.gitignore` ⇒ **the check was guaranteed to fail on a clean checkout** (dragging four tests down with it) | Added the `external:` prefix: an explicit "source outside the workspace" marker, whose row **must** still carry a `decision` or it errors | 3 new tests in `tests/test_provenance.py`; clean tree `ok: 29 rows` (the ledger is now 32 rows, §9) |
| 8 | The fixture in `tests/test_provenance.py` pointed at `参考代码库` (absent on a clean checkout) ⇒ the tests could only pass on my machine | The fixture now uses `docs/` and `docs/does_not_exist.py` | Clean tree: 446 tests green |

---

## 7. Remaining work (ordered by value for effort)

| Priority | Item | Why | Acceptance |
|---|---|---|---|
| ~~P0~~ **Completed** | Write the report body: abstract (≤300 words), rationale (≈1,000 words, max 1,100), four-column table, references, first-page total word count | It was the **only direct score gap**; the material was ready, only assembly was missing | `docs/A2_Report_3138100.docx` exists; `python tools/word_count.py --docx=docs/A2_Report_3138100.docx --check` → `ok: the stated counts match the text and are within the limits`; total 1,299 on the first page |
| ~~P0~~ **Completed** | Name **W1–4 course concepts** in the rationale, one sentence per decision ("concept → how it influenced the decision") | The marking instructions require it; the repository previously had zero mentions | `docs/course-concept-evidence.md`; the report cites six concepts with slide pages |
| ~~P1~~ **Completed** | System diagram (one figure) | The marking instructions name it; Architecture needs it for Convincingly | `System diagram/system-diagram.png`, 1300×960; `System diagram/README.md` per-box and per-edge tables; `python tools/make_diagram.py --check` → `ok: 13 stages match the source`; now Figure 1 inside the report (§2.3) |
| ~~P1~~ **Completed** | Add a fourth storyboard: rejecting a suggestion / abandoning mid-way | The marking instructions ask for "feedback **or control**"; the control surface had no frame | Done: `storyboards/4-c1-reject.png` + `4-c1-reject.promises.txt` (`suggestion_action(action=reject)`, working tree byte-identical) |
| ~~P2~~ **Completed** | Make `device` an enum; state in the report that no pseudonym mapping is stored | The two hardening items in 4.3; required before any human study | Done: `config.device_kinds` + `log.validate()` rejects values outside the list; SPEC 4.6 states "no mapping between pseudonyms and real identities was ever created" |
| ~~P2~~ **Completed** | `tools/reproduce.ps1`: combine the three commands from 5.1 and the four self-checks into one | "One command to reproduce" was three commands | Done: `powershell -NoProfile -ExecutionPolicy Bypass -File tools\reproduce.ps1` → `ok: 6 of 6 steps passed`; stops at the failing step and prints its name and exit code; refuses an existing `-OutDir` and refuses to write into `runs/` or `analysis/` |
| ~~P3~~ **Completed** | Add hashes to the dev dependencies (`--require-hashes`) or vendor the wheels | Only the pytest main version was pinned; transitive dependencies were not | Done: `requirements-dev.txt` now pins 9 packages (pytest + 8 transitive dependencies, split by environment marker) and lists the sha256 of **all 81 files** of each release (both wheel and sdist, because pip chooses by platform). Each file was downloaded and compared with the index digest: 81/81 match, none yanked. **`pip install --require-hashes` cannot run on this machine** (pip's temporary unpack directory is not writable in the sandbox, `PermissionError`), so three substitute checks were used: ① all 81 sha256 values equal the index digests; ② the 512 installed files in `.venv` are byte-identical to those wheels (the environment that runs the 446-test suite is exactly the pinned set); ③ `pip install --dry-run --no-index --require-hashes -r requirements-dev.txt` passes parsing and pinning (it fails only because `--no-index` has no package to install). On a machine that can write a temporary directory, `pip download --require-hashes -r requirements-dev.txt -d tmp` is the equivalent check |

---

## 8. What I did not verify

An honest list, so this file is not read as "everything was verified":

1. **It has not run on a clean machine.** It ran on an exported tree on this machine only; there was no second machine and no non-Windows system.
2. **No human has used the UI.** All four frames come from a headless-Chrome-driven script (`tools/make_storyboard.py`); I have not clicked through it with a mouse, and I ran no usability observation.
3. **`live` mode has never called a real external model API.** It was verified only against the loopback `_Stub` server in `tests/test_llm.py`.
4. **Concurrency pressure was not tested.** `max_parallel: 2` ran only at small scale (12 sessions).
5. **The rubric's band→score mapping is unknown.** The marking instructions give only the four band descriptors and a total, not how bands map to marks, so this file judges "which band it falls in", not a predicted score.

## 9. Final delivery audit (evening of 2026-11-14)

The last run before delivery; commands and outputs are copied verbatim. Any failing line means the check did not pass.

| # | Required check | Command | Result |
|---|---|---|---|
| 1 | Standard-library test suite | `python -m unittest discover -s tests -q` | `Ran 446 tests in 40.283s` / `OK (skipped=2)` / exit 0 |
| 2 | One-command self-check | `python -m govern.run --selftest` | `ok: 6 tasks, 6 cards` / exit 0 |
| 3 | Secret and endpoint scan | `python tools/scan_secrets.py` | `ok: 0 finding(s) in 176 files` / exit 0 (`_repro/` is excluded; otherwise the number would change with every audit run) |
| 4 | Provenance ledger | `python -m govern.provenance --check` | `ok: 32 rows, 11 modules covered (original=10, reused=3, assisted=19)` / exit 0 |
| 5 | One-command reproduction | `powershell -NoProfile -ExecutionPolicy Bypass -File tools\reproduce.ps1` | `ok: 6 of 6 steps passed` / exit 0 (written to `_repro/20261114-232213/`; `runs\`, `analysis\`, `dist\` untouched) |

The table produced by the reproduction step (different from the repository's own `runs/E-SIM-01`; see §5.2):

| condition | sessions | escape rate | mean debt Δ | OTI | mechanical |
|---|---|---|---|---|---|
| C0 | 6 | 1.00 | -3.67 | 0.00 | 0.00 |
| C1 | 6 | 1.00 | -3.67 | 0.00 | 1.00 |

The paired test for `Task time` gave `diff = -6.33`, `p = 0.036` this time, with `multiplicity: 1 tests, 1 survive Holm at alpha=0.05`; the repository's own run gave `p = 0.058` (0 survive). The four runs gave 0.058 / 0.036 / 0.036 / 0.035 — **same code, same configuration, only the wall-clock sample differs** — and Holm's verdict flips with it, so this measure is neither stable nor citable. The report's §5 has been rewritten to say so.

Delivery snapshot: `python tools/make_release.py --build` → `dist/a2-1.0.0.zip` (161 entries, 696,791 bytes, `sha256:07651cd4ac339adc4a23104abb5541b5591dda4883bf7fffce2464989266b40c`, the tree of commit `d616cd9`), `--verify` passes, and two builds have the same hash. The text recording this hash is itself inside the archive, so rebuilding after this point necessarily gives a different hash — for a check, see the self-reference note in `docs/rubric-mapping.md` §2j.

**Still unverified**: all five items in §8 still stand (clean machine, human use of the UI, a real `live` API call, concurrency pressure, band→score mapping); plus `pip install --require-hashes` cannot run on this machine (the substitute evidence is in §7's P3 row). **This section does not claim** that any human study or real model call has been completed.

---

## 10. Report rebuild (2026-11-24)

The report was restructured around the six sections the marking instructions name, and the four figures were moved inside the .docx:

| # | Check | Command | Result |
|---|---|---|---|
| 1 | Report rebuild | `C:\Python315\python.exe tools/make_report.py` | `abstract 219 words, main report 1080 words, total 1299 words` / `wrote docs/A2_Report_3138100.docx` (304,215 bytes, 5 media parts) |
| 2 | Stated counts match the text | `python tools/word_count.py --docx=docs/A2_Report_3138100.docx --check` | `ok: the stated counts match the text and are within the limits` |
| 3 | Report tests | `python -m unittest tests.test_report -q` | `Ran 11 tests ... OK` — including `test_the_shipped_report_matches_a_fresh_build` |
| 4 | Figures reachable | render the .docx | 6 pages; Figure 1 (system diagram) on p.3, Figures 2a/2b on p.4, Figures 3 and 4 on p.5, section 5, section 6 and the complete reference list on p.6 |

Open risk recorded honestly: the two figures that show the closed and open gate (2a/2b) have an empty diff pane, because nothing has been generated yet in that condition; Example 1's paragraph says so in one sentence rather than leaving the reader to guess.

Scope boundary of this rebuild: `dist/a2-1.0.0.zip` is the release snapshot of an earlier tree and therefore carries the earlier report. Rebuilding it would change the digest quoted in README.md (§Version identification and its development record), `docs/rubric-mapping.md` §2j and `docs/PLAN.md`, so the archive is left as the record of that tree; the assessed report is `docs/A2_Report_3138100.docx` in the working tree.

Environment note, because it will not reproduce elsewhere: on this machine `docs/` denies the `.venv` interpreter (`PermissionError: [Errno 13] Permission denied: '...docs\A2_Report_3138100.docx.part'`) while the system interpreter writes it, so the rebuild used `C:\Python315\python.exe` and the tests and checks ran under `.venv\Scripts\python.exe`. This does not affect a reader or a marker: the `.docx` ships in the repository, and `tests/test_report.py` rebuilds it in memory to prove the file matches its generator.
