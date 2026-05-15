#!/usr/bin/env python3
"""
Transform a knowledge-base .md or .json file into skill-format conformance.
Content is preserved; only format, syntax, and structural links are adjusted.

Usage:
  kb_transform.py <path-or-glob> [--dry-run] [--add-conventions]

What changes (default):
  .md  — <span data-wiki-link="X">Y</span>  →  [[X]]
  .md  — YAML frontmatter title promoted to H1 (when missing).
  .md  — frontmatter `sources:` rewritten to canonical block-list form when
         it was authored as the inline `sources: [{...}]` shape (the project
         parser only round-trips block-list).
  .md  — frontmatter is preserved when (and only when) it carries a non-empty
         `sources:` field; otherwise the entire frontmatter is stripped
         (legacy `title:`-only frontmatter goes away).
  .json — delegates to kb_validate.py --fix

With --add-conventions (additive):
  .md  — adds missing "Visual overview: [[slug.json]]" after H1
  .md  — adds missing "## Related" section if body wiki-links exist

What never changes:
  Prose, section order, heading hierarchy, file location, node coordinates,
  flow definitions, or --- horizontal rules inside the document body.
"""

import argparse
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_utils import backup_file

SCRIPTS_DIR = Path(__file__).parent

# Matches: <span data-wiki-link="path/to/file.md" class="wiki-link">any text</span>
SPAN_RE = re.compile(
    r'<span\s+data-wiki-link="([^"]+)"[^>]*>.*?</span>',
    re.IGNORECASE | re.DOTALL,
)

# A frontmatter block is ONLY valid when it starts on the very first line of the file.
# Pattern: starts with ---, then key:value lines, then closing ---
FRONTMATTER_RE = re.compile(r'\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)', re.DOTALL)

# Inline `sources:` line — the form the project's TS frontmatter parser
# (src/.../document/utils/frontmatter.ts) explicitly does NOT support and
# silently drops. We rewrite to block-list form on transform.
INLINE_SOURCES_RE = re.compile(r'^sources\s*:\s*\[(.*)\]\s*$', re.MULTILINE)
# Block `sources:` opener — value is empty, list items follow on indented lines.
BLOCK_SOURCES_OPENER_RE = re.compile(r'^sources\s*:\s*$', re.MULTILINE)
RE_HTTP_URL = re.compile(r'^https?://', re.IGNORECASE)


def _quote_yaml_scalar(s: str) -> str:
    """Quote a YAML scalar with the same conservative rules as the project's
    TS serializer: always emit a double-quoted string with backslash-escaped
    quotes/backslashes. Keeps the parser-side decoder happy and avoids
    ambiguity with bare-word special chars (`:`, `#`, etc.)."""
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _extract_sources_from_frontmatter(fm_body: str) -> tuple[list[dict], bool]:
    """Pull a `sources:` array out of frontmatter, regardless of inline vs
    block form. Returns `(sources, was_inline)`. Empty list when no sources
    field is present or when every entry has an invalid URL.

    Inline form: `sources: [{url: "...", title: "..."}, {url: "..."}]`
    Block form:
      sources:
        - url: "..."
          title: "..."
        - url: "..."

    Title is optional and dropped when blank (matches the TS serializer).
    """
    inline_match = INLINE_SOURCES_RE.search(fm_body)
    if inline_match:
        items = _parse_inline_objects(inline_match.group(1))
        return ([s for s in items if isinstance(s.get('url'), str) and RE_HTTP_URL.match(s['url'].strip())], True)

    block_match = BLOCK_SOURCES_OPENER_RE.search(fm_body)
    if block_match:
        # Walk indented lines following the opener until the indent breaks.
        lines = fm_body.splitlines()
        opener_idx = None
        for i, line in enumerate(lines):
            if line.strip() == 'sources:' or re.match(r'^sources\s*:\s*$', line):
                opener_idx = i
                break
        if opener_idx is None:
            return ([], False)
        block: list[str] = []
        i = opener_idx + 1
        while i < len(lines):
            line = lines[i]
            if line.strip() == '' or line.startswith(' ') or line.startswith('\t'):
                block.append(line)
                i += 1
            else:
                break
        return (_parse_block_sources(block), False)

    return ([], False)


def _parse_inline_objects(payload: str) -> list[dict]:
    """Tokenise the contents of an inline `[{...}, {...}]` payload into a
    list of dicts. Handles the limited subset the project actually emits:
    `{key: "value", key: "value"}` with quoted-string values only. Anything
    we can't parse is silently skipped — the validator already warns about
    inline form being unsupported."""
    out: list[dict] = []
    depth = 0
    current = ''
    in_string = False
    escape_next = False
    for ch in payload:
        if escape_next:
            current += ch
            escape_next = False
            continue
        if in_string:
            current += ch
            if ch == '\\':
                escape_next = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            current += ch
            continue
        if ch == '{':
            depth += 1
            if depth == 1:
                current = ''
                continue
        if ch == '}':
            depth -= 1
            if depth == 0:
                obj = _parse_inline_object_body(current)
                if obj is not None:
                    out.append(obj)
                current = ''
                continue
        if depth >= 1:
            current += ch
    return out


