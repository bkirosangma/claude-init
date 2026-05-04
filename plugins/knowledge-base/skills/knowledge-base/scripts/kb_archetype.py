#!/usr/bin/env python3
"""
Select the best knowledge-base archetype for a topic via keyword matching.
Eliminates LLM token cost for archetype scoring — pure string matching.

Usage:
  kb_archetype.py --archetypes-dir <dir> --topic "<topic>"
  kb_archetype.py --archetypes-dir <dir> --topic "<topic>" --list

Output (single line, stdout):
  <archetype-name> <absolute-path-to-archetype.md>   — if a match is found
  no-match                                             — if no archetype matched

Exit codes:
  0 — always (no-match is not an error; the LLM handles on-the-fly adaptation)
"""

import argparse
import json
import re
import sys
from pathlib import Path


def _parse_frontmatter(text: str) -> dict[str, str]:
    """
    Extract simple key: value pairs from YAML-style frontmatter.
    Handles both single-line and multi-line values (lists).
    """
    m = re.match(r'\A---\r?\n(.*?)\r?\n---', text, re.DOTALL)
    if not m:
        return {}
    result: dict[str, str] = {}
    fm_text = m.group(1)
    lines = fm_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ':' in line:
            k, _, v = line.partition(':')
            k = k.strip()
            v = v.strip()
            # If the value is empty and the next line starts with '-' or spaces,
            # it's a multi-line YAML list; capture all list items
            if not v and i + 1 < len(lines) and (lines[i + 1].lstrip().startswith('-') or lines[i + 1].startswith('  ')):
                list_lines = []
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    # Stop if we hit a new key (line with ':' at start of non-indented content)
                    if ':' in next_line and not next_line.startswith(' ') and not next_line.startswith('-'):
                        break
                    # Collect list items
                    if next_line.strip():
                        list_lines.append(next_line)
                    i += 1
                v = '\n'.join(list_lines)
                i -= 1  # Back up one since the outer loop will increment
            result[k] = v
        i += 1
    return result


def _parse_indicators(raw: str) -> list[str]:
    """
    Parse the domain-indicators field. Handles two YAML forms:
      domain-indicators: [kubernetes, container, pod, docker]
      domain-indicators: |
        - kubernetes
        - container
    """
    raw = raw.strip()
    if raw.startswith('['):
        # Inline list
        inner = raw.strip('[]')
        return [s.strip().strip('"\'') for s in inner.split(',') if s.strip()]
    # Block list or plain comma-separated
    items = []
    for line in raw.splitlines():
        item = line.strip().lstrip('-').strip().strip('"\'')
        if item:
            items.append(item)
    return items


def load_archetypes(archetypes_dir: str) -> list[dict]:
    """Load all archetype files (skip filenames starting with _)."""
    result = []
    for md in sorted(Path(archetypes_dir).glob('*.md')):
        if md.name.startswith('_'):
            continue
        try:
            text = md.read_text(encoding='utf-8')
        except OSError:
            continue
        fm = _parse_frontmatter(text)
        indicators = _parse_indicators(fm.get('domain-indicators', ''))
        result.append({
            'name':        fm.get('name', md.stem),
            'description': fm.get('description', '').strip(),
            'indicators':  indicators,
            'path':        str(md.resolve()),
        })
    return result


def load_meta_archetypes(archetypes_dir: str) -> list[dict]:
    """Load all meta-archetypes (subdirectories containing manifest.json)."""
    result = []
    base = Path(archetypes_dir)
    if not base.is_dir():
        return []
    for sub in sorted(base.iterdir()):
        if not sub.is_dir():
            continue
        manifest_path = sub / "manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
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


def score(archetype: dict, topic: str) -> int:
    """Count domain indicators that appear in the lowercased topic."""
    t = topic.lower()
    return sum(1 for ind in archetype['indicators'] if ind.lower() in t)


def select(archetypes: list[dict], topic: str) -> dict | None:
    """Return the best-matching archetype or None."""
    scored = [(score(a, topic), a) for a in archetypes]
    best_score = max((s for s, _ in scored), default=0)
    if best_score == 0:
        return None
    winners = [a for s, a in scored if s == best_score]
    # Tie-break: alphabetical by name (deterministic)
    return sorted(winners, key=lambda a: a['name'])[0]


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
        if not entry:
            return None
        first_key = next(iter(entry))
        return (first_key, str((root / entry[first_key]).resolve()))
    return None


def main():
    ap = argparse.ArgumentParser(description='Select knowledge-base archetype for a topic.')
    ap.add_argument('--archetypes-dir', required=True, help='Directory containing archetype .md files')
    ap.add_argument('--topic', required=True, help='Topic string to match against')
    ap.add_argument('--list', action='store_true', help='List all archetypes with scores and exit')
    ap.add_argument('--output-type', default='diagram',
                    choices=['diagram', 'document', 'svg', 'tabs'],
                    help='Sub-archetype output type for meta-archetypes (default: diagram)')
    ap.add_argument('--purpose-hint', default='',
                    help='Purpose hint string used to score document sub-types')
    args = ap.parse_args()

    archetypes = load_archetypes(args.archetypes_dir)
    metas = load_meta_archetypes(args.archetypes_dir)
    # Tag single-file archetypes
    for a in archetypes:
        a['is_meta'] = False
    candidates = archetypes + metas

    if not candidates:
        print('no-match')
        return

    if args.list:
        rows = sorted(candidates, key=lambda a: -score(a, args.topic))
        for a in rows:
            s = score(a, args.topic)
            print(f'{s:3d}  {a["name"]:<30s}  {a.get("path", a.get("root", ""))}')
        return

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


if __name__ == '__main__':
    main()
