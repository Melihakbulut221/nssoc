#!/usr/bin/env python3
"""Remove only byte-identical output copies in a hash-verified GitHub asset.

Never deletes source files, symlinks, changed files or unarchived results.
The journal maps each deleted file to a permanent archive member for restoration.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    allowed = root / 'hw/soc/out'
    assets = json.loads(subprocess.check_output([
        'gh', 'api', 'repos/Melihakbulut221/nssoc/releases/tags/evidence-20261006-pcie-closure']))['assets']
    assets = {a['name']: a for a in assets}
    args.journal.parent.mkdir(parents=True, exist_ok=True)
    with args.journal.open('a', buffering=1) as journal:
        def record(row):
            journal.write(json.dumps(row) + '\n')
            journal.flush()
            import os
            os.fsync(journal.fileno())

        for item in json.loads(args.plan.read_text()):
            archive = root / item['path']
            if not archive.is_file() or archive.is_symlink():
                continue
            asset = assets[archive.name]
            digest = asset.get('digest', '').removeprefix('sha256:')
            if (not archive.resolve().is_relative_to(allowed)
                    or digest != item['remote_sha256']
                    or archive.stat().st_size != asset['size']
                    or sha(archive) != digest):
                raise RuntimeError(f'Archive identity mismatch: {archive}')
            verified = []
            # Stream entire tar, hash actual member bytes, never extract paths.
            with tarfile.open(archive, 'r|gz') as tar:
                for member in tar:
                    name = PurePosixPath(member.name)
                    if (not member.isfile() or name.is_absolute() or '..' in name.parts
                            or member.size < 1024 * 1024):
                        continue
                    path = root / name
                    if (path == archive or path.is_symlink() or not path.is_file()
                            or not path.resolve().is_relative_to(allowed)
                            or 'cloud-migration-20261012' in path.parts
                            or path.stat().st_size != member.size):
                        continue
                    with tar.extractfile(member) as stream:
                        member_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
                    if sha(path) == member_sha:
                        verified.append((path, member.name, member_sha, member.size))
            if sha(archive) != digest:
                raise RuntimeError('Archive changed during verification')
            for path, member, member_sha, size in verified:
                if not path.is_file() or path.is_symlink() or sha(path) != member_sha:
                    continue
                row = dict(path=str(path.relative_to(root)), member=member,
                           sha256=member_sha, bytes=size, asset_id=asset['id'],
                           asset_url=asset['browser_download_url'], archive_sha256=digest,
                           state='DELETE_INTENT' if args.apply else 'VERIFIED_DRY_RUN')
                record(row)
                if args.apply:
                    path.unlink()
                    record(dict(row, state='DELETED'))
            if args.apply:
                record(dict(path=item['path'], sha256=digest, bytes=asset['size'],
                            asset_url=asset['browser_download_url'], state='ARCHIVE_DELETE_INTENT'))
                archive.unlink()
                record(dict(path=item['path'], bytes=asset['size'], state='ARCHIVE_DELETED'))
            print(archive.name, 'verified members', len(verified), flush=True)


if __name__ == '__main__':
    main()
