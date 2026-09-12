#!/usr/bin/env python3
"""Export Company OS roles as Claude Code subagents into a private company repo.

usage: export_claude_code.py <company-contract.json> <out-dir> [--enable name,name,...] [--marketing-profile <profile.json>]

Writes:
  <out>/.claude/agents/<name>.md        subagent = role contract markdown + runtime frontmatter
  <out>/.claude/hooks/company_os_guard.py
  <out>/.claude/settings.json           hooks wiring (merged if present)
  <out>/.agentic/runtime-manifest.json  what the guard enforces at runtime
Only roles for departments enabled in the company contract are exported, further
narrowed by --enable. Everything exported is traceable to the locked framework commit.
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def framework_commit():
    try: return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    except Exception: return 'unknown'

def title_of(md):
    for line in md.splitlines():
        if line.startswith('# '): return line[2:].strip()
    return ''

ROLE_KEY_TO_AGENT = {'brand_manager': 'brand-manager', 'direct_email': 'direct-email-specialist', 'paid_media': 'paid-media-specialist',
                     'social_media': 'social-media-specialist', 'agent_relations': 'agent-relations-specialist',
                     'content_reviewer': 'marketing-content-reviewer'}

def load_connectors(manifest):
    return [json.loads((ROOT / rel).read_text(encoding='utf-8')) for rel in manifest.get('connectors', [])]

def connector_tools(connectors):
    """Per-tool guard metadata for every tool a published connector declares. The guard fails closed on
    any tool under a connector server that is not in this map."""
    out = {}
    for c in connectors:
        server = c['mcp']['server_name']
        for t in c['tools']:
            out[f"mcp__{server}__{t['tool']}"] = {
                'connector': c['id'], 'capability': t['capability'], 'authority': t['authority'],
                'owner_agents': sorted(ROLE_KEY_TO_AGENT.get(r, r) for r in t.get('owner_roles', [])),
                'clearance_key': t.get('clearance_key'), 'preapproved_content_classes': t.get('preapproved_content_classes', []),
                'external_action': bool(t.get('external_action') or t.get('financial_commitment')),
                'invalidates_clearance': bool(t.get('invalidates_clearance'))}
    return out

def disabled_marketing_agents(argv):
    """Roles a private marketing profile marks enabled:false are not exported: the profile's authority decision wins."""
    if '--marketing-profile' not in argv: return set()
    prof = json.loads(Path(argv[argv.index('--marketing-profile') + 1]).read_text(encoding='utf-8'))
    return {ROLE_KEY_TO_AGENT[k] for k, r in (prof.get('roles') or {}).items() if k in ROLE_KEY_TO_AGENT and not r.get('enabled')}

def main(argv):
    if len(argv) < 3: print(__doc__, file=sys.stderr); return 2
    contract = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    out = Path(argv[2]); enable = None
    if '--enable' in argv: enable = set(argv[argv.index('--enable') + 1].split(','))
    manifest = json.loads((ROOT / 'claude' / 'agent-manifest.json').read_text(encoding='utf-8'))
    departments = set(contract.get('departments', []))
    declared_systems = {s.get('id') for s in contract.get('systems', []) if isinstance(s, dict)}
    connectors = load_connectors(manifest)
    connector_servers = {c['mcp']['server_name'] for c in connectors}
    disabled = disabled_marketing_agents(argv)
    commit = framework_commit()
    agents_dir = out / '.claude' / 'agents'; agents_dir.mkdir(parents=True, exist_ok=True)
    hooks_dir = out / '.claude' / 'hooks'; hooks_dir.mkdir(parents=True, exist_ok=True)
    (out / '.agentic' / 'ledger' / 'decisions').mkdir(parents=True, exist_ok=True)
    exported = []
    for a in manifest['agents']:
        if a['department'] not in departments and a['department'] != 'review': continue
        if enable is not None and a['name'] not in enable: continue
        if a['name'] in disabled: continue
        a = dict(a)
        # A server is exposed only if the private contract declares it as a system. Undeclared servers are stripped from
        # the subagent's mcpServers AND explicitly denied, so a user-level Claude config cannot leak them in.
        bound, unbound = [], []
        for srv in a.get('mcp_servers') or []:
            (bound if srv in declared_systems else unbound).append(srv)
        a['mcp_servers'] = bound
        a['deny_tool_patterns'] = list(a.get('deny_tool_patterns', [])) + [f'^mcp__{srv}__.*' for srv in unbound]
        body = (ROOT / a['role']).read_text(encoding='utf-8')
        fm = ['---', f"name: {a['name']}", f"description: {a['description']}",
              f"tools: {', '.join(a['tools'])}", f"model: {a.get('model', 'inherit')}"]
        if a.get('mcp_servers'): fm.append('mcpServers: [' + ', '.join(a['mcp_servers']) + ']')
        fm.append('---')
        header = (f"<!-- Generated from {a['role']} at agentic-business-operations@{commit}. Do not edit; re-export. -->\n\n"
                  "You are operating inside Company OS. Your authority is exactly what this contract grants and nothing more. "
                  "Write every artifact you produce under .agentic/ledger/ as JSON or markdown with a source reference for every material claim. "
                  "If you need something outside your allowed capabilities, write a handoff request and stop.\n\n")
        (agents_dir / f"{a['name']}.md").write_text('\n'.join(fm) + '\n' + header + body, encoding='utf-8')
        exported.append({k: a[k] for k in ('name', 'department', 'deny_tool_patterns', 'clearance_writer', 'review_independence') if k in a} | {'role': a['role'], 'title': title_of(body), 'confidential_scope': a.get('confidential_scope')})
    shutil.copy(ROOT / 'claude' / 'hooks' / 'company_os_guard.py', hooks_dir / 'company_os_guard.py')
    (hooks_dir / 'company_os_guard.py').chmod(0o755)
    runtime = {'version': 1, 'framework_commit': commit, 'company_id': contract.get('company', {}).get('id'),
               'external_action_default': contract.get('authority', {}).get('external_action_default', 'deny'),
               'external_action_tool_patterns': manifest['external_action_tool_patterns'],
               'ledger': manifest['ledger'], 'agents': exported,
               'clearances': manifest.get('clearances', {}), 'standing_approvals': manifest.get('standing_approvals', {}),
               'connector_servers': sorted(connector_servers & declared_systems),
               'connector_tools': connector_tools([c for c in connectors if c['mcp']['server_name'] in declared_systems])}
    (out / '.agentic' / 'runtime-manifest.json').write_text(json.dumps(runtime, indent=2) + '\n', encoding='utf-8')
    settings_path = out / '.claude' / 'settings.json'
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    guard = 'python3 .claude/hooks/company_os_guard.py'
    settings.setdefault('hooks', {})
    settings['hooks']['PreToolUse'] = [{'matcher': '*', 'hooks': [{'type': 'command', 'command': f'{guard} pre', 'timeout': 10}]}]
    settings['hooks']['PostToolUse'] = [{'matcher': 'Write|Edit|mcp__.*', 'hooks': [{'type': 'command', 'command': f'{guard} post', 'timeout': 10}]}]
    settings_path.write_text(json.dumps(settings, indent=2) + '\n', encoding='utf-8')
    print(f"exported {len(exported)} subagents to {agents_dir} (framework {commit[:12]})")
    for e in exported: print(f"  - {e['name']}")
    return 0

if __name__ == '__main__': raise SystemExit(main(sys.argv))
