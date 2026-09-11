#!/usr/bin/env python3
import argparse, json, sys
from validate_company_contract import validate_model_policy


def _models(policy):
    return {m['id']: m for m in policy['models']}


def _assignment(policy, department=None, agent=None, task=None):
    rows=policy.get('assignments',[])
    lookup={(r['scope'],r['scope_id']):r for r in rows}
    for key in (("task",task),("agent",agent),("department",department)):
        if key[1] and key in lookup: return lookup[key]
    return None


def resolve(policy, department=None, agent=None, task=None, user_model=None):
    models=_models(policy)
    row=_assignment(policy, department, agent, task)
    model_id=row['primary_model'] if row else policy['selection']['company_default_model']
    mode=row.get('execution_mode','interactive') if row else 'interactive'
    required=set(row.get('required_capabilities',[])) if row else set()
    selectable=policy['selection'].get('allow_user_override',False) and (row is None or row.get('user_selectable',False))
    if user_model:
        if not selectable: raise ValueError('user model override is not allowed for this assignment')
        model_id=user_model
    if model_id not in models: raise ValueError(f'unknown model: {model_id}')
    model=models[model_id]
    if not model.get('enabled',False): raise ValueError(f'model is disabled: {model_id}')
    if mode not in model.get('execution_modes',[]): raise ValueError(f'model {model_id} does not support execution mode {mode}')
    missing=required-set(model.get('capabilities',[]))
    if missing: raise ValueError(f'model {model_id} lacks required capabilities: {sorted(missing)}')
    fallbacks=[] if user_model else list(row.get('fallback_models',[]) if row else [])
    return {
        'model_ref': model_id,
        'provider_ref': model['provider'],
        'provider_model': model['model'],
        'execution_mode': mode,
        'fallback_models': fallbacks,
        'selected_by': 'user' if user_model else (row['scope'] if row else 'company-default'),
        'assignment_id': row['scope_id'] if row else None
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('contract')
    ap.add_argument('--department')
    ap.add_argument('--agent')
    ap.add_argument('--task')
    ap.add_argument('--user-model')
    args=ap.parse_args()
    data=json.load(open(args.contract,encoding='utf-8'))
    policy=data.get('model_policy')
    if not policy:
        print('ERROR: contract has no model_policy',file=sys.stderr); return 2
    errors=validate_model_policy(policy,set(data.get('departments',[])))
    if errors:
        for e in errors: print(f'ERROR: {e}',file=sys.stderr)
        return 1
    try:
        result=resolve(policy,args.department,args.agent,args.task,args.user_model)
    except ValueError as exc:
        print(f'ERROR: {exc}',file=sys.stderr); return 1
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
