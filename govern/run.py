"""Single CLI entry point: ``python -m govern.run``.

M8 wires the orchestrator to the command line. Every path below is an *author
self-test* run (SPEC M2 status: SIM): the console, not a recruited
participant, confirms the card and accepts the suggestion. The web UI (M9) will
reuse the same ``Session`` methods, so nothing here bypasses the gate.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from . import __version__, card as card_mod, config, impact, llm, log, session, tasks, web

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_NOT_READY = 3

RUNS_ROOT = Path("runs")
DEFAULT_RUN_ID = "R-ADHOC"
SCHEDULE_PATH = session.SCHEDULE_PATH


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------
def log_for(run_dir: Path, session_id: str, participant: str, condition: str) -> log.Logger:
    """Build the session logger from the run's configuration."""
    cfg = config.load()
    return log.Logger(
        run_dir,
        {
            "session_id": session_id,
            "participant_id": participant,
            "condition": condition,
            "app_version": cfg.app_version,
            "model_id": cfg.model_id,
            "model_temperature": cfg.temperature,
            "seed": cfg.seed,
        },
    )


def consent_for(cfg: config.Config, schedule_id: str = "SCH-01") -> dict:
    """The fixed consent record used by author self-test runs (SPEC M2: SIM)."""
    return {
        "consent_version": "SIM-AUTHOR",
        "consent_given": True,
        "prior_years": 0.0,
        "llm_freq": "never",
        "lang_familiarity": 5,
        "schedule_id": schedule_id,
        "device": "author-workstation",
    }


def _cards() -> int:
    """How many assessment cards the corpus can build right now."""
    cfg = config.load()
    count = 0
    for task in tasks.load_index():
        built = card_mod.build(impact.analyze(task.repo, task.intent), task, cfg.conditions[-1])
        count += 1 if built.card_id else 0
    return count


def _close(sess: session.Session, started: float, completed: bool, withdrawn: bool = False) -> None:
    import time as _time

    sess.logger.emit(
        "session_end",
        phase="end",
        task_id=sess.task.task_id,
        task_index=sess.task_index,
        pair_id=sess.task.pair_id,
        total_elapsed_ms=int((_time.monotonic() - started) * 1000),
        n_tasks_completed=1 if completed else 0,
        completed_all=bool(completed),
        withdrawn=bool(withdrawn),
    )


def _rehearse(sess: session.Session, consent: dict | None) -> dict:
    """Drive one session from prompt to score without a browser (SIM)."""
    cfg = config.load()
    if consent is not None:
        sess.start(consent)

    if sess.phase in ("setup", "prompt"):
        sess.submit_prompt(sess.task.intent)

    confirmed = set(sess.state()["confirmed_ids"])
    for item in sess.card.items:
        if item.item_id not in confirmed:
            sess.toggle(item.item_id)

    decision = sess.confirm()
    suggestion = sess.generate()
    sess.act(suggestion.suggestion_id, "accept", dwell_ms=cfg.tau_review_ms)
    outcome = sess.end(submitted=True)
    return {
        "task_id": sess.task.task_id,
        "condition": sess.condition,
        "card_items": sess.card.n_items,
        "gate_blocked": decision.blocked,
        "tests_pass": outcome.tests_pass,
        "n_fail": outcome.n_fail,
        "debt_delta": outcome.debt_delta,
    }


def rehearse(sess: session.Session, consent: dict | None) -> dict:
    """Public entry point for the headless SIM script, used by ``experiments/``."""
    return _rehearse(sess, consent)


def close_session(sess: session.Session, started: float, completed: bool = True) -> None:
    """Public entry point for writing ``session_end``, used by ``experiments/``."""
    _close(sess, started, completed=completed)


