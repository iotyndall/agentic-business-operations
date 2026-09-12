#!/usr/bin/env python3
"""Semantic validation for a published connector and its binding in the Claude Code manifest.

usage: validate_connector.py <connector.json> [<agent-manifest.json>]

A connector declares what every MCP tool *would do* in Company OS capability terms. This
script proves the declaration cannot smuggle authority:

  - externality is derived from the capability, not trusted from the optional flag: any tool
    mapped to a publish/send/spend/negotiate/commitment capability must declare
    external_action (or financial_commitment) and a guarded authority;
  - an external action is never observe/propose, and is execute-bounded only when it names the
    pre-approved content classes and the clearance key a reviewer must have signed;
  - department-specific rules: for marketing connectors, a financial commitment is never held
    by a marketing role, the reviewer never authors/executes, and exclusive capabilities are
    held only by their owner; for other departments the role vocabulary is that department's;
  - every tool granted to a role in the manifest is either safe or guarded, and every tool the
    connector withholds from a role is denied by that role's manifest pattern.
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_marketing_profile import EXCLUSIVE, FORBIDDEN_EVERYWHERE, AUTHORING  # noqa: E402

ROLE_TO_AGENT = {
    'marketing': {'brand_manager': 'brand-manager', 'direct_email': 'direct-email-specialist', 'paid_media': 'paid-media-specialist',
                  'social_media': 'social-media-specialist', 'agent_relations': 'agent-relations-specialist',
                  'content_reviewer': 'marketing-content-reviewer'},
    'strategy': {'strategy_lead': 'strategy-lead', 'market_intelligence': 'market-intelligence-analyst',
                 'business_performance': 'business-performance-analyst', 'long_range': 'long-range-planner',
                 'corporate_development': 'corporate-development-analyst'},
    'service': {'frontline': 'frontline-service-worker', 'supervisor': 'service-supervisor',
                'script_author': 'script-knowledge-author', 'quality_reviewer': 'service-quality-reviewer'},
    # Departments without specialist decomposition yet: the department index role is the only vocabulary.
    'sales': {'sales': 'sales'}, 'operations': {'operations': 'operations'}, 'finance': {'finance': 'finance'},
    'legal': {'legal': 'legal'}, 'product': {'product': 'product'},
}
SAFE_AUTHORITY = {'observe', 'propose'}
# Capabilities that are external by definition, whatever the connector says about them.
EXTERNAL_CAPS = set(EXCLUSIVE) - {'content.clear_bounded'}
FINANCIAL_CAPS = {'commitment.sign', 'payment.execute', 'payout.execute', 'spend.execute_bounded', 'budget.create'}


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def validate(conn, manifest=None):
    errors = []
    server = conn['mcp']['server_name']
    dept = conn['department']
    roles = ROLE_TO_AGENT.get(dept, {})
    seen = set()
    for t in conn['tools']:
        name, cap, auth, owners = t['tool'], t['capability'], t['authority'], set(t['owner_roles'])
        if name in seen: errors.append(f'duplicate tool {name}')
        seen.add(name)
        ext, fin = t.get('external_action', False), t.get('financial_commitment', False)
        if cap in EXTERNAL_CAPS and not ext and auth != 'prohibited':
            errors.append(f'{name}: capability {cap} is external by definition; declare external_action or prohibit the tool')
        if cap in FINANCIAL_CAPS and not fin and auth != 'prohibited':
            errors.append(f'{name}: capability {cap} is a financial commitment by definition; declare financial_commitment or prohibit the tool')
        if (ext or fin) and auth in SAFE_AUTHORITY:
            errors.append(f'{name}: external/financial action cannot be {auth}')
        if ext and auth == 'execute-bounded':
            if not t.get('preapproved_content_classes'): errors.append(f'{name}: execute-bounded external action must name preapproved_content_classes')
            if not t.get('clearance_key'): errors.append(f'{name}: execute-bounded external action must name a clearance_key')
        if t.get('invalidates_clearance') and not t.get('clearance_key'):
            errors.append(f'{name}: invalidates_clearance requires a clearance_key')
        if auth == 'prohibited' and owners:
            errors.append(f'{name}: prohibited tool cannot have owner roles')
        for r in owners:
            if r not in roles: errors.append(f'{name}: role {r} is not a {dept} role')
        if dept == 'marketing':
            if fin and owners:
                errors.append(f'{name}: financial commitment may not be held by any marketing role')
            if cap in FORBIDDEN_EVERYWHERE and owners:
                errors.append(f'{name}: {cap} may not be held by any marketing role')
            if cap in EXCLUSIVE and owners - {EXCLUSIVE[cap]}:
                errors.append(f'{name}: {cap} may only be held by {EXCLUSIVE[cap]}')
            if 'content_reviewer' in owners and (cap in AUTHORING or cap in EXCLUSIVE or auth not in SAFE_AUTHORITY):
                errors.append(f'{name}: content_reviewer may only observe; it cannot author, publish or execute')

    if manifest is not None:
        agents = {a['name']: a for a in manifest['agents']}
        ext_patterns = manifest.get('external_action_tool_patterns', [])
        for role, agent_name in roles.items():
            a = agents.get(agent_name)
            if a is None: continue  # no subagent exists for this role yet; nothing to bind
            uses = conn['id'] in (a.get('mcp_servers') or []) or server in (a.get('mcp_servers') or [])
            for t in conn['tools']:
                full = f"mcp__{server}__{t['tool']}"
                granted = role in t['owner_roles']
                denied = any(re.search(p, full) for p in a.get('deny_tool_patterns', []))
                external = any(re.search(p, full) for p in ext_patterns)
                if uses and granted and denied:
                    errors.append(f"{agent_name}: manifest denies {full} but connector grants it")
                if uses and not granted and not denied:
                    errors.append(f"{agent_name}: connector withholds {full} but manifest does not deny it")
                if (t.get('external_action') or t.get('financial_commitment')) and not external:
                    errors.append(f"{full} is an external/financial action but matches no external_action_tool_patterns")
            if not uses and not any(re.search(p, f'mcp__{server}__x') for p in a.get('deny_tool_patterns', [])):
                errors.append(f'{agent_name} is not bound to {server} but has no deny pattern for it')
        # every agent outside this connector's department must be unable to reach the server at all
        for a in manifest['agents']:
            if a['name'] in roles.values(): continue
            if server in (a.get('mcp_servers') or []) or not any(re.search(p, f'mcp__{server}__x') for p in a.get('deny_tool_patterns', [])):
                errors.append(f"{a['name']} ({a['department']}) can reach {server}, a {dept} connector")
    return errors


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr); return 2
    conn = load(sys.argv[1])
    manifest = load(sys.argv[2]) if len(sys.argv) > 2 else None
    errors = validate(conn, manifest)
    if errors:
        for e in errors: print(f'ERROR: {e}')
        return 1
    granted = sum(1 for t in conn['tools'] if t['owner_roles'])
    ext = sum(1 for t in conn['tools'] if t.get('external_action'))
    print(f"PASS: connector {conn['id']} — {len(conn['tools'])} tools, {granted} role-held, {ext} external action(s) guarded"
          + (', manifest consistent' if manifest else ''))
    return 0


if __name__ == '__main__': raise SystemExit(main())
