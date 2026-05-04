# Design: Music Meta-Archetype for Knowledge-Base Skill

**Date:** 2026-05-02
**Status:** Approved (brainstorming complete; ready for implementation plan)
**Author:** Walked through interactively; decisions captured below.

## 1. Overview

Add a `music` archetype family to the `knowledge-base` skill. Unlike the existing single-file `software-architecture.md` archetype, music ships as a **meta-archetype**: a directory containing one sub-archetype per output medium (diagram, document, SVG, tabs). The skill engine selects the correct sub-archetype based on the user's command (`/kb diagram` vs. `/kb document` vs. `/kb svg`) and topic.

The archetype is **globally inclusive** — it covers Western art music, jazz, blues, folk, and non-Western traditions (Hindustani, Carnatic, Arabic maqam, Persian dastgah, gamelan, West African, East Asian, Latin American) on equal footing. Tradition is **hybrid**: required frontmatter on every document, structurally significant only when content spans multiple traditions.

The spec also introduces:

- `kb_svg.py` — pure-stdlib Python script that renders 14 distinct SVG visualizations of musical concepts.
- `kb_midi.py` — pure-stdlib MIDI writer + best-effort cross-platform playback shim.
- An extension to `kb_archetype.py` for meta-archetype dispatch (selecting sub-archetypes by output type and purpose hint).
- An extension to the `validate` command for tradition-tag linting on music documents.

## 2. Decisions Captured

| Question | Decision |
|---|---|
| Q1: Archetype shape | C — Meta-archetype (directory of sub-archetypes per medium) |
| Q2: Tradition scope | C — Globally inclusive |
| Q3: Tradition handling | C — Hybrid (required frontmatter; structural when multi-tradition) |
| Q4: SVG approach | C — Generator script (`kb_svg.py`) |
| Q5: Document templates | B — Per-purpose template family (7 templates) |
| Q6 (deferred items) | All deferred items pulled into v1 except: world-music meta (subsumed) and app-side icon pack (separate repo, tracked as wishlist) |

## 3. Architecture

### File Layout

```
~/.claude/skills/knowledge-base/
├── archetypes/
│   ├── _archetype-template.md          (existing)
│   ├── software-architecture.md        (existing — single-file archetype, untouched)
│   └── music/                          (NEW — meta-archetype family)
│       ├── README.md                   (entry point — explains the family)
│       ├── manifest.json               (sub-archetype registry, domain-indicators, purpose-keywords)
│       ├── diagram.md                  (sub-archetype: JSON diagram conventions)
│       ├── tabs.md                     (sub-archetype: tab conventions, refs guitar-tabs cmd)
│       ├── svg.md                      (sub-archetype: SVG conventions, calls kb_svg.py)
│       ├── ICON_REQUESTS.md            (wishlist of icons to request from the visual editor app team)
│       └── documents/
│           ├── theory-primer.md
│           ├── biography.md
│           ├── song-breakdown.md
│           ├── instrument-profile.md
│           ├── tradition-overview.md
│           ├── history-timeline.md
│           └── comparative.md
├── scripts/
│   ├── kb_archetype.py                 (extended — meta-archetype dispatch)
│   ├── kb_svg.py                       (NEW — 14 music SVG renderers)
│   ├── kb_midi.py                      (NEW — MIDI writer + playback shim)
│   └── tests/
│       ├── test_kb_archetype.py        (NEW — meta-archetype dispatch tests)
│       ├── test_kb_svg.py              (NEW — golden-master SVG tests)
│       ├── test_kb_midi.py             (NEW — MIDI binary fixtures)
│       └── fixtures/
│           ├── svg_golden/             (NEW — 14 renderer reference SVGs)
│           ├── midi_golden/            (NEW — per-format MIDI binaries)
│           └── lint_music/             (NEW — 10 frontmatter fixtures)
└── commands/
    ├── diagram.md                      (touched — sub-archetype dispatch, 3-token output)
    ├── document.md                     (touched — NEW archetype consultation step)
    ├── svg.md                          (NEW — sub-command for SVG generation)
    └── validate.md                     (touched — NEW music-lint extension)
```

