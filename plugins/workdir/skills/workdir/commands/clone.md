# Clone Command

Clone a repository into the workspace, organize it under a group folder, update the parent
CLAUDE.md with an @include, and optionally initialize compound intelligence for the new repo.

---

## Step 1 — Parse Arguments

Received from router: everything after `clone` (e.g. `https://gitlab.com/mygroup/repo.git` or
`myorg/repo --group myteam`).

Extract:
- `REPO_ARG` — the URL or `owner/repo` shorthand (everything except the `--group` flag)
- `MANUAL_GROUP` — value after `--group` (empty if not provided)

Detect the workspace root and provider. Walk up from `$(pwd)` to find a `.workdir/` (or
legacy `.init-workdir/`) marker — like git locates `.git/`. Refuses if none found, so a clone
from an unmanaged sub-directory doesn't silently treat the wrong place as the workspace.

```bash
ORIG_PWD=$(pwd)
WORKDIR="$ORIG_PWD"
while [ "$WORKDIR" != "/" ] && [ ! -d "$WORKDIR/.workdir" ] && [ ! -d "$WORKDIR/.init-workdir" ]; do
  WORKDIR=$(dirname "$WORKDIR")
done
if [ "$WORKDIR" = "/" ]; then
  echo "ERROR: no .workdir/ marker found in any parent of $ORIG_PWD"
  echo "Run /workdir init <github|gitlab> first to provision a workspace."
  exit 1
fi
[ "$WORKDIR" != "$ORIG_PWD" ] && echo "Detected workdir: $WORKDIR (invoked from $ORIG_PWD)"

PROVIDER=$(grep "^Provider:" "$WORKDIR/CLAUDE.md" 2>/dev/null | awk '{print $2}')
CLI=$(grep "^CLI:" "$WORKDIR/CLAUDE.md" 2>/dev/null | awk '{print $2}')
```

If PROVIDER is empty, ask the user: "Is this a `github` or `gitlab` workspace?"

---

## Step 2 — Normalize Repo Identifier

**If input is already a full HTTPS or SSH URL** — use as-is. Extract the path part for group
detection.

**If input is a `owner/repo` shorthand** — expand to a full URL. Detect the host from existing
repos in the workspace first; only fall back to the public host if the workspace is empty.

```bash
# Look at any existing repo's origin to discover the actual host (and SSH port for GitLab).
DETECTED_REMOTE=$(find "$WORKDIR" -mindepth 3 -maxdepth 4 -type d -name ".git" -print -quit 2>/dev/null \
  | xargs -I{} dirname {} \
  | xargs -I{} git -C {} remote get-url origin 2>/dev/null \
  | head -1)

if [ -n "$DETECTED_REMOTE" ]; then
  echo "Detected remote pattern from existing repo: $DETECTED_REMOTE"
fi

case "$PROVIDER" in
  github)
    if echo "$DETECTED_REMOTE" | grep -q "@"; then
      # SSH form, e.g. git@github.com:owner/repo.git
      HOST=$(echo "$DETECTED_REMOTE" | sed -E 's|.*@([^:/]+).*|\1|')
      REPO_URL="git@${HOST}:${REPO_ARG}.git"
    else
      HOST=$(echo "$DETECTED_REMOTE" | sed -E 's|https?://([^/]+).*|\1|')
      HOST=${HOST:-github.com}
      REPO_URL="https://${HOST}/${REPO_ARG}.git"
    fi
    ;;
  gitlab)
    # GitLab self-hosted often uses a non-default SSH port, e.g.
    #   ssh://git@gitlab.example.com:29418/group/repo.git
    if echo "$DETECTED_REMOTE" | grep -qE '^ssh://'; then
      HOST_PORT=$(echo "$DETECTED_REMOTE" | sed -E 's|ssh://[^@]+@([^/]+)/.*|\1|')
      REPO_URL="ssh://git@${HOST_PORT}/${REPO_ARG}.git"
    elif echo "$DETECTED_REMOTE" | grep -q "@"; then
      HOST=$(echo "$DETECTED_REMOTE" | sed -E 's|.*@([^:/]+).*|\1|')
      REPO_URL="git@${HOST}:${REPO_ARG}.git"
    else
      HOST=$(echo "$DETECTED_REMOTE" | sed -E 's|https?://([^/]+).*|\1|')
      HOST=${HOST:-gitlab.com}
      REPO_URL="https://${HOST}/${REPO_ARG}.git"
    fi
    ;;
esac

echo "Resolved URL: $REPO_URL"
```

The detection deliberately mirrors whatever an existing repo uses — host, SSH vs HTTPS, custom
SSH port — so the clone path matches the rest of the workspace and your existing auth applies.

Show the resolved URL to the user before cloning. If the workspace is empty (no existing repos
to mirror), fall back to the public host (`github.com` / `gitlab.com`) and warn the user that
no existing repo was found to detect the host from.

