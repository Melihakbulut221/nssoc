#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hash existing release archive members on hosted runners, without extracting."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', type=int, required=True)
    args = parser.parse_args()
    plan = Path('docs/evidence/cloud-archive-index-input-20261012.json')
    assets = json.loads(plan.read_text())['groups'][args.group]
    out = Path('cloud-archive-index')
    out.mkdir(exist_ok=False)
    summary = dict(status='RUNNING', group=args.group, complete=[], failed=[],
                   plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest())
    def save():
        (out / 'result.json').write_text(json.dumps(summary, indent=2) + '\n')
    save()
    with gzip.open(out / 'members.jsonl.gz', 'wt') as records:
        for index, asset in enumerate(assets):
            try:
                with tempfile.TemporaryDirectory() as temp:
                    path = Path(temp) / asset['name']
                    subprocess.run(['curl', '--fail', '--location', '--retry', '4',
                                    '--silent', '--show-error', asset['url'], '-o', str(path)], check=True)
                    with path.open('rb') as stream:
                        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                    if digest != asset['sha256'] or path.stat().st_size != asset['bytes']:
                        raise ValueError('Archive digest/length mismatch')
                    # Buffer this asset's records separately: malformed containers
                    # never contribute a partially accepted membership catalog.
                    staged = Path(temp) / 'members.jsonl'
                    members = 0
                    with staged.open('w') as target:
                        def member(name, size, stream):
                            nonlocal members
                            with stream:
                                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                            target.write(json.dumps(dict(archive=asset, member=name,
                                                         bytes=size, sha256=digest)) + '\n')
                            members += 1
                        if asset['name'].endswith('.zip'):
                            with zipfile.ZipFile(path) as archive:
                                for item in archive.infolist():
                                    if not item.is_dir() and item.file_size >= 1024 * 1024:
                                        member(item.filename, item.file_size, archive.open(item))
                        else:
                            with tarfile.open(path, 'r|*') as archive:
                                for item in archive:
                                    if item.isfile() and item.size >= 1024 * 1024:
                                        member(item.name, item.size, archive.extractfile(item))
                    with staged.open() as source:
                        for line in source:
                            records.write(line)
                    records.flush()
                    summary['complete'].append(dict(asset=asset['name'], members=members))
                    print(index + 1, '/', len(assets), asset['name'], members, flush=True)
            except Exception as error:
                summary['failed'].append(dict(asset=asset['name'], error=repr(error)))
                print('FAILED', asset['name'], repr(error), flush=True)
            save()
    summary['status'] = 'COMPLETE' if not summary['failed'] else 'PARTIAL_WITH_FAILED_ARCHIVES'
    save()
    if summary['failed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
