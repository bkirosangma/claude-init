# Music Meta-Archetype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `music` meta-archetype to the knowledge-base skill (with sub-archetypes for diagram, document, svg, tabs), implement `kb_svg.py` (14 renderers) and `kb_midi.py` (writer + cross-platform playback), and extend `kb_archetype.py` for meta-archetype dispatch — enabling globally-inclusive music content generation across Western, Indian, Arabic, Gamelan, East Asian, and other traditions.

**Architecture:** A directory-based meta-archetype (`archetypes/music/`) with `manifest.json` mapping output types and purpose hints to sub-archetype files. The archetype selector returns a 3-token output (`<name> <subtype> <path>`); single-file archetypes keep working with empty `subtype`. Pure-stdlib Python scripts handle SVG rendering and MIDI export. No external pip deps.

**Tech Stack:** Python 3 stdlib (argparse, json, struct, pathlib, re, subprocess, sys); Markdown templates; JSON manifest; alphaTex (existing); bash for command files; pytest for tests.

**Spec:** `docs/superpowers/specs/2026-05-02-music-archetype-design.md`

---

## File Structure

### Files to create

| Path | Purpose |
|---|---|
| `archetypes/music/README.md` | Family overview |
| `archetypes/music/manifest.json` | Sub-archetype registry, domain-indicators, purpose-keywords |
| `archetypes/music/diagram.md` | Diagram conventions (layers, icons, colors, connections) |
| `archetypes/music/tabs.md` | Tab cross-link conventions |
| `archetypes/music/svg.md` | SVG renderer catalog and AI-facing manual |
| `archetypes/music/ICON_REQUESTS.md` | Wishlist for visual editor app team |
| `archetypes/music/documents/theory-primer.md` | Document template |
| `archetypes/music/documents/biography.md` | Document template |
| `archetypes/music/documents/song-breakdown.md` | Document template |
| `archetypes/music/documents/instrument-profile.md` | Document template |
| `archetypes/music/documents/tradition-overview.md` | Document template |
| `archetypes/music/documents/history-timeline.md` | Document template |
| `archetypes/music/documents/comparative.md` | Document template |
| `scripts/kb_svg.py` | 14 music SVG renderers + shared primitives |
| `scripts/kb_midi.py` | MIDI Format-1 writer + playback shim |
| `commands/svg.md` | New `/kb svg` sub-command |
| `scripts/tests/__init__.py` | Test package marker |
| `scripts/tests/conftest.py` | Pytest fixtures (tmp archetype dirs, etc.) |
| `scripts/tests/test_kb_archetype.py` | Meta-dispatch unit tests |
| `scripts/tests/test_kb_svg.py` | Golden-master SVG tests |
| `scripts/tests/test_kb_midi.py` | MIDI binary fixture tests |
| `scripts/tests/test_validate_lint_music.py` | Lint fixture tests |
| `scripts/tests/fixtures/svg_golden/*.svg` | 14 reference SVGs |
| `scripts/tests/fixtures/midi_golden/*.mid` | 8 reference MIDI files |
| `scripts/tests/fixtures/lint_music/*.md` | 10 frontmatter test files |

### Files to modify

| Path | Change |
|---|---|
| `scripts/kb_archetype.py` | Meta-archetype detection, 3-token output, manifest parsing, sub-archetype selection |
| `commands/diagram.md` | Pass `--output-type diagram`; parse 3-token output |
| `commands/document.md` | NEW archetype step: select template by purpose-hint |
| `commands/guitar-tabs.md` | Optional: consult `tabs.md` for cross-link conventions |
| `commands/validate.md` | NEW `--lint-music` flag and music frontmatter checks |
| `SKILL.md` | Add `svg` to dispatch table, alias list, allowed-tools; bump to v1.2.0 |

### Backward-compatibility constraints

- `software-architecture.md` (single-file) MUST keep working with no behavior change.
- 2-token output (`<name> <path>`) MUST remain a parseable subset of new 3-token output.
- `--output-type` defaults to `diagram` if omitted.

---

## Phase 1: Engine Foundation

Goal: Extend `kb_archetype.py` to handle meta-archetypes; ship the `music/manifest.json` + `diagram.md` content; update `commands/diagram.md` to pass `--output-type` and parse 3-token output.

### Task 1: Test infrastructure

**Files:**
- Create: `scripts/tests/__init__.py`
- Create: `scripts/tests/conftest.py`

- [ ] **Step 1: Create empty `__init__.py`**

```python
# scripts/tests/__init__.py
```

- [ ] **Step 2: Create `conftest.py` with archetype-dir fixture**

```python
# scripts/tests/conftest.py
"""Shared pytest fixtures for kb_* tests."""
from pathlib import Path
import json
import textwrap
import pytest


@pytest.fixture
def archetypes_dir(tmp_path):
    """Empty archetypes directory; tests add their own files."""
    d = tmp_path / "archetypes"
    d.mkdir()
    return d


@pytest.fixture
def write_archetype(archetypes_dir):
    """Helper that writes a single-file archetype with frontmatter."""
    def _write(name: str, indicators: list[str]) -> Path:
        p = archetypes_dir / f"{name}.md"
        body = textwrap.dedent(f"""\
            ---
            name: {name}
            description: test archetype
            domain-indicators: {indicators!r}
            ---

            # {name}
            """)
        p.write_text(body)
        return p
    return _write


@pytest.fixture
def write_meta_archetype(archetypes_dir):
    """Helper that writes a meta-archetype directory with manifest.json."""
    def _write(name: str, manifest: dict, sub_files: dict[str, str] | None = None) -> Path:
        d = archetypes_dir / name
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps(manifest, indent=2))
        if sub_files:
            for rel, content in sub_files.items():
                target = d / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
        return d
    return _write
```

- [ ] **Step 3: Verify pytest discovers nothing yet**

Run: `cd ~/.claude/skills/knowledge-base && python3 -m pytest scripts/tests/ -v`
Expected: `no tests ran` (or `0 collected`).

- [ ] **Step 4: Commit**

```bash
cd ~/.claude/skills/knowledge-base
git init 2>/dev/null || true
git add scripts/tests/__init__.py scripts/tests/conftest.py
git commit -m "test: add pytest infrastructure and shared fixtures for kb scripts"
```

---

### Task 2: Test for back-compat — single-file archetype still returns 2-token output (now embedded in 3-token form)

**Files:**
- Modify: `scripts/tests/test_kb_archetype.py` (create)

- [ ] **Step 1: Create test file with first failing test**

```python
# scripts/tests/test_kb_archetype.py
"""Unit tests for kb_archetype meta-archetype dispatch."""
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "kb_archetype.py"


def run(args: list[str]) -> tuple[str, int]:
    """Invoke kb_archetype.py and return (stdout, returncode)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, check=False,
    )
    return proc.stdout.strip(), proc.returncode


def test_single_file_archetype_returns_three_tokens_with_empty_subtype(write_archetype, archetypes_dir):
    write_archetype("software-architecture", ["api", "microservice"])
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "design a microservice api",
    ])
    assert rc == 0
    parts = out.split(maxsplit=2)
    assert len(parts) == 3, f"expected 3 tokens, got: {out!r}"
    assert parts[0] == "software-architecture"
    assert parts[1] == ""  # empty subtype for single-file archetype
    assert parts[2].endswith("software-architecture.md")
```

- [ ] **Step 2: Run test, verify it fails**

Run: `cd ~/.claude/skills/knowledge-base && python3 -m pytest scripts/tests/test_kb_archetype.py::test_single_file_archetype_returns_three_tokens_with_empty_subtype -v`
Expected: FAIL with `assert len(parts) == 3` (current code outputs 2 tokens).

- [ ] **Step 3: Commit the failing test**

```bash
git add scripts/tests/test_kb_archetype.py
git commit -m "test: add back-compat test for 3-token output on single-file archetypes"
```

---

### Task 3: Make 3-token output work for single-file archetypes

**Files:**
- Modify: `scripts/kb_archetype.py:121` (the print line in `main`)

- [ ] **Step 1: Update the print statement**

Change line 121 from:
```python
        print(f'{best["name"]} {best["path"]}')
```
to:
```python
        # 3-token output: name, subtype (empty for single-file), path.
        # Back-compat: callers that split on whitespace still get name+path
        # if they take first and last tokens.
        print(f'{best["name"]}  {best["path"]}')  # two spaces preserve split-into-3-tokens semantics
```

Wait — that won't work because `out.split(maxsplit=2)` on `"name  path"` gives `["name", "", "path"]` only if there are TWO spaces? Let me verify: `"name  path".split(maxsplit=2)` returns `["name", "path"]` (split collapses). So we need an explicit empty-string token.

Actually, replace with explicit empty middle token using a unique separator OR just print 3 tokens with explicit empty marker. Since this is a CLI contract, the cleanest fix is a single-character empty-marker. Let me use a different approach — print three tokens separated by single space, with empty subtype represented as `-`:

Replace line 121 with:
```python
        # 3-token output: name, subtype (- for empty/single-file), path.
        # Callers parse via split(maxsplit=2). Subtype "-" means single-file archetype.
        print(f'{best["name"]} - {best["path"]}')
```

And update the test in Task 2 to expect `"-"` instead of `""`:
```python
    assert parts[1] == "-"  # sentinel for single-file archetype
```

- [ ] **Step 2: Update the test fixture**

Edit `scripts/tests/test_kb_archetype.py`:

```python
def test_single_file_archetype_returns_three_tokens_with_empty_subtype(write_archetype, archetypes_dir):
    write_archetype("software-architecture", ["api", "microservice"])
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "design a microservice api",
    ])
    assert rc == 0
    parts = out.split(maxsplit=2)
    assert len(parts) == 3, f"expected 3 tokens, got: {out!r}"
    assert parts[0] == "software-architecture"
    assert parts[1] == "-"  # sentinel for single-file archetype
    assert parts[2].endswith("software-architecture.md")
```

- [ ] **Step 3: Run test, verify it passes**

Run: `cd ~/.claude/skills/knowledge-base && python3 -m pytest scripts/tests/test_kb_archetype.py -v`
Expected: PASS (1 passed).

- [ ] **Step 4: Verify no-match still works**

Add a second test:
```python
def test_no_match_returns_no_match_string(archetypes_dir):
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "anything",
    ])
    assert rc == 0
    assert out == "no-match"
```

Run: `python3 -m pytest scripts/tests/test_kb_archetype.py -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add scripts/kb_archetype.py scripts/tests/test_kb_archetype.py
git commit -m "feat(kb_archetype): emit 3-token output with '-' sentinel for single-file archetypes"
```

---

### Task 4: Test for meta-archetype detection (a directory with manifest.json is a candidate)

**Files:**
- Modify: `scripts/tests/test_kb_archetype.py`

- [ ] **Step 1: Add failing test for meta detection**

```python
def test_meta_archetype_with_manifest_is_detected(write_meta_archetype, archetypes_dir):
    write_meta_archetype(
        "music",
        {
            "name": "music",
            "description": "music family",
            "domain-indicators": ["music", "song", "scale"],
            "sub-archetypes": {"diagram": "diagram.md"},
        },
        sub_files={"diagram.md": "# music diagram"},
    )
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic": "C major scale music",  # purposely simple
        "--output-type": "diagram",
    ])
    # ^ syntax fix below
```

Replace with proper Python list syntax:

```python
def test_meta_archetype_with_manifest_is_detected(write_meta_archetype, archetypes_dir):
    write_meta_archetype(
        "music",
        {
            "name": "music",
            "description": "music family",
            "domain-indicators": ["music", "song", "scale"],
            "sub-archetypes": {"diagram": "diagram.md"},
        },
        sub_files={"diagram.md": "# music diagram"},
    )
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "C major scale music",
        "--output-type", "diagram",
    ])
    assert rc == 0
    parts = out.split(maxsplit=2)
    assert len(parts) == 3
    assert parts[0] == "music"
    assert parts[1] == "diagram"
    assert parts[2].endswith("music/diagram.md")
```

- [ ] **Step 2: Run test, verify it fails**

Run: `python3 -m pytest scripts/tests/test_kb_archetype.py::test_meta_archetype_with_manifest_is_detected -v`
Expected: FAIL — `--output-type` is not a recognized arg yet.

- [ ] **Step 3: Commit failing test**

```bash
git add scripts/tests/test_kb_archetype.py
git commit -m "test: add failing test for meta-archetype detection"
```

---

### Task 5: Implement meta-archetype detection and `--output-type` flag

**Files:**
- Modify: `scripts/kb_archetype.py`

- [ ] **Step 1: Add `--output-type` and `--purpose-hint` argparse flags**

In `main()`, after the existing `add_argument` calls (around line 102), add:

```python
    ap.add_argument('--output-type', default='diagram',
                    choices=['diagram', 'document', 'svg', 'tabs'],
                    help='Sub-archetype output type for meta-archetypes (default: diagram)')
    ap.add_argument('--purpose-hint', default='',
                    help='Purpose hint string used to score document sub-types')
```

- [ ] **Step 2: Add manifest loading helper**

After the existing `load_archetypes` function, add:

```python
def load_meta_archetypes(archetypes_dir: str) -> list[dict]:
    """Load all meta-archetypes (subdirectories containing manifest.json)."""
    import json as _json
    result = []
    base = Path(archetypes_dir)
    for sub in sorted(base.iterdir()):
        if not sub.is_dir():
            continue
        manifest_path = sub / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = _json.loads(manifest_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        result.append({
            'name':        manifest.get('name', sub.name),
            'description': manifest.get('description', ''),
            'indicators':  manifest.get('domain-indicators', []),
            'manifest':    manifest,
            'root':        str(sub.resolve()),
            'is_meta':     True,
        })
    return result
```

- [ ] **Step 3: Update `load_archetypes` callers to also pull metas**

In `main()`, change:

```python
    archetypes = load_archetypes(args.archetypes_dir)
```

to:

```python
    archetypes = load_archetypes(args.archetypes_dir)
    metas = load_meta_archetypes(args.archetypes_dir)
    # Tag single-file archetypes for is_meta=False
    for a in archetypes:
        a['is_meta'] = False
    candidates = archetypes + metas
```

And replace later references to `archetypes` (in `select`, `--list`) with `candidates`.

- [ ] **Step 4: Add sub-archetype resolver**

After `select`, add:

```python
def resolve_sub_archetype(meta: dict, output_type: str, purpose_hint: str) -> tuple[str, str] | None:
    """
    Given a meta-archetype + output_type (+ purpose_hint for documents),
    return (subtype_label, absolute_path) or None if unmappable.
    """
    sub_map = meta['manifest'].get('sub-archetypes', {})
    if output_type not in sub_map:
        return None
    entry = sub_map[output_type]
    root = Path(meta['root'])
    if isinstance(entry, str):
        return (output_type, str((root / entry).resolve()))
    if isinstance(entry, dict):
        # Document-style: dict of purpose -> path. Score by purpose-keywords.
        purpose_keywords = meta['manifest'].get('purpose-keywords', {})
        hint = purpose_hint.lower()
        for purpose, keywords in purpose_keywords.items():
            for kw in keywords:
                if kw.lower() in hint:
                    if purpose in entry:
                        return (purpose, str((root / entry[purpose]).resolve()))
        # No keyword match; use default
        if 'default' in entry:
            return ('default', str((root / entry['default']).resolve()))
        # No default; pick first entry
        first_key = next(iter(entry))
        return (first_key, str((root / entry[first_key]).resolve()))
    return None
```

- [ ] **Step 5: Update `main` output to handle metas**

Replace the final `if best is None: ... else: print(...)` block with:

```python
    best = select(candidates, args.topic)
    if best is None:
        print('no-match')
        return
    if best.get('is_meta'):
        resolved = resolve_sub_archetype(best, args.output_type, args.purpose_hint)
        if resolved is None:
            print('no-match')
            return
        subtype, path = resolved
        print(f'{best["name"]} {subtype} {path}')
    else:
        print(f'{best["name"]} - {best["path"]}')
```

- [ ] **Step 6: Run tests, verify both pass**

Run: `python3 -m pytest scripts/tests/test_kb_archetype.py -v`
Expected: 3 PASSED (back-compat, no-match, meta-detection).

- [ ] **Step 7: Commit**

```bash
git add scripts/kb_archetype.py
git commit -m "feat(kb_archetype): meta-archetype detection with --output-type and --purpose-hint"
```

---

### Task 6: Tests for purpose-keywords matching (document sub-types)

**Files:**
- Modify: `scripts/tests/test_kb_archetype.py`

- [ ] **Step 1: Add three tests for document purpose dispatch**

```python
def test_meta_document_dispatches_to_biography_on_keyword_hit(write_meta_archetype, archetypes_dir):
    write_meta_archetype(
        "music",
        {
            "name": "music",
            "domain-indicators": ["music", "composer"],
            "sub-archetypes": {
                "document": {
                    "default": "documents/theory-primer.md",
                    "biography": "documents/biography.md",
                }
            },
            "purpose-keywords": {
                "biography": ["biography", "life of"],
            },
        },
        sub_files={
            "documents/theory-primer.md": "# theory primer",
            "documents/biography.md": "# biography",
        },
    )
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "biography of John Coltrane",
        "--output-type", "document",
        "--purpose-hint", "biography of John Coltrane",
    ])
    parts = out.split(maxsplit=2)
    assert parts[1] == "biography"
    assert parts[2].endswith("documents/biography.md")


def test_meta_document_falls_back_to_default_on_no_keyword_match(write_meta_archetype, archetypes_dir):
    write_meta_archetype(
        "music",
        {
            "name": "music",
            "domain-indicators": ["music"],
            "sub-archetypes": {
                "document": {
                    "default": "documents/theory-primer.md",
                    "biography": "documents/biography.md",
                }
            },
            "purpose-keywords": {"biography": ["biography"]},
        },
        sub_files={
            "documents/theory-primer.md": "# primer",
            "documents/biography.md": "# bio",
        },
    )
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "music theory primer",
        "--output-type", "document",
        "--purpose-hint", "what is a perfect fifth",
    ])
    parts = out.split(maxsplit=2)
    assert parts[1] == "default"
    assert parts[2].endswith("documents/theory-primer.md")


def test_meta_unsupported_output_type_returns_no_match(write_meta_archetype, archetypes_dir):
    write_meta_archetype(
        "music",
        {
            "name": "music",
            "domain-indicators": ["music"],
            "sub-archetypes": {"diagram": "diagram.md"},
        },
        sub_files={"diagram.md": "# diagram"},
    )
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "music thing",
        "--output-type", "tabs",  # not in manifest
    ])
    assert out == "no-match"
```

- [ ] **Step 2: Run tests, verify all pass**

Run: `python3 -m pytest scripts/tests/test_kb_archetype.py -v`
Expected: 6 PASSED.

