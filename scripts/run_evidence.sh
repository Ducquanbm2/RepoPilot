#!/usr/bin/env bash
# ==============================================================================
# RepoPilot - Week 1 Gate G0 Minimum-Safe Runner
# Track B: Execution & Sandbox Runner Verification
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MANIFEST_FILE="${PROJECT_ROOT}/benchmarks/manifests/manifest.yaml"
REPOS_DIR="${PROJECT_ROOT}/benchmarks/repos"
PATCHES_DIR="${PROJECT_ROOT}/benchmarks/patches"
ARTIFACTS_DIR="${PROJECT_ROOT}/artifacts/g0"
CACHE_DIR="${PROJECT_ROOT}/.cache/repopilot_runner"

IMAGE_NAME="repopilot-runner:w1"
TIMEOUT_SEC=120

# Ensure Git allows operations on mounted directories
git config --global --add safe.directory "*" 2>/dev/null || true

# ------------------------------------------------------------------------------
# 1. Base Image Preparation
# ------------------------------------------------------------------------------
build_base_image() {
    echo "=================================================================="
    echo " [1/4] Building Base Image: ${IMAGE_NAME}"
    echo "=================================================================="
    mkdir -p "${ARTIFACTS_DIR}"
    mkdir -p "${CACHE_DIR}/gocache" "${CACHE_DIR}/gopath_pkg"
    chmod -R 777 "${CACHE_DIR}" 2>/dev/null || true

    local BUILD_CTX="/tmp/repopilot_build_ctx"
    mkdir -p "${BUILD_CTX}"
    cp "${PROJECT_ROOT}/Dockerfile" "${BUILD_CTX}/Dockerfile"

    docker build -t "${IMAGE_NAME}" "${BUILD_CTX}"
    rm -rf "${BUILD_CTX}"


    local IMAGE_ID
    IMAGE_ID=$(docker inspect --format='{{.Id}}' "${IMAGE_NAME}")
    local REPO_DIGEST
    REPO_DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "${IMAGE_NAME}" 2>/dev/null || echo "${IMAGE_ID}")

    local GO_VERSION
    GO_VERSION=$(docker run --rm "${IMAGE_NAME}" go version)

    cat <<EOF > "${ARTIFACTS_DIR}/image.txt"
Image Tag: ${IMAGE_NAME}
Image ID: ${IMAGE_ID}
RepoDigest: ${REPO_DIGEST}
Toolchain: ${GO_VERSION}
Base Image: golang:1.21.3-alpine3.18
OS Packages: git, bash, build-base (gcc, g++, make, musl-dev), coreutils, ca-certificates
Runner User: runneruser (uid=1000, gid=1000)
EOF

    echo "Image metadata written to ${ARTIFACTS_DIR}/image.txt"
    echo "Image ID: ${IMAGE_ID}"
}

# ------------------------------------------------------------------------------
# 2. Dependency Warming
# ------------------------------------------------------------------------------
warm_dependencies() {
    local REPO_PATH="$1"
    echo "Warming Go module cache for ${REPO_PATH}..."
    docker run --rm \
        --network host \
        -v "${REPO_PATH}:/src:ro" \
        -v "${CACHE_DIR}/gopath_pkg:/home/runneruser/go/pkg:rw" \
        -v "${CACHE_DIR}/gocache:/home/runneruser/.cache/go-build:rw" \
        "${IMAGE_NAME}" \
        bash -c "cd /src && go mod download" || true

    chmod -R 777 "${CACHE_DIR}" 2>/dev/null || true
}