### Dispatch Flow

1. User runs `/kb <subcommand> "<topic>"` (where `<subcommand>` is `diagram`, `document`, `svg`, etc.).
2. Command file performs vault detection and gathers compound intelligence (graphify + claude-mem + MEMORY.md).
3. Command runs:
   ```
   python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
     --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
     --topic "<topic>" \
     --output-type <diagram|document|svg|tabs> \
     [--purpose-hint "<topic-or-explicit-purpose>"]
   ```
4. Selector returns: `<archetype-name> <subtype> <absolute-path-to-sub-archetype>`.
5. Command reads the sub-archetype file and follows its instructions.
6. For `/kb svg`, the command shells out to `kb_svg.py` with renderer-specific parameters.

### Back-Compat Guarantees

- `software-architecture.md` is single-file and continues to work unchanged.
- Old 2-token output (`<name> <path>`) is preserved as a parseable subset of the new 3-token output (the middle `subtype` token is empty for single-file archetypes).
- `--output-type` defaults to `diagram` if omitted (historical behavior).
- Existing `commands/diagram.md` callers that don't pass `--output-type` keep working.

## 4. `archetypes/music/diagram.md` Sub-Archetype

### Layer Conventions (concept-driven default)

When a diagram covers a single tradition, layers are concept-driven. When nodes span 2+ traditions, the diagram switches to tradition-driven layers (auto-detected by the AI from node frontmatter / topic).

**Concept-driven layers (8):**

| Layer | Purpose | Background | Border |
|---|---|---|---|
| Pitch | Notes, intervals, accidentals, microtones | `#eff6ff` | `#bfdbfe` |
| Scales / Modes | Pitch collections — major, modes, ragas, maqamat, pelog/slendro | `#fef3c7` | `#fcd34d` |
| Harmony | Chords, progressions, voice-leading | `#f5f3ff` | `#c4b5fd` |
| Rhythm | Meter, talas, additive patterns, polyrhythm | `#fff1f2` | `#fecdd3` |
| Form | Sonata, AABA, alap–jor–jhala, taqsim | `#ecfeff` | `#a5f3fc` |
| Instrumentation | Instruments, timbral roles, ensembles | `#f1f5f9` | `#cbd5e1` |
| Performance | Articulation, ornamentation (gamaka, melisma), dynamics | `#fdf2f8` | `#f9a8d4` |
| Tradition / Era | Historical / cultural framing | `#ecfdf5` | `#6ee7b7` |

**Tradition-driven layers** (used when 2+ traditions): one layer per tradition; layer background uses the tradition badge color at low opacity (~15%).

### Tradition Badges (11)

The diagram JSON has no native badge field, so tradition appears in each node's `sub` field as a short tag (e.g., `Hindustani`, `Jazz`).

| Tradition | Badge color | When used |
|---|---|---|
| Western Common-Practice | `#2563eb` | Classical, art music |
| Jazz / Blues | `#7c3aed` | Jazz, blues, gospel, R&B |
| Hindustani | `#dc2626` | North Indian classical |
| Carnatic | `#ea580c` | South Indian classical |
| Arabic Maqam | `#059669` | Arabic, Turkish, Andalusian |
| Persian Dastgah | `#0891b2` | Iranian classical |
| Gamelan | `#a16207` | Javanese / Balinese |
| West African | `#16a34a` | Mande, Yoruba, Highlife |
| East Asian | `#9333ea` | Chinese, Japanese, Korean |
| Latin American | `#e11d48` | Son, samba, bossa, tango |
| Folk / Traditional | `#475569` | Catch-all for unmarked folk |

### Icon Mappings (within the 41 registered Lucide icons)

The 41-icon registry is the hard constraint. Best-fit mappings:

