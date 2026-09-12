#!/usr/bin/env python3
"""Company OS runtime guard for Claude Code hooks.

  PreToolUse  -> `company_os_guard.py pre`   deny calls that exceed the acting role's authority
  PostToolUse -> `company_os_guard.py post`  append a ledger event

Reads the hook JSON from stdin. Reads .agentic/runtime-manifest.json (written by the
framework exporter) from the working directory. Fails closed: if the manifest is missing
or unreadable, every tool call outside plain Read/Glob/Grep is denied.
"""
import json, re, sys, time
from pathlib import Path

SAFE_TOOLS = {'Read', 'Glob', 'Grep', 'TodoWrite', 'TodoRead', 'Task', 'Skill'}

def deny(reason):
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                             'permissionDecisionReason': f'Company OS: {reason}'}}))
    return 0

def load_manifest(cwd):
    p = Path(cwd) / '.agentic' / 'runtime-manifest.json'
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return None

def path_of(tool_input):
    for k in ('file_path', 'path', 'notebook_path'):
        if k in tool_input: return str(tool_input[k])
    return ''

def check_decision_write(tool_input, ledger):
    """Agents may write decision *drafts*; only a human writes a decided record."""
    path = path_of(tool_input)
    if not path or ledger['decisions'] not in path.replace('\\', '/'): return None
    if not path.endswith(ledger['decision_draft_suffix']):
        return 'agents may only write decision drafts (*.draft.json); a human records the decision'
    content = tool_input.get('content') or tool_input.get('new_string') or ''
    try: doc = json.loads(content) if content.strip().startswith('{') else None
    except Exception: doc = None
    if doc is not None:
        opts = doc.get('options') or []
        if len(opts) < 2: return 'decision draft must present at least two options'
        if not doc.get('review_ref'): return 'decision draft must reference an adversarial review'
        for a in doc.get('assumptions') or []:
            if not all(a.get(k) for k in ('owner', 'basis', 'confidence')):
                return 'every assumption needs owner, basis and confidence'
        if doc.get('decided_by') or doc.get('decision'):
            return 'agents may not populate decided_by/decision; that is the human principal'
    return None

def pre(evt):
    tool = evt.get('tool_name', ''); tool_input = evt.get('tool_input') or {}
    agent = evt.get('agent_type'); cwd = evt.get('cwd', '.')
    m = load_manifest(cwd)
    if m is None:
        return 0 if tool in SAFE_TOOLS else deny('runtime manifest missing; failing closed')
    ledger = m['ledger']
    # 1. External actions are denied company-wide unless a human approval token exists for this exact call.
    for pat in m.get('external_action_tool_patterns', []):
        if re.search(pat, tool):
            import hashlib
            digest = hashlib.sha256(json.dumps({'tool': tool, 'input': tool_input}, sort_keys=True).encode()).hexdigest()[:16]
            token = Path(cwd) / '.agentic' / 'approvals' / f'{digest}.json'
            if token.exists():
                try:
                    t = json.loads(token.read_text())
                    if t.get('status') == 'approved' and t.get('approved_by'): break
                except Exception: pass
            return deny(f'external action {tool} requires a human approval token at .agentic/approvals/{digest}.json')
    # 2. Role-scoped denies from the manifest (subagent frontmatter allowlists cover built-ins; this covers MCP/web patterns).
    role = next((a for a in m['agents'] if a['name'] == agent), None) if agent else None
    if role:
        for pat in role.get('deny_tool_patterns', []):
            if re.search(pat, tool): return deny(f"role {agent} may not use {tool}")
    # 3. Confidential scopes: only the owning role reads or writes inside them.
    p = path_of(tool_input).replace('\\', '/')
    if p:
        for a in m['agents']:
            scope = a.get('confidential_scope')
            if scope and scope.strip('/') in p and agent != a['name']:
                return deny(f"{p} is inside {a['name']} confidential scope")
    # 4. Decision records.
    if tool in ('Write', 'Edit', 'MultiEdit'):
        reason = check_decision_write(tool_input, ledger)
        if reason: return deny(reason)
    return 0

def post(evt):
    cwd = evt.get('cwd', '.'); m = load_manifest(cwd)
    if m is None: return 0
    ev = {'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'session': evt.get('session_id'),
          'agent': evt.get('agent_type') or 'main', 'tool': evt.get('tool_name'),
          'path': path_of(evt.get('tool_input') or {}) or None, 'framework': m.get('framework_commit')}
    f = Path(cwd) / m['ledger']['events']; f.parent.mkdir(parents=True, exist_ok=True)
    with f.open('a', encoding='utf-8') as fh: fh.write(json.dumps(ev) + '\n')
    return 0

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'pre'
    try: evt = json.load(sys.stdin)
    except Exception: evt = {}
    return pre(evt) if mode == 'pre' else post(evt)

if __name__ == '__main__': raise SystemExit(main())
