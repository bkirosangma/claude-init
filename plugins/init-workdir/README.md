# init-workdir

A Claude Code skill that initializes and maintains a **multi-repo workspace** with the full
compound-intelligence stack — graphify (structural), claude-mem (temporal), MEMORY.md
(curated) — plus workspace-scoped gitconfig, ignore files, a knowledge vault, coding
standards, the ui-ux-pro-max design skill, and group-organized repo cloning.

It treats your `Work/<workspace>/` directory as a managed environment with versioned
configuration, idempotent re-runs, and portable memory seeds.

---

## Features

| | |
|---|---|
| **Provider auth** | Authenticates with GitHub (`gh`) or GitLab (`glab`); for self-hosted GitLab it detects the actual host and SSH port from existing repo remotes — no hardcoded `gitlab.com` |
| **Workspace gitconfig** | Writes `<WORKDIR>/.gitconfig` and wires it via `~/.gitconfig` `includeIf` so every repo under the workspace inherits the right identity |
| **Ignore files** | Maintains workspace-level `.gitignore`, `.claudeignore`, `.graphifyignore` with sane defaults; idempotent appends |
| **Compound intelligence** | Installs the graphify PreToolUse hook, starts the claude-mem worker, sets up MEMORY.md routing |
| **Knowledge vault** | Initializes a `knowledgebase/` vault via the `knowledge-base` skill so all architecture docs and diagrams have a registered home |
| **Coding standards** | Copies a curated `CODING_STANDARDS.md` into the workspace; user-customisable, never overwritten on re-init |
| **Parent CLAUDE.md** | Generates a comprehensive `CLAUDE.md` with rules for graphify, claude-mem, MEMORY.md, knowledge-base, coding standards, feature/test tracking, superpowers, ui-ux-pro-max, and compound intelligence |
| **UI/UX Pro Max** | Auto-installs `uipro-cli` globally and runs `uipro init --ai claude` to register the design skill |
| **Repo cloning** | `clone <owner/repo>` auto-detects the GitLab host + SSH port from existing repos, mirrors the workspace's auth pattern, scaffolds `Features.md` and `test-cases/`, registers the repo in the parent `CLAUDE.md`, runs `graphify update .` so the new repo lands in the cross-repo graph |
| **Idempotent re-init** | Every step probes the workspace before acting — re-running is safe and surfaces only what's missing |
| **Version manifest** | Writes `.init-workdir/state.json` so future runs know what skill version provisioned the workspace |
| **Changelog diff on update** | `update` reads the prior manifest and prints "what's new since version X.Y.Z" by diffing the skill's CHANGELOG |
| **Portable memory seeds** | Ships `memory-seeds/*.md` files that get copied into the workspace's per-machine MEMORY.md memory dir on every init/update — durable feedback travels to fresh machines |

---

## Installation

This plugin is part of the **`claude-init`** marketplace. After registering the marketplace in
`~/.claude/settings.json` (see the repo root README), install with:

```
/plugin install init-workdir@claude-init
```

Restart Claude Code. The slash command `/init-workdir` appears in your command list.

### Fresh-machine setup (one-time)

```
/plugin install init-workdir@claude-init   # register the skill in your CC instance
/init-workdir bootstrap                    # installs all dependencies
/init-workdir github                       # provisions a workspace (or `gitlab`)
```

The `bootstrap` subcommand handles **everything** init-workdir depends on:

| Layer | Installed by bootstrap |
|---|---|
| External CLIs | `gh`, `glab`, `bun`, Node 22+ via nvm, `pipx` (via `brew`) |
| graphify | `pipx install graphifyy` + `graphify install --platform claude` |
| uipro-cli | `npm install -g uipro-cli` |
| Third-party Claude Code plugins | `claude-mem@thedotmack`, `superpowers@claude-plugins-official` |
| Global hooks | hybrid-search PreToolUse Read injector, PostToolUse Write/Edit/Bash auto-rebuild-graph, contradiction-check, bump-relevance, SessionEnd crystallize + proceduralize — written to `~/.claude/settings.json` (idempotent JSON merge, preserves existing entries) |

