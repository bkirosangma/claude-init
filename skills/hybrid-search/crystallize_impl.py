#!/usr/bin/env python3
"""
Auto-crystallization: Tier 2→3 promotion.
Finds observation clusters with ≥5 entries on shared concepts,
distills them into structured markdown knowledge pages.
"""

import sqlite3
import hashlib
import json
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

DB_PATH = Path.home() / ".claude-mem" / "claude-mem.db"
CRYSTAL_DIR = Path.home() / ".claude-mem" / "crystallized"
MIN_CLUSTER_SIZE = 5
MAX_CLUSTERS = 5
REGROWTH_THRESHOLD = 3  # skip re-crystallization unless ≥3 new observations


def get_concept_clusters(conn):
    """Find concept clusters with ≥ MIN_CLUSTER_SIZE observations."""
    rows = conn.execute("""
        SELECT concepts, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
        FROM observations
        WHERE concepts IS NOT NULL AND concepts != ''
        AND relevance_count != -1
        GROUP BY concepts
        HAVING cnt >= ?
        ORDER BY cnt DESC
        LIMIT ?
    """, (MIN_CLUSTER_SIZE, MAX_CLUSTERS)).fetchall()

    clusters = []
    for row in rows:
        obs_ids = [int(x) for x in row['ids'].split(',')]
        clusters.append({
            'concepts': row['concepts'],
            'count': row['cnt'],
            'ids': obs_ids
        })
    return clusters


def concept_hash(concepts: str) -> str:
    """Stable hash for a concept string."""
    normalized = '-'.join(sorted(c.strip().lower() for c in concepts.split(',') if c.strip()))
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


def should_crystallize(crystal_path: Path, current_count: int) -> bool:
    """Check if a cluster needs (re)crystallization."""
    if not crystal_path.exists():
        return True

    # Read the existing crystal to check observation count
    content = crystal_path.read_text()
    for line in content.split('\n'):
        if line.startswith('Source observations:'):
            try:
                old_count = int(line.split(':')[1].strip().split(' ')[0])
                return (current_count - old_count) >= REGROWTH_THRESHOLD
            except (ValueError, IndexError):
                return True
    return True


def fetch_observations(conn, ids):
    """Fetch full observation details for a cluster."""
    placeholders = ','.join('?' * len(ids))
    return conn.execute(f"""
        SELECT id, type, title, subtitle, narrative, facts, concepts,
               files_read, files_modified, created_at, created_at_epoch
        FROM observations
        WHERE id IN ({placeholders})
        ORDER BY created_at_epoch ASC
    """, ids).fetchall()


