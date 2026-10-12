#!/usr/bin/env python3
"""Lossless, restartable project-output migration to GitHub Releases.

Creates <=512 MiB payloads; verifies GitHub's SHA-256 digest; publishes a
self-contained restore manifest before deleting any matching original bytes.
Only hw/soc/out or explicitly selected hw/soc/pnr/runs is in scope.
Never follows symlinks or removes sources/tools.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'hw/soc/out'
STATE = BASE / 'cloud-migration-20261012'
REPO = 'Melihakbulut221/nssoc'
LIMIT = 512 * 1024 * 1024
TAG_PREFIX = 'cloud-migration-20261012'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    temp.replace(path)


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)


def safe(path):
    return (path.is_file() and not path.is_symlink()
            and path.resolve().is_relative_to(BASE)
            and not path.resolve().is_relative_to(STATE))


def release(tag):
    found = subprocess.run(['gh', 'release', 'view', tag, '-R', REPO],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if found.returncode:
        subprocess.run(['gh', 'release', 'create', tag, '-R', REPO,
                        '--target', 'codex/complete-open-work', '--prerelease', '--latest=false',
                        '--title', tag,
                        '--notes', 'Lossless local output migration. Each manifest binds original file paths and hashes to verified archive assets. Incomplete and failing CAD results are preserved as evidence, never signoff.'], check=True)
    return json.loads(gh('api', f'repos/{REPO}/releases/tags/{tag}'))


def publish(path, tag):
    expected = digest(path)
    for attempt in range(6):
        info = release(tag)
        matches = [a for a in info['assets'] if a['name'] == path.name]
        if matches:
            asset = matches[0]
            if asset['size'] == path.stat().st_size and asset.get('digest') == 'sha256:' + expected:
                return dict(name=path.name, bytes=asset['size'], sha256=expected,
                            url=asset['browser_download_url'], id=asset['id'])
            raise RuntimeError('Existing asset differs; never overwrite: ' + path.name)
        result = subprocess.run(['gh', 'release', 'upload', tag, str(path), '-R', REPO])
        if result.returncode == 0:
            continue  # Must verify hosted digest, not merely upload exit status.
        time.sleep(min(60, 5 * (attempt + 1)))
    raise RuntimeError('Upload or digest verification failed: ' + path.name)


def restore_manifest(manifest, directory):
    """Restore a single file record from verified chunks; used by hosted tests."""
    target = directory / manifest['path']
    if Path(manifest['path']).is_absolute() or '..' in Path(manifest['path']).parts:
        raise ValueError('Unsafe restore path')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as dest:
        for part in manifest['parts']:
            source = directory / part['name']
            if digest(source) != part['sha256']:
                raise ValueError('Corrupt archive')
            with gzip.open(source, 'rb') as stream:
                shutil.copyfileobj(stream, dest)
    if digest(target) != manifest['sha256']:
        raise ValueError('Restored content differs')
    os.chmod(target, manifest['mode'])
    return target


def main():
    global BASE, STATE, TAG_PREFIX
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--scope', choices=['outputs', 'pnr-runs'], default='outputs')
    args = parser.parse_args()
    if args.scope == 'pnr-runs':
        BASE = ROOT / 'hw/soc/pnr/runs'
        STATE = ROOT / 'hw/soc/out/cloud-migration-pnr-20261013'
        TAG_PREFIX = 'cloud-migration-pnr-20261013'
        tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', 'hw/soc/pnr/runs'], cwd=ROOT)
        if tracked:
            raise RuntimeError('PNR run scope contains tracked sources; refusing cleanup')
    STATE.mkdir(exist_ok=True)
    planpath = STATE / 'remaining-plan.json'
    if not planpath.exists():
        paths = []
        for directory, dirs, files in os.walk(BASE, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in (STATE.name, '.git', '.ssh')
                             and not (Path(directory) / d).is_symlink())
            for name in sorted(files):
                path = Path(directory) / name
                if name == '.env' or name.startswith(('id_rsa', 'id_ed25519')):
                    continue
                if safe(path):
                    paths.append(str(path.relative_to(ROOT)))
        # Preserve latest engineering work first, before old reproducible captures.
        paths.sort(key=lambda p: ('20261012' not in p, '20261011' not in p, p))
        atomic(planpath, paths)
    paths = json.loads(planpath.read_text())
    progresspath = STATE / 'transfer-progress.json'
    progress = json.loads(progresspath.read_text()) if progresspath.exists() else dict(
        status='RUNNING', next_index=0, batch=0, removed_bytes=0, uploaded_bytes=0)
    index = progress['next_index']
    while index < len(paths):
        # A durable manifest may precede a crash during deletion. Finish that
        # exact batch instead of rebuilding a different batch under its name.
        pending = STATE / f'batch-{progress["batch"]:06d}.manifest.json'
        if pending.exists():
            saved = json.loads(pending.read_text())
            tag = f'{TAG_PREFIX}-{progress["batch"] // 100:03d}'
            remote = {a['name']: a for a in release(tag)['assets']}
            for part in saved['parts']:
                asset = remote.get(part['name'], {})
                if (asset.get('digest') != 'sha256:' + part['sha256']
                        or asset.get('size') != part['bytes']):
                    raise RuntimeError('Resume requires every exact hosted part')
            publish(pending, tag)
            if args.apply:
                for record in saved['records']:
                    path = ROOT / record['path']
                    if safe(path):
                        if digest(path) != record['sha256']:
                            raise RuntimeError('Changed original during resume')
                        path.unlink()
                        progress['removed_bytes'] += record['bytes']
            index = saved['source_index'][1]
            progress.update(status='RUNNING', next_index=index, batch=progress['batch'] + 1)
            atomic(progresspath, progress)
            continue
        while shutil.disk_usage(STATE).free < LIMIT * 3:
            progress['status'] = 'WAITING_TRANSFER_DISK_RESERVE'
            atomic(progresspath, progress)
            time.sleep(30)
        start = index
        selected = []
        total = 0
        while index < len(paths):
            path = ROOT / paths[index]
            if not safe(path):
                index += 1
                continue
            size = path.stat().st_size
            if selected and total + size > LIMIT:
                break
            selected.append(path)
            total += size
            index += 1
            if total >= LIMIT:
                break
        if not selected:
            break
        batch = progress['batch']
        tag = f'{TAG_PREFIX}-{batch // 100:03d}'
        prefix = f'batch-{batch:06d}'
        records = [dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size,
                        mode=p.stat().st_mode & 0o777, sha256=digest(p)) for p in selected]
        manifest = dict(format=1, source_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                        records=records, source_index=[start, index], parts=[])
        if len(selected) == 1 and total > LIMIT:
            manifest['encoding'] = 'concatenated-gzip-parts-single-file'
            with selected[0].open('rb') as source:
                number = 0
                while True:
                    block = source.read(LIMIT)
                    if not block:
                        break
                    part = STATE / f'{prefix}.part-{number:04d}.gz'
                    with part.open('wb') as raw:
                        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=1) as stream:
                            stream.write(block)
                    receipt = publish(part, tag)
                    manifest['parts'].append(receipt)
                    progress['uploaded_bytes'] += receipt['bytes']
                    atomic(STATE / (prefix + '.partial.json'), manifest)
                    part.unlink()  # Verified remote copy, original still retained.
                    number += 1
        else:
            manifest['encoding'] = 'tar-gzip'
            part = STATE / (prefix + '.tar.gz')
            with part.open('wb') as raw:
                with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=1) as stream:
                    with tarfile.open(fileobj=stream, mode='w|') as tar:
                        for path in selected:
                            tar.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
            receipt = publish(part, tag)
            manifest['parts'].append(receipt)
            progress['uploaded_bytes'] += receipt['bytes']
            part.unlink()
        # Rehash original input after all uploads; changed data is never removed.
        for path, record in zip(selected, records):
            if not safe(path) or digest(path) != record['sha256']:
                raise RuntimeError('Input changed during migration: ' + str(path))
        manifestpath = STATE / (prefix + '.manifest.json')
        atomic(manifestpath, manifest)
        manifestreceipt = publish(manifestpath, tag)
        with (STATE / 'transfer-receipts.jsonl').open('a') as log:
            log.write(json.dumps(dict(manifest=manifestreceipt, records=records,
                                      delete_requested=args.apply)) + '\n')
            log.flush()
            os.fsync(log.fileno())
        if args.apply:
            for path, record in zip(selected, records):
                if safe(path) and digest(path) == record['sha256']:
                    path.unlink()
                    progress['removed_bytes'] += record['bytes']
        progress.update(status='RUNNING', next_index=index, batch=batch + 1)
        atomic(progresspath, progress)
        print(json.dumps(progress), flush=True)
    progress['status'] = 'COMPLETE_SELECTED_REGULAR_OUTPUT_FILES'
    atomic(progresspath, progress)


if __name__ == '__main__':
    main()
