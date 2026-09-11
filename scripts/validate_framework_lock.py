#!/usr/bin/env python3
import json, re, subprocess, sys
from pathlib import Path

CANONICAL_REPOSITORY='iotyndall/agentic-business-operations'
SHA40=re.compile(r'^[0-9a-f]{40}$')


def validate(lock, framework_dir, actual_head=None, origin_url=None):
    errors=[]
    if lock.get('repository') != CANONICAL_REPOSITORY:
        errors.append(f"repository must equal {CANONICAL_REPOSITORY}")
    commit=lock.get('commit')
    if not isinstance(commit,str) or not SHA40.fullmatch(commit):
        errors.append('commit must be an immutable 40-character lowercase SHA')
    if actual_head is not None and commit != actual_head:
        errors.append(f'framework checkout HEAD {actual_head} does not match lock commit {commit}')

    schema=lock.get('contract_schema')
    if not isinstance(schema,str) or not schema or schema.startswith('/') or '..' in Path(schema).parts:
        errors.append('contract_schema must be a safe relative path')
    else:
        root=Path(framework_dir).resolve()
        candidate=(root/schema).resolve()
        if root not in candidate.parents:
            errors.append('contract_schema escapes framework checkout')
        elif not candidate.is_file():
            errors.append(f'contract_schema does not exist in framework checkout: {schema}')
        else:
            try: json.loads(candidate.read_text(encoding='utf-8'))
            except Exception as exc: errors.append(f'contract_schema is not valid JSON: {exc}')

    if origin_url is not None:
        normalized=origin_url.rstrip('/').removesuffix('.git')
        if not (normalized.endswith('/'+CANONICAL_REPOSITORY) or normalized.endswith(':'+CANONICAL_REPOSITORY)):
            errors.append(f'framework checkout origin does not match {CANONICAL_REPOSITORY}')
    return errors


def git_value(framework_dir, *args):
    return subprocess.check_output(['git','-C',str(framework_dir),*args], text=True).strip()


def main():
    if len(sys.argv) != 3:
        print('usage: validate_framework_lock.py <lock.json> <framework-checkout-dir>', file=sys.stderr)
        return 2
    lock_path=Path(sys.argv[1]); framework_dir=Path(sys.argv[2])
    try:
        lock=json.loads(lock_path.read_text(encoding='utf-8'))
        head=git_value(framework_dir,'rev-parse','HEAD')
        origin=git_value(framework_dir,'remote','get-url','origin')
    except Exception as exc:
        print(f'ERROR: unable to read lock/framework checkout: {exc}')
        return 1
    errors=validate(lock,framework_dir,head,origin)
    if errors:
        for error in errors: print('ERROR:',error)
        return 1
    print(f'PASS framework lock binds {CANONICAL_REPOSITORY}@{head} and {lock["contract_schema"]}')
    return 0

if __name__=='__main__': raise SystemExit(main())
