#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve inert NSSOC temporary files remotely before removing exact originals.

Transfer only: no CAD, simulation or tests are executed. The initial inventory
is immutable on restart. Symlink text is preserved, never its target. A complete
remote readback of every member is mandatory before any original is removed.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile

from migrate_outputs_to_cloud import ROOT, atomic, digest, publish

STATE = ROOT / 'hw/soc/out/cloud-migration-transients-20261013'
TAG = 'cloud-migration-transients-20261013'
BASES = (Path('/tmp'), Path('/dev/shm'))
BATCH_SIZE = 4000


def allowed(path):
    for base in BASES:
        try:
            rel = path.relative_to(base)
        except ValueError:
            continue
        if not rel.parts or not rel.parts[0].startswith('nssoc') or '..' in rel.parts:
            continue
        if any(p.is_symlink() for p in path.parents if p != base and p.is_relative_to(base)):
            return False
        return True
    return False


def record(path):
    if not allowed(path):
        raise ValueError('Outside exact NSSOC temporary scope')
    s = path.lstat()
    item = dict(path=str(path), member=str(path).lstrip('/'), mode=stat.S_IMODE(s.st_mode))
    if stat.S_ISLNK(s.st_mode):
        item.update(kind='symlink', target=os.readlink(path))
    elif stat.S_ISREG(s.st_mode):
        item.update(kind='file', bytes=s.st_size, sha256=digest(path))
    else:
        raise ValueError('Unsupported filesystem entry: ' + str(path))
    return item


def verify_archive(archive_path, rows):
    expected = {r['member']: r for r in rows}
    if len(expected) != len(rows):
        raise ValueError('Duplicate inventory entry')
    seen = set()
    with tarfile.open(archive_path, 'r|gz') as packed:
        for member in packed:
            if member.name not in expected or member.name in seen:
                raise ValueError('Unexpected or duplicate archived entry')
            r = expected[member.name]
            if member.mode != r['mode']:
                raise ValueError('Archive mode differs')
            if r['kind'] == 'symlink':
                if not member.issym() or member.linkname != r['target']:
                    raise ValueError('Archive link differs')
            else:
                if not member.isfile() or member.size != r['bytes']:
                    raise ValueError('Archive type or length differs')
                with packed.extractfile(member) as stream:
                    if hashlib.file_digest(stream, 'sha256').hexdigest() != r['sha256']:
                        raise ValueError('Archive bytes differ')
            seen.add(member.name)
    if seen != set(expected):
        raise ValueError('Archive missing entries')


def remove_original(row):
    path = Path(row['path'])
    try:
        current = record(path)
    except FileNotFoundError:
        return False
    if current != row:
        raise ValueError('Original changed; preserve it: ' + str(path))
    path.unlink()
    return True


def transfer_batch(batch, rows):
    selected = rows
    archive = STATE / f'transients-{batch:03d}.tar.gz'
    remote = STATE / f'transients-{batch:03d}.readback.tar.gz'
    receiptfile = STATE / f'transients-{batch:03d}.receipt.json'
    if not receiptfile.exists():
        if not archive.exists():
            temporary = archive.with_suffix('.tmp')
            with tarfile.open(temporary, 'w:gz', compresslevel=1, dereference=False) as packed:
                for row in selected:
                    path = Path(row['path'])
                    if record(path) != row:
                        raise ValueError('Original changed before packaging')
                    # Each regular member has an independent hashed payload.
                    packed.inodes.clear()
                    packed.add(path, arcname=row['member'], recursive=False)
            temporary.replace(archive)
        verify_archive(archive, selected)
        atomic(receiptfile, publish(archive, TAG))
    receipt = json.loads(receiptfile.read_text())
    manifest = STATE / f'transients-{batch:03d}.manifest.json'
    atomic(manifest, dict(receipt=receipt, entries=selected))
    manifest_receipt = publish(manifest, TAG)
    from cloud_archive_readback import wait_verified_readback
    proof = wait_verified_readback(manifest_receipt, TAG, STATE / f'transients-{batch:03d}.hosted.json')
    # The complete restore manifest is durable before any deletion.
    for row in selected:
        remove_original(row)
    archive.unlink(missing_ok=True)
    remote.unlink(missing_ok=True)
    return dict(receipt=receipt, manifest=manifest_receipt, hosted_proof=proof, entries=len(selected), logical_bytes=sum(r.get('bytes', 0) for r in selected))


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    planpath = STATE / 'inventory.json'
    if not planpath.exists():
        roots = sorted(p for b in BASES for p in b.glob('nssoc*'))
        # Refuse any root still used as a working directory or open descriptor.
        for proc in Path('/proc').glob('[0-9]*'):
            try:
                refs = [os.readlink(proc / 'cwd')]
                refs += [os.readlink(p) for p in (proc / 'fd').iterdir()]
            except (PermissionError, FileNotFoundError, ProcessLookupError):
                continue
            if any(x == str(r) or x.startswith(str(r) + '/') for x in refs for r in roots):
                raise RuntimeError('Active process uses a selected temporary root')
        paths = []
        for root in roots:
            if root.is_dir() and not root.is_symlink():
                for directory, dirs, files in os.walk(root, followlinks=False):
                    paths += [Path(directory) / n for n in files]
                    paths += [Path(directory) / n for n in dirs if (Path(directory) / n).is_symlink()]
            else:
                paths.append(root)
        rows = [record(p) for p in sorted(paths)]
        token = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)')
        for row in rows:
            if row['kind'] == 'file':
                with open(row['path'], 'rb') as stream:
                    tail = b''
                    while block := stream.read(1024 * 1024):
                        if token.search(tail + block):
                            raise RuntimeError('Potential credential; preserve locally for review: ' + row['path'])
                        tail = block[-256:]
        atomic(planpath, dict(roots=[str(r) for r in roots], entries=rows))
    plan = json.loads(planpath.read_text())
    rows = plan['entries']
    progressfile = STATE / 'progress.json'
    progress = json.loads(progressfile.read_text()) if progressfile.exists() else dict(batches=[])
    if progress.get('status') == 'COMPLETE_REMOTE_READBACK_AND_LOCAL_CLEANUP':
        return
    # Each worker owns disjoint immutable archive members and receipt files.
    # Ordered progress commits preserve old restart boundaries; a later worker
    # may finish first, but its exact archive/manifest/proof remains recoverable.
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = [(batch, pool.submit(transfer_batch, batch, rows[start:start + BATCH_SIZE]))
                   for batch, start in enumerate(range(0, len(rows), BATCH_SIZE))
                   if batch >= len(progress['batches'])]
        for batch, future in pending:
            progress['batches'].append(future.result())
            progress['status'] = 'RUNNING'
            atomic(progressfile, progress)
            print(json.dumps(dict(batch=batch, entries=sum(b['entries'] for b in progress['batches']))), flush=True)
    for root in map(Path, plan['roots']):
        if root.is_dir() and not root.is_symlink():
            for directory, dirs, files in os.walk(root, topdown=False, followlinks=False):
                try:
                    Path(directory).rmdir()
                except OSError:
                    pass  # A new or changed file must never be recursively erased.
    remaining = [r for r in plan['roots'] if os.path.lexists(r)]
    if remaining:
        raise RuntimeError('Some roots contain new or changed entries: ' + repr(remaining))
    progress['status'] = 'COMPLETE_REMOTE_READBACK_AND_LOCAL_CLEANUP'
    atomic(progressfile, progress)
    publish(progressfile, TAG)


if __name__ == '__main__':
    main()
