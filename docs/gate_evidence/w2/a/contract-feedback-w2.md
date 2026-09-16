# Week 2 Track A Contract Feedback & Design Decisions

This document details the concrete implementation decisions (`[W2-DRAFT-DECISION]`) introduced during Week 2 Track A exporter development (`indexer-go/cmd/evidence-export`), along with open questions submitted for Track B (Storage/Sandbox) and Track C (Retrieval/Benchmarks) review before Week 3 canonical schema freeze.

---

## 1. Concrete W2 Implementation Decisions

### 1.1 Addition of `object_id` Field & Relation Orientation Table
- **Decision**: Added a mandatory `object_id` field to the EvidenceRef record to represent directed relation targets.
- **Orientation Matrix**:
  - `DECLARES`: `subject_id` = `package:...`, `object_id` = `symbol:...` (location: declaration node range)
  - `DEFINED_IN`: `subject_id` = `symbol:...`, `object_id` = `file:...` (location: declaration node range)
  - `IMPORTS`: `subject_id` = `package:...` (importing), `object_id` = `package:...` (imported) (location: import-spec range)
- **Rationale**: Graph construction and relational ingest pipelines require two explicit entity endpoints per record. Representing both `DECLARES` and `DEFINED_IN` ensures bidirectional navigation without client-side inverse indexing.

### 1.2 Deterministic `evidence_id` Core Composition
- **Decision**: Computed `evidence_id` as:
  ```text
  core = join("\n", repo_id, commit_sha, relation, subject_id, object_id, path, str(start_line), str(end_line))
  evidence_id = "ev_" + lowercase_hex(SHA256(utf8(core)))
  ```
- **Rationale**: Including file path and line coordinates ensures that duplicate import declarations across multiple files within the same package produce distinct evidence IDs. Deliberately excluding `artifact_hash` and `schema_version` decouples entity identity from hashing algorithm versioning.

### 1.3 Unscoped Imported Package Identity (`IMPORTS`)
- **Decision**: In `IMPORTS` records, the `object_id` is formatted as `package:<go_import_path>` without `<repo_id>@<commit_sha>` scoping (e.g. `package:fmt`, `package:go.uber.org/zap/zapcore`).
- **Rationale**: The static AST loader cannot validate external dependencies or stdlib packages at this snapshot commit. Resolving external packages to specific repository commits is deferred to Week 3 typed-graph linkers.

### 1.4 Package-Scoped `init#N` Ordinal Disambiguation
- **Decision**: Multiple `init` functions within a package are named `init#0`, `init#1`, ... assigned in deterministic order (files sorted lexicographically by relative path, then source declaration order within each file).
- **Rationale**: Go permits multiple `init()` functions across files in a single package. Numbering by line numbers is strictly forbidden (violating stable identity); deterministic lexical ordinals provide stable, reproducible symbol identities.

### 1.5 Method Receiver Owner Base Name (Pointer-ness Omitted)
- **Decision**: Method symbol identities use `symbol:<repo_id>@<commit_sha>/<pkg_path>/method/<Owner>.<Name>`, unwrapping pointer (`*T`) and generic index expressions down to the base type identifier `T`.
- **Rationale**: Canonical method set resolution (`*T` vs `T`) is an open Week 3 question. Stripping pointer-ness prevents syntax fragmentation during initial extraction.

### 1.6 Non-GitHub / Fixture `repo_id` Using Module Path
- **Decision**: For local test fixtures or repositories lacking a standard GitHub remote URL, `repo_id` uses the Go module path (e.g. `example.com/analyzer_fixtures/type_error`).
- **Rationale**: Provides a valid URI-safe namespace for synthetic and local benchmark fixtures.

### 1.7 Diagnostics Envelope Delivery via Dedicated File (`-diag-out`)
- **Decision**: Delivered the diagnostics envelope to a dedicated JSON file specified by `-diag-out`, while evidence records stream strictly to `stdout` (single-line JSONL) and human logs to `stderr`.
- **Rationale**: Clean separation of data streams allows deterministic piping (`> evidence.jsonl`) without mixing diagnostic metadata or log messages into evidence streams.

---

## 2. Open Questions for Week 3 Review

- **`[OPEN W3-1]` Method Set Grammar**: Should pointer receivers be explicitly represented in symbol grammar (e.g. `method/(*T).M` vs `method/T.M`) or handled via relation attributes?
- **`[OPEN W3-2]` Build-Universe Tagging**: Should build constraints (`GOOS`, `GOARCH`, build tags) be attached to package identities or retained strictly in dataset-level manifests?
- **`[OPEN W3-3]` Top-Level Variables and Constants**: Should package-level `var` and `const` declarations be introduced into `symbol:...` grammar in Week 3, and how should multi-variable `var (a, b = 1, 2)` specs be addressed?
- **`[OPEN W3-4]` Canonical JSON Schema Lock**: Review of field types, enum constraints, and required fields across Track B (storage) and Track C (consumer/evaluator) before finalizing `contracts/evidence_ref.schema.json` in Week 3.
