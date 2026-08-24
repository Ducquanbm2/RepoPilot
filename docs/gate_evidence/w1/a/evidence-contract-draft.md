# Week 1 Evidence Contract Draft (EvidenceRef & Diagnostics)

```text
Draft version: 0.1-draft
Status: W1 design draft, not canonical schema
DRI: Track A (Program Analysis & Semantic Indexing)
Required reviewer: Track B (Sandbox, Execution & Storage)
Integration consumer: Track C (Candidate Datasets & Benchmark Evaluation)
```

---

## 1. Purpose and Scope

The Evidence Contract defines the structured interface through which RepoPilot program-analysis, dynamic execution, and historical mining components record, store, and cite verifiable factual assertions about Go software repositories.

This contract exists so downstream components (retrieval engines, LLM orchestrators, evaluation harnesses, and human reviewers) can answer:
1. **What fact is being asserted?** (e.g., entity declaration, call relationship, test coverage, historical fix).
2. **About which repository snapshot?** (Exact Git commit object ID).
3. **About which entity?** (Canonical symbol, file, or package identity).
4. **Where is the supporting evidence?** (Normalized repository-relative file path and inclusive line span).
5. **How was that fact produced?** (Underlying static analysis, dynamic profiler, or VCS tool).
6. **What semantic strength does that method justify?** (Exact ground truth vs. conservative static over-approximation vs. dynamic runtime observation).
7. **Can another component independently validate the citation without trusting model generations?** (Reproducible verification against raw source bytes).

> `[SPEC REQUIRED]` This document defines the **v0.1-draft** specification for Week 1 exploration and Week 2 implementation (`evidence.jsonl v0`). It is **not** the finalized 1.0-rc canonical JSON Schema, which will be frozen in Week 3 following cross-track review.

---

## 2. Design Principles

### 2.1 Commit Provenance
`[SPEC REQUIRED]` All evidence is strictly commit-scoped. Every factual record is permanently bound to one full canonical Git commit object SHA. A fact extracted at Commit A must never silently be served or cited as evidence for Commit B, even if the source code appears unchanged.

