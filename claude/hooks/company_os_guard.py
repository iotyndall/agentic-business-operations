#!/usr/bin/env python3
"""Company OS runtime guard for Claude Code hooks.

  PreToolUse  -> `company_os_guard.py pre`   deny calls that exceed the acting role's authority
  PostToolUse -> `company_os_guard.py post`  append a ledger event

Reads the hook JSON from stdin. Reads .agentic/runtime-manifest.json (written by the
framework exporter) from the working directory. Fails closed: if the manifest is missing
or unreadable, every tool call outside plain Read/Glob/Grep is denied.
"""
import json, re, sys, time
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def locked(path):
    """Inter-process lock around counter read-modify-write. Concurrent PreToolUse hooks serialize here."""
    lock = Path(str(path) + '.lock'); lock.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock, 'a+')
    try:
        try:
            import fcntl; fcntl.flock(fh, fcntl.LOCK_EX)
        except ImportError:
            import msvcrt; fh.seek(0); msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        yield
    finally:
        fh.close()

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

def _approved(doc):
    return isinstance(doc, dict) and doc.get('status') == 'approved' and bool(doc.get('approved_by'))

def _not_expired(doc):
    exp = doc.get('expires')
    if not exp: return False
    try: return time.strptime(exp[:10], '%Y-%m-%d') > time.gmtime()
    except Exception: return False

def external_action_allowed(m, cwd, tool, tool_input):
    import hashlib
    digest = hashlib.sha256(json.dumps({'tool': tool, 'input': tool_input}, sort_keys=True).encode()).hexdigest()[:16]
    token = Path(cwd) / '.agentic' / 'approvals' / f'{digest}.json'
    try:
        if token.exists() and _approved(json.loads(token.read_text())): return True, ''
    except Exception: pass
    spec = (m.get('connector_tools') or {}).get(tool)
    standing = Path(cwd) / (m.get('standing_approvals', {}).get('root') or '.agentic/approvals/standing') / f'{tool}.json'
    if spec and spec.get('standing_allowed') and spec.get('clearance_key') and standing.exists():
        try: sa = json.loads(standing.read_text())
        except Exception: sa = None
        if _approved(sa) and _not_expired(sa):
            classes = set(sa.get('content_classes') or []) & set(spec.get('preapproved_content_classes') or [])
            key = spec['clearance_key']; art = str(tool_input.get(key, '')).strip()
            if classes and art and re.fullmatch(r'[A-Za-z0-9._-]+', art):
                cl = Path(cwd) / (m.get('clearances', {}).get('root') or '.agentic/ledger/reviews/clearances') / f'{art}.json'
                try: c = json.loads(cl.read_text()) if cl.exists() else None
                except Exception: c = None
                if isinstance(c, dict) and c.get('cleared') is True and c.get('content_class') in classes and c.get('reviewer'):
                    over = charge_daily_cap(standing, sa, tool)
                    if over: return False, over
                    return True, ''
                return False, f'{tool} on {key}={art} needs a reviewer clearance with content_class in {sorted(classes)} at {cl}'
            return False, f'standing approval for {tool} does not cover this content class or the call lacks {key}'
    return False, f'external action {tool} requires a human approval token at .agentic/approvals/{digest}.json'

def charge_daily_cap(standing_path, sa, tool):
    """Enforce max_per_day on a standing approval with a durable per-tool counter beside the approval file."""
    cap = sa.get('max_per_day')
    if cap is None: return None
    if not isinstance(cap, int) or cap < 0: return f'standing approval for {tool} has a malformed max_per_day; denying'
    today = time.strftime('%Y-%m-%d', time.gmtime())
    counter = standing_path.with_suffix('.counter.json')
    with locked(counter):
        try: c = json.loads(counter.read_text()) if counter.exists() else {}
        except Exception: return f'daily counter for {tool} is unreadable; denying'
        used = c.get('count', 0) if c.get('date') == today else 0
        if used >= cap: return f'standing approval for {tool} has reached max_per_day ({cap}) for {today}'
        counter.write_text(json.dumps({'date': today, 'count': used + 1}))
    return None

def charge_run_budget(cwd, tool):
    """When a charter run is active, every allowed external action consumes one unit of its budget. Fails closed on a malformed file."""
    f = Path(cwd) / '.agentic' / 'runs' / 'current.json'
    if not f.exists(): return None
    with locked(f):
        try: run = json.loads(f.read_text())
        except Exception: return 'active charter run file is unreadable; denying external actions'
        cap = run.get('max_external_actions'); used = run.get('external_actions', 0)
        if not isinstance(cap, int): return 'active charter run has no max_external_actions; denying'
        if used >= cap: return f"charter run {run.get('run_id')} has spent its external-action budget ({cap})"
        run['external_actions'] = used + 1; run.setdefault('external_calls', []).append(tool)
        f.write_text(json.dumps(run, indent=2))
    return None

