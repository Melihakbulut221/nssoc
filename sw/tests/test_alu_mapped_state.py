# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Storage-boundary coverage, bad mappings and scope guards, without PDK/history."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
import prove_alu_mapped_state as gate  # noqa: E402


def add_clock_gate(module):
    module['cells']['icg'] = dict(type=gate.CG, parameters={}, attributes={},
        port_directions=dict(CLK='input', GATE='input', GCLK='output'),
        connections=dict(CLK=[4], GATE=[2], GCLK=[20]))
    module['netnames']['gated_clock'] = dict(bits=[20], attributes={})


def add_memory(module, kind=gate.SP):
    ports = gate.macro_ports(kind); cursor = 100
    connections = {}
    for name, (_, width) in ports.items():
        connections[name] = list(range(cursor, cursor+width)); cursor += width
        module['netnames'][name] = dict(bits=connections[name], attributes={})
    module['cells']['memory'] = dict(type=kind, parameters={}, attributes={}, connections=connections,
                                   port_directions={p:d for p,(d,_) in ports.items()})


def test_bijection_is_only_proposal_then_all_state_equations_are_exported():
    original = gate.fixture(); candidate = copy.deepcopy(original)
    candidate['cells']['renamed'] = candidate['cells'].pop('ff0')
    pairs, receipt = gate.propose_bijection(original, candidate)
    assert ('ff0', 'renamed') in pairs and receipt['anchored'] == 2
    lifted, labels = gate.lift(original, [p[0] for p in pairs])
    assert set(lifted['cells']) == {'inv'}
    for suffix in ['ff_state', 'ff_d', 'ff_clk', 'ff_reset_b']:
        assert len(lifted['ports'][gate.PREFIX+suffix]['bits']) == 2
        assert len(labels[gate.PREFIX+suffix]) == 2
    assert lifted['cells']['inv'] == original['cells']['inv']
    assert lifted['ports']['output_q'] == original['ports']['output_q']


@pytest.mark.parametrize('fault', ['missing', 'extra', 'duplicate', 'type', 'width', 'pin', 'direction', 'unmapped', 'unknown_bit'])
def test_incomplete_or_unsafe_storage_boundaries_fail(fault):
    a = gate.fixture(); b = copy.deepcopy(a)
    if fault == 'missing': del b['cells']['ff0']
    if fault == 'extra':
        b['cells']['extra'] = copy.deepcopy(b['cells']['ff0']); b['cells']['extra']['connections']['Q']=[99]
    if fault == 'duplicate': b['cells']['ff1']['connections']['Q']=[10]
    if fault == 'type': b['cells']['ff0']['type']='sg13g2_dffq_1'
    if fault == 'width': b['cells']['ff0']['connections']['D']=[2,3]
    if fault == 'pin': b['cells']['ff0']['connections']['SET']=[2]
    if fault == 'direction': b['cells']['ff0']['port_directions']['D']='output'
    if fault == 'unmapped': b['cells']['inv']['type']='$not'
    if fault == 'unknown_bit': b['cells']['ff0']['connections']['D']=['x']
    with pytest.raises(ValueError): gate.propose_bijection(a,b)


@pytest.mark.parametrize('order', [['ff0'], ['ff0','ff0'], ['ff0','ff1','ff2']])
def test_lift_rejects_nonbijection(order):
    with pytest.raises(ValueError): gate.lift(gate.fixture(), order)


def test_anonymous_pairing_remains_explicitly_untrusted():
    a = gate.fixture(); a['netnames']={f'_{i}_': n for i,n in enumerate(a['netnames'].values())}
    pairs, receipt = gate.propose_bijection(a, copy.deepcopy(a))
    assert len(pairs)==2 and receipt['anchored']==0 and receipt['proposed_anonymous']==2
    assert 'untrusted' in receipt['anonymous_method']


def test_clock_gate_preserves_actual_latch_and_and_semantics():
    module = gate.fixture(); add_clock_gate(module)
    lifted, labels = gate.lift(module,['ff0','ff1'])
    mux=lifted['cells'][gate.PREFIX+'gate_latch_0']
    and_cell=lifted['cells'][gate.PREFIX+'gate_output_0']
    assert mux['type']=='$mux' and mux['connections']['S']==[4] and mux['connections']['A']==[2]
    assert mux['connections']['B']==lifted['ports'][gate.PREFIX+'gate_state']['bits']
    assert and_cell['type']=='$and' and and_cell['connections']['Y']==[20]
    assert and_cell['connections']['A']==[4] and and_cell['connections']['B']==mux['connections']['B']
    assert set(labels)>= {gate.PREFIX+s for s in ['gate_state','gate_clk','gate_enable','gate_next']}
    for clk in [0,1]:
        for enable in [0,1]:
            for state in [0,1]:
                # Pinned statetable L L -> L, L H -> H, H - -> retain.
                expected = enable if clk==0 else state
                assert (state if clk else enable)==expected
                assert clk & state == (state if clk else 0)


