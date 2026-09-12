#!/usr/bin/env python3
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required_roles = [
    'chief-of-staff.md','sales.md','marketing.md','service.md','operations.md',
    'legal.md','finance.md','product.md','adversarial-reviewer.md'
]
required_schemas = [
    'intake.schema.json','work-item.schema.json','handoff.schema.json','decision.schema.json',
    'approval.schema.json','evidence.schema.json','outcome.schema.json','review.schema.json',
    'company-contract.schema.json','model-policy.schema.json'
]

errors=[]
for name in required_roles:
    if not (ROOT/'roles'/name).is_file(): errors.append(f'missing role: {name}')
for name in required_schemas:
    p=ROOT/'schemas'/name
    if not p.is_file(): errors.append(f'missing schema: {name}')
    else:
        try: json.loads(p.read_text())
        except Exception as exc: errors.append(f'invalid JSON {p}: {exc}')

for rel in ['examples/synthetic-company/company-contract.json','examples/synthetic-company/scenarios.json','templates/private-company/business-ops.example.json']:
    try: json.loads((ROOT/rel).read_text())
    except Exception as exc: errors.append(f'invalid JSON {rel}: {exc}')

# High-confidence public-safety checks. These are deliberately generic; human review is still required.
secret_patterns = {
    'private-key': re.compile(r'-----BEGIN (?:(?:RSA|EC|OPENSSH) )?PRIVATE KEY-----'),
    'github-pat': re.compile(r'github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,}'),
    'openai-key': re.compile(r'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}'),
    'anthropic-key': re.compile(r'sk-ant-[A-Za-z0-9_-]{20,}'),
    'aws-key': re.compile(r'AKIA[0-9A-Z]{16}'),
}
email = re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I)
allowed_email_domains={'example.com','example.org','example.net','example.invalid'}
skip={'.git'}
for p in ROOT.rglob('*'):
    if not p.is_file() or any(part in skip for part in p.parts): continue
    try: text=p.read_text(encoding='utf-8')
    except Exception: continue
    for kind,pat in secret_patterns.items():
        if pat.search(text): errors.append(f'possible {kind} in {p.relative_to(ROOT)}')
    for addr in email.findall(text):
        domain=addr.rsplit('@',1)[1].lower()
        if domain not in allowed_email_domains:
            errors.append(f'non-synthetic email in {p.relative_to(ROOT)}: {addr}')

constitution=(ROOT/'policies'/'company-constitution.md').read_text()
for phrase in ['High autonomy does not imply high authority', 'Execution authority must be explicit']:
    if phrase not in constitution: errors.append(f'constitution invariant missing: {phrase}')

if errors:
    for e in errors: print(f'ERROR: {e}')
    sys.exit(1)
print('PASS: company OS structure, JSON assets and public-safety invariants')
