# Multi-File Historical Change Evidence

This document records the empirical changed-file and Git-history evidence for candidate bug-fix pairs provided by Track C in `benchmarks/manifests/manifest.yaml`.

---

## 1. Methodology & Scope

### Data Sources
- **Manifest**: Merged Track C candidate manifest (`benchmarks/manifests/manifest.yaml`).
- **Git Repositories**: Candidate repository clones (`uber-go/zap` and `stretchr/testify`) maintained outside the RepoPilot monorepo.

### Evaluation Method
- Resolved manifest abbreviated base/gold SHAs to unambiguous 40-character full commit IDs via `git rev-parse --verify <sha>^{commit}`.
- Verified ancestry relationship using `git merge-base --is-ancestor <base> <gold>`.
- Measured commit distance using `git rev-list --count <base>..<gold>`.
- Verified direct parentage via `git show -s --format="%P" <gold>`.
- Analyzed diffs using `git diff --name-status --find-renames <base> <gold>`.
- Counted total changed files, changed `.go` files, changed `*_test.go` files, and unique changed Go directories.

> **Operational Boundary**: No candidate test suites or build scripts were executed by Track A. Test execution, reproduction, and benchmark pass rates are strictly owned by Track B and Track C.

---

## 2. Note on SHA Concepts

The W1 loader snapshot SHA and Track C base/gold SHAs serve different purposes:

- **Loader snapshot SHA**: One pinned repository commit used to evaluate whether the Go semantic loader (`go/packages`) can parse and type-check the full codebase cleanly.
- **Base/Gold candidate SHAs**: Historical bug/fix commit pairs used to evaluate candidate benchmark changes, fix locality, and semantic coverage.

They are not expected to be equal.

---

## 3. Summary Table: All 12 Candidate Pairs

| Instance ID | Repo | Base Full SHA | Gold Full SHA | Ancestor? | Direct Parent? | Distance | Total Files | Go Files | Test Files | Go Dirs | Multi-File? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `zap_1033` | `zap` | `10b1fe4a64fb4d879fb091383db84fb5a4381329` | `9367581ad2e434689582eb20f68ca9b65e73da55` | Yes | Yes | 1 | 2 | 2 | 1 | 1 | Yes |
| `zap_1017` | `zap` | `221696890252bfa141f23b303652c37fe6d7a9ec` | `b62116b3231598b4b3e30bcc462254320e766f85` | Yes | Yes | 1 | 3 | 3 | 2 | 1 | Yes |
| `zap_812` | `zap` | `ec2dc456c680236892af2c645172713e1c4e1acd` | `c25a0c029fa4ead9116f9b16c7a214d1780fb8e1` | Yes | Yes | 1 | 3 | 3 | 2 | 2 | Yes |
| `testify_4c4d011` | `testify` | `c3b0c9b4f50cd8320ccdcdfd3ffd6afc5b109c4a` | `4c4d0118a66fc95ca42fceb569ed155c953eebbb` | Yes | Yes | 1 | 2 | 2 | 1 | 1 | Yes |
| `testify_2a9c44b` | `testify` | `5ac6528bffc1ed7557980c3c563caf8308568446` | `2a9c44b1d87607c362de484a7a2f7a14098530bf` | Yes | Yes | 1 | 2 | 2 | 1 | 1 | Yes |
| `testify_0bf6b94` | `testify` | `5fa984a7595bec3f65a1874f6e5a085545121508` | `0bf6b946d985309f37a4364b0b1f01a92698730e` | Yes | Yes | 1 | 2 | 2 | 1 | 1 | Yes |
| `testify_4f554a8` | `testify` | `e8daaaca9cd5c11e45f7aada79cdea3fc9f2b4eb` | `4f554a8833afff3cffb491138ba9c796ca4106b4` | Yes | Yes | 1 | 2 | 2 | 1 | 1 | Yes |
| `testify_c41592b` | `testify` | `0e75f9941b5987a9ef2bd11ff8b24a4b4489e204` | `c41592ba5fb28876af3ac0ed2cb6fce31767c53b` | Yes | Yes | 1 | 2 | 2 | 1 | 1 | Yes |
| `testify_17b83c5` | `testify` | `be3fbeb9439e3d83cd53a3518c0057b4d1bc0dc0` | `17b83c52e448cda392953b4213d611a1f8a21e0e` | Yes | Yes | 1 | 2 | 2 | 1 | 1 | Yes |
| `testify_6555fd4` | `testify` | `a012e45d185128fe5bf3370e42b0854856e0998e` | `6555fd4da6911f1a3a0e751fbe4fd61c22e809d5` | Yes | Yes | 1 | 2 | 2 | 1 | 1 | Yes |
| `testify_b074924` | `testify` | `84619f5c3cc34b4aec7872962246d19f99abf81c` | `b074924938f86d417f1c9a845c7e8b0784d7f937` | Yes | Yes | 1 | 3 | 3 | 2 | 2 | Yes |
| `testify_f7fedd9` | `testify` | `5911e38e09462765ebbe93bd7e79d761cc73d4fd` | `f7fedd9f85b07f578782e2ca6b937677fd0ad171` | Yes | Yes | 1 | 2 | 2 | 1 | 1 | Yes |

