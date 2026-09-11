#!/usr/bin/env python3
import copy, json
from pathlib import Path
from resolve_model import resolve
from validate_company_contract import validate

ROOT=Path(__file__).resolve().parents[1]
contract=json.loads((ROOT/'templates/private-company/business-ops.example.json').read_text())
assert validate(contract)==[], validate(contract)
policy=contract['model_policy']

r=resolve(policy,department='finance')
assert r['model_ref']=='openai-primary' and r['selected_by']=='company-default'

r=resolve(policy,department='marketing')
assert r['model_ref']=='openrouter-economy' and r['execution_mode']=='batch' and r['selected_by']=='department'

r=resolve(policy,department='marketing',agent='adversarial-reviewer')
assert r['model_ref']=='anthropic-review' and r['selected_by']=='agent'

r=resolve(policy,department='chief-of-staff',agent='router',task='chief-of-staff.route')
assert r['model_ref']=='openai-primary' and r['selected_by']=='task'

r=resolve(policy,department='marketing',user_model='openai-primary')
assert r['model_ref']=='openai-primary' and r['selected_by']=='user'

locked=copy.deepcopy(policy)
locked['assignments'][0]['user_selectable']=False
try:
    resolve(locked,department='marketing',user_model='openai-primary')
    raise AssertionError('locked assignment accepted user override')
except ValueError:
    pass

bad=copy.deepcopy(contract)
bad['model_policy']['assignments'][0]['primary_model']='missing-model'
assert any('unknown model' in e for e in validate(bad))

bad=copy.deepcopy(contract)
bad['model_policy']['assignments'][0]['execution_mode']='interactive'
bad['model_policy']['assignments'][0]['required_capabilities']=['vision']
assert any('lacks capabilities' in e for e in validate(bad))

bad=copy.deepcopy(contract)
bad['model_policy']['providers'][0]['credential_ref']='sk-not-a-reference'
assert any('credential_ref' in e for e in validate(bad))

print('PASS model selection precedence, overrides, references, modes and capability guardrails')