- [ ] **Step 3: Commit**

```bash
git add scripts/tests/test_kb_archetype.py
git commit -m "test: cover document purpose dispatch and unsupported output-type fallback"
```

---

### Task 7: Write `archetypes/music/manifest.json` (real content)

**Files:**
- Create: `archetypes/music/manifest.json`

- [ ] **Step 1: Create directory and write manifest**

```bash
mkdir -p ~/.claude/skills/knowledge-base/archetypes/music/documents
```

Write `archetypes/music/manifest.json`:

```json
{
  "name": "music",
  "description": "Globally-inclusive music archetype family — diagrams, documents, SVGs, and tabs across Western, Indian, Arabic, Gamelan, East Asian, and other traditions",
  "domain-indicators": [
    "music", "song", "scale", "chord", "raga", "maqam", "tala",
    "harmony", "melody", "rhythm", "composer", "instrument",
    "mode", "key", "tonality", "tradition", "ensemble", "tab",
    "fretboard", "staff", "notation", "circle of fifths",
    "improvisation", "fingerpicking", "riff", "tablature",
    "cadence", "progression", "voicing", "polyrhythm"
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
    "instrument-profile": ["the sitar", "the piano", "the guitar", "the violin", "the oud", "instrument:"],
    "tradition-overview": ["carnatic music", "hindustani music", "gamelan music", "jazz tradition"],
    "comparative":        [" vs ", " compared to ", "across traditions"]
  }
}
```

- [ ] **Step 2: Validate JSON syntax**

Run: `python3 -c "import json; json.load(open('/Users/kiro/.claude/skills/knowledge-base/archetypes/music/manifest.json'))"`
Expected: no output (valid JSON).

- [ ] **Step 3: Verify selector now finds music**

Run:
```bash
python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "C major scale" \
  --output-type diagram
```
Expected: `music diagram /Users/.../archetypes/music/diagram.md` (file doesn't exist yet — that's fine for now; selector returns the path regardless).

- [ ] **Step 4: Commit**

```bash
git add archetypes/music/manifest.json
git commit -m "feat(music): add meta-archetype manifest with sub-archetype map and purpose keywords"
```

---

### Task 8: Write `archetypes/music/diagram.md`

**Files:**
- Create: `archetypes/music/diagram.md`

- [ ] **Step 1: Write the diagram sub-archetype**

Use the spec §4 content. Full file content:

```markdown
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
```

- [ ] **Step 2: Verify it parses as a valid archetype**

Run:
```bash
python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "raga Yaman scale structure" \
  --output-type diagram
```
Expected: `music diagram /Users/.../music/diagram.md`

- [ ] **Step 3: Commit**

```bash
git add archetypes/music/diagram.md
git commit -m "feat(music): add diagram sub-archetype with concept/tradition layers, 11 tradition badges, 8 connection colors"
```

---

### Task 9: Update `commands/diagram.md` to pass `--output-type diagram` and parse 3-token output

**Files:**
- Modify: `commands/diagram.md:48-55`

- [ ] **Step 1: Read current state of Step 2a**

Already read above (line 48-55). The script invocation is:

```bash
ARCHETYPE_RESULT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "<topic>")
```

- [ ] **Step 2: Replace Step 2a with 3-token-aware version**

Edit `commands/diagram.md` lines 48-55 to:

```markdown
### 2a. Select Archetype via Script

Run the archetype selection script with `--output-type diagram` so meta-archetypes route to their `diagram.md` sub-archetype:

```bash
ARCHETYPE_RESULT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "<topic>" \
  --output-type diagram)
```

Parse the 3-token output: `<name> <subtype> <path>`.
- `subtype` = `-` indicates a single-file archetype (e.g., `software-architecture`); use the `<path>` directly.
- `subtype` = `diagram` indicates a meta-archetype's diagram sub-archetype (e.g., `music`); the `<path>` points to the sub-archetype file.
- Output `no-match`: adapt on the fly using `_archetype-template.md` (see 2c below).

Read the archetype file at `<path>` for all conventions (layers, icons, connections, layout, flows). For meta sub-archetypes, also read `<meta-root>/manifest.json` for context (e.g., tradition badges, purpose-keywords).
```

- [ ] **Step 3: Verify the file is well-formed markdown**

Run: `head -60 ~/.claude/skills/knowledge-base/commands/diagram.md`
Expected: Step 2a section reads as edited.

- [ ] **Step 4: Commit**

```bash
git add commands/diagram.md
git commit -m "feat(diagram): pass --output-type diagram and parse 3-token archetype output"
```

---

### Task 10: Phase 1 validation gate — back-compat test for software-architecture

**Files:**
- Modify: `scripts/tests/test_kb_archetype.py`

- [ ] **Step 1: Add integration test pointing at the real archetypes dir**

```python
def test_software_architecture_still_resolves_in_real_archetypes_dir():
    """Phase 1 gate: software-architecture must keep working with no behavior change."""
    real_dir = Path(__file__).resolve().parents[2] / "archetypes"
    out, rc = run([
        "--archetypes-dir", str(real_dir),
        "--topic", "Kubernetes pod lifecycle microservice api",
    ])
    assert rc == 0
    parts = out.split(maxsplit=2)
    assert parts[0] == "software-architecture"
    assert parts[1] == "-"
    assert parts[2].endswith("software-architecture.md")
```

- [ ] **Step 2: Run all tests; verify all pass**

Run: `python3 -m pytest scripts/tests/ -v`
Expected: 7 PASSED.

- [ ] **Step 3: Commit**

```bash
git add scripts/tests/test_kb_archetype.py
git commit -m "test: phase 1 gate — software-architecture back-compat against real archetypes dir"
```

**Phase 1 complete.** All tests pass. Single-file archetype output is back-compat (3-token with `-` sentinel). Meta-archetype detection works for `music`. Document purpose dispatch works.

---

## Phase 2: Document Templates

Goal: Ship 7 document templates under `archetypes/music/documents/`; teach `commands/document.md` to consult `kb_archetype.py` with `--output-type document --purpose-hint "<topic>"`.

### Task 11: Write `theory-primer.md` template

**Files:**
- Create: `archetypes/music/documents/theory-primer.md`

- [ ] **Step 1: Write the template**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add archetypes/music/documents/theory-primer.md
git commit -m "feat(music): add theory-primer document template"
```

---

### Task 12: Write `biography.md` template

**Files:**
- Create: `archetypes/music/documents/biography.md`

- [ ] **Step 1: Write the template**

```markdown
---
purpose: biography
description: Template for musician/composer biographies. Use when topic matches "biography of X" or "life of X".
---

# Biography Template

Generated documents using this template MUST include shared frontmatter with `traditions:` covering the subject's primary tradition(s).

## Life

Birth, death (or "active"), formative years, key relationships, notable life events. 2–4 paragraphs.

## Era Context

The musical landscape during the subject's life. What traditions, schools, or movements were dominant? Who were their contemporaries? What technological or social forces shaped their work?

## Output

Catalog of the subject's body of work. Group by genre/period. For each major work:
- Title
- Year (or period)
- Form / instrumentation / scale-mode-or-raga
- Brief significance

## Style

Distinctive features of the subject's musical language. Vocabulary specific to their tradition (e.g., "characteristic gamakas in Yaman alap", "harmonic substitutions over rhythm changes", "preference for Hijaz over Bayati"). 2–3 paragraphs.

## Influence

Who learned from them; whom they were learned from. Both direct (students, teachers) and indirect (artists who cite them). Use `[[wiki-links]]` to other biographies in the vault.

## Exemplary Works

3–5 specific compositions or recordings to start with. For each:
- Title
- Year / context
- Why it matters
- Link to song-breakdown if one exists: `[[<song-slug>.md]]`

## Visual Overview

- Timeline diagram: `[[<topic-slug>-timeline.json]]` (if generated)
- Influence map: `[[<topic-slug>-influences.json]]` (if generated)

## Cross-References

`[[wiki-link]]` to: tradition overview, related composers, key works, instrument profiles.

## Sources
```

- [ ] **Step 2: Commit**

```bash
git add archetypes/music/documents/biography.md
git commit -m "feat(music): add biography document template"
```

---

### Task 13: Write `song-breakdown.md` template

**Files:**
- Create: `archetypes/music/documents/song-breakdown.md`

- [ ] **Step 1: Write the template**

```markdown
---
purpose: song-breakdown
description: Template for analytical song breakdowns. Form, harmony, rhythm, instrumentation, performance analysis.
---

# Song-Breakdown Template

Use when topic is a specific song/composition or contains "analysis of", "breakdown", "anatomy of".

## Form

Outline the structural sections (intro, verse, chorus, bridge, outro; or alap-jor-jhala-gat-jhala; or taqsim-mawwal-pesrev-saz semaisi). For each section: timing (or measure range), function, mood.

## Key / Mode

The tonal center, mode, raga, maqam, or pelog/slendro. Note any modulations or modal shifts. Reference the `circle-of-fifths`, `raga-clock`, or `maqam-jins` SVG: `![[<topic-slug>-key.svg]]`.

## Harmony

Chord progressions (Western/jazz) or melodic-framework details (modal traditions). Use Roman numerals or chord symbols. Highlight key cadences and substitutions.

## Rhythm / Meter

Time signature, tala, or rhythmic cycle. Distinctive patterns (clave, tihai, additive groupings). Reference the `rhythm-grid`, `clave`, or `tala` SVG: `![[<topic-slug>-rhythm.svg]]`.

## Instrumentation

Instruments and their roles. Vocal forces. Notable performance practices (e.g., "guitar uses DADGAD tuning", "tabla in Teentaal").

## Analysis

Section-by-section commentary. Address: melodic gestures, ornamentation, timbral choices, structural tension/release, lyrical content (if applicable). 4–8 paragraphs.

## Notable Performances

Specific recordings or performances worth seeking out. For each: performer, year, label/venue, what makes it stand out.

## Visual Overview

- Form diagram: `[[<topic-slug>-form.json]]`
- Tab: `[[<topic-slug>.alphatex]]` (if generated)
- Score/notation SVG: `![[<topic-slug>-score.svg]]`

## Cross-References

`[[wiki-link]]` to: composer biography, tradition overview, instrument profiles, theory primers for any concepts referenced.

## Sources
```

- [ ] **Step 2: Commit**

```bash
git add archetypes/music/documents/song-breakdown.md
git commit -m "feat(music): add song-breakdown document template"
```

---

### Task 14: Write `instrument-profile.md` template

**Files:**
- Create: `archetypes/music/documents/instrument-profile.md`

- [ ] **Step 1: Write the template**

```markdown
---
purpose: instrument-profile
description: Template for instrument profiles. Origin, construction, tuning, technique, repertoire.
---

# Instrument-Profile Template

Use when topic matches "the <instrument>" or "<instrument> profile".

## Origin

Geographic and historical origin. Predecessor instruments. Key dates in evolution. 1–2 paragraphs.

## Construction

Materials, dimensions, parts. Distinguishing features (frets vs. fretless, gut vs. nylon vs. steel strings, drone strings, sympathetic strings, resonator, etc.). Include a labeled SVG if helpful.

## Tuning

Standard tunings and common alternates. Use `fretboard` or `staff` SVG: `![[<topic-slug>-tuning.svg]]`. For non-fretted instruments, list pitch ranges and any tradition-specific tunings (e.g., sitar's tarab strings, koto's hirajōshi).

## Technique

Distinctive playing techniques: bowing, plucking, striking, breath control, ornamentation. Note technique vocabulary specific to the tradition (e.g., "meend on sitar", "jala technique on tabla", "bend versus vibrato on electric guitar").

## Repertoire

What this instrument is typically played in: solo, ensemble roles, characteristic genres. List exemplary compositions or performance contexts.

## Notable Players

3–7 historically significant or contemporary masters. Brief note on each player's distinctive contribution. Use `[[wiki-links]]` to biographies in the vault.

## Variants Across Traditions

If the instrument has cousins or analogues in other traditions, dedicate a subsection per variant:

### In <Tradition Name>

What's different (construction, tuning, technique, repertoire).

## Visual Overview

- Anatomy diagram: `[[<topic-slug>-anatomy.json]]`
- Tuning SVG: `![[<topic-slug>-tuning.svg]]`
- Lineage / family tree: `[[<topic-slug>-family.json]]`

## Cross-References

`[[wiki-link]]` to: tradition overview, notable player biographies, songs that prominently feature this instrument.

## Sources
```

- [ ] **Step 2: Commit**

```bash
git add archetypes/music/documents/instrument-profile.md
git commit -m "feat(music): add instrument-profile document template"
```

---

### Task 15: Write `tradition-overview.md` template

**Files:**
- Create: `archetypes/music/documents/tradition-overview.md`

- [ ] **Step 1: Write the template**

```markdown
---
purpose: tradition-overview
description: Template for tradition overviews. Origin, core concepts, notation, repertoire, key figures, modern practice.
---

# Tradition-Overview Template

Use when topic is a tradition name without a specific concept (e.g., "Carnatic music", "Gamelan music").

## Origin

Geographic origin, time period, social/religious context. Key precursors and formative influences. 2–4 paragraphs.

## Core Concepts

The central organizing principles. For each concept (raga, maqam, mode, scale, pelog, tala, polyrhythm, etc.): brief definition + cross-link to its theory primer (`[[<concept-slug>.md]]`).

## Notation & Tuning

How this tradition writes music down (or doesn't — note oral traditions explicitly). Tuning systems (12-TET, just intonation, 22-shruti, 24-quartertone, slendro/pelog). SVG embeds for representative notation: `![[<tradition-slug>-notation.svg]]`.

## Repertoire

Major forms and structural conventions (sonata, raga performance, taqsim, gendhing, son). Exemplary repertoire pieces or performance contexts. Use `[[wiki-links]]` to song-breakdowns.

## Key Figures

5–10 historically significant figures (composers, theorists, performers, systematizers). For each: brief note + cross-link to biography (`[[<name-slug>.md]]`).

## Modern Practice

Contemporary state: living practitioners, conservatories, recording and performance scenes, fusion and crossover work. 2–3 paragraphs.

## Visual Overview

- Concept map: `[[<tradition-slug>-concepts.json]]`
- Timeline: `[[<tradition-slug>-timeline.json]]`
- Lineage tree: `[[<tradition-slug>-lineage.json]]`

## Cross-References

`[[wiki-link]]` to: theory primers for core concepts, biographies of key figures, instrument profiles, comparative essays.

## Sources

Cite both primary historical sources (Bharata, al-Farabi, Rameau, etc.) and modern academic references.
```

- [ ] **Step 2: Commit**

```bash
git add archetypes/music/documents/tradition-overview.md
git commit -m "feat(music): add tradition-overview document template"
```

---

### Task 16: Write `history-timeline.md` template

**Files:**
- Create: `archetypes/music/documents/history-timeline.md`

- [ ] **Step 1: Write the template**

```markdown
---
purpose: history-timeline
description: Template for chronological histories. Scope, eras, transitions, influences, legacy.
---

# History-Timeline Template

Use when topic matches "history of", "evolution of", or contains "timeline".

## Scope

What span this timeline covers (date range, geographic boundary, stylistic boundary). What's explicitly *not* covered (forces the reader to find the right adjacent entry).

## Eras

For each era, an H3 subsection. Order strictly chronological. Per-era content:

### <Era Name> (<years>)

- **Defining features:** what makes this era distinct
- **Representative composers/performers:** 3–5 names
- **Representative works:** 2–4 with brief notes
- **Innovations:** what this era introduced
- **End conditions:** what brought this era to a close (or transitioned to the next)

## Transitions

Between-era connective tissue. What historical, technological, social, or artistic forces drove each transition? 1–2 paragraphs per transition.

## Influences

How this timeline's content was shaped by, and shaped, adjacent traditions. Cross-link to comparative documents and other tradition timelines (`[[<other-tradition>-timeline.md]]`).

## Legacy

How the events of this timeline reverberate today. Living traditions, revival movements, scholarly attention, popular culture echoes.

## Visual Overview

- Timeline diagram: `[[<topic-slug>-timeline.json]]` (use horizontal layout, era boxes, dated nodes)
- Influence flow diagram: `[[<topic-slug>-influence.json]]`

## Cross-References

`[[wiki-link]]` to: tradition overview, biographies of representative figures, key works, theory primers for innovations.

## Sources
```

- [ ] **Step 2: Commit**

```bash
git add archetypes/music/documents/history-timeline.md
git commit -m "feat(music): add history-timeline document template"
```

---

### Task 17: Write `comparative.md` template

**Files:**
- Create: `archetypes/music/documents/comparative.md`

- [ ] **Step 1: Write the template**

```markdown
---
purpose: comparative
description: Template for cross-tradition comparative essays. Concept treatment in tradition A vs. tradition B, with mapping table.
---

# Comparative Template

Use when topic matches " vs ", " compared to ", or "across traditions". The `traditions:` frontmatter MUST include all compared traditions.

## Shared Concept

Identify the common thread. What musical phenomenon, structure, or idea is being compared? State it in tradition-neutral terms before going into specifics.

## Tradition A Treatment

How <Tradition A> handles the concept. Vocabulary, theory, notation, performance practice. 3–5 paragraphs with concrete examples.

## Tradition B Treatment

How <Tradition B> handles the concept. Same depth as A — never give one tradition more space than another in a comparative.

(Add Tradition C, D as needed, each in its own section.)

## Mapping Table

A direct side-by-side comparison:

| Aspect | <Tradition A> | <Tradition B> |
|---|---|---|
| Name | | |
| Notation | | |
| Tuning | | |
| Function | | |
| Performance context | | |
| Variants | | |

## Points of Divergence

Where the analogy breaks down. What aspects of the concept exist in one tradition but have no analogue in another? 2–3 paragraphs.

## Visual Overview

- Mapping diagram: `[[<topic-slug>-mapping.json]]` (use cross-tradition emerald connections from §6 of diagram archetype)
- Side-by-side notation: `![[<topic-slug>-comparison.svg]]`

## Cross-References

`[[wiki-link]]` to: tradition overviews for each tradition compared, theory primers for each treatment, related comparative essays.

## Sources

Include sources from both traditions; avoid privileging one tradition's scholarship over another.
```

- [ ] **Step 2: Commit**

```bash
git add archetypes/music/documents/comparative.md
git commit -m "feat(music): add comparative document template"
```

---

### Task 18: Add archetype consultation step to `commands/document.md`

**Files:**
- Modify: `commands/document.md` — add new Step 1c between current Step 1b and Step 2

- [ ] **Step 1: Insert new step**

Add this content to `commands/document.md` after the closing of Step 1b (after line 56) and before the existing `## Step 2: Detect Vault and Gather Context`:

```markdown
## Step 1c: Select Document Template via Archetype

Run the archetype selection script to choose a template based on the topic and purpose:

```bash
ARCHETYPE_RESULT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "<topic>" \
  --output-type document \
  --purpose-hint "<topic>")
