#!/usr/bin/env python3
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

required_roles = [
    'chief-of-staff.md','sales.md','marketing.md','service.md','operations.md',
    'legal.md','finance.md','product.md','adversarial-reviewer.md',
    'service-supervisor.md','script-knowledge-author.md','frontline-service-worker.md',
    'service-quality-reviewer.md'
]
required_schemas = [
    'intake.schema.json','work-item.schema.json','handoff.schema.json','decision.schema.json',
    'approval.schema.json','evidence.schema.json','outcome.schema.json','review.schema.json',
    'company-contract.schema.json','model-policy.schema.json','contact-center-profile.schema.json',
    'contact-center-role.schema.json','contact-center-binding.schema.json'
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

for rel in sorted(str(q.relative_to(ROOT)) for d in ('schemas','examples','templates') for q in (ROOT/d).rglob('*.json')) + [
    'examples/synthetic-company/company-contract.json',
    'examples/synthetic-company/scenarios.json',
    'examples/synthetic-company/contact-center-profile.json',
    'templates/private-company/business-ops.example.json'
]:
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
allowed_non_email_tokens={'git@github.com'}
skip={'.git'}
for p in ROOT.rglob('*'):
    if not p.is_file() or any(part in skip for part in p.parts): continue
    try: text=p.read_text(encoding='utf-8')
    except Exception: continue
    for kind,pat in secret_patterns.items():
        if pat.search(text): errors.append(f'possible {kind} in {p.relative_to(ROOT)}')
    for addr in email.findall(text):
        normalized=addr.lower()
        if normalized in allowed_non_email_tokens:
            continue
        domain=normalized.rsplit('@',1)[1]
        if domain not in allowed_email_domains:
            errors.append(f'non-synthetic email in {p.relative_to(ROOT)}: {addr}')

# Workflow supply-chain invariants: immutable SHA pins and non-persistent CI credentials.
uses_re=re.compile(r'uses:\s*([^\s#]+)')
workflow_files=list((ROOT/'.github'/'workflows').glob('*.yml'))+list((ROOT/'templates'/'private-company'/'.github'/'workflows').glob('*.yml'))
for wf in workflow_files:
    text=wf.read_text(encoding='utf-8')
    for ref in uses_re.findall(text):
        if not re.search(r'@[0-9a-f]{40}$', ref):
            errors.append(f'{wf.relative_to(ROOT)}: Action not pinned to immutable commit SHA: {ref}')
    if 'persist-credentials: false' not in text:
        errors.append(f'{wf.relative_to(ROOT)}: checkout must set persist-credentials: false')

# Every executable policy script must at least compile.
import py_compile
for s in (ROOT/'scripts').glob('*.py'):
    try: py_compile.compile(str(s), doraise=True)
    except Exception as exc: errors.append(f'script does not compile {s.relative_to(ROOT)}: {exc}')

constitution=(ROOT/'policies'/'company-constitution.md').read_text()
for phrase in ['High autonomy does not imply high authority', 'Execution authority must be explicit']:
    if phrase not in constitution: errors.append(f'constitution invariant missing: {phrase}')

if errors:
    for e in errors: print(f'ERROR: {e}')
    sys.exit(1)
print('PASS: company OS structure, JSON assets, public-safety and workflow supply-chain invariants')
