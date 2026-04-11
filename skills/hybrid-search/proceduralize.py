#!/usr/bin/env python3
"""
Procedural extraction: Tier 3→4 promotion.
Scans crystallized knowledge pages for repeated action patterns,
extracts them as reusable workflow templates.

A "procedure" is detected when the same (type, concept) subsequence
of length ≥3 appears ≥3 times across different sessions.
"""

import sqlite3
import hashlib
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone
from itertools import combinations

DB_PATH = Path.home() / ".claude-mem" / "claude-mem.db"
CRYSTAL_DIR = Path.home() / ".claude-mem" / "crystallized"
PROCEDURE_DIR = Path.home() / ".claude-mem" / "procedures"

MIN_PATTERN_LENGTH = 3    # minimum steps in a procedure
MIN_OCCURRENCES = 3       # minimum times the pattern must appear
MAX_PROCEDURES = 5        # max procedures to extract per run


def extract_crystal_observation_ids(crystal_path: Path) -> list[int]:
    """Parse observation IDs from a crystal's header."""
    content = crystal_path.read_text()
    for line in content.split('\n'):
        if line.startswith('Source observations:'):
            # Format: "Source observations: 8 (IDs: 42, 55, 67, ...)"
            match = re.search(r'IDs:\s*(.+?)\)', line)
            if match:
                return [int(x.strip()) for x in match.group(1).split(',') if x.strip().isdigit()]
    return []


def fetch_observation_sequences(conn, all_ids: list[int]) -> dict[str, list[dict]]:
    """
    Fetch observations and group by session.
    Returns: {session_id: [obs1, obs2, ...]} ordered by time.
    """
    if not all_ids:
        return {}

    placeholders = ','.join('?' * len(all_ids))
    rows = conn.execute(f"""
        SELECT id, memory_session_id, type, title, concepts,
               files_modified, created_at_epoch
        FROM observations
        WHERE id IN ({placeholders})
        ORDER BY created_at_epoch ASC
    """, all_ids).fetchall()

    sessions = defaultdict(list)
    for row in rows:
        sessions[row['memory_session_id']].append(dict(row))

    return dict(sessions)


def extract_type_sequences(sessions: dict[str, list[dict]]) -> list[list[str]]:
    """
    Extract action type sequences from each session.
    Returns list of sequences like [['decision', 'change', 'bugfix', 'change'], ...]
    """
    sequences = []
    for session_id, obs_list in sessions.items():
        if len(obs_list) >= MIN_PATTERN_LENGTH:
            seq = [obs['type'] for obs in obs_list]
            sequences.append(seq)
    return sequences


def find_common_subsequences(sequences: list[list[str]]) -> list[tuple[tuple[str, ...], int]]:
    """
    Find type subsequences of length ≥ MIN_PATTERN_LENGTH
    that appear in ≥ MIN_OCCURRENCES different sequences.
    """
    # Extract all subsequences of length MIN_PATTERN_LENGTH to 6
    subseq_counts = Counter()

    for seq in sequences:
        seen_in_this_seq = set()
        for length in range(MIN_PATTERN_LENGTH, min(len(seq) + 1, 7)):
            for i in range(len(seq) - length + 1):
                subseq = tuple(seq[i:i + length])
                if subseq not in seen_in_this_seq:
                    seen_in_this_seq.add(subseq)
                    subseq_counts[subseq] += 1

    # Filter to those appearing ≥ MIN_OCCURRENCES times
    common = [(subseq, count) for subseq, count in subseq_counts.items()
              if count >= MIN_OCCURRENCES]

    # Sort by length * count (prefer longer, more frequent patterns)
    common.sort(key=lambda x: len(x[0]) * x[1], reverse=True)

    return common[:MAX_PROCEDURES]


def collect_pattern_examples(
    sessions: dict[str, list[dict]],
    pattern: tuple[str, ...]
) -> list[list[dict]]:
    """Find actual observation sequences matching the pattern."""
    examples = []
    pattern_len = len(pattern)

    for session_id, obs_list in sessions.items():
        types = [obs['type'] for obs in obs_list]
        for i in range(len(types) - pattern_len + 1):
            if tuple(types[i:i + pattern_len]) == pattern:
                examples.append(obs_list[i:i + pattern_len])
                break  # one per session

    return examples


