# Track B Runner Execution Handoff

This document defines the handoff specification from Track A (Program Analysis & Loader Spike) to Track B (Execution & Sandbox Runner) for verifying build and test reproducibility on the candidate repositories.

---

## 1. Candidate Snapshots

### Candidate Repo A: `uber-go/zap`
- **Repository URL**: `https://github.com/uber-go/zap.git`
- **Pinned Commit SHA**: `018b91390e74732e9e40f8d356887b8d06461886`
- **Module Path**: `go.uber.org/zap`
- **Observed Go Directive**: `go 1.19`

### Candidate Repo B: `stretchr/testify`
- **Repository URL**: `https://github.com/stretchr/testify.git`
- **Pinned Commit SHA**: `959dbdacf1533e155162811ea90c90117a420463`
- **Module Path**: `github.com/stretchr/testify`
- **Observed Go Directive**: `go 1.17`

---

## 2. Verification Protocol for Track B

Track B should verify build/test reproducibility independently using the following controls:

1. **Exact Pinned Snapshots**: Check out the exact recorded commit SHAs listed above.
2. **Canonical Command Discovery**: Inspect candidate-provided documentation (`Makefile`, `CONTRIBUTING.md`, `.github/workflows/`) to determine the intended build and test commands rather than inventing ad-hoc invocations.
3. **Controlled Environment**: Prepare and cache dependencies within the isolated runner environment.
4. **Safety & Sandbox Controls**:
   - Execute as non-root user.
   - Do NOT mount or expose the host home directory, SSH agent, Docker daemon socket, or environment secrets.
   - Disable evaluation-time network access once pre-execution dependencies are downloaded.
   - Enforce execution timeouts and resource/output buffer limits.
5. **Runtime & Repeatability**:
   - Record cold and warm execution runtimes.
   - Execute across repeated clean runs in isolated containers.
   - Record exact invocation commands, stdout/stderr streams, and process exit codes.

---

## 3. Test Pass Status

- **Status**: **PENDING B EXECUTION**
- No pass/fail claims are asserted by Track A. Verification of candidate test pass rates requires Track B sandbox execution evidence.

---

## 4. Track C Candidate Manifest Integration

Track C candidate manifest has now been merged into `benchmarks/manifests/manifest.yaml`. It contains 12 candidate base/gold historical fix SHAs and targeted candidate test commands for `uber-go/zap` (3 instances) and `stretchr/testify` (9 instances).

- Track A has **not** executed those candidate test commands.
- Structural changed-file and Git-history evidence is documented in [`multi-file-change-evidence.md`](file:///c:/Users/LOQ/RepoPilot/docs/gate_evidence/w1/a/multi-file-change-evidence.md).
- Track B can use the base/gold commit pairs and targeted test commands in `benchmarks/manifests/manifest.yaml` for isolated sandbox reproduction and fail-before/pass-after validation.