| Music concept | Icon | Rationale |
|---|---|---|
| Note / pitch | `Radio` | Waveform → pitch |
| Scale / mode / raga | `Activity` | Melodic contour |
| Chord / harmony | `Layers` | Stacked tones |
| Rhythm / tala / meter | `Zap` | Pulse |
| Voice / vocal | `User` | Human |
| Ensemble / choir | `Users` | Multiple |
| Composition / score | `FileCode` | Notated work |
| Notation system | `Code` | Symbolic |
| Fretted instrument | `Cable` | Strings |
| Wind instrument | `Wifi` | Airflow |
| Keyed instrument | `Cpu` | Mechanical grid |
| Percussion | `Cog` | Repurposed |
| Composer / theorist | `User` | Individual |
| Tradition / lineage | `GitBranch` | Branching descent |
| Region / geography | `Globe` | World |
| Era / period | `Archive` | Historical |
| Form / structure | `Box` | Container |
| Cadence / resolution | `ShieldCheck` | Resolved |
| Tension / dissonance | `Bell` | Unresolved tension |
| Modulation / transition | `Plug` | Connecting |
| Tuning system | `Cog` | Configuration |
| Improvisation | `GitBranch` | Branching paths |
| Genre | `Folder` | Category |
| Recording / archive | `Archive` | Archival |

App-side icon pack expansion (Music-note, Treble-clef, Drum, Microphone, Wave, Piano-key) is tracked in `archetypes/music/ICON_REQUESTS.md` for the visual editor app team.

### Connection Semantics (8 flow types)

| Flow type | Color | Meaning |
|---|---|---|
| Melodic motion | `#3b82f6` blue | Note → note, scale degree |
| Harmonic progression | `#8b5cf6` purple | Chord → chord (V–I, ii–V–I) |
| Rhythmic relationship | `#f59e0b` amber | Pulse, accent, polyrhythm |
| Structural connection | `#64748b` slate | Section → section |
| Cross-tradition mapping | `#10b981` emerald | Mode ↔ raga, chord ↔ jins |
| Influence / lineage | `#ec4899` pink | Teacher → student, era → era |
| Tension / dissonance | `#ef4444` red | Unresolved |
| Cadence / resolution | `#0ea5e9` sky | Resolution to tonic |

### Layout Preferences

- **Primary flow:** top-to-bottom for harmonic/temporal; left-to-right for timeline/scale-degree sequences.
- **Density:** moderate (same 70px node gaps and 120–160px layer gaps as `software-architecture`).
- **Emphasis:** the tonic (or its analogue: sa, drone, finalis) anchors the visual spine when present.
- **Symmetric pairs:** parallel-tradition pairs (Aeolian ↔ Bhairavi) mirror around the center axis.

The diagram sub-archetype reuses the JSON schema, anchor system, spacing rules, and condition-node procedures from `software-architecture.md` verbatim; it overrides only the layer/icon/color/connection-semantic content.

## 5. Document Templates

### Shared Frontmatter (all 7 templates)

```yaml
---
type: document
purpose: <theory-primer | biography | song-breakdown | instrument-profile | tradition-overview | history-timeline | comparative>
title: "<Topic>"
traditions: [<tradition-tag>, ...]   # required; from the 11 badges in §4
era: "<period>"                       # optional
created: <ISO-8601>
related:
  documents: [<wiki-link>, ...]
  diagrams:  [<file.json>, ...]
  svgs:      [<file.svg>, ...]
  tabs:      [<file.alphatex>, ...]
---
```

### Closing Sections (all 7 templates)

`## Visual Overview` (links to companion diagram/SVG), `## Cross-References`, `## Sources`.

### Distinctive Bodies

| Template | Body sections |
|---|---|
| `theory-primer.md` | Concept · Definition · Notation · Worked Examples · Cross-Tradition Parallels |
| `biography.md` | Life · Era Context · Output · Style · Influence · Exemplary Works |
| `song-breakdown.md` | Form · Key/Mode · Harmony · Rhythm/Meter · Instrumentation · Analysis · Notable Performances |
| `instrument-profile.md` | Origin · Construction · Tuning · Technique · Repertoire · Notable Players · Variants Across Traditions |
| `tradition-overview.md` | Origin · Core Concepts · Notation & Tuning · Repertoire · Key Figures · Modern Practice |
| `history-timeline.md` | Scope · Eras (chronological) · Transitions · Influences · Legacy |
| `comparative.md` | Shared Concept · Tradition A Treatment · Tradition B Treatment · Mapping Table · Points of Divergence |