def build_crystal_markdown(concepts: str, observations: list) -> str:
    """Build a structured markdown digest from observations."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    obs_ids = [str(o['id']) for o in observations]

    sections = {
        'decision': [],
        'bugfix': [],
        'feature': [],
        'discovery': [],
        'change': [],
        'refactor': [],
    }

    all_facts = []
    timeline = []
    all_files = set()
    action_patterns = []

    for obs in observations:
        obs_type = obs['type']
        title = obs['title'] or '(untitled)'
        narrative = obs['narrative'] or ''
        facts = obs['facts'] or ''

        # Categorize
        if obs_type in sections:
            sections[obs_type].append(f"- **#{obs['id']}** {title}")

        # Collect facts
        if facts:
            for fact in facts.split('\n'):
                fact = fact.strip().lstrip('- ')
                if fact and fact not in all_facts:
                    all_facts.append(fact)

        # Timeline
        created = obs['created_at'][:10] if obs['created_at'] else '?'
        timeline.append(f"- [{created}] #{obs['id']} ({obs_type}) {title}")

        # Files
        for f_field in [obs['files_read'], obs['files_modified']]:
            if f_field:
                for f in f_field.split(','):
                    f = f.strip()
                    if f:
                        all_files.add(f)

        # Action patterns (type + concept sequence for Tier 4)
        action_patterns.append(f"{obs_type}:{concepts}")

    # Build markdown
    lines = [
        f"# Crystallized: {concepts}",
        "",
        f"Tier: SEMANTIC | Last updated: {now}",
        f"Source observations: {len(observations)} (IDs: {', '.join(obs_ids)})",
        "",
    ]

    # Key Facts
    if all_facts:
        lines.append("## Key Facts")
        for fact in all_facts[:15]:  # cap at 15
            lines.append(f"- {fact}")
        lines.append("")

    # Categorized sections
    for section_type, label in [
        ('decision', 'Decisions Made'),
        ('bugfix', 'Bugs Fixed'),
        ('feature', 'Features Added'),
        ('discovery', 'Discoveries'),
        ('change', 'Changes'),
        ('refactor', 'Refactors'),
    ]:
        items = sections[section_type]
        if items:
            lines.append(f"## {label}")
            lines.extend(items)
            lines.append("")

    # Files involved
    if all_files:
        lines.append("## Files Involved")
        for f in sorted(all_files)[:20]:
            lines.append(f"- `{f}`")
        lines.append("")

    # Action patterns for Tier 4
    if len(action_patterns) >= 3:
        lines.append("## Action Patterns (candidates for Tier 4)")
        # Show the type sequence
        type_sequence = [obs['type'] for obs in observations]
        lines.append(f"- Sequence: {' -> '.join(type_sequence)}")
        lines.append("")

    # Timeline
    lines.append("## Timeline")
    lines.extend(timeline)
    lines.append("")

    return '\n'.join(lines)


def build_index(crystal_dir: Path):
    """Rebuild the crystallized knowledge index."""
    crystals = sorted(crystal_dir.glob("*.md"))
    crystals = [c for c in crystals if c.name != "INDEX.md"]

    lines = [
        "# Crystallized Knowledge Index",
        "",
        f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC",
        f"Total crystals: {len(crystals)}",
        "",
        "| Crystal | Observations | Last Updated |",
        "|---------|-------------|--------------|",
    ]

    for crystal_path in crystals:
        content = crystal_path.read_text()
        title = crystal_path.stem
        obs_count = "?"
        updated = "?"

        for line in content.split('\n'):
            if line.startswith('# Crystallized:'):
                title = line.replace('# Crystallized:', '').strip()
            if line.startswith('Source observations:'):
                try:
                    obs_count = line.split(':')[1].strip().split(' ')[0]
                except (IndexError, ValueError):
                    pass
            if line.startswith('Tier: SEMANTIC'):
                try:
                    updated = line.split('Last updated:')[1].strip()
                except (IndexError, ValueError):
                    pass

        lines.append(f"| [{title}]({crystal_path.name}) | {obs_count} | {updated} |")

    lines.append("")
    (crystal_dir / "INDEX.md").write_text('\n'.join(lines))


def run():
    if not DB_PATH.exists():
        return

    CRYSTAL_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row

    clusters = get_concept_clusters(conn)

    if not clusters:
        conn.close()
        return

    crystallized_count = 0
    for cluster in clusters:
        c_hash = concept_hash(cluster['concepts'])
        crystal_path = CRYSTAL_DIR / f"{c_hash}.md"

        if not should_crystallize(crystal_path, cluster['count']):
            continue

        observations = fetch_observations(conn, cluster['ids'])
        if not observations:
            continue

        markdown = build_crystal_markdown(cluster['concepts'], observations)
        crystal_path.write_text(markdown)

        # Mark source observations as crystallized (relevance_count = -1)
        placeholders = ','.join('?' * len(cluster['ids']))
        conn.execute(f"""
            UPDATE observations
            SET relevance_count = -1
            WHERE id IN ({placeholders})
        """, cluster['ids'])

        crystallized_count += 1

    if crystallized_count > 0:
        conn.commit()
        build_index(CRYSTAL_DIR)

    conn.close()


if __name__ == "__main__":
    try:
        run()
    except Exception:
        pass
