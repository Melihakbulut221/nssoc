# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Five actual copied-input runs of the exact frozen source/native binder."""
import ast
import copy
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
W = B.parent
ROOT = W.parents[3]
G = Path('/dev/shm/nssoc-div4-v10-tail-v1-layout-01')
T = Path('/dev/shm/nssoc-div4-v10-tail-v1-binding-controls-01')
A = ROOT / 'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
CHECKER = ROOT / 'hw/soc/flow/check_pcie_clock_div4_v7_v2.py'
CASES = ['positive', 'reference_clock_swap', 'reference_pullup_length',
         'reference_missing_tap', 'native_mim_area_corruption']


def pin(p):
    p = Path(p)
    with p.open('rb') as stream:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def delta(a, b, path='$'):
    if type(a) is not type(b):
        return [dict(path=path, old=a, new=b)]
    if isinstance(a, dict):
        assert set(a) == set(b)
        return [r for k in sorted(a) for r in delta(a[k], b[k], path + '.' + k)]
    if isinstance(a, list):
        if len(a) != len(b):
            return [dict(path=path, old=a, new=b)]
        return [r for i, (x, y) in enumerate(zip(a, b)) for r in delta(x, y, path + f'[{i}]')]
    return [] if a == b else [dict(path=path, old=a, new=b)]


def main():
    assert sorted(os.sched_getaffinity(0)) == [10]
    assert not T.exists() and not (B / 'result.json').exists()
    freeze = json.loads((B / 'source-freeze.json').read_text())
    assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
    positive_geometry = json.loads((W / 'geometry-execution.json').read_text())
    assert positive_geometry['status'] == 'PASS_DIVIDER_V10_TAIL115_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
    assert positive_geometry['outputs'] == {p: pin(p) for p in positive_geometry['outputs']}
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
              SCRATCH_ROOTS=(B, T), CPU=10)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(CHECKER), 'exec'), ns)
    assert shutil.disk_usage('/dev/shm').free >= 1024**3
    ns['guard_resources']()
    T.mkdir()
    source = (W / 'bind_source_ids.py').read_text()
    old_root = "G=Path('/dev/shm/nssoc-div4-v10-tail-v1-layout-01')"
    assert source.count(old_root) == 1
    original_g = json.loads((G / 'result.json').read_text())
    original_n = json.loads((W / 'device-location-geometry.json').read_text())
    result = dict(status='RUNNING_COPIED_INPUT_BINDING_CONTROLS',
                  controller_identity=ns['lifecycle']()['process_identity'](os.getpid()),
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  freeze=pin(B / 'source-freeze.json'), cases=[],
                  positive_geometry=pin(W / 'geometry-execution.json'),
                  unchanged_production_method=pin(W / 'bind_source_ids.py'),
                  no_physical_design_mutation=True, no_new_native_device_extraction=True,
                  actual_electrical_fault_simulated=False,
                  resource_contract=positive_geometry['resource_contract'])

    def save():
        ns['atomic'](B / 'result.json', result)

    save()
    try:
        for name in CASES:
            assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
            g, n = copy.deepcopy(original_g), copy.deepcopy(original_n)
            if name == 'reference_clock_swap':
                rows = [r for r in g['instances'] if r['name'] == 'DIV__XFIRST__XSP']
                assert len(rows) == 1 and rows[0]['nets'][0] == 'CLKP'
                rows[0]['nets'][0] = 'CLKN'
            elif name == 'reference_pullup_length':
                rows = [r for r in g['instances'] if r['name'] == 'DIV__XFIRST__XUP']
                assert len(rows) == 1 and rows[0]['length_um'] == 4.0
                rows[0]['length_um'] = 6.4
            elif name == 'reference_missing_tap':
                assert sum(r['name'] == 'TAP0' for r in g['instances']) == 1
                g['instances'] = [r for r in g['instances'] if r['name'] != 'TAP0']
            elif name == 'native_mim_area_corruption':
                row = next(r for r in n['devices'] if r['model'] == 'cap_cmim')
                row['parameters']['A'] *= 1.02
            edits = dict(source=delta(original_g, g), native=delta(original_n, n))
            assert sum(map(len, edits.values())) == (0 if name == 'positive' else 1)
            q = T / name
            q.mkdir()
            f = q / 'fixture-layout'
            f.mkdir()
            (f / 'result.json').write_text(json.dumps(g, indent=2) + '\n')
            (f / 'schematic.cir').write_bytes((G / 'schematic.cir').read_bytes())
            (q / 'device-location-geometry.json').write_text(json.dumps(n, indent=2) + '\n')
            replacement = f'G=Path({str(f)!r})'
            method = source.replace(old_root, replacement)
            assert method.replace(replacement, old_root) == source
            (q / 'bind_source_ids.py').write_text(method)
            inputs = {str(p): pin(p) for p in q.rglob('*') if p.is_file()}
            execution = ns['execute']([A, 'python', q / 'bind_source_ids.py'], B, name)
            case = dict(name=name, changes=edits, inputs=inputs,
                        method_inverse_byte_exact=True, execution=execution)
            result['cases'].append(case)
            save()
            assert inputs == {p: pin(p) for p in inputs}
            output = q / 'source-native-bijection.json'
            if name == 'positive':
                assert execution['returncode'] == 0 and output.is_file()
                actual = json.loads(output.read_text())
                assert actual['status'] == 'PASS_FULL91_DEVICE_SOURCE_LOCATION_AND_NAMED_NET_BIJECTION'
                baseline = json.loads((W / 'source-native-bijection.json').read_text())
                assert {k: v for k, v in actual.items() if k != 'inputs'} == {k: v for k, v in baseline.items() if k != 'inputs'}
                case['positive_output'] = pin(output)
            else:
                assert execution['returncode'] == 1 and not output.exists()
                log = (B / (name + '.log')).read_text()
                assert 'AssertionError' in log and 'Traceback (most recent call last)' in log
                expected = {
                    'reference_clock_swap': 'assert all(len(v)==1 for v in net_map.values())',
                    'reference_pullup_length': "assert all(math.isclose(d['parameters'][k],v",
                    'reference_missing_tap': "assert len(matches)==1,(d['native_id'],at,matches)",
                    'native_mim_area_corruption': "assert all(math.isclose(d['parameters'][k],v",
                }[name]
                assert expected in log, (name, log)
                case['expected_assertion_observed'] = expected
            case['status'] = 'PASS_BASELINE' if name == 'positive' else 'PASS_EXPECTED_REJECTION'
            ns['guard_resources']()
            save()
        assert len(result['cases']) == 5
        assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
        result['status'] = 'PASS_BASELINE_AND_FOUR_ACTUAL_COPIED_INPUT_BINDING_CONTROLS'
        result['fixture_outputs'] = {str(p): pin(p) for p in T.rglob('*') if p.is_file()}
    except BaseException as error:
        result.update(status='FAIL_BINDING_CONTROLS_RETAINED', error=repr(error))
        raise
    finally:
        save()
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