# ------------------------------------------------------------------------------
# 3. Minimum Safe Execution Runner
# ------------------------------------------------------------------------------
run_in_sandbox() {
    local WORKTREE_DIR="$1"
    local CMD="$2"
    local LOG_FILE="$3"
    local EXIT_FILE="$4"

    mkdir -p "$(dirname "${LOG_FILE}")"
    mkdir -p "$(dirname "${EXIT_FILE}")"

    echo "Executing in sandbox: ${CMD}"
    
    local START_TIME
    START_TIME=$(date +%s%N)

    set +e
    docker run --rm \
        --network none \
        --user 1000:1000 \
        --cap-drop ALL \
        --security-opt no-new-privileges \
        --pids-limit 256 \
        --memory 2g \
        --cpus 2 \
        --read-only \
        --tmpfs /workspace:rw,exec,nosuid,size=1g,uid=1000,gid=1000,mode=0775 \
        --tmpfs /tmp:rw,exec,nosuid,size=500m,mode=1777 \
        --tmpfs /home/runneruser:rw,exec,nosuid,size=100m,uid=1000,gid=1000,mode=0775 \
        -v "${WORKTREE_DIR}:/src:ro" \
        -v "${CACHE_DIR}/gopath_pkg:/home/runneruser/go/pkg:ro" \
        -v "${CACHE_DIR}/gocache:/home/runneruser/.cache/go-build:rw" \
        "${IMAGE_NAME}" \
        bash -c "cp -a /src/. /workspace/ && cd /workspace && timeout ${TIMEOUT_SEC}s ${CMD}" > "${LOG_FILE}" 2>&1
    
    local EXIT_CODE=$?
    set -e

    local END_TIME
    END_TIME=$(date +%s%N)
    local DURATION_MS=$(( (END_TIME - START_TIME) / 1000000 ))

    echo "${EXIT_CODE}" > "${EXIT_FILE}"
    echo " -> Exit Code: ${EXIT_CODE} (${DURATION_MS} ms)"
    return 0
}