### Template Selection (purpose-keywords in `manifest.json`)

| Topic keyword pattern | Selected template |
|---|---|
| "biography of", "life of", "X (composer/musician)" | biography |
| "history of", "evolution of", "timeline" | history-timeline |
| "introduction to", "what is", "primer", "explained" | theory-primer |
| song titles, "analysis of", "breakdown", "anatomy of" | song-breakdown |
| "the (sitar\|piano\|...)", "instrument:" | instrument-profile |
| tradition names alone ("Carnatic music", "Gamelan music") | tradition-overview |
| " vs ", " compared to ", "across traditions" | comparative |
| ambiguous → fall back to | theory-primer |

## 6. `kb_svg.py` — 14 Renderers

### CLI

```
kb_svg.py --type <kind> [type-specific flags] [common flags]

Common flags:
  --out <path>              # default: stdout
  --width N --height N      # default: per-type
  --theme light|dark        # default: light
  --title "..."             # optional title above figure
  --tradition <tag>         # optional; tints accents using §4 badge color
  --midi-out <path>         # optional MIDI export (where notation has discrete pitches/durations)
  --play                    # best-effort: invoke afplay/aplay/start with generated MIDI
```

### Renderer Catalog

| `--type` | Tradition coverage | Key params |
|---|---|---|
| `staff` | Western, jazz; quartertones for maqam | `--clef treble\|bass\|alto\|tenor` · `--key "Eb major"` · `--time-sig 4/4` · `--notes "C4-q D4-q E4-h"` |
| `fretboard` | Any fretted (guitar, bass, banjo, ukulele, sitar, oud, lute) | `--strings N` · `--tuning "EADGBE"` · `--notes "0,2,3"` · `--highlight scale\|chord` |
| `circle-of-fifths` | Western; jazz extensions | `--highlight "Bb,F,C"` · `--jazz-extensions` · `--quartertones` |
| `raga-clock` | Hindustani, Carnatic | `--raga "Yaman"` · `--shrutis 12\|22` · `--show-vadi` |
| `maqam-jins` | Arabic, Turkish, Persian, Andalusian | `--jins "Hijaz"` · `--root D` · `--show-cents` |
| `gamelan-cipher` | Javanese, Balinese | `--tuning slendro\|pelog` · `--pattern "1 2 3 5 6 1"` |
| `chord-box` | Any fretted | `--instrument guitar\|uke\|...` · `--chord "Dm7"` · `--fingering "x x 0 2 1 1"` |
| `neume` | Medieval Western (chant) | `--mode "I"` · `--text "Kyrie eleison"` · `--neumes "punctum,clivis,torculus,..."` |
| `sargam` | Hindustani, Carnatic cipher | `--scale "Sa Re Ga Ma Pa Dha Ni"` · `--pattern "Sa Re Ga | Pa Ga Re Sa"` · `--gamaka` |
| `jianpu` | Chinese numbered notation | `--key "C"` · `--time-sig 4/4` · `--pattern "1 2 3 - | 5 3 1 -"` (dots above/below for octaves) |
| `gongche` | Traditional Chinese characters | `--scale "合四一上尺工凡"` · `--pattern "上尺工六五"` · CJK unicode + Noto Sans CJK web font ref |
| `rhythm-grid` | Universal (TR-808 style or Western 4-beat) | `--steps 16` · `--tracks "kick,snare,hi-hat"` · `--pattern "x...x...x...x..."` |
| `clave` | Afro-Cuban (3-2 / 2-3 son, rumba) | `--pattern son-3-2\|son-2-3\|rumba` · `--style staff\|dot-pattern` |
| `tala` | Indian rhythm cycle | `--tala "Teentaal"` · `--style circular\|linear` (default circular) · markers for sam/khali/tali/matra |

