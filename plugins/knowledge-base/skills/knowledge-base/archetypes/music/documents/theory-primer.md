---
purpose: theory-primer
description: Template for music theory-primer documents. AI generators copy this structure; vault content gets a real frontmatter from §5 of the design spec.
---

# Theory-Primer Template

Generated documents using this template MUST start with the shared frontmatter (purpose, title, traditions, era, created, related) defined in `archetypes/music/manifest.json` reference. Body sections follow this order:

## <Concept>

One-paragraph definition of the concept in plain prose.

## Definition

Formal definition with technical vocabulary. Use parenthetical translations for non-English terms (e.g., "raga (a melodic framework)").

## Notation

How this concept is written down. Reference SVG renderers where applicable:
- `staff` for Western notation
- `sargam` for Indian cipher
- `jianpu` for Chinese cipher
- etc.

Embed the SVG: `![[<topic-slug>.svg]]`.

## Worked Examples

Two or three concrete examples showing the concept in use. Each example includes:
- a notation snippet (SVG embed or inline reference)
- a prose explanation walking through what the listener/reader hears or sees

## Cross-Tradition Parallels

If `traditions:` frontmatter has multiple entries OR the concept has well-known analogues in other traditions, dedicate a subsection per parallel:

### In <Tradition Name>

How the same or analogous concept appears here. Note differences in name, function, and notation.

## Visual Overview

Link to companion diagram and SVG:
- Diagram: `[[<topic-slug>.json]]`
- SVG: `![[<topic-slug>.svg]]`

## Cross-References

Wiki-links to related vault content:
- `[[<related-doc-1>]]` — relationship description
- `[[<related-doc-2>]]` — relationship description

## Sources

Citations as a numbered list. Prefer canonical references (Helmholtz for Western theory, Bharata's Natya Shastra for Indian, al-Farabi for maqam, etc.).
