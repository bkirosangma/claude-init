# Command: guitar-tabs

Generate a playable guitar tab on any song, riff, or pattern. Output is a single `.alphatex` file — the text DSL that the knowledge-base app's tab pane renders + plays via `alphaTab`.

**Why alphaTex:** plain text (diff-friendly in the vault), parsed natively by the active rendering engine, hand-editable later, and survives engine swaps because the app's `TabEngine` interface treats this as the canonical source format.

## Usage

```
/knowledge-base guitar-tabs <topic>           # Generate directly from compound intelligence
/knowledge-base guitar-tabs <topic> -i        # Interactive: ask tuning / capo / tempo / style first
/knowledge-base guitar-tabs <topic> --interactive
```

Aliases at parse time: `guitar-tab`, `tabs`, `tab` (the dispatcher rewrites all four to this command).

## Inputs

The dispatcher passes:
- **topic** — everything after the verb, with `-i`/`--interactive` stripped (e.g. `"Hotel California intro fingerpicking"` or `"G major pentatonic warm-up"`)
- **interactive** — boolean (`true` if `-i` / `--interactive` present)
- **vaultRoot** — absolute path to detected vault root (or `null`)
- **vaultConfig** — parsed `.archdesigner/config.json` (or `null`)
- **gatheredContext** — compound-intelligence block from SKILL.md

## Step 1: Parse Arguments

1. **topic** is the song / riff / pattern name. Multi-word allowed.
2. If empty, ask: *"What song, riff, or pattern should I tab out?"*
3. Derive **topic-slug** via the shared script — never compute manually:

   ```bash
   SLUG=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py slug "<topic>")
   if [ -n "<vaultRoot>" ]; then
     SLUG=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py next-slug "$SLUG" "<vaultRoot>/memory/topic-registry.md")
   fi
   ```

## Step 1b: Select Tabs Archetype (optional)

Run the archetype selector to check if a music-specific tabs template applies:

```bash
ARCHETYPE_RESULT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "<topic>" \
  --output-type tabs)
```

Parse the 3-token output: `<name> <subtype> <path>`.

- If `subtype` is `tabs` (music meta-archetype matched): read the file at `<path>` (this is `archetypes/music/tabs.md`) for tradition-specific defaults (tuning, tempo, section names, alphaTex patterns, and quality checklist).
  - Override the generic defaults in Steps 3 and 5 with the tradition-specific values from the archetype.
  - Use the archetype's templates as starting point for section bodies when the topic matches a tradition.
- If output is `no-match` or `subtype` is `-`: skip this step. Use the standard guitar-tabs defaults below.

When the archetype is loaded, also extract the tradition tag (from `--tradition` in manifest indicators) and pass it to SKILL.md context so the SVG renderer uses the matching badge color if a companion SVG is generated.

## Step 2: Suggest Placement

If `vaultRoot` is set, route the file into the most appropriate vault collection. Default suggestion order:

1. `tabs/` — the canonical home for `.alphatex` files. Create with `mkdir -p` if absent.
2. Subfolder by genre or artist when the topic clearly implies one (e.g. `tabs/eagles/hotel-california/`, `tabs/exercises/scales/`).
3. Fallback: `<vaultRoot>/<topic-slug>/`.

In interactive mode, present 2–3 options + an "Other (type path)" escape.

The output path is `<targetFolder>/<topic-slug>.alphatex`.

## Step 3: Interactive Clarifications (only when `interactive = true`)

Ask in this order, one at a time, accept defaults silently:

1. **Tuning** — multiple-choice: standard EADGBE, drop-D DADGBE, drop-C# C#G#C#F#A#D#, open G DGDGBD, custom (free-form).
2. **Capo** — none / fret 1–7. Default: none.
3. **Key** — single-letter + minor/major (e.g. "G major"). Default: infer from context.
4. **Tempo** — BPM. Default: 80 for fingerpicking, 120 for strumming, 100 otherwise.
5. **Time signature** — 4/4 default; offer 3/4, 6/8, 12/8 only if the topic implies a waltz / shuffle / swing feel.
6. **Sections to include** — any subset of: Intro, Verse, Pre-Chorus, Chorus, Bridge, Solo, Outro. Default: Intro + Verse.
7. **Multi-track** — single guitar (default) / two guitars / guitar + bass.

Each answered field becomes an alphaTex header directive (see Step 5).

## Step 4: Gather Context (always)

Use the `gatheredContext` block produced by SKILL.md. Items relevant to this command:

- **Existing tabs in the vault** that share the artist, genre, or pattern → link via wiki-links in the metadata block, don't duplicate the riff.
- **Music-theory documents** the user already has (`pentatonic-scale.md`, `chord-tree-of-fifths.json`) → reference them in the metadata block so the app's link index surfaces backlinks.
- **Past sessions** (claude-mem) where this song or pattern was tabbed before → reuse the tuning + key choices for consistency unless the user overrides.

## Step 5: Compose the alphaTex File

Output one well-structured `.alphatex` file. Required sections in order:

### 5a. Wiki-link metadata block (vault cross-references)

The app's link index (TAB-011, shipped) parses `[[…]]` tokens from a single `// references:` line in alphaTex files (the renderer ignores `//` comments). Use this block to link to related docs / SVGs / diagrams the tab references — only the `// references:` line is indexed; other `//` comments (`// kb-meta`, `// generated-by`, `// generated-at`) are decorative.

