"""
runner/small_test/test_executor.py
Unit tests for DockerSandboxRunner
"""
from pathlib import Path
from runner.executor import DockerSandboxRunner


def test_docker_command_construction():
    runner = DockerSandboxRunner(
        image_name="repopilot-runner:w1",
        memory_limit="1g",
        cpu_limit="1.5",
        default_timeout=60
    )
    workspace = Path("/tmp/mock_ws")
    cmd = runner.build_docker_cmd(workspace, "go test ./... -v")

    # Verify mandatory security flags are present
    assert "docker" in cmd[0]
    assert "--rm" in cmd
    assert "--network" in cmd
    assert "none" in cmd[cmd.index("--network") + 1]
    assert "--memory=1g" in cmd
    assert "--cpus=1.5" in cmd
    assert "-w" in cmd
    assert "/workspace" in cmd
    assert "repopilot-runner:w1" in cmd
    assert "go test ./... -v" in cmd[-1]
    print("  [PASS] test_docker_command_construction (all security flags present)")


def test_docker_availability_check():
    runner = DockerSandboxRunner()
    # is_docker_available must return a boolean without raising exceptions
    status = runner.is_docker_available()
    assert isinstance(status, bool)
    print(f"  [PASS] test_docker_availability_check (Docker online: {status})")


def test_graceful_handling_when_docker_offline():
    runner = DockerSandboxRunner()
    # If Docker is offline, run_test must return status="docker_unavailable" instead of crashing
    if not runner.is_docker_available():
        res = runner.run_test(Path("."), "echo test")
        assert res.status == "docker_unavailable"
        assert res.exit_code is None
        assert "docker" in res.output.lower()
        print("  [PASS] test_graceful_handling_when_docker_offline (graceful status returned)")
    else:
        print("  [SKIP] Docker is currently online, skipping offline test")


if __name__ == "__main__":
    print("Testing DockerSandboxRunner:")
    test_docker_command_construction()
    test_docker_availability_check()
    test_graceful_handling_when_docker_offline()
    print("All DockerSandboxRunner tests passed!")
