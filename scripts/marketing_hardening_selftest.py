#!/usr/bin/env python3
"""Prove the marketing profile validator fails closed on separation-of-duties violations."""
import copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_marketing_profile import validate

ROOT = Path(__file__).resolve().parents[1]
company = json.loads((ROOT/'examples/synthetic-company/company-contract.json').read_text())
good = json.loads((ROOT/'examples/synthetic-company/marketing-profile.json').read_text())

def mutated(fn):
    p = copy.deepcopy(good); fn(p); return validate(company, p)

def add(role, cap): return lambda p: p['roles'][role]['allowed_capabilities'].append(cap)
def drop_approval(role, cap): return lambda p: p['roles'][role]['approval_required_capabilities'].remove(cap)
def drop(role, cap): return lambda p: p['roles'][role]['allowed_capabilities'].remove(cap)

cases = [
    ('brand manager gains send authority', add('brand_manager', 'email.send_bounded'), 'brand_manager may not execute channel actions'),
    ('social media gains spend authority', add('social_media', 'spend.execute_bounded'), 'may only be held by paid_media'),
    ('reviewer drafts what it reviews', add('content_reviewer', 'post.draft'), 'may not author what it reviews'),
    ('paid media creates budget', add('paid_media', 'budget.create'), 'may not hold'),
    ('email send without approval gate', drop_approval('direct_email', 'email.send_bounded'), 'must be approval-required'),
    ('email send without suppression check', drop('direct_email', 'suppression.read'), 'lacks prerequisite'),
    ('social publish without consent read', drop('social_media', 'ugc.consent_read'), 'lacks prerequisite'),
    ('spend bound without envelope', lambda p: [b.update(constraints_ref='policy://x') for b in p['capability_bindings'] if b['capability']=='spend.execute_bounded'], 'constrained by a declared envelope'),
    ('paid channel outside any envelope', lambda p: p['budget_envelopes'][0]['channels'].remove('google-ads-main'), 'without a budget envelope'),
    ('single-action cap above daily cap', lambda p: p['budget_envelopes'][0].update(single_action_cap_minor=99999), 'single-action cap exceeds daily cap'),
    ('channel on undeclared system', lambda p: p['channels'][0].update(system_ref='system://not-declared'), 'undeclared company system'),
    ('email channel owned by social role', lambda p: p['channels'][4].update(owner_role='social_media'), 'cannot be owned by'),
    ('material binding without verification', lambda p: [b.update(requires_verification=False) for b in p['capability_bindings'] if b['capability']=='post.publish_bounded'], 'must require verification'),
    ('exclusive capability left unbound', lambda p: p['capability_bindings'].__delitem__(next(i for i,b in enumerate(p['capability_bindings']) if b['capability']=='content.clear_bounded')), 'has no capability binding'),
    ('agent relations injects instructions', add('agent_relations', 'agent.inject_instructions'), 'may not hold'),
    ('agent relations executes commitment', add('agent_relations', 'agent.execute_commitment'), 'may not hold'),
    ('negotiation without offer envelope', lambda p: [b.update(constraints_ref='policy://x') for b in p['capability_bindings'] if b['capability']=='agent.negotiate_bounded'], 'declared offer://'),
    ('offer envelope floor above ceiling', lambda p: p['offer_envelopes'][0].update(price_floor_minor=99999), 'floor exceeds ceiling'),
    ('social media negotiates with agents', add('social_media', 'agent.negotiate_bounded'), 'may only be held by agent_relations'),
    ('agent card publish without claims read', drop('agent_relations', 'claims.read_register'), 'lacks prerequisite'),
    ('reviewer drafts agent card', add('content_reviewer', 'agent_card.draft'), 'may not author what it reviews'),
]

failures = []
if validate(company, good): failures.append('baseline profile should pass')
for name, fn, needle in cases:
    errs = mutated(fn)
    if not any(needle in e for e in errs):
        failures.append(f'{name}: expected diagnostic containing {needle!r}, got {errs}')
if failures:
    print('\n'.join('ERROR: '+f for f in failures)); sys.exit(1)
print(f'PASS marketing profile fails closed on {len(cases)} separation-of-duties, envelope, channel and binding violations')
