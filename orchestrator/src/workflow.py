"""Deterministic Week 2 instance workflow.

The workflow retrieves context, applies a human-supplied patch, and invokes
the instance's targeted test command.  The test invocation is isolated in a
small adapter so it can later be replaced by Hải's runner without changing
retrieval or orchestration semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shlex
import subprocess
from typing import Any

from retrieval.src.lexical import LexicalRetriever, read_source


@dataclass(frozen=True)
class WorkflowResult:
    instance_id: str
    query: str
    retrieval: list[dict[str, Any]]
    patch_path: str | None
    test_command: str
    test_result: dict[str, Any] | None
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "query": self.query,
            "retrieval": self.retrieval,
            "patch_path": self.patch_path,
            "test_command": self.test_command,
            "test_result": self.test_result,
            "status": self.status,
        }


def load_instance(path: Path) -> dict[str, Any]:
    instance = json.loads(Path(path).read_text(encoding="utf-8"))
    required = ("instance_id", "repo_url", "base_commit", "test_command")
    missing = [field for field in required if not instance.get(field)]
    if missing:
        raise ValueError(f"runtime instance missing fields: {', '.join(missing)}")
    return instance


def apply_manual_patch(workspace: Path, patch_path: Path) -> None:
    """Apply exactly one operator-provided unified diff to a workspace."""

    workspace = Path(workspace).resolve()
    patch_path = Path(patch_path).resolve()
    if not patch_path.is_file():
        raise FileNotFoundError(patch_path)
    subprocess.run(["git", "-C", str(workspace), "apply", "--whitespace=nowarn", str(patch_path)], check=True)


def run_test_command(workspace: Path, command: str, *, timeout_seconds: int = 300,
                     max_output_chars: int = 20_000) -> dict[str, Any]:
    """Run a trusted runtime test command and return bounded structured output.

    ``shlex.split`` preserves quoted regex arguments while avoiding a shell
    invocation.  Runtime commands come from the repository's trusted metadata;
    callers still receive a timeout and bounded output for predictable runs.
    """

    argv = shlex.split(command)
    if not argv:
        raise ValueError("test command must not be empty")
    try:
        completed = subprocess.run(argv, cwd=workspace, capture_output=True, text=True,
                                   timeout=timeout_seconds, check=False)
        output = (completed.stdout + completed.stderr)[-max_output_chars:]
        return {"status": "passed" if completed.returncode == 0 else "failed",
                "exit_code": completed.returncode, "timed_out": False, "output": output}
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + (exc.stderr or ""))[-max_output_chars:]
        return {"status": "timeout", "exit_code": None, "timed_out": True, "output": output}


def run_instance(instance_path: Path, workspace: Path, *, patch_path: Path | None = None,
                 top_k: int = 10, timeout_seconds: int = 300) -> WorkflowResult:
    """Retrieve context, apply a patch, then run the targeted test command."""

    instance = load_instance(instance_path)
    query = str(instance.get("issue_description", instance.get("issue description", "")))
    retrieval = [item.to_dict() for item in LexicalRetriever(workspace).search(query, top_k=top_k)]
    test_result = None
    if patch_path is not None:
        apply_manual_patch(workspace, patch_path)
        test_result = run_test_command(workspace, instance["test_command"], timeout_seconds=timeout_seconds)
    status = "retrieved"
    if test_result is not None:
        status = "tests_passed" if test_result["status"] == "passed" else "tests_failed"
    return WorkflowResult(instance["instance_id"], query, retrieval,
                          str(patch_path) if patch_path else None,
                          instance["test_command"], test_result, status)


def inspect_source(workspace: Path, path: str, start_line: int = 1, end_line: int | None = None) -> dict:
    """Expose bounded source reading as the workflow's inspect step."""

    return read_source(workspace, path, start_line=start_line, end_line=end_line)
