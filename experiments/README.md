# `experiments/` — running the study, not just one session

`govern/` is the instrument: one task, one condition, one session, one JSONL.
This package is the bench around it: it reads an experiment file, expands it into
cells, runs them with a concurrency cap, isolates failures, resumes, and rebuilds
the metrics from the logs.

## One command, one table

```powershell
python -m experiments.run --config conditions.yaml
```

```
| condition | sessions | escape rate | mean debt Δ | OTI | mechanical |
|---|---|---|---|---|---|
| C0 | 6 | 1.00 | -3.67 | 0.00 | 0.00 |
| C1 | 6 | 1.00 | -3.67 | 0.00 | 1.00 |

ok: 12 ran, 0 skipped, 0 failed of 12 → runs\E-SIM-01
```

That is the whole reproduction path: the file fixes the conditions, the task set,
the participants and the concurrency; everything the row depends on is written
into `runs/E-SIM-01/` before the first session starts. Nothing above comes from a
table typed by hand — `metrics.json` is recomputed from the 12 JSONL files with
`python -m experiments.run --config conditions.yaml --resume` (0 sessions run,
same numbers) or `python -c "from experiments import metrics; import json;
print(json.dumps(metrics.rebuild('runs/E-SIM-01'), indent=2))"`.

**Read the table for what it is.** The operator here is a script, not a person:
it ticks every card box at once, accepts the suggestion and never opens an
explanation. So `escape rate = 1.00` and `OTI = 0.00` are properties of the script
plus a shipped suggestion that deliberately omits one consumer file — not
findings about governance. What the table does prove is that the pipeline
computes each metric from logs and keeps the two conditions comparable. Anything
about people needs a human operator (`--port`, still `planned`).

## The experiment file

`conditions.yaml` is a YAML *subset* — nested mappings, block or inline lists,
comments, quoted strings, `int`/`float`/`bool`/`null` scalars. JSON is accepted
as-is. Tabs and anything outside the subset are rejected with a message rather
than guessed at (`experiments/spec.py`): a plan that is silently misread is worse
than one that refuses to start.

```yaml
version: 1
run_id: E-SIM-01
participants: [P01]
conditions:
  baseline:
    condition: C0
  governance:
    condition: C1
pairs: [PAIR-01, PAIR-02, PAIR-03]
repetitions: 1
concurrency:
  max_parallel: 2
```

The file defines **structure only**. `model_id`, `temperature`, `seed`, the metric
thresholds and the app version stay in `config/config.json` — one home per
parameter (AGENTS §2.4). Each run copies the effective values into
`runs/<run_id>/config.snapshot.json` and `manifest.json`, so the numbers stay
traceable even after the config changes.

## What a run directory contains

```
runs/E-SIM-01/
  config.snapshot.json   the experiment file plus every config value in force
  manifest.json          model_id, model_temperature, seed, mode, task_order, n_cells
  logs/<participant>/<session_id>.jsonl    one line per event (SPEC 4.2/4.3)
  metrics.json           derived cache; delete it and it is rebuilt from logs
  failures.jsonl         only if something failed — one line per failed cell
  work/<session>/<task>/ throw-away checkouts used to apply patches
```

Task order is recorded, not implied: `manifest.json.task_order` lists the task ids
in the order the cells were scheduled, so "which came first" is answerable later.

## Behaviour worth knowing

| Concern | How it works |
|---|---|
| Concurrency | `concurrency.max_parallel` (or `--workers`). Sessions are independent; each writes its own log file and its own `work/` checkout. |
| Resume | `--resume` skips a cell only when its log **ends with `session_end`**. A crash mid-session leaves the cell pending, so it is re-run rather than counted as done. |
| Failure isolation | A cell that raises is recorded in `failures.jsonl` (cell, task, condition, error class, message truncated to 300 chars) and the batch continues. Exit code `1` means "ran, with failures"; `2` means "never started". |
| Metrics | Rebuilt from logs every time (`experiments/metrics.py`); `metrics.json` is never the source. `--json` prints it. |
| Self-check | `--dry-run` validates the file, resolves the task set, prints the plan and writes nothing. |

## What the metrics mean

All of these read the same JSONL written by `govern/log.py`; SPEC 5.2 is the
definition of record.

| Metric | Source | Definition |
|---|---|---|
| `escape_defect_rate` | `task_end.tests_pass` | share of sessions that ended with a failing hidden suite |
| `mean_debt_delta` | `task_end.debt_delta` | mean weighted smell count after − before (see `config/rules.json`) |
| `oti` | `suggestion_action` + `explanation_open` | blind accepts / suggestion actions; blind = accept, after the gate, `review_dwell_ms < tau_review_ms`, no explanation opened |
| `mechanical_share` | `gate_decision` + `card_item_toggle` | share of confirmations whose median toggle dwell was below `mech_dwell_ms` **and** that confirmed the full set |
| `blocked_attempts` | `gate_decision.blocked` | how often generation was attempted before the card was complete |

`tau_review_ms` and `mech_dwell_ms` come from `config/config.json`. They are used
here and nowhere else, which is why this package is the only consumer of those two
parameters.

## Tests

```powershell
python -m pytest tests\test_experiments.py -q
```

24 tests: the YAML subset (including the cases it must reject), spec validation,
cell expansion and ordering, snapshot/manifest contents, resume, failure
isolation, metric arithmetic on synthetic logs, and the CLI.
