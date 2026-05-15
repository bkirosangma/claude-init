#!/usr/bin/env bash
# write-manifest.sh — append the prior run to `history` and write the current version + timestamp
# to `<WORKDIR>/.workdir/state.json`.
#
# Usage:
#   write-manifest.sh <workdir> <version>
#
# Schema:
#   { "skillVersion": "<version>", "appliedAt": "<ISO-8601>", "history": [ ... ] }

set -uo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <workdir> <version>" >&2
  exit 2
fi

WORKDIR="$1"
VERSION="$2"
APPLIED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

mkdir -p "$WORKDIR/.workdir"

python3 - "$WORKDIR/.workdir/state.json" "$VERSION" "$APPLIED_AT" <<'PY'
import json, os, sys

path, version, applied_at = sys.argv[1], sys.argv[2], sys.argv[3]
state = {"skillVersion": version, "appliedAt": applied_at, "history": []}
if os.path.exists(path):
    try:
        prev = json.load(open(path))
        state["history"] = prev.get("history", [])
        if prev.get("skillVersion"):
            state["history"].append({
                "version": prev["skillVersion"],
                "appliedAt": prev.get("appliedAt", ""),
            })
    except Exception:
        pass

with open(path, "w") as fh:
    json.dump(state, fh, indent=2)
PY

echo "Manifest updated: $WORKDIR/.workdir/state.json (version $VERSION)"
