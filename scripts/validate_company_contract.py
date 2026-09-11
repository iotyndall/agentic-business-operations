#!/usr/bin/env python3
import json, re, sys

VALID_DEPTS={'chief-of-staff','sales','marketing','service','operations','legal','finance','product'}
VALID_WRITE={'none','bounded','approval-required'}
VALID_PROVIDER_KINDS={'openai','anthropic','xai','openrouter','openai-compatible','custom'}
VALID_MODES={'interactive','batch'}
VALID_FALLBACKS={'rate-limit','timeout','provider-error','capacity'}
CRED_RE=re.compile(r'^(secret|env)://[A-Z][A-Z0-9_]*$')
ENDPOINT_RE=re.compile(r'^(config|env)://[A-Z][A-Z0-9_]*$')
ID_RE=re.compile(r'^[a-z0-9][a-z0-9._-]*$')


def _duplicates(values):
    seen=set(); dup=set()
    for value in values:
        if value in seen: dup.add(value)
        seen.add(value)
    return sorted(dup)


def validate_model_policy(policy, departments):
    errors=[]
    if not isinstance(policy,dict): return ['model_policy must be an object']
    selection=policy.get('selection',{})
    providers=policy.get('providers',[])
    models=policy.get('models',[])
    assignments=policy.get('assignments',[])
    if not isinstance(providers,list) or not providers: errors.append('model_policy.providers must be a non-empty array'); providers=[]
    if not isinstance(models,list) or not models: errors.append('model_policy.models must be a non-empty array'); models=[]
    if not isinstance(assignments,list): errors.append('model_policy.assignments must be an array'); assignments=[]

    provider_ids=[p.get('id') for p in providers if isinstance(p,dict)]
    for dup in _duplicates(provider_ids): errors.append(f'duplicate model provider id: {dup}')
    provider_map={p.get('id'):p for p in providers if isinstance(p,dict) and p.get('id')}
    for p in providers:
        if not isinstance(p,dict): errors.append('model provider must be an object'); continue
        pid=p.get('id','')
        if not ID_RE.fullmatch(pid): errors.append(f'invalid model provider id: {pid or "?"}')
        if p.get('kind') not in VALID_PROVIDER_KINDS: errors.append(f'provider {pid or "?"} has invalid kind')
        if not CRED_RE.fullmatch(str(p.get('credential_ref',''))): errors.append(f'provider {pid or "?"} credential_ref must be secret:// or env:// reference')
        endpoint=p.get('endpoint_ref')
        if endpoint is not None and not ENDPOINT_RE.fullmatch(str(endpoint)): errors.append(f'provider {pid or "?"} endpoint_ref must be config:// or env:// reference')
        if not isinstance(p.get('enabled'),bool): errors.append(f'provider {pid or "?"} enabled must be boolean')

    model_ids=[m.get('id') for m in models if isinstance(m,dict)]
    for dup in _duplicates(model_ids): errors.append(f'duplicate model id: {dup}')
    model_map={m.get('id'):m for m in models if isinstance(m,dict) and m.get('id')}
    for m in models:
        if not isinstance(m,dict): errors.append('model entry must be an object'); continue
        mid=m.get('id',''); provider=m.get('provider')
        if not ID_RE.fullmatch(mid): errors.append(f'invalid model id: {mid or "?"}')
        if provider not in provider_map: errors.append(f'model {mid or "?"} references unknown provider {provider}')
        elif not provider_map[provider].get('enabled',False) and m.get('enabled',False): errors.append(f'model {mid or "?"} is enabled but provider {provider} is disabled')
        if not isinstance(m.get('model'),str) or not m.get('model','').strip(): errors.append(f'model {mid or "?"} missing provider-native model id')
        modes=m.get('execution_modes',[])
        if not isinstance(modes,list) or not modes or any(x not in VALID_MODES for x in modes): errors.append(f'model {mid or "?"} has invalid execution_modes')
        if not isinstance(m.get('capabilities'),list): errors.append(f'model {mid or "?"} capabilities must be an array')
        if not isinstance(m.get('enabled'),bool): errors.append(f'model {mid or "?"} enabled must be boolean')

    default=selection.get('company_default_model') if isinstance(selection,dict) else None
    if default not in model_map: errors.append(f'company_default_model references unknown model {default}')
    elif not model_map[default].get('enabled',False): errors.append('company_default_model must be enabled')
    if not isinstance(selection.get('allow_user_override'),bool): errors.append('selection.allow_user_override must be boolean')
    fallback_on=selection.get('fallback_on',[])
    if not isinstance(fallback_on,list) or any(x not in VALID_FALLBACKS for x in fallback_on): errors.append('selection.fallback_on invalid')
    independence=selection.get('review_independence',{})
    if not isinstance(independence,dict) or not all(isinstance(independence.get(k),bool) for k in ('different_model_required','different_provider_required')):
        errors.append('selection.review_independence booleans required')

    keys=[]
    for a in assignments:
        if not isinstance(a,dict): errors.append('model assignment must be an object'); continue
        scope=a.get('scope'); sid=a.get('scope_id'); key=(scope,sid); keys.append(key)
        if scope not in {'department','agent','task'}: errors.append(f'assignment {sid or "?"} has invalid scope')
        if not isinstance(sid,str) or not sid: errors.append('assignment scope_id required')
        if scope=='department' and sid not in departments: errors.append(f'assignment references undeclared department {sid}')
        mode=a.get('execution_mode')
        if mode not in VALID_MODES: errors.append(f'assignment {sid or "?"} has invalid execution_mode')
        required=set(a.get('required_capabilities',[]) or [])
        refs=[a.get('primary_model')]+list(a.get('fallback_models',[]) or [])
        for ref in refs:
            if ref not in model_map: errors.append(f'assignment {sid or "?"} references unknown model {ref}'); continue
            model=model_map[ref]
            if not model.get('enabled',False): errors.append(f'assignment {sid or "?"} references disabled model {ref}')
            if mode not in model.get('execution_modes',[]): errors.append(f'assignment {sid or "?"} uses {ref} in unsupported mode {mode}')
            missing=required-set(model.get('capabilities',[]))
            if missing: errors.append(f'assignment {sid or "?"} model {ref} lacks capabilities: {sorted(missing)}')
        if not isinstance(a.get('user_selectable'),bool): errors.append(f'assignment {sid or "?"} user_selectable must be boolean')
    for dup in _duplicates(keys): errors.append(f'duplicate model assignment: {dup[0]}:{dup[1]}')
    return errors


