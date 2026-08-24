# Loader Verification and Repeatability Report

This document records the verification of the Go repository spike loader (`indexer-go/cmd/spike-loader`) across candidate repositories and the controlled negative fixture.

## Environment

- **Go Version**: `go version go1.26.6 windows/amd64`
- **Dependency**: `golang.org/x/tools v0.49.0`
- **Loader Implementation**: `indexer-go/cmd/spike-loader/main.go`

---

## 1. Candidate Repository Repeatability Verification

The loader was executed twice against each candidate repository snapshot from a clean working state. SHA256 checksums of the generated JSON output were computed to verify byte-for-byte determinism.

### Repo A (`uber-go/zap`)

- **Pinned Commit SHA**: `018b91390e74732e9e40f8d356887b8d06461886`
- **Execution Command**:
  ```bash
  .\spike-loader.exe -repo C:\Users\LOQ\repopilot-w1-candidates\zap
  ```
- **Exit Status**: `0`
- **Status Field**: `complete`
- **Run 1 SHA256**: `7511291526A5E88F11E41C02F528AEC57929B606222BFDDFCECDAB4269A9C013`
- **Run 2 SHA256**: `7511291526A5E88F11E41C02F528AEC57929B606222BFDDFCECDAB4269A9C013`
- **Deterministic Match**: **YES** (byte-identical)

### Repo B (`stretchr/testify`)

- **Pinned Commit SHA**: `959dbdacf1533e155162811ea90c90117a420463`
- **Execution Command**:
  ```bash
  .\spike-loader.exe -repo C:\Users\LOQ\repopilot-w1-candidates\testify
  ```
- **Exit Status**: `0`
- **Status Field**: `complete`
- **Run 1 SHA256**: `5F79061CEE3983DDEA34AE0C966F76EB01FBC362477478B5830F0C379C35ACE2`
- **Run 2 SHA256**: `5F79061CEE3983DDEA34AE0C966F76EB01FBC362477478B5830F0C379C35ACE2`
- **Deterministic Match**: **YES** (byte-identical)

---

## 2. Controlled Negative Fixture Verification

The loader was tested against the intentionally broken module at `fixtures/analyzer_fixtures/type_error/`.

### Fixture Details

- **Module**: `example.com/analyzer_fixtures/type_error`
- **Target File**: `broken.go` (contains function `BrokenFunction() int { return "invalid string return" }`)

### Prediction

- The loader must detect the type mismatch.
- Emit structured JSON to stdout.
- Mark report `status = "partial"`.
- Populate `diagnostics` array with type error position `broken.go:5:9`.
- Terminate with non-zero exit status (`1`).

### Observed Result

- **Command**:
  ```bash
  .\spike-loader.exe -repo ..\fixtures\analyzer_fixtures\type_error
  ```
- **Observed Exit Code**: `1`
- **Observed JSON Output**:
  ```json
  {
    "status": "partial",
    "module_path": "example.com/analyzer_fixtures/type_error",
    "packages": [
      {
        "id": "example.com/analyzer_fixtures/type_error",
        "path": "example.com/analyzer_fixtures/type_error",
        "name": "type_error",
        "files": [
          "broken.go"
        ],
        "imports": [],
        "functions": 1,
        "methods": 0,
        "types": 0,
        "interfaces": 0,
        "interface_names": []
      }
    ],
    "source_test_inventory": {
      "test_files": 0,
      "test_like_functions": 0
    },
    "diagnostics": [
      {
        "package": "example.com/analyzer_fixtures/type_error",
        "kind": "list",
        "position": "",
        "message": "# example.com/analyzer_fixtures/type_error\n.\\broken.go:5:9: cannot use \"invalid string return\" (untyped string constant) as int value in return statement"
      },
      {
        "package": "example.com/analyzer_fixtures/type_error",
        "kind": "type",
        "position": "broken.go:5:9",
        "message": "cannot use \"invalid string return\" (untyped string constant) as int value in return statement"
      }
    ]
  }
  ```
- **Verification Status**: **VERIFIED** — The diagnostic path correctly caught the failure and closed with a non-zero exit code while maintaining structured diagnostic output.
