#!/usr/bin/env python3
"""
Validate (and optionally fix) knowledge-base files.

Routes by extension:
  .json — diagram schema validation (layers, nodes, connections, flows)
  .md   — document convention validation (frontmatter, wiki-links, headings)

Usage:
  kb_validate.py <path-or-glob> [--fix] [--vault-root <path>] [--json]

Exit codes:
  0 — no errors found
  1 — errors found
  2 — fatal parse failure (invalid JSON; --fix will not write)
"""

import argparse
import copy
import glob
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_utils import backup_file, detect_vault

SCRIPTS_DIR = Path(__file__).parent

# ── Regex constants ────────────────────────────────────────────────────────────
RE_LAYER_ID = re.compile(r'^ly-[a-z0-9-]+$')
RE_NODE_ID  = re.compile(r'^el-[a-z0-9-]+$')
RE_CONN_ID  = re.compile(r'^dl-[a-z0-9-]+$')
RE_FLOW_ID  = re.compile(r'^flow-[a-z0-9-]+$')
RE_HEX6     = re.compile(r'^#[0-9a-fA-F]{6}$')
RE_HEX3     = re.compile(r'^#[0-9a-fA-F]{3}$')
RE_ANCHOR   = re.compile(r'^(top|right|bottom|left)-[0-9]+$|^cond-(out|in)-[0-9]+$')

SLATE_BG     = '#f1f5f9'
SLATE_BORDER = '#cbd5e1'
SLATE_COLOR  = '#64748b'
VALID_CURVES = {'orthogonal', 'curved', 'straight', 'bezier'}


