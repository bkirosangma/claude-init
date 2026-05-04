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
        "accent":      "#3b82f6",
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
    "western":      "#2563eb",
    "jazz":         "#7c3aed",
    "hindustani":   "#dc2626",
    "carnatic":     "#ea580c",
    "maqam":        "#059669",
    "persian":      "#0891b2",
    "gamelan":      "#a16207",
    "west-african": "#16a34a",
    "east-asian":   "#9333ea",
    "latin":        "#e11d48",
    "folk":         "#475569",
}

# ---------- PRIMITIVES ----------
def svg_open(width: int, height: int, theme: dict, title: str = "") -> list[str]:
    """Open SVG document with XML header, root element, background, optional title."""
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
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


RAGA_AROHANA = {
    "Yaman":     [0, 2, 4, 6, 7, 9, 11],
    "Bhairav":   [0, 1, 4, 5, 7, 8, 11],
    "Bhairavi":  [0, 1, 3, 5, 7, 8, 10],
    "Yaman Kalyan": [0, 2, 4, 5, 6, 7, 9, 11],
    "Marwa":     [0, 1, 4, 6, 9, 11],
    "Bilawal":   [0, 2, 4, 5, 7, 9, 11],
    "Khamaj":    [0, 2, 4, 5, 7, 9, 10],
    "Kafi":      [0, 2, 3, 5, 7, 9, 10],
    "Asavari":   [0, 2, 3, 5, 7, 8, 10],
    "Todi":      [0, 1, 3, 6, 7, 8, 11],
    "Purvi":     [0, 1, 4, 6, 7, 8, 11],
}

SWARA_LABELS = ["Sa", "re", "Re", "ga", "Ga", "Ma", "Ma#", "Pa", "dha", "Dha", "ni", "Ni"]

JINS_INTERVALS = {
    "Rast":    [0, 200, 350, 500],
    "Bayati":  [0, 150, 350, 500],
    "Hijaz":   [0, 100, 400, 500],
    "Saba":    [0, 150, 300, 400],
    "Kurd":    [0, 100, 300, 500],
    "Ajam":    [0, 200, 400, 500],
    "Nahawand":[0, 200, 300, 500],
    "Sikah":   [0, 150, 350],
}


def render_staff(args, theme):
    """Render a single-line Western staff with notes. Notes format: 'C4-q D4-q E4-h ...'.
    Suffixes: -w whole, -h half, -q quarter, -e eighth, -s sixteenth."""
    parts = []
    margin_x, margin_y = 60, 80
    staff_height = 40
    line_gap = staff_height // 4
    staff_top = margin_y
    width_avail = args.width - 2 * margin_x

    for i in range(5):
        y = staff_top + i * line_gap
        parts.append(line(margin_x, y, args.width - margin_x, y, theme["fg"], 1))

    clef_label = {"treble": "G", "bass": "F", "alto": "C", "tenor": "C"}.get(args.clef, "G")
    parts.append(text(margin_x - 30, staff_top + line_gap * 2 + 5, clef_label,
                      theme["accent"], size=24, weight="700"))

    if args.time_sig and "/" in args.time_sig:
        num, den = args.time_sig.split("/", 1)
        parts.append(text(margin_x + 6, staff_top + line_gap + 5, num, theme["fg"], 14, "start", "700"))
        parts.append(text(margin_x + 6, staff_top + line_gap * 3 + 5, den, theme["fg"], 14, "start", "700"))

    if args.notes:
        tokens = [t for t in args.notes.split() if t]
        if tokens:
            x_step = (width_avail - 40) // max(len(tokens), 1)
            for i, tok in enumerate(tokens):
                pitch_part, _, dur = tok.partition("-")
                cx = margin_x + 40 + i * x_step
                cy = _staff_y(pitch_part, args.clef, staff_top, line_gap)
                fill = theme["fg"] if dur in ("q", "e", "s") else "none"
                parts.append(circle(cx, cy, 5, fill=fill, stroke=theme["fg"], stroke_width=1.5))
                if dur != "w":
                    stem_top = cy - 30
                    parts.append(line(cx + 5, cy, cx + 5, stem_top, theme["fg"], 1.5))
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
    rest = pitch_part[1:].lstrip("#b")
    try:
        octave = int(rest) if rest else 4
    except ValueError:
        octave = 4
    diatonic = "CDEFGAB".index(letter)
    semitones_from_e4 = (octave - 4) * 7 + (diatonic - 2)
    half_gap = line_gap // 2
    return staff_top + 4 * line_gap - semitones_from_e4 * half_gap


