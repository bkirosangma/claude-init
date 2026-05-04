#!/usr/bin/env python3
"""
Validate a knowledge-base markdown document against skill conventions.

Usage:
  kb_validate_doc.py <path-or-glob> [--fix] [--vault-root <path>] [--json]

Rules enforced:
  Errors   — YAML frontmatter present; span wiki-links present; no H1 title
  Warnings — missing Visual overview link; heading level skips; broken wiki-link targets
  Info     — missing ## Related section

--fix delegates syntax fixes to kb_transform.py (it is the single source of truth for
format transforms). Convention additions (Visual overview, Related) require --add-conventions
to be passed through, so --fix here maps to: kb_transform.py --add-conventions.

Exit codes: 0 = no errors, 1 = errors found
"""

import argparse
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_utils import detect_vault

SCRIPTS_DIR = Path(__file__).parent

SPAN_RE = re.compile(r'<span\s+data-wiki-link="([^"]+)"[^>]*>.*?</span>', re.IGNORECASE | re.DOTALL)
FRONTMATTER_RE = re.compile(r'\A---\r?\n.*?\r?\n---[ \t]*(?:\r?\n|$)', re.DOTALL)
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
WIKI_LINK_RE = re.compile(r'\[\[([^\]]+)\]\]')


# ── Shared Diag / Result (mirrors kb_validate.py) ─────────────────────────────

class Diag:
    __slots__ = ('level', 'section', 'msg', 'fixable')

    def __init__(self, level: str, section: str, msg: str, fixable: bool = False):
        self.level = level
        self.section = section
        self.msg = msg
        self.fixable = fixable

    def glyph(self) -> str:
        return {'error': '✗', 'warning': '⚠', 'info': 'ℹ'}[self.level]


class Result:
    def __init__(self):
        self.diags: list[Diag] = []

    def add(self, level, section, msg, fixable=False):
        self.diags.append(Diag(level, section, msg, fixable))

    @property
    def errors(self):   return [d for d in self.diags if d.level == 'error']
    @property
    def warnings(self): return [d for d in self.diags if d.level == 'warning']
    @property
    def infos(self):    return [d for d in self.diags if d.level == 'info']


# ── Wiki-link resolver ─────────────────────────────────────────────────────────

def _resolve_link(target: str, doc_path: Path, vault_root: str | None) -> bool:
    """Return True if the wiki-link target resolves to an existing file."""
    # Strip display text (path|display) and anchor (path#section)
    target = target.split('|')[0].split('#')[0].strip()
    if not target:
        return True  # Empty target is handled separately

    candidate_paths = []
    doc_dir = doc_path.parent

    # Build candidate paths: try relative to doc dir, parent dir (for files inside
    # flow-descriptions/ subfolders), then vault root
    bases = [doc_dir, doc_dir.parent]
    if vault_root:
        bases.append(Path(vault_root))

    for base in bases:
        p = base / target
        candidate_paths.append(p)
        # If no extension given, try with .md and .json
        if not Path(target).suffix:
            candidate_paths.append(p.with_suffix('.md'))
            candidate_paths.append(p.with_suffix('.json'))

    return any(c.exists() for c in candidate_paths)


# ── Core validator ─────────────────────────────────────────────────────────────

