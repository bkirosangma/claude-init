# knowledge-base

Unified skill for managing knowledge-base vaults — architecture documents, design diagrams,
ADRs, runbooks, and music notation. This is the **full upstream version**: the trim that some
internal forks apply to drop music-domain features (SVG music visualisation, guitar tabs,
music archetype, music validators) is **not** applied here.

## Trigger

```
/knowledge-base   or   /kb
```

## Subcommands

| Command | What it does |
|---|---|
| `/kb init <path>` | Set up a vault at `<path>` (creates `.archdesigner/config.json`, `docs/` structure) |
| `/kb document "<topic>"` | Generate a standalone architecture/design document |
| `/kb diagram "<topic>"` | Generate a diagram on any topic |
| `/kb create "<topic>"` | Generate document + linked diagram together |
| `/kb edit <path> "<change>"` | Modify an existing diagram JSON; enforces placement constraints, collision checks, schema field names |
| `/kb svg "<topic>"` | Generate a music SVG visualisation (staff, fretboard, chord box, raga clock, maqam, jianpu, sargam, tala, gamelan, gongche, neume, clave, rhythm) |
| `/kb guitar-tabs "<topic>"` | Generate a playable guitar tab (`.alphatex` format) |
| `/kb validate <path>` | Check or auto-fix a diagram JSON / music asset against its schema |
| `/kb transform <path>` | Bring an existing `.md` or `.json` file into skill-format conformance |

## Music-domain features (full version only)

- **Archetype**: `archetypes/music/` — diagram, documents, svg, tabs templates and an icon-request manifest
- **Scripts**: `kb_midi.py`, `kb_svg.py`, `kb_validate_music.py`
- **SVG goldens**: 16 reference visualisations under `scripts/tests/fixtures/svg_golden/` covering Western, Indian (raga, tala, sargam, jianpu), Middle-Eastern (maqam), Indonesian (gamelan, gongche), and percussion (clave, rhythm) traditions
- **Tests**: `test_kb_archetype.py`, `test_kb_svg.py`, `test_kb_validate_music.py`

## Layout

```
plugins/knowledge-base/
├── .claude-plugin/plugin.json
├── hooks/
│   ├── hooks.json
│   └── check-update.sh
└── skills/knowledge-base/
    ├── SKILL.md                    # router + frontmatter
    ├── archetypes/
    │   ├── _archetype-template.md
    │   ├── music/                  # diagram, documents, svg, tabs templates + icon manifest
    │   ├── roadmaps.md
    │   └── software-architecture.md
    ├── commands/                   # init, document, diagram, create, edit, svg, guitar-tabs, validate, transform
    ├── docs/superpowers/           # superpowers integration notes
    └── scripts/                    # kb_*.py validation/migration/transform/music helpers + tests
```

## Installation

Bundled with `init-workdir`. Copied to `~/.claude/skills/knowledge-base/` by the bootstrap
subcommand:

```
/init-workdir bootstrap
```

Or standalone:

```
/plugin install knowledge-base@claude-init
```

## Dependencies

The vault scripts under `scripts/` are pure Python (stdlib + a few PyPI packages where
applicable). The skill activates automatically when the user types `/knowledge-base`, `/kb`,
or related triggers like "create architecture", "design diagram", "init vault", "music svg",
"guitar tab".
