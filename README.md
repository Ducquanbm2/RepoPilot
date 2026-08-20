# RepoPilot: Go AI Coding Agent Benchmark & Evaluation System

RepoPilot is an automated evaluation and benchmarking system designed for AI Coding Agents working on Go repositories. Inspired by SWE-bench, RepoPilot is tailored specifically for the Go ecosystem by leveraging deep program analysis (typed/SSA analysis) and secure, isolated execution sandboxes.

---

## 📌 Core Features

1. **Dataset Curation & Test-only Patching (Week 1 Feasibility):** Automatically extracts test-related changes (`*_test.go`) between the Base Commit and Gold Commit of candidate issues to produce self-contained `.patch` test suites.
2. **Deterministic Workspace Lifecycle:** Automates workspace cleaning, checking out repositories at specific commits, and applying test patches cleanly without affecting the host environment.
3. **Go Static Analysis Indexer (Go Toolchain):** Employs official Go libraries (`go/packages`, `go/types`, `go/ssa`, `go/callgraph`) to parse source code, build precise call graphs (CHA/RTA/VTA), and assign stable symbol identities (independent of line numbers).
4. **Isolated Runner Sandbox:** Restricts execution using container isolation strategies (rootless Docker, cgroup resource limits, dropped capabilities, no-network) to safely run untrusted test suites.
5. **Hybrid Retrieval & Agent Controller:** Integrates Lexical (BM25), Vector (Qdrant), and Graph Retrieval with Reciprocal Rank Fusion (RRF) to optimize context assembly for the agent.

---

## 📂 Directory Layout

```text
repopilot/
├── contracts/             # Versioned schema contracts (evidence_ref, manifest, etc.)
├── indexer-go/            # Go parser + diagnostics & callgraph generator
├── evidence_store/        # DB-independent evidence store (in-memory/SQLite/Neo4j)
├── orchestrator/          # Agent workflow controller and tool gateway
├── runner/                # Isolated patch runner and Docker sandbox setup
├── retrieval/             # Retrieval modules: Lexical, Vector, Graph & Fusion
├── eval/                  # Evaluation engine & metrics (Recall@k, MRR, Resolve Rate)
├── benchmarks/            # Benchmark suite assets
│   ├── manifests/         # Full manifests (evaluator-only, contains Gold metadata)
│   ├── patches/           # Directory for extracted test patches
│   ├── repos/             # Repository caches of candidate projects
│   └── runtime_views/     # Sanitized runtime views (leakage-free agent inputs)
├── scripts/               # Developer automation scripts
└── docs/                  # Design docs, architecture details, and ADRs
```

---

## 🛠️ Getting Started (Week 1 Feasibility Spike)

### 1. Prerequisites
*   **OS:** Linux (recommended for Docker sandbox features)
*   **Python:** >= 3.10
*   **Go Toolchain:** Installed locally (required for static analysis spikes)

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Generate Test Patches (Phase 1)
Run `scripts/1_build_dataset.py` to parse the manifest, clone the candidate repositories to `benchmarks/repos/`, extract test diffs, and write patch files:

```bash
python3 scripts/1_build_dataset.py
```
*You can target a specific instance by adding the `--instance-id zap_1033` argument.*

### 4. Prepare Workspace & Apply Patch (Phase 2)
Run `scripts/2_evaluator.py` to simulate the workspace preparation phase before running tests:

```bash
python3 scripts/2_evaluator.py --instance-id zap_1033
```
This script resets the respective repository workspace (`git reset --hard` & `git clean -fdx`) and applies the test patch generated during Phase 1.

---
