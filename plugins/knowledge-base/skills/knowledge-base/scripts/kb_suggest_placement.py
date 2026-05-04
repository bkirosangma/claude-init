#!/usr/bin/env python3
"""
Suggest a collection/parent path for a new topic based on vault structure and slug keywords.

A "collection" is any directory that directly contains at least one topic folder
(a folder where <name>/<name>.md or <name>/<name>.json exists).

Usage:
  kb_suggest_placement.py --topic <slug> --vault-root <path>

Output: JSON with ranked suggestions:
  {
    "suggestions": [
      {
        "path": "react-next",
        "reason": "27 existing topics; 3 slug words match existing topic slugs",
        "topic_count": 27,
        "score": 0.85
      },
      ...
    ]
  }

Exit code: 0 always (caller decides what to do with results).
"""

import argparse
import json
import sys
from pathlib import Path


SKIP_DIRS = {'.archdesigner', 'memory', 'graphify-out', '.claude', '.git',
             'flow-descriptions', 'node_modules', '__pycache__'}


def _is_topic_folder(d: Path) -> bool:
    """True if d looks like a topic folder (contains <name>.md or <name>.json)."""
    name = d.name
    return (d / f'{name}.md').exists() or (d / f'{name}.json').exists()


def _find_collections(vault_root: Path) -> dict[str, list[str]]:
    """
    Return {collection_relpath: [topic_slug, ...]} for every collection found.
    A collection is any directory (including vault root) containing topic folders.
    Searches up to 3 levels deep below vault root.
    """
    collections: dict[str, list[str]] = {}

    def scan(directory: Path, depth: int):
        if depth > 3:
            return
        rel = str(directory.relative_to(vault_root)) if directory != vault_root else '.'
        topics_here = []
        for child in sorted(directory.iterdir()):
            if not child.is_dir():
                continue
            if child.name.startswith('.') or child.name in SKIP_DIRS:
                continue
            if _is_topic_folder(child):
                topics_here.append(child.name)
            else:
                # Recurse into non-topic directories (they may be collections themselves)
                scan(child, depth + 1)
        if topics_here:
            collections[rel] = topics_here

    scan(vault_root, 0)
    return collections


def _score(slug: str, topic_slugs: list[str]) -> float:
    """
    Score a collection against a new topic slug by word overlap.
    slug words that appear in any existing topic slug in the collection score +1.
    Normalized by len(slug_words).
    """
    slug_words = set(slug.split('-'))
    if not slug_words:
        return 0.0
    matched = sum(
        1 for w in slug_words
        if any(w in existing.split('-') for existing in topic_slugs)
    )
    return matched / len(slug_words)


def suggest(slug: str, vault_root: Path) -> list[dict]:
    collections = _find_collections(vault_root)
    results = []

    for rel_path, topic_slugs in collections.items():
        score = _score(slug, topic_slugs)
        count = len(topic_slugs)

        # Build human-readable reason
        slug_words = set(slug.split('-'))
        matched_words = [w for w in slug_words if any(w in t.split('-') for t in topic_slugs)]
        if matched_words:
            reason = f'{count} existing topic(s); words {", ".join(repr(w) for w in matched_words)} match existing slugs'
        else:
            reason = f'{count} existing topic(s) in this collection'

        display_path = rel_path if rel_path != '.' else '(vault root)'
        results.append({
            'path': rel_path,
            'display': display_path,
            'reason': reason,
            'topic_count': count,
            'score': round(score, 3),
        })

    # Sort: score descending, then topic_count descending as tiebreaker
    results.sort(key=lambda x: (-x['score'], -x['topic_count']))
    return results[:3]


def main():
    ap = argparse.ArgumentParser(
        description='Suggest a placement path for a new knowledge-base topic.',
    )
    ap.add_argument('--topic', required=True, help='Topic slug (kebab-case)')
    ap.add_argument('--vault-root', required=True, help='Vault root directory')
    args = ap.parse_args()

    vault_root = Path(args.vault_root).resolve()
    if not vault_root.is_dir():
        print(json.dumps({'error': f'Vault root not found: {vault_root}', 'suggestions': []}))
        sys.exit(0)

    suggestions = suggest(args.topic, vault_root)
    print(json.dumps({'suggestions': suggestions}, indent=2))


if __name__ == '__main__':
    main()
