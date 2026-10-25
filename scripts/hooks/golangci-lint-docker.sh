#!/usr/bin/env bash
# Runs golangci-lint in a digest-pinned container (v2.15.0, built go1.27.0) — host go is too old
# for go1.26 modules. Repo and git common dir are mounted read-only; only the private cache is writable.
set -euo pipefail

IMAGE='golangci/golangci-lint@sha256:fbfcfd12a6f8d7f1b97b3362ca80fc2a244d46863148c73cb88e7793af96c481'
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/hooks/lib-cache.sh
. "$HERE/lib-cache.sh"
CACHE="${GOLANGCI_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/nest-golangci-lint}"
secure_cache_dir "$CACHE"
COMMON="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)"

docker run --rm --user "$(id -u):$(id -g)" \
  -e HOME=/cache/home -e GOCACHE=/cache/gocache -e GOMODCACHE=/cache/gomod \
  -e GOLANGCI_LINT_CACHE=/cache/glcache -e GOFLAGS=-mod=readonly \
  -v "$CACHE:/cache" -v "$COMMON:$COMMON:ro" -v "$PWD:$PWD:ro" -w "$PWD" \
  "$IMAGE" golangci-lint run --new-from-rev HEAD
