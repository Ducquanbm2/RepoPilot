# Week 2 Track A Evidence Generation & Verification Report

This report presents the generation metrics, determinism proofs, independent structural verification results, and W1 reconciliation analysis for `evidence.jsonl v0` generated from Candidate Repo A (`uber-go/zap`) and Candidate Repo B (`stretchr/testify`).

---

## 1. Executive Summary

- **Primary Question**: Can one deterministic exporter, following the W1 Evidence Contract Draft (v0.1-draft), produce commit-scoped `evidence.jsonl v0` (`DECLARES`, `DEFINED_IN`, `IMPORTS` with validated source ranges, Option-A artifact hashes, and fail-closed diagnostics) for `uber-go/zap` and `stretchr/testify` at their pinned W1 snapshot commits?
- **Conclusion**: **YES**. One unified Go exporter (`indexer-go/cmd/evidence-export`) successfully processed both repositories with zero repo-specific conditionals, achieving `status: "complete"`, exit code 0, 100% byte-for-byte run-over-run determinism, 100% structural validation pass rate, and exact reconciliation against Week 1 spike summaries.

---

## 2. Extraction & Inventory Metrics

| Metric | Candidate Repo A (`uber-go/zap`) | Candidate Repo B (`stretchr/testify`) |
|---|---|---|
| **Pinned Commit SHA** | `018b91390e74732e9e40f8d356887b8d06461886` | `959dbdacf1533e155162811ea90c90117a420463` |
| **Status / Exit Code** | `complete` / `0` | `complete` / `0` |
| **Total Evidence Records** | **1,674** | **1,854** |
| `DECLARES` Records | 754 | 873 |
| `DEFINED_IN` Records | 754 | 873 |
| `IMPORTS` Records | 166 | 108 |
| **Functions** | 216 | 408 |
| **Methods** | 404 | 406 |
| **Types (non-interface)** | 112 | 41 |
| **Interfaces** | 22 | 18 |
| **Total Symbols Extracted** | 754 | 873 |
| **Distinct Packages** | 15 | 10 |
| **Distinct Files with Records** | 55 | 26 |
| **Total Go Files in Module** | 59 (55 + 4 `doc.go`) | 34 (26 + 8 `doc.go`) |

---

## 3. Negative Fixture Verification (Fail-Closed Diagnostic Path)

Prior to candidate execution, the exporter was evaluated against the controlled type-error fixture `fixtures/analyzer_fixtures/type_error/` (`broken.go`) in an external Git repository:

- **Commit SHA**: `d53e7df11db4864c72ddec94b688048458c1547c`
- **Observed Exit Code**: `1` (predicted: `1`)
- **Envelope Status**: `partial` (predicted: `partial`)
- **Observed Diagnostics**:
  - `stage: "typecheck"`, `path: "broken.go"`, `line: 5`, `column: 9`, `severity: "error"`
  - `message: "cannot use \"invalid string return\" (untyped string constant) as int value in return statement"`
- **Extracted Records**: 2 records emitted for syntactically extractable declarations (`BrokenFunction` `DECLARES` and `DEFINED_IN`).

---

## 4. Determinism Verification (Byte-Identical Second Runs)

Each repository was exported twice into independent files and compared using SHA-256 digests:

| File | Run 1 SHA-256 Digest | Run 2 SHA-256 Digest | Match |
|---|---|---|---|
| `evidence-zap.jsonl` | `B6EB0C90267D54476D6303A40864806018DC554A70BDCF31CBC3969A64896383` | `B6EB0C90267D54476D6303A40864806018DC554A70BDCF31CBC3969A64896383` | **EXACT** |
| `diagnostics-zap.json` | `AFABD1BB6ED9E4A1F4B3B11AED81278BC4909B59C9DDDC3C9B17A37E1163ABE2` | `AFABD1BB6ED9E4A1F4B3B11AED81278BC4909B59C9DDDC3C9B17A37E1163ABE2` | **EXACT** |
| `evidence-testify.jsonl` | `1FFEA184744E6C0644B6652302400DE34E511B3CC175CF319EDC5EE1D8CDFD39` | `1FFEA184744E6C0644B6652302400DE34E511B3CC175CF319EDC5EE1D8CDFD39` | **EXACT** |
| `diagnostics-testify.json` | `5FEF9FC42C422A183353C6CB287080A751ED7F13045D1E48A94C6C41B2E6E6D4` | `5FEF9FC42C422A183353C6CB287080A751ED7F13045D1E48A94C6C41B2E6E6D4` | **EXACT** |

