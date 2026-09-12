#!/usr/bin/env python3
"""Prove a company contract's validator fails closed on an undeclared system reference.

usage: contract_selftest.py <business-ops.json>
Runs validate_company_contract.py against a mutated copy that references an
undeclared system and requires exit 1 plus the specific diagnostic.
"""
import json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SENTINEL = 'system://__undeclared_selftest__'
EXPECTED = f'allowed_context_ref {SENTINEL} does not resolve to a declared system'

def main():
    if len(sys.argv) != 2:
        print('usage: contract_selftest.py <business-ops.json>', file=sys.stderr)
        return 2
    d = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    d.setdefault('data', {}).setdefault('allowed_context_refs', []).append(SENTINEL)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(d, f); bad = f.name
    r = subprocess.run([sys.executable, str(HERE / 'validate_company_contract.py'), bad], capture_output=True, text=True)
    out = r.stdout + r.stderr
    print(out, end='')
    if r.returncode != 1:
        print(f'::error::Expected semantic rejection exit 1, got {r.returncode}.')
        return 1
    if EXPECTED not in out:
        print('::error::Validator failed without the expected unresolved-system diagnostic.')
        return 1
    print('PASS contract validator fails closed on undeclared system reference')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
