"""Versioned, per-test contract identity; shared by producers and validators."""
import copy
import hashlib
import json
from pathlib import PurePosixPath
import re

BINDING_VERSION = 1
VOLATILE_TEST_FIELDS = {'status', 'review_disposition'}
VOLATILE_INVENTORY_FIELDS = {'tests', 'acceptance_note'}
BINDING_FIELDS = {'version', 'inventory_version', 'inventory_path', 'inventory_sha256', 'contract_sha256'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def inventory_version(inventory):
    version = inventory.get('version')
    if type(version) is not int or version < 1:
        raise ValueError('inventory version must be a positive integer')
    return version


def safe_path(name):
    if not isinstance(name, str) or not name or '\\' in name:
        raise ValueError('invalid evidence path')
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or p.as_posix() != name:
        raise ValueError('escaping or noncanonical evidence path: ' + name)
    return name


def contract_hash(inventory, ident):
    inventory_version(inventory)
    tests = {}
    for test in inventory['tests']:
        key = test['id']
        if not isinstance(key, str) or key in tests:
            raise ValueError('invalid or duplicate contract ID')
        tests[key] = test
    closure, visiting = {}, set()

    def visit(key):
        if key in visiting:
            raise ValueError('cyclic contract prerequisites: ' + key)
        if key in closure:
            return
        if key not in tests:
            raise ValueError('unknown contract or prerequisite: ' + key)
        visiting.add(key)
        test = tests[key]
        for dependency in test.get('prerequisites', []):
            visit(dependency)
        visiting.remove(key)
        closure[key] = {k: v for k, v in test.items() if k not in VOLATILE_TEST_FIELDS}

    visit(ident)
    context = {k: v for k, v in inventory.items() if k not in VOLATILE_INVENTORY_FIELDS}
    return digest(canonical({'binding_version': BINDING_VERSION, 'inventory_context': context,
                             'test_id': ident, 'contracts': [closure[k] for k in sorted(closure)]}))


def binding_errors(inventory, report, read_bytes):
    """Check v2 bindings against retained snapshots AND the current contracts."""
    errors = []
    try:
        if type(report.get('version')) is not int or report['version'] != 2:
            raise ValueError('expected evidence envelope version 2')
        version = inventory_version(inventory)
        if type(report.get('inventory_version')) is not int or report['inventory_version'] != version:
            raise ValueError('inventory version mismatch')
        if not re.fullmatch('[0-9a-f]{64}', report.get('inventory_sha256', '')):
            raise ValueError('missing original inventory provenance hash')
        if report.get('source_revision') != inventory['source_revision']:
            raise ValueError('implementation revision mismatch')
        if not isinstance(report.get('results'), list):
            raise ValueError('invalid result list')
        snapshots = {}
        for result in report['results']:
            ident = result['id']
            binding = result.get('contract_binding')
            if not isinstance(binding, dict) or set(binding) != BINDING_FIELDS:
                raise ValueError('missing or invalid contract binding: ' + ident)
            if type(binding['version']) is not int or binding['version'] != BINDING_VERSION:
                raise ValueError('unsupported contract binding version: ' + ident)
            if type(binding['inventory_version']) is not int or binding['inventory_version'] != version:
                raise ValueError('record inventory version mismatch: ' + ident)
            for field in ['inventory_sha256', 'contract_sha256']:
                if not isinstance(binding[field], str) or not re.fullmatch('[0-9a-f]{64}', binding[field]):
                    raise ValueError('invalid binding digest: ' + ident)
            name = safe_path(binding['inventory_path'])
            if name not in snapshots:
                data = read_bytes(name)
                snapshots[name] = (digest(data), json.loads(data))
            actual, original = snapshots[name]
            if actual != binding['inventory_sha256']:
                raise ValueError('retained inventory snapshot mismatch: ' + ident)
            if inventory_version(original) != version:
                raise ValueError('retained inventory version mismatch: ' + ident)
            if contract_hash(original, ident) != binding['contract_sha256']:
                raise ValueError('binding does not describe the executed contract: ' + ident)
            if contract_hash(inventory, ident) != binding['contract_sha256']:
                raise ValueError('current test contract or prerequisite changed: ' + ident)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        errors.append(str(exc))
    return errors


def bind_report(report, original, snapshot_path, snapshot_hash):
    """Attach identities derived only from the execution's original inventory."""
    if type(report.get('version')) is not int or report['version'] not in (1, 2):
        raise ValueError('unsupported source envelope')
    if report.get('inventory_sha256') != snapshot_hash:
        raise ValueError('source report and original inventory do not match')
    if report.get('source_revision') != original['source_revision']:
        raise ValueError('source report and inventory revision do not match')
    result = copy.deepcopy(report)
    result.update(version=2, inventory_version=inventory_version(original))
    for record in result['results']:
        # Imported v2 prerequisite records retain their own exact snapshot.
        if 'contract_binding' not in record:
            record['contract_binding'] = {'version': BINDING_VERSION, 'inventory_version': inventory_version(original),
                'inventory_path': safe_path(snapshot_path), 'inventory_sha256': snapshot_hash,
                'contract_sha256': contract_hash(original, record['id'])}
    return result
