#!/usr/bin/env python3
"""Semantic validation for a private marketing profile against the company contract.

Enforces the separation-of-duties and authority invariants declared in
roles/marketing.md and policies/marketing-guardrails.md so that a private
profile cannot quietly widen what a marketing role may do.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def connector_index():
    """connector://<id>/<tool> -> declared tool, from every published connector in connectors/."""
    idx = {}
    for cf in sorted((ROOT / 'connectors').glob('*/connector.json')):
        try: c = json.loads(cf.read_text(encoding='utf-8'))
        except Exception: continue
        for t in c.get('tools', []): idx[f"connector://{c['id']}/{t['tool']}"] = t
    return idx

ROLE_KEYS = ('brand_manager', 'direct_email', 'paid_media', 'social_media', 'agent_relations', 'content_reviewer')
CHANNEL_ROLES = {'direct_email', 'paid_media', 'social_media', 'agent_relations'}

# Capabilities that perform an external or financial action. Only the named role may hold each.
EXCLUSIVE = {
    'email.send_bounded': 'direct_email',
    'email.schedule_bounded': 'direct_email',
    'spend.execute_bounded': 'paid_media',
    'bid.adjust_bounded': 'paid_media',
    'post.publish_bounded': 'social_media',
    'reply.publish_bounded': 'social_media',
    'content.clear_bounded': 'content_reviewer',
    'agent_card.publish_bounded': 'agent_relations',
    'agent.negotiate_bounded': 'agent_relations',
    'agent.message_bounded': 'agent_relations',
}
# No marketing role may ever hold these; they belong to Finance or a release mechanism.
FORBIDDEN_EVERYWHERE = {'budget.create', 'content.publish_approved', 'consent.record', 'suppression.record',
                        'agent.inject_instructions', 'agent.execute_commitment', 'commitment.sign'}
# Authoring capabilities the reviewer must never hold (cannot review own work).
AUTHORING = {'post.draft', 'reply.draft', 'email.draft', 'email.template_draft', 'creative.draft',
             'brand.guideline_draft', 'claims.register_propose', 'campaign.plan_draft',
             'agent_surface.draft', 'agent_card.draft', 'structured_facts.propose'}
# Prerequisite capabilities: if a role may do X it must also be able to observe Y.
PREREQS = {
    'email.send_bounded': {'consent.read', 'suppression.read'},
    'email.schedule_bounded': {'consent.read', 'suppression.read'},
    'post.publish_bounded': {'ugc.consent_read', 'platform_policy.read'},
    'spend.execute_bounded': {'pacing.read', 'platform_policy.read', 'campaign.pause'},
    'agent_card.publish_bounded': {'claims.read_register', 'protocol_policy.read'},
    'agent.negotiate_bounded': {'protocol_policy.read', 'claims.read_register', 'interaction.escalate'},
    'agent.message_bounded': {'consent.read', 'suppression.read', 'protocol_policy.read'},
}
# Capabilities that must be approval-required at the role level unless the private contract pre-authorises them.
APPROVAL_BY_DEFAULT = {'email.send_bounded', 'email.schedule_bounded', 'reply.publish_bounded', 'budget.request', 'campaign.brief_publish_bounded',
                       'agent_card.publish_bounded', 'agent.negotiate_bounded'}
KIND_FOR_ROLE = {'direct_email': {'email', 'messaging'}, 'paid_media': {'paid-media'}, 'social_media': {'social-owned'}, 'agent_relations': {'agent-protocol'}}


def fail(msg, errors): errors.append(msg)


def load(path):
    with open(path, encoding='utf-8') as f: return json.load(f)


