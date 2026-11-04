import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.f2p_analyzer import analyze_f2p, find_f2p_tests


class F2PAnalyzerTests(unittest.TestCase):
    @patch("subprocess.run")
    def test_finds_function_and_suite_tests(self, run):
        run.return_value.stdout = (
            "diff --git a/x_test.go b/x_test.go\n"
            "+++ b/x_test.go\n"
            "+func TestSimple(t *testing.T) {}\n"
            "+func (s *suite) TestSuite() {}\n"
            " func TestUnchanged(t *testing.T) {}\n"
        )
        self.assertEqual(analyze_f2p(Path("repo"), "base", "gold"), ["TestSimple", "TestSuite"])
        run.assert_called_once()

    @patch("subprocess.run")
    def test_empty_diff_returns_empty(self, run):
        run.return_value.stdout = ""
        self.assertEqual(find_f2p_tests("repo", "base", "gold"), [])

    @patch("subprocess.run")
    def test_finds_modified_test_from_hunk_context(self, run):
        run.return_value.stdout = (
            "diff --git a/x_test.go b/x_test.go\n"
            "@@ -10,3 +10,3 @@ func TestChanged(t *testing.T) {\n"
            "-\toldAssertion(t)\n"
            "+\tnewAssertion(t)\n"
        )
        self.assertEqual(analyze_f2p("repo", "base", "gold"), ["TestChanged"])

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git"))
    def test_git_error_is_propagated(self, _run):
        with self.assertRaises(subprocess.CalledProcessError):
            analyze_f2p("repo", "base", "gold")


if __name__ == "__main__":
    unittest.main()
