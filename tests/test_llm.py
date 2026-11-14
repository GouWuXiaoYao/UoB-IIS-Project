"""M6 = SPEC M3: the single LLM client (live + replay) and its guard rails."""

from __future__ import annotations

import json
import os
import re
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from govern import config as config_mod
from govern import llm
from govern import patch as patch_mod
from govern import tasks
from tests._scratch import scratch_dir

ROOT = Path(__file__).resolve().parent.parent
CFG = config_mod.load(ROOT / "config" / "config.json")

GOOD_REPLY = {
    "patch_diff": (
        "--- a/example/core.py\n"
        "+++ b/example/core.py\n"
        "@@ -1,1 +1,2 @@\n"
        "-TOTAL = 0\n"
        "+TOTAL = 0\n"
        "+TAX_RATE = 0.2\n"
    ),
    "rationale_text": "Move the total into integer minor units and keep tax out of the module state.",
    "touched_symbols": ["example.core.total", "example.core.TAX_RATE"],
    "layers": {"L1": "total() now returns minor units", "L2": "tax is applied once, at the call site"},
}


def a_context(task_id: str = "T-TEST") -> llm.Context:
    return llm.Context(
        task_id=task_id,
        intent="make totals exact",
        files=(llm.FileSlice("example/core.py", "TOTAL = 0\n"),),
        symbols=("example.core.total",),
        call_edges=(("example.core.total", "example.core.TOTAL"),),
    )


def a_client(tmp: Path, mode: str = "replay", logger=None) -> llm.Client:
    return llm.Client(CFG, mode=mode, recordings=tmp, logger=logger)


def write_recording(path: Path, ctx: llm.Context, reply: dict = GOOD_REPLY, **overrides) -> None:
    body = {
        "format": "recording/1",
        "source": "sim",
        "request_sha256": f"sha256:{ctx.sha256()}",
        "model_id": CFG.model_id,
        "model_temperature": CFG.temperature,
        "seed": CFG.seed,
        "response": dict(reply),
    }
    body.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=True), encoding="utf-8")