def render_fretboard(args, theme):
    """Render a fretboard with N strings, custom tuning, optional fret highlights."""
    parts = []
    margin_x, margin_y = 70, 70
    fret_count = 12
    fb_width = args.width - 2 * margin_x
    string_gap = 24
    fb_height = (args.strings - 1) * string_gap
    fb_top = margin_y
    fb_left = margin_x
    fret_gap = fb_width / fret_count

    if "," in args.tuning:
        tuning = [t.strip() for t in args.tuning.split(",")]
    else:
        tuning = list(args.tuning)
    tuning = (tuning + ["?"] * args.strings)[: args.strings]

    for i in range(args.strings):
        y = fb_top + i * string_gap
        parts.append(line(fb_left, y, fb_left + fb_width, y, theme["fg"], 1.5))
        parts.append(text(fb_left - 10, y + 4, tuning[args.strings - 1 - i],
                          theme["muted"], 12, "end"))

    for f in range(fret_count + 1):
        x = fb_left + f * fret_gap
        stroke_w = 3 if f == 0 else 1
        parts.append(line(x, fb_top, x, fb_top + fb_height, theme["fg"], stroke_w))

    dot_y = fb_top + fb_height + 16
    for fret in (3, 5, 7, 9):
        cx = fb_left + (fret - 0.5) * fret_gap
        parts.append(circle(cx, dot_y, 3, fill=theme["muted"], stroke="none"))
    cx12 = fb_left + 11.5 * fret_gap
    parts.append(circle(cx12 - 5, dot_y, 3, fill=theme["muted"], stroke="none"))
    parts.append(circle(cx12 + 5, dot_y, 3, fill=theme["muted"], stroke="none"))

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


def render_circle_of_fifths(args, theme):
    """Render the Western circle of fifths. --highlight: comma-separated key names."""
    import math
    parts = []
    cx, cy = args.width // 2, args.height // 2
    outer_r = min(cx, cy) - 60
    inner_r = outer_r - 60
    majors = ["C", "G", "D", "A", "E", "B", "F#", "C#", "G#", "D#", "A#", "F"]
    minors = ["a", "e", "b", "f#", "c#", "g#", "d#", "a#", "f", "c", "g", "d"]
    highlights = {h.strip() for h in (args.highlight or "").split(",") if h.strip()}
    parts.append(circle(cx, cy, outer_r, fill="none", stroke=theme["grid"], stroke_width=1))
    parts.append(circle(cx, cy, inner_r, fill="none", stroke=theme["grid"], stroke_width=1))
    for i, (M, m) in enumerate(zip(majors, minors)):
        angle = -math.pi / 2 + i * (2 * math.pi / 12)
        Mx = cx + outer_r * math.cos(angle)
        My = cy + outer_r * math.sin(angle)
        mx = cx + inner_r * math.cos(angle)
        my = cy + inner_r * math.sin(angle)
        Mcolor = theme["accent"] if M in highlights else theme["fg"]
        parts.append(text(Mx, My + 5, M, Mcolor, 18, "middle", "700"))
        parts.append(text(mx, my + 4, m, theme["muted"], 12))
        parts.append(line(cx + (inner_r - 6) * math.cos(angle),
                          cy + (inner_r - 6) * math.sin(angle),
                          cx + (outer_r - 18) * math.cos(angle),
                          cy + (outer_r - 18) * math.sin(angle),
                          theme["grid"], 1))
    return parts


def render_raga_clock(args, theme):
    """12-pitch or 22-shruti circle showing raga arohana. Sa at 12 o'clock."""
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


def render_maqam_jins(args, theme):
    """Render an Arabic jins as a horizontal cents-axis with quartertone-aware notation."""
    parts = []
    margin_x, margin_y = 60, 100
    axis_y = margin_y + 60
    width_avail = args.width - 2 * margin_x
    intervals = JINS_INTERVALS.get(args.jins, [0, 200, 400, 500])
    max_cents = max(intervals)
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]

    parts.append(line(margin_x, axis_y, args.width - margin_x, axis_y, theme["fg"], 1.5))
    for c in range(0, max_cents + 1, 100):
        x = margin_x + (c / max_cents) * width_avail
        parts.append(line(x, axis_y - 6, x, axis_y + 6, theme["grid"], 1))
        if args.show_cents:
            parts.append(text(x, axis_y + 22, f"{c}c", theme["muted"], 9))

    pitch_names = _maqam_pitch_names(args.root, intervals)
    for c, label in zip(intervals, pitch_names):
        x = margin_x + (c / max_cents) * width_avail
        parts.append(circle(x, axis_y, 7, fill=accent, stroke=theme["bg"], stroke_width=2))
        parts.append(text(x, axis_y - 18, label, theme["fg"], 13, "middle", "700"))

    for c1, c2 in zip(intervals, intervals[1:]):
        x1 = margin_x + (c1 / max_cents) * width_avail
        x2 = margin_x + (c2 / max_cents) * width_avail
        parts.append(line(x1, axis_y - 30, x2, axis_y - 30, accent, 1))

    parts.append(text(args.width // 2, margin_y, f"Jins {args.jins}",
                      theme["fg"], 16, "middle", "700"))
    return parts


