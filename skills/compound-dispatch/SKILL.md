---
name: compound-dispatch
description: Enrich subagent prompts with unified context from graphify (structural), claude-mem (temporal), and MEMORY.md (curated)
---

# Compound Dispatch

Enriches subagent prompts with "Prior Knowledge" from all three memory systems before dispatching them. This bridges the gap where subagents normally start with blank context.

## When to Use

- Before dispatching any subagent via the Agent tool for implementation tasks
- When a subagent needs to understand file relationships, past decisions, or user preferences
- Especially important for SDD (Subagent-Driven Development) implementation tasks

## How It Works

1. Parse the task description to extract file paths mentioned
2. Run `gather-context.py` to query all three memory systems
3. Prepend the output as a "Prior Knowledge" section in the subagent prompt

## Usage

### From the main agent (before dispatching)

```bash
# Query context for specific files the subagent will touch
python3 ~/.claude/skills/compound-dispatch/gather-context.py \
  src/app/components/MyComponent.tsx \
  src/app/utils/helpers.ts
```

### Inject into subagent prompt

Take the output and prepend it to the subagent's task description:

```
## Prior Knowledge (auto-injected by compound-dispatch)

{output from gather-context.py}

## Task

{the actual task description}
```

### Subagents can self-serve

Subagents with Bash access can query context mid-task:

```bash
python3 ~/.claude/skills/compound-dispatch/gather-context.py path/to/file.ts
```

## Step-by-Step

1. Identify which files the subagent task will touch (from the task description or plan)
2. Run `gather-context.py` with those file paths
3. Review the output — it includes:
   - **Structural Context** (graphify): community membership, neighbors, relationships
   - **Temporal Context** (claude-mem): recent observations about those files
   - **User Preferences** (MEMORY.md): relevant curated memories
4. Include the output in the subagent's prompt as "Prior Knowledge"
5. Dispatch the subagent as normal

## Example

```
Using compound-dispatch to enrich the subagent prompt.

python3 ~/.claude/skills/compound-dispatch/gather-context.py src/app/components/Header.tsx

Output:
## Prior Knowledge

### Structural Context (graphify)
- Header.tsx is in Community 3 (UI Components), connected to:
  -> types.ts [imports ViewMode type]
  -> architectureDesigner.tsx [imported_by]

### Temporal Context (claude-mem)
- [2026-04-11] Fixed CSS invisible/pointer-events-none for view mode toggle stability
- [2026-04-11] AutoArrangeDropdown added with hierarchical-tb/lr and force options

### User Preferences (MEMORY.md)
- Extract callback clusters into hooks when architectureDesigner.tsx grows
```

## Lessons Learned Integration

After all tasks in a plan complete, capture lessons learned:
- Which plan steps needed adjustment (and why)
- Patterns reviewers consistently caught
- What worked well vs. what caused friction

Save as a memory entry: `description: "Lessons learned: [feature-name]"`
