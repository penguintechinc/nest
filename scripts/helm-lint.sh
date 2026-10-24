#!/usr/bin/env bash
# Lint every Helm chart under k8s/helm (Go-template files are excluded from check-yaml, so this is
# their gate). Umbrella chart uses alpha values; node-agent needs an image tag. Fails on 0 charts.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/k8s/helm"

# Umbrella deps: build only when charts/ is missing (offline-tolerant; needs network only then).
if [ -f nest/Chart.lock ] && [ ! -d nest/charts ]; then
  (cd nest && helm dependency build >/dev/null)
fi

shopt -s nullglob
count=0
for chart in */Chart.yaml; do
  dir="$(dirname "$chart")"
  args=()
  case "$dir" in
    nest) args=(-f nest/values-alpha.yaml) ;;
    nest-node-agent) args=(--set image.tag=ci) ;;
  esac
  echo "helm lint $dir"
  helm lint "$dir" ${args[@]+"${args[@]}"}
  count=$((count + 1))
done

echo "helm-lint: linted $count charts"
if [ "$count" -eq 0 ]; then
  echo "ERROR: linted 0 charts" >&2
  exit 1
fi
