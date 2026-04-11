#!/usr/bin/env python3
"""
gather-context.py — Unified context gatherer for compound intelligence.

Queries all three memory systems and outputs a structured "Prior Knowledge"
section for subagent prompts.

Systems:
  1. graphify  (structural) — graph.json community/neighbor data
  2. claude-mem (temporal)  — SQLite FTS on observations
  3. MEMORY.md (curated)    — project-specific memory files

Usage:
  python3 gather-context.py [file_paths...]
  python3 gather-context.py --query "search terms"
  python3 gather-context.py src/components/Header.tsx src/utils/types.ts
"""

import sys
import os
import json
import sqlite3
import re
from pathlib import Path
from difflib import SequenceMatcher

# ── Path Resolution (global — works for any project) ──

def find_graphify_dir() -> Path | None:
    """Walk up from CWD to find graphify-out/graph.json."""
    d = Path.cwd()
    while d != d.parent:
        gf = d / "graphify-out" / "graph.json"
        if gf.exists():
            return d / "graphify-out"
        d = d.parent
    return None

def find_memory_dir() -> Path | None:
    """Compute the MEMORY.md directory for the current project."""
    cwd = str(Path.cwd())
    # /Users/kiro/foo → -Users-kiro-foo
    slug = cwd.replace("/", "-")
    if not slug.startswith("-"):
        slug = "-" + slug
    mem_dir = Path.home() / ".claude" / "projects" / slug / "memory"
    return mem_dir if mem_dir.is_dir() else None

def get_claude_mem_db() -> Path | None:
    """Return claude-mem SQLite DB path."""
    db = Path.home() / ".claude-mem" / "claude-mem.db"
    return db if db.exists() else None


# ── Graphify: Structural Context ──

def query_graphify(file_paths: list[str], graph_dir: Path) -> list[str]:
    """Find graph nodes matching the given files and return neighbor context."""
    graph_file = graph_dir / "graph.json"
    try:
        with open(graph_file) as f:
            g = json.load(f)
    except Exception:
        return []

    nodes = {n["id"]: n for n in g.get("nodes", [])}
    links = g.get("links", [])
    results = []

    for fp in file_paths:
        basename = os.path.basename(fp).lower()
        fp_lower = fp.lower()

        # Find matching node
        match_id = None
        for nid, n in nodes.items():
            label = n.get("label", "").lower()
            src = n.get("source_file", "").lower()
            if basename in label or basename in src or fp_lower.endswith(src):
                match_id = nid
                break

        if not match_id:
            continue

        node = nodes[match_id]
        community = node.get("community", "?")
        label = node.get("label", basename)

        # Find neighbors (1 hop)
        neighbors = []
        for link in links:
            src, tgt = link.get("source", ""), link.get("target", "")
            rel = link.get("relation", "related_to")
            if src == match_id and tgt in nodes:
                neighbors.append(f"  -> {nodes[tgt].get('label', tgt)} [{rel}]")
            elif tgt == match_id and src in nodes:
                neighbors.append(f"  <- {nodes[src].get('label', src)} [{rel}]")

        entry = f"- {label} is in Community {community}"
        if neighbors:
            entry += ", connected to:\n" + "\n".join(neighbors[:8])
            total = len(neighbors)
            if total > 8:
                entry += f"\n  ... and {total - 8} more"
        results.append(entry)

    return results


# ── Claude-Mem: Temporal Context ──

def query_claude_mem(search_terms: list[str], db_path: Path, limit: int = 10) -> list[str]:
    """Query claude-mem SQLite DB using FTS for relevant observations."""
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception:
        return []

    results = []
    seen_ids = set()

    for term in search_terms:
        # Clean term for FTS (remove extensions, path separators)
        clean = os.path.basename(term)
        clean = os.path.splitext(clean)[0]
        # Split camelCase/PascalCase into words
        words = re.sub(r'([a-z])([A-Z])', r'\1 \2', clean)
        fts_query = words.replace("-", " ").replace("_", " ")

        try:
            cursor.execute("""
                SELECT id, title, type, narrative, created_at
                FROM observations
                WHERE id IN (
                    SELECT rowid FROM observations_fts
                    WHERE observations_fts MATCH ?
                )
                ORDER BY created_at DESC
                LIMIT ?
            """, (fts_query, limit))

            for row in cursor.fetchall():
                if row["id"] in seen_ids:
                    continue
                seen_ids.add(row["id"])
                date = row["created_at"][:10] if row["created_at"] else "?"
                obs_type = row["type"] or "note"
                title = row["title"] or "Untitled"
                narrative = row["narrative"] or ""
                # Truncate narrative to first sentence
                first_sentence = narrative.split(".")[0] + "." if narrative else ""
                results.append(f"- [{date}] {obs_type}: {title}")
                if first_sentence and len(first_sentence) < 200:
                    results.append(f"  {first_sentence}")
        except Exception:
            continue

    conn.close()
    return results[:limit]


