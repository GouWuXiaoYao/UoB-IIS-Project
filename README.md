# A2 — Interactive governance prototype for AI-assisted legacy refactoring

This repository implements the programme specified in [docs/SPEC.md](docs/SPEC.md), in the order
given by [docs/PLAN.md](docs/PLAN.md). The grading evidence trail lives in
[docs/rubric-mapping.md](docs/rubric-mapping.md), and the development record in
[docs/PROVENANCE.md](docs/PROVENANCE.md).

**Status:** milestones M0–M10 are implemented and verified; M11 (end-to-end freeze and release
snapshot) is the only one left. Milestone numbers in `PLAN.md` are not module numbers in
`SPEC.md`; the mapping is in `PLAN.md` §1.

What is **implemented**: the seed corpus, the AST impact analyser, the assessment card, the
mandatory confirmation gate, the replay LLM client, the six-rule outcome scorer, the telemetry
logger, the session orchestrator with deterministic assignment, the local web UI, and the
provenance checker. What is **simulated**: model output, which is served from recordings whose
`source` field says `sim` — no external API is called and no key is needed. What is **planned**:
the analysis pipeline (`SPEC` M9) and the human study (Q1/Q2 — designed, never run).
**No human data has been collected.** Every session in this repository was run by the author.

Prose word count of this README: **946 words**, counted by `python tools/word_count.py` with this rule:
blank lines, fenced code blocks, table rows and this paragraph are excluded, everything else counts
(headings and list bullets included). An earlier version claimed 210 words from a hand count; the tool
says 889, so the earlier figure was wrong rather than counted differently. `python tools/word_count.py
--check` fails whenever the stated number and the text disagree, and the check is itself a test.

## How to run

Only the standard library is needed at runtime (Python 3.11+; verified on 3.15.0).

```powershell
python -m govern.run --selftest            # ok: 6 tasks, 6 cards
python -m govern.corpus --check            # ok: 6 tasks, gold 6/6, pairs 3/3 within 20%
python -m govern.impact --selftest         # ok: recall=1.00 precision=1.00 on 6 tasks
python -m govern.llm --selftest            # ok: 6 recordings, 10 replays each, no network used
python -m govern.log --selftest            # ok: 16 event types, seq from 1, atomic append
python -m govern.score --selftest          # ok: 6 rules with positive and negative fixtures
python -m govern.session --selftest        # ok: 10 participants, 6 slots each, deterministic
python -m govern.web --selftest            # ok: 6 routes wired
python -m govern.provenance --check        # ok: 21 rows, 11 modules covered
python -m unittest discover -s tests -q    # standard-library test runner
```

A single self-test run, end to end:

```powershell
python -m govern.run --session S-001 --task T-L01a --condition C1 --participant P01
python -m govern.run --session S-001 --task T-L01a --condition C1 --participant P01 --port 8000
```

The second form serves the same session over `http://127.0.0.1:8000`; the page reloads state from
the event log, so an interrupted session can be resumed with `--resume`.

One experiment, one table (the `experiments/` layer runs both conditions over the same task set):

```powershell
python -m experiments.run --config conditions.yaml --dry-run   # plan only, writes nothing
python -m experiments.run --config conditions.yaml             # 12 sessions -> runs/E-SIM-01/
python -m experiments.run --config conditions.yaml --resume    # only the cells that never ended
```

`metrics.json` is recomputed from the JSONL logs, not accumulated in memory, so deleting it and
re-running `--resume` reproduces the same numbers.

The analysis layer turns those logs into a result table, four figures and paste-ready captions:

```powershell
python -m analysis.run --runs runs --run-id E-SIM-01 --out analysis   # results.xlsx + figures/ + captions.md
python -m analysis.run --selftest                                     # statistics checked against known answers
```

`pytest` is a **test-time** dependency only (installed into `.venv/`, not committed).
If it is available: `python -m pytest -q`.

## Technology stack

- Python 3.15.0, standard library only. No web framework, no ORM, no LLM SDK at runtime.
- `http.server` + one HTML file for the UI; plain `unittest` for tests.
- The LLM is behind `govern/llm.py` with two modes: `replay` (default; reads committed
  recordings, no network, no key) and `live` (optional; reads `A2_API_KEY` from the environment).
  Nothing in this repository has ever called a real model API.
- Git for Windows could not be installed on this machine (`winget` returns `-1978335231`, the
  installer places no files), so Git runs from MinGit 2.56.1 unpacked into untracked `_tools/git`.

## Version identification

Two identifiers, because neither alone is enough here:

