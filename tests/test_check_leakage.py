import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.check_leakage import audit


class LeakageAuditTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Leakage Test")
        (self.repo / "sample.go").write_text("package sample\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        self.tempdir.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def instance(self):
        return {"base_commit": self.base, "gold_commit": "not-present", "f2p_tests": ["TestHidden"]}

    def test_clean_base_passes(self):
        self.assertEqual(audit(self.repo, self.instance()), [])

    def test_detects_dirty_wrong_head_and_reachable_gold(self):
        (self.repo / "dirty.txt").write_text("dirty", encoding="utf-8")
        self.git("checkout", "-b", "gold")
        self.git("add", "dirty.txt")
        self.git("commit", "-qm", "gold")
        gold = self.git("rev-parse", "HEAD").stdout.strip()
        (self.repo / "dirty.txt").write_text("changed after commit", encoding="utf-8")
        failures = audit(self.repo, {"base_commit": self.base, "gold_commit": gold})
        self.assertTrue(any("uncommitted" in item for item in failures))
        self.assertTrue(any("expected base" in item for item in failures))
        self.assertTrue(any("reachable" in item for item in failures))

    def test_detects_existing_f2p_test(self):
        (self.repo / "sample_test.go").write_text("package sample\nfunc TestHidden(t *testing.T) {}\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "hidden test")
        instance = self.instance()
        instance["base_commit"] = self.git("rev-parse", "HEAD").stdout.strip()
        self.assertTrue(any("TestHidden" in item for item in audit(self.repo, instance)))


if __name__ == "__main__":
    unittest.main()
