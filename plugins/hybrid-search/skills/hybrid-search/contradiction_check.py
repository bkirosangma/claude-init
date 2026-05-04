#!/usr/bin/env python3
"""
Contradiction detection for hybrid-search.
Checks the latest observation against similar older ones for conflicts.
Called by contradiction-check.sh (PostToolUse hook).
"""

import sqlite3
import sys
import json
import time
from pathlib import Path

DB_PATH = Path.home() / ".claude-mem" / "claude-mem.db"

CONTRADICTION_SIGNALS = [
    'instead', 'rather than', 'not', 'switch', 'replace', 'revert',
    'undo', 'wrong', 'incorrect', 'actually', 'should have', 'better to',
    'changed from', 'moved away', 'no longer'
]

CHECKABLE_TYPES = ('decision', 'bugfix', 'feature', 'change')


def check_contradictions():
    if not DB_PATH.exists():
        return

    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row

    # Get the most recent observation
    latest = conn.execute('''
        SELECT id, title, concepts, narrative, type, files_modified,
               memory_session_id, project, created_at_epoch
        FROM observations
        ORDER BY created_at_epoch DESC LIMIT 1
    ''').fetchone()

    if not latest or not latest['concepts']:
        conn.close()
        return

    latest_id = latest['id']
    latest_concepts = latest['concepts'].strip()
    latest_type = latest['type']

    if latest_type not in CHECKABLE_TYPES:
        conn.close()
        return

    # Build FTS query from concepts (take first 3 terms)
    terms = [t.strip() for t in latest_concepts.replace(',', ' ').split() if len(t.strip()) > 2][:3]
    if not terms:
        conn.close()
        return

    fts_query = ' OR '.join(terms)

    # Search for similar older observations
    try:
        similar = conn.execute('''
            SELECT o.id, o.title, o.concepts, o.narrative, o.type,
                   o.files_modified, o.created_at_epoch
            FROM observations o
            JOIN observations_fts fts ON o.id = fts.rowid
            WHERE observations_fts MATCH ?
            AND o.id != ?
            AND o.type IN ('decision', 'bugfix', 'feature', 'change')
            ORDER BY o.created_at_epoch DESC
            LIMIT 5
        ''', (fts_query, latest_id)).fetchall()
    except Exception:
        conn.close()
        return

    if not similar:
        conn.close()
        return

    # Check for contradictions
    latest_narrative = (latest['narrative'] or '').lower()
    latest_title_text = (latest['title'] or '').lower()
    latest_text = latest_narrative + ' ' + latest_title_text
    has_signal = any(sig in latest_text for sig in CONTRADICTION_SIGNALS)

    conflicts = []
    for old in similar:
        same_type = old['type'] == latest_type

        # Check for shared modified files
        same_files = False
        if latest['files_modified'] and old['files_modified']:
            new_files = set(f.strip() for f in latest['files_modified'].split(','))
            old_files = set(f.strip() for f in old['files_modified'].split(','))
            same_files = bool(new_files & old_files)

        # Score the conflict likelihood
        score = 0
        if same_type and latest_type == 'decision':
            score += 3
        elif same_type:
            score += 1
        if same_files:
            score += 2
        if has_signal:
            score += 2

        old_text = ((old['narrative'] or '') + ' ' + (old['title'] or '')).lower()
        if any(sig in old_text for sig in CONTRADICTION_SIGNALS):
            score += 1

        if score >= 3:
            conflicts.append({
                'old_id': old['id'],
                'old_title': old['title'],
                'score': score
            })

    if not conflicts:
        conn.close()
        return

    # Take the strongest conflict
    best = max(conflicts, key=lambda c: c['score'])
    now_ms = int(time.time() * 1000)
    now_iso = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())

    # Insert contradiction observation
    title = f"Potential conflict: #{latest_id} vs #{best['old_id']}"
    subtitle = f"Conflict score: {best['score']}/7"
    narrative = (
        f"New observation #{latest_id} ('{latest['title']}') may supersede "
        f"#{best['old_id']} ('{best['old_title']}'). "
        f"Both share concepts: {latest_concepts}. "
        f"Review and resolve with /hybrid-search contradictions."
    )

    conn.execute('''
        INSERT INTO observations (
            memory_session_id, project, type, title, subtitle, narrative, concepts,
            created_at, created_at_epoch
        ) VALUES (?, ?, 'contradiction', ?, ?, ?, ?, ?, ?)
    ''', (
        latest['memory_session_id'],
        latest['project'],
        title,
        subtitle,
        narrative,
        latest_concepts,
        now_iso,
        now_ms
    ))
    conn.commit()
    conn.close()

    # Output warning for Claude to see
    warning = (
        f"Contradiction detected: observation #{latest_id} may conflict with "
        f"#{best['old_id']}. Use /hybrid-search contradictions to review."
    )
    output = {
        'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'additionalContext': warning
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    try:
        check_contradictions()
    except Exception:
        # Never crash the hook pipeline
        pass
