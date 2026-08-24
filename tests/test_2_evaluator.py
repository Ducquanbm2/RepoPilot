import importlib
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

evaluator = importlib.import_module("scripts.2_evaluator")


class EvaluatorTests(unittest.TestCase):
    def test_repository_name(self):
        self.assertEqual(evaluator.repository_name("https://github.com/a/project.git"), "project")

    def test_prepare_cleans_audits_and_applies_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repos/project"
            repo.mkdir(parents=True)
            patch_file = root / "test.patch"
            patch_file.write_text("patch", encoding="utf-8")
            instance = {"instance_id": "demo", "repo_url": "https://github.com/a/project.git", "base_commit": "base", "test_patch_path": str(patch_file), "test_command": "go test"}
            args = Namespace(repos_dir=root / "repos")
            with patch.object(evaluator, "run_git") as run_git, patch.object(evaluator, "audit", return_value=[]) as audit:
                result = evaluator.prepare(instance, args)
            self.assertEqual(result["status"], "prepared")
            self.assertEqual([call.args[1:] for call in run_git.call_args_list], [("reset", "--hard"), ("clean", "-fdx"), ("checkout", "base"), ("apply", str(patch_file))])
            audit.assert_called_once_with(repo, instance)

    def test_main_returns_one_on_prepare_error(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "runtime"
            runtime.mkdir()
            (runtime / "demo.json").write_text("{}", encoding="utf-8")
            with patch.object(evaluator, "prepare", side_effect=RuntimeError("bad workspace")), patch("sys.argv", ["2_evaluator", "demo", "--runtime-dir", str(runtime)]):
                self.assertEqual(evaluator.main(), 1)

    def test_main_writes_execution_spec_on_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "runtime"
            runtime.mkdir()
            (runtime / "demo.json").write_text("{}", encoding="utf-8")
            output = root / "spec.json"
            spec = {"instance_id": "demo", "status": "prepared"}
            with patch.object(evaluator, "prepare", return_value=spec), patch.object(evaluator, "PROJECT_ROOT", root), patch("sys.argv", ["2_evaluator", "demo", "--runtime-dir", str(runtime), "--output", str(output)]):
                self.assertEqual(evaluator.main(), 0)
            self.assertEqual(output.read_text(encoding="utf-8").strip(), '{\n  "instance_id": "demo",\n  "status": "prepared"\n}')


if __name__ == "__main__":
    unittest.main()
