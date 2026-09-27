#!/usr/bin/env python3
"""Prove the SDK runtime's permission policy (node --test) and that run_charter.py --runtime sdk records the session
outcome and closes the run marker. A stub session stands in for the model, so this runs without credentials."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; PY = sys.executable
RUNTIME = ROOT / 'claude' / 'runtime' / 'agent_sdk'
failures = []

if not shutil.which('node'):
    print('ERROR: node is required for the agent-sdk runtime'); sys.exit(1)
r = subprocess.run(['node', '--test', 'policy.test.mjs'], cwd=RUNTIME, capture_output=True, text=True)
if r.returncode != 0: failures.append('policy tests failed:\n' + r.stdout[-2000:] + r.stderr[-2000:])

charter = json.loads((ROOT / 'examples/synthetic-company/charters/marketing-weekly.charter.json').read_text())
charter['bounds'].update(max_external_actions=0, standing_approvals=[], max_budget_usd=1.5, read_tools=['mcp__finance__*'])
with tempfile.TemporaryDirectory() as td:
    repo = Path(td); (repo / 'cadence').mkdir()
    ch = repo / 'cadence' / 'c.json'; ch.write_text(json.dumps(charter))
    stub = repo / 'stub.mjs'
    stub.write_text("import {readFileSync} from 'node:fs'; const i = JSON.parse(readFileSync(0,'utf8'));\n"
                    "process.stdout.write(JSON.stringify({runtime:'agent-sdk', subtype:'success', is_error:false, echoed_budget:i.max_budget_usd, echoed_read:i.read_tools, "
                    "echoed_repo:i.repo, prompt_has_intake: i.prompt.includes('.agentic/ledger/intake')})+'\\n');\n")
    env = {**os.environ, 'COMPANY_OS_SDK_SESSION': str(stub)}
    r = subprocess.run([PY, str(ROOT / 'scripts/run_charter.py'), str(ch), '--repo', str(repo), '--headless', '--runtime', 'sdk'],
                       capture_output=True, text=True, env=env)
    recs = [p for p in (repo / '.agentic/runs').glob('*.json') if p.name != 'current.json']
    if r.returncode != 0 or len(recs) != 1: failures.append(f'sdk headless run failed: rc={r.returncode} {r.stdout[-500:]} {r.stderr[-500:]}')
    else:
        rec = json.loads(recs[0].read_text()); s = rec.get('session', {})
        if rec.get('runtime') != 'sdk' or rec.get('max_budget_usd') != 1.5: failures.append(f'record missing runtime/budget: {rec}')
        if s.get('echoed_read') != ['mcp__finance__*']: failures.append(f'read_tools not passed to the session: {s}')
        if s.get('echoed_budget') != 1.5 or s.get('echoed_repo') != str(repo.resolve()) or not s.get('prompt_has_intake'):
            failures.append(f'session input wrong: {s}')
        if (repo / '.agentic/runs/current.json').exists(): failures.append('run marker left behind')
    r = subprocess.run([PY, str(ROOT / 'scripts/run_charter.py'), str(ch), '--repo', str(repo), '--headless', '--runtime', 'bogus'], capture_output=True, text=True)
    if r.returncode != 2: failures.append('unknown runtime should be rejected')

if failures:
    print('\n'.join('ERROR: ' + f for f in failures)); sys.exit(1)
print('PASS agent-sdk runtime: tool policy (ledger-only writes, repo-only reads, no shell, actor-aware web, declared MCP only), run_charter --runtime sdk passes budget and records the session, closes the marker')
