#!/usr/bin/env python3
"""Small smoke test for the F2P/P2P analyzers against the cached zap repo."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from f2p_analyzer import analyze_f2p  # noqa: E402
from p2p_analyzer import analyze_p2p  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=PROJECT_ROOT / "benchmarks/repos/zap")
    parser.add_argument("--runtime", type=Path)
    args = parser.parse_args()

    f2p = analyze_f2p(args.repo, "10b1fe4", "9367581")
    assert "TestSamplerWithZeroThereafter" in f2p, f2p
    specs = analyze_p2p(args.repo, "10b1fe4", "9367581", f2p)
    assert all(test not in f2p for spec in specs.values() for test in spec["tests"])

    if args.runtime:
        runtime = json.loads(args.runtime.read_text(encoding="utf-8"))
        assert runtime["f2p_tests"] == f2p
        assert isinstance(runtime["p2p_specs"], dict)
    print(f"ok: {len(f2p)} F2P test(s), {len(specs)} P2P package(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
