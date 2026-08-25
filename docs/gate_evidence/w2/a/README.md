# Week 2 Track A Gate Evidence

This directory stores gate evidence artifacts produced during Week 2 Track A `evidence.jsonl v0` implementation, export execution, and independent verification.

## Status Summary

- **Evidence Exporter Implementation**: Produced and tested (`indexer-go/cmd/evidence-export`).
- **Evidence Datasets**: Produced (`evidence-zap.jsonl`, `evidence-testify.jsonl`).
- **Diagnostics Envelopes**: Produced (`diagnostics-zap.json`, `diagnostics-testify.json`).
- **Fail-Closed Fixture Verification**: Completed (exit code 1, `status: "partial"`, type error detected in `broken.go`).
- **Determinism Verification**: Completed (byte-identical SHA-256 digests across repeat runs).
- **Structural Validation**: Completed via `scripts/validate_evidence_v0.ps1` (100% pass across 1,674 zap and 1,854 testify records).
- **W1 Reconciliation**: Completed (exact 1:1 symbol and import match against W1 summaries).
- **Track B / Track C Feedback**: Cataloged in `contract-feedback-w2.md`.

---

## Artifact Index

- [`candidate-snapshots-w2.md`](file:///c:/Users/LOQ/RepoPilot/docs/gate_evidence/w2/a/candidate-snapshots-w2.md): Pinned commit SHAs, git clean-state verification, and host environment metadata (`go1.26.6 windows/amd64`).
- [`evidence-zap.jsonl`](file:///c:/Users/LOQ/RepoPilot/docs/gate_evidence/w2/a/evidence-zap.jsonl): Stream of 1,674 `DECLARES`, `DEFINED_IN`, and `IMPORTS` evidence records for `uber-go/zap` at commit `018b91390e74732e9e40f8d356887b8d06461886`.
- [`evidence-testify.jsonl`](file:///c:/Users/LOQ/RepoPilot/docs/gate_evidence/w2/a/evidence-testify.jsonl): Stream of 1,854 `DECLARES`, `DEFINED_IN`, and `IMPORTS` evidence records for `stretchr/testify` at commit `959dbdacf1533e155162811ea90c90117a420463`.
- [`diagnostics-zap.json`](file:///c:/Users/LOQ/RepoPilot/docs/gate_evidence/w2/a/diagnostics-zap.json): Diagnostics envelope for `uber-go/zap` (`status: "complete"`, 0 errors).
- [`diagnostics-testify.json`](file:///c:/Users/LOQ/RepoPilot/docs/gate_evidence/w2/a/diagnostics-testify.json): Diagnostics envelope for `stretchr/testify` (`status: "complete"`, 0 errors).
- [`evidence-generation-report.md`](file:///c:/Users/LOQ/RepoPilot/docs/gate_evidence/w2/a/evidence-generation-report.md): Detailed generation metrics, determinism proofs, reconciliation calculations, and spot-check citations.
- [`contract-feedback-w2.md`](file:///c:/Users/LOQ/RepoPilot/docs/gate_evidence/w2/a/contract-feedback-w2.md): Catalog of Week 2 implementation decisions (`[W2-DRAFT-DECISION]`) and open questions for Track B/C review.
