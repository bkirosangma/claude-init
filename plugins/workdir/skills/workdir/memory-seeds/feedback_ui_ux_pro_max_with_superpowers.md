---
name: Pair ui-ux-pro-max with superpowers skills for UI work
description: When a superpowers workflow touches UI components, styling, or visual design, invoke ui-ux-pro-max alongside the workflow skill — they don't auto-pair
type: feedback
---

When a superpowers workflow touches UI components, styling, layout, palette, typography, or
any visual design decision, invoke `ui-ux-pro-max` alongside the workflow skill. They are
independent skills loaded into the same context — neither one calls the other automatically.

**Why:** ui-ux-pro-max provides design intelligence (67 styles, 96 palettes, 57 font pairings,
99 UX guidelines, stack-aware code generation) that superpowers skills do not. Without
explicit pairing, superpowers brainstorms/plans/implementations may freelance on design and
miss the accessibility, spacing, color, and responsive constraints the design skill would
catch. compound-dispatch enriches subagent prompts with graph + memory + MEMORY.md context
but does not surface ui-ux-pro-max as a required skill — the parent agent must name the
design pairing explicitly when dispatching.

**How to apply:**
- `superpowers:brainstorming` for a UI feature → also invoke ui-ux-pro-max for style/palette/layout direction before the brainstorm crystallises
- `superpowers:writing-plans` for UI work → ui-ux-pro-max informs component breakdown, design tokens, and stack-specific code targets
- `superpowers:executing-plans` / `subagent-driven-development` → name the design constraints in the subagent prompt so the dispatched agent invokes ui-ux-pro-max alongside its primary skill
- `superpowers:systematic-debugging` for a UI bug → bring in ui-ux-pro-max for visual/layout root-cause hypotheses
- `superpowers:requesting-code-review` / `receiving-code-review` on UI code → use ui-ux-pro-max as a second opinion on accessibility, spacing, color contrast, responsive behaviour
