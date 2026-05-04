# Music Meta-Archetype

The `music/` directory is a **meta-archetype** for the knowledge-base skill. Unlike single-file archetypes (e.g. `software-architecture.md`), it contains multiple sub-archetype files, a manifest, and scripts that are dispatched dynamically based on the output type requested.

## Directory layout

```
archetypes/music/
├── README.md              — this file
├── ICON_REQUESTS.md       — icons missing from Lucide's set, queued for future request
├── manifest.json          — domain indicators, sub-archetype routing, purpose-keywords
├── diagram.md             — diagram generation conventions (layers, icons, connections)
├── svg.md                 — SVG renderer catalog (all 14 renderers with flag reference)
├── tabs.md                — guitar-tabs style guide (tradition defaults, alphaTex templates)
└── documents/
    ├── theory-primer.md   — template: music theory primer (scales, modes, harmony)
    ├── biography.md       — template: composer / musician biography
    ├── song-breakdown.md  — template: song or piece analysis
    ├── instrument-profile.md — template: instrument reference page
    ├── tradition-overview.md — template: musical tradition / genre overview
    ├── history-timeline.md   — template: historical narrative with timeline
    └── comparative.md     — template: comparative analysis of two or more topics
```

## How it is selected

The archetype scorer (`kb_archetype.py`) matches the user's topic string against `manifest.json`'s `domain-indicators` list. If the music archetype wins the score, the `--output-type` flag selects which sub-archetype to use:

| `--output-type` | Sub-archetype file |
|---|---|
| `diagram` | `diagram.md` |
| `svg` | `svg.md` |
| `tabs` | `tabs.md` |
| `document` | selected from `documents/` using purpose-keyword matching |

The CLI output is always three tokens: `<name> <subtype> <path>`.

Example:
```
$ python3 kb_archetype.py --archetypes-dir archetypes --topic "Raga Yaman" --output-type diagram
music diagram /path/to/archetypes/music/diagram.md

$ python3 kb_archetype.py --archetypes-dir archetypes --topic "music biography of Ravi Shankar" --output-type document
music biography /path/to/archetypes/music/documents/biography.md
```

## Domain indicators

The music archetype matches topics containing any of these keywords (from `manifest.json`):

> music, raga, maqam, tala, chord, scale, harmony, rhythm, melody, mode, interval,
> counterpoint, polyphony, modulation, temperament, intonation, timbre, texture,
> instrument, score, notation, solfege, octave, pitch, key signature, time signature,
> composer, improvisation, ornament, gamaka, microtone, quartertone, shruti, swara,
> fretboard, tablature, chord progression, voice leading, arrangement, orchestration

## Scripts

These scripts are shared by all knowledge-base commands when a music topic is detected:

| Script | Purpose |
|---|---|
| `scripts/kb_svg.py` | 14-renderer pure-stdlib SVG generator |
| `scripts/kb_midi.py` | Pure-stdlib MIDI Format-1 writer; wired into `kb_svg.py --midi-out` |
| `scripts/kb_validate_music.py` | Music-domain linter (SVG, MIDI, Markdown, JSON) |

## Adding a new tradition

1. Add the tradition's key indicators to `manifest.json`'s `domain-indicators` list.
2. Add a badge entry to `TRADITION_BADGE` in `kb_svg.py` with a hex color.
3. Add tradition-specific row to the tables in `tabs.md` (tuning, tempo, etc.).
4. If the tradition needs custom layer colors in diagrams, add a note to `diagram.md`.
5. Add the tradition tag to `svg.md`'s Tradition Badge Color Reference table.

## Extending with new renderers

1. Add the renderer function `render_<name>(args, theme)` to `kb_svg.py`.
2. Register it in the `renderers` dict in `render()`.
3. Add its argparse flags to `main()`.
4. Write a golden-master test in `scripts/tests/test_kb_svg.py`.
5. Document it in `svg.md` under a new numbered section.
6. Update `commands/svg.md`'s renderer-to-topic mapping table.