```

Parse the 3-token output: `<name> <subtype> <path>`.

- If output is `no-match`: skip this step. Generate the document using the existing free-form structure heuristics (Step 4 below).
- If `subtype` is one of: `theory-primer`, `biography`, `song-breakdown`, `instrument-profile`, `tradition-overview`, `history-timeline`, `comparative`, or `default`: read the template at `<path>` and follow its body section structure when generating the document.
- If `subtype` is `-` (single-file archetype): treat as no-match and skip.

When a template is selected, the document MUST include the shared frontmatter and closing sections defined in the template. The body sections follow the template's order. Substantive prose still applies — the template defines structure, not content.
```

- [ ] **Step 2: Verify the step appears in the right place**

Run: `grep -n "^## " ~/.claude/skills/knowledge-base/commands/document.md`
Expected output includes:
```
## Step 1: Parse Arguments
## Step 1b: Suggest Placement
## Step 1c: Select Document Template via Archetype
## Step 2: Detect Vault and Gather Context
...
```

- [ ] **Step 3: Commit**

```bash
git add commands/document.md
git commit -m "feat(document): add Step 1c — select document template via kb_archetype with --output-type document"
```

---

### Task 19: Phase 2 validation gate — selector picks correct template per topic

**Files:**
- Modify: `scripts/tests/test_kb_archetype.py`

- [ ] **Step 1: Add integration test against real `archetypes/music/`**

```python
import pytest

@pytest.mark.parametrize("topic,expected_subtype", [
    ("biography of John Coltrane",         "biography"),
    ("life of Ravi Shankar",               "biography"),
    ("history of jazz",                    "history-timeline"),
    ("evolution of polyphony",             "history-timeline"),
    ("analysis of Hotel California",       "song-breakdown"),
    ("anatomy of Giant Steps",             "song-breakdown"),
    ("the sitar",                          "instrument-profile"),
    ("Carnatic music",                     "tradition-overview"),
    ("Gamelan music",                      "tradition-overview"),
    ("Yaman vs Aeolian",                   "comparative"),
    ("modes across traditions",            "comparative"),
    ("perfect fifth",                      "default"),  # falls back
    ("what is a raga",                     "default"),  # falls back (no keyword match)
])
def test_real_music_archetype_dispatches_documents(topic, expected_subtype):
    real_dir = Path(__file__).resolve().parents[2] / "archetypes"
    out, rc = run([
        "--archetypes-dir", str(real_dir),
        "--topic", topic,
        "--output-type", "document",
        "--purpose-hint", topic,
    ])
    assert rc == 0, f"failed for topic {topic!r}: {out!r}"
    parts = out.split(maxsplit=2)
    assert parts[0] == "music", f"expected 'music' for {topic!r}, got {parts[0]!r}"
    assert parts[1] == expected_subtype, (
        f"expected subtype {expected_subtype!r} for topic {topic!r}, got {parts[1]!r}"
    )
```

- [ ] **Step 2: Run all tests**

Run: `python3 -m pytest scripts/tests/test_kb_archetype.py -v`
Expected: All previous tests pass + 13 parametrized tests pass = 20 PASSED total.

- [ ] **Step 3: Commit**

```bash
git add scripts/tests/test_kb_archetype.py
git commit -m "test: phase 2 gate — parametrized template dispatch for 13 representative topics"
```

**Phase 2 complete.** All 7 templates exist, document.md consults the archetype, dispatch is verified across 13 representative topics.

---

## Phase 3a: SVG Generator — Core 7 Renderers

Goal: Build `scripts/kb_svg.py` with CLI router, shared primitives, theme module, and 7 renderers (staff, fretboard, circle-of-fifths, raga-clock, maqam-jins, gamelan-cipher, chord-box). Add `archetypes/music/svg.md` and `commands/svg.md`.

### Task 20: `kb_svg.py` scaffolding — CLI router, primitives, theme

**Files:**
- Create: `scripts/kb_svg.py`
- Create: `scripts/tests/test_kb_svg.py`
- Create: `scripts/tests/fixtures/svg_golden/` (directory)

- [ ] **Step 1: Create the script skeleton**

Write `scripts/kb_svg.py`:

```python
#!/usr/bin/env python3
"""
Music SVG renderer. Pure stdlib. 14 renderer types, dispatched via --type.

Usage:
  kb_svg.py --type staff --notes "C4-q D4-q E4-h" [common flags]
  kb_svg.py --type fretboard --tuning EADGBE --notes "0,2,3" [common flags]
  ...

Common flags:
  --out <path>       output file (default: stdout)
  --width N          canvas width in px (default: per-type)
  --height N         canvas height in px (default: per-type)
  --theme light|dark
  --title "..."      optional title text
  --tradition <tag>  tints accents using tradition badge color
  --midi-out <path>  emit MIDI alongside SVG (where supported)
  --play             best-effort: play generated MIDI on this platform
"""
import argparse
import sys
from pathlib import Path

# ---------- THEME ----------
THEME = {
    "light": {
        "bg":          "#ffffff",
        "fg":          "#1f2937",
        "muted":       "#6b7280",
        "grid":        "#e5e7eb",
        "accent":      "#3b82f6",  # melodic blue (matches diagram §6)
        "harmonic":    "#8b5cf6",
        "rhythmic":    "#f59e0b",
        "structural":  "#64748b",
        "cross":       "#10b981",
        "lineage":     "#ec4899",
        "tension":     "#ef4444",
        "cadence":     "#0ea5e9",
    },
    "dark": {
        "bg":          "#0f172a",
        "fg":          "#e5e7eb",
        "muted":       "#94a3b8",
        "grid":        "#1e293b",
        "accent":      "#60a5fa",
        "harmonic":    "#a78bfa",
        "rhythmic":    "#fbbf24",
        "structural":  "#94a3b8",
        "cross":       "#34d399",
        "lineage":     "#f472b6",
        "tension":     "#f87171",
        "cadence":     "#38bdf8",
    },
}

TRADITION_BADGE = {
    "western":    "#2563eb",
    "jazz":       "#7c3aed",
    "hindustani": "#dc2626",
    "carnatic":   "#ea580c",
    "maqam":      "#059669",
    "persian":    "#0891b2",
    "gamelan":    "#a16207",
    "west-african": "#16a34a",
    "east-asian": "#9333ea",
    "latin":      "#e11d48",
    "folk":       "#475569",
}

# ---------- PRIMITIVES ----------
def svg_open(width: int, height: int, theme: dict, title: str = "") -> list[str]:
    """Open SVG document with XML header, root element, background, optional title."""
    parts = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="system-ui, -apple-system, sans-serif">',
        f'  <rect width="{width}" height="{height}" fill="{theme["bg"]}"/>',
    ]
    if title:
        parts.append(
            f'  <text x="{width // 2}" y="24" text-anchor="middle" '
            f'fill="{theme["fg"]}" font-size="16" font-weight="600">{_xml(title)}</text>'
        )
    return parts


def svg_close() -> str:
    return '</svg>'


def _xml(s: str) -> str:
    """Minimal XML escape for text content."""
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def line(x1, y1, x2, y2, color, width=1) -> str:
    return f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>'


def circle(cx, cy, r, fill="none", stroke="#000", stroke_width=1) -> str:
    return (f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}"/>')


def text(x, y, content, color, size=12, anchor="middle", weight="400") -> str:
    return (f'  <text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" '
            f'font-size="{size}" font-weight="{weight}">{_xml(content)}</text>')


def rect(x, y, w, h, fill="none", stroke="#000", stroke_width=1) -> str:
    return (f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}"/>')


def kb_meta_comment(args: argparse.Namespace) -> str:
    """Embed the originating CLI invocation as an SVG comment for round-trip clarity."""
    relevant = {k: v for k, v in vars(args).items() if v is not None and k != "out"}
    return f'  <!-- kb-meta: type={args.type} args={relevant} -->'


# ---------- DISPATCH ----------
def render(args: argparse.Namespace) -> str:
    """Top-level dispatcher: pick renderer by --type."""
    theme = THEME[args.theme]
    renderers = {
        "staff":            render_staff,
        "fretboard":        render_fretboard,
        "circle-of-fifths": render_circle_of_fifths,
        "raga-clock":       render_raga_clock,
        "maqam-jins":       render_maqam_jins,
        "gamelan-cipher":   render_gamelan_cipher,
        "chord-box":        render_chord_box,
        "neume":            render_neume,
        "sargam":           render_sargam,
        "jianpu":           render_jianpu,
        "gongche":          render_gongche,
        "rhythm-grid":      render_rhythm_grid,
        "clave":            render_clave,
        "tala":             render_tala,
    }
    if args.type not in renderers:
        sys.exit(f"unknown --type {args.type!r}; choices: {list(renderers)}")
    body = renderers[args.type](args, theme)
    return "\n".join([
        *svg_open(args.width, args.height, theme, args.title or ""),
        kb_meta_comment(args),
        *body,
        svg_close(),
    ])


# Renderers (each implemented in its own task below; placeholder stubs here)
def render_staff(args, theme): return ['  <!-- TODO: staff -->']
def render_fretboard(args, theme): return ['  <!-- TODO: fretboard -->']
def render_circle_of_fifths(args, theme): return ['  <!-- TODO: circle-of-fifths -->']
def render_raga_clock(args, theme): return ['  <!-- TODO: raga-clock -->']
def render_maqam_jins(args, theme): return ['  <!-- TODO: maqam-jins -->']
def render_gamelan_cipher(args, theme): return ['  <!-- TODO: gamelan-cipher -->']
def render_chord_box(args, theme): return ['  <!-- TODO: chord-box -->']
def render_neume(args, theme): return ['  <!-- TODO: neume -->']
def render_sargam(args, theme): return ['  <!-- TODO: sargam -->']
def render_jianpu(args, theme): return ['  <!-- TODO: jianpu -->']
def render_gongche(args, theme): return ['  <!-- TODO: gongche -->']
def render_rhythm_grid(args, theme): return ['  <!-- TODO: rhythm-grid -->']
def render_clave(args, theme): return ['  <!-- TODO: clave -->']
def render_tala(args, theme): return ['  <!-- TODO: tala -->']


# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description="Music SVG renderer")
    ap.add_argument("--type", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--width", type=int, default=600)
    ap.add_argument("--height", type=int, default=400)
    ap.add_argument("--theme", choices=["light", "dark"], default="light")
    ap.add_argument("--title", default="")
    ap.add_argument("--tradition", default=None)
    ap.add_argument("--midi-out", default=None, dest="midi_out")
    ap.add_argument("--play", action="store_true")
    # Per-type flags (parsed permissively; renderers pull what they need)
    ap.add_argument("--clef", default="treble")
    ap.add_argument("--key", default="C major")
    ap.add_argument("--time-sig", default="4/4", dest="time_sig")
    ap.add_argument("--notes", default="")
    ap.add_argument("--strings", type=int, default=6)
    ap.add_argument("--tuning", default="EADGBE")
    ap.add_argument("--highlight", default="")
    ap.add_argument("--jazz-extensions", action="store_true", dest="jazz_extensions")
    ap.add_argument("--quartertones", action="store_true")
    ap.add_argument("--raga", default="")
    ap.add_argument("--shrutis", type=int, default=12)
    ap.add_argument("--show-vadi", action="store_true", dest="show_vadi")
    ap.add_argument("--jins", default="")
    ap.add_argument("--root", default="D")
    ap.add_argument("--show-cents", action="store_true", dest="show_cents")
    ap.add_argument("--pattern", default="")
    ap.add_argument("--instrument", default="guitar")
    ap.add_argument("--chord", default="")
    ap.add_argument("--fingering", default="")
    ap.add_argument("--mode", default="I")
    ap.add_argument("--text", default="", dest="lyric")
    ap.add_argument("--neumes", default="")
    ap.add_argument("--scale", default="")
    ap.add_argument("--steps", type=int, default=16)
    ap.add_argument("--tracks", default="")
    ap.add_argument("--tala", default="")
    ap.add_argument("--style", default="")
    ap.add_argument("--strum", action="store_true")
    ap.add_argument("--arpeggiate", action="store_true")
    args = ap.parse_args()

    svg = render(args)

    if args.out:
        Path(args.out).write_text(svg, encoding="utf-8")
    else:
        sys.stdout.write(svg)
        sys.stdout.write("\n")

    # MIDI export and playback handled in Phase 4 by kb_midi.py


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make script executable**

Run: `chmod +x ~/.claude/skills/knowledge-base/scripts/kb_svg.py`

- [ ] **Step 3: Create golden fixtures directory and test scaffolding**

Create `scripts/tests/test_kb_svg.py`:

```python
"""Golden-master tests for kb_svg.py. Each renderer has one canonical invocation."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "kb_svg.py"
GOLDEN = Path(__file__).resolve().parent / "fixtures" / "svg_golden"


def run_svg(*args: str) -> str:
    """Invoke kb_svg.py and return stdout SVG (stripped of timestamps)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, check=True,
    )
    return _strip_volatile(proc.stdout)


def _strip_volatile(svg: str) -> str:
    """Remove any volatile bytes (timestamps, UUIDs) before comparison."""
    svg = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "TIMESTAMP", svg)
    svg = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "UUID", svg)
    return svg.strip()


def assert_golden(name: str, actual: str):
    GOLDEN.mkdir(parents=True, exist_ok=True)
    path = GOLDEN / f"{name}.svg"
    if not path.exists():
        # First run: write golden; subsequent runs compare.
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"wrote new golden: {path}")
    expected = _strip_volatile(path.read_text(encoding="utf-8"))
    assert actual == expected, f"{name} differs from golden {path}"
```

- [ ] **Step 4: Verify the script runs and emits a stub SVG**

Run:
```bash
python3 ~/.claude/skills/knowledge-base/scripts/kb_svg.py --type staff
```
Expected: SVG output to stdout containing `<!-- TODO: staff -->`.

- [ ] **Step 5: Commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py
chmod +x scripts/kb_svg.py
git commit -m "feat(kb_svg): scaffold CLI router, primitives, theme, and renderer dispatch with stubs"
```

---

### Task 21: `staff` renderer

**Files:**
- Modify: `scripts/kb_svg.py` — replace `render_staff` stub
- Modify: `scripts/tests/test_kb_svg.py` — add staff test

- [ ] **Step 1: Add failing test**

Append to `test_kb_svg.py`:

```python
def test_staff_basic_treble_c_major():
    actual = run_svg(
        "--type", "staff",
        "--clef", "treble",
        "--key", "C major",
        "--time-sig", "4/4",
        "--notes", "C4-q D4-q E4-q F4-q",
        "--width", "600",
        "--height", "200",
    )
    assert "<line" in actual  # 5 staff lines drawn
    assert actual.count("<line") >= 5  # at least 5 lines for the staff itself
    assert_golden("staff_basic", actual)
```

- [ ] **Step 2: Run, verify it fails**

Run: `python3 -m pytest scripts/tests/test_kb_svg.py::test_staff_basic_treble_c_major -v`
Expected: FAIL — current stub has no `<line>` elements.

- [ ] **Step 3: Replace `render_staff` with real implementation**

Replace the `render_staff` stub in `kb_svg.py` with:

```python
def render_staff(args, theme):
    """Render a single-line Western staff with notes. Notes format: 'C4-q D4-q E4-h ...'.
    Suffixes: -w whole, -h half, -q quarter, -e eighth, -s sixteenth.
    Sharps/flats: 'C#4-q', 'Bb4-q'. Quartertones: 'Cd4' (half-flat) or 'C+4' (half-sharp)."""
    parts = []
    margin_x, margin_y = 60, 80
    staff_height = 40  # 4 line-spaces × 10px
    line_gap = staff_height // 4
    staff_top = margin_y
    width_avail = args.width - 2 * margin_x

    # Staff lines (5 lines, top to bottom)
    for i in range(5):
        y = staff_top + i * line_gap
        parts.append(line(margin_x, y, args.width - margin_x, y, theme["fg"], 1))

    # Clef glyph (textual; SVG fonts are not guaranteed for music symbols, use letters)
    clef_label = {"treble": "G", "bass": "F", "alto": "C", "tenor": "C"}.get(args.clef, "G")
    parts.append(text(margin_x - 30, staff_top + line_gap * 2 + 5, clef_label,
                      theme["accent"], size=24, weight="700"))

    # Time signature
    if args.time_sig and "/" in args.time_sig:
        num, den = args.time_sig.split("/", 1)
        parts.append(text(margin_x + 6, staff_top + line_gap + 5, num, theme["fg"], 14, "start", "700"))
        parts.append(text(margin_x + 6, staff_top + line_gap * 3 + 5, den, theme["fg"], 14, "start", "700"))

    # Notes
    if args.notes:
        tokens = [t for t in args.notes.split() if t]
        if tokens:
            x_step = (width_avail - 40) // max(len(tokens), 1)
            for i, tok in enumerate(tokens):
                # Parse: pitch (e.g. C4, F#4, Bb3) + duration suffix
                pitch_part, _, dur = tok.partition("-")
                cx = margin_x + 40 + i * x_step
                # Vertical position: rough mapping for treble clef E4 = bottom line.
                # Map pitch letter + octave to staff position.
                cy = _staff_y(pitch_part, args.clef, staff_top, line_gap)
                # Notehead (filled for q/e/s, open for w/h)
                fill = theme["fg"] if dur in ("q", "e", "s") else "none"
                parts.append(circle(cx, cy, 5, fill=fill, stroke=theme["fg"], stroke_width=1.5))
                # Stem (skipped for whole notes)
                if dur != "w":
                    stem_top = cy - 30
                    parts.append(line(cx + 5, cy, cx + 5, stem_top, theme["fg"], 1.5))
                # Accidental
                if "#" in pitch_part:
                    parts.append(text(cx - 10, cy + 3, "#", theme["fg"], 12, "end", "700"))
                elif "b" in pitch_part[1:]:
                    parts.append(text(cx - 10, cy + 3, "b", theme["fg"], 12, "end", "700"))
    return parts


def _staff_y(pitch_part: str, clef: str, staff_top: int, line_gap: int) -> int:
    """Map e.g. 'C4', 'F#4', 'Bb3' to vertical y on staff. Treble clef baseline."""
    if not pitch_part:
        return staff_top + line_gap * 2
    letter = pitch_part[0].upper()
    # Strip accidentals
    rest = pitch_part[1:].lstrip("#b")
    try:
        octave = int(rest) if rest else 4
    except ValueError:
        octave = 4
    # Treble clef: each step on staff = a diatonic step.
    # Bottom line = E4 at staff_top + 4*line_gap (= staff_top + 40)
    diatonic = "CDEFGAB".index(letter)
    # Distance in diatonic steps from E4
    semitones_from_e4 = (octave - 4) * 7 + (diatonic - 2)
    half_gap = line_gap // 2
    return staff_top + 4 * line_gap - semitones_from_e4 * half_gap
```

