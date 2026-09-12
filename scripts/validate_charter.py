#!/usr/bin/env python3
"""Semantic validation for standing charters against the company contract and Claude Code manifest.

usage: validate_charter.py <company-contract.json> <charter.json> [<charter.json> ...]

A charter may start work; it may never widen authority. This proves:
  - the owner role is chief-of-staff or an enabled department index;
  - every department the charter names is enabled in the company contract;
  - the dominant outcome routes to one of the charter's departments (or chief-of-staff for cross-functional);
  - every standing approval it relies on names a tool some exported agent could actually call and that is an
    external/approval-required tool per a published connector — the charter cannot mint approvals for arbitrary tools;
  - a charter with max_external_actions > 0 must name at least one standing approval, otherwise it is draft-only;
  - it has an approver and an expiry that has not passed.
"""
import json, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from router import OUTCOME_TO_DEPARTMENT  # noqa: E402


def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))


CRON_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]

def cron_ok(expr):
    """Five fields; each * or a comma list of N, N-M, */S, N-M/S within range. Names are not accepted."""
    parts = expr.split()
    if len(parts) != 5: return False
    for field, (lo, hi) in zip(parts, CRON_RANGES):
        for item in field.split(','):
            mo = re.fullmatch(r'(\*|(\d+)(?:-(\d+))?)(?:/(\d+))?', item)
            if not mo: return False
            if mo.group(2) is not None:
                a = int(mo.group(2)); b = int(mo.group(3)) if mo.group(3) else a
                if not (lo <= a <= hi and lo <= b <= hi and a <= b): return False
            if mo.group(4) is not None and int(mo.group(4)) < 1: return False
    return True

def connector_external_tools():
    """Standing-capable tools only: external, with a clearance key and pre-approved classes, so the guard's
    standing-approval path can actually admit them. Approval-required tools always need a per-call token."""
    m = load(ROOT / 'claude' / 'agent-manifest.json')
    tools = {}
    for rel in m.get('connectors', []):
        c = load(ROOT / rel)
        for t in c['tools']:
            if t.get('external_action') and t.get('clearance_key') and t.get('preapproved_content_classes'):
                tools[f"mcp__{c['mcp']['server_name']}__{t['tool']}"] = t
    return tools, m


def validate(company, charter, today=None):
    errors = []
    today = today or time.strftime('%Y-%m-%d', time.gmtime())
    depts = set(company.get('departments', []))
    systems = {s.get('id'): s.get('write_authority', 'none') for s in company.get('systems', []) if isinstance(s, dict)}
    owner = charter['owner_role']
    if owner != 'chief-of-staff' and owner not in depts:
        errors.append(f"owner_role {owner} is not chief-of-staff or an enabled department")
    for d in charter['departments']:
        if d not in depts: errors.append(f'department {d} is not enabled in the company contract')
    routed = OUTCOME_TO_DEPARTMENT.get(charter['dominant_outcome'])
    if routed not in set(charter['departments']) | {'chief-of-staff'}:
        errors.append(f"dominant_outcome routes to {routed}, which the charter does not include")
    if owner != 'chief-of-staff' and owner not in charter['departments']:
        errors.append(f'a department charter may only commission its own department; {owner} is not in {charter["departments"]}')
    if charter['expires'] <= today: errors.append(f"charter expired on {charter['expires']}")
    if not charter.get('approved_by'): errors.append('approved_by required')
    ext_tools, manifest = connector_external_tools()
    agents_by_dept = {}
    for a in manifest['agents']: agents_by_dept.setdefault(a['department'], []).append(a)
    for sa in charter['bounds'].get('standing_approvals', []):
        if sa not in ext_tools:
            errors.append(f'standing approval {sa} is not a standing-capable external tool (clearance_key + preapproved classes) of any published connector'); continue
        server = sa.split('__')[1]
        if server not in systems:
            errors.append(f'standing approval {sa} names server {server}, which the company contract does not declare under systems'); continue
        if systems[server] != 'bounded':
            errors.append(f'standing approval {sa}: system {server} is declared write_authority={systems[server]}; standing approvals need bounded'); continue
        holders = [a for d in charter['departments'] for a in agents_by_dept.get(d, [])
                   if server in (a.get('mcp_servers') or []) and not any(re.search(p, sa) for p in a.get('deny_tool_patterns', []))]
        if not holders: errors.append(f'no agent in {charter["departments"]} can call {sa}; the standing approval is dead weight')
    if charter['bounds']['max_external_actions'] > 0 and not charter['bounds'].get('standing_approvals'):
        errors.append('max_external_actions > 0 requires at least one standing_approval; otherwise set 0 for a draft-only charter')
    if 'cron' in charter['trigger']:
        if not charter['trigger'].get('timezone'): errors.append('cron triggers must declare a timezone')
        if not cron_ok(charter['trigger']['cron']): errors.append(f"cron expression out of range or unsupported: {charter['trigger']['cron']}")
    return errors


def main():
    if len(sys.argv) < 3: print(__doc__, file=sys.stderr); return 2
    company = load(sys.argv[1]); bad = 0
    for p in sys.argv[2:]:
        errs = validate(company, load(p))
        for e in errs: print(f'ERROR {p}: {e}')
        bad += bool(errs)
    if bad: return 1
    print(f'PASS: {len(sys.argv) - 2} charter(s) bounded by contract, connectors and manifest'); return 0


if __name__ == '__main__': raise SystemExit(main())
