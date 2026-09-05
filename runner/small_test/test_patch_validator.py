"""
runner/small_test/test_patch_validator.py
Unit tests for PatchValidator
"""
from pathlib import Path
from runner.validators.patch_validator import PatchValidator


def test_valid_patch():
    valid_diff = """diff --git a/zapcore/sampler.go b/zapcore/sampler.go
index 10b1fe4..9367581 100644
--- a/zapcore/sampler.go
+++ b/zapcore/sampler.go
@@ -30,2 +30,3 @@ type Sampler struct {
+	dropAll bool
 }
"""
    validator = PatchValidator()
    result = validator.validate_content(valid_diff)
    assert result.is_valid is True
    assert result.error_message is None
    assert "zapcore/sampler.go" in result.modified_files
    assert result.lines_added == 1
    assert result.lines_removed == 0
    print("  [PASS] test_valid_patch")


def test_binary_patch_rejected():
    binary_diff = """diff --git a/logo.png b/logo.png
GIT binary patch
literal 12345
zc$@#%
"""
    validator = PatchValidator()
    result = validator.validate_content(binary_diff)
    assert result.is_valid is False
    assert "binary" in (result.error_message or "").lower()
    print("  [PASS] test_binary_patch_rejected")


def test_null_byte_binary_rejected():
    null_byte_diff = "diff --git a/foo.go b/foo.go\n+\x00\x01\x02binary\n"
    validator = PatchValidator()
    result = validator.validate_content(null_byte_diff)
    assert result.is_valid is False
    assert "null bytes" in (result.error_message or "").lower()
    print("  [PASS] test_null_byte_binary_rejected")


def test_path_traversal_rejected():
    dangerous_diff = """diff --git a/safe.go b/../../etc/passwd
--- a/safe.go
+++ b/../../etc/passwd
@@ -1 +1 @@
+malicious_line
"""
    validator = PatchValidator()
    result = validator.validate_content(dangerous_diff)
    assert result.is_valid is False
    assert "traversal" in (result.error_message or "").lower() or "dangerous" in (result.error_message or "").lower()
    print("  [PASS] test_path_traversal_rejected")


def test_max_lines_exceeded():
    large_diff = "diff --git a/foo.go b/foo.go\n" + "\n".join(["+line"] * 100)
    validator = PatchValidator(max_lines_changed=50)
    result = validator.validate_content(large_diff)
    assert result.is_valid is False
    assert "exceeded" in (result.error_message or "").lower()
    print("  [PASS] test_max_lines_exceeded")


def test_real_benchmark_patch_file():
    repo_root = Path(__file__).resolve().parent.parent.parent
    patch_file = repo_root / "benchmarks" / "patches" / "zap_9367581_test.patch"
    if not patch_file.exists():
        patch_file = repo_root / "benchmarks" / "patches" / "testify_4c4d011_test.patch"
    assert patch_file.exists(), f"Benchmark patch file not found: {patch_file}"

    validator = PatchValidator()
    result = validator.validate_file(patch_file)
    assert result.is_valid is True
    print(f"  [PASS] test_real_benchmark_patch_file ({patch_file.name})")


if __name__ == "__main__":
    print("Testing PatchValidator:")
    test_valid_patch()
    test_binary_patch_rejected()
    test_null_byte_binary_rejected()
    test_path_traversal_rejected()
    test_max_lines_exceeded()
    test_real_benchmark_patch_file()
    print("All PatchValidator tests passed!")
