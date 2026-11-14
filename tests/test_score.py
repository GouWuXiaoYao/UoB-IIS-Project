"""M7 = SPEC M8: the outcome scorer (hidden tests + the six-rule JSON rule set).

Written before the implementation. The rule fixtures are the centre of gravity:
SPEC M8 acceptance 5 says a rule with no positive *and* negative fixture counts
as unimplemented, so every rule below is exercised on a bad sample and a clean
one.
"""

from __future__ import annotations

import dataclasses
import io
import json
import shutil
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from govern import patch as patch_mod
from govern import score
from govern import tasks as tasks_mod
from tests._scratch import scratch_dir

ROOT = Path(__file__).resolve().parent.parent
RULES = score.load_rules()
GOLD = {"enabled": True}


def scan(text: str, path: str = "sample.py") -> list[score.Finding]:
    return score.scan_source(text, path, RULES)


class ComplexityRuleTests(unittest.TestCase):
    def test_a_long_function_is_flagged(self) -> None:
        body = "\n".join(f"    x{i} = {i}" for i in range(50))
        hits = scan(f"def big():\n{body}\n    return x0\n")
        self.assertEqual([hit.rule_id for hit in hits], ["complexity"])

    def test_a_short_function_is_clean(self) -> None:
        self.assertEqual(scan("def small():\n    return 1\n"), [])

    def test_deep_branching_is_flagged(self) -> None:
        source = (
            "def deep(a):\n"
            "    if a:\n"
            "        if a:\n"
            "            if a:\n"
            "                if a:\n"
            "                    if a:\n"
            "                        return 1\n"
            "    return 0\n"
        )
        self.assertEqual([hit.rule_id for hit in scan(source)], ["complexity"])

    def test_flat_branching_is_clean(self) -> None:
        source = "def flat(a):\n    if a:\n        return 1\n    return 0\n"
        self.assertEqual(scan(source), [])


class DuplicationRuleTests(unittest.TestCase):
    def test_a_repeated_block_is_flagged_once_per_extra_copy(self) -> None:
        block = "\n".join(f"    v{i} = compute({i})" for i in range(6))
        source = f"def a():\n{block}\n\ndef b():\n{block}\n"
        hits = scan(source)
        self.assertEqual([hit.rule_id for hit in hits], ["duplication"])

    def test_a_single_copy_is_clean(self) -> None:
        block = "\n".join(f"    v{i} = compute({i})" for i in range(6))
        self.assertEqual(scan(f"def a():\n{block}\n"), [])


class BareExceptRuleTests(unittest.TestCase):
    def test_a_bare_except_is_flagged(self) -> None:
        hits = scan("try:\n    pass\nexcept:\n    pass\n")
        self.assertEqual([hit.rule_id for hit in hits], ["bare_except"])

    def test_a_typed_except_is_clean(self) -> None:
        self.assertEqual(scan("try:\n    pass\nexcept ValueError:\n    pass\n"), [])


class HardcodedSecretRuleTests(unittest.TestCase):
    def test_a_key_literal_is_flagged(self) -> None:
        hits = scan('password = "correct-horse-battery"\n')
        self.assertEqual([hit.rule_id for hit in hits], ["hardcoded_secret"])

    def test_a_known_prefix_is_flagged_whatever_the_name(self) -> None:
        hits = scan('value = "ghp_0123456789abcdef"\n')
        self.assertEqual([hit.rule_id for hit in hits], ["hardcoded_secret"])

    def test_an_environment_lookup_is_clean(self) -> None:
        self.assertEqual(scan('password = os.environ["A2_PASSWORD"]\n'), [])

    def test_a_short_literal_is_clean(self) -> None:
        self.assertEqual(scan('token = "abc"\n'), [])


class EvalRuleTests(unittest.TestCase):
    def test_eval_is_flagged(self) -> None:
        hits = scan("value = eval(expression)\n")
        self.assertEqual([hit.rule_id for hit in hits], ["eval_usage"])

    def test_exec_is_flagged(self) -> None:
        hits = scan("exec(source)\n")
        self.assertEqual([hit.rule_id for hit in hits], ["eval_usage"])

    def test_literal_eval_is_not_flagged(self) -> None:
        self.assertEqual(scan("import ast\nvalue = ast.literal_eval(text)\n"), [])