def validate_document(path: str, vault_root: str = None) -> Result:
    r = Result()
    doc_path = Path(path)

    try:
        text = doc_path.read_text(encoding='utf-8')
    except OSError as e:
        r.add('error', 'file', f'Cannot read file: {e}')
        return r

    # ── 1. YAML frontmatter ────────────────────────────────────────────────────
    if FRONTMATTER_RE.match(text):
        r.add('error', 'format',
              'YAML frontmatter present at top of file — run kb_transform.py to strip it',
              fixable=True)

    # ── 2. Span wiki-links ─────────────────────────────────────────────────────
    spans = SPAN_RE.findall(text)
    if spans:
        r.add('error', 'format',
              f'{len(spans)} span wiki-link(s) using <span> syntax — run kb_transform.py to convert to [[...]]',
              fixable=True)

    # ── 3. H1 title ───────────────────────────────────────────────────────────
    # Strip frontmatter for structural checks
    body = FRONTMATTER_RE.sub('', text).lstrip('\n')
    # Strip fenced code blocks before heading checks so `# comment` inside
    # code fences isn't mistaken for a heading.
    body_no_code = re.sub(r'```[^\n]*\n.*?```', '', body, flags=re.DOTALL)
    body_no_code = re.sub(r'`[^`\n]+`', '', body_no_code)  # strip inline code too

    first_line = next((l for l in body.splitlines() if l.strip()), '')
    if not re.match(r'^#\s+\S', first_line):
        r.add('error', 'structure', 'Document does not start with an H1 title (# Title)')

    # Multiple H1s
    h1_count = len(re.findall(r'^#\s+', body_no_code, re.MULTILINE))
    if h1_count > 1:
        r.add('warning', 'structure', f'{h1_count} H1 headings found — documents should have exactly one')

    # ── 4. Heading level skips ────────────────────────────────────────────────
    headings = [(len(m.group(1)), m.group(2).strip()) for m in HEADING_RE.finditer(body_no_code)]
    for i in range(1, len(headings)):
        prev_lvl, curr_lvl = headings[i - 1][0], headings[i][0]
        if curr_lvl > prev_lvl + 1:
            r.add('warning', 'structure',
                  f'Heading level skip: H{prev_lvl} "{headings[i-1][1]}" → H{curr_lvl} "{headings[i][1]}"')

    # ── 5. Visual overview link ───────────────────────────────────────────────
    slug = doc_path.stem
    companion = doc_path.parent / f'{slug}.json'
    has_overview = bool(re.search(r'visual overview:', body, re.IGNORECASE))
    if companion.exists() and not has_overview:
        r.add('warning', 'conventions',
              f'Missing "Visual overview: [[{slug}.json]]" — companion JSON exists; add with kb_transform.py --add-conventions',
              fixable=True)

    # ── 6. Broken wiki-links ──────────────────────────────────────────────────
    # Scan only outside code blocks and inline code to avoid false positives
    # (e.g. [[...slug]] is Next.js catch-all syntax, not a wiki-link)
    all_links = WIKI_LINK_RE.findall(body_no_code)
    for link in all_links:
        target = link.split('|')[0].split('#')[0].strip()
        if not target:
            r.add('warning', 'links', f'Empty wiki-link: [[{link}]]')
            continue
        if not _resolve_link(target, doc_path, vault_root):
            r.add('warning', 'links', f'Wiki-link target not found: [[{link}]]')

    # ── 7. Related section ────────────────────────────────────────────────────
    body_links = [l for l in all_links if not l.split('|')[0].strip().endswith('.json')]  # noqa: same body_no_code scan
    has_related = bool(re.search(r'^##\s+related\b', body, re.IGNORECASE | re.MULTILINE))
    if body_links and not has_related:
        r.add('info', 'conventions',
              f'Missing ## Related section ({len(body_links)} wiki-link(s) in body) — add with kb_transform.py --add-conventions')

    # ── 8. Flow files in topic root ───────────────────────────────────────────
    # Only check the main topic document (not files already inside flow-descriptions/)
    if doc_path.parent.name != 'flow-descriptions':
        loose_flows = [f for f in doc_path.parent.glob('flow-*.md') if f.parent == doc_path.parent]
        if loose_flows:
            r.add('warning', 'structure',
                  f'{len(loose_flows)} flow-*.md file(s) in topic root — run kb_migrate_flows.py to move into flow-descriptions/')

    return r


# ── Report formatter ───────────────────────────────────────────────────────────

def format_doc_report(path: str, r: Result) -> str:
    lines = [f'validate {path}', '']
    sections = [
        ('file',        'File'),
        ('format',      'Format'),
        ('structure',   'Structure'),
        ('conventions', 'Conventions'),
        ('links',       'Wiki-Links'),
    ]
    for key, label in sections:
        diags = [d for d in r.diags if d.section == key]
        lines.append(f'▸ {label}')
        if diags:
            for d in diags:
                lines.append(f'  {d.glyph()} {d.msg}')
        else:
            lines.append('  ✓ no issues')
        lines.append('')

    ne, nw, ni = len(r.errors), len(r.warnings), len(r.infos)
    fixable = sum(1 for d in r.diags if d.fixable)
    summary = f'Summary: {ne} error(s), {nw} warning(s), {ni} info.'
    if fixable:
        summary += f' kb_transform.py would fix {fixable} issue(s).'
    lines.append(summary)
    return '\n'.join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description='Validate knowledge-base markdown documents against skill conventions.',
    )
    ap.add_argument('path', help='File path or glob (*.md)')
    ap.add_argument('--fix', action='store_true',
                    help='Run kb_transform.py --add-conventions to fix all fixable issues')
    ap.add_argument('--vault-root', default=None,
                    help='Vault root for resolving wiki-link targets (auto-detected if omitted)')
    ap.add_argument('--json', dest='json_out', action='store_true',
                    help='Machine-readable JSON output')
    args = ap.parse_args()

    vault_root = args.vault_root or detect_vault()

    paths = glob.glob(args.path, recursive=True)
    if not paths and os.path.exists(args.path):
        paths = [args.path]
    if not paths:
        print(f'No files found: {args.path}', file=sys.stderr)
        sys.exit(1)

    any_errors = False

    for p in paths:
        if not p.endswith('.md'):
            print(f'  ℹ {p}: skipped (not .md)')
            continue

        r = validate_document(p, vault_root)

        if args.json_out:
            import json
            print(json.dumps({
                'path': p,
                'errors': len(r.errors), 'warnings': len(r.warnings), 'infos': len(r.infos),
                'diagnostics': [{'level': d.level, 'section': d.section, 'msg': d.msg, 'fixable': d.fixable}
                                 for d in r.diags],
            }, indent=2))
        else:
            print(format_doc_report(p, r))

        if r.errors:
            any_errors = True

        if args.fix:
            fixable = [d for d in r.diags if d.fixable]
            if fixable:
                print(f'Applying fixes via kb_transform.py --add-conventions ...')
                subprocess.run([
                    sys.executable,
                    str(SCRIPTS_DIR / 'kb_transform.py'),
                    p,
                    '--add-conventions',
                ])

    sys.exit(1 if any_errors else 0)


if __name__ == '__main__':
    main()