class _Stub:
    """A loopback HTTP server standing in for the provider endpoint."""

    def __init__(self, status: int = 200, body: object | None = None) -> None:
        self.status = status
        self.body = GOOD_REPLY if body is None else body
        self.requests: list[dict] = []
        self.headers: list[dict] = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                stub.requests.append(json.loads(self.rfile.read(length) or b"{}"))
                stub.headers.append(dict(self.headers))
                payload = stub.body
                raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                self.send_response(stub.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args):  # keep the test output clean
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}/v1/chat"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class ReplayTests(unittest.TestCase):
    def test_replay_returns_the_recorded_suggestion(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            client = a_client(tmp)
            write_recording(client.path_for(ctx), ctx)
            suggestion = client.generate(ctx)
            self.assertEqual(suggestion.patch_diff, GOOD_REPLY["patch_diff"])
            self.assertEqual(suggestion.rationale_text, GOOD_REPLY["rationale_text"])
            self.assertEqual(suggestion.touched_symbols, tuple(GOOD_REPLY["touched_symbols"]))
            self.assertEqual(suggestion.layers, GOOD_REPLY["layers"])

    def test_replay_is_byte_identical_across_ten_calls(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            client = a_client(tmp)
            write_recording(client.path_for(ctx), ctx)
            hashes = {client.generate(ctx).content_hash() for _ in range(10)}
            self.assertEqual(len(hashes), 1, f"replay drifted: {hashes}")

    def test_replay_never_touches_the_network(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            client = a_client(tmp)
            write_recording(client.path_for(ctx), ctx)
            with mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("network used")):
                client.generate(ctx)

    def test_replay_needs_no_api_key(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            client = a_client(tmp)
            write_recording(client.path_for(ctx), ctx)
            with mock.patch.dict(os.environ, {}, clear=True):
                suggestion = client.generate(ctx)
            self.assertTrue(suggestion.patch_diff)

    def test_missing_recording_raises_with_a_code(self) -> None:
        with scratch_dir() as tmp:
            client = a_client(tmp)
            with self.assertRaises(llm.RecordingMissing) as caught:
                client.generate(a_context())
            self.assertEqual(caught.exception.code, "recording_missing")

    def test_a_recording_for_another_request_is_refused(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            client = a_client(tmp)
            path = client.path_for(ctx)
            write_recording(path, ctx)
            body = json.loads(path.read_text(encoding="utf-8"))
            body["request_sha256"] = "sha256:" + "0" * 64
            path.write_text(json.dumps(body), encoding="utf-8")
            with self.assertRaises(llm.SchemaViolation):
                client.generate(ctx)

    def test_a_malformed_recording_is_refused(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            client = a_client(tmp)
            path = client.path_for(ctx)
            write_recording(path, ctx, reply={"patch_diff": 7})
            with self.assertRaises(llm.SchemaViolation):
                client.generate(ctx)

    def test_a_recording_with_an_unparseable_patch_is_refused(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            client = a_client(tmp)
            path = client.path_for(ctx)
            write_recording(path, ctx, reply={**GOOD_REPLY, "patch_diff": "not a diff at all"})
            with self.assertRaises(llm.SchemaViolation):
                client.generate(ctx)


class LiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stub = _Stub()
        self.addCleanup(self.stub.close)
        patcher = mock.patch.dict(os.environ, {"A2_API_BASE": self.stub.url, "A2_API_KEY": "test-key"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_live_posts_the_context_and_parses_the_reply(self) -> None:
        with scratch_dir() as tmp:
            suggestion = a_client(tmp, mode="live").generate(a_context())
            self.assertEqual(suggestion.patch_diff, GOOD_REPLY["patch_diff"])
            self.assertEqual(len(self.stub.requests), 1)
            sent = self.stub.requests[0]
            self.assertEqual(sent["seed"], 42)
            self.assertIn("make totals exact", json.dumps(sent))

    def test_live_sends_the_key_from_the_environment(self) -> None:
        with scratch_dir() as tmp:
            a_client(tmp, mode="live").generate(a_context())
            self.assertEqual(self.stub.headers[0].get("Authorization"), "Bearer test-key")

    def test_live_without_a_key_is_refused_before_any_request(self) -> None:
        with scratch_dir() as tmp:
            env = {"A2_API_BASE": self.stub.url}
            with mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaises(llm.AuthMissing) as caught:
                    a_client(tmp, mode="live").generate(a_context())
            self.assertEqual(caught.exception.code, "auth_missing")
            self.assertEqual(self.stub.requests, [])

    def test_live_without_an_endpoint_is_refused(self) -> None:
        with scratch_dir() as tmp:
            env = {"A2_API_KEY": "test-key"}
            with mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaises(llm.EndpointMissing) as caught:
                    a_client(tmp, mode="live").generate(a_context())
            self.assertEqual(caught.exception.code, "endpoint_missing")

    def test_unauthorised_response_is_reported_as_auth_missing(self) -> None:
        stub = _Stub(status=401, body={"error": "no"})
        self.addCleanup(stub.close)
        with mock.patch.dict(os.environ, {"A2_API_BASE": stub.url, "A2_API_KEY": "bad"}):
            with scratch_dir() as tmp:
                with self.assertRaises(llm.AuthMissing) as caught:
                    a_client(tmp, mode="live").generate(a_context())
        self.assertEqual(caught.exception.code, "auth_missing")

    def test_a_malformed_reply_raises_with_a_code(self) -> None:
        stub = _Stub(body={"patch_diff": "--- a/x\n+++ b/x\n@@ -1,1 +1,1 @@\n-1\n+2\n"})
        self.addCleanup(stub.close)
        with mock.patch.dict(os.environ, {"A2_API_BASE": stub.url, "A2_API_KEY": "k"}):
            with scratch_dir() as tmp:
                with self.assertRaises(llm.SchemaViolation) as caught:
                    a_client(tmp, mode="live").generate(a_context())
        self.assertEqual(caught.exception.code, "schema_violation")

    def test_live_writes_a_recording_that_replay_reproduces(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            live = a_client(tmp, mode="live").generate(ctx)
            config_mod.load(ROOT / "config" / "config.json")
            replay = a_client(tmp, mode="replay").generate(ctx)
            self.assertEqual(live.content_hash(), replay.content_hash())

    def test_the_recording_says_it_came_from_live(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            client = a_client(tmp, mode="live")
            client.generate(ctx)
            body = json.loads(client.path_for(ctx).read_text(encoding="utf-8"))
            self.assertEqual(body["source"], "live")
            self.assertEqual(body["request_sha256"], f"sha256:{ctx.sha256()}")


class EventTests(unittest.TestCase):
    def test_exactly_one_generation_request_per_successful_replay(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            logger = llm_test_logger(tmp)
            client = a_client(tmp, logger=logger)
            write_recording(client.path_for(ctx), ctx)
            client.generate(ctx)
            kinds = [row["event_type"] for row in read_log(logger)]
            self.assertEqual(kinds.count("generation_request"), 1)

    def test_exactly_one_generation_request_per_failed_call(self) -> None:
        with scratch_dir() as tmp:
            logger = llm_test_logger(tmp)
            client = a_client(tmp, logger=logger)
            with self.assertRaises(llm.RecordingMissing):
                client.generate(a_context())
            kinds = [row["event_type"] for row in read_log(logger)]
            self.assertEqual(kinds.count("generation_request"), 1)

    def test_the_mode_field_is_truthful(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            logger = llm_test_logger(tmp)
            client = a_client(tmp, logger=logger)
            write_recording(client.path_for(ctx), ctx)
            client.generate(ctx)
            row = next(r for r in read_log(logger) if r["event_type"] == "generation_request")
            self.assertEqual(row["mode"], "replay")

    def test_the_model_id_comes_from_config(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            logger = llm_test_logger(tmp)
            client = a_client(tmp, logger=logger)
            write_recording(client.path_for(ctx), ctx)
            client.generate(ctx)
            row = next(r for r in read_log(logger) if r["event_type"] == "generation_request")
            self.assertEqual(row["model_id"], CFG.model_id)

    def test_a_recording_from_another_model_is_refused(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            client = a_client(tmp)
            write_recording(client.path_for(ctx), ctx, model_id="some-other-model")
            with self.assertRaises(llm.SchemaViolation):
                client.generate(ctx)

    def test_a_schema_violation_also_writes_an_integrity_event(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            logger = llm_test_logger(tmp)
            client = a_client(tmp, logger=logger)
            write_recording(client.path_for(ctx), ctx, reply={"patch_diff": 1})
            with self.assertRaises(llm.SchemaViolation):
                client.generate(ctx)
            kinds = [row["event_type"] for row in read_log(logger)]
            self.assertIn("integrity_event", kinds)

    def test_the_session_continues_after_a_schema_violation(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            logger = llm_test_logger(tmp)
            client = a_client(tmp, logger=logger)
            path = client.path_for(ctx)
            write_recording(path, ctx, reply={"patch_diff": 1})
            with self.assertRaises(llm.SchemaViolation):
                client.generate(ctx)
            write_recording(path, ctx)
            self.assertTrue(client.generate(ctx).patch_diff)

    def test_the_request_hash_is_logged(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            logger = llm_test_logger(tmp)
            client = a_client(tmp, logger=logger)
            write_recording(client.path_for(ctx), ctx)
            client.generate(ctx)
            row = next(r for r in read_log(logger) if r["event_type"] == "generation_request")
            self.assertEqual(row["request_sha256"], f"sha256:{ctx.sha256()}")


class ContextTests(unittest.TestCase):
    def test_the_hash_is_stable_for_the_same_content(self) -> None:
        self.assertEqual(a_context().sha256(), a_context().sha256())

    def test_the_hash_changes_when_the_intent_changes(self) -> None:
        other = llm.Context(**{**a_context().__dict__, "intent": "something else"})
        self.assertNotEqual(a_context().sha256(), other.sha256())

    def test_the_hash_does_not_depend_on_the_absolute_path(self) -> None:
        self.assertNotIn("F:", a_context().sha256())

    def test_the_suggestion_id_is_derived_from_the_request(self) -> None:
        with scratch_dir() as tmp:
            ctx = a_context()
            client = a_client(tmp)
            write_recording(client.path_for(ctx), ctx)
            first = client.generate(ctx)
            second = client.generate(ctx)
            self.assertEqual(first.suggestion_id, second.suggestion_id)
            self.assertIn(ctx.sha256()[:12], first.suggestion_id)


class HygieneTests(unittest.TestCase):
    def test_no_temperature_or_seed_literals_outside_config(self) -> None:
        offenders = []
        for path in sorted((ROOT / "govern").glob("*.py")) + sorted((ROOT / "tools").glob("*.py")):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"\btemperature\b", line) and re.search(r"\d", line):
                    offenders.append(f"{path.name}:{lineno}: {line.strip()}")
                if re.search(r"\bseed\b", line) and re.search(r"=\s*\d", line):
                    offenders.append(f"{path.name}:{lineno}: {line.strip()}")
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_no_endpoint_or_key_literal_in_the_code(self) -> None:
        offenders = []
        for path in sorted((ROOT / "govern").glob("*.py")) + sorted((ROOT / "tools").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for lineno, line in enumerate(text.splitlines(), 1):
                if "https://" in line or "sk-" in line:
                    offenders.append(f"{path.name}:{lineno}: {line.strip()}")
        self.assertEqual(offenders, [], "\n".join(offenders))

    def test_the_repository_ships_one_recording_per_task(self) -> None:
        tasks = [p.name for p in (ROOT / "corpus").glob("T-*")]
        shipped = {p.stem for p in (ROOT / "recordings").glob("*/*.json")}
        self.assertEqual(len(tasks), 6)
        self.assertGreaterEqual(len(shipped), 6, f"recordings: {sorted(shipped)}")

    def test_shipped_recordings_declare_their_source(self) -> None:
        for path in sorted((ROOT / "recordings").glob("*/*.json")):
            body = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn(body["source"], {"sim", "live"}, path.name)
            self.assertEqual(body["format"], "recording/1")

    def test_the_shipped_recordings_match_the_factory(self) -> None:
        from tools import make_recordings

        built = make_recordings.build()
        on_disk = {
            path.relative_to(ROOT / "recordings").as_posix(): path.read_bytes()
            for path in (ROOT / "recordings").rglob("*.json")
        }
        self.assertEqual(sorted(built), sorted(on_disk))
        for name, blob in built.items():
            self.assertEqual(blob, on_disk[name], name)

    def test_every_shipped_suggestion_omits_at_least_one_consumer(self) -> None:
        from tools import make_recordings

        for task in tasks.load_index(ROOT / "corpus"):
            diff = make_recordings.suggest(task)["patch_diff"]
            gold = patch_mod.changed_files(task.gold_patch.read_text(encoding="utf-8"))
            self.assertLess(
                len(patch_mod.changed_files(diff)),
                len(gold),
                f"{task.task_id}: the simulated suggestion is not partial",
            )


class CliTests(unittest.TestCase):
    def test_selftest_names_the_coverage(self) -> None:
        import io
        from contextlib import redirect_stdout

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = llm.main(["--selftest"])
        self.assertEqual(code, 0)
        self.assertIn("replay", buffer.getvalue())
        self.assertIn("identical", buffer.getvalue())


def llm_test_logger(tmp: Path):
    from govern import log

    return log.Logger(
        tmp,
        {
            "session_id": "S-LLM-01",
            "participant_id": "P01",
            "condition": "C1",
            "app_version": "0.0.0-test",
            "model_id": CFG.model_id,
            "model_temperature": 0.2,
            "seed": 42,
        },
    )


def read_log(logger) -> list[dict]:
    return [json.loads(line) for line in logger.path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    unittest.main()
