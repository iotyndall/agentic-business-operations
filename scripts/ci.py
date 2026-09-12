#!/usr/bin/env python3
"""Single deterministic CI gate. Run locally before pushing: python scripts/ci.py"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = 'scripts'
GATES = [
    ('structure, JSON assets, public safety, Actions pinning', [f'{S}/validate_repo.py']),
    ('company-contract schema (synthetic)', [f'{S}/validate_json_schema.py', 'schemas/company-contract.schema.json', 'examples/synthetic-company/company-contract.json']),
    ('company-contract schema (template)', [f'{S}/validate_json_schema.py', 'schemas/company-contract.schema.json', 'templates/private-company/business-ops.example.json']),
    ('contact-center-profile schema', [f'{S}/validate_json_schema.py', 'schemas/contact-center-profile.schema.json', 'examples/synthetic-company/contact-center-profile.json']),
    ('semantic company invariants', [f'{S}/validate_company_contract.py', 'examples/synthetic-company/company-contract.json', 'templates/private-company/business-ops.example.json']),
    ('contact center capability boundaries', [f'{S}/validate_contact_center_profile.py', 'examples/synthetic-company/company-contract.json', 'examples/synthetic-company/contact-center-profile.json']),
    ('provider/model routing', [f'{S}/model_selection_selftest.py']),
    ('private-framework trust boundary', [f'{S}/contract_hardening_selftest.py']),
    ('synthetic company routing and authority', [f'{S}/evaluate_scenarios.py']),
    ('fail-closed contract selftest', [f'{S}/contract_selftest.py', 'examples/synthetic-company/company-contract.json']),
]

def main():
    failed = []
    for name, cmd in GATES:
        print(f'::group::{name}')
        r = subprocess.run([sys.executable, *cmd], cwd=ROOT)
        print('::endgroup::')
        if r.returncode != 0:
            failed.append(name)
            print(f'::error::gate failed: {name}')
    if failed:
        print(f'FAIL: {len(failed)} gate(s): {failed}')
        return 1
    print(f'PASS: all {len(GATES)} CI gates')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
