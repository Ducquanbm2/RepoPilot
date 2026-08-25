# Candidate Snapshots Metadata (Week 2)

This document records the repository snapshot states, pinned commit SHAs, host execution environment, and Go module directives used for Week 2 Track A `evidence.jsonl v0` generation.

---

## 1. Host Execution Environment

- **Go Version**: `go version go1.26.6 windows/amd64`
- **Operating System (`GOOS`)**: `windows`
- **Architecture (`GOARCH`)**: `amd64`
- **Cgo Enabled (`CGO_ENABLED`)**: `1`
- **Compiler/Toolchain**: standard Go toolchain (`go/packages` with `golang.org/x/tools v0.49.0`)

> **Note on Build-Universe Provenance**: Per W1 Evidence Contract Draft §17.3, build environment coordinates (`GOOS`, `GOARCH`, `CGO_ENABLED`) are recorded in dataset/environment metadata rather than injected per record to maintain cross-platform deterministic record hashing.

---

## 2. Candidate Repo A: uber-go/zap

- **Repository URL**: `https://github.com/uber-go/zap.git`
- **Pinned Commit SHA**: `018b91390e74732e9e40f8d356887b8d06461886`
- **Checked-out State**: Detached HEAD at `018b91390e74732e9e40f8d356887b8d06461886` (commit message: `fix: set content type for AtomicLevel HTTP responses (#1567)`)
- **Working Tree State**: Verified clean (`git status --porcelain` is empty)
- **Root Module Path**: `go.uber.org/zap`
- **Go Directive (`go.mod`)**: `go 1.19`
- **Local Clone Location**: `C:\Users\LOQ\repopilot-w1-candidates\zap` (strictly external to RepoPilot monorepo)

---

## 3. Candidate Repo B: stretchr/testify

- **Repository URL**: `https://github.com/stretchr/testify.git`
- **Pinned Commit SHA**: `959dbdacf1533e155162811ea90c90117a420463`
- **Checked-out State**: Detached HEAD at `959dbdacf1533e155162811ea90c90117a420463` (commit message: `Merge pull request #1935 from harryzcy/yaml-update`)
- **Working Tree State**: Verified clean (`git status --porcelain` is empty)
- **Root Module Path**: `github.com/stretchr/testify`
- **Go Directive (`go.mod`)**: `go 1.17`
- **Local Clone Location**: `C:\Users\LOQ\repopilot-w1-candidates\testify` (strictly external to RepoPilot monorepo)
