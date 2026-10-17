# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh native wire-only RC with exact geometry gates and owned lifecycle."""
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
GEOMETRY = B.parent / 'pcie-divider-v7-compact-v2-wire-v1-20261006'
O = Path('/dev/shm/nssoc-div4-v7-compact-v2-wire-rc-01')
W = Path('/dev/shm/nssoc-div4-v7-compact-v2-wire-geometry-01/wires.gds')
RT = Path('/dev/shm/nssoc-magic-area-product-v4-build/runtime/lib')
TECH = Path('/dev/shm/nssoc-magic-pad-stack-tech-v1')
PRIOR = B.parent / 'pcie-vco-v6-local-v1-wire-20261005/run_native_rc.py'
CHECKER = ROOT / 'hw/soc/flow/check_pcie_clock_div4_v7_v2.py'
AUDIT_PYTHON = Path('/home/hasanmelih/miniconda3/bin/python3')


def pin(p):
    p = Path(p)
    with p.open('rb') as stream:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def main():
    assert sorted(os.sched_getaffinity(0)) == [10]
    assert not O.exists() and not (B / 'native-execution.json').exists()
    freeze = json.loads((B / 'source-freeze.json').read_text())
    assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
    peer = json.loads((B / 'source-only-peer.json').read_text())
    assert peer['status'] == 'PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_RC'
    assert peer['freeze'] == pin(B / 'source-freeze.json') and not peer['findings']
    geometry = json.loads((GEOMETRY / 'geometry-execution.json').read_text())
    assert geometry['status'] == 'PASS_DIVIDER_V7_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
    assert geometry['outputs'] == {p: pin(p) for p in geometry['outputs']}
    controls = json.loads((GEOMETRY / 'binding-controls01/result.json').read_text())
    assert controls['status'] == 'PASS_BASELINE_AND_FOUR_ACTUAL_COPIED_INPUT_BINDING_CONTROLS'
    saved_peer = json.loads((GEOMETRY / 'saved-geometry-peer.json').read_text())
    assert saved_peer['status'] == 'PASS_DIVIDER_V7_SAVED_GEOMETRY_AND_BINDING_CONTROLS'
    assert not saved_peer['findings']
    assert saved_peer['geometry_execution'] == pin(GEOMETRY / 'geometry-execution.json')
    assert saved_peer['binding_controls'] == pin(GEOMETRY / 'binding-controls01/result.json')
    anchors = json.loads((GEOMETRY / 'anchors.json').read_text())
    assert anchors['inputs'] == {p: pin(p) for p in anchors['inputs']}
    assert len(anchors['anchors']) == 205 and anchors['source_geometry'] == pin(W)
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
    assert shutil.disk_usage('/dev/shm').free >= 1024**3
    ns['guard_resources']()
    O.mkdir()
    prior_tree = ast.parse(PRIOR.read_text())
    tcl_nodes = [n for n in prior_tree.body if (
        isinstance(n, ast.Assign) and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name) and n.targets[0].id in {'lines', 'metals'}
    ) or (
        isinstance(n, ast.For) and isinstance(n.target, ast.Tuple)
        and [x.id for x in n.target.elts] == ['i', 'r']
    ) or (
        isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name)
        and n.target.id == 'lines'
    )]
    assert len(tcl_nodes) == 4
    tcl_namespace = dict(O=O, W=W, a=anchors)
    exec(compile(ast.Module(body=tcl_nodes, type_ignores=[]), str(PRIOR), 'exec'), tcl_namespace)
    script = O / 'native.tcl'
    script.write_text('\n'.join(tcl_namespace['lines']) + '\n')
    ns['atomic'](B / 'native-tcl-inherited-source.json', dict(
        parent=pin(PRIOR), exact_ASTs=[ast.dump(n, include_attributes=False) for n in tcl_nodes],
        output=pin(script), number_of_actual_geometry_anchors=len(anchors['anchors']),
        extraction_settings_unchanged=True, generated_name_alias_edges=False))
    record = dict(status='RUNNING_NATIVE_DIVIDER_V7_WIRE_RC', inputs=freeze['inputs'],
                  freeze=pin(B / 'source-freeze.json'), source_peer=pin(B / 'source-only-peer.json'),
                  native_script=pin(script), geometry_saved_peer=pin(GEOMETRY / 'saved-geometry-peer.json'),
                  controller_identity=ns['lifecycle']()['process_identity'](os.getpid()),
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), steps=[],
                  resource_contract=geometry['resource_contract'], full_pex_qualified=False,
                  loaded_division_simulated=False, substrate_resistance_modeled=False,
                  main_chip_integrated=False)

    def save():
        ns['atomic'](B / 'native-execution.json', record)

    save()
    old_cad_root = os.environ.get('CAD_ROOT')
    os.environ['CAD_ROOT'] = str(RT)
    try:
        stages = [
            ('native', ['/usr/bin/tclsh8.6', RT / 'magic/tcl/magic.tcl', '-dnull', '-noconsole',
                        '-rcfile', TECH / 'ihp-sg13g2.magicrc', script], O),
            ('audit', [AUDIT_PYTHON, B / 'audit_wire_rc.py', O, GEOMETRY / 'anchors.json',
                       B / 'native-wire-audit.json'], B),
            ('mutations', [AUDIT_PYTHON, B / 'check_native_mutations_v2.py'], B),
        ]
        for name, command, directory in stages:
            assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
            execution = ns['execute'](command, directory, name)
            record['steps'].append(dict(name=name, execution=execution))
            save()
            assert execution['returncode'] == 0, name
            if name == 'native':
                assert (O / 'native.log').read_text().count('\nNSSOC_WIRE_RC_COMPLETE\n') == 1
            elif name == 'audit':
                assert json.loads((B / 'native-wire-audit.json').read_text())['status'] == 'PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
            else:
                assert json.loads((B / 'native-mutations-v2.json').read_text())['status'] == 'PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
            assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
        record['status'] = 'PASS_NATIVE_WIRE_RC_GRAPH_AND13_RAW_CONTROLS_ONLY'
    except BaseException as error:
        record.update(status='FAIL_NATIVE_WIRE_RC_RETAINED', error=repr(error))
        raise
    finally:
        if old_cad_root is None:
            os.environ.pop('CAD_ROOT', None)
        else:
            os.environ['CAD_ROOT'] = old_cad_root
        record['outputs'] = {str(p): pin(p) for p in O.rglob('*') if p.is_file()}
        save()
        try:
            ns['guard_resources']()
        except BaseException as error:
            record.update(status='FAIL_NATIVE_WIRE_RC_RETAINED', error=repr(error))
            save()
            raise
    print(record['status'], flush=True)


if __name__ == '__main__':
    main()
