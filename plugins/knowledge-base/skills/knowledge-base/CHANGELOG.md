# knowledge-base Changelog

Each version section lists what changed in that version. Sections are sorted newest-first.

Format: `## <version> — <YYYY-MM-DD>` followed by a bulleted list of changes.

The skill source of truth lives at `<knowledge-base-project>/skills/knowledge-base/` and is
mirrored byte-identical to `~/.claude/skills/knowledge-base/`. The marketplace copy at
`claude-init/plugins/knowledge-base/skills/knowledge-base/` ships the same content for
distribution.

## 1.3.0 — 2026-05-13
- **Mandatory graphify pre-check across every kb subcommand** (except `init`). Promotes the
  previous best-effort "Compound Intelligence" block in `SKILL.md` to a hard gate that runs
  before `diagram`, `document`, `create`, `edit`, `svg`, `guitar-tabs`, `transform`, and
  `validate`. Closes the gap where edit/validate/transform/svg/guitar-tabs had no pre-check
  at all and the generation commands treated graphify as optional
- **Stale-graph guard** — `find -newer GRAPH_REPORT.md` triggers an auto `graphify . --update`
  when the index lags behind newer vault files
- **STRONG / ADJACENT / NONE classification** for graphify matches. STRONG matches prompt the
  user (Open / Edit / Generate-new-anyway — no auto-open); ADJACENT matches carry into
  `gatheredContext.adjacentMatches`; NONE continues
- claude-mem + MEMORY.md demoted to "Companion Intelligence (best-effort, after graphify)" —
  still run, no longer gate
- Per-command **Step 0** added to: create, diagram, document, edit, guitar-tabs, init (exempt
  marker), svg, transform, validate
- Skip conditions (no vault / no `graphify-out/`) emit standard notices

## 1.2.0 — 2026-05-06
MVP 5 — KB Skill Update. Three coordinated changes covered by this version.

- **Source gathering for `svg` and `guitar-tabs`** (commit `1a90350`):
  - `svg.md` Step 1.5 gathers 1–4 canonical sources via WebSearch; Step 5c writes
    `<file>.svg.refs.json` (lazy — skipped when no sources, per delete-when-empty rule)
  - `guitar-tabs.md` Step 4.5 gathers sources; Step 6 writes `<file>.alphatex.refs.json` v3
    with `sectionRefs`/`trackRefs` empty (app populates on first edit)
  - Both files note `attachedTo?` is reserved for the deferred MVP-2 SVG/Tab attachment
    branches and must NOT be populated by the skill
- **`kb_transform.py` preserves frontmatter `sources:`** (commit `8be0dbf`):
  - The transform contract is no longer "strip all frontmatter" — frontmatter is preserved
    when (and only when) it carries a non-empty `sources:` field. Legacy `title:`-only
    frontmatter is still stripped (with title promotion to H1 when body has no H1)
  - Inline `sources: [{url: "...", title: "..."}]` is rewritten to canonical block-list form
    (the project's TS parser silently dropped inline values — that data-loss path is now
    closed)
  - Per-entry validity is enforced during rewrite — entries with non-`http(s)` URLs are
    dropped, empty `title` fields are omitted
- **`kb_validate.py` and `kb_validate_doc.py` hardening for sources** (commit `c61ff61`):
  - `kb_validate.py --fix` now strips bad source entries across every sources scope
    (top-level `data.sources` + per-entity `nodes`, `connections`, `flows`, `documents`).
    `sources` key is removed when the cleaned list is empty
  - Top-level `data.sources` is now validated (new `_validate_sources` call site)
  - `kb_validate_doc.py` warns on inline-list `sources:` in frontmatter (new
    `FRONTMATTER_INLINE_SOURCES_RE` regex, points at `kb_transform.py --add-conventions`)
  - Roadmaps archetype: minimal `flow-minimum-path` companion example restored next to
    `flow-fullstack-path` (linear 3-connections/4-nodes shape, single start, single end)

## 1.0.0 — initial release
- Vault initialization (`init`), document creation (`document`), diagram creation
  (`diagram`), combined doc+diagram (`create`), editing (`edit`), SVG (`svg`), Guitar Tabs
  (`guitar-tabs`), validation (`validate`), transformation (`transform`)
- Three archetypes: `_archetype-template`, `roadmaps`, `software-architecture`
- Helper scripts: `kb_validate.py`, `kb_validate_doc.py`, `kb_transform.py` (and music-domain
  helpers under `scripts/`)
