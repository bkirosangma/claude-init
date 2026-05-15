# workdir Changelog

Each version section lists what changed in that version. The `init` command reads this file
on re-init and prints "what's new since version X.Y.Z" to the user. Sections must be sorted
newest-first.

Format: `## <version> — <YYYY-MM-DD>` followed by a bulleted list of changes.

## 2.1.0 — 2026-05-15
- New `pull` subcommand. `/workdir pull` fetches every repo in the workspace in parallel, then
  categorises each into one of 8 buckets (up-to-date, ff-pull, ahead-only, diverged, dirty,
  in-progress, no-upstream, fetch-failed) and shows a preview table before doing anything
- Default strategy for clean+diverged repos: `git pull --rebase` (with auto-`rebase --abort` on
  conflicts, surfaced for manual resolution). Configurable per-workspace via
  `<WORKDIR>/.workdir/pull.config.json`
- Default strategy for dirty+needs-pull repos: `git stash --include-untracked` → pull → `stash
  pop`. If the pop conflicts, the stash is preserved and surfaced. Configurable
- Two-phase invocation: `pull.sh` plans (fetch + preview, no mutations), `pull.sh --execute`
  reads the plan and acts. Skill's `pull.md` confirms with the user between phases
- Hard-guarded against destructive operations: never auto-runs `reset --hard`, `clean -fd`, or
  any push. Never touches repos with active merge/rebase/cherry-pick. `GIT_TERMINAL_PROMPT=0`
  prevents auth prompts from hanging the run
- New file: `scripts/pull.sh`. New command file: `commands/pull.md`. SKILL.md routing table
  extended with the `pull` token

## 2.0.0 — 2026-05-15
- **Breaking — skill renamed `init-workdir` → `workdir`.** Slash command is now `/workdir`
  (the old `/init-workdir` and `/iwd` aliases no longer route to this skill)
- **Breaking — provider sub-commands moved under `init`.** `/init-workdir github` is now
  `/workdir init github`; `/init-workdir gitlab` is now `/workdir init gitlab`. `bootstrap`,
  `clone`, and `update` remain at the top level
