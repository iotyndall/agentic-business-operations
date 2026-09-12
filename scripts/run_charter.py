#!/usr/bin/env python3
"""Run a standing charter: charter -> intake -> routing -> (optionally) a headless Claude Code session -> run record.

usage: run_charter.py <charter.json> [--repo <private-repo-dir>] [--headless] [--dry-run]
       run_charter.py --finish [--repo <private-repo-dir>]        close an interactive run

Run from inside the private company repo (default --repo .). The framework must already be bootstrapped
(.company-os/ present, .claude/ exported). Nothing here grants authority: the guard hook in the session
enforces every external call, and the run record caps how many it may allow (bounds.max_external_actions).
If a standing approval the charter relies on is missing or expired, the run is downgraded to draft-only.
Interactive runs leave the run marker in place (so the guard enforces the budget in the session you paste the
prompt into) until you run `--finish`. Headless runs close the marker themselves.
"""
import json, subprocess, sys, time, uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from router import route_intake  # noqa: E402


def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def standing_ok(repo, tool):
    f = repo / '.agentic' / 'approvals' / 'standing' / f'{tool}.json'
    try: d = load(f)
    except Exception: return False
    return d.get('status') == 'approved' and bool(d.get('approved_by')) and str(d.get('expires', '')) [:10] > time.strftime('%Y-%m-%d', time.gmtime())


def finish(repo):
    runs = repo / '.agentic' / 'runs'; cur = runs / 'current.json'
    if not cur.exists(): print('no active run'); return 0
    record = json.loads(cur.read_text()); record['finished'] = now()
    (runs / f"{record['run_id']}.json").write_text(json.dumps(record, indent=2) + '\n'); cur.unlink()
    print(f"run {record['run_id']} closed: external actions {record.get('external_actions', 0)}/{record.get('max_external_actions')}")
    return 0

def main(argv):
    repo = (Path(argv[argv.index('--repo') + 1]) if '--repo' in argv else Path('.')).resolve()
    if '--finish' in argv: return finish(repo)
    if len(argv) < 2: print(__doc__, file=sys.stderr); return 2
    charter = load(argv[1])
    headless, dry = '--headless' in argv, '--dry-run' in argv
    today = time.strftime('%Y-%m-%d', time.gmtime())
    if charter['expires'] <= today: print(f"charter {charter['id']} expired {charter['expires']}; not running"); return 3
    runs = repo / '.agentic' / 'runs'
    if (runs / 'current.json').exists(): print('another charter run is active (.agentic/runs/current.json); refusing to overlap'); return 4
    cap = charter['bounds']['max_external_actions']; downgraded = []
    for sa in charter['bounds'].get('standing_approvals', []):
        if not standing_ok(repo, sa): downgraded.append(sa)
    if downgraded and cap > 0:
        print(f'standing approval(s) missing/expired: {downgraded}; downgrading to draft-only', file=sys.stderr); cap = 0
    run_id = f"{charter['id']}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{uuid.uuid4().hex[:6]}"
    intake = {'version': 1, 'id': run_id, 'objective': charter['commission'], 'dominant_outcome': charter['dominant_outcome'],
              'risk': charter.get('risk', 'moderate'), 'material_dependencies': [d for d in charter['departments']],
              'requires_external_action': cap > 0, 'requires_financial_commitment': False}
    routing = route_intake(intake)
    intake_path = repo / '.agentic' / 'ledger' / 'intake' / f'{run_id}.json'
    record = {'run_id': run_id, 'charter_id': charter['id'], 'owner_role': charter['owner_role'], 'started': now(), 'trigger': charter['trigger'],
              'max_external_actions': cap, 'external_actions': 0, 'downgraded_standing_approvals': downgraded,
              'intake': str(intake_path), 'routing': routing, 'headless': headless}
    prompt = (f"Charter run {run_id} initiated by {charter['owner_role']} under charter {charter['id']} (approved_by {charter['approved_by']}). "
              f"Intake is at {intake_path}; routing result: {json.dumps(routing)}. Follow the commission flow in CLAUDE.md for department(s) "
              f"{charter['departments']}. This run may perform at most {cap} external action(s); the guard enforces it. "
              f"Write all artifacts under .agentic/ledger/ and finish with a run summary at .agentic/runs/{run_id}.summary.md.\n\nCommission: {charter['commission']}")
    if dry:
        # No filesystem mutation on a dry run: the prospective intake is rendered, not written.
        print(json.dumps({'record': record, 'intake': intake, 'prompt': prompt}, indent=2)); return 0
    runs.mkdir(parents=True, exist_ok=True); intake_path.parent.mkdir(parents=True, exist_ok=True)
    intake_path.write_text(json.dumps(intake, indent=2) + '\n')
    (runs / 'current.json').write_text(json.dumps(record, indent=2))
    if not headless:
        # Interactive: the marker stays until `run_charter.py --finish`, so the session you paste this into is budgeted.
        print(prompt)
        print(f"\n[run {run_id} is active; the guard enforces max_external_actions={cap}. Close it with: run_charter.py --finish --repo {repo}]", file=sys.stderr)
        return 0
    rc = 0
    try:
        r = subprocess.run(['claude', '-p', prompt, '--output-format', 'json'], cwd=repo, capture_output=True, text=True,
                           timeout=60 * charter['bounds'].get('max_runtime_minutes', 30))
        record['session_output'] = r.stdout[-20000:]; record['session_rc'] = r.returncode; rc = r.returncode
    except Exception as exc:
        record['error'] = str(exc); rc = 5
    finally:
        try: record.update(json.loads((runs / 'current.json').read_text()))
        except Exception: pass
        record['finished'] = now()
        (runs / f'{run_id}.json').write_text(json.dumps(record, indent=2) + '\n')
        (runs / 'current.json').unlink(missing_ok=True)
    print(f"run {run_id}: external actions {record.get('external_actions', 0)}/{cap}, rc={rc}")
    return rc


if __name__ == '__main__': raise SystemExit(main(sys.argv))
