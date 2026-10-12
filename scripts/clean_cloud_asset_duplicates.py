#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Remove older output files identical to complete assets, regardless of name."""
import hashlib
import json
from pathlib import Path
import subprocess
from migrate_outputs_to_cloud import publish

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'hw/soc/out/cloud-migration-20261012'
UNIT = 'nssoc-cloud-output-transfer-20261012'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    # Freeze only the transfer controller. Its current upload can finish.
    subprocess.run(['systemctl', '--user', 'kill', '--kill-whom=main', '--signal=STOP', UNIT], check=True)
    try:
        progress = json.loads((STATE / 'transfer-progress.json').read_text())
        paths = json.loads((STATE / 'remaining-plan.json').read_text())
        # Current controller must still be wholly in the protected latest day.
        assert '20261012' in paths[progress['next_index']]
        current = STATE / f'batch-{progress["batch"]:06d}.partial.json'
        if current.exists():
            assert all('20261012' in r['path'] for r in json.loads(current.read_text())['records'])
        raw = subprocess.check_output(['gh', 'api', '--paginate',
            'repos/Melihakbulut221/nssoc/releases?per_page=100',
            '--jq', '.[] | {tag_name,assets:[.assets[]|{id,name,size,digest,browser_download_url}]}'], text=True)
        sizes = {}
        for row in raw.splitlines():
            for asset in json.loads(row)['assets']:
                if asset.get('digest', '').startswith('sha256:'):
                    sizes.setdefault(asset['size'], {})[asset['digest'][7:]] = asset
        matches = []
        count = 0
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
            count += 1
            digest = sha(path)
            asset = sizes[size].get(digest)
            if asset:
                matches.append(dict(path=relative, bytes=size, sha256=digest,
                                    asset_url=asset['browser_download_url'], asset_id=asset['id']))
            if count % 50 == 0:
                print('hashed', count, 'matches', len(matches), flush=True)
        plan = STATE / 'direct-asset-matches.json'
        plan.write_text(json.dumps(dict(method='Complete file SHA256 and length match current GitHub asset digest; original filename need not match. All latest-day migration inputs excluded.', files=matches), indent=2) + '\n')
        receipt = publish(plan, 'cloud-migration-20261012-000')
        removed = []
        for record in matches:
            path = ROOT / record['path']
            if path.is_file() and not path.is_symlink() and sha(path) == record['sha256']:
                path.unlink()
                removed.append(record)
        result = dict(status='COMPLETE_DIRECT_ASSET_DUPLICATE_CLEANUP',
                      recovery_manifest=receipt, files=len(removed),
                      logical_bytes_removed=sum(r['bytes'] for r in removed))
        (STATE / 'direct-asset-cleanup-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
    finally:
        subprocess.run(['systemctl', '--user', 'kill', '--kill-whom=main', '--signal=CONT', UNIT], check=True)


if __name__ == '__main__':
    main()
