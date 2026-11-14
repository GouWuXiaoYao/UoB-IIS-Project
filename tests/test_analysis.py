"""Analysis layer tests.

Two kinds of test live here:

* **known answers** — the statistics are checked against results that can be
  computed independently (brute-force enumeration of the signed-rank
  distribution, published t values, the closed form of a balanced mixed model), so
  "the pipeline ran" is never mistaken for "the numbers are right";
* **fixtures** — a hand-written run directory with a planted difference, so the
  loader, the checks and the workbook are exercised on data whose answer is known
  by construction, independently of ``runs/``.
"""

from __future__ import annotations

import itertools
import json
import math
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from analysis import checks, load, png, report, stats, xlsx
from tests._scratch import scratch_dir


def _quiet(function, *args, **kwargs):
    """Call a CLI entry point with its chatter captured."""
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        return function(*args, **kwargs)


def _event(session: str, seq: int, kind: str, **fields) -> str:
    payload = {
        "schema_version": "1.0.0",
        "event_id": f"{session}-{seq}",
        "seq": seq,
        "ts": "2026-11-14T10:00:00.000+00:00",
        "session_id": session,
        "participant_id": fields.pop("participant", "P01"),
        "condition": fields.pop("condition", "C1"),
        "task_id": fields.pop("task_id", None),
        "task_index": 0,
        "pair_id": fields.pop("pair_id", "PAIR-01"),
        "phase": "run",
        "event_type": kind,
        "app_version": "1.0.0",
        "model_id": "qwen2.5-coder:7b",
        "model_temperature": 0.2,
        "seed": 42,
    }
    payload.update(fields)
    return json.dumps(payload, sort_keys=True)


def _session_files(root: Path, values: dict[tuple[str, str], float], n_tasks: int = 3) -> None:
    """Write a synthetic run: one log per (condition, task), with a known outcome."""
    logs = root / "logs" / "P01"
    logs.mkdir(parents=True, exist_ok=True)
    for (condition, task), debt in values.items():
        session = f"S-{condition}-{task}"
        def ev(seq, kind, **fields):
            return _event(session, seq, kind, condition=condition, task_id=fields.pop("task_id", task), **fields)
        lines = [
            ev(1, "session_start", task_id=None, consent_version="SIM-AUTHOR",
               consent_given=True, prior_years=0.0, llm_freq="never",
               lang_familiarity=5, schedule_id="SCH-01", device="test"),
            ev(2, "prompt_submit", prompt_sha256="a" * 64, prompt_len=20),
            ev(3, "card_shown", card_id="card-1",
               card_version="1.0.0+card/1", n_items=2, n_required=2,
               latency_from_prompt_ms=0, impact_set_hash="sha256:" + "b" * 64),
            ev(4, "gate_decision", card_id="card-1",
               confirmed=True, blocked=False, n_required=2, n_confirmed=2,
               gate_latency_ms=5),
            ev(5, "generation_request", request_sha256="c" * 64, mode="replay"),
            ev(6, "suggestion_shown", suggestion_id="SUG-1",
               patch_sha256="d" * 64, patch_lines=10, n_touched=2),
            ev(7, "suggestion_action", suggestion_id="SUG-1",
               action="accept", review_dwell_ms=1200, edit_distance_lines=0,
               accepted_after_gate=True),
            ev(8, "test_run", suite="hidden", n_pass=1, n_fail=1,
               failing_tests=["test_x.py::test_a"]),
            ev(9, "suggestion_scored", suggestion_id="SUG-1",
               is_correct=False, gold_patch_match=False, scored_by="hidden_tests",
               scorer_version="score/1.0.0"),
            ev(10, "task_end", elapsed_ms=100.0, submitted=True,
               timeout=False, tests_pass=False, n_fail=1, debt_delta=debt,
               vuln_delta=0, lines_added=4, lines_removed=3, n_suggestions=1,
               n_accepted=1, n_edits=0, n_rejects=0),
            ev(11, "session_end", total_elapsed_ms=500,
               n_tasks_completed=1, completed_all=True, withdrawn=False),
        ]
        (logs / f"{session}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps({"run_id": root.name, "n_cells": len(values), "task_order": []}),
        encoding="utf-8",
    )


