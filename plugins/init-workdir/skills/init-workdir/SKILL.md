---
name: init-workdir
description: >
  Use when the user wants to initialize a multi-repo working directory, authenticate with
  GitHub or GitLab, set up compound intelligence (graphify, claude-mem, MEMORY.md) across
  repositories, configure project-level gitconfig, clone and organize repositories by group,
  update an existing workspace to the latest skill version, or bootstrap a fresh machine
  with all required CLIs/plugins/hooks. Subcommands: bootstrap, github, gitlab, clone, update.
  Triggers: "init workdir", "set up workspace", "clone repo into workspace", "organize
  repositories by group", "init workspace", "update workspace", "upgrade workspace",
  "bootstrap workspace dependencies", "fresh machine setup".
argument-hint: <bootstrap|github|gitlab|clone|update> [repo-url-or-name] [--group <name>]
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
version: 1.7.0
---

# Init Working Directory

Set up a parent directory for multi-repo development. Handles provider authentication,
project-level git identity, compound intelligence (cross-repo graphify + claude-mem + MEMORY.md),
and repository cloning organized into group folders.

## Usage

```
/init-workdir bootstrap                   — Fresh-machine setup: install all CLIs, plugins, hooks, bundled skills
/init-workdir github                      — Initialize workspace with GitHub (gh CLI)
/init-workdir gitlab                      — Initialize workspace with GitLab (glab CLI)
/init-workdir clone <url>                 — Clone repo, auto-detect group from namespace
/init-workdir clone <url> --group <name>  — Clone repo into a specific group folder
/init-workdir update                      — Update existing workspace to latest skill version
```

Typical fresh-machine flow:

```
/plugin install init-workdir@claude-init  # one-time, after registering the marketplace
/init-workdir bootstrap                   # installs all dependencies
/init-workdir gitlab                      # provisions a workspace
```

## Sub-Command Routing

| First token     | Action |
|-----------------|--------|
| `bootstrap`     | Read `~/.claude/skills/init-workdir/commands/bootstrap.md` |
| `github`        | Read `~/.claude/skills/init-workdir/commands/init.md`, pass `provider: github` |
| `gitlab`        | Read `~/.claude/skills/init-workdir/commands/init.md`, pass `provider: gitlab` |
| `clone`         | Read `~/.claude/skills/init-workdir/commands/clone.md`, pass remaining args |
| `update`        | Read `~/.claude/skills/init-workdir/commands/update.md` |
| *(empty)* / `help` | Print the Usage block above |
| *anything else* | Ask: "Did you mean `bootstrap`, `github`, `gitlab`, `clone <url>`, or `update`?" |

When reading a command file, follow every instruction inside it exactly.

## Workspace Structure After Init

```
<WORKDIR>/
├── CLAUDE.md              # Compound intelligence hub — @includes all repo CLAUDE.mds
├── .gitconfig             # Workspace-scoped git identity (wired via ~/.gitconfig includeIf)
├── graphify-out/          # Cross-repo knowledge graph (built on demand)
├── <group>/
│   ├── <repo-1>/          # Cloned repo (graphify hook optional, installed per repo)
│   └── <repo-2>/
└── <group2>/
    └── <repo-3>/
```