def build_procedure_markdown(
    pattern: tuple[str, ...],
    occurrences: int,
    examples: list[list[dict]]
) -> str:
    """Build a procedure template from detected pattern + examples."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    # Collect common files and titles across examples
    all_files = Counter()
    step_titles = defaultdict(list)

    for example in examples:
        for i, obs in enumerate(example):
            if obs.get('files_modified'):
                for f in obs['files_modified'].split(','):
                    f = f.strip()
                    if f:
                        all_files[f] += 1
            step_titles[i].append(obs.get('title', '(untitled)'))

    # Build step descriptions from most common titles
    steps = []
    for i, step_type in enumerate(pattern):
        titles = step_titles.get(i, [])
        # Pick the most representative title (longest, as a heuristic)
        best_title = max(titles, key=len) if titles else f"Step {i+1}"
        steps.append(f"{i+1}. **[{step_type}]** {best_title}")

    # Collect common concepts
    all_concepts = Counter()
    for example in examples:
        for obs in example:
            if obs.get('concepts'):
                for c in obs['concepts'].split(','):
                    c = c.strip()
                    if c:
                        all_concepts[c] += 1

    # Derive a procedure name from the most common concepts
    top_concepts = [c for c, _ in all_concepts.most_common(3)]
    procedure_name = ' + '.join(top_concepts) if top_concepts else ' -> '.join(pattern)

    # Source session count
    session_ids = set()
    for example in examples:
        for obs in example:
            session_ids.add(obs.get('memory_session_id', '?'))

    lines = [
        f"# Procedure: {procedure_name}",
        "",
        f"Tier: PROCEDURAL | Detected: {now}",
        f"Confidence: {occurrences} occurrences across {len(session_ids)} sessions",
        f"Pattern: {' -> '.join(pattern)}",
        "",
        "## Steps",
        "",
    ]
    lines.extend(steps)
    lines.append("")

    # Files typically modified
    common_files = [f for f, count in all_files.most_common(10) if count >= 2]
    if common_files:
        lines.append("## Files Typically Modified")
        for f in common_files:
            lines.append(f"- `{f}`")
        lines.append("")

    # Concepts involved
    if top_concepts:
        lines.append("## Concepts")
        for c in top_concepts:
            lines.append(f"- {c}")
        lines.append("")

    # Example instances
    lines.append("## Example Instances")
    for j, example in enumerate(examples[:3]):  # show up to 3
        obs_ids = [str(obs['id']) for obs in example]
        lines.append(f"- Instance {j+1}: observations #{', #'.join(obs_ids)}")
    lines.append("")

    return '\n'.join(lines)


def procedure_hash(pattern: tuple[str, ...]) -> str:
    """Stable hash for a pattern."""
    key = '-'.join(pattern)
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def build_index(procedure_dir: Path):
    """Rebuild the procedures index."""
    procedures = sorted(procedure_dir.glob("*.md"))
    procedures = [p for p in procedures if p.name != "INDEX.md"]

    lines = [
        "# Procedural Knowledge Index",
        "",
        f"Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC",
        f"Total procedures: {len(procedures)}",
        "",
        "| Procedure | Pattern | Confidence |",
        "|-----------|---------|------------|",
    ]

    for proc_path in procedures:
        content = proc_path.read_text()
        name = proc_path.stem
        pattern = "?"
        confidence = "?"

        for line in content.split('\n'):
            if line.startswith('# Procedure:'):
                name = line.replace('# Procedure:', '').strip()
            if line.startswith('Pattern:'):
                pattern = line.replace('Pattern:', '').strip()
            if line.startswith('Confidence:'):
                confidence = line.replace('Confidence:', '').strip()

        lines.append(f"| [{name}]({proc_path.name}) | {pattern} | {confidence} |")

    lines.append("")
    (procedure_dir / "INDEX.md").write_text('\n'.join(lines))


def run():
    if not DB_PATH.exists():
        return
    if not CRYSTAL_DIR.exists() or not list(CRYSTAL_DIR.glob("*.md")):
        return

    PROCEDURE_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row

    # Collect all observation IDs from all crystals
    all_ids = []
    for crystal_path in CRYSTAL_DIR.glob("*.md"):
        if crystal_path.name == "INDEX.md":
            continue
        ids = extract_crystal_observation_ids(crystal_path)
        all_ids.extend(ids)

    all_ids = list(set(all_ids))
    if len(all_ids) < MIN_PATTERN_LENGTH * MIN_OCCURRENCES:
        conn.close()
        return

    # Group by session
    sessions = fetch_observation_sequences(conn, all_ids)

    if len(sessions) < MIN_OCCURRENCES:
        conn.close()
        return

    # Find repeated patterns
    sequences = extract_type_sequences(sessions)
    common_patterns = find_common_subsequences(sequences)

    if not common_patterns:
        conn.close()
        return

    # Build procedures
    created = 0
    for pattern, occurrences in common_patterns:
        p_hash = procedure_hash(pattern)
        proc_path = PROCEDURE_DIR / f"{p_hash}.md"

        # Skip if already exists (don't overwrite)
        if proc_path.exists():
            continue

        examples = collect_pattern_examples(sessions, pattern)
        if len(examples) < MIN_OCCURRENCES:
            continue

        markdown = build_procedure_markdown(pattern, occurrences, examples)
        proc_path.write_text(markdown)
        created += 1

    if created > 0:
        build_index(PROCEDURE_DIR)

    conn.close()


if __name__ == "__main__":
    try:
        run()
    except Exception:
        pass
