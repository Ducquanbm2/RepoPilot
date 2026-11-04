from unittest.mock import Mock, patch

import pytest

from orchestrator.src import cli


@pytest.mark.parametrize(
    ("status", "expected_exit"),
    [("retrieved", 0), ("tests_passed", 0), ("tests_failed", 1)],
)
def test_cli_exit_matches_workflow_status(status, expected_exit, tmp_path):
    instance = tmp_path / "instance.json"
    instance.write_text('{"base_commit": "base"}', encoding="utf-8")
    log = tmp_path / "workflow.json"
    result = Mock()
    result.to_dict.return_value = {"instance_id": "demo", "status": status}
    with patch.object(cli, "run_instance", return_value=result), patch(
        "sys.argv", ["cli", str(instance), str(tmp_path), "--log", str(log)]
    ):
        assert cli.main() == expected_exit
    assert log.is_file()
    assert (tmp_path / "run_manifest.json").is_file()
