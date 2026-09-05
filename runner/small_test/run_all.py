"""
runner/small_test/run_all.py
Runner script to execute all small tests in runner/small_test/
"""
import sys
from pathlib import Path

# Ensure UTF-8 output across platforms
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runner.small_test.test_patch_validator import (
    test_valid_patch,
    test_binary_patch_rejected,
    test_null_byte_binary_rejected,
    test_path_traversal_rejected,
    test_max_lines_exceeded,
    test_real_benchmark_patch_file,
)
from runner.small_test.test_workspace import (
    test_ephemeral_workspace_lifecycle,
    test_context_manager,
)
from runner.small_test.test_executor import (
    test_docker_command_construction,
    test_docker_availability_check,
    test_graceful_handling_when_docker_offline,
)
from runner.small_test.test_manifest import (
    test_manifest_creation_and_serialization,
)


def run_suite():
    print("=" * 65)
    print("  RUNNING RUNNER SMALL TEST SUITE")
    print("=" * 65)

    tests = [
        ("PatchValidator - Valid Patch", test_valid_patch),
        ("PatchValidator - Binary Rejected", test_binary_patch_rejected),
        ("PatchValidator - Null Byte Binary Rejected", test_null_byte_binary_rejected),
        ("PatchValidator - Traversal Rejected", test_path_traversal_rejected),
        ("PatchValidator - Max Lines Exceeded", test_max_lines_exceeded),
        ("PatchValidator - Real Benchmark Patch", test_real_benchmark_patch_file),
        ("Workspace - Lifecycle", test_ephemeral_workspace_lifecycle),
        ("Workspace - Context Manager", test_context_manager),
        ("Executor - Docker Command Construction", test_docker_command_construction),
        ("Executor - Docker Availability Check", test_docker_availability_check),
        ("Executor - Graceful Offline Handling", test_graceful_handling_when_docker_offline),
        ("Manifest - Creation & Serialization", test_manifest_creation_and_serialization),
    ]

    passed = 0
    failed = 0

    for name, func in tests:
        print(f"\n[TEST] {name}:")
        try:
            func()
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {name}: {str(exc)}")
            failed += 1

    print("\n" + "=" * 65)
    print(f"  RESULTS: {passed}/{len(tests)} tests passed ({failed} failed)")
    print("=" * 65)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_suite())
