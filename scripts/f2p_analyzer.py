"""Discover fail-to-pass tests introduced or changed by a commit."""

from __future__ import annotations

import re
from pathlib import Path


TEST_DECLARATION = re.compile(
    r"^\+\s*func\s+(?:\([^)]*\)\s*)?(Test[A-Za-z0-9_]*)\s*\("
)
HUNK_TEST_DECLARATION = re.compile(
    r"\bfunc\s+(?:\([^)]*\)\s*)?(Test[A-Za-z0-9_]*)\s*\("
)


def analyze_f2p(repo_dir: Path | str, base_commit: str, gold_commit: str) -> list[str]:
    """Return top-level test names added or modified by the commit.

    A unified diff normally places the enclosing function after ``@@``. A
    changed test body therefore has no added ``func`` line, so looking only at
    ``+func`` misses most modified tests. We inspect both added declarations
    and the function context on hunk headers/context lines.
    """
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
    tests: set[str] = set()
    hunks: list[list[str]] = []
    current: list[str] | None = None
    for line in result.stdout.splitlines():
        if line.startswith("@@"):
            current = [line]
            hunks.append(current)
        elif current is not None:
            current.append(line)

    # Keep the parser useful for minimal/synthetic diff fixtures that omit
    # hunk headers. Real ``git diff`` output always has them.
    if not hunks:
        return sorted(
            {
                match.group(1)
                for line in result.stdout.splitlines()
                if (match := TEST_DECLARATION.match(line))
            }
        )

    for hunk in hunks:
        header_match = HUNK_TEST_DECLARATION.search(hunk[0])
        active_test = header_match.group(1) if header_match else None
        added_tests = {
            match.group(1)
            for line in hunk
            if (match := TEST_DECLARATION.match(line))
        }
        tests.update(added_tests)
        has_deleted_source = any(
            line.startswith("-") and not line.startswith("---") and line[1:].strip()
            for line in hunk
        )

        # For modified bodies, a change belongs to the latest function
        # declaration in the hunk. If the hunk also adds a new function, do
        # not attribute separator lines before ``+func`` to the old function.
        saw_added_declaration = False
        for line in hunk[1:]:
            if line.startswith(("+++", "---")):
                continue
            if line.startswith(" "):
                match = HUNK_TEST_DECLARATION.search(line)
                if match:
                    active_test = match.group(1)
                continue
            match = TEST_DECLARATION.match(line)
            if match:
                active_test = match.group(1)
                saw_added_declaration = True
                continue
            if line.startswith(("+", "-")) and active_test:
                content = line[1:].strip()
                if content and (not added_tests or has_deleted_source) and not saw_added_declaration:
                    tests.add(active_test)
    return sorted(tests)


# A descriptive alias for callers that prefer the module's terminology.
find_f2p_tests = analyze_f2p
