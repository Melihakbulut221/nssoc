#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Publish a small source-bound JSON report from a hosted evidence archive."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset', required=True)
    parser.add_argument('--member', required=True)
    args = parser.parse_args()
    assert Path(args.asset).name == args.asset and args.asset.endswith('.tar.gz')
    repo = 'Melihakbulut221/nssoc'
    release = 'cloud-migration-20261012-000'
    pages = json.loads(subprocess.check_output(['gh', 'api', '--paginate', '--slurp',
        f'repos/{repo}/releases/tags/{release}'], text=True))
    info = pages[0]
    assets = json.loads(subprocess.check_output(['gh', 'api', '--paginate', '--slurp',
        f'repos/{repo}/releases/{info["id"]}/assets?per_page=100'], text=True))
    matches = [a for page in assets for a in page if a['name'] == args.asset]
    assert len(matches) == 1
    asset = matches[0]
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / 'archive.tar.gz'
        subprocess.run(['curl', '--fail', '--location', '--retry', '4',
                        '--silent', '--show-error', asset['browser_download_url'],
                        '-o', str(path)], check=True)
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        assert asset.get('digest') == 'sha256:' + digest
        assert path.stat().st_size == asset['size']
        result = None
        with tarfile.open(path, 'r|gz') as archive:
            for member in archive:
                if member.name == args.member:
                    assert result is None and member.isfile() and member.size <= 10 * 1024 * 1024
                    with archive.extractfile(member) as stream:
                        member_bytes = stream.read()
                        result = json.loads(member_bytes) if args.member.endswith('.json') else member_bytes.decode('utf-8')
        assert result is not None
    member_id = hashlib.sha256(args.member.encode()).hexdigest()[:12]
    out = Path(args.asset.removesuffix('.tar.gz') + '.' + member_id + '.summary.json')
    out.write_text(json.dumps(dict(archive_url=asset['browser_download_url'],
        archive_sha256=digest, archive_bytes=asset['size'], member=args.member,
        member_sha256=hashlib.sha256(member_bytes).hexdigest(), member_bytes=len(member_bytes),
        result=result), indent=2) + '\n')
    existing = [a for page in assets for a in page if a['name'] == out.name]
    if existing:
        assert len(existing) == 1 and existing[0]['digest'] == 'sha256:' + hashlib.sha256(out.read_bytes()).hexdigest()
    else:
        subprocess.run(['gh', 'release', 'upload', release, str(out), '-R', repo], check=True)
    print(out.read_text(), flush=True)


if __name__ == '__main__':
    main()