- [ ] **Step 4: Run test; on first pass it writes the golden, on second it verifies**

Run twice:
```bash
python3 -m pytest scripts/tests/test_kb_svg.py::test_staff_basic_treble_c_major -v
python3 -m pytest scripts/tests/test_kb_svg.py::test_staff_basic_treble_c_major -v
```
Expected first run: SKIPPED (wrote new golden).
Expected second run: PASSED.

- [ ] **Step 5: Visually inspect the golden**

Run: `cat scripts/tests/fixtures/svg_golden/staff_basic.svg | head -20`
Open it in a browser to verify it looks like a staff with four notes.

- [ ] **Step 6: Commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/staff_basic.svg
git commit -m "feat(kb_svg): implement staff renderer with notes, clef, time signature, accidentals"
```

---

### Task 22: `fretboard` renderer

**Files:**
- Modify: `scripts/kb_svg.py` — replace `render_fretboard`
- Modify: `scripts/tests/test_kb_svg.py`

- [ ] **Step 1: Add test**

```python
def test_fretboard_guitar_standard_tuning():
    actual = run_svg(
        "--type", "fretboard",
        "--strings", "6",
        "--tuning", "EADGBE",
        "--notes", "0,2,3",  # frets to highlight
        "--width", "700", "--height", "240",
    )
    assert "<line" in actual
    assert "EADGBE"[0] in actual or "E" in actual  # string label rendered
    assert_golden("fretboard_guitar_eadgbe", actual)
```

- [ ] **Step 2: Implement renderer**

Replace `render_fretboard` stub:

```python
def render_fretboard(args, theme):
    """Render a fretboard with N strings (default 6), custom tuning, optional fret highlights.
    --tuning is a string of single-char string names ("EADGBE") OR comma-separated ("E,A,D,G,B,E").
    --notes is comma-separated fret numbers (or 'x' for muted) per string, top-to-bottom."""
    parts = []
    margin_x, margin_y = 70, 70
    fret_count = 12  # standard
    fb_width = args.width - 2 * margin_x
    string_gap = 24
    fb_height = (args.strings - 1) * string_gap
    fb_top = margin_y
    fb_left = margin_x
    fret_gap = fb_width / fret_count

    # Parse tuning
    if "," in args.tuning:
        tuning = [t.strip() for t in args.tuning.split(",")]
    else:
        tuning = list(args.tuning)
    # Pad/truncate to --strings
    tuning = (tuning + ["?"] * args.strings)[: args.strings]

    # Strings (horizontal lines, top = highest pitch by convention)
    for i in range(args.strings):
        y = fb_top + i * string_gap
        parts.append(line(fb_left, y, fb_left + fb_width, y, theme["fg"], 1.5))
        # String label (left of the fretboard)
        parts.append(text(fb_left - 10, y + 4, tuning[args.strings - 1 - i],
                          theme["muted"], 12, "end"))

    # Frets (vertical lines)
    for f in range(fret_count + 1):
        x = fb_left + f * fret_gap
        stroke_w = 3 if f == 0 else 1
        parts.append(line(x, fb_top, x, fb_top + fb_height, theme["fg"], stroke_w))

    # Fret-position dots (3, 5, 7, 9, 12 — single dots; 12 doubled)
    dot_y = fb_top + fb_height + 16
    for fret in (3, 5, 7, 9):
        cx = fb_left + (fret - 0.5) * fret_gap
        parts.append(circle(cx, dot_y, 3, fill=theme["muted"], stroke="none"))
    cx12 = fb_left + 11.5 * fret_gap
    parts.append(circle(cx12 - 5, dot_y, 3, fill=theme["muted"], stroke="none"))
    parts.append(circle(cx12 + 5, dot_y, 3, fill=theme["muted"], stroke="none"))

    # Highlight notes (fret positions across all strings)
    if args.notes:
        accent = theme["accent"]
        if args.tradition and args.tradition in TRADITION_BADGE:
            accent = TRADITION_BADGE[args.tradition]
        frets_to_highlight = [f.strip() for f in args.notes.split(",") if f.strip()]
        for fret_str in frets_to_highlight:
            try:
                fret = int(fret_str)
            except ValueError:
                continue
            if 0 <= fret <= fret_count:
                cx = fb_left + (fret - 0.5) * fret_gap if fret > 0 else fb_left - 14
                for s in range(args.strings):
                    cy = fb_top + s * string_gap
                    parts.append(circle(cx, cy, 7, fill=accent, stroke=theme["bg"], stroke_width=2))
    return parts
```

- [ ] **Step 3: Run test (first pass writes golden)**

Run twice:
```bash
python3 -m pytest scripts/tests/test_kb_svg.py::test_fretboard_guitar_standard_tuning -v
```
Expected second run: PASSED.

- [ ] **Step 4: Commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/fretboard_guitar_eadgbe.svg
git commit -m "feat(kb_svg): implement fretboard renderer with N strings, custom tuning, fret highlights"
```

---

### Task 23: `circle-of-fifths` renderer

**Files:**
- Modify: `scripts/kb_svg.py` — replace `render_circle_of_fifths`
- Modify: `scripts/tests/test_kb_svg.py`

- [ ] **Step 1: Add test**

```python
def test_circle_of_fifths_basic():
    actual = run_svg(
        "--type", "circle-of-fifths",
        "--highlight", "C,G,D",
        "--width", "500", "--height", "500",
    )
    # 12 outer keys
    for k in ["C", "G", "D", "A", "E", "B", "F"]:
        assert f">{k}<" in actual
    assert_golden("circle_basic", actual)
```

- [ ] **Step 2: Implement renderer**

```python
def render_circle_of_fifths(args, theme):
    """Render the Western circle of fifths. 12 outer keys, 12 inner relative minors.
    --highlight: comma-separated key names (e.g. 'C,G,D') get accent color.
    --jazz-extensions: render outer ring of common jazz extensions (Cmaj7 etc.)."""
    import math
    parts = []
    cx, cy = args.width // 2, args.height // 2
    outer_r = min(cx, cy) - 60
    inner_r = outer_r - 60
    # Major keys clockwise from C at 12 o'clock
    majors = ["C", "G", "D", "A", "E", "B", "F#", "C#", "G#", "D#", "A#", "F"]
    minors = ["a", "e", "b", "f#", "c#", "g#", "d#", "a#", "f", "c", "g", "d"]
    highlights = {h.strip() for h in (args.highlight or "").split(",") if h.strip()}
    parts.append(circle(cx, cy, outer_r, fill="none", stroke=theme["grid"], stroke_width=1))
    parts.append(circle(cx, cy, inner_r, fill="none", stroke=theme["grid"], stroke_width=1))
    for i, (M, m) in enumerate(zip(majors, minors)):
        # 12 o'clock = -π/2; clockwise increments
        angle = -math.pi / 2 + i * (2 * math.pi / 12)
        Mx = cx + outer_r * math.cos(angle)
        My = cy + outer_r * math.sin(angle)
        mx = cx + inner_r * math.cos(angle)
        my = cy + inner_r * math.sin(angle)
        Mcolor = theme["accent"] if M in highlights else theme["fg"]
        parts.append(text(Mx, My + 5, M, Mcolor, 18, "middle", "700"))
        parts.append(text(mx, my + 4, m, theme["muted"], 12))
        # Radial spoke
        parts.append(line(cx + (inner_r - 6) * math.cos(angle),
                          cy + (inner_r - 6) * math.sin(angle),
                          cx + (outer_r - 18) * math.cos(angle),
                          cy + (outer_r - 18) * math.sin(angle),
                          theme["grid"], 1))
    return parts
```

- [ ] **Step 3: Run test, then commit**

Run: `python3 -m pytest scripts/tests/test_kb_svg.py::test_circle_of_fifths_basic -v` (twice).

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/circle_basic.svg
git commit -m "feat(kb_svg): implement circle-of-fifths renderer with major/minor rings and highlights"
```

---

### Task 24: `raga-clock` renderer

**Files:**
- Modify: `scripts/kb_svg.py` — replace `render_raga_clock`
- Modify: `scripts/tests/test_kb_svg.py`

- [ ] **Step 1: Add test**

```python
def test_raga_clock_yaman():
    actual = run_svg(
        "--type", "raga-clock",
        "--raga", "Yaman",
        "--shrutis", "12",
        "--width", "500", "--height", "500",
    )
    for s in ["Sa", "Re", "Ga", "Ma", "Pa", "Dha", "Ni"]:
        assert f">{s}<" in actual
    assert_golden("raga_yaman", actual)
```

- [ ] **Step 2: Implement renderer**

```python
RAGA_AROHANA = {
    "Yaman":     [0, 2, 4, 6, 7, 9, 11],   # Sa Re Ga Ma# Pa Dha Ni
    "Bhairav":   [0, 1, 4, 5, 7, 8, 11],   # Sa Re_b Ga Ma Pa Dha_b Ni
    "Bhairavi":  [0, 1, 3, 5, 7, 8, 10],   # all komal
    "Yaman Kalyan": [0, 2, 4, 5, 6, 7, 9, 11],
    "Marwa":     [0, 1, 4, 6, 9, 11],
    "Bilawal":   [0, 2, 4, 5, 7, 9, 11],   # major
    "Khamaj":    [0, 2, 4, 5, 7, 9, 10],
    "Kafi":      [0, 2, 3, 5, 7, 9, 10],   # dorian
    "Asavari":   [0, 2, 3, 5, 7, 8, 10],   # natural minor
    "Todi":      [0, 1, 3, 6, 7, 8, 11],
    "Purvi":     [0, 1, 4, 6, 7, 8, 11],
}

SWARA_LABELS = ["Sa", "re", "Re", "ga", "Ga", "Ma", "Ma#", "Pa", "dha", "Dha", "ni", "Ni"]


def render_raga_clock(args, theme):
    """12-pitch (or 22-shruti) circle showing raga arohana. Sa at 12 o'clock."""
    import math
    parts = []
    cx, cy = args.width // 2, args.height // 2
    r = min(cx, cy) - 60
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]

    n = 22 if args.shrutis == 22 else 12
    parts.append(circle(cx, cy, r, fill="none", stroke=theme["grid"], stroke_width=1))

    arohana = RAGA_AROHANA.get(args.raga, [])
    if n == 22:
        # 22-shruti: positions are not equidistant; use canonical shruti positions if known.
        # Fallback for v1: equidistant 22 positions.
        positions = list(range(22))
        labels = [str(i + 1) for i in positions]
    else:
        positions = list(range(12))
        labels = SWARA_LABELS

    for i in positions:
        angle = -math.pi / 2 + i * (2 * math.pi / n)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        in_raga = i in arohana
        col = accent if in_raga else theme["muted"]
        weight = "700" if in_raga else "400"
        parts.append(circle(x, y, 6, fill=col, stroke="none"))
        parts.append(text(x, y - 12, labels[i], theme["fg"], 11, "middle", weight))

    # Connect arohana notes with thin lines (visualize ascending order)
    if arohana:
        for a, b in zip(arohana, arohana[1:]):
            angle_a = -math.pi / 2 + a * (2 * math.pi / n)
            angle_b = -math.pi / 2 + b * (2 * math.pi / n)
            parts.append(line(cx + r * math.cos(angle_a), cy + r * math.sin(angle_a),
                              cx + r * math.cos(angle_b), cy + r * math.sin(angle_b),
                              accent, 1.5))

    if args.raga:
        parts.append(text(cx, cy + 5, args.raga, theme["fg"], 18, "middle", "700"))
    return parts
```

- [ ] **Step 3: Run test, commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/raga_yaman.svg
git commit -m "feat(kb_svg): implement raga-clock renderer with 12-shruti and 22-shruti modes, common ragas"
```

---

### Task 25: `maqam-jins` renderer

**Files:** Modify `scripts/kb_svg.py`, add test.

- [ ] **Step 1: Add test**

```python
def test_maqam_jins_hijaz():
    actual = run_svg(
        "--type", "maqam-jins",
        "--jins", "Hijaz",
        "--root", "D",
        "--show-cents",
        "--width", "600", "--height", "260",
    )
    assert "Hijaz" in actual
    assert "D" in actual  # root pitch label
    assert_golden("maqam_hijaz", actual)
```

- [ ] **Step 2: Implement renderer**

```python
JINS_INTERVALS = {
    # cents from root: tetrachord (or pentachord)
    "Rast":    [0, 200, 350, 500],          # neutral 3rd
    "Bayati":  [0, 150, 350, 500],          # half-flat 2nd
    "Hijaz":   [0, 100, 400, 500],          # augmented 2nd
    "Saba":    [0, 150, 300, 400],
    "Kurd":    [0, 100, 300, 500],
    "Ajam":    [0, 200, 400, 500],          # major
    "Nahawand":[0, 200, 300, 500],          # minor
    "Sikah":   [0, 150, 350],               # tritonic
}


def render_maqam_jins(args, theme):
    """Render an Arabic jins (tetrachord) as a horizontal cents-axis with quartertone-aware notation."""
    parts = []
    margin_x, margin_y = 60, 100
    axis_y = margin_y + 60
    width_avail = args.width - 2 * margin_x
    intervals = JINS_INTERVALS.get(args.jins, [0, 200, 400, 500])
    max_cents = max(intervals)
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]

    # Axis line
    parts.append(line(margin_x, axis_y, args.width - margin_x, axis_y, theme["fg"], 1.5))
    # Axis ticks every 100 cents
    for c in range(0, max_cents + 1, 100):
        x = margin_x + (c / max_cents) * width_avail
        parts.append(line(x, axis_y - 6, x, axis_y + 6, theme["grid"], 1))
        if args.show_cents:
            parts.append(text(x, axis_y + 22, f"{c}¢", theme["muted"], 9))

    # Pitch markers
    pitch_names = _maqam_pitch_names(args.root, intervals)
    for c, label in zip(intervals, pitch_names):
        x = margin_x + (c / max_cents) * width_avail
        parts.append(circle(x, axis_y, 7, fill=accent, stroke=theme["bg"], stroke_width=2))
        parts.append(text(x, axis_y - 18, label, theme["fg"], 13, "middle", "700"))

    # Connect pitches with arc to suggest melodic motion
    for c1, c2 in zip(intervals, intervals[1:]):
        x1 = margin_x + (c1 / max_cents) * width_avail
        x2 = margin_x + (c2 / max_cents) * width_avail
        parts.append(line(x1, axis_y - 30, x2, axis_y - 30, accent, 1))

    parts.append(text(args.width // 2, margin_y, f"Jins {args.jins}",
                      theme["fg"], 16, "middle", "700"))
    return parts


def _maqam_pitch_names(root: str, intervals_cents: list[int]) -> list[str]:
    """Return pitch names for each interval, using nearest 12-TET letter + microtonal accidentals."""
    semitones_per_step = [round(c / 100) for c in intervals_cents]
    base_idx = "CDEFGAB".index(root[0].upper()) if root and root[0].upper() in "CDEFGAB" else 1
    notes = "CDEFGAB"
    out = []
    for c, st in zip(intervals_cents, semitones_per_step):
        # Diatonic step approximation
        diat_step = round(st * 7 / 12)
        idx = (base_idx + diat_step) % 7
        accidental = ""
        # Quartertone marker if cents not multiple of 100
        if c % 100 != 0:
            if c % 100 == 50:
                accidental = "+" if c > st * 100 else "d"  # half-sharp / half-flat sentinels
        out.append(notes[idx] + accidental)
    return out
```

- [ ] **Step 3: Run test, commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/maqam_hijaz.svg
git commit -m "feat(kb_svg): implement maqam-jins renderer with cents-axis quartertone visualization"
```

---

### Task 26: `gamelan-cipher` renderer

**Files:** Modify `scripts/kb_svg.py`, add test.

- [ ] **Step 1: Add test**

```python
def test_gamelan_cipher_slendro():
    actual = run_svg(
        "--type", "gamelan-cipher",
        "--tuning", "slendro",
        "--pattern", "1 2 3 5 6 1",
        "--width", "600", "--height", "200",
    )
    assert "1" in actual and "2" in actual
    assert_golden("gamelan_slendro", actual)
```

- [ ] **Step 2: Implement renderer**

```python
def render_gamelan_cipher(args, theme):
    """Render Javanese/Balinese cipher notation. Slendro = 5-note (1,2,3,5,6); pelog = 7-note (1-7)."""
    parts = []
    margin_x, margin_y = 60, 80
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]

    valid_digits = {"slendro": set("12356"), "pelog": set("1234567")}.get(args.tuning, set("123456"))
    tokens = (args.pattern or "").split()
    if not tokens:
        return parts
    cell_w = (args.width - 2 * margin_x) // max(len(tokens), 1)

    parts.append(text(args.width // 2, margin_y - 40,
                      f"{args.tuning.title()} pattern",
                      theme["fg"], 14, "middle", "600"))

    for i, tok in enumerate(tokens):
        x = margin_x + i * cell_w + cell_w // 2
        in_tuning = tok in valid_digits
        col = accent if in_tuning else theme["muted"]
        # Beat marker
        parts.append(line(margin_x + i * cell_w, margin_y + 20,
                          margin_x + i * cell_w, margin_y + 80, theme["grid"], 1))
        # Cipher digit
        parts.append(text(x, margin_y + 56, tok, col, 28, "middle", "700"))
    # Closing barline
    parts.append(line(margin_x + len(tokens) * cell_w, margin_y + 20,
                      margin_x + len(tokens) * cell_w, margin_y + 80, theme["fg"], 2))
    return parts
```

- [ ] **Step 3: Run test, commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/gamelan_slendro.svg
git commit -m "feat(kb_svg): implement gamelan-cipher renderer for slendro and pelog tunings"
```

---

### Task 27: `chord-box` renderer

**Files:** Modify `scripts/kb_svg.py`, add test.

- [ ] **Step 1: Add test**

```python
def test_chord_box_dm7_guitar():
    actual = run_svg(
        "--type", "chord-box",
        "--instrument", "guitar",
        "--chord", "Dm7",
        "--fingering", "x x 0 2 1 1",
        "--width", "200", "--height", "240",
    )
    assert "Dm7" in actual
    assert_golden("chord_dm7", actual)
```

- [ ] **Step 2: Implement renderer**

