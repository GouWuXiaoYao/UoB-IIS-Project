"""M6 = SPEC M3: the single LLM client.

Every model call in the project goes through :class:`Client`. The client has two
modes:

``live``
    POSTs to the provider named by ``A2_API_BASE`` with the key from
    ``A2_API_KEY`` and writes what came back into ``recordings/``. Nothing about
    the provider is stored in the repository: the endpoint and the key are read
    from the environment only (AGENTS.md rule 5).

``replay``
    The delivery default. Reads a recording, never opens a socket and never
    needs a key, which is what keeps "one command reproduces the run" true.

Errors carry a ``code`` so the session controller can log and continue rather
than crash: ``auth_missing``, ``endpoint_missing``, ``recording_missing``,
``transport_error``, ``schema_violation``.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from govern import config as config_mod
from govern import patch as patch_mod

RECORDING_FORMAT = "recording/1"
DEFAULT_RECORDINGS = Path("recordings")
DEFAULT_KEY_ENV = "A2_API_KEY"
DEFAULT_ENDPOINT_ENV = "A2_API_BASE"
HTTP_TIMEOUT_S = 60
REQUESTS_PER_SELFTEST = 10

SYSTEM_PROMPT = (
    "You are a refactoring assistant working inside an existing repository. "
    "Reply with JSON only: patch_diff (a unified diff), rationale_text, "
    "touched_symbols (list of dotted names) and layers (L1 short, L2 why)."
)


class LlmError(Exception):
    """Base class for every failure the client raises."""

    code = "llm_error"


class AuthMissing(LlmError):
    code = "auth_missing"


class EndpointMissing(LlmError):
    code = "endpoint_missing"


class RecordingMissing(LlmError):
    code = "recording_missing"


class TransportError(LlmError):
    code = "transport_error"


class SchemaViolation(LlmError):
    code = "schema_violation"


@dataclass(frozen=True)
class FileSlice:
    """One file as the model sees it: a repository-relative path and its text."""

    path: str
    text: str


@dataclass(frozen=True)
class Context:
    """Everything the model is allowed to see for one request."""

    task_id: str
    intent: str
    files: tuple[FileSlice, ...]
    symbols: tuple[str, ...]
    call_edges: tuple[tuple[str, str], ...]

    @classmethod
    def for_task(cls, task) -> "Context":
        """Build the context for a corpus task (deterministic, relative paths)."""
        repo = Path(task.repo)
        files: list[FileSlice] = []
        for path in sorted(repo.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            files.append(FileSlice(path.relative_to(repo).as_posix(), path.read_text(encoding="utf-8")))
        symbols: list[str] = []
        edges: set[tuple[str, str]] = set()
        for slice_ in files:
            module = slice_.path[: -len(".py")].replace("/", ".")
            for line in slice_.text.splitlines():
                stripped = line.strip()
                if stripped.startswith("def "):
                    symbols.append(f"{module}.{stripped[4:].split('(')[0].strip()}")
                elif stripped.startswith("class "):
                    symbols.append(f"{module}.{stripped[6:].split('(')[0].split(':')[0].strip()}")
                elif stripped.startswith("import "):
                    edges.add((module, stripped[len("import ") :].split()[0].split(".")[0]))
                elif stripped.startswith("from "):
                    edges.add((module, stripped[len("from ") :].split()[0].split(".")[0]))
        return cls(
            task_id=task.task_id,
            intent=task.intent,
            files=tuple(files),
            symbols=tuple(sorted(set(symbols))),
            call_edges=tuple(sorted(edges)),
        )

    def payload(self) -> dict[str, Any]:
        """Canonical request payload: the hash of this is the request hash."""
        return {
            "task_id": self.task_id,
            "intent": self.intent,
            "files": [{"path": f.path, "text": f.text} for f in self.files],
            "symbols": list(self.symbols),
            "call_edges": [list(edge) for edge in self.call_edges],
        }

    def sha256(self) -> str:
        """Hex digest of the canonical payload (paths are repository-relative)."""
        blob = json.dumps(self.payload(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def prompt(self) -> str:
        """The user message: intent, then each file, in sorted path order."""
        parts = [f"TASK {self.task_id}", f"INTENT: {self.intent}", "FILES:"]
        for slice_ in self.files:
            parts.append(f"--- {slice_.path} ---")
            parts.append(slice_.text.rstrip("\n"))
        return "\n".join(parts)


@dataclass(frozen=True)
class Suggestion:
    """The one structured object the rest of the system consumes."""

    suggestion_id: str
    patch_diff: str
    rationale_text: str
    touched_symbols: tuple[str, ...]
    layers: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "patch_diff": self.patch_diff,
            "rationale_text": self.rationale_text,
            "touched_symbols": list(self.touched_symbols),
            "layers": dict(self.layers),
        }

    def content_hash(self) -> str:
        """Hash of the content only: two replays must give the same value."""
        blob = json.dumps(
            {
                "patch_diff": self.patch_diff,
                "rationale_text": self.rationale_text,
                "touched_symbols": list(self.touched_symbols),
                "layers": dict(self.layers),
            },
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _parse_suggestion(payload: Any, suggestion_id: str) -> Suggestion:
    """Validate a provider/replay payload; raise SchemaViolation when it lies."""
    if not isinstance(payload, dict):
        raise SchemaViolation("reply is not a JSON object")
    missing = [k for k in ("patch_diff", "rationale_text", "touched_symbols") if k not in payload]
    if missing:
        raise SchemaViolation(f"reply is missing: {', '.join(missing)}")
    diff = payload["patch_diff"]
    rationale = payload["rationale_text"]
    touched = payload["touched_symbols"]
    layers = payload.get("layers", {})
    if not isinstance(diff, str) or not diff.strip():
        raise SchemaViolation("patch_diff must be a non-empty string")
    if not isinstance(rationale, str) or not rationale.strip():
        raise SchemaViolation("rationale_text must be a non-empty string")
    if not isinstance(touched, list) or not all(isinstance(item, str) for item in touched):
        raise SchemaViolation("touched_symbols must be a list of strings")
    if not isinstance(layers, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in layers.items()
    ):
        raise SchemaViolation("layers must map strings to strings")
    try:
        patch_mod.parse(diff)
    except patch_mod.PatchError as exc:
        raise SchemaViolation(f"patch_diff is not a usable unified diff: {exc}") from exc
    return Suggestion(
        suggestion_id=suggestion_id,
        patch_diff=diff,
        rationale_text=rationale,
        touched_symbols=tuple(touched),
        layers=dict(layers),
    )


class Client:
    """The only place in the project that talks to a model."""

    def __init__(
        self,
        config: config_mod.Config,
        mode: str = "replay",
        recordings: str | Path = DEFAULT_RECORDINGS,
        api_key_env: str = DEFAULT_KEY_ENV,
        logger=None,
    ) -> None:
        if mode not in ("replay", "live"):
            raise ValueError(f"unknown mode: {mode!r} (expected 'replay' or 'live')")
        self._config = config
        self.mode = mode
        self.recordings = Path(recordings)
        self.api_key_env = api_key_env
        self.logger = logger

    # -- paths -----------------------------------------------------------
    def path_for(self, ctx: Context) -> Path:
        return self.recordings / self._model_slug() / f"{ctx.sha256()}.json"

    def _model_slug(self) -> str:
        """A directory-safe form of the model id ('qwen2.5-coder:7b' -> ...-7b)."""
        return "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in self._config.model_id)

    # -- public entry point ----------------------------------------------
    def generate(self, ctx: Context) -> Suggestion:
        started = time.monotonic()
        suggestion: Suggestion | None = None
        failure: LlmError | None = None
        try:
            if self.mode == "live":
                suggestion = self._live(ctx)
            else:
                suggestion = self._replay(ctx)
        except LlmError as exc:
            failure = exc
            if isinstance(exc, SchemaViolation):
                self._integrity("schema_violation", ctx, str(exc))
        self._log_request(ctx, suggestion, int((time.monotonic() - started) * 1000))
        if failure is not None:
            raise failure
        assert suggestion is not None  # for type checkers
        return suggestion

    # -- replay ----------------------------------------------------------
    def _replay(self, ctx: Context) -> Suggestion:
        path = self.path_for(ctx)
        if not path.is_file():
            raise RecordingMissing(f"no recording for this request: {path}")
        body = json.loads(path.read_text(encoding="utf-8"))
        if body.get("format") != RECORDING_FORMAT:
            raise SchemaViolation(f"unsupported recording format: {body.get('format')!r}")
        recorded_model = body.get("model_id")
        if recorded_model != self._config.model_id:
            raise SchemaViolation(
                f"recording was made with model {recorded_model!r}, "
                f"but the session runs {self._config.model_id!r}"
            )
        declared = body.get("request_sha256")
        if declared != f"sha256:{ctx.sha256()}":
            raise SchemaViolation(f"recording was made for another request: {declared}")
        return _parse_suggestion(body.get("response"), self._suggestion_id(ctx))

    # -- live ------------------------------------------------------------
    def _live(self, ctx: Context) -> Suggestion:
        endpoint = os.environ.get(DEFAULT_ENDPOINT_ENV, "").strip()
        if not endpoint:
            raise EndpointMissing(f"{DEFAULT_ENDPOINT_ENV} is not set")
        key = os.environ.get(self.api_key_env, "").strip()
        if not key:
            raise AuthMissing(f"{self.api_key_env} is not set")

        body = json.dumps(self._request(ctx), ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            with exc:
                pass  # drain and close: an unclosed error body leaks a socket
            if exc.code in (401, 403):
                raise AuthMissing(f"provider refused the key: HTTP {exc.code}") from exc
            raise TransportError(f"provider returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise TransportError(f"provider unreachable: {exc.reason}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SchemaViolation(f"reply is not UTF-8 JSON: {exc}") from exc
        payload = self._unwrap(payload)
        suggestion = _parse_suggestion(payload, self._suggestion_id(ctx))
        self._record(ctx, payload, latency_ms)
        return suggestion

    def _request(self, ctx: Context) -> dict[str, Any]:
        return {
            "model": self._config.model_id,
            "temperature": self._config.temperature,
            "seed": self._config.seed,
            "max_tokens": self._config.max_tokens,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": ctx.prompt()},
            ],
        }

    @staticmethod
    def _unwrap(payload: Any) -> Any:
        """Accept either our flat object or a chat-completions style envelope."""
        if isinstance(payload, dict) and isinstance(payload.get("choices"), list) and payload["choices"]:
            message = payload["choices"][0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                try:
                    return json.loads(content)
                except json.JSONDecodeError as exc:
                    raise SchemaViolation(f"assistant content is not JSON: {exc}") from exc
        return payload

    def _record(self, ctx: Context, payload: Any, latency_ms: int) -> None:
        path = self.path_for(ctx)
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "format": RECORDING_FORMAT,
            "source": "live",
            "request_sha256": f"sha256:{ctx.sha256()}",
            "model_id": self._config.model_id,
            "model_temperature": self._config.temperature,
            "seed": self._config.seed,
            "latency_ms": latency_ms,
            "response": payload,
        }
        path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # -- events ----------------------------------------------------------
    @staticmethod
    def _suggestion_id(ctx: Context) -> str:
        return f"SUG-{ctx.sha256()[:12]}"

    def _log_request(self, ctx: Context, suggestion: Suggestion | None, latency_ms: int) -> None:
        if self.logger is None:
            return
        self.logger.emit(
            "generation_request",
            phase="generate",
            task_id=ctx.task_id,
            suggestion_id=suggestion.suggestion_id if suggestion else None,
            request_sha256=f"sha256:{ctx.sha256()}",
            mode=self.mode,
            latency_ms=latency_ms,
            tokens_in=None,
            tokens_out=None,
        )

    def _integrity(self, kind: str, ctx: Context, detail: str) -> None:
        if self.logger is None:
            return
        self.logger.emit(
            "integrity_event",
            phase="generate",
            task_id=ctx.task_id,
            kind=kind,
            detail_len=len(detail or ""),
            ref_event_id=None,
        )


def _selftest() -> int:
    """Replay the shipped recordings ten times each and show they agree."""
    from govern import tasks as tasks_mod

    root = Path(__file__).resolve().parent.parent
    cfg = config_mod.load(root / "config" / "config.json")
    client = Client(cfg, mode="replay", recordings=root / "recordings")
    tasks = tasks_mod.load_index(root / "corpus")
    if not tasks:
        print("FAIL: no tasks to replay")
        return 1
    stable = 0
    for task in tasks:
        ctx = Context.for_task(task)
        hashes = set()
        for _ in range(REQUESTS_PER_SELFTEST):
            suggestion = client.generate(ctx)
            hashes.add(suggestion.content_hash())
        if len(hashes) != 1:
            print(f"FAIL: {task.task_id} replay drifted: {sorted(hashes)}")
            return 1
        stable += 1
    print(
        f"ok: {stable} recordings, {REQUESTS_PER_SELFTEST} replays each, "
        f"{stable}/{stable} identical, no network used"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="govern.llm", description="LLM client (live/replay)")
    parser.add_argument("--selftest", action="store_true", help="replay every recording ten times")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