---

## 4. Per-Instance Inspection Details

### `zap_1033` (`uber-go/zap`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `sampler: Support thereafter of zero (#1033)`
- **Changed Paths**:
  - `M zapcore/sampler.go`
  - `M zapcore/sampler_test.go`
- **Observation**: 2 files changed, 2 Go files changed (1 implementation, 1 test), 1 changed Go directory (`zapcore`). Multi-file historical fix observed.

### `zap_1017` (`uber-go/zap`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `jsonEncoder: Close namespaces opened in an object (#1017)`
- **Changed Paths**:
  - `M zapcore/json_encoder.go`
  - `M zapcore/json_encoder_impl_test.go`
  - `M zapcore/memory_encoder_test.go`
- **Observation**: 3 files changed, 3 Go files changed (1 implementation, 2 tests), 1 changed Go directory (`zapcore`). Multi-file historical fix observed.

### `zap_812` (`uber-go/zap`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `Fix IncreaseLevel being reset after With (#812)`
- **Changed Paths**:
  - `M increase_level_test.go`
  - `M zapcore/increase_level.go`
  - `M zapcore/increase_level_test.go`
- **Observation**: 3 files changed, 3 Go files changed (1 implementation, 2 tests), 2 changed Go directories (`.`, `zapcore`). Cross-Go-directory historical fix observed.

### `testify_4c4d011` (`stretchr/testify`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `assert: Fix EqualValues to handle overflow/underflow`
- **Changed Paths**:
  - `M assert/assertions.go`
  - `M assert/assertions_test.go`
- **Observation**: 2 files changed, 2 Go files changed (1 implementation, 1 test), 1 changed Go directory (`assert`). Multi-file historical fix observed.

### `testify_2a9c44b` (`stretchr/testify`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `fix Subset/NotSubset when calling with mixed input types (array/slice list with map subset)`
- **Changed Paths**:
  - `M assert/assertions.go`
  - `M assert/assertions_test.go`
- **Observation**: 2 files changed, 2 Go files changed (1 implementation, 1 test), 1 changed Go directory (`assert`). Multi-file historical fix observed.

### `testify_0bf6b94` (`stretchr/testify`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `mock.AssertExpectationsForObjects fix panic with wrong testObject type.`
- **Changed Paths**:
  - `M mock/mock.go`
  - `M mock/mock_test.go`
- **Observation**: 2 files changed, 2 Go files changed (1 implementation, 1 test), 1 changed Go directory (`mock`). Multi-file historical fix observed.

### `testify_4f554a8` (`stretchr/testify`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `Fix #1399: Always report error message on PanicsWithError mismatch`
- **Changed Paths**:
  - `M assert/assertions.go`
  - `M assert/assertions_test.go`
- **Observation**: 2 files changed, 2 Go files changed (1 implementation, 1 test), 1 changed Go directory (`assert`). Multi-file historical fix observed.

### `testify_c41592b` (`stretchr/testify`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `suite: fix deadlock in suite.Require()/Assert()`
- **Changed Paths**:
  - `M suite/suite.go`
  - `M suite/suite_test.go`
