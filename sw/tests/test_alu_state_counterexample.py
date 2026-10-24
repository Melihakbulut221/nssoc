# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""An exact diagnostic assignment must never become an equivalence assumption."""
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import replay_alu_state_counterexample as replay  # noqa: E402


def wave(values):
    return {'signal':[dict(name=name,wave='=4',data=[value,'']) if len(value)>1
                       else dict(name=name,wave=value+'4') for name,value in values.items()]}


def module():
    return {'ports':{'x':dict(direction='input',bits=[1,2]),'y':dict(direction='output',bits=[3,4])}}


def test_exact_complete_counterexample_assignment():
    assert replay.assignments(wave({'trigger':'1','in_x':'10'}),module())=={'in_x':'10'}


@pytest.mark.parametrize('values',[
    {'trigger':'1'}, {'trigger':'1','in_x':'1'}, {'trigger':'0','in_x':'10'},
    {'trigger':'1','in_x':'1x'}, {'trigger':'1','in_x':'10','in_extra':'0'},
    {'trigger':'1','in_x':'10','internal_cutpoint':'1'},
])
def test_missing_narrow_nonbinary_or_extra_constraints_rejected(values):
    with pytest.raises(ValueError):replay.assignments(wave(values),module())


def test_duplicate_model_signal_rejected():
    model=wave({'trigger':'1','in_x':'10'});model['signal'].append(model['signal'][1])
    with pytest.raises(ValueError):replay.assignments(model,module())


def native_model():
    return wave({'trigger':'1','in_x':'10','gold_y':'10','gate_y':'11','cmp_y':'0'})


def test_exact_native_difference_bit_and_boundary_labels():
    labels={'original':{'y':['original_bit0','original_bit1']},'candidate':{'y':['candidate_bit0','candidate_bit1']}}
    result=replay.differences(native_model(),module(),module(),{'in_x':'10'},labels)
    assert result==dict(compared_bits=2,differing_bits=1,by_port={'y':1},differences=[
        dict(port='y',bit=0,original=0,candidate=1,original_boundary='original_bit0',candidate_boundary='candidate_bit0')])


@pytest.mark.parametrize('fault',['missing','changed_input','extra_input','wrong_width','wrong_cmp','no_difference','extra_output','labels'])
def test_incomplete_or_inconsistent_replay_fails(fault):
    model=native_model();values=replay.wave_values(model);labels={'original':{},'candidate':{}}
    if fault=='missing':del values['gold_y']
    if fault=='changed_input':values['in_x']='00'
    if fault=='extra_input':values['in_ignored']='0'
    if fault=='wrong_width':values['gold_y']='0'
    if fault=='wrong_cmp':values['cmp_y']='1'
    if fault=='no_difference':values['gate_y']='10';values['cmp_y']='1'
    if fault=='extra_output':values['ignored']='1'
    if fault=='labels':labels['original']['y']=['only_one']
    with pytest.raises(ValueError):replay.differences(wave(values),module(),module(),{'in_x':'10'},labels)


def test_replay_source_keeps_same_graphs_library_and_full_miter(tmp_path):
    script=replay.replay_script(tmp_path/'a',tmp_path/'b',tmp_path/'lib',tmp_path/'model',{'in_x':'10'})
    assert 'miter -equiv -make_outputs -make_outcmp -flatten gold gate miter' in script
    assert "-set in_x 2'b10" in script
    assert 'sat -verify -prove trigger 0' in script
    assert 'select -assert-none t:sg13g2_* t:RM_*' in script
    assert 'setundef' not in script and 'synth' not in script and 'abc' not in script
    assert script.count('read_json')==2


@pytest.mark.parametrize('name,value',[('internal','1'),('in_a;quit','1'),('in_a','x'),('in_a','')])
def test_assignment_injection_or_nonbinary_constraint_rejected(tmp_path,name,value):
    with pytest.raises(ValueError):replay.replay_script(tmp_path/'a',tmp_path/'b',tmp_path/'lib',tmp_path/'model',{name:value})


def test_changed_lifted_boundary_rejected():
    changed=copy.deepcopy(module());changed['ports']['y']['bits'].pop()
    with pytest.raises(ValueError):replay.differences(native_model(),module(),changed,{'in_x':'10'},{'original':{},'candidate':{}})


def test_full_replay_remains_cloud_only(tmp_path,monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    with pytest.raises(ValueError,match='cloud-only'):replay.run(tmp_path/'out',tmp_path/'work')
    assert not (tmp_path/'out').exists()


def test_permanent_failed_artifact_bytes_download_without_token(tmp_path,monkeypatch):
    seen=[]
    monkeypatch.delenv('GH_TOKEN',raising=False)
    monkeypatch.setattr(replay.state.common,'download',lambda pin,path:seen.append((pin,path)))
    result=replay.fetch_artifact(tmp_path/'source.zip')
    assert seen==[(replay.ARTIFACT,tmp_path/'source.zip')]
    assert result['source_kind']=='permanent_public_release' and result['source_run']==37003975081
    assert result['bytes']==10538738 and result['sha256']=='8a90ec932cd6f4bfd04b49b40c33f44ad123f703673cb779977b4de74a90cb5a'
