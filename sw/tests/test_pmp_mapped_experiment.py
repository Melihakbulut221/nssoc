# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed controls for the isolated PMP experiment (no PDK/history needed)."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import run_pmp_mapped_experiment as exp  # noqa: E402


def sta_log():
    return ('PMP_INTERFACE 278 3\nPMP_WORST_SETUP_NS 13.0\n'
        + ''.join(f'PMP_OUTPUT_BEGIN pmp_req_err_o[{i}]\n'
            '7.0 data arrival time\n-7.0 data arrival time\n13.0 slack (MET)\nPMP_OUTPUT_END\n' for i in range(3))
        + 'PMP_STA_COMPLETE\n')


def test_all_three_endpoint_paths_independently_check_worst_slack():
    result = exp.parse_sta(sta_log())
    assert result['worst_arrival_ns'] == 7
    assert len(result['outputs']) == 3


@pytest.mark.parametrize('old,new', [
    ('PMP_STA_COMPLETE', ''), ('PMP_INTERFACE 278 3', 'PMP_INTERFACE 244 2'),
    ('pmp_req_err_o[2]', 'pmp_req_err_o[1]'), ('PMP_WORST_SETUP_NS 13.0', 'PMP_WORST_SETUP_NS 14.0'),
    ('7.0 data arrival time', 'No paths found.'), ('13.0 slack (MET)', 'NaN slack (MET)'),
    ('PMP_STA_COMPLETE', 'PMP_STA_COMPLETE\n[ERROR STA-1] failed'),
    ('PMP_WORST_SETUP_NS 13.0', 'PMP_WORST_SETUP_NS 1e999'),
    ('-7.0 data arrival time', '-8.0 data arrival time'),
])
def test_missing_wrong_or_nonfinite_sta_result_rejected(old, new):
    with pytest.raises(ValueError):
        exp.parse_sta(sta_log().replace(old, new))


def test_formal_failure_is_distinct_from_timeout_and_tool_error():
    assert exp.proof_outcome(0, 'SAT proof finished - no model found: SUCCESS!') == 'PROVED_ALL_BINARY_INPUTS'
    assert exp.proof_outcome(1, 'SAT proof finished - model found: FAIL!\nERROR: proof did fail') == 'COUNTEREXAMPLE'
    for code, log in [(124, 'timeout'), (1, 'Error loading library'), (0, 'proof did fail'),
                      (1, 'SAT proof finished - no model found: SUCCESS!'), (1, 'proof did fail')]:
        with pytest.raises(ValueError):
            exp.proof_outcome(code, log)


@pytest.mark.parametrize('left_mapped,right_mapped', [(False, True), (True, True), (False, False)])
def test_equivalence_has_no_assumptions_and_uses_real_library_functions(tmp_path, left_mapped, right_mapped):
    script = exp.proof_script(tmp_path/'a.v', left_mapped, tmp_path/'b.v', right_mapped,
                              tmp_path/'cells.lib', tmp_path/'model')
    assert script.count('read_liberty -ignore_miss_func') == int(left_mapped)+int(right_mapped)
    assert script.count(exp.PROFILE) == 2-int(left_mapped)-int(right_mapped)
    assert 'miter -equiv -flatten gold gate miter' in script
    sat = script.split('\nsat ')[1]
    assert '-set' not in sat and '-assume' not in sat and '-undef' not in sat
    assert '-dump_json' in sat and '-dump_vcd' in sat


def mapped_fixture():
    return {'modules': {'ibex_pmp': {'ports': {
        name: {'direction': direction, 'bits': list(range(width))}
        for name, (direction, width) in exp.PORTS.items()},
        'cells': {'u1': {'type': 'sg13g2_and2_1'}}}}}


@pytest.mark.parametrize('fault', ['none', 'channel_count', 'direction', 'missing_port', 'unmapped', 'state', 'empty'])
def test_mapped_profile_and_combinational_stdcell_closure(tmp_path, fault):
    data = mapped_fixture()
    module = data['modules']['ibex_pmp']
    if fault == 'channel_count': module['ports']['pmp_req_err_o']['bits'].pop()
    if fault == 'direction': module['ports']['debug_mode_i']['direction'] = 'output'
    if fault == 'missing_port': del module['ports']['pmp_req_type_i']
    if fault == 'unmapped': module['cells']['u1']['type'] = '$and'
    if fault == 'state': module['cells']['u1']['type'] = 'sg13g2_dfrbp_1'
    if fault == 'empty': module['cells'] = {}
    path = tmp_path/'mapped.json'; path.write_text(json.dumps(data))
    if fault == 'none': assert exp.inspect_mapped(path)['cell_count'] == 1
    else:
        with pytest.raises(ValueError): exp.inspect_mapped(path)


def test_mapping_uses_same_typical_library_profile_and_explicit_twenty_ps_target(tmp_path):
    scripts = [exp.map_script(tmp_path/(tag+'.v'), tmp_path, tag, tmp_path/'same.lib')
               for tag in ('original', 'candidate')]
    for script in scripts:
        assert exp.PROFILE in script and ' -D 20\n' in script
        assert 'check -assert' in script and 'write_json' in script
    with pytest.raises(ValueError): exp.map_script(tmp_path/'a', tmp_path, 'bad', tmp_path/'b')


def test_sta_zero_wire_harness_uses_all_ports_and_identical_sdc(tmp_path):
    script = exp.sta_script(tmp_path/'mapped.v', tmp_path/'corner.lib', tmp_path, tmp_path/'same.sdc')
    assert 'all_inputs]] != 278' in script and 'all_outputs]] != 3' in script
    assert 'foreach port [lsort [all_outputs]]' in script
    assert 'read_spef' not in script and 'estimate_parasitics' not in script
    assert 'set_false_path' not in exp.SDC and 'set_multicycle' not in exp.SDC
    assert exp.MAX_AS == 2*1024**3 and exp.MAX_OUTPUT == 30*1024**2


def test_resource_timeout_kills_native_process_and_keeps_log(tmp_path):
    with pytest.raises(RuntimeError, match='time/output budget'):
        exp.bounded_run([sys.executable, '-c', 'import time; print("started", flush=True); time.sleep(30)'],
                        tmp_path/'native.log', tmp_path, 0.2)
    assert 'started' in (tmp_path/'native.log').read_text()


def test_oversized_native_output_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(exp, 'MAX_OUTPUT', 2*1024**2)
    with pytest.raises(RuntimeError, match='output'):
        exp.bounded_run([sys.executable, '-c', 'print("x"*3000000)'],
                        tmp_path/'native.log', tmp_path, 10)


def test_tcl_path_rejects_injection(tmp_path):
    with pytest.raises(ValueError): exp.tcl(tmp_path/'bad} ; exit')