def pre(evt):
    tool = evt.get('tool_name', ''); tool_input = evt.get('tool_input') or {}
    agent = evt.get('agent_type'); cwd = evt.get('cwd', '.')
    m = load_manifest(cwd)
    if m is None:
        return 0 if tool in SAFE_TOOLS else deny('runtime manifest missing; failing closed')
    ledger = m['ledger']
    # 1. External actions are denied company-wide unless a human approval exists for this call.
    #    (a) per-call token: .agentic/approvals/<sha256(tool+input)[:16]>.json with status approved + approved_by
    #    (b) standing approval for a pre-approved content class: .agentic/approvals/standing/<tool>.json, valid only when a
    #        reviewer-written clearance for the artifact named by the tool's clearance_key carries a matching content_class.
    for pat in m.get('external_action_tool_patterns', []):
        if re.search(pat, tool):
            ok, why = external_action_allowed(m, cwd, tool, tool_input)
            if not ok: return deny(why)
            over = charge_run_budget(cwd, tool)
            if over: return deny(over)
            break
    # 1b. Connector tools declared approval-required or prohibited need a per-call human token even if not external.
    spec = (m.get('connector_tools') or {}).get(tool)
    if spec and spec.get('authority') in ('approval-required', 'prohibited'):
        ok, why = external_action_allowed(m, cwd, tool, tool_input)
        if not ok: return deny(f"{tool} is {spec['authority']} by its connector; " + why)
    # 2. Role-scoped denies from the manifest (subagent frontmatter allowlists cover built-ins; this covers MCP/web patterns).
    role = next((a for a in m['agents'] if a['name'] == agent), None) if agent else None
    if role:
        for pat in role.get('deny_tool_patterns', []):
            if re.search(pat, tool): return deny(f"role {agent} may not use {tool}")
    # 2b. Connector servers fail closed: a tool under a declared connector server must be in the published map and granted
    #     to the acting role (the main session may only use observe-authority tools). New/renamed vendor tools are denied.
    mt = re.match(r'^mcp__([a-z0-9_-]+?)__', tool)
    if mt and mt.group(1) in (m.get('known_connector_servers') or []) and mt.group(1) not in (m.get('connector_servers') or []):
        return deny(f'{mt.group(1)} is a published connector this company has not declared under systems; no session may use it')
    if mt and mt.group(1) in (m.get('connector_servers') or []):
        spec = (m.get('connector_tools') or {}).get(tool)
        if spec is None: return deny(f'{tool} is not in the published connector map for {mt.group(1)}; failing closed')
        if agent:
            if agent not in spec.get('owner_agents', []): return deny(f'{tool} is not granted to {agent} by the connector')
        elif spec.get('authority') != 'observe':
            return deny(f'{tool} may not be called from the main session; delegate to a role that holds it')
        # 2c. A cleared artifact is immutable: a tool that changes it is denied while its clearance stands.
        if spec.get('invalidates_clearance') and spec.get('clearance_key'):
            art = str(tool_input.get(spec['clearance_key'], '')).strip()
            if art and re.fullmatch(r'[A-Za-z0-9._-]+', art):
                croot = Path(cwd) / (m.get('clearances', {}).get('root') or '.agentic/ledger/reviews/clearances')
                hits = []
                direct = croot / f'{art}.json'
                if direct.exists(): hits.append(direct)
                mf = spec.get('clearance_match_field')
                if mf and croot.exists():
                    for f in croot.glob('*.json'):
                        try:
                            if str(json.loads(f.read_text()).get(mf, '')) == art: hits.append(f)
                        except Exception: hits.append(f)  # unreadable clearance: treat as blocking
                for cl in hits:
                    try: c = json.loads(cl.read_text())
                    except Exception: c = {'cleared': True}
                    if c.get('cleared') is True:
                        return deny(f'{cl.stem} is cleared; edits to it or its source are not allowed. The reviewer must withdraw the clearance first')
    # 3. Confidential scopes: only the owning role reads or writes inside them.
    p = path_of(tool_input).replace('\\', '/')
    if p:
        for a in m['agents']:
            scope = a.get('confidential_scope')
            if scope and scope.strip('/') in p and agent != a['name']:
                return deny(f"{p} is inside {a['name']} confidential scope")
    # 3b. Runtime authority state is human-owned. No agent may write approvals, counters, run markers, the runtime
    #     manifest, or the generated .claude/ tree — by file tool or by shell.
    control = [c.strip('/') for c in (m.get('control_paths') or ['.agentic/approvals/', '.agentic/runs/', '.agentic/runtime-manifest.json', '.claude/'])]
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit') and p and any(c in p for c in control):
        return deny(f'{p} is runtime authority state; agents may not write it')
    if tool == 'Bash':
        cmd = str(tool_input.get('command', ''))
        if any(c in cmd for c in control) or 'runtime-manifest' in cmd:
            return deny('shell access to runtime authority state (.agentic/approvals, .agentic/runs, .claude, runtime manifest) is denied')
    # 4. Clearance records: only a reviewer role may write them; the author of content never clears it.
    if tool in ('Write', 'Edit', 'MultiEdit') and p:
        croot = (m.get('clearances', {}).get('root') or '.agentic/ledger/reviews/clearances').strip('/')
        if croot in p and not (role and role.get('clearance_writer')):
            return deny(f'only a reviewer role may write clearance records under {croot}')
    # 5. Decision records.
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
