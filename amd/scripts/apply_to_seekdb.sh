#!/usr/bin/env bash
# Apply the optimized hipVS CAGRA bridge to a seekdb checkout.
#
# Usage:
#   apply_to_seekdb.sh --seekdb /path/to/seekdb [--with-adaptor-patch] [--no-build]
#   apply_to_seekdb.sh --seekdb /path/to/seekdb --restore
#
# The script only touches:
#   tools/hipvs_bridge/seekdb_cuvs_bridge.{c,h}
#   tools/hipvs_bridge/build.sh
#   src/oblib/lib/vector/ob_vsag_adaptor.cpp   (only with --with-adaptor-patch)
# Originals are kept under .amd-solution-backup/ for --restore.

set -Eeuo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
AMD_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
SOLUTION=$AMD_ROOT/solution
PATCH=$AMD_ROOT/patches/0001-ob-vsag-adaptor-direct-search.patch
BASE_COMMIT=634888d9b037153fa143d2c913ba4b25503e1d62

SEEKDB=""
WITH_PATCH=0
NO_BUILD=0
RESTORE=0

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
}

while (($# > 0)); do
  case "$1" in
    --seekdb) SEEKDB=${2:-}; shift 2 ;;
    --with-adaptor-patch) WITH_PATCH=1; shift ;;
    --no-build) NO_BUILD=1; shift ;;
    --restore) RESTORE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$SEEKDB" && -d "$SEEKDB" ]] || { echo "missing or invalid --seekdb" >&2; exit 2; }
SEEKDB=$(cd "$SEEKDB" && pwd)
BRIDGE_DIR=$SEEKDB/tools/hipvs_bridge
BACKUP=$SEEKDB/.amd-solution-backup

[[ -f "$BRIDGE_DIR/seekdb_cuvs_bridge.c" ]] || {
  echo "not a seekdb checkout: $BRIDGE_DIR/seekdb_cuvs_bridge.c is missing" >&2
  exit 2
}

restore() {
  [[ -d "$BACKUP" ]] || { echo "no backup under $BACKUP" >&2; exit 1; }
  for rel in tools/hipvs_bridge/seekdb_cuvs_bridge.c \
             tools/hipvs_bridge/seekdb_cuvs_bridge.h \
             tools/hipvs_bridge/build.sh \
             src/oblib/lib/vector/ob_vsag_adaptor.cpp; do
    if [[ -f "$BACKUP/$rel" ]]; then
      cp -f "$BACKUP/$rel" "$SEEKDB/$rel"
      echo "restored $rel"
    fi
  done
  rm -rf "$BACKUP"
}

if ((RESTORE)); then
  restore
  exit 0
fi

mkdir -p "$BACKUP/tools/hipvs_bridge" "$BACKUP/src/oblib/lib/vector"
for rel in tools/hipvs_bridge/seekdb_cuvs_bridge.c \
           tools/hipvs_bridge/seekdb_cuvs_bridge.h \
           tools/hipvs_bridge/build.sh \
           src/oblib/lib/vector/ob_vsag_adaptor.cpp; do
  [[ -f "$BACKUP/$rel" ]] || cp -f "$SEEKDB/$rel" "$BACKUP/$rel"
done

cp -f "$SOLUTION/seekdb_cuvs_bridge.c" "$BRIDGE_DIR/seekdb_cuvs_bridge.c"
cp -f "$SOLUTION/seekdb_cuvs_bridge.h" "$BRIDGE_DIR/seekdb_cuvs_bridge.h"
cp -f "$SOLUTION/build.sh" "$BRIDGE_DIR/build.sh"
chmod +x "$BRIDGE_DIR/build.sh"
echo "installed optimized bridge sources"

if ((WITH_PATCH)); then
  if git -C "$SEEKDB" apply --reverse --check "$PATCH" >/dev/null 2>&1; then
    echo "adaptor patch already applied; skipping"
  else
    git -C "$SEEKDB" apply --check "$PATCH"
    git -C "$SEEKDB" apply "$PATCH"
    echo "applied $(basename "$PATCH")"
  fi
else
  echo "adaptor patch not applied (pass --with-adaptor-patch for the query fast path)"
fi

if git -C "$SEEKDB" rev-parse --verify -q "$BASE_COMMIT^{commit}" >/dev/null 2>&1; then
  if git -C "$SEEKDB" merge-base --is-ancestor "$BASE_COMMIT" HEAD; then
    echo "baseline ancestry: OK ($BASE_COMMIT)"
  else
    echo "WARNING: HEAD is not a descendant of the frozen baseline $BASE_COMMIT" >&2
  fi
else
  echo "note: baseline commit not present locally (shallow clone?); skipping ancestry check"
fi

if ((NO_BUILD)); then
  echo "skipped bridge build (--no-build)"
  exit 0
fi

[[ -n "${HIPCC:-}" || -x "${ROCM_ROOT:-/opt/rocm}/bin/hipcc" ]] || {
  echo "hipcc not found; set ROCM_ROOT/HIPCC or use --no-build" >&2
  exit 2
}
bash "$BRIDGE_DIR/build.sh"
