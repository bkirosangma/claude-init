# Pull Command

Pull the latest changes for every repository in the workspace, handling dirty working trees,
diverged branches, and in-progress operations safely.

The heavy lifting is done by `scripts/pull.sh`. This command file orchestrates the two-phase
flow (plan → confirm → execute) and surfaces any per-repo decisions back to the user.

---

## Phase 1 — Plan

Run the script in plan mode. This fetches all remotes in parallel and emits a preview table.
**No working tree, branch, or commit is mutated in this phase** — only remote tracking refs
are updated by `git fetch`.

```bash
bash ~/.claude/skills/workdir/scripts/pull.sh
```

The script prints a table like:

```
Workdir: /path/to/workspace
Repos:   4

Repo                Branch       A/B    Bucket               Planned action
─────────────────────────────────────────────────────────────────────────────
platform/api        main         0/3    AUTO-ff              git pull --ff-only
platform/web        main         2/0    NOOP-ahead           2 unpushed commit(s); nothing to pull
infra/terraform     main         1/4    ASK-diverged         git pull --rebase (1 ahead, 4 behind)
shared/protos       main         0/0    OK-uptodate          already up-to-date

Legend:  A/B = ahead/behind upstream; '*' = dirty working tree
```

Show this table to the user verbatim.

---

## Phase 2 — Confirm

Ask the user via `AskUserQuestion`:

> "Proceed with the planned actions above?"

Options:
- **Proceed** — run `--execute`
- **Cancel** — stop, no changes

If there are `SKIP-*` rows beyond `SKIP-noremote`/`OK-uptodate` (e.g. `SKIP-inprogress`,
`SKIP-fetchfail`, `SKIP-dirty` due to config), call them out in the question so the user knows
those repos will be left untouched.

---

## Phase 3 — Execute

If user confirms, run:

```bash
bash ~/.claude/skills/workdir/scripts/pull.sh --execute
```

The script reads the plan TSV, performs the action for each repo, and emits a final summary
table with one of these outcomes per repo:

| Outcome | Meaning |
|---------|---------|
| `pulled` | `git pull --ff-only` succeeded |
| `rebased` | `git pull --rebase` succeeded |
| `merged` | `git pull --no-rebase` succeeded |
| `pulled+restored` | Stash → pull → pop succeeded cleanly |
| `skipped` | Nothing to do (up-to-date, ahead-only, no upstream, in-progress, etc.) |
| `FAILED` | Script-level git command failed unexpectedly |
| `NEEDS-DECISION` | Config says `ask`; user has to choose |
| `NEEDS-RESOLUTION` | Auto-attempt hit a conflict; manual intervention needed |

Show the summary to the user.

---

## Phase 4 — Handle ambiguous cases

For each row with outcome `NEEDS-DECISION`, `NEEDS-RESOLUTION`, or `FAILED`, ask the user via
`AskUserQuestion` what to do for that specific repo. Options to offer:

| For state | Offer |
|---|---|
| `NEEDS-DECISION` (diverged, config=ask) | Rebase / Merge / Leave alone |
| `NEEDS-DECISION` (dirty, config=ask) | Stash then pull / Discard local / Leave alone |
| `NEEDS-RESOLUTION` (rebase/merge conflict, auto-aborted) | Retry interactively (user fixes manually) / Leave alone |
| `NEEDS-RESOLUTION` (stash pop conflict, stash preserved) | Tell user to resolve manually; show `git stash list` entry |
| `FAILED` | Show the error to the user; offer to retry the pull for that repo only |

Translate the user's choice into a direct git command:

```bash
# Rebase a single repo
git -C "<WORKDIR>/<rel>" pull --rebase

# Merge instead
git -C "<WORKDIR>/<rel>" pull --no-rebase

# Stash + pull + pop (manual, with the user watching the output)
git -C "<WORKDIR>/<rel>" stash push --include-untracked -m "manual-$(date +%s)"
git -C "<WORKDIR>/<rel>" pull --rebase
git -C "<WORKDIR>/<rel>" stash pop

# Discard local uncommitted changes (destructive — confirm with user first)
git -C "<WORKDIR>/<rel>" reset --hard HEAD
git -C "<WORKDIR>/<rel>" pull --ff-only
```

**Never `reset --hard` or `clean -fd` without explicit user confirmation in the same turn.**

---

## Configuration

Optional config at `<WORKDIR>/.workdir/pull.config.json`:

```json
{
  "scanDepth": 2,
  "includeWorkspaceRoot": false,
  "divergedStrategy": "rebase",
  "dirtyOverlapStrategy": "stash",
  "parallelism": 8
}
```

| Key | Default | Effect |
|---|---|---|
| `scanDepth` | `2` | Find `.git` at `<group>/<repo>/.git`. Increase to recurse deeper. |
| `includeWorkspaceRoot` | `false` | If the workspace itself is a git repo, include it in the scan. |
| `divergedStrategy` | `"rebase"` | `rebase` \| `merge` \| `ask` — what to do when local has commits AND remote moved. |
| `dirtyOverlapStrategy` | `"stash"` | `stash` \| `ask` \| `skip` — what to do when working tree is dirty and there's something to pull. |
| `parallelism` | `8` | Number of concurrent `git fetch` operations. |

Per-repo `pull.ff=only` / `pull.rebase=true` in the repo's own git config always wins over
these defaults.

---

## What the script will NEVER do automatically

- `git reset --hard`, `git checkout --`, `git clean -fd` — destructive operations always
  require the user's explicit "yes" in the current turn
- Force-push or any push at all — this command is read-direction only
- Touch a repo with an active merge, rebase, or cherry-pick
- Pull a detached HEAD or a branch with no upstream
- Recurse into submodules (flagged in summary; user runs `git submodule update --remote` if needed)
- Run `git lfs pull` (flagged in summary; user runs it explicitly if needed)
- Hang waiting for HTTPS credentials — `GIT_TERMINAL_PROMPT=0` is set so auth failures fast-fail
  and surface as `SKIP-fetchfail`

---

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `SKIP-fetchfail` rows | Auth expired, network down, remote moved | Run `gh auth status` / `glab auth status`, or `git -C <path> fetch -v` for the failing repo |
| All repos report `SKIP-noremote` | Branches don't track upstreams | `git -C <path> branch --set-upstream-to origin/<branch>` |
| `NEEDS-RESOLUTION` after rebase | Rebase conflicts; auto-aborted | Run the rebase manually: `git -C <path> pull --rebase` and resolve interactively |
| `NEEDS-RESOLUTION` after stash pop | Stash kept, repo clean of changes from pull | Find the stash in `git stash list`, then `git stash pop` and resolve |
| Plan file missing on `--execute` | First-time run requires Phase 1 first | Run `pull.sh` without `--execute` first |