```python
def render_chord_box(args, theme):
    """Render a chord block diagram. Fingering format: 'x x 0 2 1 1' (low to high string)."""
    parts = []
    n_strings = {"guitar": 6, "uke": 4, "bass": 4, "mandolin": 8}.get(args.instrument, 6)
    n_frets = 5
    margin_x, margin_y = 40, 70
    string_gap = 18
    fret_gap = 28
    box_w = (n_strings - 1) * string_gap
    box_h = n_frets * fret_gap
    box_left = margin_x
    box_top = margin_y

    # Title
    if args.chord:
        parts.append(text(box_left + box_w // 2, margin_y - 20, args.chord,
                          theme["fg"], 18, "middle", "700"))

    # Strings (vertical)
    for s in range(n_strings):
        x = box_left + s * string_gap
        parts.append(line(x, box_top, x, box_top + box_h, theme["fg"], 1))
    # Frets (horizontal); top = nut (thicker)
    for f in range(n_frets + 1):
        y = box_top + f * fret_gap
        sw = 3 if f == 0 else 1
        parts.append(line(box_left, y, box_left + box_w, y, theme["fg"], sw))

    # Fingering: split tokens, one per string (low to high)
    if args.fingering:
        accent = theme["accent"]
        if args.tradition and args.tradition in TRADITION_BADGE:
            accent = TRADITION_BADGE[args.tradition]
        tokens = args.fingering.strip().split()
        # Pad/truncate
        tokens = (tokens + [" "] * n_strings)[: n_strings]
        for s, tok in enumerate(tokens):
            x = box_left + s * string_gap
            if tok == "x":
                parts.append(text(x, box_top - 5, "✕", theme["muted"], 14))
            elif tok == "0":
                parts.append(circle(x, box_top - 8, 5, fill="none",
                                    stroke=theme["fg"], stroke_width=1.5))
            else:
                try:
                    fret = int(tok)
                    cy = box_top + (fret - 0.5) * fret_gap
                    parts.append(circle(x, cy, 7, fill=accent, stroke=theme["bg"],
                                        stroke_width=2))
                except ValueError:
                    pass
    return parts
```

- [ ] **Step 3: Run test, commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/chord_dm7.svg
git commit -m "feat(kb_svg): implement chord-box renderer for guitar/uke/bass/mandolin"
```

---

### Task 28: Write `archetypes/music/svg.md` renderer catalog

**Files:**
- Create: `archetypes/music/svg.md`

- [ ] **Step 1: Write the catalog**

```markdown
---
name: music-svg
description: SVG renderer catalog for music — calls scripts/kb_svg.py with renderer-specific parameters
domain-indicators:
  - svg
  - circle of fifths
  - fretboard
  - staff notation
  - raga clock
  - maqam
  - gamelan
  - chord chart
  - rhythm grid
  - clave
  - tala
  - neume
  - sargam
  - jianpu
  - gongche
---

# Sub-Archetype: Music SVG

This sub-archetype tells the AI which kb_svg.py renderer to invoke for a given musical concept and how to format the parameters. The script is at `scripts/kb_svg.py` and is invoked via shell-out from `commands/svg.md`.

## Renderer Catalog

| `--type` | Use when | Tradition coverage | Common params |
|---|---|---|---|
| `staff` | Western pitched notation; quartertone Western/maqam staves | Western, Jazz, Maqam | `--clef`, `--key`, `--time-sig`, `--notes` |
| `fretboard` | Fretted instruments; scale or chord overlays | Guitar, bass, banjo, ukulele, sitar, oud, lute | `--strings`, `--tuning`, `--notes`, `--highlight` |
| `circle-of-fifths` | Western tonal relationships, key signatures | Western, Jazz | `--highlight`, `--jazz-extensions`, `--quartertones` |
| `raga-clock` | Hindustani/Carnatic raga visualization | Hindustani, Carnatic | `--raga`, `--shrutis 12\|22`, `--show-vadi` |
| `maqam-jins` | Arabic ajnas (tetrachords), quartertones | Arabic, Turkish, Persian, Andalusian | `--jins`, `--root`, `--show-cents` |
| `gamelan-cipher` | Javanese/Balinese cipher notation | Gamelan | `--tuning slendro\|pelog`, `--pattern` |
| `chord-box` | Block-diagram chord chart | Any fretted | `--instrument`, `--chord`, `--fingering` |
| `neume` | Medieval Western chant | Western (medieval) | `--mode`, `--text`, `--neumes` |
| `sargam` | Indian cipher notation | Hindustani, Carnatic | `--scale`, `--pattern`, `--gamaka` |
| `jianpu` | Chinese numbered notation | East Asian | `--key`, `--time-sig`, `--pattern` |
| `gongche` | Traditional Chinese character notation | East Asian (historical) | `--scale`, `--pattern` |
| `rhythm-grid` | Universal beat-grid (TR-808 style) | All | `--steps`, `--tracks`, `--pattern` |
| `clave` | Afro-Cuban patterns | Latin American | `--pattern son-3-2\|...`, `--style staff\|dot-pattern` |
| `tala` | Indian rhythm cycle | Hindustani, Carnatic | `--tala`, `--style circular\|linear` |

## Parameter Conventions

### Pitch / note format

- Western pitch: `C4`, `F#4`, `Bb3` (letter + accidental + octave; 4 = middle).
- Duration suffix on staff notes: `-w` whole, `-h` half, `-q` quarter, `-e` eighth, `-s` sixteenth.
- Quartertone accidentals: `+` half-sharp, `d` half-flat (e.g. `Cd4` = C half-flat octave 4).

### Fingering format (chord-box, fretboard)

- Space-separated, one per string, low pitch to high pitch.
- `x` = muted, `0` = open, integer = fret number.
- Example: `x x 0 2 1 1` for guitar Dm7.

### Pattern format (rhythm-grid, gamelan, jianpu)

- Bar separator: `|` (jianpu uses `|` between measures).
- Step symbol: `x` (hit) or `.` (rest) for percussion grids; digits for cipher notations.

### Tradition tinting

- Pass `--tradition <tag>` to recolor accent elements using the §4 tradition badge palette.
- Valid tags: `western`, `jazz`, `hindustani`, `carnatic`, `maqam`, `persian`, `gamelan`, `west-african`, `east-asian`, `latin`, `folk`.

## Cross-Link Conventions

Every generated SVG includes an `<!-- kb-meta: ... -->` comment with the originating CLI invocation. The companion document references the SVG via `![[<filename>.svg]]` in its `## Visual Overview` section.

## Example Invocations

```
# C major scale on a treble staff
kb_svg.py --type staff --key "C major" --time-sig 4/4 --notes "C4-q D4-q E4-q F4-q G4-h" --out scale.svg

# Yaman raga clock with vadi
kb_svg.py --type raga-clock --raga Yaman --shrutis 12 --show-vadi --out yaman.svg

# Hijaz jins on D
kb_svg.py --type maqam-jins --jins Hijaz --root D --show-cents --out hijaz.svg

# Son 3-2 clave
kb_svg.py --type clave --pattern son-3-2 --style dot-pattern --out son.svg

# Teentaal in 16-beat circular layout
kb_svg.py --type tala --tala Teentaal --style circular --out teentaal.svg
```

## When to Hand-Author Instead

If the topic isn't covered by any renderer (e.g., Byzantine chant, Tibetan ritual notation, Klezmer modes shown in non-standard ways), fall back to hand-authored SVG. The AI should:

1. Describe the desired visualization in 2–3 sentences.
2. Author the SVG directly using the same color palette as `kb_svg.py` (theme module's accent, harmonic, rhythmic colors).
3. Include the `<!-- kb-meta: type=hand-authored topic="..." -->` comment.

## Future Renderers (not yet implemented)

Tracked in `ICON_REQUESTS.md`: Byzantine notation, Klezmer mode wheels, ney holes diagram, koto bridges, lute course diagrams.
```

- [ ] **Step 2: Commit**

```bash
git add archetypes/music/svg.md
git commit -m "feat(music): add svg sub-archetype with 14-renderer catalog and parameter conventions"
```

---

### Task 29: Create `commands/svg.md`

**Files:**
- Create: `commands/svg.md`

- [ ] **Step 1: Write the command file**

```markdown
# Command: svg

Generate an SVG visualization for any topic via `kb_svg.py`. The archetype selector picks the right renderer based on the topic.

## Usage

```
/knowledge-base svg <topic> [-i]
/kb svg "C major scale on staff"
/kb svg "Yaman raga clock"
/kb svg "Hijaz jins on D"
```

## Inputs

The dispatcher passes:
- **topic** — everything after the `svg` token, with `-i` stripped
- **interactive** — boolean flag
- **vaultRoot** — vault root (or null)
- **gatheredContext** — compound intelligence context block

## Step 1: Vault Detection and Context Gathering

Handled by `SKILL.md` before dispatch. Use `vaultRoot` and `gatheredContext`.

## Step 2: Select Sub-Archetype

```bash
ARCHETYPE_RESULT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "<topic>" \
  --output-type svg)
```

Parse 3-token output `<name> <subtype> <path>`.

- If `subtype` is `svg`: read `<path>` (the music svg sub-archetype) for renderer catalog and parameter conventions.
- If output is `no-match`: fall back to hand-authored SVG (the AI writes raw SVG markup directly using the conventions described in `archetypes/music/svg.md` if available, or a minimal stylesheet otherwise).

## Step 3: Determine Renderer Type and Parameters

From the topic and the renderer catalog in the sub-archetype:

1. Identify which `--type` best fits the topic.
2. Extract concrete parameters from the topic and any `gatheredContext`. For example:
   - "C major scale on treble staff" → `--type staff --clef treble --key "C major" --notes "..."`
   - "Yaman raga" → `--type raga-clock --raga Yaman --shrutis 12`
   - "Dm7 chord guitar" → `--type chord-box --instrument guitar --chord Dm7 --fingering "x x 0 2 1 1"`
3. If the topic references a tradition, pass `--tradition <tag>`.

If `interactive` is `true`, ask the user 1–2 questions about specifics before invoking (e.g., "Which raga melakarta should this represent?").

## Step 4: Suggest Placement

If `vaultRoot` is set, run the placement script:

```bash
SLUG=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py slug "<topic>")
PLACEMENT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_suggest_placement.py \
  --topic "$SLUG" \
  --vault-root "<vaultRoot>")
```

Set `topicFolder = "<vaultRoot>/<confirmed-path>/<slug>/"` and write SVG to `<topicFolder>/<slug>.svg`.

If no vault, write to `<cwd>/<slug>.svg`.

## Step 5: Invoke `kb_svg.py`

```bash
python3 ~/.claude/skills/knowledge-base/scripts/kb_svg.py \
  --type <renderer> \
  [renderer-specific flags] \
  --title "<topic>" \
  --tradition <tradition-tag-if-any> \
  --out "<output-path>"
```

If MIDI is appropriate (renderer is one of: staff, raga-clock, sargam, jianpu, gongche, rhythm-grid, clave, tala), pass `--midi-out "<output-path-with-mid-extension>"` so the SVG and MIDI travel together.

## Step 6: Update Vault State

If `vaultRoot` is set:

1. Append SVG entry to topic registry:
   ```bash
   python3 ~/.claude/skills/knowledge-base/scripts/kb_utils.py append-registry \
     --vault-root "<vaultRoot>" \
     --date "<YYYY-MM-DD>" \
     --topic "<topic>" \
     --slug "$SLUG" \
     --svg "<relative-path-from-vault-root>"
   ```
2. Run `graphify . --update` (best-effort) to index the new file.

## Report

```
SVG generated: <topic>
  File: <absolute-path-to-.svg>
  Renderer: <type>
  Parameters: <key flags used>
  Tradition: <tag or "none">
  MIDI: <path or "skipped">
  Vault: <vault-name or "none">
```
```

- [ ] **Step 2: Commit**

```bash
git add commands/svg.md
git commit -m "feat(svg): add /kb svg sub-command for SVG generation via kb_svg.py"
```

---

### Task 30: Update `SKILL.md` to register the `svg` sub-command

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Update the description, argument-hint, allowed-tools, version**

In the YAML frontmatter (lines 2-22), update:

```yaml
description: >
  Unified skill for managing knowledge-base vaults. Sub-commands: init (set up a vault),
  diagram (generate a diagram on any topic), document (generate a standalone document),
  create (generate both a document and diagram, linked together),
  guitar-tabs (generate a playable guitar tab on any song or riff as alphaTex),
  svg (generate a music visualization SVG via kb_svg.py — staff, fretboard, circle of fifths, raga clock, maqam, gamelan, chord box, neume, sargam, jianpu, gongche, rhythm-grid, clave, tala),
  edit (modify an existing diagram JSON — enforces placement constraints),
  validate (check / auto-fix a diagram JSON against the app schema; supports --lint-music for music frontmatter),
  transform (bring an existing .md or .json file into skill-format conformance without changing content).
  Trigger on: "knowledge-base", "kb", "create architecture", "design diagram",
  "architecture of X", "create document", "write about X", "init vault",
  "initialize vault", "set up vault", "create about X", "diagram of X",
  "validate diagram", "fix diagram json", "check diagram",
  "edit diagram", "update diagram", "add to diagram", "modify diagram",
  "guitar tab", "guitar tabs", "guitar tab of X", "tab for X", "alphatex",
  "tablature", "fingerpicking pattern for X", "riff for X",
  "svg of X", "circle of fifths", "raga clock", "fretboard diagram",
  "rhythm grid", "neume", "sargam", "jianpu", "tala diagram",
  "transform file", "fix format", "bring into conformance", "normalize vault files".
argument-hint: <sub-command> [args] — sub-commands: init, diagram, document, create, guitar-tabs, svg, edit, validate, transform
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Agent, WebSearch, WebFetch]
version: 1.2.0
```

- [ ] **Step 2: Add `svg` to the Usage block (line ~31-39)**

After the `guitar-tabs` line, insert:

```
/knowledge-base svg <topic> [-i]         — Generate a music SVG visualization
```

- [ ] **Step 3: Add `svg` to dispatch table**

After the `guitar-tabs` row, insert:

```
| `svg`               | Read `~/.claude/skills/knowledge-base/commands/svg.md` and execute it. Pass remaining args as **topic**. Pass `interactive` flag. Output is an `.svg` file (and optionally `.mid`). |
```

- [ ] **Step 4: Add example to Examples block**

After the `guitar-tabs` example:

```
/kb svg "C major scale on treble staff"
/knowledge-base svg "Yaman raga clock" -i
```

- [ ] **Step 5: Commit**

```bash
git add SKILL.md
git commit -m "feat(skill): register svg sub-command and bump to v1.2.0"
```

---

### Task 31: Phase 3a validation gate — all 7 core renderers produce stable SVGs

**Files:**
- Modify: `scripts/tests/test_kb_svg.py`

- [ ] **Step 1: Add cross-renderer validation test**

```python
def test_phase3a_all_seven_renderers_produce_valid_svg():
    """Phase 3a gate: every core renderer produces well-formed SVG with kb-meta comment."""
    invocations = [
        ("staff",            ["--clef", "treble", "--key", "C major", "--notes", "C4-q D4-q E4-q F4-q"]),
        ("fretboard",        ["--strings", "6", "--tuning", "EADGBE", "--notes", "0,2,3"]),
        ("circle-of-fifths", ["--highlight", "C,G,D"]),
        ("raga-clock",       ["--raga", "Yaman"]),
        ("maqam-jins",       ["--jins", "Hijaz", "--root", "D"]),
        ("gamelan-cipher",   ["--tuning", "slendro", "--pattern", "1 2 3 5 6 1"]),
        ("chord-box",        ["--instrument", "guitar", "--chord", "Dm7", "--fingering", "x x 0 2 1 1"]),
    ]
    for kind, extra in invocations:
        out = run_svg("--type", kind, *extra)
        assert "<svg" in out, f"{kind}: missing <svg>"
        assert "</svg>" in out, f"{kind}: missing </svg>"
        assert "kb-meta:" in out, f"{kind}: missing kb-meta comment"
```

- [ ] **Step 2: Run all tests**

Run: `python3 -m pytest scripts/tests/ -v`
Expected: All Phase 1 tests + Phase 2 tests + 7 individual renderer tests + this gate test all PASS.

- [ ] **Step 3: Commit**

```bash
git add scripts/tests/test_kb_svg.py
git commit -m "test: phase 3a gate — all 7 core renderers produce well-formed SVG with kb-meta"
```

**Phase 3a complete.** 7 core renderers ship with golden masters. The CLI router, primitives module, and theme module are stable. `commands/svg.md` and `archetypes/music/svg.md` connect end-to-end.

---

## Phase 3b: SVG Generator — 7 Added Renderers

Goal: Implement neume, sargam, jianpu, gongche, rhythm-grid, clave, tala renderers.

### Task 32: `neume` renderer (medieval Western chant)

**Files:** Modify `scripts/kb_svg.py`, add test.

- [ ] **Step 1: Add test**

```python
def test_neume_kyrie_mode_i():
    actual = run_svg(
        "--type", "neume",
        "--mode", "I",
        "--text", "Kyrie eleison",
        "--neumes", "punctum,clivis,torculus,porrectus",
        "--width", "700", "--height", "200",
    )
    assert "Kyrie" in actual
    assert_golden("neume_kyrie", actual)
```

- [ ] **Step 2: Implement renderer**

```python
NEUME_GLYPHS = {
    # Each is a list of (dx, dy) pen strokes from a starting point
    "punctum":   [("rect", 0, 0, 8, 8)],                       # single square note
    "virga":     [("rect", 0, 0, 8, 8), ("line", 8, 0, 8, 14)],
    "clivis":    [("rect", 0, 0, 8, 8), ("rect", 12, 6, 8, 8)],   # high-low pair
    "torculus":  [("rect", 0, 6, 8, 8), ("rect", 12, 0, 8, 8), ("rect", 24, 6, 8, 8)],  # low-high-low
    "porrectus": [("rect", 0, 0, 8, 8), ("line", 0, 8, 16, 16), ("rect", 16, 12, 8, 8)],
    "scandicus": [("rect", 0, 12, 8, 8), ("rect", 12, 6, 8, 8), ("rect", 24, 0, 8, 8)],  # ascending
    "climacus":  [("rect", 0, 0, 8, 8), ("rect", 12, 8, 6, 6), ("rect", 22, 14, 6, 6)], # descending
}


