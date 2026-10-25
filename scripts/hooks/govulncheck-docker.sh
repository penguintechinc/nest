#!/usr/bin/env bash
# Runs govulncheck over every Go module in a digest-pinned golang container
# (same image as services/k8s-controller/Dockerfile) — host go is too old for go1.26 modules.
# Fails on any govulncheck non-zero exit and when a module examines 0 packages.
set -euo pipefail

IMAGE='golang:1.26.10-bookworm@sha256:632dff7351799a5a9954a48dc06670ade72ee44e8c351cdc0e5a57af2fea21af'
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/hooks/lib-cache.sh
. "$HERE/lib-cache.sh"
CACHE="${GOVULN_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/nest-govulncheck}"
secure_cache_dir "$CACHE"
ROOT="$(git rev-parse --show-toplevel)"

# shellcheck disable=SC2016  # expanded inside the container
INNER='set -euo pipefail
rc=0
for mod in . services/db-proxy services/k8s-controller; do
  cd "$ROOT/$mod"
  n=$(go list ./... | wc -l)
  if [ "$n" -eq 0 ]; then echo "FAIL: $mod examined 0 packages"; rc=1; continue; fi
  echo "== govulncheck $mod ($n packages)"
  go run golang.org/x/vuln/cmd/govulncheck@v1.3.0 ./... || rc=1
done
exit $rc'

docker run --rm --user "$(id -u):$(id -g)" \
  -e HOME=/tmp/home -e GOPATH=/tmp/cache/gopath -e GOCACHE=/tmp/cache/gocache \
  -e GOFLAGS="-buildvcs=false -mod=readonly" -e GOTOOLCHAIN=local -e ROOT="$ROOT" \
  -v "$CACHE:/tmp/cache" -v "$ROOT:$ROOT:ro" -w "$ROOT" \
  "$IMAGE" bash -c "mkdir -p /tmp/home; $INNER"