---

## 5. Independent Structural Validation (`scripts/validate_evidence_v0.ps1`)

An independent PowerShell validator verified every line of both outputs against strict schema and filesystem invariants:

1. **JSON Parsing**: 100% of records parse as valid JSON objects.
2. **Required Fields**: All 13 fields present in all 1,674 (`zap`) and 1,854 (`testify`) records.
3. **Evidence ID Format & Uniqueness**: 100% match `^ev_[a-f0-9]{64}$`; 0 duplicate IDs detected (1,674 unique in zap, 1,854 unique in testify).
4. **Commit SHA Consistency**: 100% match pinned commit SHA across all records.
5. **Path Normalization**: 0 unnormalized paths, 0 absolute paths, 0 drive letters, 0 backslashes.
6. **No Test Contamination**: 0 records referencing `_test.go` files.
7. **Line Bounds Validation**: 100% of records satisfy `1 <= start_line <= end_line <= totalLines` computed directly from repository files on disk.
8. **Option-A Artifact Hash Validation**: 100% of records have `artifact_hash` matching the SHA-256 byte digest of the referenced source file.
9. **Relation & Enum Invariants**: 100% match `relation` ∈ `{DECLARES, DEFINED_IN, IMPORTS}`, `evidence_class` = `EXACT_STATIC`, `analysis_method` = `go.types`, `schema_version` = `0.1-draft`.

---

## 6. Reconciliation Against W1 Spike Summaries

### 6.1 Symbol Count Reconciliation
- **Candidate Repo A (`uber-go/zap`)**:
  - W1 Spike Inventory: 216 functions + 404 methods + 134 types (including 22 interfaces) = **754 symbols**.
  - W2 `DECLARES` Records: **754** (Exact 1:1 match).
  - W2 `DEFINED_IN` Records: **754** (Exact 1:1 match).
- **Candidate Repo B (`stretchr/testify`)**:
  - W1 Spike Inventory: 408 functions + 406 methods + 59 types (including 18 interfaces) = **873 symbols**.
  - W2 `DECLARES` Records: **873** (Exact 1:1 match).
  - W2 `DEFINED_IN` Records: **873** (Exact 1:1 match).

### 6.2 Distinct Package Imports Reconciliation
- For all 15 packages in `zap`, the count of distinct `(subject_id, object_id)` `IMPORTS` pairs in `evidence.jsonl v0` matched the W1 summary imports list exactly (15/15 packages matched).
- For all 10 packages in `testify`, the count of distinct `(subject_id, object_id)` `IMPORTS` pairs in `evidence.jsonl v0` matched the W1 summary imports list exactly (10/10 packages matched).

### 6.3 File Count Difference Explanation
- In `zap`, W1 recorded 59 files while W2 produced records referencing 55 files. The 4 non-referenced files are `doc.go` (`doc.go`, `internal/ztest/doc.go`, `zapcore/doc.go`, `zaptest/doc.go`).
- In `testify`, W1 recorded 34 files while W2 produced records referencing 26 files. The 8 non-referenced files are `doc.go` (`doc.go`, `assert/doc.go`, `assert/internal/unsafetests/doc.go`, `http/doc.go`, `internal/spew/doc.go`, `mock/doc.go`, `require/doc.go`, `suite/doc.go`).
- **Root Cause**: `doc.go` files contain only package documentation and package declarations with 0 import specs and 0 top-level type/func declarations. Because `evidence.jsonl v0` represents evidence through relation records (`DECLARES`, `DEFINED_IN`, `IMPORTS`), declaration-less documentation files emit zero relation records.

---

## 7. Spot-Check Renderability Verification

### 7.1 Candidate Repo A (`uber-go/zap`)

