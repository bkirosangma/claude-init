#!/usr/bin/env python3
"""
Aggregate validation report for a knowledge-base directory or glob.

Validates all .md and .json files found and prints a grouped summary:
  - Overall counts by severity
  - Errors section (files + issues)
  - Warnings section (files + issues)
  - Info section (summarized count)

Usage:
  kb_report.py <path-or-glob> [--vault-root <path>] [--json]

Exit codes: 0 = no errors, 1 = errors found
"""

import argparse
import glob as glob_mod
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_utils import detect_vault


# ── Collect per-file results ───────────────────────────────────────────────────

def _collect(paths: list[str], vault_root: str | None) -> list[dict]:
    """Validate each path and return list of result dicts."""
    from kb_validate import validate, Result as JsonResult
    from kb_validate_doc import validate_document

    results = []
    for p in paths:
        ext = Path(p).suffix.lower()
        if ext == '.json':
            try:
                text = Path(p).read_text(encoding='utf-8')
                data = json.loads(text)
            except OSError as e:
                results.append({'path': p, 'ext': ext, 'error': str(e), 'diags': []})
                continue
            except json.JSONDecodeError as e:
                results.append({'path': p, 'ext': ext, 'error': f'invalid JSON: {e.msg}', 'diags': []})
                continue
            r = validate(data, p)
        elif ext == '.md':
            r = validate_document(p, vault_root)
        else:
            continue

        results.append({
            'path': p,
            'ext': ext,
            'error': None,
            'diags': [{'level': d.level, 'section': d.section, 'msg': d.msg, 'fixable': d.fixable}
                      for d in r.diags],
        })
    return results


# ── Text report ────────────────────────────────────────────────────────────────

def _format_text(results: list[dict]) -> str:
    lines = []

    md_results   = [r for r in results if r['ext'] == '.md']
    json_results = [r for r in results if r['ext'] == '.json']

    def counts(rs):
        e = sum(1 for r in rs if any(d['level'] == 'error'   for d in r['diags']) or r['error'])
        w = sum(1 for r in rs if any(d['level'] == 'warning' for d in r['diags']))
        i = sum(1 for r in rs if any(d['level'] == 'info'    for d in r['diags']))
        clean = sum(1 for r in rs if not r['error']
                    and not any(d['level'] in ('error', 'warning') for d in r['diags']))
        return e, w, i, clean

    md_e, md_w, md_i, md_clean   = counts(md_results)
    js_e, js_w, js_i, js_clean   = counts(json_results)
    total = len(results)

    lines += [
        '=' * 60,
        'KNOWLEDGE-BASE VALIDATION REPORT',
        '=' * 60,
        '',
        f'Documents (.md) : {len(md_results):>4} files  —  '
        f'{md_e} error(s), {md_w} warning(s), {md_i} info, {md_clean} clean',
        f'Diagrams  (.json): {len(json_results):>4} files  —  '
        f'{js_e} error(s), {js_w} warning(s), {js_i} info, {js_clean} clean',
        f'Total            : {total:>4} files',
        '',
    ]

    def section(title, level, rs):
        hits = [(r, [d for d in r['diags'] if d['level'] == level]) for r in rs]
        hits = [(r, ds) for r, ds in hits if ds or (level == 'error' and r['error'])]
        if not hits:
            return
        lines.append('─' * 60)
        lines.append(title)
        lines.append('─' * 60)
        glyph = {'error': '✗', 'warning': '⚠', 'info': 'ℹ'}[level]
        for r, ds in hits:
            lines.append(f'  {r["path"]}')
            if r['error']:
                lines.append(f'    {glyph} {r["error"]}')
            for d in ds:
                lines.append(f'    {glyph} {d["msg"]}')
        lines.append('')

    section('ERRORS', 'error', md_results)
    section('ERRORS', 'error', json_results)
    section('DOCUMENT WARNINGS', 'warning', md_results)
    section('DIAGRAM WARNINGS', 'warning', json_results)

    # Info: grouped by message pattern
    import re as _re
    from collections import Counter
    md_info_msgs   = Counter()
    json_info_msgs = Counter()
    for r in md_results:
        for d in r['diags']:
            if d['level'] == 'info':
                key = d['msg'].split('(')[0].strip().rstrip(' —')
                md_info_msgs[key] += 1
    for r in json_results:
        for d in r['diags']:
            if d['level'] == 'info':
                # Strip quoted IDs, leaving the pattern: e.g. "connection is not in any flow"
                key = _re.sub(r'"[^"]+"', '...', d['msg'])
                key = key.split('(')[0].strip().rstrip(' —')
                json_info_msgs[key] += 1

    if md_info_msgs or json_info_msgs:
        lines.append('─' * 60)
        lines.append('INFO (low priority — grouped)')
        lines.append('─' * 60)
        for msg, count in sorted(md_info_msgs.items(), key=lambda x: -x[1]):
            lines.append(f'  ℹ {count}× {msg}  [docs]')
        for msg, count in sorted(json_info_msgs.items(), key=lambda x: -x[1]):
            lines.append(f'  ℹ {count}× {msg}  [diagrams]')
        lines.append('')

    any_errors = md_e > 0 or js_e > 0
    lines.append(f'{"✗ ERRORS FOUND" if any_errors else "✓ NO ERRORS"} — '
                 f'{md_e + js_e} error(s), {md_w + js_w} warning(s) across {total} files.')
    return '\n'.join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description='Aggregated validation report for a knowledge-base directory or glob.',
    )
    ap.add_argument('path', help='Directory, file path, or glob (e.g. react-next/**/*)')
    ap.add_argument('--vault-root', default=None, help='Vault root for resolving wiki-links (auto-detected if omitted)')
    ap.add_argument('--json', dest='json_out', action='store_true', help='Machine-readable JSON output')
    ap.add_argument('--exclude', default='.history.json', help='Filename suffix to exclude (default: .history.json)')
    args = ap.parse_args()

    vault_root = args.vault_root or detect_vault()

    # Resolve paths
    pattern = args.path
    # If it's a directory, expand to all files inside
    if os.path.isdir(pattern):
        pattern = os.path.join(pattern, '**', '*')

    paths = sorted(glob_mod.glob(pattern, recursive=True))
    if not paths and os.path.exists(args.path):
        paths = [args.path]

    BACKUP_MARKERS = ('.transform-backup-', '.invalid-backup-', '.history.json')
    paths = [
        p for p in paths
        if Path(p).suffix.lower() in ('.md', '.json')
        and not any(m in p for m in BACKUP_MARKERS)
        and os.path.isfile(p)
    ]

    if not paths:
        print(f'No .md or .json files found matching: {args.path}', file=sys.stderr)
        sys.exit(1)

    results = _collect(paths, vault_root)

    if args.json_out:
        print(json.dumps(results, indent=2))
    else:
        print(_format_text(results))

    any_errors = any(
        r['error'] or any(d['level'] == 'error' for d in r['diags'])
        for r in results
    )
    sys.exit(1 if any_errors else 0)


if __name__ == '__main__':
    main()
