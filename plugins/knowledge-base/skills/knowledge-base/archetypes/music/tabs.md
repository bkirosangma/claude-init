---
name: music-tabs
description: Music archetype guidance for guitar-tabs command — style conventions, alphaTex patterns, and tradition-specific layout hints for multi-tradition tablature.
purpose: tabs
---

# Music Tabs Archetype

This file provides style guidance when the `guitar-tabs` command detects a music topic that belongs to the music archetype (via `kb_archetype.py --output-type tabs`). The guidance here overrides generic guitar-tabs defaults.

---

## Tradition-Aware Defaults

When a music topic has a detected tradition, apply the following overrides to alphaTex defaults:

| Tradition | Tuning | Tempo default | Time sig | Capo | Notes |
|-----------|--------|--------------|----------|------|-------|
| `western` (classical) | EADGBE | 72 | 4/4 | none | Use `\instrument 24` (nylon guitar) |
| `jazz` | EADGBE | 130 | 4/4 | none | Include chord voicings above staff |
| `hindustani` | DADGBD (open D) | 60 | varies | none | Use `\instrument 104` (sitar-like) |
| `carnatic` | DADGAD | 80 | varies | none | Emphasize legato slides for gamakas |
| `maqam` | DADGAD | 72 | 4/4 | none | Mark microtonal bends with `b` + annotation |
| `persian` | DADGAD | 60 | 6/8 | none | Dastgah name as section header |
| `gamelan` | EADGBE (retuned) | 100 | 4/4 | none | Use repeated ostinato patterns |
| `west-african` | EADGBE | 120 | 12/8 | none | Cross-rhythm markup with separate tracks |
| `east-asian` | DADGBD | 80 | 4/4 | none | Pentatonic scale emphasis |
| `latin` | EADGBE | 130 | 4/4 | none | Rhythmic strumming with accent marks |
| `folk` | DADGAD | 90 | 3/4 | 2 | Natural harmonics welcome |

---

## alphaTex Structure Conventions

### Header block

Always emit in this order:
```
\title "<Song/Riff Title>"
\artist "<Artist or tradition>"
\album "<Album or source>"
\tempo <bpm>
\tuning <string-list>       // e.g. E4 B3 G3 D3 A2 E2
\instrument <gm-program>    // 25 = acoustic steel, 24 = nylon, 28 = clean electric
```

### Section markers

Use alphaTex section markers to delineate named sections:
```
\section Intro
.
// measures
\section Verse
.
// measures
```

For tradition-based pieces (raga, maqam, dastgah), use the section names:
- Raga: `Alap`, `Jod`, `Jhala`, `Composition`, `Taan`
- Maqam taqsim: `Taqsim`, `Modulation`, `Resolution`
- Carnatic: `Alapana`, `Tanam`, `Pallavi`, `Anupallavi`, `Charanam`

### Note encoding

Standard encoding:
```
// string.fret.duration | string.fret.duration
1.0.4 | 1.2.4 | 1.3.8 1.2.8 | 1.0.2
```

Chord encoding:
```
(1.0 2.0 3.0 4.0 5.2 6.3).4
```

Techniques:
- Bend: `1.7.4{b 100}` (100 = full step, 50 = half step)
- Slide up: `1.5.4{su}`
- Slide down: `1.7.4{sd}`
- Hammer-on: `1.5.8{h} 1.7.8`
- Pull-off: `1.7.8{p} 1.5.8`
- Vibrato: `1.7.4{v}`
- Natural harmonic: `1.12.4{nh}`

---

## Microtonal Notation

For maqam and Persian traditions where quartertone bends are required:

- Mark a quartertone flat with a bend annotation: `1.5.4{b 50}` and add an inline comment `// ~50¢ flat`
- For tivra (sharp) Ma in raga: use fret + `{b 20}` with a comment `// tivra Ma`
- These are approximations; include a note in the file header:
  ```
  // Note: microtonal inflections are approximated. See companion SVG for precise cents.
  ```

---

## Companion SVG Reference

When a music tab topic has an associated SVG (from `/kb svg`), the alphaTex file should include a reference comment near the top:

```
// Visual companion: <topic-slug>.svg
// See [[<topic-slug>.json]] for the structural diagram
```

This enables the vault's link index to discover the relationship.

---

## Template: Raga Alap Fragment

```
\title "Raga <Name> — Alap fragment"
\artist "Hindustani classical"
\tempo 50
\tuning D3 A3 D4 G4 B4 D5
\instrument 104

\section Alap
.
// Sa — rest on Sa
6.0.2 |
// Slow ascent
6.0.4 6.2.4 5.0.4 5.2.4 |
// Pause on Ga
5.4.1 |
```

---

## Template: Maqam Taqsim Opening

```
\title "<Maqam> Taqsim"
\artist "Arabic / Turkish classical"
\tempo 60
\tuning D2 A2 D3 G3 A3 D4
\instrument 24

\section Taqsim
.
// Descent from tonic
6.0.4 6.2.4 6.3.4{b 50} 6.5.4 |
// Jins statement
6.5.2 5.0.4 5.2.4 |
```

---

## Template: Gamelan-Inspired Ostinato

```
\title "<Piece Name> — Gamelan-inspired"
\artist "Javanese gamelan"
\tempo 96
\tuning E4 B3 G3 D3 A2 E2
\instrument 12

\section Ostinato
.
// Slendro pattern: 1 2 3 5 6
1.0.8 1.2.8 1.4.8 1.7.8 | 1.9.8 1.7.8 1.4.8 1.2.8 |
```

---

## Quality Checklist

Before finalising a music-tradition tab:

1. **Header complete**: title, artist, tempo, tuning, instrument all present
2. **Section markers**: at least one `\section` header used
3. **Tradition comment**: `// Tradition: <tag>` in first line after header
4. **Microtonal note**: if quartertones used, disclaimer comment present
5. **Companion SVG reference**: if a matching SVG exists in the vault, `// Visual companion:` line present
6. **No empty measures**: every measure has at least one note or rest
