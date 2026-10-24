#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""After all selected local transfers finish, run final reconstruction on GitHub only.

This controller performs transfer metadata packaging and API orchestration only.
It never runs CAD/tests locally or deletes files. Its durable request identifier
allows recovery of the same hosted run after a controller or computer restart.
"""
import fcntl
import json
from pathlib import Path
import subprocess
import tarfile
import time

from migrate_outputs_to_cloud import ROOT, atomic, publish

REPO = 'Melihakbulut221/nssoc'
BRANCH = 'codex/complete-open-work'
TAG = 'cloud-migration-finalization-20261013'
STATES = [ROOT / 'hw/soc/out/cloud-migration-20261012',
          ROOT / 'hw/soc/out/cloud-migration-pnr-20261013',
          ROOT / 'hw/soc/out/cloud-migration-tools-20261013']
DIRECTORY = ROOT / 'hw/soc/out/cloud-migration-finalization-20261013'
REQUEST = 'final-migration-20261013'
COMPLETE = 'COMPLETE_SELECTED_REGULAR_OUTPUT_FILES'


def snapshot():
    result = {}
    for state in STATES:
        path = state / 'transfer-progress.json'
        result[state.name] = json.loads(path.read_text()) if path.exists() else {}
    return result


def transfers_complete(states):
    return (set(states) == {p.name for p in STATES}
            and all(p.get('status') == COMPLETE for p in states.values()))


def find_run():
    rows = json.loads(subprocess.check_output([
        'gh', 'run', 'list', '-R', REPO, '--workflow', 'cloud-output-restore.yml',
        '--branch', BRANCH, '--event', 'workflow_dispatch', '--limit', '100',
        '--json', 'databaseId,displayTitle'], text=True))
    found = [r['databaseId'] for r in rows
             if r['displayTitle'] == 'cloud-output-restore ' + REQUEST]
    if len(found) > 1:
        raise RuntimeError('Ambiguous final reconstruction request: ' + str(found))
    return found[0] if found else None


def main():
    DIRECTORY.mkdir(exist_ok=True)
    with (DIRECTORY / 'controller.lock').open('w') as lock:
        # A persistent user service and a manually resumed controller must not race.
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        statefile = DIRECTORY / 'state.json'
        state = json.loads(statefile.read_text()) if statefile.exists() else {}
        if state.get('status') in ('PASS_FINAL_HOSTED_RECONSTRUCTION', 'FAIL_FINAL_HOSTED_RECONSTRUCTION'):
            return
        while not transfers_complete(current := snapshot()):
            state.update(status='WAITING_ALL_TRANSFERS', transfers=current)
            atomic(statefile, state)
            time.sleep(60)
        state.update(transfers=current, request_id=REQUEST)
        if 'transfer_metadata_archive' not in state:
            archive = DIRECTORY / 'cloud-final-transfer-metadata-20261013.tar.gz'
            if not archive.exists():
                temporary = archive.with_suffix('.tmp')
                with tarfile.open(temporary, 'w:gz') as packed:
                    for directory in STATES:
                        for path in sorted(directory.iterdir()):
                            if path.is_file() and not path.is_symlink() and path.suffix in ('.json', '.jsonl'):
                                packed.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
                temporary.replace(archive)
            state['transfer_metadata_archive'] = publish(archive, TAG)
            atomic(statefile, state)
        run = state.get('run_id') or find_run()
        if not run:
            # An uncertain API result is recovered by title; never blindly repeat.
            if state.get('dispatch_attempted'):
                raise RuntimeError('Dispatch attempted but run not discoverable; inspect request before retry')
            state.update(status='DISPATCHING_FINAL_HOSTED_RECONSTRUCTION', dispatch_attempted=True)
            atomic(statefile, state)
            subprocess.run(['gh', 'workflow', 'run', 'cloud-output-restore.yml', '-R', REPO,
                            '--ref', BRANCH, '-f', 'archive_scope=all', '-f', 'request_id=' + REQUEST], check=True)
            for _ in range(12):
                time.sleep(10)
                run = find_run()
                if run:
                    break
            if not run:
                raise RuntimeError('Final hosted run not yet discoverable')
        state.update(status='FINAL_HOSTED_RECONSTRUCTION_RUNNING', run_id=run,
                     url=f'https://github.com/{REPO}/actions/runs/{run}')
        atomic(statefile, state)
        while True:
            result = json.loads(subprocess.check_output([
                'gh', 'run', 'view', str(run), '-R', REPO,
                '--json', 'status,conclusion,headSha,jobs'], text=True))
            if result['status'] == 'completed':
                break
            time.sleep(60)
        state['hosted_result'] = result
        state['status'] = ('PASS_FINAL_HOSTED_RECONSTRUCTION' if result['conclusion'] == 'success'
                           else 'FAIL_FINAL_HOSTED_RECONSTRUCTION')
        report = DIRECTORY / f'cloud-final-migration-{run}.json'
        atomic(report, state)
        state['published_final_report'] = publish(report, TAG)
        atomic(statefile, state)
        print(json.dumps(state), flush=True)


if __name__ == '__main__':
    main()
