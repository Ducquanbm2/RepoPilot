#!/usr/bin/env python3
"""Audit a checked-out base workspace for benchmark data leakage."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = PROJECT_ROOT / "benchmarks" / "runtime_instances"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, text=True, encoding="utf-8",
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def audit(repo: Path, instance: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    head = _git(repo, "rev-parse", "HEAD")
    if head.returncode:
        return [f"not a git repository: {repo}"]
    actual_head = head.stdout.strip()
    if actual_head != instance["base_commit"] and not actual_head.startswith(instance["base_commit"]):
        failures.append(f"workspace HEAD is {actual_head}, expected base commit {instance['base_commit']}")
    status = _git(repo, "status", "--porcelain")
    if status.stdout.strip():
        failures.append("workspace has uncommitted changes")
    gold_reachable = _git(repo, "merge-base", "--is-ancestor", instance["gold_commit"], "HEAD")
    if gold_reachable.returncode == 0:
        failures.append(f"gold commit {instance['gold_commit']} is reachable from base workspace history")

    tests = instance.get("f2p_tests", [])
    if isinstance(tests, str):
        tests = [tests]
    patterns = [re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?" + re.escape(name) + r"\s*\(", re.M) for name in tests]
    tracked = _git(repo, "ls-files", "*.go").stdout.splitlines()
    for relative in tracked:
        path = repo / relative
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for name, pattern in zip(tests, patterns):
            if pattern.search(content):
                failures.append(f"F2P test {name} already exists in base workspace: {relative}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance_id", nargs="?")
    parser.add_argument("--instance-id", dest="instance_id_option")
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    parser.add_argument("--repo", type=Path, help="checked-out repository; defaults to cached benchmark repo")
    args = parser.parse_args()
    instance_id = args.instance_id_option or args.instance_id
    if not instance_id:
        parser.error("an instance ID is required")
    runtime_file = args.runtime_dir / f"{instance_id}.json"
    try:
        instance = json.loads(runtime_file.read_text(encoding="utf-8"))
        repo = args.repo or PROJECT_ROOT / "benchmarks" / "repos" / instance["repo_url"].rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
        failures = audit(repo, instance)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if failures:
        for failure in failures:
            print(f"Leakage detected: {failure}", file=sys.stderr)
        return 1
    print(f"leakage check passed: {instance_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
