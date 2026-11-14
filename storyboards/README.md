# Storyboard frames (M9)

Three frames, captured from the **running** server by `tools/make_storyboard.py`:
the script starts the real `govern.web` app on an OS-picked port, walks the same
HTTP calls a person would make, and photographs the page with headless Chrome.
They are not mock-ups or drawings; every pixel below came back from
`govern/web.py` after the step named in its caption.

Regenerate with:

```
python tools\make_storyboard.py          # needs Chrome or Edge installed
python tools\make_storyboard.py --check  # only verify the three files exist
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

## Honest limits of these frames

- **Author self-test, not participants.** Every run here is the author driving
  the UI against simulated recordings (`source: sim`). No human data exists
  (SPEC 0.2 red line).
- **The left pane is empty on purpose.** The request text is not stored (`Q7`:
  hash and length only), so a page reloaded from server state cannot redisplay
  what was typed. The caption says so instead of inventing a transcript.
- **No timings.** These are static frames; dwell times and gate latency come
  from the JSONL, not from the pictures.

Log for the C1 walk (from the capture run): `session_start` → `prompt_submit` →
`card_shown` → `card_item_toggle` ×2 → `gate_decision(blocked=true)` →
`card_item_toggle` ×3 → `gate_decision(blocked=false)`.
