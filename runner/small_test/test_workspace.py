"""
runner/small_test/test_workspace.py
Unit tests for EphemeralWorkspace lifecycle management
"""
import subprocess
from pathlib import Path
from runner.workspace import EphemeralWorkspace, ephemeral_workspace


def test_ephemeral_workspace_lifecycle():
    repo_root = Path(__file__).resolve().parent.parent.parent
    
    # Retrieve current HEAD commit SHA
    head_res = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True
    )
    current_sha = head_res.stdout.strip()

    ws = EphemeralWorkspace(base_repo_path=repo_root, commit_sha=current_sha)
    ws_path = ws.create()

    try:
        # Verify temporary directory exists and contains repo files
        assert ws_path.exists()
        assert (ws_path / "README.md").exists() or (ws_path / "Dockerfile").exists()
        print(f"  [PASS] EphemeralWorkspace created at: {ws_path}")
    finally:
        ws.cleanup()

    # Verify clean teardown
    assert not ws_path.exists()
    print("  [PASS] EphemeralWorkspace cleaned up successfully")


def test_context_manager():
    repo_root = Path(__file__).resolve().parent.parent.parent
    head_res = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True
    )
    current_sha = head_res.stdout.strip()

    captured_path = None
    with ephemeral_workspace(repo_root, current_sha) as ws_path:
        captured_path = ws_path
        assert ws_path.exists()

    assert not captured_path.exists()
    print("  [PASS] Context manager ephemeral_workspace auto-cleanup")


if __name__ == "__main__":
    print("Testing EphemeralWorkspace:")
    test_ephemeral_workspace_lifecycle()
    test_context_manager()
    print("All EphemeralWorkspace tests passed!")
