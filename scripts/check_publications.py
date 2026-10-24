#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh manuscript builds and a hash-bound tracked thesis, never chip signoff."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ('paper-soc', 'paper-design', 'paper-residual', 'thesis')
RECEIPT = 'docs/evidence/publications-current.json'
HELPERS = ('scripts/check_publications.py', 'scripts/tex_lint.py',
           'scripts/pdf_overlap_check.py', 'paper/check_claims.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(root, name):
    directory = root/name
    paths = {directory/'main.tex', directory/'refs.bib', directory/'Makefile', directory/'claims.yaml'}
    paths.update(directory.rglob('*.tex'))
    paths.update((directory/'figures').rglob('*.pdf'))
    paths.update(root/p for p in HELPERS)
    registry = yaml.safe_load((directory/'claims.yaml').read_text())
    paths.update(root/c['file'] for c in registry['claims'] if c.get('file'))
    for path in paths:
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Publication input escapes repository: '+str(path))
    return {str(p.relative_to(root)): sha(p) for p in sorted(paths)}


def check_freshness(root=ROOT):
    record = json.loads((root/RECEIPT).read_text())
    if record.get('status') != 'PASS' or set(record['documents']) != set(DOCUMENTS):
        raise ValueError('Incomplete publication build receipt')
    for name, row in record['documents'].items():
        if row['inputs'] != inputs(root, name):
            raise ValueError('Stale publication inputs: '+name)
    if set(record.get('tracked_thesis', {})) != {'main.pdf', 'main.bbl'}:
        raise ValueError('Missing tracked thesis PDF or bibliography identity')
    for filename, expected in record['tracked_thesis'].items():
        if sha(root/'thesis'/filename) != expected:
            raise ValueError('Tracked thesis output differs from fresh build: '+filename)
    return record


def pdf_text(path):
    output = subprocess.check_output(['pdftotext', str(path), '-'], text=True)
    if not output.strip():
        raise ValueError('PDF has no extractable text: '+str(path))
    # Ignore line wrapping and metadata, not numbers, punctuation or page order.
    return ''.join(output.split())


def build(root, out, tectonic=None, compare_thesis=False):
    if out.exists() or out.is_symlink():
        raise ValueError('Refusing existing build output: '+str(out))
    if not out.resolve().is_relative_to((root/'hw/soc/out').resolve()):
        raise ValueError('Publication build output must be below hw/soc/out')
    out.mkdir(parents=True)
    (out/'scripts').mkdir()
    shutil.copyfile(root/'scripts/pdf_overlap_check.py', out/'scripts/pdf_overlap_check.py')
    record = {'status': 'FAIL', 'scope': 'Fresh PDF/source/archive and selected historical metric checks only. Outstanding scientific claims and product gates remain open.', 'documents': {}}
    try:
        for name in DOCUMENTS:
            row = {'inputs': inputs(root, name), 'commands': []}
            record['documents'][name] = row
            directory = out/name
            directory.mkdir()
            for rel in row['inputs']:
                if rel.startswith(name+'/'):
                    target = out/rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(root/rel, target)
            commands = [
                [sys.executable, str(root/'scripts/tex_lint.py'), str(directory/'main.tex')],
                [sys.executable, str(root/'paper/check_claims.py'), '--claims', str(root/name/'claims.yaml')],
                ['make', '-C', str(directory), 'arxiv', 'TECTONIC='+str(tectonic or '')],
                [sys.executable, str(root/'scripts/pdf_overlap_check.py'), str(directory/'main.pdf'), '--quiet'],
            ]
            for index, command in enumerate(commands):
                log = out/f'{name}-{index}.log'
                with log.open('x') as stream:
                    result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT, timeout=300,
                                            env={**os.environ, 'SOURCE_DATE_EPOCH': '1789776000'})
                row['commands'].append({'command': command, 'returncode': result.returncode, 'log_sha256': sha(log)})
                if result.returncode:
                    raise ValueError('Publication command failed: '+str(log))
            log_text = (directory/'main.log').read_text(errors='replace')
            if re.search(r'Overfull|(?:Citation|Reference) .* undefined', log_text):
                raise ValueError('TeX layout/reference error: '+name)
            # make success alone is not output provenance: verify nonempty PDFs
            # and text, plus source stability across compilation.
            row['pdf_sha256'] = sha(directory/'main.pdf')
            row['bbl_sha256'] = sha(directory/'main.bbl')
            row['text_sha256'] = hashlib.sha256(pdf_text(directory/'main.pdf').encode()).hexdigest()
            row['archive_sha256'] = sha(directory/'arxiv.tar.gz')
            if row['inputs'] != inputs(root, name):
                raise ValueError('Sources changed during build: '+name)
        if compare_thesis and pdf_text(out/'thesis/main.pdf') != pdf_text(root/'thesis/main.pdf'):
            raise ValueError('Rebuilt thesis content differs from tracked PDF')
        for name, row in record['documents'].items():
            if row['inputs'] != inputs(root, name):
                raise ValueError('Sources changed across document builds: '+name)
        record['status'] = 'PASS'
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        record['error'] = str(error)
    (out/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='check recorded source/output freshness without rebuilding')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--tectonic', type=Path, help='explicit Tectonic; otherwise use TeX Live')
    parser.add_argument('--compare-thesis', action='store_true', help='compare fresh text with the tracked thesis PDF')
    parser.add_argument('--record', action='store_true', help='after a passing build, update the tracked thesis and receipt')
    args = parser.parse_args()
    try:
        if args.check:
            if args.out or args.record:
                parser.error('--check cannot build or publish')
            check_freshness()
            print('Four manuscript source sets and tracked thesis match the fresh-build receipt')
            return 0
        if not args.out:
            parser.error('--out is required for a fresh build')
        result = build(ROOT, args.out.resolve(), args.tectonic, args.compare_thesis)
        if result['status'] != 'PASS':
            raise ValueError(result.get('error', 'Publication build failed'))
        if args.record:
            # Recheck all source sets before replacing any deliverable.
            for name, row in result['documents'].items():
                if row['inputs'] != inputs(ROOT, name):
                    raise ValueError('Sources changed before publication: '+name)
            for filename in ('main.pdf', 'main.bbl'):
                shutil.copyfile(args.out/'thesis'/filename, ROOT/'thesis'/filename)
            result['tracked_thesis'] = {n: sha(ROOT/'thesis'/n) for n in ('main.pdf', 'main.bbl')}
            (ROOT/RECEIPT).write_text(json.dumps(result, indent=2).replace(str(ROOT), '<repo>')+'\n')
        print('PASS: four fresh manuscript builds; no product or complete scientific-claim acceptance')
        return 0
    except (OSError, ValueError, KeyError) as error:
        print('FAIL:', error)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