class KnownAnswerTests(unittest.TestCase):
    def test_paired_t_matches_published_values(self):
        before = [10, 12, 14, 16, 18, 20]
        after = [9, 10, 11, 12, 13, 14]
        result = stats.compare_paired(before, after)
        self.assertAlmostEqual(result.t.statistic, 4.5826, places=4)
        self.assertEqual(result.t.df, 5)
        self.assertAlmostEqual(result.t.p_value, 0.005934, places=6)
        self.assertAlmostEqual(result.t.effect, 1.8708, places=4)
        self.assertAlmostEqual(result.mean_difference, 3.5)

    def test_t_distribution_matches_the_table(self):
        self.assertAlmostEqual(stats.t_cdf(2.0, 10), 0.963306, places=6)
        self.assertAlmostEqual(stats.t_cdf(-2.228, 10), 0.025, places=3)
        self.assertAlmostEqual(stats.t_quantile(0.975, 10), 2.228139, places=5)

    def test_wilcoxon_exact_p_matches_brute_force(self):
        """The DP must agree with enumerating all 2^n sign assignments."""
        rng_values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        for n in (4, 5, 6):
            differences = rng_values[:n]
            statistic = sum(differences)  # all positive -> W+ is the full rank sum
            total = 2 ** n
            as_or_more = sum(
                1
                for signs in itertools.product((-1, 1), repeat=n)
                if sum(r for r, s in zip(range(1, n + 1), signs) if s > 0) >= statistic
            )
            expected = min(1.0, 2 * as_or_more / total)
            got = stats._wilcoxon_exact_p(int(statistic), n)
            self.assertAlmostEqual(got, expected, places=12, msg=f"n={n}")

    def test_wilcoxon_is_undefined_when_nothing_changes(self):
        result = stats.compare_paired([1, 2, 3], [1, 2, 3])
        self.assertTrue(result.zero_variance)
        self.assertIsNone(result.t.p_value)
        self.assertIsNone(result.wilcoxon.p_value)
        self.assertIn("0/0", result.t.note)

    def test_wilcoxon_reports_a_tie_corrected_approximation(self):
        before = [10, 10, 10, 20, 20, 20, 30]
        after = [9, 10, 10, 19, 20, 18, 27]
        result = stats.wilcoxon(before, after)
        self.assertIn("tie correction", result.method)
        self.assertGreaterEqual(result.p_value, 0.0)
        self.assertLessEqual(result.p_value, 1.0)

    def test_summary_ci_uses_the_t_quantile(self):
        summary = stats.summarise([1.0, 2.0, 3.0, 4.0, 5.0])
        half = stats.t_quantile(0.975, 4) * summary.sd / math.sqrt(5)
        self.assertAlmostEqual(summary.ci_high - summary.mean, half, places=9)
        self.assertEqual(summary.median, 3.0)

    def test_hedges_g_is_smaller_than_dz(self):
        differences = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertLess(stats.hedges_g(differences), stats.cohens_dz(differences))

    def test_bootstrap_ci_is_deterministic(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        first = stats.bootstrap_ci(values, statistic=lambda s: sum(s) / len(s), seed=7)
        second = stats.bootstrap_ci(values, statistic=lambda s: sum(s) / len(s), seed=7)
        self.assertEqual(first, second)

    def test_mixed_model_recovers_the_within_group_difference(self):
        groups = ["g1", "g1", "g2", "g2"]
        condition = [0.0, 1.0, 0.0, 1.0]
        outcome = [1.0, 2.4, 5.0, 6.2]
        fit = stats.mixed_model(groups, condition, outcome)
        self.assertAlmostEqual(fit["estimate"], 1.3, places=2)
        self.assertEqual(fit["n_groups"], 2.0)

    def test_mixed_model_refuses_one_group(self):
        fit = stats.mixed_model(["g1", "g1", "g1", "g1"], [0, 1, 0, 1], [1, 2, 3, 4])
        self.assertIsNone(fit["estimate"])
        self.assertIn("collinear", fit["note"])

    def test_holm_and_bh_against_hand_computation(self):
        p_values = [0.01, 0.02, 0.03, 0.04]
        holm = stats.holm(p_values)
        # m*p_1, (m-1)*p_2, (m-2)*p_3, (m-3)*p_4, then forced monotone: the last one
        # cannot fall below the one before it, hence 0.06 rather than 0.04.
        self.assertEqual([round(r["p_adjusted"], 6) for r in holm],
                         [0.04, 0.06, 0.06, 0.06])
        bh = stats.benjamini_hochberg(p_values)
        # BH adjusted = p_i * m / i, then made monotone from the largest down.
        self.assertEqual([round(r["p_adjusted"], 6) for r in bh],
                         [0.04, 0.04, 0.04, 0.04])


class CanvasTests(unittest.TestCase):
    def test_png_header_and_dimensions(self):
        canvas = png.Canvas(32, 16)
        data = canvas.png_bytes()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        self.assertEqual((width, height), (32, 16))

    def test_text_changes_pixels_and_is_deterministic(self):
        blank = png.Canvas(60, 20)
        written = png.Canvas(60, 20)
        written.text(2, 2, "AB", png.BLACK, 1)
        self.assertNotEqual(blank.pixels, written.pixels)
        again = png.Canvas(60, 20)
        again.text(2, 2, "AB", png.BLACK, 1)
        self.assertEqual(written.png_bytes(), again.png_bytes())

    def test_drawing_outside_the_canvas_is_clipped(self):
        canvas = png.Canvas(10, 10)
        canvas.fill_rect(-20, -20, 5, 5, png.BLACK)
        canvas.fill_rect(8, 8, 50, 50, png.BLACK)
        self.assertEqual(len(canvas.pixels), 10 * 10 * 3)


class WorkbookTests(unittest.TestCase):
    def test_round_trip_keeps_text_and_numbers(self):
        with scratch_dir("xlsx") as path:
            book = xlsx.write(path / "t.xlsx", {"第一表": [["metric", "value"], ["debt", 1.25]]})
            back = xlsx.read_sheets(book)
            self.assertEqual(back["第一表"], [["metric", "value"], ["debt", "1.25"]])

    def test_xml_special_characters_are_escaped(self):
        with scratch_dir("xlsx-escape") as path:
            book = xlsx.write(path / "t.xlsx", {"A": [["a & b < c"]]})
            back = xlsx.read_sheets(book)
            self.assertEqual(back["A"], [["a & b < c"]])

    def test_output_is_byte_identical_for_the_same_cells(self):
        with scratch_dir("xlsx-determinism") as path:
            first = xlsx.write(path / "a.xlsx", {"A": [["x"], [1]]}).read_bytes()
            second = xlsx.write(path / "b.xlsx", {"A": [["x"], [1]]}).read_bytes()
            self.assertEqual(first, second)

    def test_every_sheet_is_present(self):
        with scratch_dir("xlsx-sheets") as path:
            book = xlsx.write(path / "t.xlsx", {"A": [["1"]], "B": [["2"]], "C": [["3"]]})
            self.assertEqual(sorted(xlsx.read_sheets(book)), ["A", "B", "C"])


class LoaderTests(unittest.TestCase):
    def test_task_id_comes_from_the_events_that_carry_it(self):
        with scratch_dir("load") as path:
            run = path / "R-TEST"
            _session_files(run, {("C0", "T-1"): 0.0, ("C1", "T-1"): -2.0})
            sessions = load.load_run(run)
            self.assertEqual(len(sessions), 2)
            for session in sessions:
                self.assertEqual(session.task_id, "T-1", "session_start has no task id")
                self.assertEqual(session.participant, "P01")
                self.assertTrue(session.ended)

    def test_bad_lines_are_counted_not_swallowed(self):
        with scratch_dir("load-bad") as path:
            run = path / "R-BAD"
            _session_files(run, {("C1", "T-1"): -1.0})
            log = next((run / "logs" / "P01").glob("*.jsonl"))
            log.write_text(log.read_text(encoding="utf-8") + "{not json\n", encoding="utf-8")
            session = load.load_run(run)[0]
            self.assertEqual(session.n_bad_lines, 1)

    def test_pairing_keeps_only_complete_pairs(self):
        with scratch_dir("load-pairs") as path:
            run = path / "R-PAIRS"
            _session_files(run, {("C0", "T-1"): 0.0, ("C1", "T-1"): -2.0, ("C1", "T-2"): -1.0})
            sessions = load.load_run(run)
            labels, left, right, _participants, _tasks = load.paired_series(sessions, "debt_delta")
            self.assertEqual(labels, ["T-1"])
            self.assertEqual((left, right), ([0.0], [-2.0]))


class StudyTests(unittest.TestCase):
    def _fixture(self, path: Path) -> Path:
        run = path / "R-FIXTURE"
        _session_files(
            run,
            {
                ("C0", "T-1"): 0.0,
                ("C0", "T-2"): -2.0,
                ("C0", "T-3"): -4.0,
                ("C0", "T-4"): -6.0,
                ("C1", "T-1"): -1.0,
                ("C1", "T-2"): -3.0,
                ("C1", "T-3"): -5.0,
                ("C1", "T-4"): -7.0,
            },
        )
        return run

    def test_planted_difference_is_recovered(self):
        with scratch_dir("study") as path:
            run = self._fixture(path)
            sessions = load.load_run(run)
            analysis = report.analyse(sessions, [load.read_manifest(run)])
            test = analysis.tests["debt_delta"]
            self.assertEqual(test.n, 4)
            self.assertAlmostEqual(test.mean_difference, 1.0)
            self.assertFalse(test.zero_variance)
            # 4 identical differences: no variance, so both tests say so instead of p=0.
            self.assertIsNone(test.t.p_value)

    def test_missing_cell_is_reported(self):
        with scratch_dir("study-missing") as path:
            run = self._fixture(path)
            victim = next((run / "logs" / "P01").glob("S-C1-T-3.jsonl"))
            victim.unlink()
            sessions = load.load_run(run)
            analysis = report.analyse(sessions, [load.read_manifest(run)])
            self.assertIn("P01/T-3", " ".join(analysis.missing.unpaired))
            self.assertFalse(analysis.missing.complete)

    def test_outlier_flag_finds_the_planted_value(self):
        values = [1.0, 1.1, 0.9, 1.05, 1.02, 40.0]
        report_ = checks.outliers([f"s{i}" for i in range(len(values))], values)
        self.assertEqual([label for label, _v, _z in report_.flagged], ["s5"])

    def test_outliers_are_not_computed_when_mad_is_zero(self):
        report_ = checks.outliers(["a", "b", "c", "d"], [2.0, 2.0, 2.0, 5.0])
        self.assertEqual(report_.flagged, [])
        self.assertIn("MAD is zero", report_.note)

    def test_multiplicity_needs_p_values(self):
        report_ = checks.multiplicity(["a", "b"], [None, None])
        self.assertEqual(report_.holm, [])
        self.assertIn("no computable", report_.note)

    def test_end_to_end_outputs(self):
        with scratch_dir("study-out") as path:
            run = self._fixture(path)
            sessions = load.load_run(run)
            analysis = report.analyse(sessions, [load.read_manifest(run)])
            out = path / "out"
            outputs = report.build_outputs(analysis, out)
            self.assertTrue(outputs["workbook"].is_file())
            self.assertTrue(outputs["captions"].is_file())
            sheets = xlsx.read_sheets(outputs["workbook"])
            for name in ("README", "Descriptives", "Paired tests", "Multiplicity", "Checks",
                         "Figures", "Sessions"):
                self.assertIn(name, sheets)
            figures = sorted((out / "figures").glob("*.png"))
            self.assertEqual(len(figures), 4)
            for figure in figures:
                self.assertTrue(figure.read_bytes().startswith(b"\x89PNG"))
            captions = outputs["captions"].read_text(encoding="utf-8")
            self.assertIn("Figure 1", captions)

    def test_report_marks_a_structural_zero(self):
        with scratch_dir("study-structural") as path:
            run = self._fixture(path)
            sessions = load.load_run(run)
            analysis = report.analyse(sessions, [load.read_manifest(run)])
            rows = list(report._test_rows(analysis))
            header = rows[0]
            column = header.index("Status")
            for row in rows[1:]:
                if row[0].startswith("Gate decision latency"):
                    self.assertEqual(row[column], "structural zero in baseline")
            self.assertNotIn("gate_latency_ms", analysis.multiplicity.family)


class CliTests(unittest.TestCase):
    def test_selftest_passes(self):
        from analysis import run as cli

        self.assertEqual(_quiet(cli._selftest), 0)

    def test_missing_path_fails_loudly(self):
        from analysis import run as cli

        self.assertEqual(_quiet(cli.main, ["--runs", "does-not-exist", "--selftest"]), 0)
        self.assertEqual(_quiet(cli.main, ["--runs", "does-not-exist"]), 2)

    def test_two_runs_need_an_explicit_choice(self):
        from analysis import run as cli

        with scratch_dir("cli") as path:
            _session_files(path / "R-A", {("C0", "T-1"): 0.0, ("C1", "T-1"): -1.0})
            _session_files(path / "R-B", {("C0", "T-1"): 0.0, ("C1", "T-1"): -1.0})
            with self.assertRaises(SystemExit) as caught:
                _quiet(cli.main, ["--runs", str(path), "--out", str(path / "out")])
            self.assertIn("--run-id", str(caught.exception))

    def test_one_command_writes_a_workbook(self):
        from analysis import run as cli

        with scratch_dir("cli-out") as path:
            _session_files(
                path / "R-ONE",
                {("C0", "T-1"): 0.0, ("C1", "T-1"): -1.0, ("C0", "T-2"): -2.0,
                 ("C1", "T-2"): -3.0},
            )
            code = _quiet(cli.main, ["--runs", str(path / "R-ONE"), "--out", str(path / "out")])
            self.assertEqual(code, 0)
            self.assertTrue((path / "out" / "results.xlsx").is_file())


if __name__ == "__main__":
    unittest.main()
