# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Owned unsimplified native extraction and geometry; no comparison/RC/SPICE run."""
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

B = Path(__file__).resolve().parent
ROOT = B.parents[3]
W = Path('/dev/shm/nssoc-div4-v7-wire-geometry-04')
G = Path('/dev/shm/nssoc-div4-v7-layout-01')
C = Path('/dev/shm/nssoc-div4-v7-checks-02')
N = Path('/dev/shm/nssoc-div4-v7-wire-native-02')
A = ROOT / 'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
CHECKER = ROOT / 'hw/soc/flow/check_pcie_clock_div4_v7_v2.py'
CHECKER_SHA = '24c89628c6d61226344214e077b5fa535c5570e4a7853fbd109e8cb1b1fcd163'
NAMES = ['probe_native_cells', 'probe_device_locations', 'probe_wire_components',
         'probe_terminal_anchors', 'prepare_anchors', 'bind_source_ids']


def pin(path):
    with Path(path).open('rb') as stream:
        return dict(bytes=Path(path).stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def main():
    assert sorted(os.sched_getaffinity(0)) == [10]
    assert not W.exists() and not N.exists()
    assert not (B / 'geometry-execution.json').exists()
    freeze = json.loads((B / 'geometry-source-freeze.json').read_text())
    assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
    peer = json.loads((B / 'geometry-source-only-peer.json').read_text())
    assert peer['status'] == 'PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_GEOMETRY'
    assert peer['freeze'] == pin(B / 'geometry-source-freeze.json')
    assert not peer['findings']
    assert pin(CHECKER)['sha256'] == CHECKER_SHA
    # Clone exact already-controlled functions into a private namespace. New
    # scratch roots only; original checker globals and old files are untouched.
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
              SCRATCH_ROOTS=(B, W, N), CPU=10)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(CHECKER), 'exec'), ns)
    identity = ns['lifecycle']()['process_identity'](os.getpid())
    record = dict(status='RUNNING_UNSIMPLIFIED_DIVIDER_V7_GEOMETRY',
                  controller_identity=identity,
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  freeze=pin(B / 'geometry-source-freeze.json'),
                  peer=pin(B / 'geometry-source-only-peer.json'),
                  inputs=freeze['inputs'], steps=[],
                  inherited_exact_function_ASTs=sorted(names),
                  resource_contract=dict(cpu=10, native_AS=2 * 1024**3,
                                         own_scratch=80 * 1024**2,
                                         reserve=24 * 1024**2, entry=1024**3,
                                         continuous=512 * 1024**2,
                                         healthy_elapsed_watchdog_seconds=None,
                                         failure_cleanup_grace_seconds=5),
                  rc_extraction_executed=False, native_device_extraction_executed=False, qualified_pex=False,
                  main_chip_integrated=False)

    def save():
        ns['atomic'](B / 'geometry-execution.json', record)

    save()
    try:
        N.mkdir()
        deck = B / 'native_unsimplified.lvs'
        command = [A, 'klayout', '-b', '-zz', '-r', deck]
        options = dict(input=G / 'nssoc_clock_div4_v7_layout.gds',
                       topcell='nssoc_clock_div4_v7_layout', log=N / 'deck.log',
                       run_mode='flat', native_l2n=N / 'result.l2n',
                       target_netlist=N / 'extracted.cir', thr=1,
                       net_only='True', no_simplify='True', top_lvl_pins='True',
                       combine_devices='False', purge='False', purge_nets='False',
                       purge_devices='False', disable_tap_extraction='False')
        for key, value in options.items():
            command += ['-rd', f'{key}={value}']
        execution = ns['execute'](command, B, 'native_unsimplified_extraction')
        record['steps'].append(dict(name='native_unsimplified_extraction', options={k: str(v) for k, v in options.items()}, execution=execution))
        save()
        assert execution['returncode'] == 0
        log = (N / 'deck.log').read_text()
        assert 'NET_ONLY enabled: apply extraction netlist options and skip comparison.' in log
        for name in ['simplify', 'combine_devices', 'purge', 'purge_nets', 'purge_devices']:
            assert f'[layout_netlist] {name}: SKIPPED' in log
        assert '[layout_netlist] make_top_level_pins: ENABLED' in log
        assert 'ERROR' not in log and 'Error:' not in log
        assert 'NSSOC_UNSIMPLIFIED_GEOMETRY_L2N_EXPORT_REQUESTED' in log
        assert (N / 'result.l2n').is_file() and (N / 'extracted.cir').is_file()
        record['native_device_extraction_executed'] = True
        record['native_comparison_executed'] = False
        assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
        save()
        for name in NAMES:
            assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
            execution = ns['execute']([A, 'python', B / (name + '.py')], B, name)
            record['steps'].append(dict(name=name, execution=execution))
            save()
            assert execution['returncode'] == 0, name
            assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
        record['status'] = 'PASS_DIVIDER_V7_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
        record['outputs'] = {str(p): pin(p) for p in [
            *(B / n for n in ['native-pcell-inventory.json', 'device-location-geometry.json',
                             'wire-component-geometry.json', 'terminal-reference-planes.json',
                             'anchors.json', 'source-native-bijection.json']),
            *(p for directory in (W, N) for p in directory.rglob('*') if p.is_file())]}
        ns['guard_resources']()
    except BaseException as error:
        record.update(status='FAIL_GEOMETRY_RETAINED', error=repr(error))
        raise
    finally:
        save()
    print(record['status'], flush=True)


if __name__ == '__main__':
    main()