```alphatex
// kb-meta
// references: [[major-scale-shapes]] [[picking-pattern.svg]] [[song-history.md]]
// generated-by: knowledge-base/guitar-tabs
// generated-at: <ISO-8601 timestamp>
```

Always include `generated-by` + `generated-at`. `references` line is optional — only emit when at least one wiki-link target exists.

### 5b. Header directives

```alphatex
\title "<topic title-cased>"
\subtitle "<optional descriptor>"
\artist "<artist or 'Exercise' / 'Pattern' / 'Riff'>"
\tempo <bpm>
\key <key>            # e.g. Gmaj, Em, C#min
\time <num>/<den>     # default 4/4
\track "Guitar"
\tuning <s6> <s5> <s4> <s3> <s2> <s1>   # low → high (string 6 = lowest); alphaTex uses scientific pitch e.g. E2 A2 D3 G3 B3 E4
\capo <fret>          # omit if no capo
```

`\tuning` notes go from string 6 (lowest) to string 1 (highest) using scientific pitch (octave digit included).

### 5c. Section bodies

```alphatex
\section "Intro"
.
:8 7.6 8.6 5.6 |
0.5 0.5 7.5 5.5 5.5 |

\section "Verse 1"
.
:16 0.6 3.5 0.4 0.3 |
...
```

The first `.` after a section header signals "music starts here". Bars are pipe-delimited. `:8` / `:16` set the prevailing duration; `<fret>.<string>` places a note. Techniques: `h` hammer, `p` pull, `b` bend, `~` vibrato, `()` ghost, `t` tie, `lr` let-ring.

### 5d. Generation rules

- **Be musically valid.** Frets must be reachable on the chosen tuning (no fret 25 unless the topic is shred). Notes within a chord must share a beat. Bends resolve within the same bar.
- **Keep it short by default.** 8–16 bars per section unless the user asks for the whole song. Long songs are tedious to render and pollute the vault.
- **Prefer common patterns.** Travis picking, alternating bass, blues shuffle, pentatonic licks — pick one that matches the topic and stay consistent.
- **No copyright wholesale.** For known songs, generate a *recognisable transcription of the public-domain or common-knowledge motif*, not a full commercial reproduction. If the topic clearly implies copying a copyrighted full-song transcription, narrow to the iconic riff or chord progression and add a comment: `// This is a study transcription of the iconic motif, not the full arrangement.`
- **Add expression marks** (`mf`, `let ring`, `H`, `P`) where the pattern calls for them.

### 5e. Final file shape

```alphatex
// kb-meta
// references: [[picking-pattern.svg]]
// generated-by: knowledge-base/guitar-tabs
// generated-at: 2026-05-02T18:30:00Z

\title "G Major Pentatonic Warm-up"
\subtitle "Ascending pattern, 4ths"
\artist "Exercise"
\tempo 100
\key Gmaj
\time 4/4
\track "Guitar"
\tuning E2 A2 D3 G3 B3 E4
.
\section "Pattern"
:16 3.6 5.6 2.5 5.5 |
2.4 4.4 0.3 2.3 |
0.2 3.2 0.1 3.1 |
3.1 0.1 3.2 0.2 |
```

## Step 6: Write the File + Register

1. Write the alphaTex content to `<targetFolder>/<topic-slug>.alphatex` (UTF-8, LF line endings).
2. If the vault has a `memory/topic-registry.md`, append the new slug there via the standard registration pattern from `commands/document.md`.
3. If the vault has graphify wired, suggest running `/graphify .` to refresh the structural index — don't run it unprompted; long-running.
4. Print a one-line success summary: `✓ Wrote <relative path> (<bar count> bars, <section count> sections, <bpm> bpm).`

## Step 7: Suggest Cross-References (silent)

After writing, scan `gatheredContext` once more for documents that explain the music theory behind this riff (scale doc, chord tree, technique guide). For each strong candidate that wasn't already linked in the metadata block, **suggest** (don't auto-edit) one cross-reference the user might want to add — printed below the success line:

```
✓ Wrote tabs/exercises/g-pentatonic-warmup.alphatex (4 bars, 1 section, 100 bpm).

  Suggested wiki-links to add (manual): [[g-pentatonic-positions]], [[fingering-guide]]
```

The user adds these by hand or via a follow-up `/kb edit` style flow once the tab pane lands; nothing in this command auto-mutates other files.

## Validation Hook

The app's `TabEngine` is shipped (`features/tab/`, M1 viewer ship-point). Generated `.alphatex` files are validated at render time by the app: it parses via `alphaTab` and surfaces unresolved sections, malformed bars, or out-of-range frets in the tab pane. This skill validates statically by writing well-formed alphaTex per the rules above. Extending `/kb validate <path>` to invoke the engine's parse path for `.alphatex` files is a future enhancement (see `~/.claude/skills/knowledge-base/SKILL.md`).

## Output Conventions Summary

| Aspect | Convention |
|---|---|
| Extension | `.alphatex` |
| Encoding | UTF-8, LF |
| Default folder | `tabs/` (vault root) |
| Header order | `// kb-meta` block → `\title` / `\artist` / etc. directives → sections |
| Comment syntax | `//` (alphaTex line comments) — `%` triggers a parse error |
| Tuning notation | scientific pitch, low-to-high, e.g. `E2 A2 D3 G3 B3 E4` |
| Length | 8–16 bars per section unless overridden |
| Cross-refs | wiki-links in `// references: ...` line; backlinks via app link index |
