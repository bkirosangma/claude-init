# Update Command

Bring an existing workspace up to date with the latest init-workdir skill version. Reads the
prior manifest, prints the changelog diff, runs only the idempotent steps from `init.md` that
matter for upgrades, and rewrites the manifest.

**This command requires an existing workspace.** For first-time setup, use `/init-workdir
github` or `/init-workdir gitlab`.

---

## Step 1 — Verify Workspace Exists

```bash
WORKDIR=$(pwd)
WORKDIR_BASENAME=$(basename "$WORKDIR")
CURRENT_VERSION=$(awk '/^version:/{print $2; exit}' ~/.claude/skills/init-workdir/SKILL.md)

MANIFEST="$WORKDIR/.init-workdir/state.json"
if [ -f "$MANIFEST" ]; then
  PRIOR_VERSION=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["skillVersion"])' "$MANIFEST" 2>/dev/null || echo "")
  PRIOR_AT=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("appliedAt",""))' "$MANIFEST" 2>/dev/null || echo "")
  echo "Workspace:        $WORKDIR"
  echo "Last init:        $PRIOR_VERSION at $PRIOR_AT"
  STATE="UPGRADE"
elif grep -q 'Multi-Repo Workspace' "$WORKDIR/CLAUDE.md" 2>/dev/null; then
  PRIOR_VERSION="legacy"
  echo "Workspace:        $WORKDIR"
  echo "Last init:        legacy (no manifest)"
  STATE="LEGACY"
else
  echo "ERROR: No init-workdir workspace found at $WORKDIR"
  echo "Run /init-workdir <github|gitlab> to initialize first."
  exit 1
fi

echo "Current skill:    $CURRENT_VERSION"
```

If neither manifest nor parent `CLAUDE.md` is present, abort with the error message above —
do **not** silently fall through to first-time init (the user invoked `update`, not `init`).

---

## Step 2 — Up-to-Date Check

```bash
if [ "$PRIOR_VERSION" = "$CURRENT_VERSION" ]; then
  echo ""
  echo "✓ Workspace is already at $CURRENT_VERSION (the latest skill version)."
  echo ""
  # Continue to Step 3 to ask whether to re-run probes anyway
fi
```

If versions match, ask:
> "Workspace is already at the latest version. Re-run idempotent probes anyway to verify
> state? (useful if you've manually edited workspace files)"

If the user says no, exit cleanly. If yes, continue.

---

## Step 3 — Print Changelog Diff

For an actual version bump (not a re-verify):

```bash
if [ "$PRIOR_VERSION" != "legacy" ] && [ "$PRIOR_VERSION" != "$CURRENT_VERSION" ]; then
  echo ""
  echo "Changes since $PRIOR_VERSION → $CURRENT_VERSION:"
  echo ""
  awk -v prior="$PRIOR_VERSION" '
    /^## / && $2 == prior { exit }
    /^## / { active=1 }
    active { print }
  ' ~/.claude/skills/init-workdir/CHANGELOG.md
fi
```

For `LEGACY` workspaces (CLAUDE.md present, no manifest):

```
No prior manifest — running all idempotent steps to catch up to $CURRENT_VERSION.
See ~/.claude/skills/init-workdir/CHANGELOG.md for the full version history.
```

---

## Step 4 — Confirm

Ask the user:
> "Apply update? Each step will probe the workspace and skip work that's already in place."

On "no", abort without writing the manifest. On "yes", continue.

---

## Step 5 — Run Idempotent Steps from `init.md`

Read `~/.claude/skills/init-workdir/commands/init.md` and execute the following steps in
order. They share the same `WORKDIR`, `WORKDIR_BASENAME`, `CURRENT_VERSION`, `PRIOR_VERSION`,
and `STATE` variables already set above.

| Step | Action | Why included in `update` |
|------|--------|--------------------------|
| Step 5 — Configure Workspace Ignore Files | Append any missing entries to `.gitignore`, `.claudeignore`, `.graphifyignore` | New ignore rules ship in skill updates |
| Step 6 — Install Graphify Hook | `graphify claude install` (idempotent) | Hook schema may change between versions |
| Step 7 — Initialize Knowledge Vault | Skip if `.archdesigner/config.json` exists | New vault config keys may be added |
| Step 8 — Copy Coding Standards | Skip if `CODING_STANDARDS.md` already exists | Preserves user customisations |
| Step 9 — Write Parent CLAUDE.md | Preserve existing `## Projects` @includes, refresh other sections | New CLAUDE.md template sections (e.g. UI/UX) land here |
| Step 10 — Start Claude-Mem Worker | `status \|\| start` (idempotent) | Worker may need restart after upgrades |
| Step 12 — Install UI/UX Pro Max Skill | `command -v uipro` check, then `uipro init --ai claude` | Skill version refresh |
| Step 13 — Bootstrap MEMORY.md Seeds | Copy any seeds from `~/.claude/skills/init-workdir/memory-seeds/` not yet in the workspace memory dir; preserve existing files | New seed files added in skill releases land here on update |

**Skipped on update:**

| Skipped step | Why |
|--------------|-----|
| Step 1 — Verify Prerequisites | Workspace already exists → prereqs were met previously |
| Step 2 — Authenticate | Auth state preserved by provider CLI |
| Step 3 — Capture Working Directory & Detect Prior Init | Done above as Step 1 of this command |
| Step 4 — Project-Level Gitconfig | Identity rarely changes; user can re-run `/init-workdir <provider>` if it does |
| Step 11 — Build Initial Knowledge Graph | Auto-rebuild hook keeps the graph fresh; skip the heavy initial build |

If you need any of the skipped steps, run the full `/init-workdir <provider>` command — its
own probes will skip already-applied work, just like this one.

---

## Step 6 — Persist Updated Manifest

Same logic as `init.md` Step 13 — append prior run to `history`, write current version and
timestamp:

```bash
mkdir -p "$WORKDIR/.init-workdir"
APPLIED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

python3 - "$WORKDIR/.init-workdir/state.json" "$CURRENT_VERSION" "$APPLIED_AT" <<'PY'
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

echo "Manifest updated: $WORKDIR/.init-workdir/state.json (version $CURRENT_VERSION)"
```

---

## Step 7 — Summary

```
Workspace updated: <WORKDIR>

  Skill version:   $PRIOR_VERSION → $CURRENT_VERSION
  Manifest:        <WORKDIR>/.init-workdir/state.json
  Applied at:      $APPLIED_AT

Next:
  Re-run anytime:  /init-workdir update
  Full re-init:    /init-workdir <github|gitlab>
  Clone a repo:    /init-workdir clone <url>
```
