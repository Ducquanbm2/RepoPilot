"""
runner/executor.py
Isolated Execution in Docker Sandbox (Execution & Sandbox Runner)
Owner: Person B (Runtime & Platform Lead)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TestRunResult:
    status: str              # "passed" | "failed" | "timeout" | "docker_unavailable" | "error"
    exit_code: int | None
    duration_seconds: float
    output: str              # Bounded trích xuất stdout + stderr
    timed_out: bool
    runner_image: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "exit_code": self.exit_code,
            "duration_seconds": round(self.duration_seconds, 2),
            "output": self.output,
            "timed_out": self.timed_out,
            "runner_image": self.runner_image,
        }


class DockerSandboxRunner:
    """Controls Docker containers to execute tests within a safe, isolated environment.
    
    Security boundaries enforced since Week 1 & Week 2:
    - --network none: Cuts off all internet connectivity during test execution.
    - Resource capping (--memory, --cpus) to prevent host exhaustion.
    - Mounts isolated temporary /workspace directory.
    - Automatic timeout kills runaway or infinite-loop processes.
    - Caps output log size to prevent memory exhaustion.
    """

    def __init__(
        self,
        image_name: str = "repopilot-runner:w1",
        default_timeout: int = 180,
        memory_limit: str = "2g",
        cpu_limit: str = "2.0",
        max_output_chars: int = 20_000,
    ):
        self.image_name = image_name
        self.default_timeout = default_timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.max_output_chars = max_output_chars

    @staticmethod
    def is_docker_available() -> bool:
        """Checks if Docker CLI is installed and the Docker daemon is responding."""
        if not shutil.which("docker"):
            return False
        try:
            res = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            return res.returncode == 0
        except Exception:
            return False

    def build_docker_cmd(self, workspace: Path | str, test_command: str) -> list[str]:
        """Constructs standardized docker run command arguments."""
        abs_workspace = Path(workspace).resolve()
        ws_mount = str(abs_workspace)

        return [
            "docker", "run", "--rm",
            "--network", "none",
            f"--memory={self.memory_limit}",
            f"--cpus={self.cpu_limit}",
            "-v", f"{ws_mount}:/workspace:rw",
            "-w", "/workspace",
            self.image_name,
            "bash", "-c", test_command
        ]

    def apply_patch(self, workspace: Path | str, patch_path: Path | str) -> bool:
        """Applies a unified diff patch into the workspace using git apply."""
        abs_workspace = Path(workspace).resolve()
        abs_patch = Path(patch_path).resolve()

        cmd = ["git", "-C", str(abs_workspace), "apply", "--whitespace=nowarn", str(abs_patch)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to apply patch to workspace: {res.stderr or res.stdout}")
        return True

    def run_test(
        self,
        workspace: Path | str,
        test_command: str,
        timeout_seconds: int | None = None,
    ) -> TestRunResult:
        """Executes the test command inside the Docker Sandbox and captures results."""
        timeout = timeout_seconds if timeout_seconds is not None else self.default_timeout
        start_time = time.time()

        # Guard: check if Docker daemon is active
        if not self.is_docker_available():
            duration = time.time() - start_time
            return TestRunResult(
                status="docker_unavailable",
                exit_code=None,
                duration_seconds=duration,
                output="Docker daemon is not running or 'docker' command was not found. Please start Docker Desktop/daemon.",
                timed_out=False,
                runner_image=self.image_name,
            )

        cmd = self.build_docker_cmd(workspace, test_command)

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            duration = time.time() - start_time
            raw_output = (completed.stdout or "") + (completed.stderr or "")
            bounded_output = raw_output[-self.max_output_chars:]
            status = "passed" if completed.returncode == 0 else "failed"

            return TestRunResult(
                status=status,
                exit_code=completed.returncode,
                duration_seconds=duration,
                output=bounded_output,
                timed_out=False,
                runner_image=self.image_name,
            )

        except subprocess.TimeoutExpired as exc:
            duration = time.time() - start_time
            raw_output = ((exc.stdout or "") + (exc.stderr or ""))
            bounded_output = raw_output[-self.max_output_chars:]
            return TestRunResult(
                status="timeout",
                exit_code=None,
                duration_seconds=duration,
                output=bounded_output,
                timed_out=True,
                runner_image=self.image_name,
            )

        except Exception as exc:
            duration = time.time() - start_time
            return TestRunResult(
                status="error",
                exit_code=-1,
                duration_seconds=duration,
                output=f"Execution error while invoking sandbox runner: {str(exc)}",
                timed_out=False,
                runner_image=self.image_name,
            )
