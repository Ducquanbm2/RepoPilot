import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import leakage_sanitizer as sanitizer


class LeakageSanitizerTests(unittest.TestCase):
    def test_sanitize_text_removes_sensitive_references_and_diff(self):
        source = (
            "See https://github.com/acme/repo/pull/42 deadbee1 and fix/zero-rate.\n"
            "diff --git a/x.go b/x.go\n--- a/x.go\n+++ b/x.go\n@@ -1 +1 @@\n-old\n+new\n"
            "Keep this explanation."
        )
        result = sanitizer.sanitize_text(source)
        self.assertNotIn("github.com/acme/repo/pull/42", result)
        self.assertNotIn("deadbee1", result)
        self.assertNotIn("fix/zero-rate", result)
        self.assertNotIn("diff --git", result)
        self.assertIn("Keep this explanation.", result)

    def test_load_manifest_uses_yaml_and_validates_shape(self):
        yaml = type("Yaml", (), {"safe_load": staticmethod(lambda stream: {"instances": [{"instance_id": "x"}]})})
        with patch.dict(sys.modules, {"yaml": yaml}), patch.object(Path, "open") as open_file:
            open_file.return_value.__enter__.return_value = "instances: []"
            self.assertEqual(sanitizer.load_manifest(Path("manifest.yml"))["instances"][0]["instance_id"], "x")

    @patch("scripts.leakage_sanitizer.analyze_f2p", return_value=["TestNew"])
    @patch("scripts.leakage_sanitizer._ensure_repo")
    @patch("scripts.leakage_sanitizer._git")
    def test_sanitize_instance_writes_patches_runtime_and_statement(self, git, ensure, analyze):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            (repo / ".git").mkdir(parents=True)
            ensure.return_value = repo
            git.side_effect = ["", "", "TEST PATCH", "GOLD PATCH"]
            instance = {"instance_id": "demo", "repo_url": "https://github.com/a/b.git", "base_commit": "base", "gold_commit": "gold", "issue_description": "fix/secret deadbeef"}
            sanitizer.sanitize_instance(instance, root / "repos", root / "patches", root / "runtime", root)
            self.assertIn("[REDACTED_BRANCH]", (root / "runtime/demo/problem_statement.md").read_text())
            runtime = json.loads((root / "runtime/demo.json").read_text())
            self.assertEqual(runtime["f2p_tests"], ["TestNew"])
            self.assertTrue((root / "patches/f2p/demo_eval_f2p.patch").is_file())
            self.assertTrue((root / "patches/gold/demo_gold_solution.patch").is_file())


if __name__ == "__main__":
    unittest.main()