- **Observation**: 2 files changed, 2 Go files changed (1 implementation, 1 test), 1 changed Go directory (`suite`). Multi-file historical fix observed.

### `testify_17b83c5` (`stretchr/testify`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `Fix time.Time compare`
- **Changed Paths**:
  - `M assert/assertion_compare.go`
  - `M assert/assertion_compare_test.go`
- **Observation**: 2 files changed, 2 Go files changed (1 implementation, 1 test), 1 changed Go directory (`assert`). Multi-file historical fix observed.

### `testify_6555fd4` (`stretchr/testify`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `Fix issue #1662 (comparing infs should fail)`
- **Changed Paths**:
  - `M assert/assertions.go`
  - `M assert/assertions_test.go`
- **Observation**: 2 files changed, 2 Go files changed (1 implementation, 1 test), 1 changed Go directory (`assert`). Multi-file historical fix observed.

### `testify_b074924` (`stretchr/testify`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `assert: collect.FailNow() should not panic (#1481)`
- **Changed Paths**:
  - `M assert/assertions.go`
  - `M assert/assertions_test.go`
  - `M require/requirements_test.go`
- **Observation**: 3 files changed, 3 Go files changed (1 implementation, 2 tests), 2 changed Go directories (`assert`, `require`). Cross-Go-directory historical fix observed.

### `testify_f7fedd9` (`stretchr/testify`)
- **Relationship**: Base is ancestor (`true`), Direct parent (`true`), Commit distance: `1`
- **Gold Subject**: `assert: better formatting for Len() error`
- **Changed Paths**:
  - `M assert/assertions.go`
  - `M assert/assertions_test.go`
- **Observation**: 2 files changed, 2 Go files changed (1 implementation, 1 test), 1 changed Go directory (`assert`). Multi-file historical fix observed.

---

## 5. Repository-Level Conclusions

### Repo A (`uber-go/zap`)

- **Candidate pairs inspected**: 3
- **Pairs resolving successfully**: 3 (100%)
- **Direct-parent pairs (`distance == 1`)**: 3 (100%)
- **Multi-file pairs (`files >= 2`)**: 3 (100%)
- **Multi-Go-file pairs (`Go files >= 2`)**: 3 (100%)
- **Cross-Go-directory pairs (`Go dirs >= 2`)**: 1 (`zap_812` touches root `.` and `zapcore`)

**Track A Assessment**:
- `[Dữ kiện]` 3/3 inspected candidate pairs in `uber-go/zap` resolved cleanly, represent direct-parent atomic fix commits (distance 1), and touch at least 2 files (implementation + test). 1 instance (`zap_812`) spans across 2 distinct Go directories (`.` and `zapcore`).
- `[Suy luận]` `uber-go/zap` exhibits genuine multi-file and cross-directory fix locality in historical patches, satisfying Week 1 program-analysis screening requirements for realistic patch grounding.
- `[Không biết]` Test reproducibility, execution isolation, and fail-before/pass-after validation of these 3 pairs remain pending Track B runner execution and Track C benchmark qualification.

### Repo B (`stretchr/testify`)

- **Candidate pairs inspected**: 9
- **Pairs resolving successfully**: 9 (100%)
- **Direct-parent pairs (`distance == 1`)**: 9 (100%)
- **Multi-file pairs (`files >= 2`)**: 9 (100%)
- **Multi-Go-file pairs (`Go files >= 2`)**: 9 (100%)
- **Cross-Go-directory pairs (`Go dirs >= 2`)**: 1 (`testify_b074924` touches `assert` and `require`)

**Track A Assessment**:
- `[Dữ kiện]` 9/9 inspected candidate pairs in `stretchr/testify` resolved cleanly, represent direct-parent atomic fix commits (distance 1), and touch at least 2 files (implementation + test). 1 instance (`testify_b074924`) spans across 2 distinct Go directories (`assert` and `require`).
- `[Suy luận]` `stretchr/testify` provides strong multi-file fix evidence across diverse functional modules (`assert`, `mock`, `suite`), confirming structural patch complexity for Week 1 evaluation.
- `[Không biết]` Test reproducibility, execution isolation, and fail-before/pass-after validation of these 9 pairs remain pending Track B runner execution and Track C benchmark qualification.
