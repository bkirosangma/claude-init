---
name: workdir
description: >
  Use when the user wants to initialize a multi-repo working directory, authenticate with
  GitHub or GitLab, set up compound intelligence (graphify, claude-mem, MEMORY.md) across
  repositories, configure project-level gitconfig, clone and organize repositories by group,
  update an existing workspace to the latest skill version, or bootstrap a fresh machine
  with all required CLIs/plugins/hooks, or pull the latest changes for every repository in
  the workspace (handling dirty trees and diverged branches safely). Subcommands: bootstrap,
  init <github|gitlab>, clone, update, pull.
  Triggers: "init workdir", "set up workspace", "clone repo into workspace", "organize
  repositories by group", "init workspace", "update workspace", "upgrade workspace",
  "bootstrap workspace dependencies", "fresh machine setup", "pull all repos", "update all repos",
  "git pull workspace".
argument-hint: <bootstrap|init|clone|update|pull> [github|gitlab|repo-url] [--group <name>]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
version: 2.2.0
---

# Workdir

Set up a parent directory for multi-repo development. Handles provider authentication,
project-level git identity, compound intelligence (cross-repo graphify + claude-mem + MEMORY.md),
and repository cloning organized into group folders.

## Usage

```
/workdir bootstrap                   — Fresh-machine setup: install all CLIs, plugins, hooks, bundled skills
/workdir init github                 — Initialize workspace with GitHub (gh CLI)
/workdir init gitlab                 — Initialize workspace with GitLab (glab CLI)
/workdir clone <url>                 — Clone repo, auto-detect group from namespace
/workdir clone <url> --group <name>  — Clone repo into a specific group folder
/workdir update                      — Update existing workspace to latest skill version
/workdir pull                        — Pull latest changes for every repo in the workspace
```

Typical fresh-machine flow:

```
/plugin install workdir@claude-init   # one-time, after registering the marketplace
/workdir bootstrap                    # installs all dependencies
/workdir init gitlab                  # provisions a workspace
```

## Sub-Command Routing

Parse the first token as the subcommand. For `init`, the second token must be the provider
(`github` or `gitlab`).

| First token        | Second token       | Action |
|--------------------|--------------------|--------|
| `bootstrap`        | *(any/none)*       | Read `~/.claude/skills/workdir/commands/bootstrap.md` |
| `init`             | `github`           | Read `~/.claude/skills/workdir/commands/init.md`, pass `provider: github` |
| `init`             | `gitlab`           | Read `~/.claude/skills/workdir/commands/init.md`, pass `provider: gitlab` |
| `init`             | *(empty/other)*    | Ask: "Which provider? `github` or `gitlab`?" |
| `clone`            | *(url + flags)*    | Read `~/.claude/skills/workdir/commands/clone.md`, pass remaining args |
| `update`           | *(any/none)*       | Read `~/.claude/skills/workdir/commands/update.md` |
| `pull`             | *(any/none)*       | Read `~/.claude/skills/workdir/commands/pull.md` |
| *(empty)* / `help` | —                  | Print the Usage block above |
| *anything else*    | —                  | Ask: "Did you mean `bootstrap`, `init <github\|gitlab>`, `clone <url>`, `update`, or `pull`?" |

When reading a command file, follow every instruction inside it exactly.

## Workspace Structure After Init

```
<WORKDIR>/
├── CLAUDE.md              # Compound intelligence hub — @includes all repo CLAUDE.mds
├── .gitconfig             # Workspace-scoped git identity (wired via ~/.gitconfig includeIf)
├── .workdir/              # Skill state manifest (state.json)
├── graphify-out/          # Cross-repo knowledge graph (built on demand)
├── <group>/
│   ├── <repo-1>/          # Cloned repo (graphify hook optional, installed per repo)
│   └── <repo-2>/
└── <group2>/
    └── <repo-3>/
```
