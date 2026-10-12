#!/usr/bin/env bash
# Probe the package index for penguin-libs packages; print FOUND/MISSING + denominator.
set -euo pipefail

PKGS=(penguin-aaa penguin-limiter penguin-http penguin-validation penguin-utils penguin-pydantic)
INDEX_ARGS=()
if [[ -n "${PIP_INDEX_URL:-}" ]]; then
  INDEX_ARGS=(--index-url "${PIP_INDEX_URL}")
fi

found=0
missing=0
for pkg in "${PKGS[@]}"; do
  rc=0
  out="$(python3 -m pip index versions "${pkg}" "${INDEX_ARGS[@]}" 2>/dev/null)" || rc=$?
  if [[ ${rc} -eq 0 && -n "${out}" ]]; then
    ver="$(printf '%s\n' "${out}" | sed -n '1s/^[^(]*(\([^)]*\)).*/\1/p')"
    echo "FOUND ${pkg} ${ver}"
    found=$((found + 1))
  else
    echo "MISSING ${pkg}"
    missing=$((missing + 1))
  fi
done

total=${#PKGS[@]}
echo "examined=${total} found=${found} missing=${missing}"
if [[ $((found + missing)) -ne ${total} || ${total} -eq 0 ]]; then
  echo "FAIL: denominator mismatch" >&2
  exit 1
fi