def _maqam_pitch_names(root: str, intervals_cents: list[int]) -> list[str]:
    """Return pitch names for each interval."""
    semitones_per_step = [round(c / 100) for c in intervals_cents]
    base_idx = "CDEFGAB".index(root[0].upper()) if root and root[0].upper() in "CDEFGAB" else 1
    notes = "CDEFGAB"
    out = []
    for c, st in zip(intervals_cents, semitones_per_step):
        diat_step = round(st * 7 / 12)
        idx = (base_idx + diat_step) % 7
        accidental = ""
        if c % 100 != 0:
            if c % 100 == 50:
                accidental = "+" if c > st * 100 else "d"
        out.append(notes[idx] + accidental)
    return out


def render_gamelan_cipher(args, theme):
    """Render Javanese/Balinese cipher notation. Slendro = 5-note; pelog = 7-note."""
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
        parts.append(line(margin_x + i * cell_w, margin_y + 20,
                          margin_x + i * cell_w, margin_y + 80, theme["grid"], 1))
        parts.append(text(x, margin_y + 56, tok, col, 28, "middle", "700"))
    parts.append(line(margin_x + len(tokens) * cell_w, margin_y + 20,
                      margin_x + len(tokens) * cell_w, margin_y + 80, theme["fg"], 2))
    return parts


def render_chord_box(args, theme):
    """Render a chord block diagram. Fingering: 'x x 0 2 1 1' (low to high string)."""
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

    if args.chord:
        parts.append(text(box_left + box_w // 2, margin_y - 20, args.chord,
                          theme["fg"], 18, "middle", "700"))

    for s in range(n_strings):
        x = box_left + s * string_gap
        parts.append(line(x, box_top, x, box_top + box_h, theme["fg"], 1))
    for f in range(n_frets + 1):
        y = box_top + f * fret_gap
        sw = 3 if f == 0 else 1
        parts.append(line(box_left, y, box_left + box_w, y, theme["fg"], sw))

    if args.fingering:
        accent = theme["accent"]
        if args.tradition and args.tradition in TRADITION_BADGE:
            accent = TRADITION_BADGE[args.tradition]
        tokens = args.fingering.strip().split()
        tokens = (tokens + [" "] * n_strings)[: n_strings]
        for s, tok in enumerate(tokens):
            x = box_left + s * string_gap
            if tok == "x":
                parts.append(text(x, box_top - 5, "x", theme["muted"], 14))
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


def render_neume(args, theme):
    """Render Gregorian-style 4-line staff with square neume note heads."""
    parts = []
    margin_x, margin_y = 60, 80
    line_gap = 12
    n_lines = 4
    staff_top = margin_y
    width_avail = args.width - 2 * margin_x

    for i in range(n_lines):
        y = staff_top + i * line_gap
        parts.append(line(margin_x, y, args.width - margin_x, y, theme["fg"], 1))

    if args.mode:
        parts.append(text(margin_x, args.height - 20, f"Mode {args.mode}",
                          theme["muted"], 11, "start"))

    neume_tokens = [t for t in (args.neumes or "").split() if t]
    lyric_tokens = [t for t in (args.lyric or "").split("-") if t]

    if neume_tokens:
        x_step = width_avail // max(len(neume_tokens), 1)
        for i, tok in enumerate(neume_tokens):
            cx = margin_x + i * x_step + x_step // 2
            row = 1 + (i % 3)
            cy = staff_top + row * line_gap - 4
            parts.append(rect(cx - 4, cy - 4, 8, 8, fill=theme["fg"], stroke="none"))
            if i < len(lyric_tokens):
                parts.append(text(cx, staff_top + n_lines * line_gap + 18,
                                  lyric_tokens[i], theme["muted"], 11))
    return parts