def _parse_inline_object_body(body: str) -> dict | None:
    """Parse the inside of one `{key: "value", key: "value"}` object."""
    out: dict = {}
    # Split on commas at depth 0 (no nested objects in our subset).
    parts = []
    depth = 0
    in_string = False
    escape_next = False
    current = ''
    for ch in body:
        if escape_next:
            current += ch
            escape_next = False
            continue
        if in_string:
            current += ch
            if ch == '\\':
                escape_next = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            current += ch
            continue
        if ch == ',' and depth == 0:
            parts.append(current)
            current = ''
            continue
        current += ch
    if current.strip():
        parts.append(current)

    for p in parts:
        kv = p.strip()
        m = re.match(r'^([A-Za-z_][\w-]*)\s*:\s*(.+)$', kv)
        if not m:
            continue
        key = m.group(1)
        raw_value = m.group(2).strip()
        # Strip outer quotes; un-escape backslash-escaped chars.
        if (raw_value.startswith('"') and raw_value.endswith('"')) or (raw_value.startswith("'") and raw_value.endswith("'")):
            raw_value = raw_value[1:-1].encode().decode('unicode_escape')
        out[key] = raw_value
    return out if out else None


def _parse_block_sources(block_lines: list[str]) -> list[dict]:
    """Parse the indented YAML block under a `sources:` opener.
    Recognises:
      - url: "..."
        title: "..."
    Empty lines + comments are skipped.
    """
    out: list[dict] = []
    current: dict | None = None
    for line in block_lines:
        if not line.strip() or line.strip().startswith('#'):
            continue
        # Detect a list-item opener: `  - key: value`
        list_item = re.match(r'^\s*-\s+([A-Za-z_][\w-]*)\s*:\s*(.*)$', line)
        if list_item:
            if current is not None:
                out.append(current)
            current = {}
            key = list_item.group(1)
            value = _decode_yaml_scalar(list_item.group(2))
            current[key] = value
            continue
        # Continuation key on an existing item: `    key: value`
        cont = re.match(r'^\s+([A-Za-z_][\w-]*)\s*:\s*(.*)$', line)
        if cont and current is not None:
            current[cont.group(1)] = _decode_yaml_scalar(cont.group(2))
            continue
    if current is not None:
        out.append(current)
    # Filter to entries with valid http(s) URLs (mirror TS parser's contract).
    return [s for s in out if isinstance(s.get('url'), str) and RE_HTTP_URL.match(s['url'].strip())]


def _decode_yaml_scalar(raw: str) -> str:
    raw = raw.strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1].encode().decode('unicode_escape')
    return raw


def _serialize_sources_block(sources: list[dict]) -> str:
    """Produce a canonical block-list `sources:` chunk. Title is omitted
    when blank/missing (matches the TS serializer)."""
    out = ['sources:']
    for s in sources:
        out.append(f'  - url: {_quote_yaml_scalar(s["url"])}')
        title = s.get('title')
        if isinstance(title, str) and title != '':
            out.append(f'    title: {_quote_yaml_scalar(title)}')
    return '\n'.join(out)