# ------------------------------------------------------------------------------
# 4. 4-Step Verification Workflow Per Instance
# ------------------------------------------------------------------------------
verify_instance() {
    local INSTANCE_ID="$1"
    local REPO_URL="$2"
    local BASE_SHA="$3"
    local GOLD_SHA="$4"
    local TARGETED_TEST_CMD="$5"
    local REGRESSION_TEST_CMD="$6"

    local REPO_NAME
    REPO_NAME=$(basename "${REPO_URL}" .git)
    local REPO_DIR="${REPOS_DIR}/${REPO_NAME}"

    if [ ! -d "${REPO_DIR}/.git" ]; then
        echo "Error: Repository ${REPO_DIR} not found. Running dataset builder..."
        python3 "${PROJECT_ROOT}/scripts/1_build_dataset.py" --instance-id "${INSTANCE_ID}"
    fi

    # Resolve full 40-character SHAs
    local FULL_BASE_SHA
    FULL_BASE_SHA=$(git -C "${REPO_DIR}" rev-parse --verify "${BASE_SHA}^{commit}")
    local FULL_GOLD_SHA
    FULL_GOLD_SHA=$(git -C "${REPO_DIR}" rev-parse --verify "${GOLD_SHA}^{commit}")

    echo "=================================================================="
    echo " Verifying Instance: ${INSTANCE_ID}"
    echo " Repository: ${REPO_NAME} (${REPO_URL})"
    echo " Base SHA: ${FULL_BASE_SHA}"
    echo " Gold SHA: ${FULL_GOLD_SHA}"
    echo " Targeted Command: ${TARGETED_TEST_CMD}"
    echo " Regression Command: ${REGRESSION_TEST_CMD}"
    echo "=================================================================="

    local INSTANCE_ART_DIR="${ARTIFACTS_DIR}/${INSTANCE_ID}"
    mkdir -p "${INSTANCE_ART_DIR}"

    echo "${FULL_BASE_SHA}" > "${ARTIFACTS_DIR}/${INSTANCE_ID}-base-sha.txt"
    echo "${FULL_GOLD_SHA}" > "${ARTIFACTS_DIR}/${INSTANCE_ID}-gold-sha.txt"

    # Pre-warm dependencies
    warm_dependencies "${REPO_DIR}"

    # Extract test patch if not already present
    local PATCH_FILE="${PATCHES_DIR}/${INSTANCE_ID}_test.patch"
    if [ ! -f "${PATCH_FILE}" ]; then
        mkdir -p "${PATCHES_DIR}"
        git -C "${REPO_DIR}" diff --no-ext-diff "${FULL_BASE_SHA}" "${FULL_GOLD_SHA}" -- "*_test.go" > "${PATCH_FILE}"
    fi

    local WORKTREE_BASE="/tmp/repopilot-worktree-${INSTANCE_ID}-base"
    local WORKTREE_GOLD="/tmp/repopilot-worktree-${INSTANCE_ID}-gold"

    # Cleanup any old worktrees
    git -C "${REPO_DIR}" worktree remove --force "${WORKTREE_BASE}" 2>/dev/null || true
    git -C "${REPO_DIR}" worktree remove --force "${WORKTREE_GOLD}" 2>/dev/null || true
    rm -rf "${WORKTREE_BASE}" "${WORKTREE_GOLD}"

    # --------------------------------------------------------------------------
    # Run 1: Base Targeted (Fail-to-Pass)
    # --------------------------------------------------------------------------
    echo "--- [Run 1/4] Base Targeted (F2P, Expect Fail != 0) ---"
    git -C "${REPO_DIR}" worktree add --detach "${WORKTREE_BASE}" "${FULL_BASE_SHA}"
    if [ -s "${PATCH_FILE}" ]; then
        (cd "${WORKTREE_BASE}" && git apply --whitespace=nowarn --ignore-whitespace "${PATCH_FILE}")
    fi
    run_in_sandbox "${WORKTREE_BASE}" "${TARGETED_TEST_CMD}" \
        "${INSTANCE_ART_DIR}/base-targeted.log" \
        "${INSTANCE_ART_DIR}/base-targeted.exit"

    local R1_EXIT
    R1_EXIT=$(cat "${INSTANCE_ART_DIR}/base-targeted.exit")
    if [ "${R1_EXIT}" -eq 0 ]; then
        echo "WARNING: Expected base-targeted to fail, but it exited with 0!"
    else
        echo "SUCCESS: Base targeted failed as expected (exit ${R1_EXIT})."
    fi

    # --------------------------------------------------------------------------
    # Run 2: Base Regression (Pass-to-Pass)
    # --------------------------------------------------------------------------
    echo "--- [Run 2/4] Base Regression (P2P, Expect Pass == 0) ---"
    # Reset worktree to clean base without patch
    (cd "${WORKTREE_BASE}" && git reset --hard && git clean -fdx)
    run_in_sandbox "${WORKTREE_BASE}" "${REGRESSION_TEST_CMD}" \
        "${INSTANCE_ART_DIR}/base-regression.log" \
        "${INSTANCE_ART_DIR}/base-regression.exit"

    local R2_EXIT
    R2_EXIT=$(cat "${INSTANCE_ART_DIR}/base-regression.exit")
    if [ "${R2_EXIT}" -ne 0 ]; then
        echo "WARNING: Expected base-regression to pass, but it exited with ${R2_EXIT}!"
    else
        echo "SUCCESS: Base regression passed as expected (exit 0)."
    fi

    # Clean up base worktree
    git -C "${REPO_DIR}" worktree remove --force "${WORKTREE_BASE}" 2>/dev/null || true
    rm -rf "${WORKTREE_BASE}"

    # --------------------------------------------------------------------------
    # Run 3: Gold Targeted (Pass)
    # --------------------------------------------------------------------------
    echo "--- [Run 3/4] Gold Targeted (Expect Pass == 0) ---"
    git -C "${REPO_DIR}" worktree add --detach "${WORKTREE_GOLD}" "${FULL_GOLD_SHA}"
    run_in_sandbox "${WORKTREE_GOLD}" "${TARGETED_TEST_CMD}" \
        "${INSTANCE_ART_DIR}/gold-targeted.log" \
        "${INSTANCE_ART_DIR}/gold-targeted.exit"

    local R3_EXIT
    R3_EXIT=$(cat "${INSTANCE_ART_DIR}/gold-targeted.exit")
    if [ "${R3_EXIT}" -ne 0 ]; then
        echo "WARNING: Expected gold-targeted to pass, but it exited with ${R3_EXIT}!"
    else
        echo "SUCCESS: Gold targeted passed as expected (exit 0)."
    fi

    # --------------------------------------------------------------------------
    # Run 4: Gold Regression (Pass)
    # --------------------------------------------------------------------------
    echo "--- [Run 4/4] Gold Regression (Expect Pass == 0) ---"
    run_in_sandbox "${WORKTREE_GOLD}" "${REGRESSION_TEST_CMD}" \
        "${INSTANCE_ART_DIR}/gold-regression.log" \
        "${INSTANCE_ART_DIR}/gold-regression.exit"

    local R4_EXIT
    R4_EXIT=$(cat "${INSTANCE_ART_DIR}/gold-regression.exit")
    if [ "${R4_EXIT}" -ne 0 ]; then
        echo "WARNING: Expected gold-regression to pass, but it exited with ${R4_EXIT}!"
    else
        echo "SUCCESS: Gold regression passed as expected (exit 0)."
    fi

    # Clean up gold worktree
    git -C "${REPO_DIR}" worktree remove --force "${WORKTREE_GOLD}" 2>/dev/null || true
    rm -rf "${WORKTREE_GOLD}"

    echo "--- Verification Completed for ${INSTANCE_ID} ---"
}

