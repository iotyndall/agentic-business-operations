#!/usr/bin/env python3
"""Prove the Claude Code adapter exports the right subagents and the guard fails closed."""
import json, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

def run(args, stdin=None, cwd=None):
    r = subprocess.run([PY, *args], input=stdin, capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout, r.stderr

def guard(evt, cwd, mode='pre'):
    rc, out, err = run([str(cwd / '.claude/hooks/company_os_guard.py'), mode], stdin=json.dumps(evt), cwd=cwd)
    denied = 'permissionDecision' in out and '"deny"' in out
    return denied, out.strip()

failures = []
with tempfile.TemporaryDirectory() as td:
    out = Path(td)
    # A private contract that declares the connector servers as systems (the synthetic company does not).
    contract = json.loads((ROOT / 'examples/synthetic-company/company-contract.json').read_text())
    contract['systems'] += [{'id': s, 'kind': 'external', 'write_authority': 'bounded'} for s in ('yalloha', 'quickbooks', 'hospitable', 'pricelabs')]
    cpath = out / 'contract.json'; cpath.write_text(json.dumps(contract))
    rc, so, se = run([str(ROOT / 'scripts/export_claude_code.py'), str(cpath), str(out)])
    if rc != 0: failures.append(f'export failed: {se}')
    # Undeclared systems are stripped AND denied: export the plain synthetic contract elsewhere and check.
    with tempfile.TemporaryDirectory() as td2:
        bare = json.loads((ROOT / 'examples/synthetic-company/company-contract.json').read_text())
        bare['systems'] = [x for x in bare['systems'] if x['id'] != 'yalloha']
        (Path(td2) / 'bare.json').write_text(json.dumps(bare))
        run([str(ROOT / 'scripts/export_claude_code.py'), str(Path(td2) / 'bare.json'), td2])
        sm = (Path(td2) / '.claude/agents/social-media-specialist.md').read_text()
        if 'mcpServers' in sm.split('---', 2)[1]: failures.append('undeclared yalloha system was exported into mcpServers')
        rm = json.loads((Path(td2) / '.agentic/runtime-manifest.json').read_text())
        sa = next(a for a in rm['agents'] if a['name'] == 'social-media-specialist')
        if not any(p == '^mcp__yalloha__.*' for p in sa['deny_tool_patterns']): failures.append('undeclared yalloha system is not denied')
        if rm['connector_servers']: failures.append('connector_servers should be empty when no system is declared')
        o = subprocess.run([PY, str(Path(td2) / '.claude/hooks/company_os_guard.py'), 'pre'], input=json.dumps({'tool_name': f'mcp__yalloha__list_properties', 'tool_input': {}, 'cwd': td2}), capture_output=True, text=True, cwd=td2).stdout
        if '"deny"' not in o: failures.append('main session could use a known-but-undeclared connector server')
    # A draft-only profile strips publish ownership even though the vendor connector grants it to social_media.
    with tempfile.TemporaryDirectory() as td4:
        prof = json.loads((ROOT / 'examples/yalloha-host/marketing-profile.json').read_text())
        prof['roles']['social_media']['allowed_capabilities'].remove('post.publish_bounded')
        prof['capability_bindings'] = [b for b in prof['capability_bindings'] if b['capability'] != 'post.publish_bounded']
        (Path(td4) / 'p.json').write_text(json.dumps(prof))
        run([str(ROOT / 'scripts/export_claude_code.py'), str(cpath), td4, '--marketing-profile', str(Path(td4) / 'p.json')])
        rm4 = json.loads((Path(td4) / '.agentic/runtime-manifest.json').read_text())
        if rm4['connector_tools']['mcp__yalloha__publish_post']['owner_agents']: failures.append('draft-only profile still grants publish_post')
        if 'social-media-specialist' not in rm4['connector_tools']['mcp__yalloha__generate_post']['owner_agents']: failures.append('profile-granted draft tool lost')
    # write_authority none on the system leaves only observe tools.
    with tempfile.TemporaryDirectory() as td5:
        ro = json.loads(cpath.read_text())
        for x in ro['systems']:
            if x['id'] == 'yalloha': x['write_authority'] = 'none'
        (Path(td5) / 'c.json').write_text(json.dumps(ro))
        run([str(ROOT / 'scripts/export_claude_code.py'), str(Path(td5) / 'c.json'), td5])
        rm5 = json.loads((Path(td5) / '.agentic/runtime-manifest.json').read_text())
        if rm5['connector_tools']['mcp__yalloha__generate_post']['owner_agents']: failures.append('read-only system still grants a draft tool')
        if not rm5['connector_tools']['mcp__yalloha__list_properties']['owner_agents']: failures.append('read-only system lost observe tools')
        if rm5['connector_tools']['mcp__yalloha__publish_post']['standing_allowed']: failures.append('read-only system should not allow standing approvals')
    # Disabled roles in a marketing profile are not exported.
    with tempfile.TemporaryDirectory() as td3:
        run([str(ROOT / 'scripts/export_claude_code.py'), str(cpath), td3, '--marketing-profile', str(ROOT / 'examples/yalloha-host/marketing-profile.json')])
        got = sorted(p.stem for p in (Path(td3) / '.claude/agents').glob('*.md'))
        for gone in ('direct-email-specialist', 'paid-media-specialist', 'agent-relations-specialist'):
            if gone in got: failures.append(f'{gone} exported despite enabled:false in the marketing profile')
    agents = sorted(p.stem for p in (out / '.claude/agents').glob('*.md'))
    expected = ['adversarial-reviewer', 'agent-relations-specialist', 'brand-manager', 'business-performance-analyst', 'corporate-development-analyst', 'direct-email-specialist', 'long-range-planner', 'market-intelligence-analyst', 'marketing-content-reviewer', 'paid-media-specialist', 'partnerships-program-manager', 'social-media-specialist', 'strategy-lead']
    if agents != expected: failures.append(f'exported agents {agents} != {expected}')
    for a in agents:
        text = (out / f'.claude/agents/{a}.md').read_text()
        if not text.startswith('---\nname: ' + a): failures.append(f'{a}: bad frontmatter')
        if '## ' not in text.split('---',2)[2]: failures.append(f'{a}: role contract body missing')
    settings = json.loads((out / '.claude/settings.json').read_text())
    if 'PreToolUse' not in settings.get('hooks', {}): failures.append('settings.json missing PreToolUse hook')
    manifest = json.loads((out / '.agentic/runtime-manifest.json').read_text())
    if manifest['external_action_default'] != 'deny': failures.append('manifest should carry deny default')

    cwd = out
    cases = [
        ('corp-dev cannot web search', {'tool_name': 'WebSearch', 'tool_input': {'query': 'x'}, 'agent_type': 'corporate-development-analyst', 'cwd': str(cwd)}, True),
        ('corp-dev cannot call any MCP', {'tool_name': 'mcp__gmail__send_message', 'tool_input': {}, 'agent_type': 'corporate-development-analyst', 'cwd': str(cwd)}, True),
        ('main session cannot send email without approval token', {'tool_name': 'mcp__gmail__send_message', 'tool_input': {'to': ['a@example.com']}, 'cwd': str(cwd)}, True),
        ('performance analyst cannot write to QuickBooks', {'tool_name': 'mcp__quickbooks__create_invoice', 'tool_input': {}, 'agent_type': 'business-performance-analyst', 'cwd': str(cwd)}, True),
        ('performance analyst may read QuickBooks', {'tool_name': 'mcp__quickbooks__get_profit_and_loss', 'tool_input': {}, 'agent_type': 'business-performance-analyst', 'cwd': str(cwd)}, False),
        ('strategy lead cannot read corp-dev scope', {'tool_name': 'Read', 'tool_input': {'file_path': f'{cwd}/.agentic/ledger/corpdev/valuation.json'}, 'agent_type': 'strategy-lead', 'cwd': str(cwd)}, True),
        ('corp-dev may read its own scope', {'tool_name': 'Read', 'tool_input': {'file_path': f'{cwd}/.agentic/ledger/corpdev/valuation.json'}, 'agent_type': 'corporate-development-analyst', 'cwd': str(cwd)}, False),
        ('agent cannot write a decided record', {'tool_name': 'Write', 'tool_input': {'file_path': f'{cwd}/.agentic/ledger/decisions/sedona.json', 'content': '{}'}, 'agent_type': 'strategy-lead', 'cwd': str(cwd)}, True),
        ('decision draft with one option is blocked', {'tool_name': 'Write', 'tool_input': {'file_path': f'{cwd}/.agentic/ledger/decisions/sedona.draft.json', 'content': json.dumps({'options': [{'id': 'hold'}], 'review_ref': 'r1'})}, 'agent_type': 'strategy-lead', 'cwd': str(cwd)}, True),
        ('decision draft without review is blocked', {'tool_name': 'Write', 'tool_input': {'file_path': f'{cwd}/.agentic/ledger/decisions/sedona.draft.json', 'content': json.dumps({'options': [{'id': 'hold'}, {'id': 'sell'}]})}, 'agent_type': 'strategy-lead', 'cwd': str(cwd)}, True),
        ('agent cannot pre-fill the decision', {'tool_name': 'Write', 'tool_input': {'file_path': f'{cwd}/.agentic/ledger/decisions/sedona.draft.json', 'content': json.dumps({'options': [{'id': 'hold'}, {'id': 'sell'}], 'review_ref': 'r1', 'decision': 'sell'})}, 'agent_type': 'strategy-lead', 'cwd': str(cwd)}, True),
        ('valid decision draft is allowed', {'tool_name': 'Write', 'tool_input': {'file_path': f'{cwd}/.agentic/ledger/decisions/sedona.draft.json', 'content': json.dumps({'options': [{'id': 'hold'}, {'id': 'sell'}], 'review_ref': 'r1', 'assumptions': [{'owner': 'lead', 'basis': 'x', 'confidence': 'medium'}]})}, 'agent_type': 'strategy-lead', 'cwd': str(cwd)}, False),
        ('plain read is allowed', {'tool_name': 'Read', 'tool_input': {'file_path': f'{cwd}/README.md'}, 'agent_type': 'market-intelligence-analyst', 'cwd': str(cwd)}, False),
    ]
    # ---- marketing / connector flow: reviewer clears, specialist publishes, everyone else is denied ----
    Y = 'mcp__yalloha__'
    pub = {'postId': 'post-123', 'platforms': ['facebook']}
    def ev(tool, inp, agent=None, extra=None):
        e = {'tool_name': tool, 'tool_input': inp, 'cwd': str(cwd)}
        if agent: e['agent_type'] = agent
        if extra: e.update(extra)
        return e
    def check(name, evt, should_deny):
        denied, out_text = guard(evt, cwd)
        cases.append((name, None, should_deny))
        if denied != should_deny: failures.append(f'{name}: expected deny={should_deny}, got {out_text or "allow"}')
    cl_dir = cwd / '.agentic/ledger/reviews/clearances'; cl_dir.mkdir(parents=True, exist_ok=True)
    st_dir = cwd / '.agentic/approvals/standing'; st_dir.mkdir(parents=True, exist_ok=True)
    flow = [
        ('specialist may read reviews', ev(f'{Y}list_pending_reviews', {}, 'social-media-specialist'), False),
        ('specialist may draft a post', ev(f'{Y}generate_post', {'reviewId': 'r1'}, 'social-media-specialist'), False),
        ('specialist cannot publish with no approval', ev(f'{Y}publish_post', pub, 'social-media-specialist'), True),
        ('specialist cannot change brand settings', ev(f'{Y}update_preferences', {'imageStyle': 'bold'}, 'social-media-specialist'), True),
        ('specialist cannot touch affiliate money', ev(f'{Y}mark_commission_paid', {'commissionId': 'c1'}, 'social-media-specialist'), True),
        ('reviewer cannot draft', ev(f'{Y}generate_post', {'reviewId': 'r1'}, 'marketing-content-reviewer'), True),
        ('reviewer cannot publish', ev(f'{Y}publish_post', pub, 'marketing-content-reviewer'), True),
        ('reviewer may read the post', ev(f'{Y}get_post', {'postId': 'post-123'}, 'marketing-content-reviewer'), False),
        ('brand manager cannot publish', ev(f'{Y}publish_post', pub, 'brand-manager'), True),
        ('brand manager settings change needs a per-call human token', ev(f'{Y}update_preferences', {'imageStyle': 'bold'}, 'brand-manager'), True),
        ('paid media cannot see yalloha', ev(f'{Y}get_analytics', {}, 'paid-media-specialist'), True),
        ('strategy analyst cannot see yalloha', ev(f'{Y}get_analytics', {}, 'business-performance-analyst'), True),
        ('specialist cannot write its own clearance', ev('Write', {'file_path': str(cl_dir / 'post-123.json'), 'content': '{}'}, 'social-media-specialist'), True),
        ('reviewer may write a clearance', ev('Write', {'file_path': str(cl_dir / 'post-123.json'), 'content': '{}'}, 'marketing-content-reviewer'), False),
    ]
    for c in flow: check(*c)
    # standing approval present but no clearance yet -> still denied
    (st_dir / f'{Y}publish_post.json').write_text(json.dumps({'status': 'approved', 'approved_by': 'human@example', 'expires': '2999-01-01', 'content_classes': ['consented-review-repost'], 'clearance_key': 'postId'}))
    check('standing approval without clearance is denied', ev(f'{Y}publish_post', pub, 'social-media-specialist'), True)
    (cl_dir / 'post-123.json').write_text(json.dumps({'cleared': True, 'content_class': 'scheduled-calendar-post', 'reviewer': 'marketing-content-reviewer'}))
    check('clearance of a non-preapproved class is denied', ev(f'{Y}publish_post', pub, 'social-media-specialist'), True)
    (cl_dir / 'post-123.json').write_text(json.dumps({'cleared': True, 'content_class': 'consented-review-repost', 'reviewer': 'marketing-content-reviewer'}))
    check('cleared pre-approved repost publishes under standing approval', ev(f'{Y}publish_post', pub, 'social-media-specialist'), False)
    check('a different post is still denied', ev(f'{Y}publish_post', {'postId': 'post-999', 'platforms': ['facebook']}, 'social-media-specialist'), True)
    (st_dir / f'{Y}publish_post.json').write_text(json.dumps({'status': 'approved', 'approved_by': 'human@example', 'expires': '2000-01-01', 'content_classes': ['consented-review-repost']}))
    check('expired standing approval is denied', ev(f'{Y}publish_post', pub, 'social-media-specialist'), True)
    import hashlib
    d = hashlib.sha256(json.dumps({'tool': f'{Y}publish_post', 'input': pub}, sort_keys=True).encode()).hexdigest()[:16]
    (cwd / '.agentic/approvals').mkdir(parents=True, exist_ok=True)
    (cwd / f'.agentic/approvals/{d}.json').write_text(json.dumps({'status': 'approved', 'approved_by': 'human@example'}))
    check('per-call human token publishes even with expired standing approval', ev(f'{Y}publish_post', pub, 'social-media-specialist'), False)
    # Codex findings
    check('unlisted vendor tool under a connector server fails closed', ev(f'{Y}set_booking_url', {'url': 'x'}, 'social-media-specialist'), True)
    check('main session may call an observe tool on the connector', ev(f'{Y}list_properties', {}), False)
    check('main session may not draft on the connector', ev(f'{Y}generate_post', {'reviewId': 'r1'}), True)
    check('cleared post cannot be edited', ev(f'{Y}update_caption', {'postId': 'post-123', 'caption': 'changed'}, 'social-media-specialist'), True)
    check('uncleared post can be edited', ev(f'{Y}update_caption', {'postId': 'post-777', 'caption': 'x'}, 'social-media-specialist'), False)
    (st_dir / f'{Y}publish_post.json').write_text(json.dumps({'status': 'approved', 'approved_by': 'human@example', 'expires': '2999-01-01', 'content_classes': ['consented-review-repost'], 'max_per_day': 1}))
    (cwd / f'.agentic/approvals/{d}.json').unlink()
    check('first publish under max_per_day=1 allowed', ev(f'{Y}publish_post', pub, 'social-media-specialist'), False)
    check('second publish same day denied by max_per_day', ev(f'{Y}publish_post', pub, 'social-media-specialist'), True)
    # round 2
    check('agent cannot write a standing approval', ev('Write', {'file_path': str(st_dir / f'{Y}publish_post.json'), 'content': '{}'}, 'social-media-specialist'), True)
    check('agent cannot reset a daily counter', ev('Edit', {'file_path': str(st_dir / f'{Y}publish_post.counter.json'), 'old_string': '1', 'new_string': '0'}, 'brand-manager'), True)
    check('agent cannot touch the run marker', ev('Write', {'file_path': str(cwd / '.agentic/runs/current.json'), 'content': '{}'}, 'strategy-lead'), True)
    check('agent cannot edit the generated agents tree', ev('Write', {'file_path': str(cwd / '.claude/agents/x.md'), 'content': ''}, 'strategy-lead'), True)
    check('shell access to approvals is denied', ev('Bash', {'command': 'cat > .agentic/approvals/standing/x.json'}, 'market-intelligence-analyst'), True)
    check('agent may still write ordinary ledger artifacts', ev('Write', {'file_path': str(cwd / '.agentic/ledger/handoffs/x.json'), 'content': '{}'}, 'strategy-lead'), False)
    (cl_dir / 'post-123.json').write_text(json.dumps({'cleared': True, 'content_class': 'consented-review-repost', 'reviewer': 'marketing-content-reviewer', 'review_id': 'r1'}))
    check('regenerating a review whose post is cleared is denied', ev(f'{Y}generate_post', {'reviewId': 'r1'}, 'social-media-specialist'), True)
    check('regenerating an uncleared review is allowed', ev(f'{Y}generate_post', {'reviewId': 'r2'}, 'social-media-specialist'), False)
    for name, evt, should_deny in cases:
        if evt is None: continue
        denied, out_text = guard(evt, cwd)
        if denied != should_deny: failures.append(f'{name}: expected deny={should_deny}, got {out_text or "allow"}')
    # missing manifest fails closed
    with tempfile.TemporaryDirectory() as empty:
        denied, _ = guard({'tool_name': 'Write', 'tool_input': {'file_path': 'x'}, 'cwd': empty}, cwd)
        if not denied: failures.append('missing manifest should fail closed')
    # post hook appends an event
    guard({'tool_name': 'Write', 'tool_input': {'file_path': 'x'}, 'agent_type': 'strategy-lead', 'cwd': str(cwd), 'session_id': 's1'}, cwd, mode='post')
    if not (cwd / '.agentic/ledger/events.jsonl').exists(): failures.append('post hook did not append ledger event')

if failures:
    print('\n'.join('ERROR: ' + f for f in failures)); sys.exit(1)
print(f'PASS Claude Code adapter exports {len(expected)} subagents; guard denies {sum(1 for c in cases if c[2])} authority violations and allows {sum(1 for c in cases if not c[2])} in-authority calls')