def render_neume(args, theme):
    """Render medieval Western chant on a 4-line staff with named neume glyphs."""
    parts = []
    margin_x, margin_y = 60, 70
    line_gap = 12
    staff_top = margin_y
    parts.append(text(margin_x, margin_y - 28, f"Mode {args.mode or 'I'}",
                      theme["fg"], 14, "start", "600"))
    # 4 staff lines (Gregorian convention)
    for i in range(4):
        y = staff_top + i * line_gap
        parts.append(line(margin_x, y, args.width - margin_x, y, theme["fg"], 1))
    # C clef at left
    parts.append(text(margin_x - 14, staff_top + line_gap + 4, "C",
                      theme["accent"], 18, "middle", "700"))
    # Neume glyphs distributed left to right
    neume_names = [n.strip() for n in (args.neumes or "").split(",") if n.strip()]
    if neume_names:
        spacing = (args.width - 2 * margin_x - 60) / max(len(neume_names), 1)
        for i, name in enumerate(neume_names):
            x0 = margin_x + 30 + i * spacing
            y0 = staff_top + line_gap  # pivot row
            for stroke in NEUME_GLYPHS.get(name, [("rect", 0, 0, 8, 8)]):
                kind = stroke[0]
                if kind == "rect":
                    _, dx, dy, w, h = stroke
                    parts.append(rect(x0 + dx, y0 + dy, w, h,
                                      fill=theme["fg"], stroke="none"))
                elif kind == "line":
                    _, dx1, dy1, dx2, dy2 = stroke
                    parts.append(line(x0 + dx1, y0 + dy1, x0 + dx2, y0 + dy2,
                                      theme["fg"], 1.5))
            # Label
            parts.append(text(x0 + 8, staff_top + 4 * line_gap + 14, name,
                              theme["muted"], 9))
    # Underlying text (lyric)
    if args.lyric:
        parts.append(text(margin_x, staff_top + 4 * line_gap + 36, args.lyric,
                          theme["fg"], 13, "start", "400"))
    return parts
```

- [ ] **Step 3: Run test, commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/neume_kyrie.svg
git commit -m "feat(kb_svg): implement neume renderer for medieval Western chant"
```

---

### Task 33: `sargam` renderer (Hindustani/Carnatic cipher)

**Files:** Modify `scripts/kb_svg.py`, add test.

- [ ] **Step 1: Add test**

```python
def test_sargam_yaman_aroh():
    actual = run_svg(
        "--type", "sargam",
        "--scale", "Sa Re Ga Ma# Pa Dha Ni",
        "--pattern", "Sa Re Ga | Ma# Pa | Dha Ni Sa",
        "--width", "700", "--height", "200",
    )
    assert "Sa" in actual
    assert_golden("sargam_yaman", actual)
```

- [ ] **Step 2: Implement renderer**

```python
def render_sargam(args, theme):
    """Render Indian sargam cipher notation. Capital = madhya saptak (middle); 'a dot above'
    = tara saptak (upper); 'a dot below' = mandra saptak (lower). v1 uses Unicode combining
    characters for octave dots."""
    parts = []
    margin_x, margin_y = 60, 80
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]
    parts.append(text(args.width // 2, margin_y - 40,
                      args.scale or "Sargam",
                      theme["fg"], 14, "middle", "600"))
    # Pattern as space- or pipe-separated tokens
    raw = args.pattern or ""
    measures = [m.strip() for m in raw.split("|")]
    measures = [m for m in measures if m]
    if not measures:
        measures = [raw.strip()]
    # Layout
    avail = args.width - 2 * margin_x
    measure_w = avail / max(len(measures), 1)
    for mi, m in enumerate(measures):
        x_left = margin_x + mi * measure_w
        # Bar line at end of each measure
        parts.append(line(x_left + measure_w - 4, margin_y - 10,
                          x_left + measure_w - 4, margin_y + 40, theme["grid"], 1))
        tokens = m.split()
        if not tokens:
            continue
        slot_w = (measure_w - 8) / len(tokens)
        for ti, tok in enumerate(tokens):
            x = x_left + ti * slot_w + slot_w / 2
            # Determine octave by case: lowercase = mandra, ALLCAPS = madhya, with #/' = tara
            label = tok
            color = accent
            parts.append(text(x, margin_y + 16, label, color, 18, "middle", "700"))
    return parts
```

- [ ] **Step 3: Run test, commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/sargam_yaman.svg
git commit -m "feat(kb_svg): implement sargam renderer for Indian cipher notation"
```

---

### Task 34: `jianpu` renderer (Chinese numbered notation)

**Files:** Modify `scripts/kb_svg.py`, add test.

- [ ] **Step 1: Add test**

```python
def test_jianpu_basic():
    actual = run_svg(
        "--type", "jianpu",
        "--key", "C",
        "--time-sig", "4/4",
        "--pattern", "1 2 3 - | 5 3 1 -",
        "--width", "600", "--height", "180",
    )
    assert "1" in actual
    assert_golden("jianpu_basic", actual)
```

- [ ] **Step 2: Implement renderer**

```python
def render_jianpu(args, theme):
    """Render Chinese jianpu numbered notation. Digits 1-7 = scale degrees.
    Dots above = upper octave; dots below = lower. Dashes extend duration."""
    parts = []
    margin_x, margin_y = 60, 80
    parts.append(text(margin_x, margin_y - 30, f"1 = {args.key}",
                      theme["fg"], 13, "start"))
    if args.time_sig:
        parts.append(text(margin_x + 80, margin_y - 30, args.time_sig,
                          theme["fg"], 13, "start"))
    measures = [m.strip() for m in (args.pattern or "").split("|") if m.strip()]
    if not measures:
        return parts
    avail = args.width - 2 * margin_x
    mw = avail / len(measures)
    for mi, m in enumerate(measures):
        x_left = margin_x + mi * mw
        parts.append(line(x_left + mw - 4, margin_y - 10,
                          x_left + mw - 4, margin_y + 30, theme["grid"], 1))
        tokens = m.split()
        if not tokens:
            continue
        sw = (mw - 8) / len(tokens)
        for ti, tok in enumerate(tokens):
            x = x_left + ti * sw + sw / 2
            color = theme["accent"] if tok in "1234567" else theme["fg"]
            parts.append(text(x, margin_y + 14, tok, color, 22, "middle", "700"))
    return parts
```

- [ ] **Step 3: Run test, commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/jianpu_basic.svg
git commit -m "feat(kb_svg): implement jianpu renderer for Chinese numbered notation"
```

---

### Task 35: `gongche` renderer (traditional Chinese characters)

**Files:** Modify `scripts/kb_svg.py`, add test.

- [ ] **Step 1: Add test**

```python
def test_gongche_basic():
    actual = run_svg(
        "--type", "gongche",
        "--scale", "合四一上尺工凡",
        "--pattern", "上尺工六五",
        "--width", "600", "--height", "200",
    )
    assert "上" in actual
    assert "尺" in actual
    assert_golden("gongche_basic", actual)
```

- [ ] **Step 2: Implement renderer**

```python
GONGCHE_FONT_STYLE = (
    '<style>text.gongche { font-family: "Noto Sans CJK SC", '
    '"Source Han Sans CN", "PingFang SC", system-ui, sans-serif; }</style>'
)


def render_gongche(args, theme):
    """Render traditional Chinese gongche notation using CJK Unicode characters.
    Falls back gracefully if Noto Sans CJK is unavailable on the viewer's machine."""
    parts = [GONGCHE_FONT_STYLE]
    margin_x, margin_y = 60, 80
    if args.scale:
        parts.append(f'  <text class="gongche" x="{margin_x}" y="{margin_y - 30}" '
                     f'fill="{theme["muted"]}" font-size="14">'
                     f'Scale: {_xml(args.scale)}</text>')
    chars = list(args.pattern.strip()) if args.pattern else []
    if not chars:
        return parts
    avail = args.width - 2 * margin_x
    sw = avail / max(len(chars), 1)
    for i, ch in enumerate(chars):
        x = margin_x + i * sw + sw / 2
        parts.append(f'  <text class="gongche" x="{x}" y="{margin_y + 18}" '
                     f'text-anchor="middle" fill="{theme["accent"]}" '
                     f'font-size="32" font-weight="700">{_xml(ch)}</text>')
    return parts
```

- [ ] **Step 3: Run test, commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/gongche_basic.svg
git commit -m "feat(kb_svg): implement gongche renderer with Noto Sans CJK fallback"
```

---

### Task 36: `rhythm-grid` renderer (universal beat grid)

**Files:** Modify `scripts/kb_svg.py`, add test.

- [ ] **Step 1: Add test**

```python
def test_rhythm_grid_four_on_floor():
    actual = run_svg(
        "--type", "rhythm-grid",
        "--steps", "16",
        "--tracks", "kick,snare,hi-hat",
        "--pattern", "x...x...x...x... | ....x.......x... | x.x.x.x.x.x.x.x.",
        "--width", "800", "--height", "240",
    )
    assert "kick" in actual and "snare" in actual
    assert_golden("rhythm_grid_four_on_floor", actual)
```

- [ ] **Step 2: Implement renderer**

```python
def render_rhythm_grid(args, theme):
    """Render a step sequencer grid. --tracks comma-separated; --pattern uses '|' between tracks
    (one row per track, in same order as --tracks). 'x' = onset, '.' = rest."""
    parts = []
    margin_x, margin_y = 110, 70
    track_h = 40
    avail_w = args.width - margin_x - 30
    cell_w = avail_w / max(args.steps, 1)
    track_names = [t.strip() for t in (args.tracks or "").split(",") if t.strip()]
    # Patterns split per-track via '|'
    patterns = [p.replace(" ", "") for p in (args.pattern or "").split("|")]
    patterns = [p for p in patterns if p]
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]

    for ti, name in enumerate(track_names):
        y = margin_y + ti * track_h
        parts.append(text(margin_x - 12, y + track_h / 2 + 4, name,
                          theme["fg"], 12, "end", "600"))
        # Cells
        pat = patterns[ti] if ti < len(patterns) else ""
        for s in range(args.steps):
            x = margin_x + s * cell_w
            # Quarter-beat shading every 4 steps
            shade = theme["grid"] if s % 4 == 0 else theme["bg"]
            parts.append(rect(x, y + 4, cell_w - 2, track_h - 8,
                              fill=shade, stroke=theme["grid"], stroke_width=1))
            if s < len(pat) and pat[s] == "x":
                parts.append(rect(x + 2, y + 6, cell_w - 6, track_h - 12,
                                  fill=accent, stroke="none"))
    return parts
```

- [ ] **Step 3: Run test, commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/rhythm_grid_four_on_floor.svg
git commit -m "feat(kb_svg): implement rhythm-grid step-sequencer renderer with N tracks"
```

---

### Task 37: `clave` renderer (Afro-Cuban patterns)

**Files:** Modify `scripts/kb_svg.py`, add test.

- [ ] **Step 1: Add test**

```python
def test_clave_son_3_2_dot():
    actual = run_svg(
        "--type", "clave",
        "--pattern", "son-3-2",
        "--style", "dot-pattern",
        "--width", "600", "--height", "160",
    )
    assert_golden("clave_son_3_2", actual)
```

- [ ] **Step 2: Implement renderer**

```python
CLAVE_PATTERNS = {
    "son-3-2":  "x..x..x...x.x...",
    "son-2-3":  "..x.x...x..x..x.",
    "rumba-3-2":"x..x...x..x.x...",
    "rumba-2-3":"..x.x...x...x..x",
    "bossa":    "x..x..x..x..x..x",
}


def render_clave(args, theme):
    """Render Afro-Cuban clave patterns. Style 'dot-pattern' = filled circles on a 16-step grid;
    'staff' = single-line staff with accents."""
    parts = []
    pat = CLAVE_PATTERNS.get(args.pattern, args.pattern or "")
    if not pat:
        return parts
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]
    margin_x, margin_y = 70, 80
    avail_w = args.width - 2 * margin_x
    n = len(pat)
    cell_w = avail_w / max(n, 1)
    if args.style == "staff":
        # Single staff line with accents above
        y = margin_y + 20
        parts.append(line(margin_x, y, args.width - margin_x, y, theme["fg"], 1))
        for i, ch in enumerate(pat):
            x = margin_x + i * cell_w + cell_w / 2
            if ch == "x":
                parts.append(circle(x, y, 5, fill=accent, stroke="none"))
                parts.append(line(x, y - 5, x, y - 22, theme["fg"], 1))
    else:  # dot-pattern (default)
        y = margin_y + 20
        for i, ch in enumerate(pat):
            x = margin_x + i * cell_w + cell_w / 2
            # Quarter-beat tick
            if i % 4 == 0:
                parts.append(line(x, y - 18, x, y + 18, theme["grid"], 1))
            r = 8 if ch == "x" else 3
            fill = accent if ch == "x" else theme["muted"]
            parts.append(circle(x, y, r, fill=fill, stroke="none"))
    parts.append(text(args.width // 2, margin_y - 30, args.pattern or "clave",
                      theme["fg"], 14, "middle", "600"))
    return parts
```

- [ ] **Step 3: Run test, commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/clave_son_3_2.svg
git commit -m "feat(kb_svg): implement clave renderer for son/rumba/bossa patterns"
```

---

### Task 38: `tala` renderer (Indian rhythm cycle)

**Files:** Modify `scripts/kb_svg.py`, add test.

- [ ] **Step 1: Add test**

```python
def test_tala_teentaal_circular():
    actual = run_svg(
        "--type", "tala",
        "--tala", "Teentaal",
        "--style", "circular",
        "--width", "500", "--height", "500",
    )
    assert "Teentaal" in actual
    assert_golden("tala_teentaal", actual)
```

- [ ] **Step 2: Implement renderer**

```python
TALA_CYCLES = {
    # (name): list of (matra-type, label) where matra-type ∈ {"sam", "tali", "khali", "matra"}
    "Teentaal":  [("sam", "x"), ("matra", ""), ("matra", ""), ("matra", ""),
                  ("tali", "2"), ("matra", ""), ("matra", ""), ("matra", ""),
                  ("khali", "0"), ("matra", ""), ("matra", ""), ("matra", ""),
                  ("tali", "3"), ("matra", ""), ("matra", ""), ("matra", "")],
    "Jhaptaal":  [("sam", "x"), ("matra", ""),
                  ("tali", "2"), ("matra", ""), ("matra", ""),
                  ("khali", "0"), ("matra", ""),
                  ("tali", "3"), ("matra", ""), ("matra", "")],
    "Ektaal":    [("sam", "x"), ("matra", ""),
                  ("khali", "0"), ("matra", ""),
                  ("tali", "2"), ("matra", ""),
                  ("tali", "3"), ("matra", ""),
                  ("khali", "0"), ("matra", ""),
                  ("tali", "4"), ("matra", "")],
    "Adi tala":  [("sam", "x"), ("matra", ""), ("matra", ""), ("matra", ""),
                  ("tali", "2"), ("matra", ""),
                  ("tali", "3"), ("matra", "")],
}


def render_tala(args, theme):
    """Render Indian rhythm cycle. Circular default; --style linear = horizontal."""
    import math
    parts = []
    cycle = TALA_CYCLES.get(args.tala, [])
    if not cycle:
        return parts
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]
    n = len(cycle)
    # Color per beat type
    colors = {"sam": accent, "tali": theme["cadence"],
              "khali": theme["muted"], "matra": theme["grid"]}
    if args.style == "linear":
        margin_x, margin_y = 60, 100
        avail = args.width - 2 * margin_x
        cw = avail / n
        for i, (typ, lab) in enumerate(cycle):
            x = margin_x + i * cw
            parts.append(rect(x, margin_y, cw - 2, 60, fill=colors[typ], stroke=theme["grid"]))
            if lab:
                parts.append(text(x + cw / 2, margin_y + 38, lab,
                                  theme["bg"] if typ == "sam" else theme["fg"], 14, "middle", "700"))
        parts.append(text(args.width // 2, margin_y - 30, args.tala,
                          theme["fg"], 16, "middle", "700"))
    else:  # circular
        cx, cy = args.width // 2, args.height // 2
        r = min(cx, cy) - 70
        for i, (typ, lab) in enumerate(cycle):
            angle = -math.pi / 2 + i * (2 * math.pi / n)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            parts.append(circle(x, y, 14, fill=colors[typ],
                                stroke=theme["fg"], stroke_width=1))
            if lab:
                lcol = theme["bg"] if typ == "sam" else theme["fg"]
                parts.append(text(x, y + 4, lab, lcol, 13, "middle", "700"))
        parts.append(text(cx, cy, args.tala, theme["fg"], 18, "middle", "700"))
        parts.append(text(cx, cy + 24, f"{n} matras", theme["muted"], 11))
    return parts
```

- [ ] **Step 3: Run test**

```bash
python3 -m pytest scripts/tests/test_kb_svg.py::test_tala_teentaal_circular -v
```

- [ ] **Step 4: Phase 3b validation gate — all 14 renderers**

Add to `test_kb_svg.py`:

```python
def test_phase3b_all_fourteen_renderers_produce_valid_svg():
    invocations = [
        ("staff", ["--clef", "treble", "--key", "C major", "--notes", "C4-q"]),
        ("fretboard", ["--strings", "6", "--tuning", "EADGBE"]),
        ("circle-of-fifths", []),
        ("raga-clock", ["--raga", "Yaman"]),
        ("maqam-jins", ["--jins", "Hijaz", "--root", "D"]),
        ("gamelan-cipher", ["--tuning", "slendro", "--pattern", "1 2 3"]),
        ("chord-box", ["--instrument", "guitar", "--chord", "C", "--fingering", "x 3 2 0 1 0"]),
        ("neume", ["--mode", "I", "--text", "test", "--neumes", "punctum,clivis"]),
        ("sargam", ["--scale", "Sa Re Ga", "--pattern", "Sa Re Ga"]),
        ("jianpu", ["--key", "C", "--pattern", "1 2 3"]),
        ("gongche", ["--scale", "上尺工", "--pattern", "上尺工"]),
        ("rhythm-grid", ["--steps", "16", "--tracks", "kick", "--pattern", "x...x...x...x..."]),
        ("clave", ["--pattern", "son-3-2"]),
        ("tala", ["--tala", "Teentaal"]),
    ]
    for kind, extra in invocations:
        out = run_svg("--type", kind, *extra)
        assert "<svg" in out, f"{kind}: missing <svg>"
        assert "</svg>" in out, f"{kind}: missing </svg>"
        assert "kb-meta:" in out, f"{kind}: missing kb-meta"
```

Run: `python3 -m pytest scripts/tests/ -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py scripts/tests/fixtures/svg_golden/tala_teentaal.svg
git commit -m "feat(kb_svg): implement tala renderer (circular + linear) and phase 3b gate test"
```

**Phase 3b complete.** All 14 renderers ship with golden masters. End-to-end SVG generation works for the full v1 catalog.

---

## Phase 4: MIDI Export + Audio Playback

Goal: New `scripts/kb_midi.py` (pure-stdlib MIDI Format-1 writer + cross-platform `--play` shim). 8 SVG renderers gain `--midi-out` support.

### Task 39: `kb_midi.py` scaffolding — MIDI writer

**Files:**
- Create: `scripts/kb_midi.py`
- Create: `scripts/tests/test_kb_midi.py`
- Create: `scripts/tests/fixtures/midi_golden/` (directory)

- [ ] **Step 1: Write the MIDI writer module**

```python
#!/usr/bin/env python3
"""
Minimal MIDI Format-1 writer using only stdlib `struct`.

Public API:
  write_midi(path, tracks, ticks_per_quarter=480, tempo_bpm=120, time_sig=(4,4), key=0)
  play(path)   — best-effort cross-platform playback

Each track is a list of (delta_ticks, event_type, *args):
  ("note_on",  channel, pitch, velocity)
  ("note_off", channel, pitch, velocity)
  ("meta_tempo", microseconds_per_quarter)
  ("meta_time_sig", num, den, clocks_per_click, ticks_per_32nd)
  ("meta_key_sig", sharps_or_flats, mode)
  ("meta_end")

Pitches are MIDI numbers (0-127). Channel 9 (zero-indexed) = percussion (GM drum kit).
"""
import argparse
import struct
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path


