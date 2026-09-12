#!/usr/bin/env python3
import json, sys

ROLE_KEYS=('frontline','supervisor','script_author','quality_reviewer')


def fail(msg, errors): errors.append(msg)


def load(path):
    with open(path, encoding='utf-8') as f: return json.load(f)


def validate(company, profile):
    errors=[]
    system_ids={s.get('id') for s in company.get('systems',[]) if isinstance(s,dict)}
    roles=profile.get('roles',{})

    for role_name in ROLE_KEYS:
        role=roles.get(role_name,{})
        allowed=set(role.get('allowed_capabilities',[]) or [])
        approval=set(role.get('approval_required_capabilities',[]) or [])
        prohibited=set(role.get('prohibited_capabilities',[]) or [])
        overlap=allowed & prohibited
        if overlap: fail(f'{role_name} has capabilities both allowed and prohibited: {sorted(overlap)}', errors)
        missing=approval-allowed
        if missing: fail(f'{role_name} approval-required capabilities must also be allowed: {sorted(missing)}', errors)
        if role.get('enabled') and role_name in {'frontline','supervisor'} and 'interaction.escalate' not in allowed:
            fail(f'{role_name} must allow interaction.escalate when enabled', errors)
        if 'content.publish_approved' in allowed:
            fail(f'{role_name} may not directly publish approved content; use a separate release mechanism', errors)

    declared=set()
    for role in roles.values():
        if isinstance(role,dict): declared.update(role.get('allowed_capabilities',[]) or [])

    seen=set()
    for binding in profile.get('capability_bindings',[]) or []:
        cap=binding.get('capability')
        key=(cap,binding.get('system_ref'),binding.get('connector_ref'))
        if key in seen: fail(f'duplicate capability binding: {key}', errors)
        seen.add(key)
        if cap not in declared: fail(f'capability binding {cap} is not allowed by any enabled role', errors)
        system_ref=binding.get('system_ref','')
        if system_ref.startswith('system://') and system_ref[9:] not in system_ids:
            fail(f'capability {cap} references undeclared company system {system_ref}', errors)
        if binding.get('authority') in {'execute-bounded','approval-required'} and binding.get('requires_verification') is not True:
            fail(f'material capability {cap} must require verification', errors)

    return errors


def main():
    if len(sys.argv)!=3:
        print('usage: validate_contact_center_profile.py <company-contract.json> <contact-center-profile.json>', file=sys.stderr)
        return 2
    try:
        company=load(sys.argv[1]); profile=load(sys.argv[2])
    except Exception as exc:
        print(f'ERROR: {exc}')
        return 2
    errors=validate(company,profile)
    if errors:
        for e in errors: print(f'ERROR: {e}')
        return 1
    print('PASS: contact center profile semantics and company-system bindings')
    return 0

if __name__=='__main__': raise SystemExit(main())
