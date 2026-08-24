# Indexer (Go)

This directory contains the Go semantic-analysis and indexing component for RepoPilot.

## Week 1 Feasibility Spike: `cmd/spike-loader`

`cmd/spike-loader` is a standalone feasibility tool developed for Week 1 Track A evaluation. It uses `golang.org/x/tools/go/packages` to load, type-check, and extract a deterministic inventory of packages, declarations, imports, and interface definitions from a target Go repository.

### CLI Usage

```bash
# Basic usage from indexer-go/
go run ./cmd/spike-loader -repo <path-to-target-repo>

# Or with custom package pattern
go run ./cmd/spike-loader -repo <path-to-target-repo> -pattern ./...
```

### Output and Behavior

- **Standard Output (`stdout`)**: Deterministic JSON report containing package summaries, declaration counts, interface names, coarse source test inventory, and diagnostics.
- **Standard Error (`stderr`)**: Informational and fatal execution error logs.
- **Status Field**:
  - `status: "complete"` (exit code 0): All packages parsed and type-checked cleanly with 0 diagnostics.
  - `status: "partial"` (exit code 1): One or more packages contained parse/type errors or ill-typed packages. Diagnostics are captured in the JSON report.

### Scope Limitations and Non-Goals

- **Not Canonical Evidence Contract**: The JSON output produced by this spike is a local evaluation report, **not** the finalized `EvidenceRef` schema or canonical evidence model.
- **Source Test Inventory**: Counts of test files and test-like functions (`Test...`, `Benchmark...`, `Example...`, `Fuzz...`) represent coarse source-level inventory only and do not indicate executed tests or test pass rates.
- **Excluded Features**: SSA generation, call-graph construction (CHA/RTA/VTA), reference graphs, graph database storage, and incremental indexing are explicitly out of scope for this feasibility spike.