Extract `REPO_NAME` (last path segment, stripped of `.git`):
```bash
REPO_NAME=$(basename "$REPO_URL" .git)
```

---

## Step 3 — Determine Group

**If `MANUAL_GROUP` is set:** use it as the group path (supports `/` for nested groups,
e.g. `myorg/backend`).

**If not set, auto-detect from URL path:**

*GitHub:*
```
https://github.com/myorg/myrepo.git  →  GROUP=myorg
```

*GitLab:*
Mirror the full namespace (everything between the host and the repo name):
```
https://gitlab.com/mygroup/myrepo.git           →  GROUP=mygroup
https://gitlab.com/mygroup/subgroup/myrepo.git  →  GROUP=mygroup/subgroup
```

Show the detected group and confirm with the user:
```
Cloning '<REPO_NAME>' into group '<GROUP>'
Full path: <WORKDIR>/<GROUP>/<REPO_NAME>/

Press Enter to confirm, or type a different group name:
```

If the user types an alternative, use that as GROUP. Accept `/`-separated paths for nesting.

---

## Step 4 — Clone

Create the group directory and clone into it:

```bash
mkdir -p "<WORKDIR>/<GROUP>"
```

**Preferred: use the provider CLI (handles auth automatically):**

GitHub:
```bash
gh repo clone "<REPO_NAME_WITH_OWNER>" "<WORKDIR>/<GROUP>/<REPO_NAME>"
# REPO_NAME_WITH_OWNER is the owner/repo portion from the URL
```

GitLab:
```bash
glab repo clone "<NAMESPACE/REPO_NAME>" "<WORKDIR>/<GROUP>/<REPO_NAME>"
# NAMESPACE/REPO_NAME is the full path after the host
```

**Fallback: plain git (works when CLI clone fails or for SSH URLs):**
```bash
git clone "<REPO_URL>" "<WORKDIR>/<GROUP>/<REPO_NAME>"
```

If clone fails, report the error and stop. Do not proceed to CLAUDE.md updates.

---

## Step 5 — Scaffold Features.md and test-cases/

After a successful clone, ensure the repo has both files. These are created fresh if absent; never overwritten if they already exist.

### Features.md

```bash
test -f "<WORKDIR>/<GROUP>/<REPO_NAME>/Features.md" && echo "EXISTS" || echo "NEW"
```

**If NEW:** scan the cloned repo (README, directory structure, key source files) and write `<WORKDIR>/<GROUP>/<REPO_NAME>/Features.md` with a real initial catalogue of the repo's features and sub-systems — not an empty stub. Use this structure:

```markdown
# <REPO_NAME> — Features

Legend:
- `✅` User-observable feature
- `⚙️` Internal subsystem
- `?` Inferred / unverified — promote once confirmed

## <Section inferred from repo>

<!-- bullets describing what you found -->
```

**If EXISTS:** leave untouched.

### test-cases/

```bash
test -d "<WORKDIR>/<GROUP>/<REPO_NAME>/test-cases" && echo "EXISTS" || echo "NEW"
```

**If NEW:** create `<WORKDIR>/<GROUP>/<REPO_NAME>/test-cases/README.md`:

```markdown
# Test Cases

Human-readable catalogue of every scenario worth covering. One file per top-level feature bucket, mirroring `Features.md`'s section numbering. This is the scope contract between product features and tests.

## Format

Each case is one line:

```
<STATUS> <ID>: <GIVEN context,> WHEN <action>, THEN <expected result>
```

## Status Markers

| Marker | Meaning |
|--------|---------|
| ❌ | Not yet covered by a test |
| ✅ | Covered and passing |
| 🟡 | Partially covered |
| 🧪 | Test exists but flaky or not yet merged |
| 🚫 | Consciously out of scope (add a brief reason inline) |

## ID Format

`<BUCKET>-<SECTION>-<NN>` — e.g. `AUTH-1.2-03`

Bucket prefix matches the file name (e.g. `01-auth.md` → `AUTH`).

## Rules

- Never renumber existing IDs. If a case is deleted, leave its number unused — new cases continue past it.
- Flip the status marker in the same commit as the test that covers the case.
- Cross-reference test names with case IDs (`it('AUTH-1.2-03: ...')`) so grep finds both directions.
- Prose only — no test code in this folder.
```

**If EXISTS:** leave untouched.

---

## Step 6 — Update Parent CLAUDE.md

After a successful clone, update `<WORKDIR>/CLAUDE.md` to include the new repo.

**Check if the repo has a CLAUDE.md:**
```bash
test -f "<WORKDIR>/<GROUP>/<REPO_NAME>/CLAUDE.md" && echo "HAS_CLAUDE" || echo "NO_CLAUDE"
```