class SqlConcatRuleTests(unittest.TestCase):
    def test_concatenated_sql_is_flagged(self) -> None:
        hits = scan('q = "SELECT * FROM t WHERE id=" + user_id\n')
        self.assertEqual([hit.rule_id for hit in hits], ["sql_concat"])

    def test_an_f_string_sql_is_flagged(self) -> None:
        hits = scan('q = f"DELETE FROM t WHERE id={uid}"\n')
        self.assertEqual([hit.rule_id for hit in hits], ["sql_concat"])

    def test_a_parameterised_query_is_clean(self) -> None:
        self.assertEqual(scan('q = "SELECT * FROM t WHERE id=?"\n'), [])


class WeightsTests(unittest.TestCase):
    def test_vulnerabilities_only_count_the_last_three_rules(self) -> None:
        counts = {"complexity": 1, "duplication": 1, "bare_except": 1,
                  "hardcoded_secret": 1, "eval_usage": 1, "sql_concat": 1}
        self.assertGreater(score.debt(counts, RULES), 0)
        self.assertEqual(
            score.vuln(counts, RULES),
            sum(rule["weight"] for rule in RULES["rules"] if rule["category"] in score.VULN_CATEGORIES),
        )

    def test_every_rule_declares_id_severity_and_weight(self) -> None:
        for rule in RULES["rules"]:
            self.assertTrue(rule["rule_id"])
            self.assertIn(rule["severity"], {"low", "medium", "high"})
            self.assertGreater(rule["weight"], 0)

    def test_the_six_categories_are_exactly_the_spec_list(self) -> None:
        self.assertEqual(
            {rule["category"] for rule in RULES["rules"]},
            {"complexity", "duplication", "bare_except", "hardcoded_secret", "eval_usage", "sql_concat"},
        )


