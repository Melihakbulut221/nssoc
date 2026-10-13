#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read back published migration batches on hosted runners without extracting code."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile

REPO = 'Melihakbulut221/nssoc'


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path], text=True))


def pages(path):
    result = json.loads(subprocess.check_output(
        ['gh', 'api', '--paginate', '--slurp', path], text=True))
    return [item for page in result for item in page]


def download(asset, destination):
    subprocess.run(['curl', '--fail', '--location', '--retry', '4',
                    '--silent', '--show-error', asset['browser_download_url'],
                    '-o', str(destination)], check=True)
    with destination.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    assert destination.stat().st_size == asset['size'], asset['name']
    assert asset.get('digest') == 'sha256:' + digest, asset['name']
    return digest


def safe_name(name):
    p = PurePosixPath(name)
    assert not p.is_absolute() and '..' not in p.parts
    assert (p.parts[:3] == ('hw', 'soc', 'out') or
            p.parts[:4] == ('hw', 'soc', 'pnr', 'runs') or
            p.parts[:3] == ('hw', 'soc', 'tools'))
    assert str(p) == name


def audit(manifest, assets, work):
    assert manifest['format'] == 1
    records = manifest['records']
    expected = {r['path']: r for r in records}
    assert len(expected) == len(records) and expected
    for name in expected:
        safe_name(name)
    seen = set()
    verified_members = {}
    hardlinks = 0
    total = 0
    single = manifest['encoding'] == 'concatenated-gzip-parts-single-file'
    assert single or manifest['encoding'] == 'tar-gzip'
    if single:
        assert len(records) == 1
        combined = hashlib.sha256()
    else:
        assert len(manifest['parts']) == 1
    for part in manifest['parts']:
        asset = assets[part['name']]
        assert asset['size'] == part['bytes']
        assert asset['digest'] == 'sha256:' + part['sha256']
        assert asset['browser_download_url'] == part['url']
        packed = work / 'payload'
        download(asset, packed)
        if single:
            with gzip.open(packed, 'rb') as stream:
                while block := stream.read(1024 * 1024):
                    combined.update(block)
                    total += len(block)
        else:
            with tarfile.open(packed, 'r|gz') as archive:
                for member in archive:
                    safe_name(member.name)
                    assert member.name not in seen, ('Duplicate member', member.name)
                    record = expected[member.name]
                    assert member.mode & 0o777 == record['mode']
                    if member.islnk():
                        # tarfile preserves repeated inodes as backward hard links.
                        # Resolve only already hashed archive members, never paths
                        # in the runner filesystem or unverified forward targets.
                        safe_name(member.linkname)
                        assert member.size == 0
                        assert member.linkname in verified_members, ('Unverified hardlink target', member.name, member.linkname)
                        size, actual = verified_members[member.linkname]
                        assert size == record['bytes'], ('Hardlink length differs', member.name)
                        hardlinks += 1
                    else:
                        assert member.isfile(), ('Unsupported member type', member.name, member.type)
                        assert member.size == record['bytes']
                        with archive.extractfile(member) as stream:
                            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
                    assert actual == record['sha256'], member.name
                    verified_members[member.name] = (record['bytes'], actual)
                    seen.add(member.name)
                    total += record['bytes']
        packed.unlink()
    if single:
        assert total == records[0]['bytes']
        assert combined.hexdigest() == records[0]['sha256']
    else:
        assert seen == set(expected)
    return dict(files=len(records), restored_logical_bytes=total, verified_hardlinks=hardlinks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', type=int, required=True)
    parser.add_argument('--archive-scope', choices=['all', 'outputs', 'pnr-runs', 'tools'], default='all')
    args = parser.parse_args()
    assert 0 <= args.group < 4
    out = Path('cloud-output-restore')
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', group=args.group, archive_scope=args.archive_scope, batches=[],
                  scope='Full compressed asset and reconstructed original-byte checks for complete published batch manifests at this run snapshot. Partial uploads and prior independent catalog cleanup are excluded.')
    try:
        prefixes = {'outputs': ('cloud-migration-20261012-',),
                    'pnr-runs': ('cloud-migration-pnr-20261013-',),
                    'tools': ('cloud-migration-tools-20261013-',),
                    'all': ('cloud-migration-20261012-', 'cloud-migration-pnr-20261013-',
                            'cloud-migration-tools-20261013-')}
        releases = pages(f'repos/{REPO}/releases?per_page=100')
        worklist = []
        for release in releases:
            if not release['tag_name'].startswith(prefixes[args.archive_scope]):
                continue
            items = pages(f'repos/{REPO}/releases/{release["id"]}/assets?per_page=100')
            assets = {a['name']: a for a in items}
            for name, asset in sorted(assets.items()):
                if name.startswith('batch-') and name.endswith('.manifest.json'):
                    batch = int(name.split('.')[0].split('-')[1])
                    if batch % 4 == args.group:
                        worklist.append((asset, assets))
        assert worklist, 'No complete batch manifests available for this group'
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            for asset, assets in worklist:
                path = work / 'manifest.json'
                digest = download(asset, path)
                manifest = json.loads(path.read_text())
                checked = audit(manifest, assets, work)
                checked.update(manifest_url=asset['browser_download_url'], manifest_sha256=digest,
                               source_head=manifest['source_head'])
                result['batches'].append(checked)
                print(json.dumps(checked), flush=True)
                (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        result['status'] = 'PASS_COMPLETE_PUBLISHED_BATCH_BYTE_RECONSTRUCTION'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