# ------------------------------------------------------------------------------
# Main Entrypoint
# ------------------------------------------------------------------------------
main() {
    build_base_image

    local TARGET_INSTANCE="${1:-}"

    python3 -c "
import yaml, os, sys, json
with open('${MANIFEST_FILE}') as f:
    manifest = yaml.safe_load(f)
instances = manifest['instances']
target = '${TARGET_INSTANCE}'
if target:
    instances = [i for i in instances if i['instance_id'] == target]
    if not instances:
        print(f'Error: instance {target} not found in manifest', file=sys.stderr)
        sys.exit(1)
else:
    # Run at least 3 instances to establish baseline (e.g. first 3)
    instances = instances[:3]

for inst in instances:
    pkg = inst['test_command'].split()[2] if len(inst['test_command'].split()) > 2 and inst['test_command'].split()[2].startswith('./') else './...'
    reg_cmd = f'go test {pkg} -v'
    print(json.dumps({
        'instance_id': inst['instance_id'],
        'repo_url': inst['repo_url'],
        'base_commit': inst['base_commit'],
        'gold_commit': inst['gold_commit'],
        'test_command': inst['test_command'],
        'regression_command': reg_cmd
    }))
" | while read -r line; do
        i_id=$(python3 -c "import json; d=json.loads('''$line'''); print(d['instance_id'])")
        r_url=$(python3 -c "import json; d=json.loads('''$line'''); print(d['repo_url'])")
        b_sha=$(python3 -c "import json; d=json.loads('''$line'''); print(d['base_commit'])")
        g_sha=$(python3 -c "import json; d=json.loads('''$line'''); print(d['gold_commit'])")
        t_cmd=$(python3 -c "import json; d=json.loads('''$line'''); print(d['test_command'])")
        r_cmd=$(python3 -c "import json; d=json.loads('''$line'''); print(d['regression_command'])")
        verify_instance "${i_id}" "${r_url}" "${b_sha}" "${g_sha}" "${t_cmd}" "${r_cmd}"
    done

    echo "=================================================================="
    echo " All verification runs completed. Summary of generated artifacts:"
    echo "=================================================================="
    find "${ARTIFACTS_DIR}" -type f | sort
}


main "$@"
