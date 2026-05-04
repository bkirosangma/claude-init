#!/usr/bin/env python3
"""
Generate the "Nodes Involved" and "Connections" markdown tables for a flow
explanation document. Data is extracted directly from the diagram JSON —
no LLM work required.

Usage:
  kb_flow_tables.py --diagram <path.json> --flow <flow-id>

Output: markdown tables printed to stdout, ready to paste into a flow .md file.

The LLM still writes the prose paragraph at the top of the flow doc.
This script only generates the two mechanical tables below it.
"""

import argparse
import json
import sys
from pathlib import Path


def generate(diagram_path: str, flow_id: str) -> str:
    try:
        data = json.loads(Path(diagram_path).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        print(f'Error reading {diagram_path}: {e}', file=sys.stderr)
        sys.exit(1)

    nodes_by_id  = {n['id']: n for n in data.get('nodes',       []) if isinstance(n, dict) and 'id' in n}
    conns_by_id  = {c['id']: c for c in data.get('connections', []) if isinstance(c, dict) and 'id' in c}

    flow = next(
        (f for f in data.get('flows', []) if isinstance(f, dict) and f.get('id') == flow_id),
        None,
    )
    if flow is None:
        print(f'Error: flow "{flow_id}" not found in {diagram_path}', file=sys.stderr)
        sys.exit(1)

    conn_ids  = flow.get('connectionIds', [])
    flow_conns = [conns_by_id[cid] for cid in conn_ids if cid in conns_by_id]

    # ── Nodes Involved (traversal order, deduplicated) ─────────────────────────
    seen: set[str] = set()
    ordered_nodes: list[str] = []
    for C in flow_conns:
        for ref in (C.get('from'), C.get('to')):
            if ref and ref not in seen:
                seen.add(ref); ordered_nodes.append(ref)

    node_rows = []
    for nid in ordered_nodes:
        n = nodes_by_id.get(nid)
        if n:
            label = n.get('label', nid)
            sub   = n.get('sub', '').strip()
            node_rows.append(f'| {label} | {sub or "—"} |')

    nodes_table = (
        '## Nodes Involved\n\n'
        '| Node | Role in Flow |\n'
        '|------|-------------|\n'
        + '\n'.join(node_rows)
    )

    # ── Connections ────────────────────────────────────────────────────────────
    conn_rows = []
    for C in flow_conns:
        from_n = nodes_by_id.get(C.get('from', ''), {})
        to_n   = nodes_by_id.get(C.get('to',   ''), {})
        conn_rows.append(
            f'| {from_n.get("label", C.get("from", "?"))} '
            f'| {to_n.get("label",   C.get("to",   "?"))} '
            f'| {C.get("label", "—")} |'
        )

    conns_table = (
        '## Connections\n\n'
        '| From | To | What flows |\n'
        '|------|----|-----------|\n'
        + '\n'.join(conn_rows)
    )

    return nodes_table + '\n\n' + conns_table


def main():
    ap = argparse.ArgumentParser(
        description='Generate flow explanation tables from a diagram JSON.',
    )
    ap.add_argument('--diagram', required=True, help='Path to diagram .json file')
    ap.add_argument('--flow',    default=None,  help='Flow ID (e.g. flow-auth-code)')
    ap.add_argument('--list-flows', action='store_true',
                    help='List all flow IDs in the diagram and exit')
    args = ap.parse_args()

    if not args.list_flows and not args.flow:
        ap.error('--flow is required unless --list-flows is set')

    if args.list_flows:
        try:
            data = json.loads(Path(args.diagram).read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as e:
            print(f'Error: {e}', file=sys.stderr); sys.exit(1)
        for f in data.get('flows', []):
            if isinstance(f, dict):
                print(f'{f.get("id", "?")}  {f.get("name", "")}')
        return

    print(generate(args.diagram, args.flow))


if __name__ == '__main__':
    main()
