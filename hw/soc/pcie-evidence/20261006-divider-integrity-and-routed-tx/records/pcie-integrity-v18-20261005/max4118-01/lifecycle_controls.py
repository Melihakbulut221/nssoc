# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual isolated descendant/cancellation controls for the frozen wrapper."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

B = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('maximum_owner', B / 'run.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def one(case, directory):
    directory.mkdir()
    m.W = directory
    m.subreaper()
    owner = m.life.ProcessOwner(directory / 'owner.json')
    result = dict(case=case, source=m.pin(B / 'run.py'))
    try:
        with owner:
            if case == 'healthy':
                p = owner.launch('native', [sys.executable, '-c', 'print("healthy")'])
                assert owner.wait(p) == 0
                owner.check()
                m.guard()
            elif case == 'complete_signal':
                p = owner.launch('native', ['/bin/true'])
                assert owner.wait(p) == 0
                os.kill(os.getpid(), signal.SIGTERM)
                owner.check()
            else:
                ready = directory / 'ready.json'
                child = 'import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(300)'
                launcher = ('import subprocess,sys,time,json,signal;from pathlib import Path;'
                            'signal.signal(signal.SIGTERM,signal.SIG_IGN);'
                            f'p=subprocess.Popen([sys.executable,"-c",{child!r}],start_new_session=True);'
                            f'Path({str(ready)!r}).write_text(json.dumps(dict(child=p.pid)));time.sleep(300)')
                p = owner.launch('native', [sys.executable, '-c', launcher])
                deadline = time.monotonic() + 10
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                assert ready.exists()
                time.sleep(0.1)
                assert len([r for r in m.descendants() if r['state'] != 'Z']) == 2
                try:
                    if case == 'resource':
                        with (directory / 'sparse-cap-witness').open('wb') as f:
                            f.truncate(2 * 1024**3 + 1)
                        m.guard()
                    else:
                        os.kill(os.getpid(), signal.SIGTERM)
                        owner.check()
                except BaseException:
                    result['tree_cleanup'] = m.cleanup_tree()
                    raise
        owner.check()
    except (AssertionError, m.life.Cancelled) as error:
        result['expected_error'] = repr(error)
    result['remaining'] = m.descendants()
    assert not any(r['state'] != 'Z' for r in result['remaining'])
    if case == 'healthy':
        assert 'expected_error' not in result
    elif case == 'resource':
        assert 'own capture ceiling' in result['expected_error']
    else:
        assert 'Parent received SIGTERM' in result['expected_error']
    if case in ('resource', 'cancel_tree'):
        assert len(result['tree_cleanup']['before']) == 2
        assert len({r['process_group'] for r in result['tree_cleanup']['before']}) == 2
    witness = directory / 'sparse-cap-witness'
    if witness.exists():
        result['sparse_cap_witness_size'] = witness.stat().st_size
        witness.unlink()  # Only this declared zero-block harness witness.
    result['status'] = 'PASS_ACTUAL_LIFECYCLE_CONTROL'
    (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    if len(sys.argv) == 3:
        one(sys.argv[1], Path(sys.argv[2]))
    else:
        root = Path('/dev/shm/nssoc-integrity-v18-max4118-lifecycle01')
        root.mkdir()
        rows = []
        for case in ['healthy', 'resource', 'cancel_tree', 'complete_signal']:
            with (root / (case + '.log')).open('x') as log:
                code = subprocess.call([sys.executable, __file__, case, str(root / case)],
                                       stdout=log, stderr=subprocess.STDOUT)
            assert code == 0, (case, code)
            rows.append(json.loads((root / case / 'result.json').read_text()))
        (B / 'lifecycle-controls.json').write_text(json.dumps(dict(
            status='PASS_FOUR_ACTUAL_LIFECYCLE_CONTROLS', source=m.pin(B / 'run.py'),
            method=m.pin(__file__), rows=rows,
            raw_files={str(p): m.pin(p) for p in root.rglob('*') if p.is_file()}), indent=2) + '\n')
        print('PASS', len(rows))