def render_sargam(args, theme):
    """Render Indian sargam notation row with swara syllables."""
    parts = []
    margin_x, margin_y = 40, 80
    width_avail = args.width - 2 * margin_x
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]

    tokens = [t for t in (args.notes or "").split() if t]
    if not tokens:
        return parts

    cell_w = width_avail // max(len(tokens), 1)
    komal = {"re", "ga", "dha", "ni"}
    tivra = {"ma#", "ma+"}

    for i, tok in enumerate(tokens):
        cx = margin_x + i * cell_w + cell_w // 2
        cy = margin_y + 20
        low = tok.lower()
        if low in tivra:
            col = theme["tension"]
        elif low in komal:
            col = theme["harmonic"]
        else:
            col = accent
        parts.append(rect(margin_x + i * cell_w + 2, cy - 18, cell_w - 4, 30,
                          fill="none", stroke=theme["grid"], stroke_width=1))
        parts.append(text(cx, cy + 6, tok, col, 15, "middle", "700"))

    lyric_tokens = [t for t in (args.lyric or "").split("-") if t]
    if lyric_tokens:
        for i, syl in enumerate(lyric_tokens[:len(tokens)]):
            cx = margin_x + i * cell_w + cell_w // 2
            parts.append(text(cx, margin_y + 60, syl, theme["muted"], 11))
    return parts


def render_jianpu(args, theme):
    """Render Chinese jianpu (numbered notation) row."""
    parts = []
    margin_x, margin_y = 50, 80
    width_avail = args.width - 2 * margin_x
    accent = theme["accent"]

    if args.key:
        parts.append(text(margin_x, margin_y - 30, _xml(args.key),
                          theme["fg"], 13, "start", "600"))
    if args.time_sig:
        parts.append(text(margin_x + 60, margin_y - 30, args.time_sig,
                          theme["muted"], 12, "start"))

    tokens = [t for t in (args.notes or "").split() if t]
    if not tokens:
        return parts

    cell_w = width_avail // max(len(tokens), 1)
    for i, tok in enumerate(tokens):
        cx = margin_x + i * cell_w + cell_w // 2
        cy = margin_y + 20
        if tok == "-":
            parts.append(line(cx - 8, cy, cx + 8, cy, theme["muted"], 2))
        elif tok == "0":
            parts.append(text(cx, cy + 5, "0", theme["muted"], 22, "middle", "400"))
        else:
            parts.append(text(cx, cy + 8, tok, accent, 24, "middle", "700"))
    return parts


def render_gongche(args, theme):
    """Render traditional Chinese gongche character notation."""
    parts = []
    margin_x, margin_y = 50, 80
    width_avail = args.width - 2 * margin_x

    tokens = [t for t in (args.notes or "").split() if t]
    if not tokens:
        return parts

    cell_w = width_avail // max(len(tokens), 1)
    for i, tok in enumerate(tokens):
        cx = margin_x + i * cell_w + cell_w // 2
        cy = margin_y + 28
        if i > 0:
            parts.append(line(margin_x + i * cell_w, margin_y,
                              margin_x + i * cell_w, margin_y + 60,
                              theme["grid"], 1))
        parts.append(text(cx, cy, _xml(tok), theme["fg"], 22, "middle", "400"))

    if args.style:
        parts.append(text(args.width // 2, args.height - 20, _xml(args.style),
                          theme["muted"], 11))
    return parts


def render_rhythm_grid(args, theme):
    """Render a polyrhythm step-sequencer grid."""
    parts = []
    margin_x, margin_y = 80, 60
    steps = args.steps or 16
    cell_w = (args.width - 2 * margin_x) // max(steps, 1)
    cell_h = 24
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]

    raw_tracks = [t for t in (args.tracks or "").split(";") if t.strip()]
    if not raw_tracks:
        raw_tracks = [f"Track 1:{'.' * steps}"]

    for row, track_def in enumerate(raw_tracks):
        name, _, pattern = track_def.partition(":")
        name = name.strip()[:10]
        y_top = margin_y + row * (cell_h + 6)
        parts.append(text(margin_x - 6, y_top + cell_h // 2 + 5,
                          name, theme["muted"], 10, "end"))
        for step in range(steps):
            x = margin_x + step * cell_w
            beat_char = pattern[step] if step < len(pattern) else "."
            fill = accent if beat_char == "x" else theme["bg"]
            parts.append(rect(x + 1, y_top, cell_w - 2, cell_h,
                              fill=fill, stroke=theme["grid"], stroke_width=1))
            if step % 4 == 0:
                parts.append(line(x, y_top - 4, x, y_top,
                                  theme["structural"], 1))
    return parts