### 2.2 Source Provenance & Location
`[SPEC REQUIRED]` Where source-backed evidence exists, locations are expressed as normalized repository-relative paths with 1-based inclusive line ranges. Machine-specific absolute paths (e.g., `C:\Users\...` or `/home/...`) and environment-dependent path separators (`\`) are strictly forbidden.

### 2.3 Method Provenance & Semantic Stratification
`[SPEC REQUIRED]` The contract strictly separates the asserted fact (the `relation`) from the technique used to derive it (`analysis_method`) and its resulting semantic guarantee (`evidence_class`).
- A static call edge (`CALLS_STATIC`) derived via direct syntax/type resolution is fundamentally distinct from a conservative reachability edge (`CALLS_POSSIBLE`) derived via Variable Type Analysis (VTA), and distinct from an observed execution trace (`CALLS_OBSERVED`).
- A conservative static relationship **must never** be represented as guaranteed runtime execution truth.

### 2.4 Fail-Closed Analysis & Diagnostics First-Class
`[SPEC REQUIRED]` If type-checking, AST parsing, or package loading encounters fatal or semantic-invalidating errors, analysis output must be explicitly marked `partial` or `failed`. Incomplete or ill-typed analysis must **never** be presented as complete evidence. Diagnostics are preserved with structured location and severity.

### 2.5 Model Does Not Author Evidence Truth
`[SPEC REQUIRED]` LLMs and agentic orchestrators may query, retrieve, and cite existing evidence records by `evidence_id`. However, an LLM **must never author, hallucinate, or alter**:
- Line ranges or file paths
- Symbol or entity identities
- Analysis methods or evidence classes
- Numeric confidence or probability scores (e.g., `confidence: 0.95`)

---

## 3. EvidenceRef Draft Record

The logical JSON structure of a single source-backed `EvidenceRef` record is defined as:

```json
{
  "evidence_id": "ev_a1b2c3d4e5f6",
  "repo_id": "uber-go/zap",
  "commit_sha": "018b91390e74732e9e40f8d356887b8d06461886",
  "path": "zapcore/core.go",
  "start_line": 42,
  "end_line": 48,
  "subject_id": "symbol:uber-go/zap@018b91390e74732e9e40f8d356887b8d06461886/go.uber.org/zap/zapcore/interface/Core",
  "relation": "DECLARES",
  "analysis_method": "go.types",
  "evidence_class": "EXACT_STATIC",
  "artifact_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "schema_version": "0.1-draft"
}
```

---

## 4. Field Semantics and Invariants

| Field Name | Type | Presence | Normalization / Invariant | What It MUST NOT Mean |
| :--- | :--- | :--- | :--- | :--- |
| `evidence_id` | `string` | **Required** | Deterministic prefix `ev_` followed by hash digest. Unique within commit dataset. | Must not be a random non-reproducible UUID. |
| `repo_id` | `string` | **Required** | Normalized canonical repository slug `owner/name` (e.g., `uber-go/zap`). Lowercase. | Must not contain local paths, branch names, or commit SHAs. |
| `commit_sha` | `string` | **Required** | Full canonical Git commit object ID (40-character hexadecimal SHA-1 or 64-character SHA-256). | Must not be an abbreviated SHA (e.g., `018b913`) or branch name. |
| `path` | `string` | **Required** | Repository-relative path using `/` separators. No leading `./` or `../`. | Must not contain OS drive letters or absolute host paths. |
| `start_line` | `integer` | **Required** | 1-based, inclusive line index. `start_line >= 1`. | Must not be 0 or negative. Does not define symbol identity. |
| `end_line` | `integer` | **Required** | 1-based, inclusive line index. `end_line >= start_line`. | Must not exceed total lines in source file at `commit_sha`. |
| `subject_id` | `string` | **Required** | Unambiguous identifier for the entity the evidence describes. | Must not be a free-form natural language label. |
| `relation` | `string` | **Required** | Canonical relation enum from the approved vocabulary (e.g., `DECLARES`, `CALLS_POSSIBLE`). | Must not be an ad-hoc or unconstrained string. |
| `analysis_method` | `string` | **Required** | Stable namespaced producer token (e.g., `go.types`, `callgraph.vta`, `runtime.coverage`). | Must not omit specific toolchain provenance. |
| `evidence_class` | `string` | **Required** | Enum: `EXACT_STATIC`, `CONSERVATIVE_STATIC`, `OBSERVED_DYNAMIC`, `HISTORICAL`, `RETRIEVAL_INFERENCE`. | Must not claim `EXACT_STATIC` for conservative over-approximations. |
| `artifact_hash` | `string` | **Optional (W1) / Required (W2)** | Hash of supporting source file bytes at commit (`sha256:<hex>`). | Must not hash un-normalized in-memory objects. |
| `schema_version` | `string` | **Required** | Must be `"0.1-draft"` for W1/W2 artifacts. | Must not claim `"1.0"` or `"1.0-rc"` prior to Week 3 lock. |

---

## 5. FileIdentity Draft

`[SPEC REQUIRED]` File identity represents a specific source file within a specific repository commit.

### Logical Representation
```json
{
  "repo_id": "uber-go/zap",
  "commit_sha": "018b91390e74732e9e40f8d356887b8d06461886",
  "path": "zapcore/core.go"
}
```

### Proposed String Serialization `[OPEN W2/W3]`
```text
file:<repo_id>@<commit_sha>:<path>
```
*Example*: `file:uber-go/zap@018b91390e74732e9e40f8d356887b8d06461886:zapcore/core.go`

### Invariants:
1. Two distinct commits produce two distinct `FileIdentity` records even if file bytes are identical.
2. Renaming a file across commits produces a distinct commit-scoped `FileIdentity`.
3. Host filesystem paths, line spans, and drive letters **never** enter FileIdentity.

---

## 6. SymbolIdentity Draft

`[SPEC REQUIRED]` Symbol identity represents a named code entity (function, method, type, interface) within a Go package at a specific commit.
`[SPEC REQUIRED]` **Line numbers MUST NOT be used as symbol identity.** Source code formatting, line insertions, or comment shifts must not alter a symbol's conceptual identity.

### Logical Representation
```json
{
  "repo_id": "uber-go/zap",
  "commit_sha": "018b91390e74732e9e40f8d356887b8d06461886",
  "package_path": "go.uber.org/zap/zapcore",
  "kind": "method",
  "owner": "Core",
  "name": "Enabled"
}
```

### Proposed String Serialization `[OPEN W2/W3]`
```text
symbol:<repo_id>@<commit_sha>/<package_path>/<kind>/[<owner>.]<name>
```
*Examples*:
- Package Function: `symbol:uber-go/zap@018b9139.../go.uber.org/zap/function/New`
- Named Type: `symbol:uber-go/zap@018b9139.../go.uber.org/zap/zapcore/type/Level`
- Interface: `symbol:uber-go/zap@018b9139.../go.uber.org/zap/zapcore/interface/Core`
- Method: `symbol:uber-go/zap@018b9139.../go.uber.org/zap/zapcore/method/Core.Enabled`

### Symbol Kind Scope (W1/W2):
- `function`: Top-level package function (`*ast.FuncDecl` with `Recv == nil`).
- `method`: Receiver-bound method (`*ast.FuncDecl` with `Recv != nil`).
- `type`: Concrete struct or basic type declaration (`*ast.TypeSpec` with non-interface underlying type).
- `interface`: Interface type declaration (`*ast.TypeSpec` with `*types.Interface` underlying type).

---

## 7. Relation Vocabulary & Compatibility Matrix

| Relation | Semantic Meaning | Producer Stage | Allowed Evidence Class | W1 Spike Status |
| :--- | :--- | :--- | :--- | :--- |
| `DECLARES` | Package or File declares a Symbol entity | `go.types` / AST | `EXACT_STATIC` | Specified |
| `DEFINED_IN` | Symbol is located within a source file range | `go.types` / AST | `EXACT_STATIC` | Specified |
| `IMPORTS` | Package imports another Package | `go.packages` | `EXACT_STATIC` | Specified |
| `REFERENCES` | Source symbol syntactically references another symbol | `go.types` | `EXACT_STATIC` | Specified |
| `IMPLEMENTS` | Concrete type implements interface methods | `go.types` | `EXACT_STATIC` | Specified |
| `CALLS_STATIC` | Direct syntactic/static function or method invocation | AST / `go.types` | `EXACT_STATIC` | Future (W4) |
| `CALLS_POSSIBLE`| Conservative static call-graph reachability edge | VTA / RTA / CHA | `CONSERVATIVE_STATIC` | Future (W4) |
| `CALLS_OBSERVED`| Runtime execution observed dynamic call trace | Dynamic Tracer | `OBSERVED_DYNAMIC` | Future (W4) |
| `TEST_REFERENCES`| Test source statically references target symbol | AST / `go.types` | `EXACT_STATIC` | Specified |
| `TEST_COVERS` | Test execution dynamically covers source block | Coverage Profile | `OBSERVED_DYNAMIC` | Future (Track B) |
| `FAILS_BEFORE` | Test fails on base commit before patch | Benchmark Runner | `HISTORICAL` / `OBSERVED_DYNAMIC` | Track C Manifest |
| `PASSES_AFTER` | Test passes on gold commit after patch | Benchmark Runner | `HISTORICAL` / `OBSERVED_DYNAMIC` | Track C Manifest |
| `CHANGED_BY` | Source file/symbol modified by Git commit | `git.diff` | `HISTORICAL` | Specified |
| `FIXED_BY` | Issue or bug resolved by target patch | `git.log` / Issues | `HISTORICAL` | Specified |
| `BASED_ON` | Patch gold commit is based on parent commit | `git.merge_base` | `HISTORICAL` | Specified |

> `[SPEC REQUIRED]`
> - `CALLS_POSSIBLE` **MUST NOT** be represented as definite runtime call truth.
> - `TEST_REFERENCES` **MUST NOT** be represented as runtime coverage evidence.

---

## 8. Analysis Method and Evidence Class Semantics

### 8.1 Evidence Classes (`evidence_class`)

1. **`EXACT_STATIC`**:
   - Facts established definitively by language syntax and type rules within the analyzed universe.
   - *Examples*: Declaration spans, static import statements, explicit type definitions, resolved named symbol references.
2. **`CONSERVATIVE_STATIC`**:
   - Facts produced by static analysis models that intentionally over-approximate possible program states (sound/may-call approximations).
   - *Examples*: Call graph reachability from CHA, RTA, or VTA (`CALLS_POSSIBLE`).
3. **`OBSERVED_DYNAMIC`**:
   - Facts directly witnessed during concrete program execution under a specific test or runner environment.
   - *Examples*: Line coverage blocks (`TEST_COVERS`), dynamic function entry traces (`CALLS_OBSERVED`).
   - *Meaning*: "This execution path was traversed in this run", **not** "this happens in all runs".
4. **`HISTORICAL`**:
   - Facts derived from VCS commit graphs, historical diffs, and issue tracking.
   - *Examples*: File modifications in a pull request (`CHANGED_BY`), base/gold test execution assertions (`FAILS_BEFORE`).
5. **`RETRIEVAL_INFERENCE`**:
   - Facts or relevance associations inferred by semantic retrieval models or vector search algorithms.
   - *Constraint*: Must not be promoted to compiler-grade ground truth.

### 8.2 Analysis Methods (`analysis_method`)
`[DRAFT DECISION]` Analysis methods use structured namespaced identifiers:
- `go.ast`: Pure syntactic AST parsing without full type resolution.
- `go.types`: Full Go type-checker and symbol resolution.
- `callgraph.vta`: Variable Type Analysis call-graph construction.
- `callgraph.cha`: Class Hierarchy Analysis call-graph construction.
- `runtime.coverage`: Go test execution coverage profiles (`go test -coverprofile`).
- `git.diff`: Git object and tree diffing.

---

## 9. Source-Location Semantics

1. **Coordinate System**:
   - `start_line`: 1-based, inclusive line index of the first character of the entity.
   - `end_line`: 1-based, inclusive line index of the last character of the entity.
   - `start_line <= end_line`.
2. **Path Normalization**:
   - All paths are relative to the repository root at `commit_sha`.
   - Forward slashes (`/`) are used unconditionally, including on Windows environments.
3. **Columns `[DRAFT DECISION]`**:
   - Columns are omitted from the W1/W2 EvidenceRef baseline to prevent fragile whitespace sensitivity. Exact byte offsets and columns remain deferred to W3 if consumer requirements demand sub-line granularity.

---

## 10. Artifact Hash Semantics

`[SPEC REQUIRED]` The specification includes an `artifact_hash` field to ensure cryptographic traceability to underlying artifacts.

### Semantic Options Evaluated:
- **Option A (Supporting Source File Hash)**: SHA-256 digest of the raw source file bytes located at `path` within `commit_sha`.
- **Option B (Producer Artifact Hash)**: SHA-256 digest of the intermediate generator artifact (e.g., coverage output file, compilation log).
- **Option C (Evidence Record Hash)**: SHA-256 digest of the serialized canonical evidence record itself.

### Recommendation:
`[DRAFT DECISION]` **Option A is recommended for all source-backed static evidence.**
- `artifact_hash = "sha256:" + Hex(SHA256(RawBytes(path @ commit_sha)))`
- *Rationale*: Allows downstream consumers to verify that the cited source file has not suffered corruption, local modification, or branch drift without requiring access to intermediate indexer binaries.
- `[OPEN W3]` Non-source evidence (e.g., dynamic execution traces, benchmark runs) will define secondary artifact hashing rules in Week 3.

---

## 11. Diagnostics Contract

When package loading, parsing, or type-checking encounters errors, the analyzer emits a structured Diagnostics Envelope rather than failing silently.

### Diagnostics Envelope Shape
```json
{
  "repo_id": "uber-go/zap",
  "commit_sha": "018b91390e74732e9e40f8d356887b8d06461886",
  "status": "partial",
  "diagnostics": [
    {
      "stage": "typecheck",
      "package": "example.com/analyzer_fixtures/type_error",
      "path": "broken.go",
      "line": 5,
      "column": 9,
      "severity": "error",
      "message": "cannot use \"invalid string return\" (untyped string constant) as int value in return statement"
    }
  ],
  "schema_version": "0.1-draft"
}
```

### Diagnostic Field Definitions:
- `stage`: Pipeline stage where failure occurred: `load`, `parse`, `typecheck`, `analysis`.
- `package`: Go package import path experiencing the diagnostic.
- `path`: Repository-relative path to offending file (or `null` if load failure is package-wide).
- `line`: 1-based line number (or `null` if location unavailable).
- `column`: 1-based column number (or `null` if unavailable).
- `severity`: `"error"` (invalidates semantic completeness) or `"warning"`.
- `message`: Sanitized error message text.

---

## 12. Complete, Partial, and Failed Status Semantics

### 12.1 Status Definitions

- **`complete` (Exit Code 0)**:
  - All requested repository packages loaded, parsed, and type-checked cleanly with 0 semantic error diagnostics.
  - *Consumer Rule*: Consumers may ingest and trust all extracted evidence records within the analyzed scope.
- **`partial` (Exit Code 1)**:
  - Analyzer produced partial syntax or package inventory, but encountered at least one type, parse, or package resolution error (`pkg.IllTyped == true` or `len(pkg.Errors) > 0`).
  - *Consumer Rule*: Consumers **must not** treat the analysis as complete. Evidence records may be inspected for debugging, but completeness assertions are disallowed.
- **`failed` (Exit Code > 1)**:
  - Unrecoverable loader failure (e.g., invalid repository path, missing toolchain, corrupted Go module environment). No valid evidence records produced.
  - *Consumer Rule*: No evidence records accepted.

---

## 13. Determinism and Canonicalization Requirements

`[SPEC REQUIRED]` Given identical input repository snapshots and analysis parameters, evidence generation must be **byte-for-byte deterministic**.

### Canonicalization Invariants:
1. **Sorted Collections**: Packages, files, imports, symbol names, and diagnostics must be sorted lexicographically prior to encoding.
2. **Stable Identifiers**: Evidence IDs and Symbol IDs must be derived deterministically from canonical properties, not random UUIDs or runtime timestamps.
3. **Normalized Paths**: Windows path separators (`\`) must be converted to standard `/`.
4. **No Environmental Leaks**: Absolute host directories (`C:\...`, `/tmp/...`), CPU clock durations, and host usernames must never enter output records.

---

## 14. Validation Rules

| Level | Validation Rule | Pass Criteria | Violation Consequence |
| :--- | :--- | :--- | :--- |
| **Structural** | `evidence_id` non-empty | Matches `^ev_[a-f0-9]+$` | Record Rejected |
| **Structural** | `commit_sha` canonical | 40-char or 64-char hex string | Record Rejected |
| **Structural** | `path` normalized | Relative path, `/` only, no `.` or `..` segments | Record Rejected |
| **Structural** | `start_line` & `end_line` | `1 <= start_line <= end_line` | Record Rejected |
| **Relational** | `path` existence | File exists in repository at `commit_sha` | Provenance Invalid |
| **Relational** | `line_span` bounds | `end_line <= TotalLines(path @ commit_sha)` | Range Invalid |
| **Semantic** | Class-Relation Match | `CALLS_POSSIBLE` mapped to `CONSERVATIVE_STATIC` | Semantic Violation |
| **Semantic** | Dynamic Match | `TEST_COVERS` mapped to `OBSERVED_DYNAMIC` | Semantic Violation |

---

## 15. Worked Examples

### Example A: Exact Static Declaration (`DECLARES`)
```json
{
  "evidence_id": "ev_4f89a1c2",
  "repo_id": "uber-go/zap",
  "commit_sha": "018b91390e74732e9e40f8d356887b8d06461886",
  "path": "zapcore/sampler.go",
  "start_line": 40,
  "end_line": 48,
  "subject_id": "symbol:uber-go/zap@018b91390e74732e9e40f8d356887b8d06461886/go.uber.org/zap/zapcore/function/NewSamplerWithOptions",
  "relation": "DECLARES",
  "analysis_method": "go.types",
  "evidence_class": "EXACT_STATIC",
  "artifact_hash": "sha256:8b4c09...",
  "schema_version": "0.1-draft"
}
```

### Example B: Conservative Static Call Edge (`CALLS_POSSIBLE`)
```json
{
  "evidence_id": "ev_b731d8e4",
  "repo_id": "uber-go/zap",
  "commit_sha": "018b91390e74732e9e40f8d356887b8d06461886",
  "path": "logger.go",
  "start_line": 120,
  "end_line": 122,
  "subject_id": "symbol:uber-go/zap@018b91390e74732e9e40f8d356887b8d06461886/go.uber.org/zap/zapcore/interface/Core.Write",
  "relation": "CALLS_POSSIBLE",
  "analysis_method": "callgraph.vta",
  "evidence_class": "CONSERVATIVE_STATIC",
  "artifact_hash": "sha256:3a7d91...",
  "schema_version": "0.1-draft"
}
```

### Example C: Dynamic Runtime Test Coverage (`TEST_COVERS`)
```json
{
  "evidence_id": "ev_c912e5f0",
  "repo_id": "stretchr/testify",
  "commit_sha": "959dbdacf1533e155162811ea90c90117a420463",
  "path": "assert/assertions.go",
  "start_line": 140,
  "end_line": 155,
  "subject_id": "symbol:stretchr/testify@959dbdacf1533e155162811ea90c90117a420463/github.com/stretchr/testify/assert/function/Equal",
  "relation": "TEST_COVERS",
  "analysis_method": "runtime.coverage",
  "evidence_class": "OBSERVED_DYNAMIC",
  "artifact_hash": "sha256:7f14b2...",
  "schema_version": "0.1-draft"
}
```

### Example D: Historical Bug-Fix Evidence (`CHANGED_BY`)
```json
{
  "evidence_id": "ev_d019f3a8",
  "repo_id": "uber-go/zap",
  "commit_sha": "9367581ad2e434689582eb20f68ca9b65e73da55",
  "path": "zapcore/sampler.go",
  "start_line": 45,
  "end_line": 52,
  "subject_id": "file:uber-go/zap@9367581ad2e434689582eb20f68ca9b65e73da55:zapcore/sampler.go",
  "relation": "CHANGED_BY",
  "analysis_method": "git.diff",
  "evidence_class": "HISTORICAL",
  "artifact_hash": "sha256:9c21a4...",
  "schema_version": "0.1-draft"
}
```

### Example E: Controlled Negative Type-Error Fixture Diagnostics
*(Grounded directly in Track A fixture `fixtures/analyzer_fixtures/type_error/broken.go`)*
```json
{
  "repo_id": "example.com/analyzer_fixtures/type_error",
  "commit_sha": "uncommitted-fixture",
  "status": "partial",
  "diagnostics": [
    {
      "stage": "typecheck",
      "package": "example.com/analyzer_fixtures/type_error",
      "path": "broken.go",
      "line": 5,
      "column": 9,
      "severity": "error",
      "message": "cannot use \"invalid string return\" (untyped string constant) as int value in return statement"
    }
  ],
  "schema_version": "0.1-draft"
}
```

---

## 16. Examples That MUST Be Rejected

1. **Line-Number Embedded in Symbol ID**:
   - `INVALID`: `symbol:uber-go/zap/service.go:42:MyFunc`
   - *Reason*: Violates invariant that line numbers must not define symbol identity.
2. **Absolute Host File Path**:
   - `INVALID`: `path: "C:\\Users\\LOQ\\RepoPilot\\zapcore\\core.go"`
   - *Reason*: Leaks host environment; breaks repository portability.
3. **Abbreviated Commit SHA**:
   - `INVALID`: `commit_sha: "018b913"`
   - *Reason*: Ambiguous provenance. Must resolve to full canonical commit object ID.
4. **Conservative Edge Mislabeled Exact**:
   - `INVALID`: `relation: "CALLS_POSSIBLE"`, `evidence_class: "EXACT_STATIC"`
   - *Reason*: Conservative over-approximations must not claim exact compiler truth.
5. **Static Test Reference Mislabeled as Coverage**:
   - `INVALID`: `relation: "TEST_COVERS"`, `analysis_method: "go.ast"`
   - *Reason*: Syntactic test references are `TEST_REFERENCES` (`EXACT_STATIC`), not dynamic coverage.
6. **Model-Authored Confidence Score**:
   - `INVALID`: `confidence: 0.95`
   - *Reason*: Numeric model scores are not verified semantic evidence.
7. **Cross-Commit Drift**:
   - `INVALID`: `EvidenceRef.commit_sha = A`, but source cited is fetched from commit `B`.

---

## 17. Edge Cases and Unresolved Design Questions

### 17.1 Pointer vs. Value Method Receivers `[OPEN W3]`
- In Go, `func (t T) M()` and `func (t *T) M()` represent distinct method signatures.
- *Open Question*: Should receiver pointer-ness be encoded in the symbol string (`method/(*T).M` vs `method/T.M`) or resolved via underlying `types.Object` object-path mechanisms?

### 17.2 Multiple Package `init()` Functions `[OPEN W3]`
- Go allows multiple `init()` declarations within the same file and package.
- *Open Question*: Because line numbers cannot be used for identity, how should duplicate `init()` symbols be distinguished?
- *Candidates*: Stable AST ordinal within package (`init#0`, `init#1`), `types.Object` path, or explicit exclusion of anonymous/init lifecycle blocks from named Symbol scope.

### 17.3 Build Universe & Environment Variations `[OPEN W2/W3]`
- The same `repo_id + commit_sha` can yield different ASTs and package sets under varying `GOOS`, `GOARCH`, `CGO_ENABLED`, or build tags.
- *Open Question*: Does build-universe metadata belong in the `EvidenceRef` record, or in top-level dataset envelope metadata?

### 17.4 Non-Source Evidence Locations `[OPEN W3]`
- Historical commits, patch chunks, and test suites do not always map cleanly to `path:start_line:end_line`.
- *Open Question*: Should `EvidenceRef` introduce an abstract `Location` union in Week 3 to support diff offsets and test execution targets?

---

## 18. Week 2 Implementation Boundary

Track A will implement the following minimal subset in Week 2:
1. Extraction of `File`, `Package`, and named `Symbol` entities for Go codebases fixed at a commit.
2. Production of `evidence.jsonl v0` containing initial exact static relations (`DECLARES`, `DEFINED_IN`, `IMPORTS`).
3. Commit-scoped entity IDs and normalized repo-relative source ranges.
4. Fail-closed diagnostics emission when type errors occur.

---

## 19. Week 3 Canonicalization Boundary

The following decisions must be finalized in Week 3 cross-track review prior to 1.0-rc schema lock:
- Exact cryptographic hash algorithm for `evidence_id`.
- Receiver pointer notation and `init()` disambiguation grammar.
- Finalization of `artifact_hash` behavior for non-source artifacts.
- Build-universe provenance representation.
- JSON Schema definition in `contracts/evidence_ref.schema.json`.

---

## 20. Track B Review Checklist (Storage & Sandbox)

- [ ] Can evidence records be ingested into graph/relational storage without parsing unstructured text?
- [ ] Are required vs. optional fields unambiguous for database table schemas?
- [ ] Are line range and path validation rules implementable in ingestion pipelines?
- [ ] Is partial/failed analysis clearly distinguishable to prevent corrupted graph state?
- [ ] Can diagnostics be persisted alongside evidence without losing package context?
- [ ] Is `artifact_hash` verification implementable within the storage pipeline?

---

## 21. Track C Consumer Checklist (Retrieval & Benchmarks)

- [ ] Can retrieval components return `evidence_id` tokens directly without reconstructing file paths?
- [ ] Can citation validity be verified against exact repository snapshots?
- [ ] Does the separation between `EXACT_STATIC`, `CONSERVATIVE_STATIC`, and `OBSERVED_DYNAMIC` satisfy ranking and precision requirements?
- [ ] Are historical fix relations (`CHANGED_BY`, `FIXED_BY`) sufficiently distinct from runtime agent evidence?
- [ ] Can benchmark evaluation detect incomplete or partial analysis evidence?