def validate(d):
    errors=[]
    if d.get('version') != 1: errors.append('version must equal 1')
    depts=d.get('departments')
    if not isinstance(depts,list) or not depts or any(x not in VALID_DEPTS for x in depts): errors.append('departments invalid'); depts=[]
    authority=d.get('authority',{})
    if authority.get('external_action_default') not in {'deny','approval-required'}: errors.append('external actions must default deny/approval-required')
    if authority.get('financial_commitment_default') not in {'deny','approval-required'}: errors.append('financial commitments must default deny/approval-required')
    if d.get('data',{}).get('private_by_default') is not True: errors.append('data.private_by_default must be true')
    systems=d.get('systems')
    if not isinstance(systems,list): errors.append('systems must be an array'); systems=[]
    ids=[s.get('id') for s in systems if isinstance(s,dict)]
    for dup in _duplicates(ids): errors.append(f'duplicate system id: {dup}')
    for s in systems:
        if not isinstance(s,dict): errors.append('system entry must be an object'); continue
        if s.get('write_authority') not in VALID_WRITE: errors.append(f"system {s.get('id','?')} has invalid write_authority")
    system_ids=set(ids)
    for ref in d.get('data',{}).get('allowed_context_refs',[]) or []:
        if isinstance(ref,str) and ref.startswith('system://') and ref[9:] not in system_ids:
            errors.append(f'allowed_context_ref {ref} does not resolve to a declared system')
    if 'model_policy' in d: errors.extend(validate_model_policy(d['model_policy'],set(depts)))
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
