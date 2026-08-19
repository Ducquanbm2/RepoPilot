#!/usr/bin/env python3
"""Prepare a benchmark repository and emit an execution specification."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = PROJECT_ROOT / "benchmarks" / "runtime_instances"
DEFAULT_REPOS_DIR = PROJECT_ROOT / "benchmarks" / "repos"
DEFAULT_SPECS_DIR = PROJECT_ROOT / "benchmarks" / "execution_specs"


def repository_name(repo_url: str) -> str:
    name = Path(urlparse(repo_url).path).name
    return name[:-4] if name.endswith(".git") else name


def run_git(repository: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def prepare(instance: dict, args: argparse.Namespace) -> dict:
    repository = args.repos_dir / repository_name(instance["repo_url"])
    if not repository.is_dir():
        raise FileNotFoundError(f"Repository cache does not exist: {repository}")

    # Đọc trực tiếp test_patch_path đã được tính toán từ file Runtime JSON của Pha 1
    patch = Path(instance["test_patch_path"])
    if not patch.is_absolute():
        patch = PROJECT_ROOT / patch
    if not patch.is_file():
        raise FileNotFoundError(f"Test patch does not exist: {patch}")

    # 1. Dọn dẹp Workspace & Checkout Base Commit
    run_git(repository, "reset", "--hard")
    run_git(repository, "clean", "-fdx")
    run_git(repository, "checkout", instance["base_commit"])

    # 2. Áp dụng Test Patch
    run_git(repository, "apply", str(patch))

    return {
        "instance_id": instance["instance_id"],
        "repository": str(repository),
        "base_commit": instance["base_commit"],
        "test_patch_path": instance["test_patch_path"],
        "test_command": instance["test_command"],
        "expected_failing_test": instance.get("expected_failing_test"),
        "status": "prepared",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance_id", nargs="?", help="ID of the benchmark instance (e.g. zap_1033)")
    parser.add_argument("--instance-id", dest="instance_id_option", help="ID of the benchmark instance")
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    parser.add_argument("--repos-dir", type=Path, default=DEFAULT_REPOS_DIR)
    parser.add_argument("--output", type=Path)
    
    # 1. Parse argument từ Terminal trước
    args = parser.parse_args()
    args.project_root = PROJECT_ROOT
    args.instance_id = args.instance_id_option or args.instance_id
    if not args.instance_id:
        parser.error("an instance ID is required (positional or --instance-id)")

    try:
        runtime_file = args.runtime_dir / f"{args.instance_id}.json"
        if not runtime_file.is_file():
            raise FileNotFoundError(
                f"Runtime instance file not found: {runtime_file}. "
                f"Please run 'python -m scripts.1_build_dataset' first!"
            )

        with open(runtime_file, "r", encoding="utf-8") as f:
            instance = json.load(f)

        # 3. Chuẩn bị Workspace
        spec = prepare(instance, args)

        # 4. Ghi và In kết quả Execution Spec
        output = args.output or DEFAULT_SPECS_DIR / f"{args.instance_id}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        
        print(json.dumps(spec, indent=2, ensure_ascii=False))
        return 0

    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