### Implementation Constraints

- **Pure stdlib.** No `pip install` in the skill. SVG is XML; we write strings.
- **Single file.** `scripts/kb_svg.py`, ~1,400–1,700 LOC for v1. Each renderer is one function.
- **Shared in-file primitives module:** line/circle/text/polygon helpers with consistent stroke widths, font sizes, paddings.
- **Color palette** mirrors §4 connection-semantic colors (melodic blue, harmonic purple, rhythmic amber, cadence sky, etc.) so SVGs and diagrams feel visually consistent.
- **Golden-master tests** in `scripts/tests/fixtures/svg_golden/` — reference SVGs for one canonical invocation per renderer; CI compares output byte-for-byte after stripping timestamps and UUIDs.
- **CJK font fallback.** `gongche` SVGs include `<style>` referencing Noto Sans CJK; degrades gracefully if the font is absent on the viewer's machine.
- **`<!-- kb-meta: ... -->` comment** on every generated SVG records the originating CLI invocation for round-trip understanding.

### `archetypes/music/svg.md` Content

The sub-archetype is the AI-facing manual:

1. **Renderer catalog** (which `--type` to pick for which musical concept).
2. **Parameter conventions** (note string format `C4-q` = C4 quarter-note, fingering format `x x 0 2 1 1`, sargam pattern syntax with `|` as bar separator and uppercase = madhya saptak, etc.).
3. **Cross-link rules** — every generated SVG gets a `<!-- kb-meta: ... -->` comment with source params; the originating document references the SVG via `![[file.svg]]`.
4. **Example invocations** — 1–2 per renderer.
5. **When to hand-author instead** — fallback path when topic isn't covered by any renderer.

## 7. `kb_midi.py` — MIDI Export + Playback

### Scope

Pure-stdlib MIDI Format-1 single-track writer using `struct`. Supports:

- Note-on / note-off events with velocity
- Tempo (microseconds-per-quarter)
- Time signature
- Key signature
- Variable-length quantities (VLQ) for delta times
- End-of-track meta event

### Per-Renderer MIDI Generation

The 8 renderers with discrete pitches/durations support `--midi-out`:

| Renderer | MIDI mapping |
|---|---|
| `staff` | Direct: notes → pitches with durations |
| `raga-clock` | Arohana → ascending scale; avarohana → descending |
| `sargam` | Sa = root MIDI note (configurable); pattern → notes |
| `jianpu` | 1–7 + octave dots → MIDI; dashes extend duration |
| `gongche` | Character → MIDI per traditional pitch table |
| `rhythm-grid` | Each track → percussion MIDI channel 10; steps → onsets |
| `clave` | Pattern → percussion onsets on channel 10 |
| `tala` | Sam/khali/tali → percussion onsets with accent variations |

`fretboard` and `chord-box` are positional — they get MIDI only when given an explicit `--strum` or `--arpeggiate` flag. Default: silent (no MIDI).

### Playback Shim

`--play` flag generates MIDI to a temp file and invokes the platform player:

| Platform | Player |
|---|---|
| macOS | `afplay` |
| Linux | `aplay` (with timidity fallback if installed) |
| Windows | `start` |

Best-effort: on missing player, prints `[kb_midi] no system MIDI player found; midi written to <path>` and exits 0. Never blocks generation.

## 8. `archetypes/music/tabs.md`

Thin sub-archetype documenting:

1. **Tab conventions** across fretted instruments. alphaTex (the format `guitar-tabs` produces) supports custom tunings, so banjo (5-string `gDGBD`), ukulele (`GCEA`), bass (`EADG`), mandolin (`GDAE`) all work via the existing `guitar-tabs` command — no code change.
2. **Cross-link rules** tying tabs to theory-primer / song-breakdown documents (every tab references its theory doc; every song-breakdown references its tab).
3. **Selection logic** — when topic suggests tablature ("tab for X", "fingerpicking pattern", "riff for"), the existing `guitar-tabs` command runs; `tabs.md` is consulted for cross-link conventions only.
4. **Future extensibility** — placeholders for cipher-tablature traditions (sargam-tab, jianpu-tab) where alphaTex doesn't fit cleanly.

