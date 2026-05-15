# Clone Command

Clone a repository into the workspace, organise it under a group folder, update the parent
CLAUDE.md, and rebuild the cross-repo graph.

The mechanical work is done by `scripts/clone.sh`. This command file handles the three
interactive bits:
1. Confirming the auto-detected group with the user
2. Generating `Features.md` content (requires reading the repo — semantic LLM work)
3. Offering the per-repo graphify hook

---

## Step 1 — Parse arguments

The router passes everything after `clone` (e.g. `https://gitlab.com/mygroup/repo.git` or
`myorg/repo --group myteam`).

Extract:
- `REPO_ARG` — the URL or `owner/repo` shorthand (everything except the `--group` flag)
- `MANUAL_GROUP` — value after `--group` (empty if not provided)

---

## Step 2 — Preview detected group and confirm

Before running clone.sh in full, derive what the script will do so the user can confirm or
override the group:

```bash
# Quick host/group preview (read-only — no clone yet). Reads from clone.sh's logic by
# calling it with --preview, OR re-implements the auto-detect inline.
```

For simplicity, just run `clone.sh "$REPO_ARG" "$MANUAL_GROUP"` and watch its first
`GROUP=...` output line. If the user wants a different group, ask via `AskUserQuestion`:

> "Detected group: `<GROUP>`. Use this, or type a different group name? (`/`-separated for nested groups)"

If they override, re-run `clone.sh "$REPO_ARG" "<new-group>"`.

> **Implementation note:** the simplest flow is to call `clone.sh` once with the user's
> initial input, parse the `GROUP=` output line, and if they want to change it, re-invoke
> with the override. The clone is idempotent (skips if already cloned) so this is safe.

---

## Step 3 — Run the script

```bash
bash ~/.claude/skills/workdir/scripts/clone.sh "$REPO_ARG" "$MANUAL_GROUP"
```

The script:
- Locates the workspace via the walk-up helper
- Resolves the URL (auto-detects host + SSH port from any existing repo's origin)
- Clones via the provider CLI (falls back to plain `git clone` on failure)
- Scaffolds `test-cases/README.md` from `templates/test-cases-README.md` (static)
- Inserts `@<group>/<repo>/CLAUDE.md` into the workspace `## Projects` section (idempotent)
- Runs `graphify update .` to index the new repo in the cross-repo graph

Parse the script's key/value output:

| Key | Meaning |
|---|---|
| `WORKDIR=...` | Workspace root (walked up from `$(pwd)`) |
| `PROVIDER=...` | Provider read from workspace CLAUDE.md |
| `REPO_URL=...` | Resolved full URL |
| `REPO_NAME=...` | Last path segment (without `.git`) |
| `GROUP=...` | Final group (auto-detected or user-overridden) |
| `REPO_PATH=...` | `<WORKDIR>/<GROUP>/<REPO_NAME>` |
| `CLONE_OK=true\|false` | Whether the clone succeeded |
| `FEATURES_NEW=true\|false` | Whether `Features.md` is missing and needs LLM generation |
| `TESTCASES_NEW=true\|false` | Whether `test-cases/` was created |
| `INCLUDE_STATUS=added\|placeholder\|exists\|no-projects-section` | Result of CLAUDE.md @include insertion |
| `GRAPH_REBUILD=ok\|fail\|noop` | Result of `graphify update .` |

If `CLONE_OK=false`, stop. Surface the error and do not proceed.

---

## Step 4 — Generate Features.md (LLM-driven, only if FEATURES_NEW=true)

If the script reports `FEATURES_NEW=true`, scan the cloned repo (README, directory structure,
key source files) and write `$REPO_PATH/Features.md` with a real initial catalogue — not a stub:

```markdown
# <REPO_NAME> — Features

Legend:
- `✅` User-observable feature
- `⚙️` Internal subsystem
- `?` Inferred / unverified — promote once confirmed

## <Section inferred from the repo>

- ✅ <feature>: <one-line description> (`<path/to/file>`)
- ⚙️ <subsystem>: <one-line description> (`<path/to/file>`)
- ? <inferred-thing>: <description>
```

This step **must** be done by the LLM — it requires reading the repo and producing a
semantic catalogue that scripts can't generate. Use the `Read` and `Glob` tools to scan the
repo first, then `Write` to create `$REPO_PATH/Features.md`.

If `FEATURES_NEW=false`, leave the existing `Features.md` alone.

---

## Step 5 — Offer the per-repo graphify hook

Ask via `AskUserQuestion`:

> "Install the graphify PreToolUse hook for `<REPO_NAME>`? Enables per-repo graph lookups
> when working inside that repo directory."

If yes:

```bash
mkdir -p "$REPO_PATH/.claude"
export PATH="$HOME/.local/bin:$PATH"
(cd "$REPO_PATH" && graphify claude install)
```

If no, note the user can install it later by running `graphify claude install` from
`$REPO_PATH`.

---

## Step 6 — Summary

Show the user a concise final summary combining the script's key/value output with the
results from Steps 4 and 5:

```
Cloned: <GROUP>/<REPO_NAME>
  Location:        <REPO_PATH>
  CLAUDE.md:       <INCLUDE_STATUS>
  Features.md:     <"Created — catalogued N features" | "Already exists — untouched">
  test-cases/:     <"Created from template" | "Already exists — untouched">
  graphify graph:  <GRAPH_REBUILD>
  Per-repo hook:   <"Installed" | "Skipped">
```

---

## Common failure modes

| Symptom | Fix |
|---------|-----|
| `no .workdir/ marker found` | `cd` into a managed workspace, or run `/workdir init <provider>` first |
| `workspace CLAUDE.md is missing 'Provider:' line` | Workspace CLAUDE.md was hand-edited — run `/workdir update` to re-render from template |
| `gh: command not found` | Run `/workdir bootstrap` |
| `Authentication required` | Run `! gh auth login` or `! glab auth login` |
| `Repository not found` | Check spelling; confirm you have access |
| `GRAPH_REBUILD=fail` | Surface; user can re-run `graphify update .` from `$WORKDIR` manually |