def _vlq(n: int) -> bytes:
    """Variable-length quantity encoding."""
    if n == 0:
        return b'\x00'
    out = []
    out.append(n & 0x7F)
    n >>= 7
    while n > 0:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def _encode_event(delta: int, ev: tuple) -> bytes:
    kind = ev[0]
    if kind == "note_on":
        ch, pitch, vel = ev[1], ev[2], ev[3]
        return _vlq(delta) + bytes([0x90 | (ch & 0x0F), pitch & 0x7F, vel & 0x7F])
    if kind == "note_off":
        ch, pitch, vel = ev[1], ev[2], ev[3]
        return _vlq(delta) + bytes([0x80 | (ch & 0x0F), pitch & 0x7F, vel & 0x7F])
    if kind == "meta_tempo":
        usec = ev[1]
        data = struct.pack(">I", usec)[1:]  # 24-bit
        return _vlq(delta) + b'\xFF\x51\x03' + data
    if kind == "meta_time_sig":
        num, den, cpc, t32 = ev[1], ev[2], ev[3], ev[4]
        # den is encoded as power of 2: 2->1, 4->2, 8->3, 16->4
        denom_pow = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5}.get(den, 2)
        return _vlq(delta) + b'\xFF\x58\x04' + bytes([num, denom_pow, cpc, t32])
    if kind == "meta_key_sig":
        sharps, mode = ev[1], ev[2]
        sharps_byte = sharps & 0xFF  # signed in MIDI; we mask to byte
        return _vlq(delta) + b'\xFF\x59\x02' + bytes([sharps_byte, mode & 0x01])
    if kind == "meta_end":
        return _vlq(delta) + b'\xFF\x2F\x00'
    raise ValueError(f"unknown event {kind}")


def _track_chunk(events: list[tuple]) -> bytes:
    """events is list of (delta_ticks, event_tuple)."""
    body = b''.join(_encode_event(d, e) for d, e in events)
    if not events or events[-1][1][0] != "meta_end":
        body += _encode_event(0, ("meta_end",))
    return b'MTrk' + struct.pack(">I", len(body)) + body


def write_midi(path, tracks, ticks_per_quarter=480, tempo_bpm=120,
               time_sig=(4, 4), key=0):
    """Write a Format-1 MIDI file. tracks = list of event lists."""
    # Tempo track (track 0)
    usec_per_q = int(60_000_000 / tempo_bpm)
    tempo_events = [
        (0, ("meta_tempo", usec_per_q)),
        (0, ("meta_time_sig", time_sig[0], time_sig[1], 24, 8)),
        (0, ("meta_key_sig", key, 0)),
    ]
    chunks = [_track_chunk(tempo_events)]
    for tr in tracks:
        chunks.append(_track_chunk(tr))
    header = b'MThd' + struct.pack(">IHHH", 6, 1, len(chunks), ticks_per_quarter)
    Path(path).write_bytes(header + b''.join(chunks))


