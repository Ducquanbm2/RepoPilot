import json
import unittest
from unittest.mock import patch

from scripts import p2p_analyzer as analyzer


class P2PAnalyzerTests(unittest.TestCase):
    @patch("scripts.p2p_analyzer._run", return_value="pkg/a.go\npkg/a_test.go\nroot.go\n")
    def test_changed_go_dirs_excludes_test_files(self, run):
        self.assertEqual(analyzer._changed_go_dirs("repo", "b", "g"), [".", "./pkg"])
        run.assert_called_once()

    @patch("scripts.p2p_analyzer._changed_go_dirs", return_value=["./pkg"])
    @patch("scripts.p2p_analyzer._run", return_value="example.com/pkg\n")
    def test_direct_packages(self, run, _dirs):
        self.assertEqual(analyzer._direct_packages("repo", "b", "g"), {"example.com/pkg"})

    @patch("scripts.p2p_analyzer.subprocess.run")
    def test_package_metadata_decodes_json_stream(self, run):
        run.return_value.stdout = json.dumps({"ImportPath": "a"}) + "\n" + json.dumps({"ImportPath": "b"})
        self.assertEqual(analyzer._package_metadata("repo"), [{"ImportPath": "a"}, {"ImportPath": "b"}])

    def test_related_packages_walks_reverse_dependencies(self):
        metadata = [
            {"ImportPath": "a", "Imports": []},
            {"ImportPath": "b", "Imports": ["a"]},
            {"ImportPath": "c", "TestImports": ["b"]},
            {"ImportPath": "outside", "Imports": ["a"]},
        ]
        self.assertEqual(analyzer._related_packages(metadata, {"a"}), {"a", "b", "c", "outside"})

    @patch("scripts.p2p_analyzer.subprocess.run")
    def test_tests_for_package_filters_non_test_lines(self, run):
        run.return_value.stdout = "ok\nTestAlpha\nBenchmarkThing\nTestAlpha\nTest_2\n"
        self.assertEqual(analyzer._tests_for_package("repo", "pkg"), ["TestAlpha", "Test_2"])

    @patch("scripts.p2p_analyzer._tests_for_package", return_value=["TestA", "TestB"])
    @patch("scripts.p2p_analyzer._related_packages", return_value={"example.com/pkg"})
    @patch("scripts.p2p_analyzer._package_metadata", return_value=[])
    @patch("scripts.p2p_analyzer._direct_packages", return_value={"example.com/pkg"})
    def test_analyze_excludes_f2p_and_builds_command(self, _direct, _metadata, _related, _tests):
        result = analyzer.analyze_p2p("repo", "b", "g", ["TestA"])
        self.assertEqual(result["example.com/pkg"]["tests"], ["TestB"])
        self.assertEqual(result["example.com/pkg"]["command"], "go test example.com/pkg -run '^(TestB)$' -v")


if __name__ == "__main__":
    unittest.main()
