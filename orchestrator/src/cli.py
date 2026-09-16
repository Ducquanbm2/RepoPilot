"""CLI for the Week 2 retrieve -> inspect -> manual-patch workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .workflow import run_instance
from runner.manifest import RunManifest


def main() -> int:
    parser = argparse.ArgumentParser(description="RepoPilot Week 2 instance workflow")
    parser.add_argument("instance", type=Path, help="runtime instance JSON")
    parser.add_argument("workspace", type=Path, help="clean repository workspace")
    parser.add_argument("--patch", type=Path, help="human-authored unified diff")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--log", type=Path, help="write structured workflow output")
    args = parser.parse_args()
    result = run_instance(args.instance, args.workspace, patch_path=args.patch,
                          top_k=args.top_k, timeout_seconds=args.timeout_seconds).to_dict()
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)

    '''
    # Original log output without run_manifest stub:
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text(rendered + "\n", encoding="utf-8")
    '''

    # Write structured workflow output and generate run_manifest.json stub
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text(rendered + "\n", encoding="utf-8")

        # Generate and save run_manifest.json stub alongside log
        instance_data = json.loads(args.instance.read_text(encoding="utf-8"))
        manifest = RunManifest(
            run_id=f"run_{result['instance_id']}",
            instance_id=result["instance_id"],
            repo_sha=instance_data.get("base_commit", "unknown"),
            status=result["status"],
            runner_image="repopilot-runner:w1",
        )
        manifest_path = args.log.parent / "run_manifest.json"
        manifest.write_json(manifest_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
