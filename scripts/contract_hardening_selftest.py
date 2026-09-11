#!/usr/bin/env python3
import copy, json, subprocess, tempfile
from pathlib import Path
from validate_company_contract import validate as validate_contract
from validate_framework_lock import CANONICAL_REPOSITORY, validate as validate_lock

ROOT=Path(__file__).resolve().parents[1]
base=json.loads((ROOT/'examples/synthetic-company/company-contract.json').read_text())
assert validate_contract(base) == [], validate_contract(base)

bad=copy.deepcopy(base); bad['data']['allowed_context_refs'].append('system://missing-system')
assert any('unresolved system context reference' in x for x in validate_contract(bad))

bad=copy.deepcopy(base); bad['systems'].append(copy.deepcopy(bad['systems'][0]))
assert any('system ids must be unique' in x for x in validate_contract(bad))

head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
origin=subprocess.check_output(['git','-C',str(ROOT),'remote','get-url','origin'],text=True).strip()
lock={'repository':CANONICAL_REPOSITORY,'commit':head,'contract_schema':'schemas/company-contract.schema.json','adoption':'selftest'}
assert validate_lock(lock,ROOT,head,origin) == [], validate_lock(lock,ROOT,head,origin)

bad=copy.deepcopy(lock); bad['commit']='0'*40
assert any('does not match lock commit' in x for x in validate_lock(bad,ROOT,head,origin))

bad=copy.deepcopy(lock); bad['contract_schema']='schemas/does-not-exist.json'
assert any('does not exist' in x for x in validate_lock(bad,ROOT,head,origin))

bad=copy.deepcopy(lock); bad['repository']='example/other'
assert any('repository must equal' in x for x in validate_lock(bad,ROOT,head,origin))

print('PASS contract/reference/lock hardening regression tests')