- **`DECLARES`**: `ev_0007a712f20cf79b20efdcb6432a96871979d1892d302daca3284fb4fe7bbc13`
  - Location: `array.go:325-330`
  - Subject: `package:uber-go/zap@018b91390e74732e9e40f8d356887b8d06461886:go.uber.org/zap`
  - Object: `symbol:uber-go/zap@018b91390e74732e9e40f8d356887b8d06461886/go.uber.org/zap/method/float32s.MarshalLogArray`
  ```go
  func (nums float32s) MarshalLogArray(arr zapcore.ArrayEncoder) error {
  	for i := range nums {
  		arr.AppendFloat32(nums[i])
  	}
  	return nil
  }
  ```

- **`DEFINED_IN`**: `ev_00468431aabeedc8b887f7c42a66100571ac312dd90e3bd30a1bb9e747d60534`
  - Location: `zapgrpc/zapgrpc.go:127-129`
  - Subject: `symbol:uber-go/zap@018b91390e74732e9e40f8d356887b8d06461886/go.uber.org/zap/zapgrpc/method/printer.Printf`
  - Object: `file:uber-go/zap@018b91390e74732e9e40f8d356887b8d06461886:zapgrpc/zapgrpc.go`
  ```go
  func (v *printer) Printf(format string, args ...interface{}) {
  	v.printf(format, args...)
  }
  ```

- **`IMPORTS`**: `ev_029164dbc64a658114c1424e12cac463fe1f406a03257c592f69f2dad0af5b63`
  - Location: `options.go:24-24`
  - Subject: `package:uber-go/zap@018b91390e74732e9e40f8d356887b8d06461886:go.uber.org/zap`
  - Object: `package:fmt`
  ```go
  	"fmt"
  ```

### 7.2 Candidate Repo B (`stretchr/testify`)

- **`DECLARES`**: `ev_0029a1b9207d7801bcc7fe125898158a2962261be31367671697b1641aef9881`
  - Location: `require/require.go:515-523`
  - Subject: `package:stretchr/testify@959dbdacf1533e155162811ea90c90117a420463:github.com/stretchr/testify/require`
  - Object: `symbol:stretchr/testify@959dbdacf1533e155162811ea90c90117a420463/github.com/stretchr/testify/require/function/Fail`
  ```go
  func Fail(t TestingT, failureMessage string, msgAndArgs ...interface{}) {
  	if h, ok := t.(tHelper); ok {
  		h.Helper()
  	}
  	if assert.Fail(t, failureMessage, msgAndArgs...) {
  		return
  	}
  	t.FailNow()
  }
  ```

- **`DEFINED_IN`**: `ev_00132e745268e62fa139684201b08016688043f6eee07cf311b36e6bea05d65a`
  - Location: `http/test_response_writer.go:8-18`
  - Subject: `symbol:stretchr/testify@959dbdacf1533e155162811ea90c90117a420463/github.com/stretchr/testify/http/type/TestResponseWriter`
  - Object: `file:stretchr/testify@959dbdacf1533e155162811ea90c90117a420463:http/test_response_writer.go`
  ```go
  type TestResponseWriter struct {

  	// StatusCode is the last int written by the call to WriteHeader(int)
  	StatusCode int

  	// Output is a string containing the written bytes using the Write([]byte) func.
  	Output string

  	// header is the internal storage of the http.Header object
  	header http.Header
  }
  ```

- **`IMPORTS`**: `ev_01c3d126a651d0f927fb560307cc978d5a4733c2ab2b9d21f78a3b13e63f64d8`
  - Location: `assert/assertions.go:4-4`
  - Subject: `package:stretchr/testify@959dbdacf1533e155162811ea90c90117a420463:github.com/stretchr/testify/assert`
  - Object: `package:bufio`
  ```go
  	"bufio"
  ```

---

## 8. Explicit Scope & Limitations

1. **Test Files Excluded**: Per Week 2 scope, `Tests: false` was enforced during package loading; `_test.go` files are excluded to prevent duplicate symbol variants.
2. **Relation Coverage**: Only exact static relations (`DECLARES`, `DEFINED_IN`, `IMPORTS`) are extracted in Week 2. Dynamic, conservative call-graph, and historical patch relations are deferred to later phases.
3. **Implicit Entity Representation**: Entities (files, packages, symbols) are expressed solely through relation endpoints; standalone entity node emission is not part of v0.
4. **Unscoped Imported Packages**: External imported packages (`package:<import_path>`) are unscoped in v0.