def _new_session(
    run_dir: Path,
    task: tasks.Task,
    condition: str,
    participant: str,
    session_id: str,
    task_index: int,
    mode: str,
) -> session.Session:
    return session.Session(
        run_dir,
        task,
        condition,
        participant,
        log_for(run_dir, session_id, participant, condition),
        mode=mode,
        task_index=task_index,
    )


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def selftest(config_path: str | Path = config.DEFAULT_PATH) -> int:
    """Verify imports, config, corpus index and card construction."""
    config.load(config_path)
    task_list = tasks.load_index()
    print(f"ok: {len(task_list)} tasks, {_cards()} cards")
    return EXIT_OK


def dry_run(config_path: str | Path = config.DEFAULT_PATH) -> int:
    config.load(config_path)
    task_list = tasks.load_index()
    print(f"ok: {len(task_list)} tasks, {_cards()} cards")
    print("dry run: no logs written, no network used")
    return EXIT_OK


def _usage(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return EXIT_USAGE


def single(
    session_id: str,
    participant: str,
    condition: str,
    task_id: str,
    run_id: str = DEFAULT_RUN_ID,
    consent: bool = True,
    live: bool = False,
    task_index: int = 0,
    port: int | None = None,
) -> int:
    import time as _time

    if condition not in config.load().conditions:
        return _usage(f"unknown condition: {condition}")
    task = tasks.by_id(tasks.load_index(), task_id)
    run_dir = RUNS_ROOT / run_id
    sess = _new_session(
        run_dir, task, condition, participant, session_id, task_index,
        "live" if live else "replay",
    )
    started = _time.monotonic()
    record = consent_for(config.load()) if consent else {**consent_for(config.load()), "consent_given": False}
    if port is not None:
        return _browse(sess, record, started, port)
    try:
        summary = _rehearse(sess, record)
    except session.ConsentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    _close(sess, started, completed=True)
    print(
        f"ok: {session_id} {summary['task_id']} {condition} "
        f"card={summary['card_items']} items, tests_pass={summary['tests_pass']}, "
        f"n_fail={summary['n_fail']}, debt_delta={summary['debt_delta']:+.1f}"
    )
    print(f"log: {sess.logger.path}")
    return EXIT_OK


def _browse(sess: session.Session, consent: dict, started: float, port: int) -> int:
    """Serve the UI for one session and stop when the browser run ends.

    Nothing is rehearsed here: the human drives. The session is closed honestly
    -- ``withdrawn`` when they left before finishing -- rather than being marked
    complete just because the server exited.
    """
    try:
        sess.start(consent)
    except session.ConsentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print(f"log: {sess.logger.path}")
    code = web.serve(sess, port)
    ended = bool(sess.state()["ended"])
    _close(sess, started, completed=ended, withdrawn=not ended)
    return code


def batch(
    participant: str,
    schedule_path: str | Path = SCHEDULE_PATH,
    run_id: str = "R-BATCH",
    consent: bool = True,
    live: bool = False,
) -> int:
    import time as _time

    cfg = config.load()
    schedule = session.load_schedule(schedule_path)
    slots = session.assign(schedule, participant, tasks.load_index())
    run_dir = RUNS_ROOT / run_id
    done = 0
    for slot in slots:
        task = tasks.by_id(tasks.load_index(), slot.task_id)
        session_id = f"S-{run_id}-{slot.task_index:02d}"
        sess = _new_session(
            run_dir, task, slot.condition, participant, session_id, slot.task_index,
            "live" if live else "replay",
        )
        started = _time.monotonic()
        record = consent_for(cfg, schedule["schedule_id"])
        if not consent:
            record = {**record, "consent_given": False}
        try:
            summary = _rehearse(sess, record)
        except session.ConsentError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return EXIT_USAGE
        _close(sess, started, completed=True)
        print(
            f"  [{slot.task_index}] {slot.task_id} {slot.condition} "
            f"tests_pass={summary['tests_pass']} debt_delta={summary['debt_delta']:+.1f}"
        )
        done += 1
    print(f"ok: batch {participant} ran {done} of {len(slots)} slots in {run_dir}")
    return EXIT_OK


def resume(state_path: str | Path) -> int:
    import time as _time

    cfg = config.load()
    started = _time.monotonic()
    try:
        sess = session.Session.resume(state_path)
    except (session.StateConflict, FileNotFoundError) as exc:
        print(f"error: cannot resume: {exc}", file=sys.stderr)
        return EXIT_USAGE
    try:
        summary = _rehearse(sess, None)
    except session.ConsentError as exc:  # pragma: no cover - consent already logged
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    _close(sess, started, completed=True)
    print(
        f"ok: resumed {sess.logger.session_id} at task {summary['task_id']} "
        f"({sess.condition}), tests_pass={summary['tests_pass']}"
    )
    print(f"log: {sess.logger.path}")
    return EXIT_OK


def simulate(n: int) -> int:
    report = session.simulate(session.load_schedule(SCHEDULE_PATH), tasks.load_index(), n)
    target = RUNS_ROOT / "_sim" / "sim.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verdict = "balanced" if report["balanced"] else "UNBALANCED"
    print(
        f"ok: simulated {report['n']} assignments, C0={report['counts']['C0']} "
        f"C1={report['counts']['C1']} chi2 p={report['p']:.3f} ({verdict} at alpha="
        f"{report['alpha']}), every pair in both conditions: "
        f"{'yes' if report['pairs_both_conditions'] else 'no'}"
    )
    print(f"report: {target}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m govern.run",
        description="Interactive governance prototype for legacy refactoring.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--selftest", action="store_true", help="check config and corpus")
    parser.add_argument("--dry-run", action="store_true", help="validate wiring offline")

    single_group = parser.add_argument_group("single session")
    single_group.add_argument("--session", metavar="S-001")
    single_group.add_argument("--participant", metavar="P01", default="P01")
    single_group.add_argument("--condition", choices=("C0", "C1"), default="C1")
    single_group.add_argument("--task", metavar="T-L01a")
    single_group.add_argument("--port", type=int, metavar="8000", help="served by M9")
    single_group.add_argument("--live", action="store_true", help="call the model API")
    single_group.add_argument(
        "--no-consent", action="store_true", help="withhold the consent record (refusal test)"
    )
    single_group.add_argument("--task-index", type=int, default=0)

    batch_group = parser.add_argument_group("batch")
    batch_group.add_argument("--batch", action="store_true")
    batch_group.add_argument("--schedule", metavar="config/schedule.json", default=str(SCHEDULE_PATH))
    batch_group.add_argument("--run-id", metavar="R-001", default=DEFAULT_RUN_ID)
    batch_group.add_argument("--resume", metavar="runs/R-001/state/S-001.json")
    batch_group.add_argument("--simulate", type=int, metavar="N")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.port is not None:
        if not args.session:
            return _usage("--port needs --session (and --task): the UI serves one session")
        if not args.task:
            return _usage("--port needs --task")
        try:
            tasks.by_id(tasks.load_index(), args.task)
        except KeyError:
            return _usage(f"unknown task: {args.task}")
        return single(
            args.session,
            args.participant,
            args.condition,
            args.task,
            run_id=args.run_id,
            consent=not args.no_consent,
            live=args.live,
            task_index=args.task_index,
            port=args.port,
        )
    if args.selftest:
        return selftest()
    if args.dry_run:
        return dry_run()
    if args.simulate is not None:
        return simulate(args.simulate)
    if args.resume:
        return resume(args.resume)
    if args.batch:
        return batch(
            args.participant,
            schedule_path=args.schedule,
            run_id=args.run_id,
            consent=not args.no_consent,
            live=args.live,
        )
    if args.session:
        if not args.task:
            return _usage("--session needs --task")
        try:
            tasks.by_id(tasks.load_index(), args.task)
        except KeyError:
            return _usage(f"unknown task: {args.task}")
        return single(
            args.session,
            args.participant,
            args.condition,
            args.task,
            run_id=args.run_id,
            consent=not args.no_consent,
            live=args.live,
            task_index=args.task_index,
        )

    parser.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