**Check if this include is already in the workspace CLAUDE.md (idempotency):**
```bash
grep -qF "@<GROUP>/<REPO_NAME>/CLAUDE.md" "<WORKDIR>/CLAUDE.md" && echo "EXISTS" || echo "NEW"
```

**If HAS_CLAUDE and NEW:**
Find the `## Projects` section in `<WORKDIR>/CLAUDE.md`. Insert the @include line after any
existing @include lines in that section (before the closing comment line or the next `##`):

```
@<GROUP>/<REPO_NAME>/CLAUDE.md
```

**If NO_CLAUDE and NEW:**
Insert a comment placeholder so the repo is still tracked:
```
<!-- <GROUP>/<REPO_NAME> — no CLAUDE.md (add one and re-run /workdir clone to activate) -->
```

**If EXISTS:** Skip (already included, no action needed).

---

## Step 7 — Rebuild Cross-Repo Graphify Graph

The PostToolUse auto-rebuild hook only catches Write/Edit events. A fresh `git clone` brings
in tracked files that the hook never saw, so they're invisible to the cross-repo graph until
a manual rebuild. Run an incremental rebuild now to index the new repo:

```bash
export PATH="$HOME/.local/bin:$PATH"
cd "$WORKDIR" && graphify update . 2>&1 | tail -20
```

`graphify update .` is incremental — it only re-parses files that changed since the last
build, so it's fast even on large workspaces. If `graphify` isn't on PATH, surface the error
and continue — the rest of the clone flow is unaffected and the graph can be rebuilt later
with the same command.

Verify the new repo made it into the graph. Note: graphify only indexes code files (java,
cs, py, js, ts, etc.). A repo with only docs/config will (correctly) produce no nodes — so
only flag the repo as "not indexed" if it actually contains code files:

```bash
HAS_CODE=$(find "$WORKDIR/<GROUP>/<REPO_NAME>" -type f \
  \( -name "*.java" -o -name "*.cs" -o -name "*.py" -o -name "*.js" -o -name "*.ts" \
     -o -name "*.tsx" -o -name "*.go" -o -name "*.rs" -o -name "*.kt" -o -name "*.swift" \) \
  -not -path "*/.git/*" -not -path "*/node_modules/*" -print -quit)

if [ -z "$HAS_CODE" ]; then
  echo "✓ Repo has no code files — nothing to index in the structural graph (docs/config only)"
elif grep -q "<GROUP>/<REPO_NAME>" "$WORKDIR/graphify-out/graph.json"; then
  echo "✓ Indexed"
else
  echo "⚠ Code files present but not indexed — run 'graphify update .' from $WORKDIR"
fi
```

---

## Step 8 — Offer Per-Repo Graphify Hook

Ask the user:
```
Would you like to install the graphify PreToolUse hook for '<REPO_NAME>'?
This enables per-repo graph lookups when working inside that repo directory.
```

If yes, write `<WORKDIR>/<GROUP>/<REPO_NAME>/.claude/settings.json` with the graphify
PreToolUse hook entry (same hook installed at the workspace level, but scoped to the repo
directory). The compound intelligence CLAUDE.md sections are already in the parent
`<WORKDIR>/CLAUDE.md` via @include — do not add them to the repo CLAUDE.md.

If no: note they can install it later by adding the graphify PreToolUse hook to
`<REPO>/.claude/settings.json`.

---

## Step 9 — Summary

```
Cloned: <REPO_NAME>
  Provider:    <github|gitlab>
  Location:    <WORKDIR>/<GROUP>/<REPO_NAME>/
  Group:       <GROUP>

  CLAUDE.md:    <"@<GROUP>/<REPO_NAME>/CLAUDE.md added to workspace" |
                 "No CLAUDE.md in this repo — placeholder comment added" |
                 "Already included — no change">
  Features.md:  <"Created — catalogued <N> features/modules" | "Already exists — untouched">
  test-cases/:  <"Created test-cases/README.md" | "Already exists — untouched">
  graphify graph: <"Rebuilt — repo indexed" | "Rebuild failed — run 'graphify update .' from $WORKDIR">
  graphify hook: <"Installed at .claude/settings.json" | "Skipped — add graphify PreToolUse hook to .claude/settings.json when ready">

Workspace now includes these repos:
<list all current @includes from CLAUDE.md ## Projects section>
```

---

## Common Failure Modes

| Symptom | Fix |
|---------|-----|
| `gh: command not found` | Run `/workdir init github` to set up the workspace first |
| `Authentication required` | Run `gh auth login` or `glab auth login` |
| `Repository not found` | Check spelling; confirm you have access to the repo |
| SSH URL fails via CLI | Use plain `git clone` fallback (Step 4) |
| CLAUDE.md Projects section not found | The workspace CLAUDE.md may be from a manual setup — add `## Projects` section manually |
