# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hash-check exact peer-reviewed work, checkpoint identity, exec the owner.

No nested supervisor, healthy timeout, native measurement or archive mutation.
The checker retains this PID/birth/group and owns each child through its pinned
ProcessOwner. Its ongoing physical artifacts remain in declared fresh RAM roots.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys

ROOT = Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'launch-manifest02.json'
CHECKPOINT = HERE / 'identity-checkpoint02.json'


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


def main():
    if CHECKPOINT.exists():
        raise ValueError('Fresh launch identity checkpoint required')
    manifest = json.loads(MANIFEST.read_text())
    if manifest['inputs'] != {p: pin(p) for p in manifest['inputs']}:
        raise ValueError('All frozen source, review, runtime, PCell and deck bytes must match')
    peer = json.loads(Path(manifest['source_peer']).read_text())
    if (peer['status'] != 'PASS_SOURCE_ONLY_DIVIDER_V7_NATIVE_SCHEMA_V2'
            or peer.get('findings') != []
            or peer.get('source_pins') != manifest['product_sources']
            or peer.get('launcher') != pin(Path(__file__))):
        raise ValueError('Exact current independent source peer must pass without findings before native launch')
    roots = [Path(manifest[n]) for n in ('layout', 'checks')]
    if (not roots[0].is_dir() or roots[1].exists()
            or any(p.parent != Path('/dev/shm') or not p.name.startswith('nssoc-div4-v7-') for p in roots)):
        raise ValueError('Exact existing generated layout and fresh checker root required')
    layout_files = {str(p.relative_to(roots[0])): pin(p) for p in roots[0].rglob('*') if p.is_file()}
    if layout_files != manifest['layout_files']:
        raise ValueError('Every existing generated layout byte must remain exact')
    if sorted(os.sched_getaffinity(0)) != [10] or shutil.disk_usage('/dev/shm').free < 1024**3:
        raise ValueError('CPU10 and1GiB launch resource floor required')
    checker = ROOT / 'hw/soc/flow/check_pcie_clock_div4_v7_v2.py'
    argv = [manifest['python'], str(checker), '--pdk', manifest['pdk'],
            '--layout', manifest['layout'], '--out', manifest['checks']]
    fields = Path('/proc', str(os.getpid()), 'stat').read_text().rsplit(') ', 1)[1].split()
    identity = dict(pid=os.getpid(), process_group=int(fields[2]), start_ticks=fields[19])
    record = dict(status='IDENTITY_CHECKPOINT_BEFORE_EXEC_OWNED_PHYSICAL_CONTROLLER',
                  manifest=pin(MANIFEST), identity=identity, command=argv,
                  source_peer=pin(Path(manifest['source_peer'])),
                  source_pins=manifest['inputs'], native_roots=list(map(str, roots)),
                  native_terminal_receipt=str(roots[1] / 'result.json'),
                  native_owned_receipts_glob=str(roots[1] / '**/*.owned.json'),
                  healthy_elapsed_watchdog=None, physical_acceptance=False,
                  shutdown='Signal only this exact live PID/start_ticks with SIGTERM; checker closes its current owned group with5s failure grace. Preserve unique declared RAM roots before reboot.')
    with CHECKPOINT.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    # Exec preserves the recorded birth identity and the detached session.
    environment = {k: v for k, v in os.environ.items() if k not in ('GH_TOKEN', 'GITHUB_TOKEN', 'PYTHONPATH', 'PYTHONHOME')}
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    os.chdir(ROOT)
    os.execve(manifest['python'], argv, environment)


if __name__ == '__main__':
    main()
