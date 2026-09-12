#!/usr/bin/env python3
"""Small dependency-free validator for the JSON Schema subset used by Company OS.

Supported keywords: $ref (relative files), type, const, enum, required,
properties, additionalProperties=false, items, minItems, uniqueItems,
minLength and pattern.
"""
import json
import re
import sys
from pathlib import Path


def _type_ok(expected, value):
    mapping = {
        'object': lambda v: isinstance(v, dict),
        'array': lambda v: isinstance(v, list),
        'string': lambda v: isinstance(v, str),
        'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
        'boolean': lambda v: isinstance(v, bool),
        'null': lambda v: v is None,
    }
    if isinstance(expected, list):
        return any(_type_ok(x, value) for x in expected)
    check = mapping.get(expected)
    if check is None:
        raise ValueError(f'unsupported schema type: {expected}')
    return check(value)


def _http_uri_ok(value):
    from urllib.parse import urlsplit
    try: u = urlsplit(value)
    except Exception: return False
    if u.scheme not in ('http', 'https') or not u.netloc or u.username or u.password: return False
    host = u.hostname or ''
    if re.search(r'%(?![0-9A-Fa-f]{2})', value): return False
    if host.startswith('[') or ':' in host:
        import ipaddress
        try: ipaddress.IPv6Address(host.strip('[]')); return True
        except Exception: return False
    labels = host.split('.')
    return all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', l, re.I) for l in labels) and bool(labels[0])


def validate_instance(schema, value, schema_file, path='$'):
    errors = []
    if '$ref' in schema:
        ref = schema['$ref']
        if not isinstance(ref, str) or ref.startswith(('http://', 'https://', '#')):
            return [f'{path}: only relative file $ref values are supported']
        target = (Path(schema_file).parent / ref).resolve()
        root = Path(schema_file).resolve().parent
        if target.parent != root:
            return [f'{path}: $ref escapes schema directory: {ref}']
        try:
            target_schema = json.loads(target.read_text(encoding='utf-8'))
        except Exception as exc:
            return [f'{path}: unable to load $ref {ref}: {exc}']
        return validate_instance(target_schema, value, target, path)

    expected = schema.get('type')
    if expected is not None and not _type_ok(expected, value):
        return [f'{path}: expected type {expected}, got {type(value).__name__}']
    if 'const' in schema and value != schema['const']:
        errors.append(f'{path}: value must equal {schema["const"]!r}')
    if 'enum' in schema and value not in schema['enum']:
        errors.append(f'{path}: value {value!r} is not in enum')

    if isinstance(value, dict):
        required = schema.get('required', [])
        for key in required:
            if key not in value:
                errors.append(f'{path}: missing required property {key}')
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False:
            for key in value:
                if key not in props:
                    errors.append(f'{path}: additional property not allowed: {key}')
        for key, child in props.items():
            if key in value:
                errors.extend(validate_instance(child, value[key], schema_file, f'{path}.{key}'))

    if isinstance(value, list):
        if 'minItems' in schema and len(value) < schema['minItems']:
            errors.append(f'{path}: requires at least {schema["minItems"]} item(s)')
        if schema.get('uniqueItems'):
            seen = set()
            for item in value:
                encoded = json.dumps(item, sort_keys=True, separators=(',', ':'))
                if encoded in seen:
                    errors.append(f'{path}: duplicate array item')
                    break
                seen.add(encoded)
        child = schema.get('items')
        if child is not None:
            for i, item in enumerate(value):
                errors.extend(validate_instance(child, item, schema_file, f'{path}[{i}]'))

    if isinstance(value, str):
        if 'minLength' in schema and len(value) < schema['minLength']:
            errors.append(f'{path}: string shorter than minLength {schema["minLength"]}')
        if 'pattern' in schema and re.search(schema['pattern'], value) is None:
            errors.append(f'{path}: string does not match required pattern')
        if schema.get('format') == 'uri' and not _http_uri_ok(value):
            errors.append(f'{path}: not a valid http(s) URI')
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 'minimum' in schema and value < schema['minimum']:
            errors.append(f'{path}: below minimum {schema["minimum"]}')
        if 'maximum' in schema and value > schema['maximum']:
            errors.append(f'{path}: above maximum {schema["maximum"]}')
    if 'oneOf' in schema:
        matches = sum(1 for alt in schema['oneOf'] if not validate_instance(alt, value, schema_file, path))
        if matches != 1:
            errors.append(f'{path}: must match exactly one alternative, matched {matches}')
    return errors


def validate_files(schema_path, instance_path):
    schema_path = Path(schema_path).resolve()
    try:
        schema = json.loads(schema_path.read_text(encoding='utf-8'))
        instance = json.loads(Path(instance_path).read_text(encoding='utf-8'))
    except Exception as exc:
        return [f'unable to parse schema/instance: {exc}']
    return validate_instance(schema, instance, schema_path)


def main():
    if len(sys.argv) != 3:
        print('usage: validate_json_schema.py <schema.json> <instance.json>', file=sys.stderr)
        return 2
    errors = validate_files(sys.argv[1], sys.argv[2])
    if errors:
        for error in errors:
            print('ERROR:', error)
        return 1
    print(f'PASS {sys.argv[2]} conforms to {sys.argv[1]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
