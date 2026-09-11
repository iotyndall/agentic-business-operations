#!/usr/bin/env python3
import json, re, sys

VALID_DEPTS={'chief-of-staff','sales','marketing','service','operations','legal','finance','product'}
VALID_WRITE={'none','bounded','approval-required'}
SYSTEM_ID=re.compile(r'^[a-z0-9][a-z0-9._-]*$')


def validate(d):
    errors=[]
    if d.get('version') != 1: errors.append('version must equal 1')
    depts=d.get('departments')
    if not isinstance(depts,list) or not depts or any(x not in VALID_DEPTS for x in depts): errors.append('departments invalid')
    elif len(depts) != len(set(depts)): errors.append('departments must be unique')

    authority=d.get('authority',{})
    if authority.get('external_action_default') not in {'deny','approval-required'}: errors.append('external actions must default deny/approval-required')
    if authority.get('financial_commitment_default') not in {'deny','approval-required'}: errors.append('financial commitments must default deny/approval-required')
    if d.get('data',{}).get('private_by_default') is not True: errors.append('data.private_by_default must be true')

    systems=d.get('systems')
    system_ids=[]
    if not isinstance(systems,list):
        errors.append('systems must be an array')
    else:
        for s in systems:
            sid=s.get('id') if isinstance(s,dict) else None
            if not isinstance(sid,str) or not SYSTEM_ID.fullmatch(sid): errors.append(f'invalid system id: {sid!r}')
            else: system_ids.append(sid)
            if not isinstance(s,dict) or s.get('write_authority') not in VALID_WRITE: errors.append(f"system {sid or '?'} has invalid write_authority")
        if len(system_ids) != len(set(system_ids)): errors.append('system ids must be unique')

    context_refs=d.get('data',{}).get('allowed_context_refs',[])
    if not isinstance(context_refs,list):
        errors.append('data.allowed_context_refs must be an array')
    else:
        declared=set(system_ids)
        for ref in context_refs:
            if not isinstance(ref,str):
                errors.append('allowed_context_refs entries must be strings')
            elif ref.startswith('system://'):
                sid=ref[len('system://'):]
                if sid not in declared:
                    errors.append(f'unresolved system context reference: {ref}')
    return errors


def main():
    if len(sys.argv)<2:
        print('usage: validate_company_contract.py <contract.json> [...]', file=sys.stderr)
        return 2
    failed=False
    for path in sys.argv[1:]:
        try: d=json.load(open(path,encoding='utf-8'))
        except Exception as exc:
            print(f'ERROR {path}: {exc}'); failed=True; continue
        errs=validate(d)
        if errs:
            failed=True
            for e in errs: print(f'ERROR {path}: {e}')
        else:
            print(f'PASS {path}')
    return 1 if failed else 0

if __name__=='__main__': raise SystemExit(main())