def _transform_md(path: str, dry_run: bool, add_conventions: bool) -> list[str]:
    """Apply all format transforms to a markdown file. Returns list of change descriptions."""
    original = Path(path).read_text(encoding='utf-8')
    text = original
    changes: list[str] = []

    # ── 1. YAML frontmatter — preserve `sources:`, strip everything else ─────
    # The project's TS frontmatter parser only round-trips block-list `sources:`;
    # docs that authored sources inline silently lose them. Behaviour:
    #   - Rewrite inline `sources:` to canonical block-list form.
    #   - When sources is non-empty, emit a sources-only frontmatter block
    #     (other keys like `title:` are still extracted for H1 promotion but
    #     not preserved as frontmatter — kept consistent with the historical
    #     "stripped" contract for non-sources keys).
    #   - When sources is empty, strip frontmatter entirely (legacy behaviour).
    fm_match = FRONTMATTER_RE.match(text)
    if fm_match:
        fm_body = fm_match.group(1)
        title_match = re.search(r'^title:\s*(.+)$', fm_body, re.MULTILINE)
        sources, was_inline = _extract_sources_from_frontmatter(fm_body)

        rest = text[fm_match.end():].lstrip('\n')
        # If the remaining text has no H1 heading but frontmatter had a title, promote it
        if title_match and not re.match(r'#\s', rest):
            extracted = title_match.group(1).strip().strip('"\'')
            rest = f'# {extracted}\n\n{rest}'

        if sources:
            sources_yaml = _serialize_sources_block(sources)
            text = f'---\n{sources_yaml}\n---\n\n{rest}'
            if was_inline:
                changes.append('rewrote inline `sources:` to block-list form')
            else:
                changes.append('preserved frontmatter `sources:` (rewrote to canonical block-list)')
        else:
            text = rest
            changes.append('stripped YAML frontmatter')

    # ── 2. Convert <span data-wiki-link="X"> → [[X]] ──────────────────────────
    spans = SPAN_RE.findall(text)
    if spans:
        text = SPAN_RE.sub(lambda m: f'[[{m.group(1)}]]', text)
        changes.append(f'converted {len(spans)} span wiki-link(s) to [[...]] syntax')

    # ── 3. Visual overview link (--add-conventions only) ──────────────────────
    if add_conventions:
        slug = Path(path).stem
        companion = Path(path).parent / f'{slug}.json'
        has_overview = bool(re.search(r'visual overview:', text, re.IGNORECASE))

        if not has_overview and companion.exists():
            h1 = re.search(r'^#\s.+$', text, re.MULTILINE)
            if h1:
                ins = f'\nVisual overview: [[{slug}.json]]\n'
                text = text[:h1.end()] + ins + text[h1.end():]
                changes.append(f'added Visual overview link → [[{slug}.json]]')
        elif not has_overview:
            changes.append(f'no Visual overview added (no companion {slug}.json found)')

    # ── 4. ## Related section (--add-conventions only) ────────────────────────
    if add_conventions:
        has_related = bool(re.search(r'^##\s+related\b', text, re.IGNORECASE | re.MULTILINE))
        if not has_related:
            # Collect all [[...]] links; exclude the Visual overview JSON link
            slug = Path(path).stem
            all_links = re.findall(r'\[\[([^\]]+)\]\]', text)
            body_links = [
                l.split('|')[0]  # strip display part: [[path|display]] → path
                for l in all_links
                if not l.split('|')[0].strip().endswith('.json')
            ]
            unique = list(dict.fromkeys(body_links))  # deduplicate, preserve order

            if unique:
                section = '\n## Related\n\n' + '\n'.join(f'- [[{l}]]' for l in unique) + '\n'
                text = text.rstrip('\n') + '\n' + section
                changes.append(f'added ## Related section ({len(unique)} link(s))')

    if not changes:
        return []

    if not dry_run:
        bak = backup_file(path, 'transform-backup')
        Path(path).write_text(text, encoding='utf-8')
        from kb_validate_doc import validate_document as _vd
        if _vd(path).errors:
            changes.append(f'⚠ backup kept at {Path(bak).name} (validation errors remain)')
        else:
            Path(bak).unlink(missing_ok=True)

    return changes


def _transform_json(path: str, dry_run: bool) -> None:
    """Delegate JSON files to kb_validate --fix."""
    cmd = [sys.executable, str(SCRIPTS_DIR / 'kb_validate.py'), path]
    if not dry_run:
        cmd.append('--fix')
    subprocess.run(cmd)


def main():
    ap = argparse.ArgumentParser(
        description='Transform knowledge-base files into skill-format conformance.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument('path', help='File path or glob (.md or .json)')
    ap.add_argument('--dry-run', action='store_true', help='Show changes without writing')
    ap.add_argument('--add-conventions', action='store_true',
                    help='Also add missing Visual overview link and ## Related section')
    args = ap.parse_args()

    paths = glob.glob(args.path, recursive=True)
    if not paths and os.path.exists(args.path):
        paths = [args.path]
    if not paths:
        print(f'No files found matching: {args.path}', file=sys.stderr)
        sys.exit(1)

    total = len(paths)
    changed = 0

    for p in paths:
        ext = Path(p).suffix.lower()

        print(f'transform {p}')

        if ext == '.json':
            print('  ℹ JSON file — running kb_validate --fix')
            _transform_json(p, args.dry_run)
            print()
            continue

        if ext != '.md':
            print('  ℹ skipped (not .md or .json)\n')
            continue

        try:
            chgs = _transform_md(p, args.dry_run, args.add_conventions)
        except OSError as e:
            print(f'  ✗ {e}\n')
            continue

        if not chgs:
            print('  ✓ already conformant — no changes needed')
        else:
            for c in chgs:
                glyph = 'ℹ' if c.startswith('no ') else '✓'
                print(f'  {glyph} {c}')
            if args.dry_run:
                print('  — dry run — no files written')
            else:
                changed += 1

        print()

    verb = 'would change' if args.dry_run else 'changed'
    print(f'transform complete: {total} file(s) processed, {changed} {verb}')


if __name__ == '__main__':
    main()
