# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Only saved-byte controls; preserve actual native RC and its first failure."""
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import threading
import time

C = Path(__file__).resolve().parent
B = C.parent
ROOT = B.parents[3]
O = Path('/dev/shm/nssoc-div4-v7-wire-rc-01')
CHECKER = ROOT / 'hw/soc/flow/check_pcie_clock_div4_v7_v2.py'


def pin(p):
    p = Path(p)
    with p.open('rb') as stream:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def main():
    assert sorted(os.sched_getaffinity(0)) == [10]
    assert not (C / 'result.json').exists() and not (B / 'native-mutations-v2.json').exists()
    freeze = json.loads((C / 'source-freeze.json').read_text())
    assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
    peer = json.loads((C / 'source-only-peer.json').read_text())
    assert peer['status'] == 'PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_RC_SAVED_CONTROLS_V2'
    assert peer['freeze'] == pin(C / 'source-freeze.json') and not peer['findings']
    native = json.loads((B / 'native-execution.json').read_text())
    assert native['status'] == 'FAIL_NATIVE_WIRE_RC_RETAINED'
    assert [(s['name'], s['execution']['returncode']) for s in native['steps']] == [('native', 0), ('audit', 0), ('mutations', 1)]
    assert native['outputs'] == {p: pin(p) for p in native['outputs']}
    audit = json.loads((B / 'native-wire-audit.json').read_text())
    assert audit['status'] == 'PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
    assert (audit['actual_exported_resistors'], audit['actual_exported_capacitors'], audit['geometry_probes']) == (312, 618, 205)
    assert pin(CHECKER)['sha256'] == '24c89628c6d61226344214e077b5fa535c5570e4a7853fbd109e8cb1b1fcd163'
    names = {'require', 'atomic', 'lifecycle', 'limits', 'scratch_bytes',
             'guard_resources', 'execute'}
    selected = [n for n in ast.parse(CHECKER.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(selected) == len(names)
    ns = dict(__file__=str(CHECKER), os=os, Path=Path, resource=resource,
              shutil=shutil, signal=signal, subprocess=subprocess,
              threading=threading, time=time, ast=ast, json=json,
              digest=lambda p: pin(p)['sha256'],
              LIFECYCLE_SOURCE='scripts/characterize_pcie_clock_trim_stream_v2.py',
              LIFECYCLE_SHA='39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886',
              SCRATCH_LIMIT=80 * 1024**2, SHARED_FLOOR=512 * 1024**2,
              ENTRY_FREE=1024**3, LAUNCH_RESERVATION=24 * 1024**2,
              SCRATCH_ROOTS=(B, O), CPU=10)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(CHECKER), 'exec'), ns)
    result = dict(status='RUNNING_SAVED_WIRE_RC_CONTROLS_V2',
                  freeze=pin(C / 'source-freeze.json'), peer=pin(C / 'source-only-peer.json'),
                  native_extraction_repeated=False, native_files_modified=False,
                  failed_first_control_harness_preserved=pin(B / 'native-execution.json'),
                  exact_native_outputs=native['outputs'], full_pex_qualified=False,
                  controller_identity=ns['lifecycle']()['process_identity'](os.getpid()),
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())

    def save():
        ns['atomic'](C / 'result.json', result)

    save()
    try:
        result['execution'] = ns['execute']([
            '/home/hasanmelih/miniconda3/bin/python3', B / 'check_native_mutations_v2.py'], C, 'saved-controls')
        save()
        assert result['execution']['returncode'] == 0
        tests = json.loads((B / 'native-mutations-v2.json').read_text())
        assert tests['status'] == 'PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
        assert len(tests['cases']) == 13
        assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
        assert native['outputs'] == {p: pin(p) for p in native['outputs']}
        result.update(status='PASS_SAVED_NATIVE_BASELINE_AND13_EXACT_RC_CORRUPTION_CONTROLS_V2',
                      controls=pin(B / 'native-mutations-v2.json'))
    except BaseException as error:
        result.update(status='FAIL_SAVED_WIRE_RC_CONTROLS_V2_RETAINED', error=repr(error))
        raise
    finally:
        save()
        try:
            ns['guard_resources']()
        except BaseException as error:
            result.update(status='FAIL_SAVED_WIRE_RC_CONTROLS_V2_RETAINED', error=repr(error))
            save()
            raise
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
