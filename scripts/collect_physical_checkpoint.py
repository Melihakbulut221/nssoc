#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Capture actual files referenced by the last completed physical state."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def transform(value, visit):
    if isinstance(value, dict):
        return {k: v if k == 'metrics' else transform(v, visit) for k, v in value.items()}
    if isinstance(value, list):
        return [transform(v, visit) for v in value]
    if value is None:
        return None
    if isinstance(value, str):
        return visit(value)
    raise ValueError('Unexpected state view value')


def capture(root, run, out):
    root, run, out = root.resolve(), run.resolve(), out.resolve()
    if not run.is_relative_to(root/'hw/soc/pnr/runs'):
        raise ValueError('Run must be under hw/soc/pnr/runs')
    if not out.is_relative_to(root/'hw/soc/out') or out.exists():
        raise ValueError('Use a fresh output directory under hw/soc/out')
    candidates = []
    for p in run.glob('*/state_out.json'):
        match = re.fullmatch(r'(\d+)-.+', p.parent.name)
        if match:
            candidates.append((int(match[1]), p))
    if not candidates:
        raise ValueError('No completed physical step state')
    # Do not silently substitute an older state if the newest one is damaged.
    source = max(candidates)[1]
    source_bytes = source.read_bytes()
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    state = json.loads(source_bytes)
    if not all(isinstance(state.get(k), str) for k in ('odb', 'nl', 'sdc')):
        raise ValueError('Latest state lacks ODB/netlist/constraints')
    files = {}

    def inspect(name):
        original = Path(name).resolve()
        if not original.is_relative_to(root/'hw/soc') or not original.is_file():
            raise ValueError('Missing or external state view: '+name)
        destination = 'files/'+str(original.relative_to(root))
        files[destination] = {'source': str(original), 'sha256': digest(original),
                              'bytes': original.stat().st_size}
        return destination

    relative = transform(state, inspect)
    out.mkdir(parents=True)
    for name, item in files.items():
        target = out/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item['source'], target)
        if digest(target) != item['sha256'] or digest(Path(item['source'])) != item['sha256']:
            raise ValueError('Source changed during checkpoint capture')
    (out/'state.relative.json').write_text(json.dumps(relative, indent=2)+'\n')
    shutil.copyfile(source, out/'state.original.json')
    if digest(source) != source_digest or digest(out/'state.original.json') != source_digest:
        raise ValueError('State changed during checkpoint capture')
    if any(digest(Path(item['source'])) != item['sha256'] for item in files.values()):
        raise ValueError('Source changed during checkpoint capture')
    record = {'status': 'CAPTURED', 'scope': 'Restart files only; no timing/DRC/LVS acceptance',
              'collector_sha256': digest(Path(__file__)),
              'source_state': str(source), 'source_state_sha256': source_digest,
              'relative_state_sha256': digest(out/'state.relative.json'), 'files': files}
    (out/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


def restore(bundle):
    bundle = bundle.resolve()
    record = json.loads((bundle/'manifest.json').read_text())
    if record['status'] != 'CAPTURED':
        raise ValueError('Incomplete checkpoint')
    if digest(bundle/'state.relative.json') != record['relative_state_sha256']:
        raise ValueError('State digest mismatch')
    target = bundle/'state.local.json'
    if target.exists():
        raise ValueError('Refusing to overwrite existing local state')

    def relocate(name):
        path = (bundle/name).resolve()
        if not path.is_relative_to(bundle) or name not in record['files']:
            raise ValueError('Checkpoint view escapes bundle')
        if not path.is_file() or digest(path) != record['files'][name]['sha256']:
            raise ValueError('Checkpoint view digest mismatch: '+name)
        return str(path)

    state = transform(json.loads((bundle/'state.relative.json').read_text()), relocate)
    target.write_text(json.dumps(state, indent=2)+'\n')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    collect = sub.add_parser('capture')
    collect.add_argument('--run', type=Path, required=True)
    collect.add_argument('--out', type=Path, required=True)
    local = sub.add_parser('restore')
    local.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'capture':
        record = capture(ROOT, args.run, args.out)
        print('CAPTURED', record['source_state'], len(record['files']), 'files')
    else:
        print(restore(args.bundle))


if __name__ == '__main__':
    main()
