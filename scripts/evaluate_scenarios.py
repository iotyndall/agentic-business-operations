#!/usr/bin/env python3
import json, sys
from pathlib import Path
from router import route_intake, RoutingError

ROOT=Path(__file__).resolve().parents[1]
scenarios=json.loads((ROOT/'examples/synthetic-company/scenarios.json').read_text())['scenarios']
errors=[]
for scenario in scenarios:
    try: result=route_intake(scenario['intake'])
    except RoutingError as exc:
        errors.append(f"{scenario['id']}: routing error: {exc}"); continue
    expected=scenario['expected']
    for field in ['department','authority_ceiling','escalation_required']:
        if result[field] != expected[field]:
            errors.append(f"{scenario['id']}: {field} expected {expected[field]!r}, got {result[field]!r}")
    if sorted(result['required_handoffs']) != sorted(expected.get('required_handoffs', [])):
        errors.append(f"{scenario['id']}: handoffs expected {expected.get('required_handoffs', [])!r}, got {result['required_handoffs']!r}")
if errors:
    print('\n'.join('ERROR: '+e for e in errors)); sys.exit(1)
print(f'PASS: {len(scenarios)} synthetic company routing/authority scenarios')
