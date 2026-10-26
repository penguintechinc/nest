#!/usr/bin/env bash
# Update Helm deps (nest-cloudnativepg, then nest) and fail loudly if the alpha render lacks the
# CNPG operator Deployment despite cloudnativepg.enabled=true (silent-missing-operator gap).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/k8s/helm/nest-cloudnativepg" && helm dependency update
cd "$ROOT/k8s/helm/nest" && helm dependency update

render="$(mktemp)"
trap 'rm -f "$render"' EXIT
helm template nest . -n nest -f values-alpha.yaml --include-crds > "$render"

total=$(awk '/^kind:/{n++} END{print n+0}' "$render")
if [ "$total" -eq 0 ]; then
  echo "ERROR: render produced 0 resources" >&2
  exit 1
fi

if grep -Eq '^  enabled: true' <(awk '/^cloudnativepg:/{f=1;next} /^[^ ]/{f=0} f' values-alpha.yaml); then
  ops=$(awk '/^kind: Deployment$/{d=1;next} d&&/^  name:/{if ($2 ~ /cloudnative-pg/) n++; d=0} /^---/{d=0} END{print n+0}' "$render")
  echo "checked: resources=$total cloudnative-pg Deployments=$ops"
  if [ "$ops" -eq 0 ]; then
    echo "ERROR: cloudnativepg.enabled=true but no *cloudnative-pg* Deployment in render (operator missing)" >&2
    exit 1
  fi
else
  echo "ERROR: could not find cloudnativepg.enabled=true in values-alpha.yaml" >&2
  exit 1
fi
echo "OK"
