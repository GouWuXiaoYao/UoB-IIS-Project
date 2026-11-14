# AGENTS.md — project rules

This repository is the implementation of the A2 governance prototype. The specification is
[docs/SPEC.md](docs/SPEC.md); the implementation order is [docs/PLAN.md](docs/PLAN.md).
**No change may break the six hard rules in this file.**

## 1. Runtime environment

- Python **3.11+** (3.15.0 measured on this machine).
- **Zero third-party runtime dependencies**: the standard library only. A code path that needs
  `pip install` to run is forbidden.
- Without git, a `SHA256SUMS` snapshot stands in for the commit identity; `app_version.txt` is the
  version source (it falls back to `config/config.json`).

## 2. Six non-negotiable rules

1. **One command to run the tests**: `python -m unittest discover -s tests -q`. The project uses
   `unittest` throughout; pytest is a test-time tool only (see `requirements-dev.txt`) and it also
   discovers unittest cases, so the two do not conflict.
2. **One command to self-check**: `python -m govern.run --selftest`, printing something like
   `ok: 6 tasks, 6 cards`.
3. **One command to reproduce**: `python -m govern.run --batch --schedule config/schedule.json`,
   in `replay` mode by default, **with no network and no key**. The single command that runs both
   reproductions and the self-checks is `tools/reproduce.ps1`; `--batch` also needs `--participant`.
4. **No magic numbers**: every threshold, model name, temperature, seed and sample size may appear
   only in `config/*.json`. Such a literal in code is a defect.
5. **No keys, no endpoints**: `sk-`, `api_key`, `token=`, `https://` must not enter the repository.
   The key is read from the environment variable `A2_API_KEY` only; it is never written to a file,
   never logged, never screenshotted.
6. **Every experiment run must write JSONL**: one `<session_id>.jsonl` per session, one event per
   line, fields as in [docs/SPEC.md](docs/SPEC.md) 4.2–4.3. The log is the only data source;
   metrics may only be recomputed from it.

## 3. Module conventions

- The package root is `govern/`, flat, entered through `python -m govern.run`.
- Every module provides `--selftest` (called as `python -m govern.<module> --selftest`), prints
  `ok: ...` and returns 0.
- Modules interact only through public functions and data classes; no module reads another's
  private attributes.
- LLM calls may appear **only** in `govern/llm.py`; every other module goes through `Client`.

## 4. Logs and privacy

- Logs hold **hash + length only**, never the raw text (Q7). The validator must reject fields such
  as `text` / `content` / `body` / `prompt_raw`.
- `runs/` is never committed; the retention period is `retention_days` (90 days) and
  `govern.log --purge` is the only way to delete.
- `recordings/` is the controlled exception for replay: it may hold only recordings made from the
  built-in corpus and from author self-testing; **recordings of human sessions must never enter
  that directory**.

## 5. Pre-submit checks

1. `python -m unittest discover -s tests -q` is green.
2. `python -m govern.run --selftest` prints what it should.
3. `python tools/scan_secrets.py` reports zero findings.
4. `python -m govern.provenance --check` passes (in force since M10).
5. New or changed behaviour has a test; when fixing a defect, write the failing test first.

## 6. Forbidden

- Never describe planned or simulated behaviour as implemented (the marking red line; see SPEC 0.2).
- Never claim in the report or the UI that human data was collected — this round is author
  self-testing plus recorded replay.
- Never relax an acceptance threshold to look finished; if something cannot be done, downgrade it
  honestly and record that in `docs/`.
