#!/usr/bin/env python3
"""Sanitize issue prompts and split gold changes into isolated patches."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from .f2p_analyzer import analyze_f2p
except ImportError:  # Support direct execution.
    from f2p_analyzer import analyze_f2p


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "benchmarks" / "manifests" / "manifest.yaml"
DEFAULT_REPOS_DIR = PROJECT_ROOT / "benchmarks" / "repos"
DEFAULT_PATCHES_DIR = PROJECT_ROOT / "benchmarks" / "patches"
DEFAULT_RUNTIME_DIR = PROJECT_ROOT / "benchmarks" / "runtime_instances"

GITHUB_FIX_URL = re.compile(
    r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/"
    r"(?:pull|commit|issues)/[A-Za-z0-9_.-]+",
    re.IGNORECASE,
)
COMMIT_SHA = re.compile(r"\b[0-9a-fA-F]{7,40}\b")
FIX_BRANCH = re.compile(r"\b(?:fix|bugfix|patch|issue|feature)/[A-Za-z0-9_.-]+\b", re.I)


def sanitize_text(text: str) -> str:
    """Remove common references that reveal the reference solution."""
    text = GITHUB_FIX_URL.sub("[REDACTED_GITHUB_URL]", text)
    text = _remove_diff_blocks(text)
    text = FIX_BRANCH.sub("[REDACTED_BRANCH]", text)
    return COMMIT_SHA.sub("[REDACTED_SHA]", text)


def _remove_diff_blocks(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    in_diff = False
    for line in lines:
        if line.startswith("diff --git "):
            in_diff = True
            continue
        if in_diff:
            # A new prose line after a complete patch ends the block. Patch
            # metadata and hunks are otherwise intentionally discarded.
            if line.startswith((
                "diff --git ", "index ", "new file mode ", "deleted file mode ",
                "similarity index ", "rename from ", "rename to ",
                "--- ", "+++ ", "@@", "+", "-", " ",
            )) or not line.strip():
                continue
            in_diff = False
        kept.append(line)
    return "\n".join(kept).strip()


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read the benchmark manifest") from exc
    with path.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict) or not isinstance(document.get("instances"), list):
        raise ValueError("manifest must contain an 'instances' list")
    return document


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True, encoding="utf-8",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout


def _repo_name(url: str) -> str:
    name = url.rstrip("/").rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".git") else name


def _ensure_repo(instance: dict[str, Any], repos_dir: Path) -> Path:
    repo = repos_dir / _repo_name(instance["repo_url"])
    if not (repo / ".git").exists():
        repos_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", instance["repo_url"], str(repo)], check=True)
    else:
        _git(repo, "fetch", "--all", "--tags")
    return repo


def sanitize_instance(instance: dict[str, Any], repos_dir: Path, patches_dir: Path,
                      runtime_dir: Path, project_root: Path) -> None:
    for field in ("instance_id", "repo_url", "base_commit", "gold_commit"):
        if not instance.get(field):
            raise ValueError(f"missing required field: {field}")
    repo = _ensure_repo(instance, repos_dir)
    for commit in (instance["base_commit"], instance["gold_commit"]):
        _git(repo, "cat-file", "-e", f"{commit}^{{commit}}")

    instance_id = instance["instance_id"]
    f2p_patch = patches_dir / "f2p" / f"{instance_id}_eval_f2p.patch"
    gold_patch = patches_dir / "gold" / f"{instance_id}_gold_solution.patch"
    f2p_patch.parent.mkdir(parents=True, exist_ok=True)
    gold_patch.parent.mkdir(parents=True, exist_ok=True)
    f2p = _git(repo, "diff", "--no-ext-diff", instance["base_commit"], instance["gold_commit"], "--", "*_test.go")
    gold = _git(repo, "diff", "--no-ext-diff", instance["base_commit"], instance["gold_commit"], "--", "*.go", ":(exclude)*_test.go")
    f2p_patch.write_text(f2p, encoding="utf-8")
    gold_patch.write_text(gold, encoding="utf-8")

    raw_description = instance.get("issue_description", instance.get("issue description", ""))
    runtime_instance = {key: value for key, value in instance.items() if key not in {"issue description", "issue_description"}}
    runtime_instance["issue_description"] = raw_description
    runtime_instance["problem_statement_path"] = (runtime_dir / instance_id / "problem_statement.md").relative_to(project_root).as_posix()
    runtime_instance["eval_f2p_patch_path"] = f2p_patch.relative_to(project_root).as_posix()
    runtime_instance["gold_solution_patch_path"] = gold_patch.relative_to(project_root).as_posix()
    # Compatibility for older evaluator consumers.
    runtime_instance["test_patch_path"] = runtime_instance["eval_f2p_patch_path"]
    runtime_instance["f2p_tests"] = analyze_f2p(repo, instance["base_commit"], instance["gold_commit"])

    statement = runtime_dir / instance_id / "problem_statement.md"
    statement.parent.mkdir(parents=True, exist_ok=True)
    statement.write_text(sanitize_text(str(raw_description)) + "\n", encoding="utf-8")
    runtime_file = runtime_dir / f"{instance_id}.json"
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_file.write_text(json.dumps(runtime_instance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"built {instance_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repos-dir", type=Path, default=DEFAULT_REPOS_DIR)
    parser.add_argument("--patches-dir", type=Path, default=DEFAULT_PATCHES_DIR)
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    parser.add_argument("--instance-id")
    args = parser.parse_args()
    try:
        instances = load_manifest(args.manifest)["instances"]
        if args.instance_id:
            instances = [item for item in instances if item.get("instance_id") == args.instance_id]
            if not instances:
                raise ValueError(f"instance not found: {args.instance_id}")
        for instance in instances:
            sanitize_instance(instance, args.repos_dir, args.patches_dir, args.runtime_dir, PROJECT_ROOT)
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