1. **Git history** — real commits; `git log --oneline`.
2. **Checksum snapshot** — each release is also a ZIP with a `SHA256SUMS` manifest, so a reviewer
   without Git can verify which bytes were assessed:

   ```powershell
   python tools\make_release.py --build    # dist/a2-1.0.0.zip + dist/SHA256SUMS
   python tools\make_release.py --verify   # re-hash the archive and compare
   ```

   The archive is reproducible: a second build of the same tree hashes identically, so the digest
   identifies the work rather than the machine that packed it. `dist/` is not committed; rebuild it.
   This file therefore does not quote a digest for "now" — it would go stale the moment this line
   changes the tree. Quoted digests are historical: `2f2ea5d2…` is the 123-file tree frozen at M11,
   `b2fbc378…` the 131-file tree once `experiments/` was added. For the commit you are reading, run
   `--build` and use the digest it prints.

   The archive is defined by an allowlist (`PAYLOAD_DIRS` and `PAYLOAD_FILES` in
   `tools/make_release.py`), so a new top-level directory has to be added there to ship. That is
   deliberate: walking the whole tree once pulled a stray temporary file into the archive, and an
   unreadable one made the build fail outright.

   The `govern/` system was frozen at `00fdf92` (123 files,
   `sha256:2f2ea5d2…`). Later commits add `experiments/`, `analysis/`, the report and the
   provenance rows, so the archive of the tree you are reading is larger — rebuild it rather than
   trusting a number quoted here. Rebuilding an earlier commit reproduces that commit's hash.

## Development record

Significant changes, why they were made and what checked them are recorded in three places:
`git log --oneline` (one commit per milestone), `docs/PROVENANCE.md` (per-item ledger with
`origin = original | reused | assisted`, the decision and the check), and
`docs/rubric-mapping.md` (each acceptance test mapped to a named test case).

Two examples of reviewing and changing AI output, both caught by tests or by reading the result:

- The card first rendered every checkbox as `checked disabled`, which reproduces the "mechanical
  confirmation" failure the literature warns about. It is now never pre-ticked, and
  `tests/test_card.py::test_html_never_renders_a_pre_ticked_checkbox` keeps it that way.
- The hidden-test runner called `pytest`, so `python -m unittest discover` failed on a bare
  Python install. `govern/hidden.py` now runs suites in a standard-library child interpreter.
- The experiment layer's first tables looked like a finding ("escape rate 1.00, no over-trust")
  until I read the logs: the operator is a script that ticks every box and accepts at once. The
  README of `experiments/` now says plainly that those columns show the metrics can be computed,
  not that governance works.

## AI assistance

AI tools were used throughout. This assistant generated first drafts of the code, tests and
documentation; the author set the scope (SPEC Q1–Q8), reviewed every draft, and changed what was
wrong. Concretely, the author's interventions were: the eight scope rulings, the decision to keep
`replay` as the only shipped mode, the "no pre-ticked boxes" rule, the removal of the pytest
dependency, replacing item IDs with statements in the blocked message, and the fixes recorded in
`docs/PROVENANCE.md` rows P-003, P-005, P-007, P-011, P-014, P-015 and P-017. Output was verified
by running the commands above, not by inspection alone.

## Repository layout

| Path | Contents |
|---|---|
| `govern/` | the system under test: config, tasks, run, patch, corpus, impact, card, gate, llm, log, score, hidden, session, web, provenance |
| `corpus/` | six seed legacy repositories, hidden suites, gold patches, impact labels |
| `tools/` | generators: `make_repo.py` (corpus), `make_recordings.py` (replay), `make_storyboard.py` (screenshots), `scan_secrets.py` |
| `static/` | `index.html`, the only UI file |
| `experiments/` | the harness around the instrument: `spec.py` (condition file), `runner.py` (bounded parallelism, resume, failure isolation), `metrics.py` (recompute from logs), `run.py` (CLI), `conditions.yaml` |
| `analysis/` | the statistics on top of the logs: `load.py`, `checks.py`, `stats.py`, `report.py`, plus hand-written `xlsx.py` and `png.py` (no third-party packages) |
| `storyboards/` | three captured interaction frames and a frame-by-frame script |
| `tests/` | 384 test cases across 21 modules |
| `config/` | every threshold, seed, rule and model id — no magic numbers in code |
| `docs/` | `SPEC.md`, `PLAN.md`, `PROVENANCE.md`, `rubric-mapping.md` |

Course material (`参考代码库/`, the assignment briefs) is input rather than delivered work; it is
acknowledged as reused material in `docs/PROVENANCE.md` (rows P-002, P-010, P-018).
