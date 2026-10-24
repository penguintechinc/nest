#!/usr/bin/env bash
# Bootstrap out-of-band dal2alpha resources (nest-local-retain StorageClass).
# Requires KUBE_CONTEXT=dal2alpha. Default = server-side dry-run; pass --apply to really apply.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/k8s/dal2alpha/storageclass-nest-local-retain.yaml"

if [ -z "${KUBE_CONTEXT:-}" ]; then
  echo "ERROR: KUBE_CONTEXT is required (must be dal2alpha)" >&2
  exit 1
fi
if [ "$KUBE_CONTEXT" != "dal2alpha" ]; then
  echo "ERROR: refusing to run: KUBE_CONTEXT='$KUBE_CONTEXT', expected 'dal2alpha'" >&2
  exit 1
fi
if [ ! -f "$MANIFEST" ]; then
  echo "ERROR: manifest not found: $MANIFEST" >&2
  exit 1
fi

if [ "${1:-}" = "--apply" ]; then
  kubectl --context "$KUBE_CONTEXT" apply -f "$MANIFEST"
  echo "APPLIED $MANIFEST to context $KUBE_CONTEXT"
else
  kubectl --context "$KUBE_CONTEXT" apply --dry-run=server -f "$MANIFEST"
  echo "DRY-RUN (server) only: $MANIFEST on context $KUBE_CONTEXT; re-run with --apply to apply"
fi
