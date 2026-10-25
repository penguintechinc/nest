#!/usr/bin/env bash
# Sourced helper: create and validate a private per-user cache dir for docker hooks.
# Aborts (exit 1) if the dir is a symlink, not owned by us, or group/world-writable —
# a shared/predictable cache path would allow module-cache poisoning.

# secure_cache_dir <dir>: mkdir 0700 and validate; exits 1 on any violation.
secure_cache_dir() {
  local dir="$1" uid owner mode
  uid="$(id -u)"
  if [ -L "$dir" ]; then echo "FAIL: cache dir $dir is a symlink" >&2; exit 1; fi
  mkdir -p "$dir"
  if [ -L "$dir" ]; then echo "FAIL: cache dir $dir is a symlink" >&2; exit 1; fi
  chmod 700 "$dir" 2>/dev/null || true
  owner="$(stat -c %u "$dir" 2>/dev/null || stat -f %u "$dir")"
  mode="$(stat -c %a "$dir" 2>/dev/null || stat -f %Lp "$dir")"
  if [ "$owner" != "$uid" ]; then
    echo "FAIL: cache dir $dir owned by uid $owner, not $uid" >&2; exit 1
  fi
  case "$mode" in
    ?00) ;;
    *) echo "FAIL: cache dir $dir mode $mode is group/world-accessible" >&2; exit 1 ;;
  esac
}
