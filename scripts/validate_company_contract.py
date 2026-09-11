#!/usr/bin/env python3
import json, sys
VALID_DEPTS={'chief-of-staff','sales','marketing','service','operations','legal','finance','product'}
VALID_WRITE={'none','bounded','approval-required'}

def validate(d):
    errors=[]
    if d.get('version') != 1: errors.append('version must equal 1')
    depts=d.get('departments')
    if not isinstance(depts,list) or not depts or any(x not in VALID_DEPTS for x in depts): errors.append('departments invalid')
    authority=d.get('authority',{})
    if authority.get('external_action_default') not in {'deny','approval-required'}: errors.append('external actions must default deny/approval-required')
    if authority.get('financial_commitment_default') not in {'deny','approval-required'}: errors.append('financial commitments must default deny/approval-required')
    if d.get('data',{}).get('private_by_default') is not True: errors.append('data.private_by_default must be true')
    systems=d.get('systems')
    if not isinstance(systems,list): errors.append('systems must be an array')
    else:
        for s in systems:
            if s.get('write_authority') not in VALID_WRITE: errors.append(f"system {s.get('id','?')} has invalid write_authority")
    return errors

def main():
    if len(sys.argv)<2: print('usage: validate_company_contract.py <contract.json> [...]', file=sys.stderr); return 2
    failed=False
    for path in sys.argv[1:]:
        try: d=json.load(open(path,encoding='utf-8'))
        except Exception as exc: print(f'ERROR {path}: {exc}'); failed=True; continue
        errs=validate(d)
        if errs:
            failed=True
            for e in errs: print(f'ERROR {path}: {e}')
        else: print(f'PASS {path}')
    return 1 if failed else 0
if __name__=='__main__': raise SystemExit(main())
