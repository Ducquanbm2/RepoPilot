# Week 2 integration verification — 2026-11-04

Environment: Windows amd64, Python 3.11 virtual environment, Go 1.26.6,
Docker Desktop Linux engine 28.5.2. Results apply to this environment.

## Revisions and scope

- Refreshed origin with `git fetch origin --prune` from a clean tree.
- main: `1af6c08adf9f0fbc9f7fe5956f701a92f3affce9`
- Original Week2 and integration base: `b90ef18972c375fa580c19165858c9c2871b957c`
- A: `e2aeaba999c8feecf308332518ab9363ab5c7738`
- Runner: `66bce5c09cf57b37b05e312d6a62ad8b182858c9`
- Both `git merge-base --is-ancestor <component-ref> origin/Week2` and
  checks against HEAD returned 0. No redundant merges or history rewrites.
- Inspected exporter, runner/orchestrator, retrieval/evaluation changes against main.
  Removed files in the original integration are old benchmark artifacts/runtime IDs;
  no source components were removed. No Week 3 implementation added.

## Integration fixes

- Removed seven accidentally tracked CPython 3.13 cache files. Existing ignore rules cover them.
- Replaced unavailable `golang:1.26.6-alpine3.22` (build failed twice: manifest not found)
  with verified Go 1.26.6 Alpine 3.24 multi-platform digest; updated image reporting.
- CLI previously returned process exit 0 for a `tests_failed` report (observed with
  missing runner image). It now returns 1. Three regression cases cover retrieval,
  success and failure, including report/manifest writing.

## Verification [RAN]

Commands run from repository root using `.venv/Scripts/python.exe` as Python:

- `python runner/small_test/run_all.py`: 12/12 reported, 0 failures; Docker-online
  run skipped the offline-only function body. Earlier Docker-offline run exercised it.
- `python -m py_compile orchestrator/src/cli.py`: exit 0.
- `python -m py_compile orchestrator/src/workflow.py`: exit 0.
- `python -m orchestrator.src.cli --help`: exit 0.
- `python -m pytest -q`: initially 36 passed; after CLI regression checks 39 passed.
- From indexer-go: `go test ./...`: exporter package passed, spike-loader has no tests.
- `docker build -t repopilot-runner:w1 .`: passed with repaired base reference.
- Retrieval CLI source inspection of `zapcore/sampler.go` lines 195–220: passed.
- Existing orchestrator CLI used with a temporary instance and combined evaluator
  implementation/test patch, preserving LF bytes. Targeted and package regression passed.

Setup: `python -m venv .venv`, `.venv/Scripts/python.exe -m pip install -r requirements.txt`.
Sandbox restrictions initially prevented Git worktrees/network; normal-access reruns passed.
`git submodule update --init --recursive` failed because this repository has gitlinks
without .gitmodules. Used existing dataset builder `ensure_repository` for zap instead;
checked out `10b1fe4a64fb4d879fb091383db84fb5a4381329`.

Runner dependency preparation used a local derived image (no network during tests):
copy zap go.mod/go.sum into a temporary build context, then:

```dockerfile
FROM repopilot-runner:w1
COPY --chown=1000:1000 go.mod go.sum /tmp/repopilot-deps/
RUN cd /tmp/repopilot-deps && go mod download
```

Build command: `docker build -t repopilot-runner:w1 logs/week2-integration/warm`.
The temporary candidate patch concatenates
`artifacts/g0/gold/zap_9367581_gold_solution.patch` and
`benchmarks/patches/f2p/zap_9367581_eval_f2p.patch` as LF bytes.
Temporary instance copies zap_9367581 metadata and replaces test_command with:

```sh
mkdir -p /tmp/zap && cp -a /workspace/. /tmp/zap/ && cd /tmp/zap && go test ./zapcore -run '^TestSamplerWithZeroThereafter$' -v && go test ./...
```

Existing CLI invocation:

```sh
python -m orchestrator.src.cli logs/week2-integration/integration-instance.json benchmarks/repos/zap --patch logs/week2-integration/candidate.patch --log logs/week2-integration/full-workflow.json
```

This is a composed invocation of existing interfaces, not a pre-existing documented
end-to-end smoke script. The evaluator reference patch is used only as a verification
candidate; this is not a claim of solving the issue without reference information.
Raw local reports/setup are under ignored `logs/week2-integration/`.

## Audit and limits

Local/staged `git diff --check` passed. Baseline-to-integration diff has inherited
whitespace warnings, including meaningful unified-patch context; these were preserved.
Conflict-marker scan found none. Common private-key/GitHub-token/AWS-key patterns
found no candidate files; this is not a comprehensive security audit.
Evidence artifacts/exporter tests inspected; full evidence regeneration and all
benchmark instances were not rerun. No deployment or merge authorized/performed.

Full zap suite initially failed at /workspace because upstream caller-path assertions
expect /zap/. The subsequent full run uses /tmp/zap inside the same isolated container,
without changing/excluding upstream tests. See final run result recorded below.

Final full zap run: CLI exit 0, tests_passed; 10 tested packages passed, 2 packages had no tests. Targeted TestSamplerWithZeroThereafter passed. Structured report verified independently of the CLI exit code.
