# RepoPilot Runner Base Image (Week 1 Feasibility Spike)
# Pinned toolchain: Go 1.21.3 on Alpine 3.18
FROM golang:1.21.3-alpine3.18

# Essential OS packages: git, bash, build-base (CGO/compiler), coreutils, ca-certificates
RUN apk add --no-cache git bash build-base ca-certificates coreutils

# Create non-root runner user with explicit UID:GID 1000:1000
RUN addgroup -g 1000 -S runnergroup && \
    adduser -u 1000 -S runneruser -G runnergroup -h /home/runneruser

# Pinned environment paths
ENV PATH="/usr/local/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    GOPATH="/home/runneruser/go" \
    GOCACHE="/home/runneruser/.cache/go-build" \
    GOMODCACHE="/home/runneruser/go/pkg/mod"

# Switch to non-root user and ephemeral workspace directory
USER runneruser
WORKDIR /workspace
