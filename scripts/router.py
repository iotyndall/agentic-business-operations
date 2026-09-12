#!/usr/bin/env python3
import json, sys

OUTCOME_TO_DEPARTMENT = {
    'commercial-opportunity': 'sales',
    'demand-generation': 'marketing',
    'customer-resolution': 'service',
    'internal-operations': 'operations',
    'legal-obligation': 'legal',
    'financial-control': 'finance',
    'strategic-direction': 'strategy',
    'product-capability': 'product',
    'cross-functional': 'chief-of-staff',
    'unknown': 'chief-of-staff',
}
VALID_RISK = {'low','moderate','high','critical'}
VALID_DEPS = {'sales','marketing','service','operations','legal','finance','product','strategy'}

class RoutingError(ValueError):
    pass

def route_intake(data):
    if not isinstance(data, dict): raise RoutingError('intake must be an object')
    for field in ['version','id','objective','dominant_outcome','risk','requires_external_action','requires_financial_commitment']:
        if field not in data: raise RoutingError(f'missing required field: {field}')
    if data['version'] != 1: raise RoutingError('unsupported intake version')
    outcome=data['dominant_outcome']; risk=data['risk']
    if outcome not in OUTCOME_TO_DEPARTMENT: raise RoutingError('unknown dominant_outcome')
    if risk not in VALID_RISK: raise RoutingError('invalid risk')
    deps=data.get('material_dependencies', [])
    if not isinstance(deps, list) or any(d not in VALID_DEPS for d in deps): raise RoutingError('invalid material_dependencies')
    department=OUTCOME_TO_DEPARTMENT[outcome]
    handoffs=[d for d in deps if d != department]
    reasons=[]
    if outcome == 'unknown': reasons.append('ownership-ambiguous')
    if risk == 'critical': reasons.append('critical-risk')
    if data['requires_external_action']: reasons.append('external-action')
    if data['requires_financial_commitment']: reasons.append('financial-commitment')
    return {
        'work_item_id': data['id'],
        'department': department,
        'authority_ceiling': 'PROPOSE',
        'required_handoffs': sorted(set(handoffs)),
        'escalation_required': bool(reasons),
        'escalation_reasons': reasons,
    }

def main():
    if len(sys.argv) != 2:
        print('usage: router.py <intake.json>', file=sys.stderr); return 2
    try:
        data=json.load(open(sys.argv[1], encoding='utf-8'))
        print(json.dumps(route_intake(data), indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, RoutingError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr); return 1

if __name__ == '__main__': raise SystemExit(main())