class RepoScanTests(unittest.TestCase):
    def test_counts_are_deterministic(self) -> None:
        task = tasks_mod.load_index(ROOT / "corpus")[0]
        self.assertEqual(score.counts(task.repo, RULES), score.counts(task.repo, RULES))

    def test_the_smell_ladder_follows_the_corpus_strata(self) -> None:
        """Debt grows with the stratum: medium and hard tiers carry rule smells."""
        per_task = {
            task.task_id: score.debt(score.counts(task.repo, RULES), RULES)
            for task in tasks_mod.load_index(ROOT / "corpus")
        }
        light = [v for k, v in per_task.items() if k.startswith("T-L01")]
        medium = [v for k, v in per_task.items() if k.startswith("T-L02")]
        hard = [v for k, v in per_task.items() if k.startswith("T-L03")]
        self.assertEqual(len(light) + len(medium) + len(hard), 6)
        self.assertTrue(all(v > 0 for v in medium), per_task)
        self.assertTrue(all(v > 0 for v in hard), per_task)
        self.assertGreater(min(hard), max(medium), per_task)

    def test_the_light_tier_is_clean_by_these_six_rules(self) -> None:
        """The light tier's smells (float money, module cache) are outside the rule set.

        Recorded rather than papered over: the six categories measure maintenance
        and security debt, not the money-as-float defect that the light tier is
        built around, so its ``debt_delta`` is zero by construction. The coverage
        gap is listed in ``docs/rubric-mapping.md``.
        """
        for task in tasks_mod.load_index(ROOT / "corpus"):
            if not task.task_id.startswith("T-L01"):
                continue
            counts = score.counts(task.repo, RULES)
            self.assertEqual(score.debt(counts, RULES), 0, task.task_id)
            self.assertEqual(set(counts), {rule["rule_id"] for rule in RULES["rules"]})

    def test_a_clean_repository_scores_zero(self) -> None:
        with scratch_dir() as tmp:
            repo = tmp / "repo"
            (repo / "pkg").mkdir(parents=True)
            (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (repo / "pkg" / "core.py").write_text(
                "def add(a, b):\n    return a + b\n", encoding="utf-8"
            )
            counts = score.counts(repo, RULES)
            self.assertEqual(score.debt(counts, RULES), 0)
            self.assertEqual(score.vuln(counts, RULES), 0)

    def test_scanning_ignores_pycache_and_tests(self) -> None:
        with scratch_dir() as tmp:
            repo = tmp / "repo"
            (repo / "pkg").mkdir(parents=True)
            (repo / "pkg" / "core.py").write_text("value = eval(x)\n", encoding="utf-8")
            (repo / "__pycache__").mkdir()
            (repo / "__pycache__" / "junk.py").write_text("value = eval(x)\n", encoding="utf-8")
            (repo / "tests").mkdir()
            (repo / "tests" / "test_x.py").write_text("value = eval(x)\n", encoding="utf-8")
            self.assertEqual(score.counts(repo, RULES)["eval_usage"], 1)


class ScorerVersionTests(unittest.TestCase):
    def test_the_version_carries_the_rules_hash(self) -> None:
        self.assertTrue(score.scorer_version(RULES).startswith(score.SCORER_VERSION))
        self.assertIn(score.rules_hash(RULES)[:12], score.scorer_version(RULES))

    def test_a_different_rules_file_changes_the_version(self) -> None:
        other = json.loads(json.dumps(RULES))
        other["rules"][0]["weight"] += 1
        self.assertNotEqual(score.scorer_version(RULES), score.scorer_version(other))


class BaselineAndEvaluateTests(unittest.TestCase):
    def test_baseline_reports_the_starting_state(self) -> None:
        task = tasks_mod.by_id(tasks_mod.load_index(ROOT / "corpus"), "T-L03a")
        base = score.baseline(task)
        self.assertEqual(base["task_id"], task.task_id)
        self.assertGreater(base["debt"], 0)
        self.assertFalse(base["tests_pass"])
        self.assertGreater(base["n_fail"], 0)
        self.assertEqual(base["scorer_version"], score.scorer_version(RULES))

    def test_gold_patch_passes_the_hidden_suite(self) -> None:
        task = tasks_mod.load_index(ROOT / "corpus")[0]
        with scratch_dir() as tmp:
            after = tmp / "repo"
            shutil.copytree(task.repo, after)
            patch_mod.apply_unified_diff(task.gold_patch.read_text(encoding="utf-8"), after)
            outcome = score.evaluate(task, after, score.baseline(task))
            self.assertTrue(outcome.tests_pass, outcome.failing_tests)
            self.assertEqual(outcome.n_fail, 0)
            self.assertEqual(outcome.failing_tests, [])

    def test_an_unmodified_repository_fails_the_hidden_suite(self) -> None:
        task = tasks_mod.load_index(ROOT / "corpus")[0]
        with scratch_dir() as tmp:
            after = tmp / "repo"
            shutil.copytree(task.repo, after)
            outcome = score.evaluate(task, after, score.baseline(task))
            self.assertFalse(outcome.tests_pass)
            self.assertGreater(outcome.n_fail, 0)
            self.assertTrue(outcome.failing_tests)

    def test_deltas_are_after_minus_before(self) -> None:
        task = tasks_mod.load_index(ROOT / "corpus")[0]
        base = score.baseline(task)
        with scratch_dir() as tmp:
            after = tmp / "repo"
            shutil.copytree(task.repo, after)
            patch_mod.apply_unified_diff(task.gold_patch.read_text(encoding="utf-8"), after)
            outcome = score.evaluate(task, after, base)
            expected = score.counts(after, RULES)
            self.assertEqual(outcome.debt_delta, score.debt(expected, RULES) - base["debt"])
            self.assertEqual(outcome.vuln_delta, score.vuln(expected, RULES) - base["vuln"])

    def test_line_counts_describe_the_change(self) -> None:
        task = tasks_mod.load_index(ROOT / "corpus")[0]
        with scratch_dir() as tmp:
            after = tmp / "repo"
            shutil.copytree(task.repo, after)
            patch_mod.apply_unified_diff(task.gold_patch.read_text(encoding="utf-8"), after)
            outcome = score.evaluate(task, after, score.baseline(task))
            self.assertGreater(outcome.lines_added, 0)
            self.assertGreater(outcome.lines_removed, 0)

    def test_is_correct_requires_an_improvement(self) -> None:
        task = tasks_mod.load_index(ROOT / "corpus")[0]
        base_outcome = score.Outcome(
            tests_pass=False, n_fail=3, failing_tests=["a"], debt_delta=0, vuln_delta=0,
            lines_added=0, lines_removed=0, scorer_version=score.scorer_version(RULES),
        )
        better = score.Outcome(
            tests_pass=False, n_fail=1, failing_tests=["a"], debt_delta=0, vuln_delta=0,
            lines_added=1, lines_removed=1, scorer_version=score.scorer_version(RULES),
        )
        worse = score.Outcome(
            tests_pass=False, n_fail=4, failing_tests=["a"], debt_delta=0, vuln_delta=0,
            lines_added=1, lines_removed=1, scorer_version=score.scorer_version(RULES),
        )
        self.assertTrue(score.is_correct(base_outcome, better))
        self.assertFalse(score.is_correct(base_outcome, worse))
        self.assertFalse(score.is_correct(base_outcome, base_outcome))


class IsolationTests(unittest.TestCase):
    def test_a_hanging_suite_is_killed_and_reported(self) -> None:
        task = tasks_mod.load_index(ROOT / "corpus")[0]
        with scratch_dir() as tmp:
            repo = tmp / "repo"
            shutil.copytree(task.repo, repo)
            hidden = tmp / "hidden"
            hidden.mkdir()
            (hidden / "test_hang.py").write_text(
                "import time\n\n\ndef test_hangs():\n    time.sleep(30)\n", encoding="utf-8"
            )
            slow = dataclasses.replace(task, hidden_tests=hidden)
            started = time.monotonic()
            passed, failing = score.run_hidden_tests(slow, repo, timeout_s=2)
            elapsed = time.monotonic() - started
            self.assertFalse(passed)
            self.assertTrue(any("timeout" in name for name in failing))
            self.assertLess(elapsed, 15)

    def test_a_failing_test_is_named(self) -> None:
        task = tasks_mod.load_index(ROOT / "corpus")[0]
        with scratch_dir() as tmp:
            repo = tmp / "repo"
            shutil.copytree(task.repo, repo)
            passed, failing = score.run_hidden_tests(task, repo, timeout_s=60)
            self.assertFalse(passed)
            self.assertTrue(failing)
            self.assertTrue(all("::" in name for name in failing), failing)


class EventTests(unittest.TestCase):
    def test_the_scored_event_matches_the_log_schema(self) -> None:
        from govern import config as config_mod
        from govern import log as log_mod

        task = tasks_mod.load_index(ROOT / "corpus")[0]
        with scratch_dir() as tmp:
            after = tmp / "repo"
            shutil.copytree(task.repo, after)
            patch_mod.apply_unified_diff(task.gold_patch.read_text(encoding="utf-8"), after)
            outcome = score.evaluate(task, after, score.baseline(task))
            payload = score.scored_event("s-1", outcome, before=score.baseline(task))
            self.assertEqual(
                set(payload),
                set(log_mod.EVENT_FIELDS["suggestion_scored"]),
            )
            self.assertEqual(payload["scored_by"], "hidden_tests")
            self.assertTrue(payload["is_correct"])

            cfg = config_mod.load()
            meta = {
                "session_id": "S-M7-0001",
                "participant_id": "P00",
                "condition": "C0",
                "app_version": "0.0.0-test",
                "model_id": cfg.model_id,
                "model_temperature": cfg.temperature,
                "seed": cfg.seed,
            }
            logger = log_mod.Logger(tmp / "run", meta)
            logger.emit(
                "suggestion_scored",
                phase="test",
                task_id=task.task_id,
                task_index=0,
                pair_id="PAIR-01",
                **payload,
            )
            written = list((tmp / "run").rglob("*.jsonl"))
            self.assertEqual(len(written), 1)
            event = json.loads(written[0].read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(log_mod.validate(event), [])
            self.assertEqual(event["event_type"], "suggestion_scored")


class CliTests(unittest.TestCase):
    def test_selftest_reports_the_six_rules(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = score.main(["--selftest"])
        self.assertEqual(code, 0, buffer.getvalue())
        text = buffer.getvalue()
        for rule in ("complexity", "duplication", "bare_except",
                     "hardcoded_secret", "eval_usage", "sql_concat"):
            self.assertIn(rule, text)
        self.assertIn("ok:", text)
