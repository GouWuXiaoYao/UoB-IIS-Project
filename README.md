# A2 — Interactive governance prototype for AI-assisted legacy refactoring

This repository implements the experiment programme specified in [docs/SPEC.md](docs/SPEC.md),
in the order given by [docs/PLAN.md](docs/PLAN.md). The grading evidence trail lives in
[docs/rubric-mapping.md](docs/rubric-mapping.md).

**Status:** in progress — milestones M0 (skeleton) and M1 (seed corpus) are implemented and
verified; M2–M11 are not. Nothing here has collected human data: the prototype is exercised by
the author and by recorded replay (`SIM`), never by participants.

## How to run

Only the standard library is needed at runtime (Python 3.11+; verified on 3.15.0).

```powershell
python -m govern.run --selftest          # ok: 2 tasks, 0 cards
python -m govern.corpus --check          # ok: 2 tasks, gold 2/2, labels 2/2
python -m unittest discover -s tests -q  # standard-library test runner
```

`pytest` is a **test-time** dependency only. If it is available:

```powershell
python -m pytest
```

## Version identification — commit **and** checksum snapshot

Two independent identifiers are kept, because neither alone is sufficient here:

1. **Git history.** The repository has real commits (`git log --oneline`). Git for Windows could
   not be installed system-wide on this machine — `winget` returns `-1978335231` and the Inno
   installer exits without placing any files, both inside the sandboxed session. Git is therefore
   used from **MinGit 2.56.1**, unpacked into `_tools/git` and put on `PATH` per shell:

   ```powershell
   $env:PATH = "<repo>\_tools\git\cmd;$env:PATH"
   git log --oneline
   ```

   `_tools/` is deliberately **not committed**; it is local tooling, not project content.

2. **Checksum snapshot.** From M11 on, every release is also published as a ZIP with a
   `SHA256SUMS` manifest, so a reviewer without Git can verify exactly which bytes were assessed:

   ```powershell
   Get-FileHash -Algorithm SHA256 .\dist\<release>.zip
   ```

   A reviewer may cite the commit **or** the snapshot; both identify the same tree.

## Repository layout

| Path | Contents |
|---|---|
| `govern/` | the system under test: `config`, `tasks`, `run`, `patch`, `corpus` |
| `corpus/` | seed legacy repositories, hidden suites, gold patches, impact labels |
| `tools/` | generators (`make_repo.py`) that rebuild `corpus/` deterministically |
| `tests/` | pytest/unittest suite |
| `config/` | every threshold, seed and model id — no magic numbers in code |
| `docs/` | `SPEC.md` (what is being built), `PLAN.md` (in what order), `rubric-mapping.md` (evidence) |

Course material (`参考代码库/`, the assignment briefs) is intentionally excluded from the
repository: it is input, not delivered work, and is acknowledged as reused material in the report.
