# Storyboard frames (M9)

Four frames, captured from the **running** server by `tools/make_storyboard.py`:
the script starts the real `govern.web` app on an OS-picked port, walks the same
HTTP calls a person would make, and photographs the page with headless Chrome.
They are not mock-ups or drawings; every pixel below came back from
`govern/web.py` after the step named in its caption.

> **Author self-test, not a participant session.** Every frame comes from a
> scripted operator (`participant_id = P01`) replaying recordings whose
> `source` is `sim`; `consent_version` in the log reads `SIM-AUTHOR`. No human
> took part, no model was called, and no network was used. Nothing here is
> human-subject data (SPEC 0.2 red line), so these frames cannot be reported as
> evidence of how people behave.

Regenerate with:

```
python tools\make_storyboard.py          # needs Chrome or Edge installed
python tools\make_storyboard.py --check  # four frames exist, and frame 4's evidence agrees
```

## 1. `1-c1-gate-closed.png` — C1, two of five confirmed

- **What the person did:** sent the refactoring request, then ticked two of the
  five card items.
- **What the system did:** listed all five impact items (`cross_module_contract`,
  `global_var`, `side_effect`, two `test_impact`), counted `2 of 5 confirmed`,
  raised the `role="alert"` block naming the three outstanding items **by
  statement, not by id**, and left *Generate suggestion* disabled.
- **Why it matters:** the request to generate while the gate is closed was made
  for real and answered `409 gate_closed`; the refusal is in the log as
  `gate_decision(blocked=true)`.

## 2. `2-c1-gate-open.png` — C1, all five confirmed

- **What the person did:** ticked the remaining three, then pressed *Confirm and
  allow generation*.
- **What the system did:** cleared the alert, counted `5 of 5 confirmed`, and
  enabled *Generate suggestion*. Nothing has been generated yet — confirmation
  permits the next step, it does not perform it.

## 3. `3-c0-baseline.png` — C0 baseline

- **What the person did:** sent the same request in the baseline condition.
- **What the system did:** showed *No assessment card in this condition —
  generation is not gated*, with *Generate suggestion* enabled immediately.
- **Why it matters:** C0 is the control arm. The comparison in the report is
  between this and frame 1, so C0 has to be a genuinely ungated path rather than
  a disabled copy of the card screen.

## 4. `4-c1-reject.png` — C1, the suggestion is refused

This is the **control path**: the frame where the person declines what the model
proposed. It is the path the report's "the developer stays in charge" claim rests
on, so it is the one frame whose evidence is written down next to the picture.

- **What the person did:** with the gate open, generated a suggestion, read it,
  and pressed *Reject* (`POST /api/act {"action": "reject", "dwell_ms": 2400}`).
  Then finished the task without submitting a patch (`POST /api/end
  {"submitted": false}`).
- **What the system did:** showed the suggested diff, then replied
  `Suggestion rejected; the working copy is untouched.` and left the working copy
  byte-identical; the hidden suite still fails (`n_fail=2`), because nothing was
  applied.
- **The log events this frame corresponds to** (`storyboards/4-c1-reject.promises.txt`
  holds the full extract):

| seq | event | evidence it carries |
|---|---|---|
| 13 | `suggestion_action` | `action=reject`, `accepted_after_gate=True`, `review_dwell_ms=2400` |
| 16 | `task_end` | `submitted=False`, `n_accepted=0`, `n_rejects=1`, `tests_pass=False`, `n_fail=2` |

- **What was checked mechanically:** every file in the session's working copy was
  hashed before the refusal and after it — 5 files, 0 changed, 0 added — and the
  capture run reported `work_tree_identical=True`. `--check` re-reads that claim
  and fails if it is absent, so the frame cannot survive a change that makes
  *reject* start touching the tree.
- **Why it matters:** the accept path is easy to fake — a page that always applies
  the patch would look fine in frames 1–2. This frame is the one that shows the
  opposite outcome is reachable, and that refusing costs the score rather than
  buying it.

## Honest limits of these frames

- **Author self-test, not participants.** Every run here is the author driving
  the UI against simulated recordings (`source: sim`). No human data exists
  (SPEC 0.2 red line).
- **The left pane is empty on purpose.** The request text is not stored (`Q7`:
  hash and length only), so a page reloaded from server state cannot redisplay
  what was typed. The caption says so instead of inventing a transcript.
- **No timings.** These are static frames; dwell times and gate latency come
  from the JSONL, not from the pictures. Frame 4's `review_dwell_ms=2400` was the
  value the capture script sent, not a measured human pause.
- **One session per frame pair.** Frames 1, 2 and 4 come from a single C1 session
  (`S-SB-C1`), so the card id is stable across them; frame 3 is a separate C0
  session (`S-SB-C0`) and therefore has a different card id.

Log for the C1 walk (from the capture run): `session_start` → `prompt_submit` →
`card_shown` → `card_item_toggle` ×2 → `gate_decision(blocked=true)` →
`card_item_toggle` ×3 → `gate_decision(blocked=false)` → `generation_request` →
`suggestion_shown` → `suggestion_action(reject)` → `test_run` →
`suggestion_scored` → `task_end(submitted=false)`.