def render_clave(args, theme):
    """Render an Afro-Cuban clave pattern as a linear circle row."""
    parts = []
    margin_x, margin_y = 50, 120
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]

    raw = (args.pattern or "1 0 0 1 0 0 1 0 1 0 0 0 1 0 0 0").split()
    beats = [t.strip() for t in raw if t.strip()]
    if not beats:
        return parts

    n = len(beats)
    width_avail = args.width - 2 * margin_x
    step = width_avail / max(n, 1)

    for i, b in enumerate(beats):
        cx = margin_x + i * step + step / 2
        cy = margin_y
        if b == "1":
            parts.append(circle(cx, cy, 10, fill=accent, stroke=theme["bg"], stroke_width=2))
        else:
            parts.append(circle(cx, cy, 8, fill="none", stroke=theme["muted"], stroke_width=1.5))
        if i % 4 == 0:
            parts.append(line(cx, cy + 14, cx, cy + 22, theme["structural"], 1))

    if args.style:
        parts.append(text(args.width // 2, margin_y + 50, _xml(args.style),
                          theme["muted"], 12))
    return parts


def render_tala(args, theme):
    """Render an Indian tala cycle as a circular beat wheel."""
    import math
    TALAS = {
        "teentaal":  (16, [4, 4, 4, 4]),
        "ektaal":    (12, [2, 2, 2, 2, 2, 2]),
        "jhaptaal":  (10, [2, 3, 2, 3]),
        "rupak":     (7,  [3, 2, 2]),
        "keherwa":   (8,  [4, 4]),
        "dadra":     (6,  [3, 3]),
    }
    parts = []
    cx, cy = args.width // 2, args.height // 2
    r = min(cx, cy) - 60
    accent = theme["accent"]
    if args.tradition and args.tradition in TRADITION_BADGE:
        accent = TRADITION_BADGE[args.tradition]

    tala_key = (args.tala or "").lower().replace("-", "").replace(" ", "")
    n_beats, vibhaga = TALAS.get(tala_key, (8, [4, 4]))

    parts.append(circle(cx, cy, r, fill="none", stroke=theme["grid"], stroke_width=1))

    cumulative = 0
    for vib_len in vibhaga:
        angle = -math.pi / 2 + cumulative * (2 * math.pi / n_beats)
        parts.append(line(cx, cy,
                          cx + r * math.cos(angle),
                          cy + r * math.sin(angle),
                          theme["structural"], 1.5))
        cumulative += vib_len

    for beat in range(n_beats):
        angle = -math.pi / 2 + beat * (2 * math.pi / n_beats)
        bx = cx + r * math.cos(angle)
        by = cy + r * math.sin(angle)
        if beat == 0:
            parts.append(circle(bx, by, 10, fill=accent, stroke=theme["bg"], stroke_width=2))
            parts.append(text(bx, by + 4, "X", theme["bg"], 12, "middle", "700"))
        else:
            parts.append(circle(bx, by, 6, fill=theme["fg"], stroke="none"))
            parts.append(text(bx, by - 12, str(beat + 1), theme["muted"], 9))

    if args.tala:
        parts.append(text(cx, cy + 5, _xml(args.tala.title()), theme["fg"], 16, "middle", "700"))
    return parts


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

    if args.midi_out and args.notes:
        _export_midi(args)


def _export_midi(args: argparse.Namespace) -> None:
    """Export MIDI for renderers that carry note data (staff, sargam, jianpu)."""
    try:
        from kb_midi import MidiFile, notes_to_track, write_midi, play_midi
    except ImportError:
        _midi_dir = Path(__file__).resolve().parent
        sys.path.insert(0, str(_midi_dir))
        from kb_midi import MidiFile, notes_to_track, write_midi, play_midi  # type: ignore

    MIDI_RENDERERS = {"staff", "sargam", "jianpu", "fretboard", "chord-box",
                      "raga-clock", "gamelan-cipher"}
    if args.type not in MIDI_RENDERERS:
        return

    tpb = 480
    mf = MidiFile(ticks_per_beat=tpb, bpm=120)
    track = notes_to_track(args.notes, tpb)
    mf.add_track(track)
    write_midi(mf, args.midi_out)
    if args.play:
        play_midi(args.midi_out)


if __name__ == "__main__":
    main()