def _kebab(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', str(s).lower()).strip('-') or 'id'


def _expand_hex3(c: str) -> str:
    return '#' + ''.join(ch * 2 for ch in c[1:]) if RE_HEX3.match(c) else c


def _finite(v) -> bool:
    return isinstance(v, (int, float)) and math.isfinite(v)


def _valid_color(c) -> bool:
    return isinstance(c, str) and (RE_HEX6.match(c) or RE_HEX3.match(c))


# ── Diagnostic ─────────────────────────────────────────────────────────────────

class Diag:
    __slots__ = ('level', 'section', 'msg', 'fixable')

    def __init__(self, level: str, section: str, msg: str, fixable: bool = False):
        self.level   = level    # 'error' | 'warning' | 'info'
        self.section = section
        self.msg     = msg
        self.fixable = fixable

    def glyph(self) -> str:
        return {'error': '✗', 'warning': '⚠', 'info': 'ℹ'}[self.level]


class Result:
    def __init__(self):
        self.diags: list[Diag] = []
        self.id_remap: dict[str, str] = {}   # old_id -> new_id

    def add(self, level, section, msg, fixable=False):
        self.diags.append(Diag(level, section, msg, fixable))

    @property
    def errors(self):   return [d for d in self.diags if d.level == 'error']
    @property
    def warnings(self): return [d for d in self.diags if d.level == 'warning']
    @property
    def infos(self):    return [d for d in self.diags if d.level == 'info']


# ── Validator ──────────────────────────────────────────────────────────────────

def validate(data: dict, path: str = '') -> Result:
    r = Result()
    basename = Path(path).stem if path else 'diagram'

    # Top-level
    if 'title' not in data:
        r.add('warning', 'schema', f'title missing — would default to "{re.sub(chr(45)+chr(95), " ", basename).title()}"', True)
    elif not isinstance(data.get('title'), str):
        r.add('warning', 'schema', 'title is not a string — would coerce', True)

    for req in ('layers', 'nodes', 'connections'):
        if req not in data:
            r.add('error', 'schema', f'"{req}" is required but missing')
        elif not isinstance(data[req], list):
            r.add('error', 'schema', f'"{req}" must be an array')

    for opt, dflt in [('layerManualSizes', '{}'), ('lineCurve', '"bezier"'), ('flows', '[]')]:
        if opt not in data:
            r.add('warning', 'schema', f'"{opt}" missing — would default to {dflt}', True)

    lc = data.get('lineCurve')
    if lc is not None and lc not in VALID_CURVES:
        r.add('warning', 'schema', f'lineCurve "{lc}" invalid — would replace with "bezier"', True)

    lms = data.get('layerManualSizes')
    if lms is not None and (not isinstance(lms, dict) or isinstance(lms, list)):
        r.add('warning', 'schema', 'layerManualSizes must be a plain object — would reset to {}', True)

    layers      = data.get('layers',      []) if isinstance(data.get('layers'),      list) else []
    nodes       = data.get('nodes',       []) if isinstance(data.get('nodes'),       list) else []
    connections = data.get('connections', []) if isinstance(data.get('connections'), list) else []
    flows       = data.get('flows',       []) if isinstance(data.get('flows'),       list) else []

    # ── Layers
    seen_lids: dict[str, int] = {}
    valid_lids: set[str] = set()

    for i, L in enumerate(layers):
        if not isinstance(L, dict):
            r.add('error', 'layers', f'layers[{i}] is not an object'); continue
        lid = L.get('id')
        if lid is None:
            r.add('error', 'layers', f'layers[{i}]: id is missing')
        elif not isinstance(lid, str):
            r.add('error', 'layers', f'layers[{i}]: id must be a string')
        elif not RE_LAYER_ID.match(lid):
            new = 'ly-' + _kebab(lid)
            r.add('warning', 'layers', f'layers[{i}]: id "{lid}" malformed — would rewrite to "{new}"', True)
            r.id_remap[lid] = new
            if lid not in seen_lids:
                seen_lids[lid] = i; valid_lids.add(new)
        elif lid in seen_lids:
            r.add('error', 'layers', f'layers[{i}]: duplicate id "{lid}"')
        else:
            seen_lids[lid] = i; valid_lids.add(lid)

        t = L.get('title')
        if not t or not isinstance(t, str) or not t.strip():
            r.add('warning', 'layers', f'layers[{i}]: title missing/empty — would default to "UNTITLED LAYER"', True)
        elif t != t.upper():
            r.add('info', 'layers', f'layers[{i}]: title "{t}" is lowercase — convention prefers uppercase')

        for cf in ('bg', 'border'):
            cv = L.get(cf)
            if cv is None:
                r.add('warning', 'layers', f'layers[{i}]: {cf} missing — would default to slate', True)
            elif RE_HEX3.match(str(cv)):
                r.add('warning', 'layers', f'layers[{i}]: {cf} "{cv}" is 3-digit hex — would expand to "{_expand_hex3(cv)}"', True)
            elif not RE_HEX6.match(str(cv)):
                r.add('warning', 'layers', f'layers[{i}]: {cf} "{cv}" is not a valid hex color — would replace with slate', True)

    # ── Nodes
    seen_nids: dict[str, int] = {}
    valid_nids: set[str] = set()

    for i, N in enumerate(nodes):
        if not isinstance(N, dict):
            r.add('error', 'nodes', f'nodes[{i}] is not an object'); continue
        nid = N.get('id')
        if nid is None:
            r.add('error', 'nodes', f'nodes[{i}]: id is missing')
        elif not isinstance(nid, str):
            r.add('error', 'nodes', f'nodes[{i}]: id must be a string')
        elif not RE_NODE_ID.match(nid):
            new = 'el-' + _kebab(nid)
            r.add('warning', 'nodes', f'nodes[{i}]: id "{nid}" malformed — would rewrite to "{new}"', True)
            r.id_remap[nid] = new
            if nid not in seen_nids:
                seen_nids[nid] = i; valid_nids.add(new)
        elif nid in seen_nids:
            r.add('error', 'nodes', f'nodes[{i}]: duplicate id "{nid}"')
        else:
            seen_nids[nid] = i; valid_nids.add(nid)

        if not N.get('label') or not isinstance(N.get('label'), str):
            r.add('warning', 'nodes', f'nodes[{i}]: label missing/empty — would default to "Untitled"', True)
        icon = N.get('icon')
        if icon is None or icon == '' or not isinstance(icon, str):
            r.add('warning', 'nodes', f'nodes[{i}]: icon invalid — would default to "Database"', True)
        for coord, dflt in (('x', 750), ('y', 100)):
            if not _finite(N.get(coord)):
                r.add('warning', 'nodes', f'nodes[{i}]: {coord} missing/invalid — would default to {dflt}', True)
        if not _finite(N.get('w')):
            r.add('warning', 'nodes', f'nodes[{i}]: w missing/invalid — would default to 210', True)

        if N.get('shape') != 'condition':
            nl = N.get('layer')
            eff = r.id_remap.get(nl, nl)
            if nl is None:
                r.add('error', 'nodes', f'nodes[{i}]: layer is required for non-condition nodes')
            elif eff not in valid_lids:
                r.add('error', 'nodes', f'nodes[{i}]: layer "{nl}" does not exist — would clear under --fix', True)

    # ── Connections
    seen_cids: dict[str, int] = {}
    valid_cids: set[str] = set()

    for i, C in enumerate(connections):
        if not isinstance(C, dict):
            r.add('error', 'connections', f'connections[{i}] is not an object'); continue
        cid = C.get('id')
        if cid is None:
            r.add('error', 'connections', f'connections[{i}]: id is missing')
        elif not isinstance(cid, str):
            r.add('error', 'connections', f'connections[{i}]: id must be a string')
        elif not RE_CONN_ID.match(cid):
            new = 'dl-' + _kebab(cid)
            r.add('warning', 'connections', f'connections[{i}]: id "{cid}" malformed — would rewrite to "{new}"', True)
            r.id_remap[cid] = new
            if cid not in seen_cids:
                seen_cids[cid] = i; valid_cids.add(new)
        elif cid in seen_cids:
            r.add('error', 'connections', f'connections[{i}]: duplicate id "{cid}"')
        else:
            seen_cids[cid] = i; valid_cids.add(cid)

        for ref in ('from', 'to'):
            rv = C.get(ref)
            eff = r.id_remap.get(rv, rv)
            if rv is None:
                r.add('error', 'connections', f'connections[{i}]: {ref} is missing')
            elif eff not in valid_nids:
                r.add('error', 'connections', f'connections[{i}]: {ref} "{rv}" is not a known node — would drop connection', True)

        for af, dflt in (('fromAnchor', 'bottom-1'), ('toAnchor', 'top-1')):
            av = C.get(af)
            if av is None or not isinstance(av, str) or not RE_ANCHOR.match(av):
                r.add('warning', 'connections', f'connections[{i}]: {af} {"missing" if av is None else f"invalid: {av!r}"} — would default to "{dflt}"', True)

        cc = C.get('color')
        if not _valid_color(cc):
            r.add('warning', 'connections', f'connections[{i}]: color {cc!r} invalid — would replace with slate', True)
        elif RE_HEX3.match(str(cc)):
            r.add('warning', 'connections', f'connections[{i}]: color "{cc}" is 3-digit hex — would expand', True)

        lp = C.get('labelPosition')
        if lp is not None and (not isinstance(lp, (int, float)) or not 0 <= lp <= 1):
            r.add('warning', 'connections', f'connections[{i}]: labelPosition {lp!r} out of [0,1] — would clamp', True)

    # ── Flows
    seen_fids: set[str] = set()

    for i, F in enumerate(flows):
        if not isinstance(F, dict):
            r.add('error', 'flows', f'flows[{i}] is not an object'); continue
        fid = F.get('id')
        if fid is None:
            r.add('error', 'flows', f'flows[{i}]: id is missing')
        elif not isinstance(fid, str):
            r.add('error', 'flows', f'flows[{i}]: id must be a string')
        elif not RE_FLOW_ID.match(fid):
            r.add('warning', 'flows', f'flows[{i}]: id "{fid}" malformed — should match flow-[a-z0-9-]+', True)
        elif fid in seen_fids:
            r.add('error', 'flows', f'flows[{i}]: duplicate id "{fid}"')
        else:
            seen_fids.add(fid)

        if not F.get('name') or not isinstance(F.get('name'), str):
            r.add('warning', 'flows', f'flows[{i}]: name missing/empty — would default to "Flow"', True)

        cids = F.get('connectionIds', [])
        if not isinstance(cids, list):
            r.add('error', 'flows', f'flows[{i}]: connectionIds must be an array'); continue

        # Resolve and check IDs
        eff_cids = []
        for cid in cids:
            eff = r.id_remap.get(cid, cid)
            if eff not in valid_cids:
                r.add('warning', 'flows', f'flows[{i}]: connectionIds contains unknown "{cid}" — would drop', True)
            else:
                eff_cids.append(eff)

        # Contiguity
        if len(eff_cids) > 1:
            conn_ep: dict[str, tuple] = {}
            for C in connections:
                if isinstance(C, dict):
                    eid = r.id_remap.get(C.get('id', ''), C.get('id', ''))
                    if eid in eff_cids:
                        conn_ep[eid] = (
                            r.id_remap.get(C.get('from', ''), C.get('from', '')),
                            r.id_remap.get(C.get('to',   ''), C.get('to',   '')),
                        )
            parent = {c: c for c in eff_cids}

            def _find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]; x = parent[x]
                return x

            clist = list(conn_ep)
            for j in range(len(clist)):
                for k in range(j + 1, len(clist)):
                    if set(conn_ep.get(clist[j], ())) & set(conn_ep.get(clist[k], ())):
                        parent[_find(clist[j])] = _find(clist[k])

            comps: dict[str, list] = {}
            for c in eff_cids:
                comps.setdefault(_find(c), []).append(c)
            if len(comps) > 1:
                parts = '; '.join('{' + ', '.join(v) + '}' for v in comps.values())
                r.add('error', 'flows',
                      f'flows[{i}] "{F.get("name", "")}": not contiguous ({len(comps)} components: {parts}) — would split under --fix',
                      True)

    # ── Semantic checks (info-level)
    used_layers = {r.id_remap.get(N.get('layer', ''), N.get('layer', ''))
                   for N in nodes if isinstance(N, dict)}
    for L in layers:
        if isinstance(L, dict):
            lid = r.id_remap.get(L.get('id', ''), L.get('id', ''))
            if lid and lid not in used_layers:
                r.add('info', 'semantic', f'layer "{L.get("id")}" has no nodes')

    connected = set()
    for C in connections:
        if isinstance(C, dict):
            connected.add(r.id_remap.get(C.get('from', ''), C.get('from', '')))
            connected.add(r.id_remap.get(C.get('to',   ''), C.get('to',   '')))
    for N in nodes:
        if isinstance(N, dict):
            nid = r.id_remap.get(N.get('id', ''), N.get('id', ''))
            if nid and nid not in connected:
                r.add('info', 'semantic', f'node "{N.get("id")}" has no connections (standalone)')

    flow_cids: set[str] = set()
    for F in flows:
        if isinstance(F, dict) and isinstance(F.get('connectionIds'), list):
            for cid in F['connectionIds']:
                flow_cids.add(r.id_remap.get(cid, cid))
    for C in connections:
        if isinstance(C, dict):
            cid = r.id_remap.get(C.get('id', ''), C.get('id', ''))
            if cid and cid not in flow_cids:
                r.add('info', 'semantic', f'connection "{C.get("id")}" is not in any flow')

    return r