def validate(company, profile):
    errors = []
    system_ids = {s.get('id') for s in company.get('systems', []) if isinstance(s, dict)}
    roles = profile.get('roles', {})
    holders = {}

    for name in ROLE_KEYS:
        role = roles.get(name, {})
        allowed = set(role.get('allowed_capabilities', []) or [])
        approval = set(role.get('approval_required_capabilities', []) or [])
        prohibited = set(role.get('prohibited_capabilities', []) or [])
        if allowed & prohibited:
            fail(f'{name} has capabilities both allowed and prohibited: {sorted(allowed & prohibited)}', errors)
        if approval - allowed:
            fail(f'{name} approval-required capabilities must also be allowed: {sorted(approval - allowed)}', errors)
        if allowed & FORBIDDEN_EVERYWHERE:
            fail(f'{name} may not hold {sorted(allowed & FORBIDDEN_EVERYWHERE)}', errors)
        for cap in allowed:
            holders.setdefault(cap, set()).add(name)
        for cap, prereq in PREREQS.items():
            if cap in allowed and prereq - allowed:
                fail(f'{name} allows {cap} but lacks prerequisite {sorted(prereq - allowed)}', errors)
        for cap in APPROVAL_BY_DEFAULT & allowed:
            if cap not in approval:
                fail(f'{name}: {cap} must be approval-required (private contract may pre-authorise specific flows via constraints_ref, not by removing approval)', errors)
        if name == 'content_reviewer' and allowed & AUTHORING:
            fail(f'content_reviewer may not author what it reviews: {sorted(allowed & AUTHORING)}', errors)
        if name == 'brand_manager' and allowed & set(EXCLUSIVE):
            fail(f'brand_manager may not execute channel actions: {sorted(allowed & set(EXCLUSIVE))}', errors)
        if name in CHANNEL_ROLES and role.get('enabled') and 'content.request_review' not in allowed and name != 'paid_media':
            fail(f'{name} must be able to request review when enabled', errors)
        if name == 'paid_media' and role.get('enabled') and 'creative.request_review' not in allowed:
            fail('paid_media must be able to request creative review when enabled', errors)
        if name in {'social_media', 'agent_relations'} and role.get('enabled') and 'interaction.escalate' not in allowed:
            fail(f'{name} must allow interaction.escalate when enabled', errors)

    for cap, owner in EXCLUSIVE.items():
        others = holders.get(cap, set()) - {owner}
        if others:
            fail(f'{cap} may only be held by {owner}; also held by {sorted(others)}', errors)

    channel_ids = {}
    for ch in profile.get('channels', []) or []:
        cid = ch.get('id')
        if cid in channel_ids: fail(f'duplicate channel id {cid}', errors)
        channel_ids[cid] = ch
        sref = ch.get('system_ref', '')
        if sref.startswith('system://') and sref[9:] not in system_ids:
            fail(f'channel {cid} references undeclared company system {sref}', errors)
        owner = ch.get('owner_role')
        if ch.get('kind') not in KIND_FOR_ROLE.get(owner, set()):
            fail(f'channel {cid} kind {ch.get("kind")} cannot be owned by {owner}', errors)
        if not roles.get(owner, {}).get('enabled'):
            fail(f'channel {cid} owned by disabled role {owner}', errors)

    paid_channels = {c for c, ch in channel_ids.items() if ch.get('kind') == 'paid-media'}
    enveloped = set()
    for env in profile.get('budget_envelopes', []) or []:
        eid = env.get('id')
        if env.get('amount_minor', 0) <= 0: fail(f'envelope {eid} amount must be positive', errors)
        dc = env.get('daily_cap_minor'); sc = env.get('single_action_cap_minor')
        if dc is not None and dc > env.get('amount_minor', 0): fail(f'envelope {eid} daily cap exceeds amount', errors)
        if sc is not None and dc is not None and sc > dc: fail(f'envelope {eid} single-action cap exceeds daily cap', errors)
        for c in env.get('channels', []):
            if c not in channel_ids: fail(f'envelope {eid} references undeclared channel {c}', errors)
            elif c not in paid_channels: fail(f'envelope {eid} references non-paid channel {c}', errors)
            enveloped.add(c)
    if paid_channels - enveloped and 'spend.execute_bounded' in holders:
        fail(f'paid channels without a budget envelope cannot carry spend authority: {sorted(paid_channels - enveloped)}', errors)

    agent_channels = {c for c, ch in channel_ids.items() if ch.get('kind') == 'agent-protocol'}
    offer_ids = set()
    for env in profile.get('offer_envelopes', []) or []:
        eid = env.get('id'); offer_ids.add(eid)
        fl = env.get('price_floor_minor'); ce = env.get('price_ceiling_minor')
        if fl is not None and ce is not None and fl > ce: fail(f'offer envelope {eid} floor exceeds ceiling', errors)
        for c in env.get('channels', []):
            if c not in channel_ids: fail(f'offer envelope {eid} references undeclared channel {c}', errors)
            elif c not in agent_channels: fail(f'offer envelope {eid} references non-agent channel {c}', errors)

    cidx = connector_index()
    declared = set().union(*(set(r.get('allowed_capabilities', []) or []) for r in roles.values() if isinstance(r, dict))) if roles else set()
    seen = set()
    bound = set()
    envelope_ids = {e.get('id') for e in profile.get('budget_envelopes', []) or []}
    for b in profile.get('capability_bindings', []) or []:
        cap = b.get('capability'); bound.add(cap)
        key = (cap, b.get('system_ref'), b.get('connector_ref'))
        if key in seen: fail(f'duplicate capability binding: {key}', errors)
        seen.add(key)
        if cap not in declared: fail(f'capability binding {cap} is not allowed by any enabled role', errors)
        sref = b.get('system_ref', '')
        if sref.startswith('system://') and sref[9:] not in system_ids:
            fail(f'capability {cap} references undeclared company system {sref}', errors)
        if b.get('authority') in {'execute-bounded', 'approval-required'} and b.get('requires_verification') is not True:
            fail(f'material capability {cap} must require verification', errors)
        if cap == 'spend.execute_bounded':
            cref = b.get('constraints_ref', '')
            if not cref.startswith('envelope://') or cref[11:] not in envelope_ids:
                fail('spend.execute_bounded binding must be constrained by a declared envelope://<id>', errors)
        if cap == 'agent.negotiate_bounded':
            cref = b.get('constraints_ref', '')
            if not cref.startswith('offer://') or cref[8:] not in offer_ids:
                fail('agent.negotiate_bounded binding must be constrained by a declared offer://<id> envelope', errors)
        if cap in {'post.publish_bounded', 'email.send_bounded', 'agent_card.publish_bounded'} and not b.get('constraints_ref'):
            fail(f'{cap} binding must declare a constraints_ref', errors)
        cref = b.get('connector_ref', '')
        published_ids = {k.split('/')[2] for k in cidx}
        if cref.startswith('connector://') and cref.split('/')[2] in published_ids:
            # A binding to a *published* connector's tool must exist and must carry the capability the connector declares for it.
            # Refs to unpublished (private) connectors are the adopter's own and are not checked here.
            t = cidx.get(cref)
            if t is None: fail(f'{cap} binds {cref}, which no published connector declares', errors)
            elif t['capability'] != cap: fail(f'{cap} binds {cref}, but the connector declares that tool as {t["capability"]}', errors)
            elif t['authority'] == 'prohibited': fail(f'{cap} binds {cref}, which the connector prohibits', errors)
    for cap in set(EXCLUSIVE) & declared:
        if cap not in bound:
            fail(f'{cap} is allowed but has no capability binding; unbound external actions fail closed', errors)

    return errors


def main():
    if len(sys.argv) != 3:
        print('usage: validate_marketing_profile.py <company-contract.json> <marketing-profile.json>', file=sys.stderr)
        return 2
    try:
        company = load(sys.argv[1]); profile = load(sys.argv[2])
    except Exception as exc:
        print(f'ERROR: {exc}'); return 2
    errors = validate(company, profile)
    if errors:
        for e in errors: print(f'ERROR: {e}')
        return 1
    print('PASS: marketing profile separation of duties, envelopes, channels and company-system bindings')
    return 0


if __name__ == '__main__': raise SystemExit(main())
