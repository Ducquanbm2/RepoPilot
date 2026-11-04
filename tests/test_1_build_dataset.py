import importlib
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

builder = importlib.import_module("scripts.1_build_dataset")


class BuildDatasetTests(unittest.TestCase):
    def test_repo_name_validate_and_patch_path(self):
        self.assertEqual(builder.repo_name("https://github.com/uber-go/zap.git"), "zap")
        instance = {"instance_id": "demo", "repo_url": "x", "base_commit": "b", "gold_commit": "g", "test_command": "go test"}
        builder.validate_instance(instance)
        with self.assertRaises(ValueError):
            builder.validate_instance({})
        self.assertEqual(builder.patch_path(instance, Path("/project"), Path("/patches")), Path("/patches/demo_test.patch"))

    def test_sanitized_runtime_instance_keeps_only_allowed_fields(self):
        instance = {"instance_id": "x", "repo_url": "url", "base_commit": "b", "gold_commit": "g", "test_command": "go test", "secret": "remove"}
        result = builder.sanitized_runtime_instance(instance, Path("/project/patch.patch"), Path("/project"))
        self.assertNotIn("secret", result)
        self.assertEqual(result["test_patch_path"], "patch.patch")

    def test_main_parses_instance_id_and_succeeds(self):
        instance = {"instance_id": "demo"}
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.yml"
            manifest.write_text("instances: []", encoding="utf-8")
            with patch.object(builder, "load_manifest", return_value={"instances": [instance]}), patch.object(builder, "build_instance") as build, patch.object(sys, "argv", ["1_build_dataset", "--manifest", str(manifest), "--instance-id", "demo"]):
                self.assertEqual(builder.main(), 0)
            build.assert_called_once()

    def test_build_instance_creates_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            args = Namespace(
                repos_dir=root / "repos",
                patches_dir=root / "patches",
                runtime_dir=root / "runtime",
                gold_patches_dir=root / "artifacts/g0/gold",
                project_root=root,
            )
            instance = {"instance_id": "demo", "repo_url": "https://github.com/a/b.git", "base_commit": "b", "gold_commit": "g", "test_command": "go test", "issue_description": "Fix details"}
            with patch.object(builder, "analyze_p2p", return_value={}), patch.object(builder, "analyze_f2p", return_value=["TestAdded"]), patch.object(builder, "ensure_repository", return_value=repo), patch.object(builder, "git", side_effect=["", "", "TEST DIFF", "SOURCE DIFF"]):
                builder.build_instance(instance, args)
            self.assertTrue((root / "patches/demo_test.patch").is_file())
            self.assertTrue((root / "patches/f2p/demo_eval_f2p.patch").is_file())
            self.assertTrue((root / "artifacts/g0/gold/demo_gold_solution.patch").is_file())
            self.assertEqual((root / "runtime/demo.json").is_file(), True)
            self.assertEqual((root / "runtime/demo/problem_statement.md").read_text().strip(), "Fix details")
            runtime = json.loads((root / "runtime/demo.json").read_text())
            self.assertNotIn("gold_commit", runtime)
            self.assertNotIn("gold_solution_patch_path", runtime)


if __name__ == "__main__":
    unittest.main()