## 9. Engine Changes — `kb_archetype.py`

### Manifest Schema (`archetypes/music/manifest.json`)

```json
{
  "name": "music",
  "description": "Globally-inclusive music archetype family",
  "domain-indicators": [
    "music", "song", "scale", "chord", "raga", "maqam", "tala",
    "harmony", "melody", "rhythm", "composer", "instrument",
    "mode", "key", "tonality", "tradition", "ensemble", "tab",
    "fretboard", "staff", "notation", "circle of fifths"
  ],
  "sub-archetypes": {
    "diagram": "diagram.md",
    "tabs":    "tabs.md",
    "svg":     "svg.md",
    "document": {
      "default":            "documents/theory-primer.md",
      "theory-primer":      "documents/theory-primer.md",
      "biography":          "documents/biography.md",
      "song-breakdown":     "documents/song-breakdown.md",
      "instrument-profile": "documents/instrument-profile.md",
      "tradition-overview": "documents/tradition-overview.md",
      "history-timeline":   "documents/history-timeline.md",
      "comparative":        "documents/comparative.md"
    }
  },
  "purpose-keywords": {
    "biography":          ["biography", "life of", "profile of"],
    "history-timeline":   ["history of", "evolution of", "timeline"],
    "song-breakdown":     ["analysis of", "breakdown", "anatomy of"],
    "instrument-profile": ["the (sitar|piano|...)", "instrument:"],
    "tradition-overview": ["carnatic music", "hindustani music", "gamelan music"],
    "comparative":        [" vs ", " compared to ", "across traditions"]
  }
}
```

### CLI

```
kb_archetype.py \
  --archetypes-dir <dir> \
  --topic "<topic>" \
  [--output-type diagram|document|svg|tabs]   # default: diagram (back-compat)
  [--purpose-hint "<topic-or-explicit-purpose>"]
```

Output: `<name> <subtype> <absolute-path>` (subtype empty for single-file archetypes).

### Selection Algorithm

1. Build candidate list:
   - Single-file: every `<archetypes-dir>/*.md` excluding `_archetype-template.md`
   - Meta:        every `<archetypes-dir>/*/manifest.json`
2. Score each candidate by domain-indicator hits in `--topic` (existing scoring logic, applied uniformly).
3. Winner = highest score; ties → alphabetical.
4. If winner is single-file → return `<name>  <abs-path>`.
5. If winner is meta:
   1. Look up `sub-archetypes[--output-type]`.
   2. If string → return `<name> <output-type> <abs-path>`.
   3. If dict (e.g., document):
      - Score each `purpose-keywords[purpose]` against `--purpose-hint`.
      - If any keyword matches → return that sub-archetype.
      - Else → return `sub-archetypes.default`.
   4. If `--output-type` missing from manifest → return `sub-archetypes.default` || `no-match`.
6. If no candidates score > 0 → return `no-match`.

### Command File Touches

| Command | Change |
|---|---|
| `commands/diagram.md` | Pass `--output-type diagram`; parse 3-token output |
| `commands/document.md` | **NEW** archetype step: pass `--output-type document --purpose-hint "<topic>"`; read returned template; follow its body structure; fall back to free-form on `no-match` |
| `commands/svg.md` | **NEW** file: pass `--output-type svg`; shell out to `kb_svg.py` with renderer-specific params |
| `commands/guitar-tabs.md` | Optional consult of `tabs.md` for cross-link conventions (deferrable) |

## 10. `validate` Command — Music-Lint Extension

`commands/validate.md` gains a `--lint-music` flag (or auto-detects via vault config when `archetypes/music/` is registered). For each file:

