#!/usr/bin/env python3
"""
Shared utilities for knowledge-base skill scripts.
Also usable as a CLI for individual utility operations.

Usage:
  kb_utils.py slug "<topic>"
  kb_utils.py next-slug "<slug>" "<registry-path>"
  kb_utils.py backup "<file>" [<label>]
  kb_utils.py detect-vault [<start-path>]
  kb_utils.py append-registry --vault-root <path> --date <YYYY-MM-DD>
                               --topic <topic> --slug <slug>
                               [--doc <relative-path>] [--diagram <relative-path>]
"""

import argparse
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Core utilities ─────────────────────────────────────────────────────────────

def slugify(topic: str) -> str:
    """Convert a topic string to a file-safe slug."""
    s = topic.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


def detect_vault(start_path: str = None) -> str | None:
    """Walk up from start_path (up to 4 levels) for .archdesigner/config.json."""
    path = Path(start_path or os.getcwd()).resolve()
    for _ in range(4):
        if (path / '.archdesigner' / 'config.json').exists():
            return str(path)
        parent = path.parent
        if parent == path:
            break
        path = parent
    return None


def backup_file(file_path: str, label: str = 'backup') -> str:
    """Create a timestamped backup. Returns the backup path."""
    p = Path(file_path)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S')
    backup = p.parent / f'{p.stem}.{label}-{ts}{p.suffix}'
    shutil.copy2(p, backup)
    return str(backup)


def next_available_slug(slug: str, registry_path: str) -> str:
    """Return slug unchanged, or slug-2/slug-3/... if already in registry."""
    if not Path(registry_path).exists():
        return slug
    content = Path(registry_path).read_text(encoding='utf-8')
    candidate = slug
    counter = 2
    # Match as a whole word (surrounded by non-alnum or line boundaries)
    while re.search(r'(?<![a-z0-9-])' + re.escape(candidate) + r'(?![a-z0-9-])', content):
        candidate = f'{slug}-{counter}'
        counter += 1
    return candidate


def append_to_topic_registry(vault_root: str, date: str, topic: str, slug: str,
                               doc_file: str = None, diag_file: str = None) -> None:
    """Append a topic entry to memory/topic-registry.md."""
    memory_dir = Path(vault_root) / 'memory'
    memory_dir.mkdir(exist_ok=True)
    registry = memory_dir / 'topic-registry.md'

    parts = []
    if doc_file:
        parts.append(f'document: `{doc_file}`')
    if diag_file:
        parts.append(f'diagram: `{diag_file}`')

    entry = f'- **{topic}** -- {", ".join(parts)} (created {date})\n'

    if not registry.exists():
        registry.write_text(
            '# Topic Registry\n\nAll topics generated in this vault.\n\n## Topics\n\n' + entry,
            encoding='utf-8',
        )
    else:
        content = registry.read_text(encoding='utf-8')
        if '## Topics' in content:
            content = content.rstrip('\n') + '\n' + entry
        else:
            content = content.rstrip('\n') + '\n\n## Topics\n\n' + entry
        registry.write_text(content, encoding='utf-8')


# ── CLI dispatch ───────────────────────────────────────────────────────────────

def _cmd_slug(argv: list[str]) -> None:
    if not argv:
        sys.exit('Usage: kb_utils.py slug "<topic>"')
    print(slugify(' '.join(argv)))


def _cmd_next_slug(argv: list[str]) -> None:
    if len(argv) < 2:
        sys.exit('Usage: kb_utils.py next-slug "<slug>" "<registry-path>"')
    print(next_available_slug(argv[0], argv[1]))


def _cmd_backup(argv: list[str]) -> None:
    if not argv:
        sys.exit('Usage: kb_utils.py backup "<file>" [<label>]')
    label = argv[1] if len(argv) > 1 else 'backup'
    print(backup_file(argv[0], label))


def _cmd_detect_vault(argv: list[str]) -> None:
    result = detect_vault(argv[0] if argv else None)
    if result:
        print(result)
    else:
        sys.exit(1)


def _cmd_append_registry(argv: list[str]) -> None:
    p = argparse.ArgumentParser(prog='kb_utils.py append-registry')
    p.add_argument('--vault-root', required=True)
    p.add_argument('--date', required=True)
    p.add_argument('--topic', required=True)
    p.add_argument('--slug', required=True)
    p.add_argument('--doc')
    p.add_argument('--diagram')
    args = p.parse_args(argv)
    append_to_topic_registry(
        args.vault_root, args.date, args.topic, args.slug,
        args.doc, args.diagram,
    )


_COMMANDS = {
    'slug':             _cmd_slug,
    'next-slug':        _cmd_next_slug,
    'backup':           _cmd_backup,
    'detect-vault':     _cmd_detect_vault,
    'append-registry':  _cmd_append_registry,
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in _COMMANDS:
        print(f'Usage: kb_utils.py <command> [args]')
        print(f'Commands: {", ".join(_COMMANDS)}')
        sys.exit(1)
    _COMMANDS[sys.argv[1]](sys.argv[2:])