- **Breaking — workspace state dir renamed `.init-workdir/` → `.workdir/`.** Existing
  workspaces are auto-migrated on the next `/workdir init` or `/workdir update` run (the
  directory is `mv`'d in place, preserving `state.json` and history)
- Marketplace reference in `bootstrap` switched from `sportstech` to `claude-init`. The
  bootstrap step reads bundled skills from `~/.claude/plugins/marketplaces/claude-init/`
- `.gitignore` template now emits `.workdir/` (was `.init-workdir/`)

## 1.7.0 — 2026-05-04
- New `bootstrap` subcommand. `/init-workdir bootstrap` does fresh-machine setup: installs
  Homebrew packages (gh, glab, bun, pipx), Node 22 via nvm, graphify via pipx + its skill via
  `graphify install --platform claude`, uipro-cli via npm, third-party plugins (claude-mem,
  superpowers), and writes the global hook entries to `~/.claude/settings.json` (idempotent
  JSON merge — preserves existing hooks)
- `bootstrap` also copies the bundled sportstech marketplace skills (knowledge-base,
  hybrid-search, compound-dispatch) into `~/.claude/skills/<name>/` so existing hook paths
  resolve. Use `--force` to overwrite existing local skill copies
- Sibling plugins added to the sportstech marketplace alongside init-workdir:
  knowledge-base, hybrid-search, compound-dispatch. Each ships its own plugin manifest +
  README. The bootstrap step reads them from the marketplace clone path
- SKILL.md routing table now lists `bootstrap` as the first subcommand; "Typical fresh-machine
  flow" added to Usage section

## 1.6.0 — 2026-05-04
- New `memory-seeds/` directory in the skill — markdown files in this directory are seeded
  into a workspace's per-machine MEMORY.md memory dir on init/update. Solves the portability
  gap where MEMORY.md lives outside the workspace tree (under `~/.claude/projects/`) so
  durable feedback wouldn't travel to a fresh machine
- New init.md Step 13 — Bootstrap MEMORY.md Seeds: encodes the workdir to find the memory dir
  (`/`, `_` → `-`), copies any seed not yet present, appends an index entry to MEMORY.md.
  Existing files are never overwritten
- update.md routing table now also runs the seed-bootstrap step so existing workspaces pick up
  new seeds shipped in skill releases
- First seed shipped: `feedback_ui_ux_pro_max_with_superpowers.md` — instructs subagents to
  pair ui-ux-pro-max with superpowers skills for UI work

## 1.5.0 — 2026-05-04
- CLAUDE.md template now cross-references ui-ux-pro-max from the superpowers section and vice
  versa. Superpowers skills don't auto-pair with ui-ux-pro-max — both must be invoked
  explicitly when a workflow touches UI
- New "Superpowers Integration" subsection inside `## UI/UX Design — Design Intelligence`
  with a per-superpowers-skill mapping of how ui-ux-pro-max plugs in (brainstorming,
  writing-plans, executing-plans, systematic-debugging, code-review)
- New row in the superpowers Development Workflow table pointing at the UI/UX Design section
  for UI work

## 1.4.0 — 2026-05-04
- Clone Step 2 — host detection from existing repos. `owner/repo` shorthand no longer hardcodes
  `gitlab.com`/`github.com`; instead, it reads an existing repo's `origin` to mirror the actual
  host, SSH protocol, and custom SSH port (e.g. self-hosted GitLab on port 29418). Falls back
  to the public host only if the workspace is empty
- New Clone Step 7 — Rebuild Cross-Repo Graphify Graph. The PostToolUse auto-rebuild hook only
  catches Write/Edit, so freshly cloned files were invisible to the cross-repo graph. The
  clone subcommand now runs `graphify update .` after a successful clone and verifies the new
  repo is indexed
- Clone summary now reports graphify graph rebuild status alongside the existing fields

## 1.3.0 — 2026-05-04
- New subcommand `/init-workdir update`: brings an existing workspace up to date with the
  latest skill version. Reads the prior manifest, prints the changelog diff, runs only the
  idempotent steps that matter for upgrades (ignore files, graphify hook, vault, CLAUDE.md,
  claude-mem worker, UI/UX skill), and rewrites the manifest
- Update skips auth, gitconfig prompts, and the heavy initial graph build — those run only
  during full `init`
- New file `commands/update.md` and routing entry in `SKILL.md`

## 1.2.0 — 2026-05-04
- Re-init now reads `<WORKDIR>/.init-workdir/state.json` and prints "what's new since version X.Y.Z"
  by diffing against this CHANGELOG
- New Step 13 — Persist Init Manifest: writes skill version + ISO timestamp + history of prior runs
- Step 3 expanded: detects prior init (manifest, legacy CLAUDE.md, or none) and prints upgrade summary
- Step 4 (gitconfig) now probes existing `<WORKDIR>/.gitconfig` and skips name/email prompts if
  `user.name` and `user.email` are already set
- Per-step idempotency probes are now the source of truth — manifest is informational only

## 1.1.0 — 2026-05-04
- New Step 12 — Install UI/UX Pro Max Skill: auto-installs `uipro-cli` globally if missing,
  then runs `uipro init --ai claude` from the workspace
- New CLAUDE.md template section: "UI/UX Design — Design Intelligence" instructing Claude to
  use the skill for all UI/UX work (designs, audits, edits, palette/font choices, frontend code)

## 1.0.0 — 2026-04-21
- Initial release
- Provider authentication (GitHub via `gh`, GitLab via `glab`)
- Workspace gitconfig wired into `~/.gitconfig` via `includeIf`
- Workspace-level ignore files (`.gitignore`, `.claudeignore`, `.graphifyignore`)
- Graphify PreToolUse hook installed at workspace level
- Knowledge vault initialized via `/knowledge-base init`
- Coding standards copied from skill into workspace
- Parent CLAUDE.md with compound intelligence + workflow rules
- Claude-mem worker started
- Optional initial cross-repo knowledge graph build
