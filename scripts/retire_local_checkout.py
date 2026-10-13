#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Retire the exact local NSSOC checkout after cloud handoff, without data loss.

This is an explicitly destructive transfer tool, not a CAD or test launcher.
It preserves the complete checkout, including all Git objects and controller
state, in hash-verified release archives and manifests before unlinking files.
The empty workspace directory remains usable by the desktop task.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

import migrate_cloud_transients as transfer
from migrate_outputs_to_cloud import ROOT, atomic, digest, publish

STATE = Path('/tmp/nssoc-final-checkout-20261013')
TAG = 'cloud-migration-final-checkout-20261013'
LIMIT = 256 * 1024 * 1024


def allowed(path):
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        return False
    return (bool(relative.parts) and '..' not in relative.parts
            and not ROOT.is_symlink()
            and not any(p.is_symlink() for p in path.parents if p.is_relative_to(ROOT)))


def ready(root):
    state = root / 'hw/soc/out'
    for family in ('20261012', 'pnr-20261013', 'tools-20261013'):
        r = json.loads((state / ('cloud-migration-' + family) / 'transfer-progress.json').read_text())
        if r['status'] != 'COMPLETE_SELECTED_REGULAR_OUTPUT_FILES':
            raise RuntimeError('Transfer not complete: ' + family)
    r = json.loads((state / 'cloud-migration-transients-20261013/progress.json').read_text())
    if r['status'] != 'COMPLETE_REMOTE_READBACK_AND_LOCAL_CLEANUP':
        raise RuntimeError('Transient cleanup not complete')
    r = json.loads((state / 'cloud-migration-finalization-20261013/state.json').read_text())
    if r.get('status') not in ('FINAL_HOSTED_RECONSTRUCTION_RUNNING', 'PASS_FINAL_HOSTED_RECONSTRUCTION') or not r.get('run_id'):
        raise RuntimeError('Final hosted reconstruction not dispatched successfully')
    return r


def main():
    STATE.mkdir(exist_ok=True)
    transfer.allowed = allowed
    planpath = STATE / 'checkout-inventory.json'
    if not planpath.exists():
        handoff = ready(ROOT)
        for unit in ('nssoc-cloud-output-transfer-20261012', 'nssoc-cloud-transients-20261013', 'nssoc-cloud-migration-finalize-20261013'):
            active = subprocess.run(['systemctl', '--user', 'is-active', '--quiet', unit])
            if active.returncode == 0:
                raise RuntimeError('Stop completed transfer/controller before freezing checkout: ' + unit)
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
            raise RuntimeError('Uncommitted sources must be pushed first')
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/heads/codex/complete-open-work'], cwd=ROOT, text=True).split()[0]
        if head != remote:
            raise RuntimeError('Local HEAD differs from published branch')
        # Keep a small restart controller outside the soon-to-be-empty checkout.
        # Its copies are also published before deletion and removed on success.
        runtime = STATE / 'runtime'
        runtime.mkdir(exist_ok=True)
        for name in ('retire_local_checkout.py', 'migrate_cloud_transients.py', 'migrate_outputs_to_cloud.py', 'cloud_archive_readback.py'):
            shutil.copyfile(ROOT / 'scripts' / name, runtime / name)
            publish(runtime / name, TAG)
        launcher = STATE / 'resume.py'
        launcher.write_text('import json,sys\nfrom pathlib import Path\n'
                            'base=Path(__file__).resolve().parent\n'
                            'sys.path.insert(0,str(base/"runtime"))\n'
                            'import retire_local_checkout as controller\n'
                            'controller.ROOT=Path(json.loads((base/"checkout-inventory.json").read_text())["root"])\n'
                            'controller.main()\n')
        publish(launcher, TAG)
        rows = []
        for directory, dirs, files in os.walk(ROOT, followlinks=False):
            rows += [transfer.record(Path(directory) / n) for n in files]
            rows += [transfer.record(Path(directory) / n) for n in dirs if (Path(directory) / n).is_symlink()]
        rows.sort(key=lambda r: r['path'])
        if any(r.get('bytes', 0) > 1800 * 1024 * 1024 for r in rows):
            raise RuntimeError('Unexpected oversized file; requires explicit chunking')
        atomic(planpath, dict(head=head, root=str(ROOT), hosted_reconstruction=handoff, entries=rows))
    plan = json.loads(planpath.read_text())
    if plan['root'] != str(ROOT):
        raise RuntimeError('Inventory belongs to a different checkout')
    inventory_receipt = publish(planpath, TAG)
    batches = []
    current = []
    size = 0
    for row in plan['entries']:
        if current and size + row.get('bytes', 0) > LIMIT:
            batches.append(current)
            current, size = [], 0
        current.append(row)
        size += row.get('bytes', 0)
    if current:
        batches.append(current)
    statefile = STATE / 'retirement-progress.json'
    state = json.loads(statefile.read_text()) if statefile.exists() else dict(status='RUNNING', batches=[], inventory=inventory_receipt)
    # Reuse the same independently tested, per-manifest hosted deletion gate.
    from concurrent.futures import ThreadPoolExecutor
    transfer.STATE, transfer.TAG = STATE, TAG
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = [(i, pool.submit(transfer.transfer_batch, i, rows, 'checkout'))
                   for i, rows in enumerate(batches) if i >= len(state['batches'])]
        for i, future in pending:
            state['batches'].append(future.result())
            atomic(statefile, state)
            print(json.dumps(dict(batch=i, total_batches=len(batches))), flush=True)
    for directory, dirs, files in os.walk(ROOT, topdown=False, followlinks=False):
        if Path(directory) == ROOT:
            continue
        try:
            Path(directory).rmdir()
        except OSError:
            pass  # New or changed files are never recursively erased.
    if list(ROOT.iterdir()):
        raise RuntimeError('Checkout contains new or changed entries; preserve and inspect')
    state.update(status='COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE', source_head=plan['head'], hosted_reconstruction_run=plan['hosted_reconstruction']['run_id'], logical_bytes=sum(r.get('bytes', 0) for r in plan['entries']))
    atomic(statefile, state)
    final_receipt = publish(statefile, TAG)
    print(json.dumps(dict(status=state['status'], receipt=final_receipt)), flush=True)
    # This directory contains only this controller's disposable transfer copies;
    # the final report and complete reconstruction manifests are already remote.
    shutil.rmtree(STATE)


if __name__ == '__main__':
    main()
