# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind actual RX13 proof execution to exact native-expanded graphs and kernels."""
import ast
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import shutil

B = Path(__file__).resolve().parent
E = Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-equivalence')
NET = Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-13/repaired.v')
EXPECTED_NET = {'bytes': 2093617, 'sha256': '533ecba38bc02e0f08cf96e9aef1e71682141de26dd772bc965abe9619c6ab34'}
KINDS = ['invert_D', 'invert_clock', 'invert_reset', 'invert_output', 'missing_state', 'unknown_function', 'unknown_output', 'undriven_reset', 'duplicate_driver', 'changed_port_census']


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


def load(p):
    return json.loads(Path(p).read_text())


def graph_pins(directory=E):
    normalization = load(directory / 'normalization.json')
    assert normalization['inputs'][str(NET)] == EXPECTED_NET == pin(NET)
    assert normalization['inputs'] == {p: pin(p) for p in normalization['inputs']}
    answer = {}
    assert [r['name'] for r in normalization['runs']] == ['gold', 'gate']
    for row in normalization['runs']:
        assert row['returncode'] == 0
        name = row['name']
        assert pin(directory / (name + '.ys'))['sha256'] == row['script_sha256']
        assert pin(directory / (name + '.log'))['sha256'] == row['log_sha256']
        p = directory / (name + '.json.gz')
        assert pin(p)['sha256'] == row['expanded_json']['lossless_gzip_sha256']
        digest = hashlib.sha256()
        size = 0
        with gzip.open(p, 'rb') as f:
            while data := f.read(1024**2):
                digest.update(data)
                size += len(data)
        actual = {'bytes': size, 'sha256': digest.hexdigest()}
        assert actual == {k: row['expanded_json'][k] for k in ('bytes', 'sha256')}
        answer[name] = {'compressed': pin(p), 'expanded': actual}
    return answer


def input_paths(directory=E):
    return [Path(__file__), B / 'eco-proof/compare.py', B / 'eco-proof/mutations.py', B / 'postroute_repair13.py', NET, directory / 'normalization.json', *(directory / (name + suffix) for name in ('gold', 'gate') for suffix in ('.json.gz', '.ys', '.log'))]


def verify_binding(directory=E):
    record = load(directory / 'proof-execution-binding.json')
    assert record['status'] == 'PASS_ACTUAL_RX13_PROOF_AND_MUTATION_EXECUTION_BOUND'
    assert record['before_inputs'] == record['after_inputs'] == {str(p): pin(p) for p in input_paths(directory)}
    assert record['expanded_graphs_before'] == record['expanded_graphs_after'] == graph_pins(directory)
    assert record['outputs'] == {name: pin(directory / name) for name in ('equivalence.json', 'mutation-controls.json', 'bound-compare.log', 'bound-mutations.log')}
    assert record['runtime_before'] == record['runtime_after']
    assert record['runtime_before']['pin'] == pin(record['runtime_before']['path'])
    assert [(x['method'], x['returncode']) for x in record['runs']] == [('compare.py', 0), ('mutations.py', 0)]
    for row in record['runs']:
        assert row['command'][0] == record['runtime_before']['path']
        assert row['command'][1:] == [str(B / 'eco-proof' / row['method'])]
    eq = load(directory / 'equivalence.json')
    assert eq['status'] == 'PASS_COMPLETE_STATE_TRANSITION_AND_OUTPUT_FUNCTION_EQUALITY'
    assert eq['states'] == 1804 and eq['matched'] == eq['targets'] == 5443 and not eq['mismatches']
    faults = load(directory / 'mutation-controls.json')
    assert faults['status'] == 'PASS_TEN_MEANINGFUL_EQUIVALENCE_KERNEL_CONTROLS'
    assert faults['positive']['matched'] == faults['positive']['targets'] == 5443 and not faults['positive']['mismatches']
    assert [c['kind'] for c in faults['controls']] == KINDS
    assert all(c['status'].startswith('REJECTED_') for c in faults['controls'])
    return record


def run():
    assert not (E / 'proof-execution-binding.json').exists()
    record = {'status': 'RUNNING_BOUND_RX13_PROOF', 'before_inputs': {str(p): pin(p) for p in input_paths()}, 'expanded_graphs_before': graph_pins(), 'runtime_before': {'path': sys.executable, 'pin': pin(sys.executable)}, 'runs': [], 'scope': 'Same canonical binary kernel and ten actual kernel faults; exact completed native-expanded graphs and all methods pinned before/after. No new normalization or physical timing claim.'}
    tree = ast.parse((B / 'postroute_repair13.py').read_text())
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'stop_failed_group')
    ns = {'os': os, 'signal': signal, 'time': time}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), str(B / 'postroute_repair13.py'), 'exec'), ns)

    def stop_signal(number, frame):
        raise InterruptedError(f'Parent signal {number}')

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT, signal.SIGTERM})

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, stop_signal)
    try:
        for method, logname in [('compare.py', 'bound-compare.log'), ('mutations.py', 'bound-mutations.log')]:
            command = [sys.executable, str(B / 'eco-proof' / method)]
            process = None
            complete = False
            with (E / logname).open('x') as log:
                try:
                    old = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
                    try:
                        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'NSSOC_EQUIVALENCE_CAPTURE': str(E)}, start_new_session=True, preexec_fn=limits)
                    finally:
                        signal.pthread_sigmask(signal.SIG_SETMASK, old)
                    while process.poll() is None:
                        if shutil.disk_usage('/dev/shm').free < 528 * 1024**2:
                            raise RuntimeError('Shared scratch floor')
                        time.sleep(.25)
                    code = process.wait()
                    record['runs'].append({'method': method, 'command': command, 'returncode': code})
                    assert code == 0
                    complete = True
                finally:
                    if process is not None and not complete:
                        ns['stop_failed_group'](process)
        record['after_inputs'] = {str(p): pin(p) for p in input_paths()}
        record['expanded_graphs_after'] = graph_pins()
        assert record['before_inputs'] == record['after_inputs'] and record['expanded_graphs_before'] == record['expanded_graphs_after']
        record['outputs'] = {name: pin(E / name) for name in ('equivalence.json', 'mutation-controls.json', 'bound-compare.log', 'bound-mutations.log')}
        record['runtime_after'] = {'path': sys.executable, 'pin': pin(sys.executable)}
        record['status'] = 'PASS_ACTUAL_RX13_PROOF_AND_MUTATION_EXECUTION_BOUND'
    except BaseException as error:
        record.update(status='FAIL_PROOF_BINDING_RETAINED', error=repr(error))
        raise
    finally:
        (E / 'proof-execution-binding.json').write_text(json.dumps(record, indent=2) + '\n')
    verify_binding()
    print(record['status'])


if __name__ == '__main__':
    run()