# ── Fixer ──────────────────────────────────────────────────────────────────────

def fix(data: dict, basename: str = 'diagram') -> dict:
    d = copy.deepcopy(data)
    remap: dict[str, str] = {}

    # Top-level defaults
    if not isinstance(d.get('title'), str) or not d.get('title'):
        d['title'] = re.sub(r'[-_]+', ' ', basename).title()
    if not isinstance(d.get('layerManualSizes'), dict) or isinstance(d.get('layerManualSizes'), list):
        d['layerManualSizes'] = {}
    if d.get('lineCurve') not in VALID_CURVES:
        d['lineCurve'] = 'bezier'
    for req in ('layers', 'nodes', 'connections', 'flows'):
        if not isinstance(d.get(req), list):
            d[req] = []

    # Fix layers
    seen_lids: set[str] = set()
    for i, L in enumerate(d['layers']):
        if not isinstance(L, dict): continue
        lid = L.get('id', '')
        if not isinstance(lid, str) or not RE_LAYER_ID.match(lid):
            new = 'ly-' + _kebab(lid) if lid else f'ly-layer-{i}'
            remap[lid] = new; L['id'] = new; lid = new
        if lid in seen_lids:
            new = lid + f'-{i}'; remap[lid + f'_dup{i}'] = new; L['id'] = new; lid = new
        seen_lids.add(lid)
        if not L.get('title') or not isinstance(L.get('title'), str): L['title'] = 'UNTITLED LAYER'
        for cf, dflt in (('bg', SLATE_BG), ('border', SLATE_BORDER)):
            cv = L.get(cf)
            if not isinstance(cv, str) or (not RE_HEX6.match(cv) and not RE_HEX3.match(cv)):
                L[cf] = dflt
            elif RE_HEX3.match(cv):
                L[cf] = _expand_hex3(cv)
        if 'textColor' in L and RE_HEX3.match(str(L['textColor'])):
            L['textColor'] = _expand_hex3(L['textColor'])

    valid_lids = {L['id'] for L in d['layers'] if isinstance(L, dict) and 'id' in L}

    # Fix nodes
    seen_nids: set[str] = set()
    for i, N in enumerate(d['nodes']):
        if not isinstance(N, dict): continue
        nid = N.get('id', '')
        if not isinstance(nid, str) or not RE_NODE_ID.match(nid):
            new = 'el-' + _kebab(nid) if nid else f'el-node-{i}'
            remap[nid] = new; N['id'] = new; nid = new
        if nid in seen_nids:
            new = nid + f'-{i}'; remap[nid + f'_dup{i}'] = new; N['id'] = new; nid = new
        seen_nids.add(nid)
        if not N.get('label') or not isinstance(N.get('label'), str): N['label'] = 'Untitled'
        if not N.get('icon') or not isinstance(N.get('icon'), str): N['icon'] = 'Database'
        if not _finite(N.get('x')): N['x'] = 750
        if not _finite(N.get('y')): N['y'] = 100
        if not _finite(N.get('w')): N['w'] = 210
        if N.get('shape') != 'condition':
            nl = N.get('layer')
            eff = remap.get(nl, nl)
            if eff not in valid_lids: N.pop('layer', None)

    valid_nids = {N['id'] for N in d['nodes'] if isinstance(N, dict) and 'id' in N}

    # Fix connections — drop orphans
    seen_cids: set[str] = set()
    keep_conns = []
    for i, C in enumerate(d['connections']):
        if not isinstance(C, dict): continue
        cid = C.get('id', '')
        if not isinstance(cid, str) or not RE_CONN_ID.match(cid):
            new = 'dl-' + _kebab(cid) if cid else f'dl-conn-{i}'
            remap[cid] = new; C['id'] = new; cid = new
        if cid in seen_cids:
            new = cid + f'-{i}'; remap[cid + f'_dup{i}'] = new; C['id'] = new; cid = new
        seen_cids.add(cid)
        C['from'] = remap.get(C.get('from', ''), C.get('from', ''))
        C['to']   = remap.get(C.get('to',   ''), C.get('to',   ''))
        if C['from'] not in valid_nids or C['to'] not in valid_nids: continue
        for af, dflt in (('fromAnchor', 'bottom-1'), ('toAnchor', 'top-1')):
            av = C.get(af)
            if not isinstance(av, str) or not RE_ANCHOR.match(av): C[af] = dflt
        cc = C.get('color')
        if not _valid_color(cc): C['color'] = SLATE_COLOR
        elif RE_HEX3.match(str(cc)): C['color'] = _expand_hex3(cc)
        lp = C.get('labelPosition')
        if lp is not None and isinstance(lp, (int, float)): C['labelPosition'] = max(0.0, min(1.0, lp))
        keep_conns.append(C)
    d['connections'] = keep_conns
    valid_cids = {C['id'] for C in d['connections']}

    # Fix flows — drop orphan cids, split non-contiguous
    seen_fids: set[str] = set()
    fixed_flows = []
    for i, F in enumerate(d['flows']):
        if not isinstance(F, dict): continue
        fid = F.get('id', '')
        if not isinstance(fid, str) or not RE_FLOW_ID.match(fid):
            new = 'flow-' + _kebab(fid) if fid else f'flow-{i}'
            F['id'] = new; fid = new
        if fid in seen_fids: F['id'] = fid + f'-{i}'; fid = F['id']
        seen_fids.add(fid)
        if not F.get('name') or not isinstance(F.get('name'), str): F['name'] = 'Flow'
        cids = F.get('connectionIds', [])
        if not isinstance(cids, list): continue
        clean = [remap.get(c, c) for c in cids if remap.get(c, c) in valid_cids]
        F['connectionIds'] = clean
        if not clean: continue

        # Contiguity split
        if len(clean) > 1:
            conn_ep: dict[str, tuple] = {}
            for C in d['connections']:
                if C.get('id') in clean:
                    conn_ep[C['id']] = (C.get('from'), C.get('to'))
            parent = {c: c for c in clean}

            def _find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]; x = parent[x]
                return x

            cl = list(conn_ep)
            for j in range(len(cl)):
                for k in range(j + 1, len(cl)):
                    if set(conn_ep.get(cl[j], ())) & set(conn_ep.get(cl[k], ())):
                        parent[_find(cl[j])] = _find(cl[k])
            comps: dict[str, list] = {}
            for c in clean:
                comps.setdefault(_find(c), []).append(c)
            if len(comps) > 1:
                for n, comp_cids in enumerate(comps.values(), 1):
                    fixed_flows.append({'id': f'{fid}-{n}', 'name': f'{F["name"]} ({n})', 'connectionIds': comp_cids})
                continue

        fixed_flows.append(F)
    d['flows'] = fixed_flows

    # Canonical key order
    ordered = {k: d[k] for k in ('title', 'layers', 'nodes', 'connections', 'layerManualSizes', 'lineCurve', 'flows') if k in d}
    if 'documents' in d: ordered['documents'] = d['documents']
    for k, v in d.items():
        if k not in ordered: ordered[k] = v
    return ordered


