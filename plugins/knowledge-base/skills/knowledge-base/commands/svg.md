# Command: svg

Generate a music SVG visualization for any topic using `kb_svg.py`. Selects the appropriate renderer based on the topic and produces a standalone `.svg` file.

## Usage

```
/knowledge-base svg <topic>
```

Examples:
```
/kb svg "C major scale on treble staff"
/kb svg "Raga Yaman clock"
/kb svg "Jins Hijaz on D"
/kb svg "Dm7 chord box"
/kb svg "Slendro gamelan pattern"
/kb svg "Circle of fifths highlighting C G D"
/kb svg "Son clave 3-2"
/kb svg "Teentaal cycle"
```

## Inputs

- **topic** (string, required): The subject of the SVG, passed from the SKILL.md dispatcher.
- **vaultRoot** (string | null): Vault root path if vault detection succeeded.
- **vaultConfig** (object | null): Parsed `.archdesigner/config.json`.
- **gatheredContext** (object): Compound intelligence context assembled by SKILL.md.

---

## Step 1: Parse Arguments and Derive Slug

1. The **topic** string describes what to visualize.
2. Derive a **topic-slug** via script:

```bash
SLUG=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py slug "<topic>")
```

3. If `vaultRoot` is set, check for duplicate slugs:

```bash
SLUG=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py next-slug "$SLUG" "<vaultRoot>/memory/topic-registry.md")
```

---

## Step 2: Suggest Placement

If `vaultRoot` is set:

```bash
PLACEMENT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_suggest_placement.py \
  --topic "$SLUG" \
  --vault-root "<vaultRoot>")
```

Present up to 4 placement options from `suggestions[]`, plus "Vault root" and "Other (type path)".

Set `topicFolder = "<vaultRoot>/<confirmed-path>/$SLUG/"`.

If no vault: `topicFolder = "<cwd>/$SLUG/"`.

Create the folder: `mkdir -p "<topicFolder>"`.

---

## Step 3: Select Renderer

### 3a. Run the archetype selector

```bash
ARCHETYPE_RESULT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "<topic>" \
  --output-type svg)
```

Parse the 3-token output: `<name> <subtype> <path>`.

- If `subtype` is `svg`: read `<path>` (this is `archetypes/music/svg.md`) for the full renderer catalog and flag reference.
- If output is `no-match` or `subtype` is `-`: no specialized music renderer is available; produce a fallback diagram (inform user and offer to use `/kb diagram` instead).

### 3b. Match topic to renderer

Read `archetypes/music/svg.md` (loaded in 3a). Map the topic to one of the 14 renderers using these signals:

| Topic keywords | Renderer |
|---------------|----------|
| staff, clef, treble, bass, scale, melody, notes | `staff` |
| fretboard, neck, string, tab, guitar, bass, uke, mandolin | `fretboard` |
| circle of fifths, fifth, key signature, major minor | `circle-of-fifths` |
| raga, arohana, avaroha, shruti, swara, hindustani, carnatic | `raga-clock` |
| maqam, jins, bayati, hijaz, rast, saba, quarter tone, arabic, turkish | `maqam-jins` |
| gamelan, slendro, pelog, cipher, kepatihan, javanese, balinese | `gamelan-cipher` |
| chord, voicing, fingering, barre, open chord | `chord-box` |
| neume, gregorian, chant, byzantine | `neume` |
| sargam, swara notation, do re mi (indian context) | `sargam` |
| jianpu, numbered notation, chinese folk | `jianpu` |
| gongche, gong che, classical chinese | `gongche` |
| rhythm, beat, groove, polyrhythm, drum | `rhythm-grid` |
| clave, son, rumba, afro-cuban, guaguanco | `clave` |
| tala, tal, teentaal, ektaal, jhaptaal, rupak, keherwa, mridangam | `tala` |

If ambiguous, ask: "Which type of visualization fits best?" and list the relevant options.

### 3c. Map topic to renderer flags

From the topic string, extract values for the renderer's flags. Use these defaults when a value is not mentioned:

- **staff**: `--notes ""` (empty), `--clef treble`, `--time-sig 4/4`
- **fretboard**: `--strings 6`, `--tuning EADGBE`
- **circle-of-fifths**: `--highlight ""`
- **raga-clock**: `--raga ""`, `--shrutis 12`
- **maqam-jins**: `--jins Rast`, `--root D`
- **gamelan-cipher**: `--tuning slendro`, `--pattern ""`
- **chord-box**: `--instrument guitar`, `--chord ""`, `--fingering ""`

Detect the tradition from the topic and pass `--tradition <tag>` when relevant (see tradition tags in svg.md).

---

## Step 4: Generate the SVG

Run `kb_svg.py` with the selected renderer and extracted flags:

```bash
python3 ~/.claude/skills/knowledge-base/scripts/kb_svg.py \
  --type <renderer> \
  [renderer-specific flags] \
  --theme light \
  --title "<topic>" \
  --out "<topicFolder>/$SLUG.svg"
```

Check the exit code. If non-zero, report the error message and ask the user for clarification on the failing flag.

---

## Step 5: Update Vault State

Skip if no vault detected.

### 5a. Update Topic Registry

```bash
mkdir -p "<vaultRoot>/memory"
python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py append-registry \
  --vault-root "<vaultRoot>" \
  --date "<YYYY-MM-DD>" \
  --topic "<topic>" \
  --slug "$SLUG" \
  --doc "<relative-path-from-vault-root>"
```

### 5b. Update graphify (best-effort)

```bash
cd "<vaultRoot>" && graphify . --update 2>/dev/null || true
```

---

## Step 6: Report

```
SVG generated: <topic>
  File:     <absolute-path>
  Renderer: <renderer-name>
  Tradition: <tag or "none">
  Vault:    <vault-name> (or "none — standalone file")
  Registry: <updated | created | skipped (no vault)>

Open <filename>.svg in any SVG viewer or browser to verify the output.
If anything needs adjustment, describe the change and I'll re-render.
```
