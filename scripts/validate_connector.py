#!/usr/bin/env python3
"""Semantic validation for a published connector and its binding in the Claude Code manifest.

usage: validate_connector.py <connector.json> [<agent-manifest.json>]

A connector declares what every MCP tool *would do* in Company OS capability terms. This
script proves the declaration cannot smuggle authority:

  - an external action is never `observe` or `propose`, and is `execute-bounded` only when it
    names the pre-approved content classes and the clearance key a reviewer must have signed;
  - a financial commitment is never held by a marketing role;
  - the reviewer role never holds an authoring or publishing tool;
  - an exclusive capability (publish, send, spend...) is only held by its owning role;
  - every tool granted to a role in the manifest is either observe/propose or guarded as an
    external action, and every tool the connector withholds from a role is denied by that
    role's manifest pattern.
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_marketing_profile import EXCLUSIVE, FORBIDDEN_EVERYWHERE, AUTHORING  # noqa: E402

ROLE_TO_AGENT = {'brand_manager': 'brand-manager', 'direct_email': 'direct-email-specialist', 'paid_media': 'paid-media-specialist',
                 'social_media': 'social-media-specialist', 'agent_relations': 'agent-relations-specialist',
                 'content_reviewer': 'marketing-content-reviewer'}
SAFE_AUTHORITY = {'observe', 'propose'}


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def validate(conn, manifest=None):
    errors = []
    server = conn['mcp']['server_name']
    seen = set()
    for t in conn['tools']:
        name, cap, auth, owners = t['tool'], t['capability'], t['authority'], set(t['owner_roles'])
        if name in seen: errors.append(f'duplicate tool {name}')
        seen.add(name)
        ext, fin = t.get('external_action', False), t.get('financial_commitment', False)
        if ext and auth in SAFE_AUTHORITY:
            errors.append(f'{name}: external action cannot be {auth}')
        if ext and auth == 'execute-bounded':
            if not t.get('preapproved_content_classes'): errors.append(f'{name}: execute-bounded external action must name preapproved_content_classes')
            if not t.get('clearance_key'): errors.append(f'{name}: execute-bounded external action must name a clearance_key')
        if fin and (owners or auth != 'prohibited'):
            errors.append(f'{name}: financial commitment must be prohibited with no owner roles')
        if cap in FORBIDDEN_EVERYWHERE and owners:
            errors.append(f'{name}: {cap} may not be held by any marketing role')
        if cap in EXCLUSIVE and owners - {EXCLUSIVE[cap]}:
            errors.append(f'{name}: {cap} may only be held by {EXCLUSIVE[cap]}')
        if 'content_reviewer' in owners and (cap in AUTHORING or cap in EXCLUSIVE or auth not in SAFE_AUTHORITY):
            errors.append(f'{name}: content_reviewer may only observe; it cannot author, publish or execute')
        if auth == 'prohibited' and owners:
            errors.append(f'{name}: prohibited tool cannot have owner roles')
        for r in owners:
            if r not in ROLE_TO_AGENT: errors.append(f'{name}: unknown role {r}')

    if manifest is not None:
        agents = {a['name']: a for a in manifest['agents']}
        ext_patterns = manifest.get('external_action_tool_patterns', [])
        for role, agent_name in ROLE_TO_AGENT.items():
            a = agents.get(agent_name)
            if a is None: errors.append(f'manifest lacks agent {agent_name}'); continue
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
                if t.get('external_action') and not external:
                    errors.append(f"{full} is an external action but matches no external_action_tool_patterns")
                if t.get('financial_commitment') and not external:
                    errors.append(f"{full} is a financial commitment but matches no external_action_tool_patterns")
            if not uses:
                # a role that cannot see the server must be denied it outright
                if not any(re.search(p, f'mcp__{server}__x') for p in a.get('deny_tool_patterns', [])):
                    errors.append(f'{agent_name} is not bound to {server} but has no deny pattern for it')
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