# ── Report formatter ───────────────────────────────────────────────────────────

def report(path: str, r: Result) -> str:
    lines = [f'validate {path}', '']
    sections = [
        ('schema',      'Schema'),
        ('layers',      'Layers'),
        ('nodes',       'Nodes'),
        ('connections', 'Connections'),
        ('flows',       'Flows'),
        ('semantic',    'Semantic'),
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
    fixable = sum(1 for d in r.diags if d.fixable and d.level in ('error', 'warning'))
    summary = f'Summary: {ne} error(s), {nw} warning(s), {ni} info.'
    if fixable:
        summary += f' --fix would resolve {fixable} issue(s).'
    lines.append(summary)
    return '\n'.join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────

def _run_doc(p: str, fix: bool, json_out: bool, vault_root: str | None) -> bool:
    """Validate a .md document. Returns True if errors found."""
    from kb_validate_doc import validate_document, format_doc_report
    r = validate_document(p, vault_root)
    if json_out:
        print(json.dumps({
            'path': p,
            'errors': len(r.errors), 'warnings': len(r.warnings), 'infos': len(r.infos),
            'diagnostics': [{'level': d.level, 'section': d.section, 'msg': d.msg, 'fixable': d.fixable}
                             for d in r.diags],
        }, indent=2))
    else:
        print(format_doc_report(p, r))
    if fix:
        fixable = [d for d in r.diags if d.fixable]
        if fixable:
            print(f'Applying fixes via kb_transform.py --add-conventions ...')
            subprocess.run([sys.executable, str(SCRIPTS_DIR / 'kb_transform.py'), p, '--add-conventions'])
    return bool(r.errors)


def _run_json(p: str, do_fix: bool, json_out: bool) -> bool:
    """Validate a .json diagram. Returns True if errors found."""
    try:
        text = Path(p).read_text(encoding='utf-8')
    except OSError as e:
        print(f'✗ {p}: {e}', file=sys.stderr)
        return True

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f'✗ {p}: FATAL — invalid JSON at line {e.lineno}: {e.msg}')
        return True

    r = validate(data, p)

    if json_out:
        print(json.dumps({
            'path': p,
            'errors': len(r.errors), 'warnings': len(r.warnings), 'infos': len(r.infos),
            'diagnostics': [{'level': d.level, 'section': d.section, 'msg': d.msg, 'fixable': d.fixable}
                             for d in r.diags],
        }, indent=2))
    else:
        print(report(p, r))

    if do_fix:
        fixed = fix(data, Path(p).stem)
        r2 = validate(fixed, p)
        bak = backup_file(p, 'invalid-backup')
        Path(p).write_text(json.dumps(fixed, indent=2) + '\n', encoding='utf-8')
        if r2.errors:
            print(f'Fixed {p}. Backup kept at {bak} ({len(r2.errors)} error(s) remain — manual inspection recommended).')
        else:
            Path(bak).unlink(missing_ok=True)
            print(f'Fixed {p}.')

    return bool(r.errors)


def main():
    ap = argparse.ArgumentParser(
        description='Validate (and optionally fix) knowledge-base files (.md and .json).',
    )
    ap.add_argument('path', help='File path or glob')
    ap.add_argument('--fix',        action='store_true', help='Write corrected file back to disk')
    ap.add_argument('--vault-root', default=None,        help='Vault root for resolving wiki-links (auto-detected if omitted)')
    ap.add_argument('--json',       dest='json_out', action='store_true', help='Machine-readable JSON output')
    args = ap.parse_args()

    vault_root = args.vault_root or detect_vault()

    paths = glob.glob(args.path, recursive=True)
    if not paths:
        paths = [args.path] if os.path.exists(args.path) else []
    if not paths:
        print(f'No files found: {args.path}', file=sys.stderr); sys.exit(1)

    any_errors = False

    for p in paths:
        ext = Path(p).suffix.lower()
        if ext == '.md':
            if _run_doc(p, args.fix, args.json_out, vault_root):
                any_errors = True
        elif ext == '.json':
            if _run_json(p, args.fix, args.json_out):
                any_errors = True
        else:
            print(f'  ℹ {p}: skipped (unsupported extension "{ext}")')

    sys.exit(1 if any_errors else 0)


if __name__ == '__main__':
    main()
