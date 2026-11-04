"""
runner/small_test/test_manifest.py
Unit tests for RunManifest stub generation
"""
import json
import tempfile
from pathlib import Path
from runner.manifest import RunManifest


def test_manifest_creation_and_serialization():
    manifest = RunManifest(
        run_id="run_test_001",
        instance_id="zap_9367581",
        repo_sha="10b1fe4",
        config_version="w2-v1",
        runner_image="repopilot-runner:w1",
        status="passed"
    )

    data = manifest.to_dict()
    assert data["run_id"] == "run_test_001"
    assert data["instance_id"] == "zap_9367581"
    assert data["repo_sha"] == "10b1fe4"
    assert data["status"] == "passed"
    assert "created_at" in data and len(data["created_at"]) > 0

    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = Path(tmpdir) / "run_manifest.json"
        manifest.write_json(json_file)

        assert json_file.exists()
        loaded = json.loads(json_file.read_text(encoding="utf-8"))
        assert loaded["run_id"] == "run_test_001"
        assert loaded["status"] == "passed"

    print("  [PASS] test_manifest_creation_and_serialization")


if __name__ == "__main__":
    print("Testing RunManifest:")
    test_manifest_creation_and_serialization()
    print("All RunManifest tests passed!")
