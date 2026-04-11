#!/usr/bin/env python3
"""
Confidence decay scoring for hybrid-search.
Applies Ebbinghaus-inspired forgetting curve to observation rankings.

Usage:
  # As a library (imported by other scripts):
  from decay import compute_decay, apply_decay_to_results

  # Standalone test:
  python3 decay.py <observation_id> [<observation_id> ...]
"""

import math
import sqlite3
import sys
import time
from pathlib import Path

DB_PATH = Path.home() / ".claude-mem" / "claude-mem.db"

# Default half-life: 30 days (observations lose half their weight per month)
BASE_HALF_LIFE_DAYS = 30

# Reinforcement bonus: each relevance_count point adds 50% to half-life
REINFORCEMENT_FACTOR = 0.5

# Crystallized observations (relevance_count == -1) get minimal weight
# since their value is captured in the crystal
CRYSTALLIZED_DECAY = 0.1

# ln(2) for the exponential decay formula
LN2 = 0.6931471805599453


def compute_decay(created_at_epoch_ms: int, relevance_count: int = 0, now_ms: int = None) -> float:
    """
    Compute decay score for a single observation.

    Returns a float between 0.0 and 1.0:
    - 1.0 = brand new observation
    - 0.5 = observation at its half-life
    - 0.0 = infinitely old

    Special cases:
    - relevance_count == -1: crystallized, returns CRYSTALLIZED_DECAY (0.1)
    - relevance_count > 0: extended half-life (frequently accessed = slower decay)
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)

    # Crystallized observations are deprioritized
    if relevance_count == -1:
        return CRYSTALLIZED_DECAY

    age_days = (now_ms - created_at_epoch_ms) / 86400000.0

    if age_days <= 0:
        return 1.0

    # Extend half-life for reinforced observations
    half_life = BASE_HALF_LIFE_DAYS * (1 + REINFORCEMENT_FACTOR * max(0, relevance_count))

    # Exponential decay: score = exp(-ln(2) * age / half_life)
    decay = math.exp(-LN2 * age_days / half_life)

    return max(0.001, decay)  # floor at 0.001 to never fully zero out


def apply_decay_to_results(results: list[dict], now_ms: int = None) -> list[dict]:
    """
    Apply decay scoring to a list of search results.

    Each result dict should have:
      - 'id': observation ID
      - 'created_at_epoch': epoch ms
      - 'relevance_count': int (default 0)
      - 'rrf_score': float (optional, from RRF fusion)

    Returns the same list with 'decay_score' and 'final_score' added,
    sorted by final_score descending.
    """
    if now_ms is None:
        now_ms = int(time.time() * 1000)

    for r in results:
        decay = compute_decay(
            r.get('created_at_epoch', now_ms),
            r.get('relevance_count', 0),
            now_ms
        )
        r['decay_score'] = round(decay, 4)

        # Multiply RRF score by decay (or use decay alone if no RRF)
        rrf = r.get('rrf_score', 1.0)
        r['final_score'] = round(rrf * decay, 6)

    results.sort(key=lambda r: r['final_score'], reverse=True)
    return results


def fetch_and_score(observation_ids: list[int]) -> list[dict]:
    """
    Fetch observations from the DB and compute their decay scores.
    """
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(str(DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row

    placeholders = ','.join('?' * len(observation_ids))
    rows = conn.execute(f"""
        SELECT id, title, type, concepts, created_at_epoch, relevance_count
        FROM observations
        WHERE id IN ({placeholders})
    """, observation_ids).fetchall()
    conn.close()

    results = [dict(row) for row in rows]
    return apply_decay_to_results(results)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 decay.py <id1> [<id2> ...]")
        sys.exit(1)

    ids = [int(x) for x in sys.argv[1:]]
    scored = fetch_and_score(ids)

    for r in scored:
        age_days = (time.time() * 1000 - r['created_at_epoch']) / 86400000
        print(f"  #{r['id']} [{r['type']}] \"{r['title']}\"")
        print(f"    age={age_days:.1f}d  relevance={r['relevance_count']}  decay={r['decay_score']}  final={r['final_score']}")
