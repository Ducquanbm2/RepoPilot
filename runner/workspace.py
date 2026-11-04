"""
runner/workspace.py
Ephemeral Workspace Lifecycle Management (Isolated Single-Use Workspaces)
Owner: Person B (Runtime & Platform Lead)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


def _force_rmtree(target_path: Path | str) -> None:
    """Recursively removes a directory tree, forcefully unlocking Windows read-only files if needed.
    
    Supports both Python 3.12+ (onexc) and older versions (onerror) cleanly.
    """
    path = Path(target_path)
    if not path.exists():
        return

    def _unlock_and_remove(func, fpath, exc_info):
        try:
            os.chmod(fpath, 0o777)
            func(fpath)
        except Exception:
            pass

    try:
        shutil.rmtree(path, onexc=lambda func, fpath, exc: _unlock_and_remove(func, fpath, None))
    except TypeError:
        shutil.rmtree(path, onerror=_unlock_and_remove)


class EphemeralWorkspace:
    """Creates and cleans up a temporary isolated workspace per test run.
    
    Guarantees:
    1. Zero mutation on the original repository (clean isolation).
    2. Exact checkout of the required commit SHA.
    3. Deterministic teardown and cleanup after execution.
    """

    def __init__(self, base_repo_path: Path | str, commit_sha: str):
        self.base_repo_path = Path(base_repo_path).resolve()
        self.commit_sha = commit_sha
        self.temp_dir: Path | None = None
        self._used_worktree: bool = False

    def create(self) -> Path:
        """Creates an ephemeral workspace and checks out the specified commit SHA."""
        if not (self.base_repo_path / ".git").exists():
            raise ValueError(f"Path is not a git repository: {self.base_repo_path}")

        # 1. Create a unique temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="repopilot_ws_")).resolve()

        # 2. Prefer 'git worktree add --detach' for fast, lightweight isolated checkouts
        cmd = [
            "git", "-C", str(self.base_repo_path),
            "worktree", "add", "--detach", str(self.temp_dir), self.commit_sha
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            self._used_worktree = True
        else:
            # Fallback: If git worktree fails, clean up any partially created files forcefully,
            # copy the repository and check out commit_sha
            _force_rmtree(self.temp_dir)
            self.temp_dir = Path(tempfile.mkdtemp(prefix="repopilot_ws_")).resolve()
            shutil.copytree(self.base_repo_path, self.temp_dir, dirs_exist_ok=True)
            subprocess.run(
                ["git", "-C", str(self.temp_dir), "checkout", "-f", self.commit_sha],
                capture_output=True, text=True, check=True
            )
            self._used_worktree = False

        return self.temp_dir

    def cleanup(self) -> None:
        """Deterministically removes temporary directories and unregisters git worktree."""
        if not self.temp_dir or not self.temp_dir.exists():
            return

        if self._used_worktree:
            # Deregister worktree from git
            subprocess.run(
                ["git", "-C", str(self.base_repo_path), "worktree", "remove", "--force", str(self.temp_dir)],
                capture_output=True, text=True
            )
            subprocess.run(
                ["git", "-C", str(self.base_repo_path), "worktree", "prune"],
                capture_output=True, text=True
            )

        # Forcefully remove temporary directory from disk
        _force_rmtree(self.temp_dir)
        self.temp_dir = None


@contextmanager
def ephemeral_workspace(base_repo_path: Path | str, commit_sha: str) -> Generator[Path, None, None]:
    """Context manager supporting 'with ephemeral_workspace(...) as ws_path:' syntax."""
    ws = EphemeralWorkspace(base_repo_path, commit_sha)
    path = ws.create()
    try:
        yield path
    finally:
        ws.cleanup()
