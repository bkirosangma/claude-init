---
name: music-diagram
description: Music diagram conventions — globally inclusive across Western, Indian, Arabic, Gamelan, East Asian traditions
domain-indicators:
  - music
  - scale
  - chord
  - raga
  - maqam
  - tala
  - harmony
  - melody
  - rhythm
---

# Sub-Archetype: Music Diagram

Visual conventions for music architecture diagrams in the knowledge-base app. Reuses the JSON schema, anchor system, spacing rules, and condition-node procedures from `software-architecture.md` verbatim; overrides only layer/icon/color/connection-semantic content.

## Mode Selection

When the diagram covers a **single tradition**, layers are **concept-driven** (default).
When the diagram spans **2+ traditions**, layers are **tradition-driven** (one layer per tradition).

The mode is auto-detected by the AI from node frontmatter and topic.

## Layer Conventions — Concept-Driven (default)

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

## Layer Conventions — Tradition-Driven (multi-tradition)

One layer per tradition. Layer background uses the tradition badge color at ~15% opacity (use the lighter `#fX...` variants below; if needed, mix toward `#ffffff` 85%).

## Tradition Badges

The diagram JSON has no native badge field, so tradition appears in each node's `sub` field as a short tag (e.g., `Hindustani`, `Jazz`).

| Tradition | Badge color | Lighter (15% bg) | When used |
|---|---|---|---|
| Western Common-Practice | `#2563eb` | `#dbeafe` | Classical, art music |
| Jazz / Blues | `#7c3aed` | `#ede9fe` | Jazz, blues, gospel, R&B |
| Hindustani | `#dc2626` | `#fee2e2` | North Indian classical |
| Carnatic | `#ea580c` | `#ffedd5` | South Indian classical |
| Arabic Maqam | `#059669` | `#d1fae5` | Arabic, Turkish, Andalusian |
| Persian Dastgah | `#0891b2` | `#cffafe` | Iranian classical |
| Gamelan | `#a16207` | `#fef3c7` | Javanese / Balinese |
| West African | `#16a34a` | `#dcfce7` | Mande, Yoruba, Highlife |
| East Asian | `#9333ea` | `#f3e8ff` | Chinese, Japanese, Korean |
| Latin American | `#e11d48` | `#ffe4e6` | Son, samba, bossa, tango |
| Folk / Traditional | `#475569` | `#f1f5f9` | Catch-all for unmarked folk |

## Icon Mappings (within the 41 registered Lucide icons)

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

App-side icon pack expansion (Music-note, Treble-clef, Drum, Microphone, Wave, Piano-key) is tracked in `ICON_REQUESTS.md`.

## Connection Semantics

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

## Layout Preferences

- **Primary flow:** top-to-bottom for harmonic/temporal; left-to-right for timeline/scale-degree sequences.
- **Density:** moderate (same 70px node gaps and 120–160px layer gaps as `software-architecture`).
- **Emphasis:** the tonic (or its analogue: sa, drone, finalis) anchors the visual spine when present.
- **Symmetric pairs:** parallel-tradition pairs (Aeolian ↔ Bhairavi) mirror around the center axis.

## Schema, Spacing, Anchors, Conditions, Label Positioning

All schema (`LayerDef`, `SerializedNodeData`, `Connection`, `FlowDef`), spacing constants (`NODE_GAP`, `LAYER_GAP`, etc.), anchor points, condition-node placement procedures, and label-positioning rules are inherited verbatim from `archetypes/software-architecture.md`. Apply them unchanged.

## Design Process

Same 10-step process as `software-architecture.md` § "Design Process". Substitute music vocabulary for software vocabulary in step 1 (identify layers).
