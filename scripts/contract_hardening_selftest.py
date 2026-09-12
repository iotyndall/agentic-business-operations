#!/usr/bin/env python3
import copy
import json
import subprocess
import tempfile
from pathlib import Path

from validate_company_contract import validate as validate_contract
from validate_framework_lock import CANONICAL_REPOSITORY, canonical_repo_from_origin, validate as validate_lock
from validate_json_schema import validate_files

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / 'schemas' / 'company-contract.schema.json'
EXAMPLE = ROOT / 'templates' / 'private-company' / 'business-ops.example.json'
SYNTHETIC = ROOT / 'examples' / 'synthetic-company' / 'company-contract.json'

assert validate_files(SCHEMA, EXAMPLE) == [], validate_files(SCHEMA, EXAMPLE)
assert validate_files(SCHEMA, SYNTHETIC) == [], validate_files(SCHEMA, SYNTHETIC)
base = json.loads(EXAMPLE.read_text())
assert validate_contract(base) == [], validate_contract(base)

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    def schema_errors(mutator):
        d = copy.deepcopy(base)
        mutator(d)
        p = td / 'bad.json'
        p.write_text(json.dumps(d))
        return validate_files(SCHEMA, p)

    assert schema_errors(lambda d: d.pop('company'))
    assert schema_errors(lambda d: d.__setitem__('unexpected', True))

    def remove_kind(d):
        d['systems'] = [{'id': 'crm', 'write_authority': 'none'}]
    assert schema_errors(remove_kind)

bad = copy.deepcopy(base)
bad['systems'] = [{'id': 'crm', 'kind': 'crm', 'write_authority': 'none'}]
bad['data']['allowed_context_refs'] = ['system://missing-system']
assert any('does not resolve' in x for x in validate_contract(bad)), validate_contract(bad)

bad = copy.deepcopy(base)
bad['systems'] = [
    {'id': 'crm', 'kind': 'crm', 'write_authority': 'none'},
    {'id': 'crm', 'kind': 'crm', 'write_authority': 'none'},
]
assert any('duplicate system id' in x for x in validate_contract(bad)), validate_contract(bad)

head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
origin = subprocess.check_output(['git', '-C', str(ROOT), 'remote', 'get-url', 'origin'], text=True).strip()
lock = {
    'version': 1,
    'repository': CANONICAL_REPOSITORY,
    'commit': head,
    'contract_schema': 'schemas/company-contract.schema.json',
}
assert validate_lock(lock, ROOT, head, origin) == [], validate_lock(lock, ROOT, head, origin)

bad = copy.deepcopy(lock); bad['commit'] = '0' * 40
assert any('does not match lock commit' in x for x in validate_lock(bad, ROOT, head, origin))
bad = copy.deepcopy(lock); bad['repository'] = 'example/other'
assert any('repository must equal' in x for x in validate_lock(bad, ROOT, head, origin))
bad = copy.deepcopy(lock); bad['contract_schema'] = 'schemas/does-not-exist.json'
assert any('does not exist' in x for x in validate_lock(bad, ROOT, head, origin))

assert canonical_repo_from_origin('https://github.com/iotyndall/agentic-business-operations.git') == CANONICAL_REPOSITORY
assert canonical_repo_from_origin('git@github.com:iotyndall/agentic-business-operations.git') == CANONICAL_REPOSITORY
assert canonical_repo_from_origin('https://evil.example/iotyndall/agentic-business-operations.git') is None
assert canonical_repo_from_origin('/tmp/iotyndall/agentic-business-operations') is None
assert any('origin must be' in x for x in validate_lock(lock, ROOT, head, 'https://evil.example/iotyndall/agentic-business-operations.git'))

print('PASS schema application, system references, immutable lock and trusted-origin regression tests')