1. Read frontmatter.
2. If `purpose:` matches a music template (theory-primer, biography, etc.):
   - Require `traditions:` field (non-empty list).
   - Each entry must be one of the 11 tradition tags from §4.
3. On violation:
   - Report `<file>:<line> missing/invalid traditions: <details>`.
   - `--fix` adds `traditions: [unmarked]` placeholder rather than guessing.
4. 10 fixture files in `scripts/tests/fixtures/lint_music/` (5 pass, 5 fail) for tests.

## 11. SKILL.md Changes

- Add `svg` to the Usage block, dispatch table, alias list, and allowed-tools.
- Update the trigger phrases in description to include "svg of X", "circle of fifths", "raga clock", "fretboard diagram", "rhythm grid", "neume", "sargam", "jianpu", "tala diagram", etc.
- Bump version to 1.2.0.

## 12. Implementation Roadmap

Each phase is independently shippable. The validation gate at the end of each phase must pass before starting the next.

### Phase 1 — Engine Foundation *(~2 days; low risk)*
- `scripts/kb_archetype.py` — meta detection, manifest parsing, sub-archetype selection, 3-token output.
- `archetypes/music/manifest.json` — placeholder with empty sub-archetypes for testing meta detection.
- `archetypes/music/diagram.md` — full §4 sub-archetype content.
- `commands/diagram.md` — `--output-type` flag, 3-token parse.
- Unit tests: meta detection, scoring, ties, back-compat.
- **Validation gate:** regenerate the existing `software-architecture` sample diagram to confirm zero-regression.

### Phase 2 — Document Templates *(~2 days; medium risk — touches existing `document.md`)*
- All 7 `archetypes/music/documents/*.md` templates.
- `commands/document.md` — NEW archetype step (selects template, falls back to free-form on `no-match`).
- Tests: purpose-hint selection across 20 representative topics.
- **Validation gate:** generate one biography, one theory primer, one comparative essay on real topics; eyeball quality.

### Phase 3a — SVG Generator: Core 7 Renderers *(~3–4 days; high risk)*
- `staff`, `fretboard`, `circle-of-fifths`, `raga-clock`, `maqam-jins`, `gamelan-cipher`, `chord-box`.
- Shared primitives + theme module.
- Golden-master fixtures.
- **Validation gate:** generate one SVG per renderer; visual inspection.

### Phase 3b — SVG Generator: 7 Added Renderers *(~3–4 days; high risk)*
- `neume`, `sargam`, `jianpu`, `gongche`, `rhythm-grid`, `clave`, `tala`.
- `archetypes/music/svg.md` (renderer catalog).
- `commands/svg.md` (new sub-command).
- `SKILL.md` updates.
- **Validation gate:** generate one SVG per renderer; visual inspection; byte-stable golden masters.

### Phase 4 — MIDI Export + Playback *(~2 days; medium risk; new surface)*
- `scripts/kb_midi.py` — pure-stdlib MIDI writer.
- `--midi-out` flag on 8 compatible renderers.
- `--play` cross-platform shim.
- Per-format MIDI golden fixtures.
- **Validation gate:** generate + play MIDI from one of each compatible renderer.

### Phase 5 — `validate` Music-Lint Extension *(~½ day)*
- `commands/validate.md` extension.
- 10 fixture files for tests.
- `--lint-music` flag and `--fix` mode.

### Phase 6 — Tabs Sub-Archetype + Cross-Links *(~½ day)*
- `archetypes/music/tabs.md`.
- `_links.json` integration tests.
- (Optional) `commands/guitar-tabs.md` consult of `tabs.md`.

### Phase 7 — Polish & Integration *(~½ day)*
- `archetypes/music/README.md`.
- `archetypes/music/ICON_REQUESTS.md` wishlist.
- Vault `CLAUDE.md` template guidance (init-time injection if vault opts into music).

## 13. Total Scope Estimate

