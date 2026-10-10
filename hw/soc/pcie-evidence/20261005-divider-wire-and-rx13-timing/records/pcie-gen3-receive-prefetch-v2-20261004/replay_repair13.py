# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive exact proof-binding gate; unchanged RX13 six ports and runtime."""
import ast
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time

assert sys.version_info[:2] == (3, 12), 'Exact cocotb runtime requires Python3.12'
R = Path.cwd()
B = Path(__file__).resolve().parent
E = Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-equivalence')
OUT = Path('/dev/shm/nssoc-rx-prefetch-v2-repair13-physical-replay-01')
NET = Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-13/repaired.v')
MODEL = Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v')
TOOLS = R / 'hw/soc/tools/oss-cad-suite/bin'
DRIVER = R / 'scripts/check_pcie_gen3_receive.py'
sys.path.insert(0, str(R / 'scripts'))


def pin(path):
    with path.open('rb') as f:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


def interrupted(number, frame):
    raise InterruptedError(f'Parent signal {number}')


for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, interrupted)
assert not OUT.exists()
proof = json.loads((E / 'equivalence.json').read_text())
assert proof['status'] == 'PASS_COMPLETE_STATE_TRANSITION_AND_OUTPUT_FUNCTION_EQUALITY'
assert proof['states'] == 1804 and proof['matched'] == proof['targets'] == 5443 and not proof['mismatches']
controls = json.loads((E / 'mutation-controls.json').read_text())
assert len(controls['controls']) == 10 and all(c['status'].startswith('REJECTED_') for c in controls['controls'])
normalization = json.loads((E / 'normalization.json').read_text())
assert pin(NET) == normalization['inputs'][str(NET)] == {'bytes': 2093617, 'sha256': '533ecba38bc02e0f08cf96e9aef1e71682141de26dd772bc965abe9619c6ab34'}
gate_spec = importlib.util.spec_from_file_location('rx13_proof_gate', B / 'proof_gate_repair13.py')
gate = importlib.util.module_from_spec(gate_spec)
gate_spec.loader.exec_module(gate)
binding = gate.verify_binding()
dependencies = [Path(__file__), B / 'proof_gate_repair13.py', E / 'proof-execution-binding.json', *gate.input_paths(), DRIVER, B / 'postroute_repair13.py', B / 'normalize_repair13.py', NET, MODEL, E / 'normalization.json', E / 'equivalence.json', E / 'mutation-controls.json']
before = {str(p): pin(p) for p in dependencies}
while shutil.disk_usage('/dev/shm').free < 1024**3:
    time.sleep(5)
record = {'status': 'RUNNING_EXACT_PROVED_NETLIST_PORT_REPLAY', 'inputs': before, 'entry_free_bytes': shutil.disk_usage('/dev/shm').free, 'elapsed_watchdog_seconds': None, 'address_space_limit_bytes': 2 * 1024**3, 'single_cpu': True, 'scope': 'Existing unchanged six-case native receive oracle/model on provedRX13; only command lifecycle/resource runner replaced. No SDF, LCRC, physical/fullPHY acceptance.'}


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})


# Reuse the exact tested helper body without executing the GRT producer.
tree = ast.parse((B / 'postroute_repair13.py').read_text())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'stop_failed_group')
helper_namespace = {'os': os, 'signal': signal, 'time': time}
exec(compile(ast.Module(body=[fn], type_ignores=[]), str(B / 'postroute_repair13.py'), 'exec'), helper_namespace)
stop_failed_group = helper_namespace['stop_failed_group']


def owned_execute(command, log_path, environment, timeout):
    assert timeout is None
    process = None
    complete = False
    record['minimum_shared_free_bytes'] = shutil.disk_usage('/dev/shm').free
    with log_path.open('x') as log:
        try:
            old = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM, signal.SIGINT})
            try:
                process = subprocess.Popen(command, cwd=log_path.parent, env=environment, stdout=log, stderr=subprocess.STDOUT, preexec_fn=limits, start_new_session=True)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, old)
            record['pid'] = process.pid
            while process.poll() is None:
                free = shutil.disk_usage('/dev/shm').free
                record['minimum_shared_free_bytes'] = min(record['minimum_shared_free_bytes'], free)
                if free < 528 * 1024**2:
                    raise RuntimeError('Shared scratch floor')
                time.sleep(.25)
            code = process.wait()
            if code != 0:
                raise RuntimeError(f'Native compile/simulation exit {code}')
            complete = True
            return code
        finally:
            if process is not None and not complete:
                stop_failed_group(process)


try:
    spec = importlib.util.spec_from_file_location('rx13_port_oracle', DRIVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.execute_command = owned_execute
    sys.argv = [str(DRIVER), '--out', str(OUT), '--iverilog-dir', str(TOOLS), '--netlist', str(NET), '--models', str(MODEL)]
    assert module.main() == 0
    result = json.loads((OUT / 'result.json').read_text())
    assert result['tests'] == {'passed': 6, 'failed': 0, 'skipped': 0}
    assert before == {str(p): pin(p) for p in dependencies}
    assert gate.verify_binding() == binding
    # Only a terminal program is compressed; every original byte is read back.
    raw = OUT / 'sim/sim.vvp'
    original = pin(raw)
    zipped = raw.with_suffix('.vvp.gz')
    with raw.open('rb') as source, gzip.open(zipped, 'xb', compresslevel=1) as dest:
        shutil.copyfileobj(source, dest)
    with gzip.open(zipped, 'rb') as stream:
        digest = hashlib.sha256()
        count = 0
        while data := stream.read(1024**2):
            count += len(data)
            digest.update(data)
    assert {'bytes': count, 'sha256': digest.hexdigest()} == original
    record['lossless_closed_program'] = {'raw': original, 'gzip': pin(zipped), 'full_decompressed_readback': original}
    assert pin(raw) == original
    raw.unlink()
    record['status'] = 'PASS_EXACT_PROVED_RX13_SIX_NATIVE_PORT_CASES'
except BaseException as error:
    record.update(status='FAILED_RETAINED', error=repr(error))
    raise
finally:
    target = OUT / 'owned-driver.json' if OUT.exists() else B / 'repair13-source/port-prelaunch-failure.json'
    target.write_text(json.dumps(record, indent=2) + '\n')
