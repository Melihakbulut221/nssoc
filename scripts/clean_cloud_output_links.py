#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Archive inert output link/FIFO metadata before unlinking; never follow links.

Regular output bytes use migrate_outputs_to_cloud.py. This companion preserves
the link text and FIFO mode needed to recreate excluded filesystem entries.
Run only after local producers are stopped. Source checkout is out of scope; tool links require --scope tools. The default is inventory only; --apply requires a verified receipt.
"""
import argparse
import os
from pathlib import Path
import stat
import subprocess

from migrate_outputs_to_cloud import ROOT, atomic, digest, publish

BASE = ROOT / 'hw/soc/out'
STATE = BASE / 'cloud-migration-links-20261013'
TAG = 'cloud-migration-20261012-000'


def record(path, base):
    relative = path.relative_to(base)
    # Reject link ancestors even if they happen to point back inside the scope.
    if any(p.is_symlink() for p in [base, *path.parents[:len(relative.parts)-1]]):
        raise ValueError('Symlink ancestor')
    st = path.lstat()
    kind = 'symlink' if stat.S_ISLNK(st.st_mode) else 'fifo' if stat.S_ISFIFO(st.st_mode) else None
    if kind is None:
        raise ValueError('Only symlinks and FIFOs are in scope')
    return dict(path=relative.as_posix(), kind=kind, mode=stat.S_IMODE(st.st_mode),
                device=st.st_dev, inode=st.st_ino,
                target=os.readlink(path) if kind == 'symlink' else None)


def inventory(base):
    rows = []
    for directory, dirs, files in os.walk(base, followlinks=False):
        parent = Path(directory)
        dirs[:] = [name for name in dirs if not name.startswith('cloud-migration')
                   and name not in ('.git', '.ssh')]
        for name in [*dirs, *files]:
            path = parent / name
            try:
                mode = path.lstat().st_mode
            except FileNotFoundError:
                continue  # Regular-file transfer may finish during inventory.
            if stat.S_ISLNK(mode) or stat.S_ISFIFO(mode):
                rows.append(record(path, base))
        dirs[:] = [name for name in dirs if not (parent / name).is_symlink()]
    return sorted(rows, key=lambda r: r['path'])


def remove_entry(base, expected):
    relative = Path(expected['path'])
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('Unsafe path')
    if relative.parts[0].startswith('cloud-migration') or '.git' in relative.parts or '.ssh' in relative.parts:
        raise ValueError('Protected scope')
    path = base / relative
    try:
        actual = record(path, base)
    except FileNotFoundError:
        return False  # Restart after already removing the exact entry.
    if actual != expected:
        raise ValueError('Entry changed; refusing deletion')
    path.unlink()  # A FIFO is never opened and a symlink target is never visited.
    return True


def main():
    global BASE, STATE, TAG
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--scope', choices=('outputs','tools'), default='outputs')
    args = parser.parse_args()
    if args.scope=='tools':
        tracked=subprocess.check_output(['git','ls-files','-z','--','hw/soc/tools'],cwd=ROOT)
        if tracked:
            raise RuntimeError('Tool scope contains tracked sources; refusing cleanup')
        BASE=ROOT/'hw/soc/tools'
        STATE=ROOT/'hw/soc/out/cloud-migration-tool-links-20261013'
        TAG='cloud-migration-tool-links-20261013'
    STATE.mkdir(parents=True,exist_ok=True)
    plan = STATE / ('tool-links-and-fifos-20261013.json' if args.scope=='tools' else 'output-links-and-fifos-20261013.json')
    if not plan.exists():
        atomic(plan, dict(format=1, base=str(BASE.relative_to(ROOT)), entries=inventory(BASE)))
    rows = json.loads(plan.read_text())['entries']
    if not args.apply:
        print(json.dumps(dict(entries=len(rows), plan=str(plan))))
        return
    receipt = publish(plan, TAG)
    if receipt['sha256'] != digest(plan) or receipt['bytes'] != plan.stat().st_size:
        raise RuntimeError('Missing exact cloud metadata receipt')
    atomic(STATE / 'receipt.json', receipt)
    removed = sum(remove_entry(BASE, row) for row in rows)
    result = dict(status='COMPLETE_RECORDED_LINK_FIFO_CLEANUP', removed_this_run=removed,
                  recorded_entries=len(rows), receipt=receipt,
                  scope='Only recorded '+args.scope+' symlinks/FIFOs. All targets and regular files untouched.')
    atomic(STATE / 'result.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
