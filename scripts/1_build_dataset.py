#!/usr/bin/env python3
"""Build test-only patches and sanitized runtime instance files."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    from .f2p_analyzer import analyze_f2p
    from .p2p_analyzer import analyze_p2p
except ImportError:  # Support direct execution: python scripts/1_build_dataset.py
    from f2p_analyzer import analyze_f2p
    from p2p_analyzer import analyze_p2p


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "benchmarks" / "manifests" / "manifest.yaml"
DEFAULT_REPOS_DIR = PROJECT_ROOT / "benchmarks" / "repos"
DEFAULT_PATCHES_DIR = PROJECT_ROOT / "benchmarks" / "patches"
DEFAULT_RUNTIME_DIR = PROJECT_ROOT / "benchmarks" / "runtime_instances"


def load_manifest(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read the benchmark manifest") from exc

    with path.open("r", encoding="utf-8") as manifest_file:
        document = yaml.safe_load(manifest_file)
    if not isinstance(document, dict) or not isinstance(document.get("instances"), list):
        raise ValueError("manifest must contain an 'instances' list")
    return document


def git(repo_dir: Path, *args: str, capture: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        check=True,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    return result.stdout if capture else ""


def repo_name(repo_url: str) -> str:
    name = Path(urlparse(repo_url).path).name
    if name.endswith(".git"):
        name = name[:-4]
    if not name:
        raise ValueError(f"cannot determine repository name from URL: {repo_url}")
    return name


def ensure_repository(instance: dict, repos_dir: Path) -> Path:
    destination = repos_dir / repo_name(instance["repo_url"])
    if not (destination / ".git").exists():
        repos_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", instance["repo_url"], str(destination)], check=True)
    else:
        git(destination, "fetch", "--all", "--tags", capture=False)
    return destination


def validate_instance(instance: dict) -> None:
    required = ("instance_id", "repo_url", "base_commit", "gold_commit", "test_command")
    missing = [field for field in required if not instance.get(field)]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")


def patch_path(instance: dict, project_root: Path, patches_dir: Path) -> Path:
    configured = instance.get("test_patch_path")
    return (project_root / configured) if configured else patches_dir / f"{instance['instance_id']}_test.patch"


def sanitized_runtime_instance(instance: dict, patch_file: Path, project_root: Path) -> dict:
    allowed = (
        "instance_id", "repo_url", "base_commit", "gold_commit", "test_command",
        "expected_failing_test", "issue description", "issue_description",
    )
    runtime = {key: instance[key] for key in allowed if key in instance}
    runtime["test_patch_path"] = patch_file.relative_to(project_root).as_posix()
    return runtime


def build_instance(instance: dict, args: argparse.Namespace) -> None:
    validate_instance(instance)
    repository = ensure_repository(instance, args.repos_dir)

    for commit in (instance["base_commit"], instance["gold_commit"]):
        git(repository, "cat-file", "-e", f"{commit}^{{commit}}")

    diff = git(
        repository,
        "diff",
        "--no-ext-diff",
        instance["base_commit"],
        instance["gold_commit"],
        "--",
        "*_test.go",
    )
    if not diff.strip():
        raise ValueError("gold commit contains no *_test.go changes")

    f2p_tests = analyze_f2p(repository, instance["base_commit"], instance["gold_commit"])
    p2p_specs = analyze_p2p(
        repository,
        instance["base_commit"],
        instance["gold_commit"],
        f2p_tests,
    )

    output_patch = patch_path(instance, args.project_root, args.patches_dir)
    output_patch.parent.mkdir(parents=True, exist_ok=True)
    output_patch.write_text(diff, encoding="utf-8")

    runtime_file = args.runtime_dir / f"{instance['instance_id']}.json"
    runtime_file.parent.mkdir(parents=True, exist_ok=True)
    runtime = sanitized_runtime_instance(instance, output_patch, args.project_root)
    runtime["f2p_tests"] = f2p_tests
    runtime["p2p_specs"] = p2p_specs
    runtime_file.write_text(
        json.dumps(
            runtime,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"built {instance['instance_id']}: {output_patch}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repos-dir", type=Path, default=DEFAULT_REPOS_DIR)
    parser.add_argument("--patches-dir", type=Path, default=DEFAULT_PATCHES_DIR)
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    parser.add_argument("--instance-id")
    args = parser.parse_args()
    args.project_root = PROJECT_ROOT

    try:
        manifest = load_manifest(args.manifest)
        instances = manifest["instances"]
        if args.instance_id:
            instances = [item for item in instances if item.get("instance_id") == args.instance_id]
            if not instances:
                raise ValueError(f"instance not found: {args.instance_id}")
        failures = 0
        for instance in instances:
            try:
                build_instance(instance, args)
            except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
                failures += 1
                print(f"skipped {instance.get('instance_id', '<unknown>')}: {exc}", file=sys.stderr)
        return 1 if failures else 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