| Surface | Lines |
|---|---|
| `archetypes/music/**` (manifest, diagram, tabs, svg, 7 docs, README, ICON_REQUESTS) | ~1,500 |
| `scripts/kb_svg.py` (14 renderers) | ~1,400–1,700 |
| `scripts/kb_midi.py` (writer + per-format generation + playback shim) | ~400–600 |
| `scripts/kb_archetype.py` changes | ~+150 |
| `commands/document.md` changes | ~+40 |
| `commands/svg.md` (new) | ~150 |
| `commands/validate.md` changes | ~+80 |
| `SKILL.md` changes | ~+25 |
| Tests (unit + golden SVG + MIDI fixtures + lint fixtures) | ~700 |
| **Total** | **~4,500–5,000 LOC** |

## 14. Testing Strategy

- **Unit tests:** `kb_archetype.py` (meta detection, scoring, sub-archetype selection, ties, no-match fallback).
- **Golden masters:** `kb_svg.py` per-renderer SVG fixtures, byte-comparison after stripping timestamps and UUIDs.
- **MIDI fixtures:** binary-comparison golden files for each of the 8 MIDI-capable renderers.
- **Integration:** phase-level "generate a real piece of music content" smoke tests in a throwaway vault (e.g., generate a Coltrane biography, a Yaman theory primer, a Hijaz fretboard SVG).
- **Manual eyeball:** Phases 2, 3a, 3b require human aesthetic review on representative outputs.
- **Lint fixtures:** 10 frontmatter test files for `--lint-music` (5 pass, 5 fail).

## 15. Risk Register

| Risk | Mitigation |
|---|---|
| 41-icon limit constrains music diagrams | Document repurposed mappings in §4; track wishlist in `ICON_REQUESTS.md`; revisit if app gains a music-icon pack |
| `kb_svg.py` v1 misses an exotic notation | `svg.md` documents the hand-authored fallback path |
| Tradition tagging drift (Western default creep) | `traditions:` is required frontmatter; lint check via `validate --lint-music` |
| Back-compat regression for `software-architecture` | Phase 1 validation gate; explicit unit tests |
| `kb_svg.py` AI-generated parameters are wrong | Each renderer validates inputs; emits clear error + suggested syntax |
| Neume custom glyphs visually finicky | Liber Usualis as canonical reference; ship as-good-as-feasible v1, iterate |
| Gongche needs CJK font on viewer's machine | Embed unicode chars + reference Noto Sans CJK web font; degrades gracefully if absent |
| MIDI binary format edge cases (running status, VLQ) | Write minimal-but-correct subset (Format 1, single track per renderer); golden-file tests |
| `--play` cross-platform fragility | Best-effort only; never blocks generation; clear error message |
| Tala visualization style ambiguity | Default circular; `--style linear` flag for those who prefer it |
| Tradition-tag lint false positives | `--lint-music` is opt-in; `--fix` adds neutral `[unmarked]` rather than guessing |

## 16. Out of Scope for v1

| Item | Reason | Path forward |
|---|---|---|
| App-side icon pack | Different repo (visual editor app) | `ICON_REQUESTS.md` wishlist; PR against that app separately |
| Live audio synthesis (DAW-style) | MIDI playback satisfies "hear it" use case at far lower cost | Could add later via FluidSynth shim if someone needs higher fidelity |
| Notation editing (round-trip parse/edit) | Pure-output design; editing requires a parser per format | Defer until concrete need emerges |
| World-music meta-archetype | Subsumed into `music/` (already globally inclusive) | Closed |

## 17. Open Questions for Implementation Plan

To be resolved during planning:

1. Sargam pattern syntax — uppercase/lowercase for octave (`Sa` vs `sa`), or explicit dot markers?
2. Neume glyph approach — vector-drawn from canonical shapes vs. unicode neume block (`U+1D1xx`)?
3. MIDI tempo defaults per renderer — should the AI specify or should renderers default to 120 BPM?
4. Tala default visualization — circular is the spec default, but should `--style linear` be auto-selected for cycles longer than 12 matras?
5. Vault opt-in mechanism for music — explicit `archetypes: [music]` in vault config, or auto-enable when any music document is created?

These don't block the design; they're decisions for the implementation plan.
