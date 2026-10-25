#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Remove exact older-file copies found inside fully verified cloud archives."""
import gzip
import json
from pathlib import Path
import subprocess
from migrate_outputs_to_cloud import publish, digest

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'hw/soc/out/cloud-migration-20261012'
UNIT = 'nssoc-cloud-output-transfer-20261012'


def main():
    receipt = json.loads((STATE / 'catalog-receipt.json').read_text())
    assert receipt['status'] == 'COMPLETE_FOUR_VERIFIED_CLOUD_CATALOGS'
    subprocess.run(['systemctl', '--user', 'kill', '--kill-whom=main', '--signal=STOP', UNIT], check=True)
    try:
        progress = json.loads((STATE / 'transfer-progress.json').read_text())
        paths = json.loads((STATE / 'remaining-plan.json').read_text())
        assert '20261012' in paths[progress['next_index']]
        current = STATE / f'batch-{progress["batch"]:06d}.partial.json'
        if current.exists():
            assert all('20261012' in r['path'] for r in json.loads(current.read_text())['records'])
        sizes = {}
        with gzip.open(STATE / 'cloud-verified-members.jsonl.gz', 'rt') as source:
            for line in source:
                record = json.loads(line)
                sizes.setdefault(record['bytes'], {})[record['sha256']] = record
        matches = []
        checked = 0
        for relative in paths:
            if '20261012' in relative:
                continue
            path = ROOT / relative
            if (path.is_symlink() or not path.is_file()
                    or not path.resolve().is_relative_to(ROOT / 'hw/soc/out')):
                continue
            size = path.stat().st_size
            if size < 1024 * 1024 or size not in sizes:
                continue
            sha = digest(path)
            source = sizes[size].get(sha)
            if source:
                matches.append(dict(path=relative, bytes=size, sha256=sha,
                                    archive=source['archive'], member=source['member']))
            checked += 1
            if checked % 100 == 0:
                print('checked', checked, 'matched', len(matches),
                      'GB', sum(r['bytes'] for r in matches) / 1e9, flush=True)
        plan = STATE / 'catalog-exact-matches.json'
        plan.write_text(json.dumps(dict(catalog=receipt, files=matches,
            method='Exact original file digest and length equal an actual archive-member digest measured on hosted runner. Each complete archive digest matched GitHub first. Latest-day active transfer inputs excluded.'), indent=2) + '\n')
        remote = publish(plan, 'cloud-migration-20261012-000')
        removed = 0
        size = 0
        # Durable remote restoration map exists before the first unlink.
        with (STATE / 'catalog-deletions.jsonl').open('a', buffering=1) as journal:
            for record in matches:
                path = ROOT / record['path']
                if path.is_file() and not path.is_symlink() and digest(path) == record['sha256']:
                    path.unlink()
                    size += record['bytes']
                    removed += 1
                    journal.write(json.dumps(dict(path=record['path'], bytes=record['bytes'], sha256=record['sha256'])) + '\n')
        result = dict(status='COMPLETE_VERIFIED_ARCHIVE_MEMBER_CLEANUP',
                      restoration_manifest=remote, files=removed, logical_bytes_removed=size)
        (STATE / 'catalog-cleanup-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    finally:
        subprocess.run(['systemctl', '--user', 'kill', '--kill-whom=main', '--signal=CONT', UNIT], check=True)


if __name__ == '__main__':
    main()
