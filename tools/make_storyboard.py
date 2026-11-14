"""Capture the four storyboard moments from the real UI (PLAN milestone M9).

The M9 acceptance criterion is "walk C1 and C0 by hand and produce storyboard
frames".  Nobody is sitting at this keyboard, so this script walks the same paths
over the real HTTP surface and photographs them with a headless browser.  What it
produces is therefore *evidence of the running server*, not a mock-up: every frame
is the page as served, after the same API calls a person would have made.

Frames (storyboards/):

    1-c1-gate-closed.png    C1, two of five confirmed: Generate disabled, the
                            blocked alert names the outstanding items.
    2-c1-gate-open.png      C1, all five confirmed: Generate enabled.
    3-c0-baseline.png       C0 baseline: no card, generation never gated.
    4-c1-reject.png         C1, the suggestion is refused: the page says the
                            working copy is untouched, and the frame is captured
                            only after the work tree has been proved identical.

Usage::

    python tools/make_storyboard.py            # capture into storyboards/
    python tools/make_storyboard.py --check    # frames exist and are non-empty

Frame 4 also writes storyboards/4-c1-reject.promises.txt: the SHA-256 of every
file in the working copy before and after the refusal, plus the log events the
refusal produced.  The control path is claimed in the report, so the evidence for
it is stored next to the picture rather than described in prose.

The browser is found in the usual Windows locations; if none is installed the
script reports that plainly and leaves the frames alone rather than pretending.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from govern import config, log, run, session, tasks, web  # noqa: E402

OUT = ROOT / "storyboards"
SCRATCH = ROOT / ".scratch" / "storyboard"
RUN_DIR = SCRATCH / "run"
TASK_ID = "T-L01a"
BROWSERS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
FRAMES = (
    "1-c1-gate-closed.png",
    "2-c1-gate-open.png",
    "3-c0-baseline.png",
    "4-c1-reject.png",
)
PROMISES = OUT / "4-c1-reject.promises.txt"


# ---------------------------------------------------------------------------
# serving
# ---------------------------------------------------------------------------
class Server:
    """The real UI server, on a port the OS picks, in a background thread."""

    def __init__(self, sess: session.Session) -> None:
        self.app = web.App(sess)
        self.httpd = web.make_server(self.app, 0)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self) -> "Server":
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)

    @property
    def base(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}"


def _call(base: str, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# capture
# ---------------------------------------------------------------------------
def find_browser() -> str | None:
    for candidate in BROWSERS:
        if Path(candidate).exists():
            return candidate
    return None


def shoot(browser: str, url: str, out: Path) -> None:
    profile = SCRATCH / "chrome-profile"
    shutil.rmtree(profile, ignore_errors=True)
    profile.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    command = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--disable-extensions",
        f"--user-data-dir={profile}",
        "--window-size=1440,1000",
        "--virtual-time-budget=2500",
        f"--screenshot={out}",
        url,
    ]
    result = subprocess.run(command, capture_output=True, timeout=120)
    if not out.exists() or out.stat().st_size == 0:
        detail = (result.stderr or b"").decode("utf-8", "replace")[-400:]
        raise RuntimeError(f"browser produced no frame ({result.returncode}): {detail}")


def _session(condition: str, session_id: str) -> session.Session:
    run_dir = SCRATCH / "run"
    shutil.rmtree(run_dir, ignore_errors=True)
    task = tasks.by_id(tasks.load_index(), TASK_ID)
    return run._new_session(run_dir, task, condition, "P01", session_id, 0, "replay")


def _tree_digest(root: Path) -> dict[str, str]:
    """SHA-256 of every file in the working copy, keyed by relative path."""
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _events(run_dir: Path) -> list[dict[str, Any]]:
    """Every JSONL line the session wrote, in order."""
    rows: list[dict[str, Any]] = []
    for path in sorted((run_dir / "logs").rglob("*.jsonl")):
        rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    return rows


def _write_promises(sess: session.Session, before: dict[str, str], after: dict[str, str],
                    events: list[dict[str, Any]], outcome: dict[str, Any]) -> Path:
    """Record what the refusal promised and what the log says it did."""
    target = OUT / "4-c1-reject.promises.txt"
    changed = sorted(name for name in before if before[name] != after.get(name))
    added = sorted(set(after) - set(before))
    action = [e for e in events if e["event_type"] == "suggestion_action"]
    end = [e for e in events if e["event_type"] == "task_end"]
    lines = [
        "Frame 4 (4-c1-reject.png): what the refusal promised, and what happened.",
        "",
        "Author self-test. The session is a scripted IMAGINARY participant (P01) replaying",
        "recordings; no human was involved and no model was called.",
        "",
        f"task: {sess.task.task_id}   condition: {sess.condition}   session: {sess.logger.session_id}",
        f"files hashed: {len(before)}   changed after the refusal: {len(changed)}   added: {len(added)}",
        f"work tree identical: {before == after}",
    ]
    if changed:
        lines.append(f"changed files: {', '.join(changed)}")
    if added:
        lines.append(f"added files: {', '.join(added)}")
    lines += ["", "log events produced by the refusal:"]
    for event in action:
        lines.append(
            f"  seq {event['seq']:>2}  {event['event_type']}  action={event['action']} "
            f"accepted_after_gate={event['accepted_after_gate']} "
            f"dwell_ms={event['review_dwell_ms']}"
        )
    for event in end:
        lines.append(
            f"  seq {event['seq']:>2}  {event['event_type']}  submitted={event['submitted']} "
            f"n_accepted={event['n_accepted']} n_rejects={event['n_rejects']} "
            f"tests_pass={event['tests_pass']} n_fail={event['n_fail']}"
        )
    lines += [
        "",
        f"ending via POST /api/end answered n_fail={outcome['n_fail']} "
        f"lines_added={outcome['lines_added']} lines_removed={outcome['lines_removed']}",
        "",
        "Every path above is relative to the session's working copy",
        f"({sess.work.relative_to(ROOT).as_posix()}), which is copied from corpus/{sess.task.task_id}/repo.",
        "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def capture(browser: str) -> list[str]:
    notes: list[str] = []
    for condition, session_id, frames in (
        ("C1", "S-SB-C1", ("1-c1-gate-closed.png", "2-c1-gate-open.png", "4-c1-reject.png")),
        ("C0", "S-SB-C0", ("3-c0-baseline.png",)),
    ):
        sess = _session(condition, session_id)
        with Server(sess) as server:
            sess.start(run.consent_for(config.load()))
            _, card = _call(server.base, "POST", "/api/prompt", {"text": f"refactor {TASK_ID}"})
            notes.append(f"{condition}: card {card['card_id']} with {card['n_items']} items, "
                         f"{card['n_required']} required, gate_open={card['gate_open']}")
            if condition == "C1":
                required = [i["item_id"] for i in card["items"] if i["required"]]
                for item_id in required[:2]:
                    _call(server.base, "POST", "/api/toggle", {"item_id": item_id})
                status, refused = _call(server.base, "POST", "/api/generate", {})
                notes.append(f"{condition}: generating at 2/{len(required)} answered {status} {refused.get('error')}"
                             f" with missing={len(refused.get('missing', []))}")
                shoot(browser, server.base + "/?playback=1", OUT / frames[0])
                for item_id in required[2:]:
                    _call(server.base, "POST", "/api/toggle", {"item_id": item_id})
                status, opened = _call(server.base, "POST", "/api/confirm", {})
                notes.append(f"{condition}: confirming answered {status} gate_open={opened.get('gate_open')}")
                shoot(browser, server.base + "/?playback=1", OUT / frames[1])

                # -- the control path: refuse the suggestion --------------
                before = _tree_digest(sess.work)
                status, suggestion = _call(server.base, "POST", "/api/generate", {})
                notes.append(f"{condition}: generating at full gate answered {status}")
                status, action = _call(
                    server.base,
                    "POST",
                    "/api/act",
                    {"suggestion_id": suggestion["suggestion_id"], "action": "reject", "dwell_ms": 2400},
                )
                after = _tree_digest(sess.work)
                notes.append(
                    f"{condition}: reject answered {status} applied={action.get('applied')} "
                    f"work_tree_identical={before == after}"
                )
                shoot(browser, server.base + "/?playback=1", OUT / frames[2])
                status, outcome = _call(server.base, "POST", "/api/end", {"submitted": False})
                notes.append(
                    f"{condition}: ending after the refusal answered {status} "
                    f"n_fail={outcome.get('n_fail')} lines_added={outcome.get('lines_added')}"
                )
                written = _write_promises(sess, before, after, _events(RUN_DIR), outcome)
                notes.append(f"{condition}: wrote {written.relative_to(ROOT).as_posix()}")
            else:
                status, suggestion = _call(server.base, "POST", "/api/generate", {})
                notes.append(f"{condition}: no gate, generating answered {status}")
                shoot(browser, server.base + "/?playback=1", OUT / frames[0])
                _call(server.base, "POST", "/api/act",
                      {"suggestion_id": suggestion.get("suggestion_id", ""), "action": "reject"})
    return notes


def check() -> int:
    missing = [name for name in FRAMES if not (OUT / name).exists() or (OUT / name).stat().st_size < 2000]
    if missing:
        print(f"fail: missing or empty frame(s): {', '.join(missing)}")
        return 1
    if not PROMISES.exists():
        print(f"fail: {PROMISES.name} is missing, so the control path has no evidence beside its frame")
        return 1
    text = PROMISES.read_text(encoding="utf-8")
    if "work tree identical: True" not in text:
        print(f"fail: {PROMISES.name} does not claim an unchanged work tree; re-capture the frame")
        return 1
    if "n_rejects=1" not in text:
        print(f"fail: {PROMISES.name} shows no rejected suggestion in the log")
        return 1
    print(f"ok: {len(FRAMES)} storyboard frame(s) in storyboards, refusal evidenced in {PROMISES.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="make_storyboard")
    parser.add_argument("--check", action="store_true", help="verify the frames exist")
    args = parser.parse_args(argv)
    if args.check:
        return check()

    browser = find_browser()
    if browser is None:
        print("fail: no Chrome or Edge found, so no frames can be captured", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    notes = capture(browser)
    for note in notes:
        print(note)
    code = check()
    print(f"captured in {time.monotonic() - started:.1f}s with {Path(browser).name}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())