# ── MEMORY.md: Curated Context ──

def query_memory(file_paths: list[str], memory_dir: Path) -> list[str]:
    """Scan MEMORY.md entries for relevance to the given files."""
    results = []
    search_terms = set()
    for fp in file_paths:
        base = os.path.basename(fp).lower()
        base_no_ext = os.path.splitext(base)[0]
        search_terms.add(base)
        search_terms.add(base_no_ext)
        # Add camelCase parts
        parts = re.sub(r'([a-z])([A-Z])', r'\1 \2', base_no_ext).lower().split()
        search_terms.update(parts)

    for f in os.listdir(memory_dir):
        if f == "MEMORY.md" or not f.endswith(".md"):
            continue
        path = memory_dir / f
        try:
            content = path.read_text()
        except Exception:
            continue

        content_lower = content.lower()
        # Check if any search term appears in the memory
        relevant = any(term in content_lower for term in search_terms if len(term) > 2)

        if relevant:
            # Extract name and description from frontmatter
            name = ""
            desc = ""
            for line in content.split("\n"):
                if line.startswith("name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
            if name:
                entry = f"- {name}"
                if desc:
                    entry += f": {desc}"
                results.append(entry)

    # Also include ALL memories if no file-specific matches (they're user preferences)
    if not results:
        memory_index = memory_dir / "MEMORY.md"
        if memory_index.exists():
            for line in memory_index.read_text().split("\n"):
                line = line.strip()
                if line.startswith("- ["):
                    # Extract the hook text after ] —
                    match = re.search(r"\]\([^)]+\)\s*[—–-]\s*(.+)", line)
                    if match:
                        results.append(f"- {match.group(1)}")

    return results


# ── Deduplication ──

def deduplicate(memories: list[str], observations: list[str]) -> tuple[list[str], list[str]]:
    """Remove observations that substantially overlap with MEMORY.md entries."""
    if not memories or not observations:
        return memories, observations

    filtered = []
    for obs in observations:
        is_dup = False
        obs_lower = obs.lower()
        for mem in memories:
            if SequenceMatcher(None, obs_lower, mem.lower()).ratio() > 0.6:
                is_dup = True
                break
        if not is_dup:
            filtered.append(obs)
    return memories, filtered


# ── Main ──

def main():
    # Parse args
    args = sys.argv[1:]
    query_mode = False
    search_terms = []

    if "--query" in args:
        idx = args.index("--query")
        query_mode = True
        search_terms = args[idx + 1:]
        args = args[:idx]

    file_paths = args if args else []

    # If no files and no query, print usage
    if not file_paths and not search_terms:
        print("Usage: gather-context.py [file_paths...] [--query search terms]", file=sys.stderr)
        sys.exit(1)

    # Resolve system paths
    graph_dir = find_graphify_dir()
    memory_dir = find_memory_dir()
    claude_mem_db = get_claude_mem_db()

    sections = []

    # 1. Structural context
    if graph_dir and file_paths:
        structural = query_graphify(file_paths, graph_dir)
        if structural:
            sections.append("### Structural Context (graphify)\n" + "\n".join(structural))

    # 2. Temporal context
    if claude_mem_db:
        terms = search_terms if query_mode else file_paths
        temporal = query_claude_mem(terms, claude_mem_db)
    else:
        temporal = []

    # 3. Curated context
    if memory_dir:
        curated = query_memory(file_paths if file_paths else search_terms, memory_dir)
    else:
        curated = []

    # 4. Deduplicate across systems
    curated, temporal = deduplicate(curated, temporal)

    if temporal:
        sections.append("### Temporal Context (claude-mem)\n" + "\n".join(temporal))
    if curated:
        sections.append("### User Preferences (MEMORY.md)\n" + "\n".join(curated))

    # Output
    if sections:
        print("## Prior Knowledge\n")
        print("\n\n".join(sections))
    else:
        print("(No relevant context found across memory systems)", file=sys.stderr)


if __name__ == "__main__":
    main()
