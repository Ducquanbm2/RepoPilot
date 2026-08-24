"""Find regression tests affected by changed Go packages."""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def _run(repo_dir: Path | str, *args: str) -> str:
    result = subprocess.run(
        list(args), cwd=repo_dir, check=True, text=True, encoding="utf-8",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout


def _changed_go_dirs(repo_dir: Path | str, base_commit: str, gold_commit: str) -> list[str]:
    names = _run(repo_dir, "git", "diff", "--name-only", base_commit, gold_commit, "--", "*.go")
    dirs = set()
    for name in names.splitlines():
        if name.endswith("_test.go") or not name.endswith(".go"):
            continue
        parent = Path(name).parent.as_posix()
        dirs.add("." if parent == "." else f"./{parent}")
    return sorted(dirs)


def _direct_packages(repo_dir: Path | str, base_commit: str, gold_commit: str) -> set[str]:
    packages = set()
    for directory in _changed_go_dirs(repo_dir, base_commit, gold_commit):
        output = _run(repo_dir, "go", "list", "-find", "-f", "{{.ImportPath}}", directory)
        packages.update(line.strip() for line in output.splitlines() if line.strip())
    return packages


def _package_metadata(repo_dir: Path | str) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["go", "list", "-json", "./..."], cwd=repo_dir, check=True,
        text=True, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    decoder = json.JSONDecoder()
    packages = []
    offset = 0
    while offset < len(result.stdout):
        while offset < len(result.stdout) and result.stdout[offset].isspace():
            offset += 1
        if offset >= len(result.stdout):
            break
        package, end = decoder.raw_decode(result.stdout, offset)
        packages.append(package)
        offset = end
    return packages


def _related_packages(metadata: list[dict[str, Any]], direct: set[str]) -> set[str]:
    known = {item.get("ImportPath") for item in metadata}
    reverse: dict[str, set[str]] = defaultdict(set)
    for item in metadata:
        package = item.get("ImportPath")
        for field in ("Imports", "TestImports", "XTestImports"):
            for dependency in item.get(field, []) or []:
                if dependency in known and package:
                    reverse[dependency].add(package)

    related = set(direct) & known
    queue = deque(related)
    while queue:
        dependency = queue.popleft()
        for dependent in reverse[dependency]:
            if dependent not in related:
                related.add(dependent)
                queue.append(dependent)
    return related


def _tests_for_package(repo_dir: Path | str, package: str) -> list[str]:
    result = subprocess.run(
        ["go", "test", "-list", ".*", package], cwd=repo_dir,
        check=True, text=True, encoding="utf-8", stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    tests = set()
    for line in result.stdout.splitlines():
        candidate = line.strip()
        if re.fullmatch(r"Test[A-Za-z0-9_]+", candidate):
            tests.add(candidate)
    return sorted(tests)


def analyze_p2p(
    repo_dir: Path | str,
    base_commit: str,
    gold_commit: str,
    f2p_tests: list[str] | tuple[str, ...] | set[str] = (),
) -> dict[str, dict[str, Any]]:
    """Return related packages and runnable test selections, excluding F2P tests."""
    direct = _direct_packages(repo_dir, base_commit, gold_commit)
    metadata = _package_metadata(repo_dir)
    related = _related_packages(metadata, direct)
    excluded = set(f2p_tests)
    specs: dict[str, dict[str, Any]] = {}
    for package in sorted(related):
        tests = [test for test in _tests_for_package(repo_dir, package) if test not in excluded]
        if not tests:
            continue
        pattern = "^(" + "|".join(re.escape(test) for test in tests) + ")$"
        specs[package] = {
            "tests": tests,
            "command": f"go test {package} -run '{pattern}' -v",
        }
    return specs


find_p2p_specs = analyze_p2p