`bootstrap` runs Homebrew as a prerequisite — install Homebrew first if it's missing
([brew.sh](https://brew.sh)).

---

## Usage

```
/init-workdir bootstrap                   Fresh-machine setup: install all CLIs, plugins, hooks
/init-workdir github                      Initialize workspace with GitHub (gh CLI)
/init-workdir gitlab                      Initialize workspace with GitLab (glab CLI)
/init-workdir clone <url>                 Clone repo, auto-detect group from namespace
/init-workdir clone <url> --group <name>  Clone repo into a specific group folder
/init-workdir update                      Update existing workspace to latest skill version
```

### First-time init

```
cd ~/Work/my-workspace
/init-workdir github
```

Walks you through prerequisites, auth, gitconfig identity, ignore files, hook installation,
vault init, coding standards copy, parent CLAUDE.md, claude-mem worker, ui-ux-pro-max skill,
optional initial knowledge graph build, MEMORY.md seed bootstrap, and writes a manifest.

### Cloning a repo

```
/init-workdir clone bkirosangma/myrepo
/init-workdir clone https://github.com/myorg/myrepo.git --group platform
```

Auto-detects the group from the URL namespace (or use `--group`). For GitLab self-hosted, it
reads an existing repo's `origin` to discover the actual host (and custom SSH port like
`29418`) — so `owner/repo` shorthand works on internal GitLab instances, not just gitlab.com.

After clone:
- Scaffolds `Features.md` (a real catalogue inferred from the repo, not a stub) and
  `test-cases/README.md`
- Inserts an `@<group>/<repo>/CLAUDE.md` line in the workspace `CLAUDE.md` `## Projects`
  section (or a placeholder comment if the repo has no CLAUDE.md)
- Runs `graphify update .` so the new repo's code is indexed in the cross-repo graph
- Optionally installs the per-repo graphify PreToolUse hook

### Updating an existing workspace

```
/init-workdir update
```

Reads `<WORKDIR>/.init-workdir/state.json`, prints the changelog diff between the prior
version and the current skill version, and runs only the idempotent steps that matter for
upgrades — ignore files, graphify hook, vault, CLAUDE.md, claude-mem worker, ui-ux-pro-max
re-sync, memory seeds. Skips auth, gitconfig prompts, and the heavy initial graph build.

For a "legacy" workspace (CLAUDE.md present but no manifest), `update` runs all idempotent
steps and writes the first manifest.

---

## Concepts

### Idempotency via per-step probes

Every step inspects the workspace before acting:

- Coding standards step skips if `CODING_STANDARDS.md` already exists
- Gitconfig step probes existing `<WORKDIR>/.gitconfig` and skips name/email prompts if both
  are set
- Ignore files step appends only entries that aren't already present
- Vault step skips if `.archdesigner/config.json` exists
- Memory seeds step preserves any seed file already in the memory dir

Source of truth is **the workspace itself**, not the manifest. The manifest is informational.

### Version manifest at `<WORKDIR>/.init-workdir/state.json`

```json
{
  "skillVersion": "1.7.0",
  "appliedAt": "2026-05-04T08:28:55Z",
  "history": [
    { "version": "1.5.0", "appliedAt": "2026-05-04T08:08:53Z" },
    { "version": "1.6.0", "appliedAt": "2026-05-04T08:15:58Z" }
  ]
}
```

The manifest answers "which version of the skill provisioned this workspace, and when?" The
re-init/update flow reads it to compute "what's new since X.Y.Z" by diffing the skill's
[CHANGELOG.md](skills/init-workdir/CHANGELOG.md).

### CHANGELOG-driven upgrade summaries

Every change to the skill is recorded in `CHANGELOG.md` newest-first. On `update`, the skill
runs an `awk` diff of the changelog from the prior version to the current and prints the
combined sections to the user. Adding a new feature requires:

1. Implement it in `commands/init.md` and (where applicable) `commands/update.md`
2. Bump `version:` in `SKILL.md`
3. Add a `## X.Y.Z — YYYY-MM-DD` section at the **top** of `CHANGELOG.md`

Existing workspaces pick up the change on the next `/init-workdir update`.

### MEMORY.md seeds (portability)

MEMORY.md lives at `~/.claude/projects/<encoded-workdir>/memory/MEMORY.md` — under the user's
home directory, **not** in the workspace tree. So MEMORY.md doesn't travel between machines.

To make durable feedback portable, the skill ships markdown files in `memory-seeds/`. The
init/update flow:

1. Encodes the workdir path (`/`, `_` → `-`) to find the per-machine memory dir
2. Copies any seed file not yet present in the memory dir
3. Appends an index entry to `MEMORY.md`

Existing seed files are never overwritten — the user can edit them locally without losing
their changes on the next update.

**Currently shipped seeds:**

- `feedback_ui_ux_pro_max_with_superpowers.md` — instructs subagents to pair `ui-ux-pro-max`
  with `superpowers` skills for any UI/UX work, since they don't auto-pair

### Compound intelligence routing

The skill writes a CLAUDE.md template that establishes the canonical routing for what goes
where:

| What to save | Where | Why |
|---|---|---|
| User preferences, corrections, feedback | MEMORY.md | Curated, durable, user-controlled |
| Project context, deadlines, stakeholder info | MEMORY.md | Outlives sessions, needs human curation |
| External resource pointers | MEMORY.md | Stable pointers to external systems |
| Bug fixes, decisions, discoveries | claude-mem (auto-captured) | High-volume temporal stream, auto-indexed |
| Code structure, relationships | graphify (auto-discovered) | Derived from source, always fresh via rebuild hooks |

---

## Plugin Layout

```
plugins/init-workdir/
├── .claude-plugin/
│   └── plugin.json                       # plugin manifest
├── hooks/
│   ├── hooks.json                        # SessionStart update-check
│   └── check-update.sh                   # marketplace drift detector
└── skills/
    └── init-workdir/
        ├── SKILL.md                      # router and metadata (frontmatter + sub-command table)
        ├── CHANGELOG.md                  # newest-first version history; drives upgrade diffs
        ├── CODING_STANDARDS.md           # seeded into each workspace
        ├── commands/
        │   ├── bootstrap.md              # fresh-machine dependency install (bootstrap subcommand)
        │   ├── init.md                   # 15-step setup flow (github/gitlab subcommand)
        │   ├── update.md                 # incremental upgrade flow (update subcommand)
        │   └── clone.md                  # repo clone + scaffolding (clone subcommand)
        └── memory-seeds/
            └── feedback_ui_ux_pro_max_with_superpowers.md
```

---

## Adding a new memory seed

1. Create `skills/init-workdir/memory-seeds/<type>_<topic>.md` with frontmatter:
   ```markdown
   ---
   name: Short title
   description: One-line "why this exists"
   type: feedback | reference | project | user
   ---

   Body. For feedback/project, lead with the rule, then **Why:** and **How to apply:** lines.
   ```
2. Bump the skill's `version:` and add a `CHANGELOG.md` entry referencing the new seed.
3. Open a PR.
4. After merge, the seed is picked up on the next `/init-workdir update`.

---

## Workspace structure after `init`

```
<WORKDIR>/
├── CLAUDE.md                     # Compound intelligence hub — @includes all repo CLAUDE.mds
├── CODING_STANDARDS.md           # Workspace-scoped (customisable)
├── .gitconfig                    # Workspace-scoped git identity
├── .gitignore .claudeignore .graphifyignore
├── .init-workdir/
│   └── state.json                # Skill version manifest
├── .claude/
│   └── settings.json             # graphify PreToolUse hook
├── graphify-out/                 # Cross-repo knowledge graph (built on demand)
├── knowledgebase/                # Architecture docs/diagrams vault
└── <group>/<repo>/               # Cloned repos, organised by group
```

---

## Subcommand summary

| Command | What it does |
|---------|--------------|
| `/init-workdir bootstrap` | Fresh-machine setup: external CLIs, third-party plugins, global hooks |
| `/init-workdir github` | First-time init, GitHub provider |
| `/init-workdir gitlab` | First-time init, GitLab provider |
| `/init-workdir clone <url>` | Clone a repo, auto-detect group, scaffold `Features.md`/`test-cases/`, update workspace `CLAUDE.md`, rebuild cross-repo graph |
| `/init-workdir clone <url> --group <name>` | Same, with manual group override |
| `/init-workdir update` | Bring workspace up to current skill version; prints changelog diff, runs idempotent steps |
| `/init-workdir help` | Print the usage block |

---

## Contributing

The skill source of truth lives in this plugin folder. To make changes:

1. Edit the relevant file under `skills/init-workdir/`
2. Bump `version:` in `SKILL.md`
3. Add a section at the top of `CHANGELOG.md` describing what changed
4. Open a PR

After merge, users pick up changes on `/plugin update init-workdir@claude-init` (or a
Claude Code restart) and `/init-workdir update` from inside their workspaces.