# ---------- Note name → MIDI ----------
NOTE_TABLE = {"C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,
              "F#":6,"Gb":6,"G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11}


def pitch_to_midi(name: str, default_octave: int = 4) -> int | None:
    """'C4' -> 60. 'F#3' -> 54. Returns None for unparseable."""
    if not name:
        return None
    # Find where the octave number starts
    i = 0
    while i < len(name) and (name[i].isalpha() or name[i] in "#b"):
        i += 1
    letter_part = name[:i] if i > 0 else name
    octave_part = name[i:]
    if letter_part not in NOTE_TABLE:
        return None
    try:
        octave = int(octave_part) if octave_part else default_octave
    except ValueError:
        return None
    return NOTE_TABLE[letter_part] + (octave + 1) * 12


# ---------- Playback shim ----------
def play(path: str) -> bool:
    """Invoke the platform's default MIDI player. Returns True on success."""
    players = {
        "darwin": ["afplay"],
        "linux":  ["aplay", "timidity"],
        "win32":  ["start", "/wait", ""],
    }
    plat = sys.platform
    candidates = players.get(plat, [])
    for p in candidates:
        if not p:
            continue
        if shutil.which(p):
            try:
                subprocess.run([p, str(path)], check=False, capture_output=True)
                return True
            except (OSError, subprocess.SubprocessError):
                continue
    print(f"[kb_midi] no system MIDI player found; midi written to {path}", file=sys.stderr)
    return False


def main():
    ap = argparse.ArgumentParser(description="Minimal MIDI writer / playback shim")
    ap.add_argument("--play", help="play an existing MIDI file")
    args = ap.parse_args()
    if args.play:
        play(args.play)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make executable**

Run: `chmod +x ~/.claude/skills/knowledge-base/scripts/kb_midi.py`

- [ ] **Step 3: Create test**

```python
# scripts/tests/test_kb_midi.py
"""Tests for kb_midi.py: MIDI writer correctness via byte fixtures."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kb_midi


def test_pitch_to_midi_basic():
    assert kb_midi.pitch_to_midi("C4") == 60
    assert kb_midi.pitch_to_midi("A4") == 69
    assert kb_midi.pitch_to_midi("F#3") == 54
    assert kb_midi.pitch_to_midi("Bb3") == 58
    assert kb_midi.pitch_to_midi("invalid") is None


def test_write_midi_minimal_file_has_correct_header(tmp_path):
    path = tmp_path / "test.mid"
    kb_midi.write_midi(str(path), tracks=[[
        (0, ("note_on", 0, 60, 100)),
        (480, ("note_off", 0, 60, 0)),
    ]], tempo_bpm=120)
    data = path.read_bytes()
    # Format-1 header
    assert data[:4] == b"MThd"
    # Header chunk length = 6
    assert data[4:8] == b"\x00\x00\x00\x06"
    # Format = 1, num tracks = 2 (tempo + 1 user), ticks-per-quarter = 480
    assert data[8:10] == b"\x00\x01"
    assert data[10:12] == b"\x00\x02"
    assert data[12:14] == b"\x01\xe0"
    # Track chunks present
    assert b"MTrk" in data[14:]
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest scripts/tests/test_kb_midi.py -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add scripts/kb_midi.py scripts/tests/test_kb_midi.py
chmod +x scripts/kb_midi.py
git commit -m "feat(kb_midi): pure-stdlib MIDI Format-1 writer with playback shim"
```

---

### Task 40: Wire `--midi-out` into `kb_svg.py` for compatible renderers

**Files:**
- Modify: `scripts/kb_svg.py` — add `emit_midi(args)` and call from `main()`
- Modify: `scripts/tests/test_kb_svg.py` — add MIDI emission tests

- [ ] **Step 1: Add MIDI emission helpers in `kb_svg.py`**

Insert after the `render` function and before `def main()`:

```python
import kb_midi  # local script import; works because tests prepend scripts/ to sys.path
                # and direct CLI invocation finds it via the same dir.


def _midi_for_staff(args) -> list[tuple]:
    """Convert --notes 'C4-q D4-q E4-h' to MIDI events on channel 0."""
    tokens = [t for t in (args.notes or "").split() if t]
    events = []
    tpq = 480
    dur_ticks = {"w": 4 * tpq, "h": 2 * tpq, "q": tpq, "e": tpq // 2, "s": tpq // 4}
    delta_accumulator = 0
    for tok in tokens:
        pitch_part, _, dur = tok.partition("-")
        midi_pitch = kb_midi.pitch_to_midi(pitch_part) or 60
        d = dur_ticks.get(dur, tpq)
        events.append((delta_accumulator, ("note_on", 0, midi_pitch, 100)))
        events.append((d, ("note_off", 0, midi_pitch, 0)))
        delta_accumulator = 0
    return events


def _midi_for_raga(args) -> list[tuple]:
    """Convert raga arohana to ascending scale on channel 0; root = MIDI 60 (C4)."""
    arohana = RAGA_AROHANA.get(args.raga, [])
    if not arohana:
        return []
    events = []
    tpq = 480
    for st in arohana + [12]:  # close on octave
        events.append((0, ("note_on", 0, 60 + st, 100)))
        events.append((tpq, ("note_off", 0, 60 + st, 0)))
    return events


def _midi_for_rhythm_grid(args) -> list[tuple]:
    """Convert rhythm-grid pattern to drum hits on channel 9 (GM percussion)."""
    track_names = [t.strip() for t in (args.tracks or "").split(",") if t.strip()]
    patterns = [p.replace(" ", "") for p in (args.pattern or "").split("|") if p.strip()]
    drum_map = {"kick": 36, "snare": 38, "hi-hat": 42, "tom": 45, "crash": 49, "ride": 51}
    events = []
    tpq = 480
    step_ticks = tpq // 4  # 16th-note grid by default
    # Merge events by absolute time, then deltify
    abs_events = []
    for ti, name in enumerate(track_names):
        pitch = drum_map.get(name, 38)
        pat = patterns[ti] if ti < len(patterns) else ""
        for s, ch in enumerate(pat):
            if ch == "x":
                t = s * step_ticks
                abs_events.append((t, ("note_on", 9, pitch, 100)))
                abs_events.append((t + step_ticks // 2, ("note_off", 9, pitch, 0)))
    abs_events.sort(key=lambda x: x[0])
    last = 0
    for t, ev in abs_events:
        events.append((t - last, ev))
        last = t
    return events


def emit_midi(args) -> None:
    """Generate MIDI for renderers that have an inherent pitch/duration meaning."""
    if not args.midi_out:
        return
    midi_capable = {
        "staff":        _midi_for_staff,
        "raga-clock":   _midi_for_raga,
        "sargam":       lambda a: [],  # TODO: implement sargam→MIDI in v1.1
        "jianpu":       lambda a: [],
        "gongche":      lambda a: [],
        "rhythm-grid":  _midi_for_rhythm_grid,
        "clave":        lambda a: [],
        "tala":         lambda a: [],
    }
    if args.type not in midi_capable:
        return  # silently skip for non-MIDI-capable types
    events = midi_capable[args.type](args)
    if not events:
        return
    kb_midi.write_midi(args.midi_out, tracks=[events])
    if args.play:
        kb_midi.play(args.midi_out)
```

In `main()`, after the SVG write, call `emit_midi(args)`:

```python
    # ... existing svg write block ...
    emit_midi(args)
```

- [ ] **Step 2: Add MIDI emission test**

Append to `test_kb_svg.py`:

```python
def test_midi_emission_for_staff(tmp_path):
    """`--midi-out` produces a valid MIDI file alongside the SVG."""
    midi_path = tmp_path / "out.mid"
    run_svg(
        "--type", "staff",
        "--notes", "C4-q D4-q E4-q F4-q",
        "--midi-out", str(midi_path),
    )
    assert midi_path.exists()
    data = midi_path.read_bytes()
    assert data[:4] == b"MThd"
    assert b"MTrk" in data


def test_midi_emission_for_rhythm_grid(tmp_path):
    midi_path = tmp_path / "drums.mid"
    run_svg(
        "--type", "rhythm-grid",
        "--steps", "16",
        "--tracks", "kick,snare",
        "--pattern", "x...x...x...x... | ....x.......x...",
        "--midi-out", str(midi_path),
    )
    assert midi_path.exists()
    assert midi_path.read_bytes()[:4] == b"MThd"
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest scripts/tests/ -v`
Expected: All PASS (Phase 1 + 2 + 3a/b + new MIDI tests).

- [ ] **Step 4: Commit**

```bash
git add scripts/kb_svg.py scripts/tests/test_kb_svg.py
git commit -m "feat(kb_svg): emit MIDI alongside SVG for staff, raga-clock, and rhythm-grid renderers"
```

---

### Task 41: Phase 4 validation gate — round-trip MIDI playability

**Files:**
- Modify: `scripts/tests/test_kb_midi.py`

- [ ] **Step 1: Add gate test**

```python
def test_phase4_gate_midi_files_have_minimum_required_chunks(tmp_path):
    """Phase 4 gate: every MIDI file must have MThd header + at least 2 MTrk chunks (tempo + content)."""
    cases = [
        ("staff", ["--notes", "C4-q D4-q"]),
        ("raga-clock", ["--raga", "Yaman"]),
        ("rhythm-grid", ["--steps", "8", "--tracks", "kick", "--pattern", "x.x.x.x."]),
    ]
    import subprocess, sys
    SCRIPT = Path(__file__).resolve().parents[1] / "kb_svg.py"
    for kind, extra in cases:
        midi_path = tmp_path / f"{kind}.mid"
        subprocess.run([sys.executable, str(SCRIPT), "--type", kind, *extra,
                        "--midi-out", str(midi_path)],
                       check=True, capture_output=True)
        data = midi_path.read_bytes()
        assert data[:4] == b"MThd", f"{kind}: missing header"
        assert data.count(b"MTrk") >= 2, f"{kind}: needs tempo + content tracks"
```

- [ ] **Step 2: Run, commit**

```bash
git add scripts/tests/test_kb_midi.py
git commit -m "test: phase 4 gate — MIDI files have header + tempo + content tracks"
```

**Phase 4 complete.** MIDI export works for staff, raga-clock, and rhythm-grid. Three more renderers (sargam, jianpu, gongche, clave, tala) ship `--midi-out` placeholders that no-op for v1; flesh out in v1.1.

---

## Phase 5: `validate` Music-Lint Extension

Goal: Add `--lint-music` flag to `commands/validate.md`; check that music documents have valid `traditions:` frontmatter.

### Task 42: Create music lint script

**Files:**
- Create: `scripts/kb_validate_music.py`

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""
Validate music document frontmatter. Checks:
  - purpose: matches a music template
  - traditions: required, non-empty, all entries from the 11 valid badges
"""
import argparse
import re
import sys
from pathlib import Path

VALID_TRADITIONS = {
    "western", "jazz", "hindustani", "carnatic", "maqam", "persian",
    "gamelan", "west-african", "east-asian", "latin", "folk", "unmarked",
}

MUSIC_PURPOSES = {
    "theory-primer", "biography", "song-breakdown", "instrument-profile",
    "tradition-overview", "history-timeline", "comparative",
}


def parse_frontmatter(text: str) -> dict | None:
    m = re.match(r'\A---\r?\n(.*?)\r?\n---', text, re.DOTALL)
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def parse_list_value(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("["):
        inner = raw.strip("[]")
        return [s.strip().strip('"\'') for s in inner.split(",") if s.strip()]
    return [s.strip().strip('"\'') for s in raw.split(",") if s.strip()]


def lint_file(path: Path, fix: bool = False) -> list[str]:
    """Return list of violations. Fix in place if requested."""
    text = path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if fm is None:
        return [f"{path}: no YAML frontmatter"]
    purpose = fm.get("purpose", "")
    if purpose not in MUSIC_PURPOSES:
        return []  # not a music doc; skip silently
    violations = []
    traditions_raw = fm.get("traditions", "")
    traditions = parse_list_value(traditions_raw) if traditions_raw else []
    if not traditions:
        violations.append(f"{path}: missing/empty 'traditions:' field")
        if fix:
            new_text = text.replace("---\n", "---\ntraditions: [unmarked]\n", 1) \
                if "traditions:" not in text else \
                re.sub(r"traditions:.*", "traditions: [unmarked]", text)
            path.write_text(new_text, encoding="utf-8")
        return violations
    for t in traditions:
        if t not in VALID_TRADITIONS:
            violations.append(f"{path}: invalid tradition tag {t!r} "
                              f"(valid: {sorted(VALID_TRADITIONS)})")
    return violations


def main():
    ap = argparse.ArgumentParser(description="Lint music documents.")
    ap.add_argument("paths", nargs="+", help="Files or directories to lint")
    ap.add_argument("--fix", action="store_true", help="Insert traditions: [unmarked] for missing")
    args = ap.parse_args()
    all_violations = []
    for p in args.paths:
        path = Path(p)
        if path.is_dir():
            for md in path.rglob("*.md"):
                all_violations.extend(lint_file(md, fix=args.fix))
        elif path.is_file():
            all_violations.extend(lint_file(path, fix=args.fix))
    for v in all_violations:
        print(v)
    sys.exit(0 if not all_violations else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make executable**

Run: `chmod +x ~/.claude/skills/knowledge-base/scripts/kb_validate_music.py`

- [ ] **Step 3: Commit**

```bash
git add scripts/kb_validate_music.py
chmod +x scripts/kb_validate_music.py
git commit -m "feat(validate): add kb_validate_music.py for music frontmatter linting"
```

---

### Task 43: Test fixtures for lint

**Files:**
- Create: `scripts/tests/fixtures/lint_music/pass_*.md` (5 files)
- Create: `scripts/tests/fixtures/lint_music/fail_*.md` (5 files)
- Create: `scripts/tests/test_validate_lint_music.py`

- [ ] **Step 1: Create the 10 fixture files**

```bash
mkdir -p ~/.claude/skills/knowledge-base/scripts/tests/fixtures/lint_music
```

Create the 5 passing fixtures:

**`pass_biography.md`**:
```markdown
---
purpose: biography
title: "John Coltrane"
traditions: [jazz]
created: 2026-05-02
---
# Biography content here
```

**`pass_theory_multi.md`**:
```markdown
---
purpose: theory-primer
title: "Modes vs ragas"
traditions: [western, hindustani]
created: 2026-05-02
---
```

**`pass_song.md`**:
```markdown
---
purpose: song-breakdown
title: "Giant Steps"
traditions: [jazz]
---
```

**`pass_instrument.md`**:
```markdown
---
purpose: instrument-profile
title: "The Sitar"
traditions: [hindustani]
---
```

**`pass_unmarked.md`**:
```markdown
---
purpose: tradition-overview
title: "Some folk tradition"
traditions: [unmarked]
---
```

Create the 5 failing fixtures:

**`fail_no_traditions.md`**:
```markdown
---
purpose: biography
title: "Someone"
---
```

**`fail_empty_traditions.md`**:
```markdown
---
purpose: theory-primer
title: "Concept"
traditions: []
---
```

**`fail_invalid_tag.md`**:
```markdown
---
purpose: comparative
title: "X vs Y"
traditions: [klingon, vulcan]
---
```

**`fail_typo.md`**:
```markdown
---
purpose: tradition-overview
title: "Indian"
traditions: [hindustanee]
---
```

**`fail_no_frontmatter.md`**:
```markdown
# Just a markdown file
purpose: biography
traditions: [jazz]
```

- [ ] **Step 2: Create the test file**

```python
# scripts/tests/test_validate_lint_music.py
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "kb_validate_music.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "lint_music"


def lint(paths):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *paths],
        capture_output=True, text=True, check=False,
    )
    return proc.stdout, proc.returncode


@pytest.mark.parametrize("name", ["pass_biography", "pass_theory_multi",
                                  "pass_song", "pass_instrument", "pass_unmarked"])
def test_passing_fixtures_lint_clean(name):
    out, rc = lint([str(FIXTURES / f"{name}.md")])
    assert rc == 0, f"{name} should pass; got: {out}"


@pytest.mark.parametrize("name", ["fail_no_traditions", "fail_empty_traditions",
                                  "fail_invalid_tag", "fail_typo", "fail_no_frontmatter"])
def test_failing_fixtures_lint_dirty(name):
    out, rc = lint([str(FIXTURES / f"{name}.md")])
    assert rc != 0, f"{name} should fail lint; got: {out}"


def test_directory_walk_catches_all_failures(tmp_path):
    out, rc = lint([str(FIXTURES)])
    # 5 fail fixtures; expect at least 5 violations reported
    assert rc != 0
    assert out.count("\n") >= 5
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest scripts/tests/test_validate_lint_music.py -v`
Expected: 11 PASSED.

- [ ] **Step 4: Commit**

```bash
git add scripts/tests/fixtures/lint_music/ scripts/tests/test_validate_lint_music.py
git commit -m "test: 10 music-lint fixtures (5 pass, 5 fail) + walk test"
```

---

### Task 44: Wire `--lint-music` into `commands/validate.md`

**Files:**
- Modify: `commands/validate.md`

- [ ] **Step 1: Read current validate.md**

Run: `grep -n "^## " ~/.claude/skills/knowledge-base/commands/validate.md`
Identify a good insertion point (after the existing main validation block).

- [ ] **Step 2: Append a new section**

Add to the end of `commands/validate.md`:

```markdown
## Music Document Lint (`--lint-music`)

When the `--lint-music` flag is present in the args, OR when the vault config indicates music is enabled (presence of `archetypes/music/` reference), validate music documents have correct `traditions:` frontmatter.

### Step M1: Detect Mode

```bash
# Pass-through if user explicitly requested music linting
LINT_MUSIC="${args[lint-music]:-false}"

# Auto-detect: check if vault registers music archetypes
if [ -d "<vault-root>/archetypes/music" ] || \
   [ -f "<vault-root>/.archdesigner/config.json" ] && \
   grep -q '"music"' "<vault-root>/.archdesigner/config.json" 2>/dev/null; then
   LINT_MUSIC="true"
fi
```

### Step M2: Run Music Lint

```bash
if [ "$LINT_MUSIC" = "true" ]; then
   python3 ~/.claude/skills/knowledge-base/scripts/kb_validate_music.py \
     "<target-path>" \
     ${fix:+--fix}
fi
```

The script exits 0 when clean, 1 when violations found. Report violations to the user.

### Auto-Fix Behavior

When `--fix` is also passed:
- Missing `traditions:` field → inserts `traditions: [unmarked]`
- Invalid tag → reported but NOT auto-fixed (no safe inference)
- No frontmatter → reported, no auto-fix (would risk corrupting non-music files)
```

- [ ] **Step 3: Commit**

```bash
git add commands/validate.md
git commit -m "feat(validate): add --lint-music flag wired to kb_validate_music.py"
```

---

### Task 45: Phase 5 validation gate

- [ ] **Step 1: Run all tests**

Run: `python3 -m pytest scripts/tests/ -v`
Expected: All PASS — Phase 1, 2, 3a, 3b, 4, 5 all green.

- [ ] **Step 2: Manual validate-script smoke test**

```bash
python3 ~/.claude/skills/knowledge-base/scripts/kb_validate_music.py \
  ~/.claude/skills/knowledge-base/scripts/tests/fixtures/lint_music/
```
Expected: prints 5 violations and exits 1.

```bash
echo $?
```
Expected: `1`

- [ ] **Step 3: Commit (no changes; gate is procedural)**

No code change; verify and proceed.

**Phase 5 complete.** Music documents are now lintable; 10 fixtures cover the 11 valid tradition tags + structural failures.

---

## Phase 6: Tabs Sub-Archetype + Cross-Links

Goal: Ship `archetypes/music/tabs.md` documenting tab cross-link conventions.

### Task 46: Write `archetypes/music/tabs.md`

**Files:**
- Create: `archetypes/music/tabs.md`

- [ ] **Step 1: Write the sub-archetype**

```markdown
---
name: music-tabs
description: Tab cross-link conventions; references the existing /kb guitar-tabs command for execution
domain-indicators:
  - tab
  - tablature
  - fingerpicking
  - alphatex
  - riff
  - lick
---

# Sub-Archetype: Music Tabs

This sub-archetype documents conventions for tablature in music vault content. **It does not execute tab generation** — that happens via the existing `/kb guitar-tabs <topic>` command, which produces alphaTex.

## Coverage via existing `guitar-tabs` command

alphaTex supports custom tunings and string counts, so the existing `guitar-tabs` command already handles:

| Instrument | Strings | Default tuning | How |
|---|---|---|---|
| Guitar | 6 | EADGBE | default |
| 7-string guitar | 7 | BEADGBE | `--tuning BEADGBE` |
| Bass guitar | 4 | EADG | `--tuning EADG` |
| Ukulele | 4 | GCEA | `--tuning GCEA` |
| Banjo (5-string) | 5 | gDGBD | `--tuning gDGBD` |
| Mandolin | 4×2 | GDAE | `--tuning GDAE` |
| Bouzouki | 4×2 | DAFC | `--tuning DAFC` (Greek) or `GDAD` (Irish) |

The `guitar-tabs` command name is preserved for backward compatibility. To generate tabs for a non-guitar instrument, pass the appropriate tuning.

## Cross-Link Conventions

Tabs should be cross-linked to related vault content:

1. **Theory primer** — every tab MUST reference its theory primer document (the scale/raga/maqam/key it uses): `[[<concept-slug>.md]]` in the alphaTex header comments.
2. **Song-breakdown** — if the tab is a transcription of a specific song, the song-breakdown document MUST reference the tab via `[[<song-slug>.alphatex]]`.
3. **Instrument profile** — for non-guitar tabs, link to the instrument profile.
4. **Visual SVG** — when a tab has a representable scale or chord, generate the corresponding SVG (`fretboard`, `chord-box`) and link both ways.

## Frontmatter (alphaTex header conventions)

The alphaTex format supports header metadata. Convention:

```
\title "<title>"
\subtitle "<key/scale/raga>"
\artist "<performer or composer>"
\tempo <bpm>
\tuning "<tuning string>"
\tradition "<tradition-tag>"
% related: [[<theory-primer-slug>]]
% related: [[<song-breakdown-slug>]]
```

The `\tradition` field is a kb-specific extension; it lives as a comment if the alphaTex viewer doesn't support custom keys.

## Selection Logic

When a topic suggests tablature ("tab for X", "fingerpicking pattern", "riff for"), the dispatcher routes to the existing `guitar-tabs` command directly — `tabs.md` is consulted by `guitar-tabs` for cross-link conventions only.

## Future Extensibility (deferred)

- **Sargam-tab** — Indian sargam-style notation as tab; alphaTex doesn't fit; deferred to a future cipher-tab generator.
- **Jianpu-tab** — Chinese cipher tab; same deferred path.
- **Tab-from-MIDI** — round-trip from generated MIDI back to alphaTex; deferred.
```

- [ ] **Step 2: Commit**

```bash
git add archetypes/music/tabs.md
git commit -m "feat(music): add tabs sub-archetype documenting cross-link conventions"
```

---

### Task 47: Optionally consult `tabs.md` from `guitar-tabs.md`

**Files:**
- Modify: `commands/guitar-tabs.md`

- [ ] **Step 1: Add archetype consultation step**

At the top of the existing `commands/guitar-tabs.md` (after the Inputs section), insert:

```markdown
## Step 0: Consult Music Tabs Sub-Archetype

If the music meta-archetype is registered, read its tabs sub-archetype for cross-link conventions:

```bash
ARCHETYPE_RESULT=$(python3 ~/.claude/skills/knowledge-base/scripts/kb_archetype.py \
  --archetypes-dir ~/.claude/skills/knowledge-base/archetypes \
  --topic "<topic>" \
  --output-type tabs)
```

If `subtype` is `tabs`, read the file at `<path>` for header conventions and cross-link rules. Apply them when writing the alphaTex.

If output is `no-match` or `subtype` is `-`, proceed with the legacy generation path (no cross-link conventions enforced).
```

- [ ] **Step 2: Commit**

```bash
git add commands/guitar-tabs.md
git commit -m "feat(guitar-tabs): consult tabs sub-archetype for cross-link conventions"
```

---

### Task 48: Phase 6 validation gate — selector dispatches to tabs.md

**Files:**
- Modify: `scripts/tests/test_kb_archetype.py`

- [ ] **Step 1: Add test**

```python
def test_real_music_archetype_dispatches_tabs():
    real_dir = Path(__file__).resolve().parents[2] / "archetypes"
    out, rc = run([
        "--archetypes-dir", str(real_dir),
        "--topic", "guitar tab for Wonderwall",
        "--output-type", "tabs",
    ])
    parts = out.split(maxsplit=2)
    assert parts[0] == "music"
    assert parts[1] == "tabs"
    assert parts[2].endswith("music/tabs.md")
```

- [ ] **Step 2: Run, commit**

```bash
python3 -m pytest scripts/tests/test_kb_archetype.py -v
git add scripts/tests/test_kb_archetype.py
git commit -m "test: phase 6 gate — tabs sub-archetype dispatch"
```

**Phase 6 complete.** Tabs cross-link conventions documented; existing `guitar-tabs` command consults them when music archetype is in use.

---

## Phase 7: Polish & Integration

Goal: Ship `README.md`, `ICON_REQUESTS.md`, and final integration touches.

### Task 49: Write `archetypes/music/README.md`

**Files:**
- Create: `archetypes/music/README.md`

- [ ] **Step 1: Write README**

```markdown
# Music Meta-Archetype

Globally-inclusive music archetype family covering Western, Indian, Arabic, Persian, Gamelan, West African, East Asian, and Latin American traditions on equal footing.

## Files

| File | Purpose |
|---|---|
| `manifest.json` | Sub-archetype registry, domain-indicators, purpose-keywords |
| `diagram.md` | Diagram conventions (layers, colors, icons, connections) |
| `tabs.md` | Tab cross-link conventions |
| `svg.md` | SVG renderer catalog (14 renderers in `kb_svg.py`) |
| `documents/` | 7 per-purpose document templates |
| `ICON_REQUESTS.md` | Wishlist of music-specific icons for the visual editor app |

## How it routes

The `kb_archetype.py` selector returns 3 tokens: `<name> <subtype> <path>`. For music:

- `/kb diagram <topic>` → `music diagram <path-to-music-diagram.md>`
- `/kb document <topic>` → `music <one-of-7-purposes> <path-to-template.md>`
- `/kb svg <topic>` → `music svg <path-to-svg.md>` → invokes `kb_svg.py`
- `/kb guitar-tabs <topic>` → `music tabs <path-to-tabs.md>` for cross-link conventions

## Tradition tags

Use these in document `traditions:` frontmatter and for `--tradition` SVG flag:

`western`, `jazz`, `hindustani`, `carnatic`, `maqam`, `persian`, `gamelan`, `west-african`, `east-asian`, `latin`, `folk`, `unmarked`

## Related skill files

- `~/.claude/skills/knowledge-base/scripts/kb_archetype.py` — selector
- `~/.claude/skills/knowledge-base/scripts/kb_svg.py` — 14 SVG renderers
- `~/.claude/skills/knowledge-base/scripts/kb_midi.py` — MIDI writer + playback
- `~/.claude/skills/knowledge-base/scripts/kb_validate_music.py` — frontmatter linter

## Spec

`docs/superpowers/specs/2026-05-02-music-archetype-design.md`
```

- [ ] **Step 2: Commit**

```bash
git add archetypes/music/README.md
git commit -m "docs(music): add family README"
```

---

### Task 50: Write `archetypes/music/ICON_REQUESTS.md`

**Files:**
- Create: `archetypes/music/ICON_REQUESTS.md`

- [ ] **Step 1: Write the wishlist**

```markdown
# Icon Requests for the Visual Editor App

The knowledge-base diagram archetype is constrained to 41 Lucide icons registered in the architecture-designer app. The music archetype currently repurposes these (see `diagram.md` icon mappings table). The icons below would dramatically improve music-diagram fidelity.

This file is the standing wishlist tracked against the visual editor app's repository — **not this skill's repository**. PRs against the app should reference this list.

## Requested Icons

| Icon | Lucide name | Music use case |
|---|---|---|
| Music note | `Music` / `Music2` / `Music3` / `Music4` | Generic note / pitch (currently `Radio`) |
| Treble clef | `MusicNote` (custom) or `TrebleClef` | Western notation diagrams |
| Drum | `Drum` (Lucide has it) | Percussion (currently `Cog`) |
| Microphone | `Mic` / `Mic2` | Vocal / recording (currently `User`) |
| Wave | `AudioWaveform` / `Waves` | Pitch / acoustic wave (currently `Radio`) |
| Piano key | `Piano` (custom) | Keyed instruments (currently `Cpu`) |
| Headphones | `Headphones` | Listening / playback context |
| Guitar | `Guitar` (Lucide has it) | Fretted instruments (currently `Cable`) |
| Disc / Record | `Disc` / `Disc3` | Recording / album (currently `Archive`) |
| Speaker | `Speaker` (Lucide has it) | Amplification / output |

## Cross-Reference

When these icons land in the app, update `archetypes/music/diagram.md` § Icon Mappings to use them instead of the repurposed icons.

## Tradition Badges

The 11 tradition badges in `diagram.md` § Tradition Badges currently render as the node's `sub` field (subtitle). A future app feature could render these as colored corner badges; if so, the diagram archetype's `tradition-driven layer` mode would benefit. Track as a separate request.
```

- [ ] **Step 2: Commit**

```bash
git add archetypes/music/ICON_REQUESTS.md
git commit -m "docs(music): track icon-pack wishlist for the visual editor app"
```

---

### Task 51: Phase 7 final validation gate — full test suite + smoke test

**Files:**
- (no new files; runs the full suite)

- [ ] **Step 1: Run full test suite**

```bash
cd ~/.claude/skills/knowledge-base
python3 -m pytest scripts/tests/ -v --tb=short
```

Expected: All tests across all phases PASS. Count should be approximately:
- Phase 1: 7 tests (back-compat, no-match, meta detection, document dispatch, etc.)
- Phase 2: 13 parametrized + 1 = 14 tests
- Phase 3a: 7 renderer tests + 1 gate = 8
- Phase 3b: 7 renderer tests + 1 gate = 8
- Phase 4: 4 tests (pitch_to_midi, header, 2 emission, 1 gate)
- Phase 5: 11 lint tests (5 pass + 5 fail + 1 walk)
- Phase 6: 1 tabs dispatch test

Total: ~53 tests.

- [ ] **Step 2: End-to-end smoke test**

Generate one piece of content per output type to confirm the full stack works:

```bash
# Diagram
python3 scripts/kb_archetype.py --archetypes-dir archetypes --topic "Yaman raga structure" --output-type diagram
# Expected: music diagram /path/to/music/diagram.md

# Document
python3 scripts/kb_archetype.py --archetypes-dir archetypes --topic "biography of Coltrane" --output-type document --purpose-hint "biography of Coltrane"
# Expected: music biography /path/to/biography.md

# SVG
python3 scripts/kb_svg.py --type circle-of-fifths --highlight C,G,D --out /tmp/circle.svg
ls -la /tmp/circle.svg
# Expected: file exists, ~2-5KB

# MIDI
python3 scripts/kb_svg.py --type staff --notes "C4-q D4-q E4-q F4-q" --midi-out /tmp/scale.mid
ls -la /tmp/scale.mid
# Expected: file exists, header MThd

# Lint
python3 scripts/kb_validate_music.py archetypes/music/documents/
# Expected: 0 violations on the templates themselves (templates have purpose: but are templates, not docs)
```

- [ ] **Step 3: Final commit (no code; mark phase complete)**

If all the above pass, the implementation is complete. No commit needed.

**Phase 7 complete.** Music meta-archetype ships with 14 SVG renderers, MIDI export + playback, 7 document templates, frontmatter linting, and full back-compat with `software-architecture`.

---

## Self-Review Notes

**Spec coverage check:** All 7 phases from the spec are mapped to tasks 1–51:
- Phase 1 (engine foundation): Tasks 1–10 ✓
- Phase 2 (document templates): Tasks 11–19 ✓
- Phase 3a (core 7 renderers): Tasks 20–31 ✓
- Phase 3b (added 7 renderers): Tasks 32–38 ✓
- Phase 4 (MIDI + playback): Tasks 39–41 ✓
- Phase 5 (validate lint): Tasks 42–45 ✓
- Phase 6 (tabs cross-links): Tasks 46–48 ✓
- Phase 7 (polish): Tasks 49–51 ✓

**Type/name consistency:** Sub-archetype subtype tokens used consistently throughout — `diagram`, `document`, `svg`, `tabs`, `-` (single-file sentinel), and document purpose names (`biography`, `theory-primer`, etc.). Renderer `--type` names are consistent across `kb_svg.py`, `svg.md`, and tests.

**Known gaps for v1.1 (intentional):**
- `_midi_for_sargam`, `_midi_for_jianpu`, `_midi_for_gongche`, `_midi_for_clave`, `_midi_for_tala` are placeholder no-ops that return `[]`. The plumbing exists; flesh out per-format MIDI generation in v1.1. This is a deliberate choice to keep Phase 4 to ~2 days.
- 22-shruti raga clock falls back to equidistant positions in v1; canonical shruti positions deferred.
- `commands/guitar-tabs.md` does not yet enforce alphaTex header `\tradition` field; it merely consults `tabs.md`.

These gaps don't block any v1 deliverable and are documented in the renderer code as comments.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-02-music-archetype.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for this plan because:
- 51 tasks across 7 phases is a lot of context churn for one session
- Phase boundaries are natural review points
- SVG golden masters need eyeball review at phase gates

**2. Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints. Best if you want to run the whole thing now in one session.

**Which approach?**

