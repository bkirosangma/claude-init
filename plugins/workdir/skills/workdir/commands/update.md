# Update Command

Bring an existing workspace up to the current `workdir` skill version. Reads the prior
manifest, prints the changelog diff, runs the idempotent steps that matter for upgrades, and
rewrites the manifest.

**Requires an existing workspace.** For first-time setup use `/workdir init <github|gitlab>`.

The mechanical work is done by `scripts/update.sh`. This command file handles confirmation
and surfaces output.

---

## Step 1 — Detect and preview

Run the update script in detect mode (it reads the manifest, prints the changelog diff, but
does NOT mutate anything until confirmed):

```bash
bash ~/.claude/skills/workdir/scripts/update.sh --plan
```

This prints:
- Detected workdir (walks up from `$(pwd)` to find `.workdir/`)
- Last init version + timestamp from the manifest
- Current skill version
- The CHANGELOG diff between the two

Show this output verbatim to the user.

> **Note:** If `--plan` mode isn't yet implemented in `update.sh`, fall back to reading the
> manifest manually and invoking `scripts/lib/changelog-diff.sh "$PRIOR_VERSION"`.

---

## Step 2 — Confirm

Ask via `AskUserQuestion`:

> "Apply update? Each step probes the workspace and skips work already in place."

If the user declines, exit cleanly. If they confirm, proceed.

---

## Step 3 — Execute

```bash
bash ~/.claude/skills/workdir/scripts/update.sh
```

Show the script's stdout to the user. It will:

- Run `step_ignores`, `step_graphify_hook`, `step_coding_standards`, `step_render_claude_md`,
  `step_claude_mem_worker`, `step_uipro`, `step_memory_seeds` from `lib/init-steps.sh`
- Re-render `<WORKDIR>/CLAUDE.md` from the template (preserves any `## Projects` @includes)
- Rewrite the manifest with the new version + timestamp, appending the prior run to `history`

**Skipped on update** (intentionally — run `/workdir init <provider>` for these):
- Prerequisite checks (workspace exists → prereqs were already met)
- Provider auth (preserved by `gh`/`glab`)
- Gitconfig identity (rarely changes)
- Optional initial graph build (auto-rebuild hook keeps the graph fresh)

---

## Step 4 — Handle failures

If `update.sh` exits non-zero, the cause is one of:

| Symptom | Fix |
|---|---|
| `no .workdir/ marker found` | `cd` into a managed workspace, or run `/workdir init <provider>` |
| `Re-rendering CLAUDE.md ... provider/name/email missing` | Workspace's `.gitconfig` is missing user.name or user.email — run `/workdir init <provider>` to refresh |
| Any per-step `⚠ ... failed` line | Investigate the specific failure; the script continues past them |

Surface the relevant fix. Do not auto-retry.
