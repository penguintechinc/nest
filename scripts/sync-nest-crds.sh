#!/usr/bin/env bash
# Sync Nest CRDs from k8s/kustomize/base/crds/ (source of truth) into the nest umbrella
# chart's crds/ dir. Usage: sync-nest-crds.sh [sync|check]; check exits 1 on drift.
set -euo pipefail
# NOTE: Helm installs crds/ only on FIRST install and never upgrades/deletes them. CRD changes need
# `kubectl apply -f k8s/helm/nest/crds/` BEFORE `helm upgrade` on gamma/prod (alpha is destroy+fresh).

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/k8s/kustomize/base/crds"
DST="$ROOT/k8s/helm/nest/crds"
MODE="${1:-sync}"

count=$(find "$SRC" -maxdepth 1 -name '*.yaml' ! -name kustomization.yaml | wc -l)
if [ "$count" -eq 0 ]; then
  echo "ERROR: no CRD files found in $SRC" >&2
  exit 1
fi

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
find "$SRC" -maxdepth 1 -name '*.yaml' ! -name kustomization.yaml -exec cp {} "$stage"/ \;

case "$MODE" in
  sync)
    mkdir -p "$DST"
    find "$DST" -maxdepth 1 -name '*.yaml' -delete
    cp "$stage"/*.yaml "$DST"/
    echo "synced $count CRDs -> $DST"
    ;;
  check)
    if diff -r "$stage" "$DST" >/dev/null; then
      echo "OK: $count CRDs in sync"
    else
      diff -r "$stage" "$DST" >&2 || true
      echo "DRIFT: run 'make sync-nest-crds'" >&2
      exit 1
    fi
    ;;
  *) echo "usage: $0 [sync|check]" >&2; exit 2 ;;
esac
