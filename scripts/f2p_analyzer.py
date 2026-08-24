"""Discover fail-to-pass tests introduced or changed by a commit."""

from __future__ import annotations

import re
from pathlib import Path


TEST_DECLARATION = re.compile(
    r"^\+\s*func\s+(?:\([^)]*\)\s*)?(Test[A-Za-z0-9_]*)\s*\("
)


def analyze_f2p(repo_dir: Path | str, base_commit: str, gold_commit: str) -> list[str]:
    """Return test function names declared on added/changed diff lines."""
    import subprocess

    result = subprocess.run(
        [
            "git", "diff", "--no-ext-diff", base_commit, gold_commit, "--",
            "*_test.go",
        ],
        cwd=repo_dir,
        check=True,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    tests = {
        match.group(1)
        for line in result.stdout.splitlines()
        if not line.startswith("+++")
        for match in [TEST_DECLARATION.match(line)]
        if match
    }
    return sorted(tests)


# A descriptive alias for callers that prefer the module's terminology.
find_f2p_tests = analyze_f2p
