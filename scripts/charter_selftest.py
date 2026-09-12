#!/usr/bin/env python3
"""Prove charters can start work but never widen authority, and that a run's external-action budget is enforced by the guard."""
import copy, json, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; PY = sys.executable
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_charter import validate  # noqa: E402

company = json.loads((ROOT / 'examples/synthetic-company/company-contract.json').read_text())
good = json.loads((ROOT / 'examples/synthetic-company/charters/marketing-weekly.charter.json').read_text())
failures = []
if validate(company, good): failures.append(f'good charter rejected: {validate(company, good)}')

def mutate(name, fn):
    c = copy.deepcopy(good); fn(c)
    if not validate(company, c): failures.append(f'mutation accepted: {name}')

mutate('expired charter', lambda c: c.update(expires='2000-01-01'))
mutate('no approver', lambda c: c.update(approved_by=''))
mutate('owner is not a department', lambda c: c.update(owner_role='ceo'))
mutate('department charter commissions another department', lambda c: c.update(owner_role='service'))
mutate('disabled department', lambda c: c.update(departments=['sales'], dominant_outcome='commercial-opportunity') or company['departments'].remove('sales'))
company = json.loads((ROOT / 'examples/synthetic-company/company-contract.json').read_text())
mutate('outcome routes outside charter departments', lambda c: c.update(dominant_outcome='financial-control'))
mutate('standing approval for a non-connector tool', lambda c: c['bounds'].update(standing_approvals=['mcp__gmail__send_message']))
mutate('standing approval for a read tool', lambda c: c['bounds'].update(standing_approvals=['mcp__yalloha__get_analytics']))
mutate('external budget without any standing approval', lambda c: c['bounds'].update(standing_approvals=[]))
mutate('cron without timezone', lambda c: c['trigger'].pop('timezone'))

# runner + budget: export a runtime into a temp private repo, run the charter dry, then simulate a session spending its budget
with tempfile.TemporaryDirectory() as td:
    repo = Path(td)
    subprocess.run([PY, str(ROOT / 'scripts/export_claude_code.py'), str(ROOT / 'examples/synthetic-company/company-contract.json'), str(repo)], check=True, capture_output=True)
    (repo / 'cadence').mkdir(); ch = repo / 'cadence/marketing-weekly.charter.json'; ch.write_text(json.dumps(good))
    # no standing approval on disk -> downgraded to draft-only
    r = subprocess.run([PY, str(ROOT / 'scripts/run_charter.py'), str(ch), '--repo', str(repo), '--dry-run'], capture_output=True, text=True)
    out = json.loads(r.stdout)
    if out['record']['max_external_actions'] != 0 or 'mcp__yalloha__publish_post' not in out['record']['downgraded_standing_approvals']:
        failures.append('missing standing approval should downgrade the run to draft-only')
    if out['record']['routing']['department'] != 'marketing': failures.append(f"charter routed to {out['record']['routing']}")
    # with the standing approval present: run for real (non-headless), which writes the run record and leaves no current.json
    sa = repo / '.agentic/approvals/standing'; sa.mkdir(parents=True)
    (sa / 'mcp__yalloha__publish_post.json').write_text(json.dumps({'status': 'approved', 'approved_by': 'human', 'expires': '2999-01-01', 'content_classes': ['consented-review-repost']}))
    r = subprocess.run([PY, str(ROOT / 'scripts/run_charter.py'), str(ch), '--repo', str(repo)], capture_output=True, text=True)
    recs = list((repo / '.agentic/runs').glob('marketing-weekly-reviews-*.json'))
    if r.returncode != 0 or len(recs) != 1 or (repo / '.agentic/runs/current.json').exists(): failures.append(f'run record not written cleanly: rc={r.returncode} {r.stderr[-300:]}')
    if not list((repo / '.agentic/ledger/intake').glob('*.json')): failures.append('intake not written')
    # budget: simulate an active run with cap 2 and a fully-approved publish; third call must be denied
    cl = repo / '.agentic/ledger/reviews/clearances'; cl.mkdir(parents=True)
    (cl / 'p1.json').write_text(json.dumps({'cleared': True, 'content_class': 'consented-review-repost', 'reviewer': 'marketing-content-reviewer'}))
    (repo / '.agentic/runs/current.json').write_text(json.dumps({'run_id': 'r1', 'max_external_actions': 2, 'external_actions': 0}))
    def guard(inp):
        evt = {'tool_name': 'mcp__yalloha__publish_post', 'tool_input': inp, 'agent_type': 'social-media-specialist', 'cwd': str(repo)}
        o = subprocess.run([PY, str(repo / '.claude/hooks/company_os_guard.py'), 'pre'], input=json.dumps(evt), capture_output=True, text=True, cwd=repo).stdout
        return '"deny"' in o, o
    results = [guard({'postId': 'p1', 'platforms': ['facebook']}) for _ in range(3)]
    if [d for d, _ in results] != [False, False, True]: failures.append(f'budget not enforced: {[d for d,_ in results]}')
    if 'budget' not in results[2][1]: failures.append('third call denied for the wrong reason: ' + results[2][1])
    run = json.loads((repo / '.agentic/runs/current.json').read_text())
    if run['external_actions'] != 2 or run.get('external_calls') != ['mcp__yalloha__publish_post'] * 2: failures.append(f'budget accounting wrong: {run}')
    # malformed run file fails closed
    (repo / '.agentic/runs/current.json').write_text('{not json')
    d, o = guard({'postId': 'p1', 'platforms': ['facebook']})
    if not d: failures.append('malformed run file should fail closed')
    # overlapping run refused
    r = subprocess.run([PY, str(ROOT / 'scripts/run_charter.py'), str(ch), '--repo', str(repo)], capture_output=True, text=True)
    if r.returncode != 4: failures.append('runner should refuse to overlap an active run')

if failures:
    print('\n'.join('ERROR: ' + f for f in failures)); sys.exit(1)
print('PASS charters: 10 authority-widening mutations rejected; runner downgrades without standing approval, writes run records, refuses overlap; guard enforces the per-run external-action budget and fails closed')
