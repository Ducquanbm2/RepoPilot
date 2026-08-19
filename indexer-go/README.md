# Indexer (Go)

This directory contains the Go semantic-analysis and indexing component for RepoPilot.

## Status and Scope

- **Phase 1**: Structure and bootstrap documentation only (no Go module or source files initialized yet).
- **Week 1 Phase 2**: Will introduce a feasibility spike evaluating `golang.org/x/tools/go/packages` for AST/type-check loading and extraction of a minimal semantic inventory (declarations, imports, basic symbol references).
- **Out of Scope for Initial Spike**: SSA generation, call-graph construction, and incremental indexing are explicitly deferred and out of scope for the W1 feasibility spike.