@pytest.mark.parametrize('location', ['port', 'cell_connection'])
def test_fresh_latch_bits_cannot_collide_with_unnamed_existing_bits(location):
    module = gate.fixture(); add_clock_gate(module)
    if location == 'port':
        module['ports']['unnamed_input'] = dict(direction='input', bits=[100001])
    else:
        module['cells']['inv']['connections']['A'] = [100001]
    lifted, _ = gate.lift(module, ['ff0', 'ff1'])
    assert lifted['ports'][gate.PREFIX+'gate_state']['bits'][0] > 100001
    assert lifted['ports'][gate.PREFIX+'gate_next']['bits'][0] > 100001


@pytest.mark.parametrize('kind,width_in,width_out', [(gate.SP,288,64),(gate.DP,180,32)])
def test_every_memory_input_and_output_bit_is_accounted_for(kind,width_in,width_out):
    module=gate.fixture();add_memory(module,kind)
    _, counts=gate.inspect(module)
    assert counts['memory_input_bits']==width_in and counts['memory_output_bits']==width_out
    lifted, labels=gate.lift(module,['ff0','ff1'])
    assert 'memory' not in lifted['cells']
    assert len(lifted['ports'][gate.PREFIX+'memory_inputs']['bits'])==width_in
    assert len(lifted['ports'][gate.PREFIX+'memory_outputs']['bits'])==width_out
    names={row[1] for row in labels[gate.PREFIX+'memory_inputs']}
    assert names=={p for p,(d,_) in gate.macro_ports(kind).items() if d=='input'}
    assert 'A_BIST_CLK' in names and 'A_BIST_DIN' in names and 'A_DLY' in names


@pytest.mark.parametrize('fault',['instance','kind','input_pin','output_pin'])
def test_memory_contract_mismatch_rejected(fault):
    a=gate.fixture();add_memory(a);b=copy.deepcopy(a)
    if fault=='instance':b['cells']['different']=b['cells'].pop('memory')
    if fault=='kind':b['cells']['memory']['type']=gate.DP
    if fault=='input_pin':del b['cells']['memory']['connections']['A_BIST_EN']
    if fault=='output_pin':b['cells']['memory']['connections']['A_DOUT'].pop()
    with pytest.raises(ValueError):gate.propose_bijection(a,b)


def test_no_named_internal_cutpoints_assumptions_or_unproved_cell_models(tmp_path):
    script=gate.miter_script(tmp_path/'a.json',tmp_path/'b.json',tmp_path/'lib',tmp_path/'model')
    assert script.count('read_liberty -ignore_miss_func')==2
    assert script.count('select -assert-none t:sg13g2_* t:RM_* t:$dff* t:$adff* t:$dlatch*')==2
    assert 'miter -equiv -flatten gold gate miter' in script
    sat=script.split('\nsat ')[1]
    assert '-set' not in sat and '-assume' not in sat and '-undef' not in sat
    assert '-dump_json' in sat and '-dump_vcd' in sat
    frontend=gate.frontend_script(tmp_path/'a',tmp_path/'b',tmp_path/'c',tmp_path/'d',tmp_path/'e')
    assert 'synth' not in frontend and 'abc' not in frontend and 'setundef' not in frontend


def test_actual_failure_cannot_be_confused_with_tool_error_or_timeout():
    assert gate.outcome(0,'SAT proof finished - no model found: SUCCESS!')=='PROVED_ALL_BINARY_BOUNDARY_EQUATIONS'
    assert gate.outcome(1,'model found: FAIL!\nERROR: proof did fail')=='COUNTEREXAMPLE_PRESERVED'
    for code,log in [(124,'timeout'),(1,'proof did fail'),(0,'model found: FAIL!'),(1,'unknown cell')]:
        with pytest.raises(ValueError):gate.outcome(code,log)


def test_full_native_task_is_cloud_only(tmp_path,monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    with pytest.raises(ValueError,match='cloud-only'):gate.run(tmp_path/'out',tmp_path/'work')
    assert not (tmp_path/'out').exists()


def test_native_controls_include_equal_and_four_real_faults(tmp_path,monkeypatch):
    cases=[]
    def fake_run(runtime,script,output,name,timeout):
        cases.append(name)
        negative=name!='tiny-equal'
        (output/(name+'.log')).write_text('model found: FAIL! proof did fail' if negative else 'SAT proof finished - no model found: SUCCESS!')
        if negative:
            (output/(name+'-model.json')).write_text('{}')
            (output/(name+'-model.vcd')).write_text('model')
        return {'returncode':int(negative)}
    monkeypatch.setattr(gate,'execute',fake_run)
    results=gate.controls(tmp_path/'runtime',tmp_path/'lib',tmp_path)
    assert set(results)=={'equal','wrong_state_pair','wrong_reset','wrong_output','wrong_gate_latch'}
    assert len(cases)==5
