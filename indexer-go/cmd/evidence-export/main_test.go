package main

import (
	"path/filepath"
	"regexp"
	"testing"
)

func TestCountTotalLines(t *testing.T) {
	tests := []struct {
		name     string
		content  []byte
		expected int
	}{
		{"empty", []byte(""), 0},
		{"single_line_no_newline", []byte("package main"), 1},
		{"single_line_with_newline", []byte("package main\n"), 1},
		{"two_lines_no_trailing_newline", []byte("package main\nvar x = 1"), 2},
		{"two_lines_with_trailing_newline", []byte("package main\nvar x = 1\n"), 2},
		{"multiple_lines_with_newline", []byte("line1\nline2\nline3\n"), 3},
		{"multiple_lines_no_trailing_newline", []byte("line1\nline2\nline3"), 3},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := countTotalLines(tt.content)
			if got != tt.expected {
				t.Errorf("countTotalLines() = %d, expected %d", got, tt.expected)
			}
		})
	}
}

func TestNormalizeRepoPath(t *testing.T) {
	repoDir := filepath.Join("C:", "Users", "TestUser", "repo")

	t.Run("valid_subpath", func(t *testing.T) {
		absPath := filepath.Join(repoDir, "pkg", "service", "file.go")
		got, err := normalizeRepoPath(absPath, repoDir)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		expected := "pkg/service/file.go"
		if got != expected {
			t.Errorf("normalizeRepoPath() = %s, expected %s", got, expected)
		}
	})

	t.Run("reject_parent_traversal", func(t *testing.T) {
		absPath := filepath.Join("C:", "Users", "TestUser", "other", "file.go")
		_, err := normalizeRepoPath(absPath, repoDir)
		if err == nil {
			t.Error("expected error for path outside repo, got nil")
		}
	})
}

func TestComputeEvidenceID(t *testing.T) {
	pattern := regexp.MustCompile(`^ev_[a-f0-9]{64}$`)

	id1 := computeEvidenceID("uber-go/zap", "018b91390e74732e9e40f8d356887b8d06461886", "DECLARES",
		"package:uber-go/zap@018b9139:go.uber.org/zap/zapcore", "symbol:uber-go/zap@018b9139/go.uber.org/zap/zapcore/interface/Core", "zapcore/core.go", 42, 48)

	if !pattern.MatchString(id1) {
		t.Errorf("computeEvidenceID() format mismatch: got %s", id1)
	}

	// Determinism
	id2 := computeEvidenceID("uber-go/zap", "018b91390e74732e9e40f8d356887b8d06461886", "DECLARES",
		"package:uber-go/zap@018b9139:go.uber.org/zap/zapcore", "symbol:uber-go/zap@018b9139/go.uber.org/zap/zapcore/interface/Core", "zapcore/core.go", 42, 48)

	if id1 != id2 {
		t.Errorf("computeEvidenceID() is not deterministic: %s != %s", id1, id2)
	}

	// Different core -> different ID
	id3 := computeEvidenceID("uber-go/zap", "018b91390e74732e9e40f8d356887b8d06461886", "DEFINED_IN",
		"package:uber-go/zap@018b9139:go.uber.org/zap/zapcore", "symbol:uber-go/zap@018b9139/go.uber.org/zap/zapcore/interface/Core", "zapcore/core.go", 42, 48)

	if id1 == id3 {
		t.Errorf("computeEvidenceID() collision across different relations: %s", id1)
	}
}

func TestComputeArtifactHash(t *testing.T) {
	pattern := regexp.MustCompile(`^sha256:[a-f0-9]{64}$`)
	content := []byte("package main\n\nfunc main() {}\n")
	hash := computeArtifactHash(content)

	if !pattern.MatchString(hash) {
		t.Errorf("computeArtifactHash() format mismatch: got %s", hash)
	}
}
