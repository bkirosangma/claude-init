# Icon Requests

Icons missing from the [Lucide icon set](https://lucide.dev) that would be useful for music knowledge-base diagrams. These are queued for potential contribution or workaround tracking.

The music archetype's `diagram.md` limits icon choices to Lucide's available set. Where a concept has no good Lucide match, we use a workaround fallback and note the gap here.

---

## Pending Requests

### 1. Staff / Clef Symbol

**Concept:** Western music staff with treble or bass clef.
**Current workaround:** Using `Music` (generic note icon) or `FileText`.
**Ideal icon:** A treble clef glyph, or a 5-line staff snippet.
**Priority:** High — used for any Western notation node.

---

### 2. Sitar / Oud / Lute Shape

**Concept:** Long-necked plucked string instrument (Indian / Arabic / Medieval).
**Current workaround:** Using `Guitar` (electric body shape) which does not convey the instrument family.
**Ideal icon:** A silhouette with a round or pear-shaped body and long neck.
**Priority:** Medium — used in Hindustani, Carnatic, Maqam tradition diagrams.

---

### 3. Tabla / Mridangam (Double-sided drum)

**Concept:** South Asian pair-drum or barrel drum.
**Current workaround:** Using `Drum` (single Western snare shape).
**Ideal icon:** Two drum shapes side by side, or a barrel/hourglass drum.
**Priority:** Medium — used in tala and rhythm-related diagrams.

---

### 4. Ney / Bansuri (End-blown flute)

**Concept:** An end-blown flute, held at an angle rather than horizontally.
**Current workaround:** Using `Wind` or no icon (text label only).
**Ideal icon:** A diagonal tube with finger holes and a slanted blow-end.
**Priority:** Low — niche, but valuable for maqam and Carnatic wind node differentiation.

---

### 5. Shruti Box / Harmonium (Bellows keyboard)

**Concept:** A small bellows-driven keyboard used as a drone instrument.
**Current workaround:** Using `Piano` (grand piano icon — wrong family).
**Ideal icon:** A small rectangular keyboard with a bellows hinge on one side.
**Priority:** Low — used in drone-layer nodes in Hindustani diagrams.

---

### 6. Gamelan Gong

**Concept:** A large hanging bronze gong (used in Javanese/Balinese diagrams).
**Current workaround:** Using `Circle` with a label.
**Ideal icon:** A circular gong hanging from a frame or a boss-gong top-down view.
**Priority:** Medium — central instrument in gamelan tradition diagrams.

---

### 7. Score / Staff Paper

**Concept:** Sheet music / manuscript paper (multiple staves on a page).
**Current workaround:** Using `FileMusic` or `BookOpen`.
**Ideal icon:** A page with horizontal staff lines drawn on it.
**Priority:** Low — used as a "score" node in music-theory diagrams.

---

### 8. Quartertone / Microtone Accidental

**Concept:** The half-flat (𝄳) or half-sharp (𝄲) accidental symbol.
**Current workaround:** Text label with "½♭" or annotation only; no icon.
**Ideal icon:** A half-flat or half-sharp glyph.
**Priority:** High for maqam diagrams — these are distinct pitch nodes.

---

## Resolved (found workaround)

| Concept | Workaround used | Notes |
|---------|----------------|-------|
| Piano / keyboard | `Piano` | Available in Lucide — acceptable |
| Guitar (electric) | `Guitar` | Available — used for all fretted strings |
| Microphone | `Mic` | Available — used for vocalist nodes |
| Metronome | `Timer` | Acceptable proxy — no metronome icon exists |
| Vinyl / Record | `Disc` | Available — used for recording nodes |
| Speaker | `Speaker` | Available — used for output / amplification nodes |
| Sheet music | `Music` | Single note glyph — minimal but functional |
| Headphones | `Headphones` | Available — used for listening / perception nodes |
| Radio waves | `Radio` | Available — used for broadcast / transmission nodes |
| Waveform | `Activity` | Zigzag line — reasonable proxy for audio waveform |

---

## How to file a Lucide request

1. Check [lucide.dev/icons](https://lucide.dev/icons) to confirm the icon is truly missing.
2. Open an issue at [github.com/lucide-icons/lucide](https://github.com/lucide-icons/lucide/issues) with the label `icon request`.
3. Attach an SVG sketch if possible — requests with visuals are prioritised.
4. Update this file: move the entry from "Pending" to "Resolved" once the icon ships in a Lucide release and is available in the app's icon set.
