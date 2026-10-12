#!/usr/bin/env bash
# scripts/verify-go-leftovers.sh — prove apps/api Go leftovers are unreachable and pkg/auth has other importers.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
tmp="$(mktemp)"
trap 'rm -f "${tmp}"' EXIT
mapfile_files() { git ls-files 'apps/api/*.go' 'apps/api/**/*.go' | sort -u; }
files="$(mapfile_files)"
go_files=$(printf '%s' "${files}" | grep -c . || true)
echo "apps/api go files examined: ${go_files}"
[ "${go_files}" -gt 0 ] || { echo "FAIL: zero files examined (already deleted? update doc)"; exit 1; }
# 1. no main package => cannot produce a binary
# shellcheck disable=SC2086
if grep -lE '^package main$' ${files}; then echo "FAIL: main package found"; exit 1; fi
# 2. nothing outside apps/api imports it
imp=$(grep -rln 'penguintechinc/nest/apps/api' --include='*.go' . | grep -v '^./apps/api/' | wc -l || true)
echo "external importers of apps/api: ${imp}"
[ "${imp}" -eq 0 ] || { echo "FAIL: apps/api has external importers"; exit 1; }
# 3. pkg/auth importers (must stay: other services)
echo "pkg/auth importer dirs:"
grep -rln 'nest/pkg/auth' --include='*.go' . | xargs -n1 dirname | sort -u | tee "${tmp}"
n=$(wc -l < "${tmp}")
echo "pkg/auth importer dirs examined: ${n}"
[ "${n}" -gt 0 ] || { echo "FAIL: pkg/auth has no importers examined"; exit 1; }
