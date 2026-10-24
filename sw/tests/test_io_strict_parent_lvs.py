# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict original reference and prior-geometry identity controls; no native work."""
import hashlib
import inspect
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_io_strict_parent_lvs as p  # noqa: E402


def fixture():
    source='* isolated test library\n.PARAM\n*.GLOBAL sub!\n'
    for i in range(5):
        source+=f'.SUBCKT leaf{i} a b\nXR0 a b / ptap1 r=22.832 A=23.523p Perim=19.4u w=4.85u l=4.85u\n.ENDS\n'
    for i,name in enumerate(dict.fromkeys(r['master'] for r in p.CHAIN)):
        source+=f'.SUBCKT {name} iovdd iovss vdd vss\n'
        if i==0:source+=''.join(f'XI{j} iovss sub! / leaf{j}\n' for j in range(5))
        source+='.ENDS\n'
    return source


def pin(monkeypatch,raw):
    monkeypatch.setattr(p,'CDL_SHA',hashlib.sha256(raw.encode()).hexdigest())


def test_reference_preserves_original_globals_bodies_and_parameters(monkeypatch):
    raw=fixture();pin(monkeypatch,raw)
    selected,receipt=p.reference(raw)
    assert selected.startswith('.GLOBAL sub!\n')
    assert receipt['explicit_globals']==['sub!'] and len(receipt['selected_subcircuits'])==11
    assert receipt['wrapper'].count('\nXu_')==7
    assert receipt['formal_order']==['iovdd','iovss','vdd','vss']
    assert 'R0 a b / ptap1 r=22.832 A=23.523p Perim=19.4u w=4.85u l=4.85u' in selected
    assert all(not receipt[k] for k in ['globals_inferred','vendor_node_tokens_changed','tap_parameters_changed','terminal_candidate_applied'])
    assert all(c['reason'] in ['empty_parameter_declaration','native_explicit_global_declaration','native_tap_device_prefix'] for c in receipt['dialect_changes'])


@pytest.mark.parametrize('fault',['hash','missing-declaration','extra-global','reordered-formals','extra-dependency'])
def test_reference_contract_mutations_fail(monkeypatch,fault):
    raw=fixture()
    if fault=='missing-declaration':raw=raw.replace('*.GLOBAL sub!\n','')
    if fault=='extra-global':raw=raw.replace('*.GLOBAL sub!','*.GLOBAL sub! other!')
    if fault=='reordered-formals':raw=raw.replace('iovdd iovss vdd vss\n','vdd vss iovdd iovss\n',1)
    if fault=='extra-dependency':raw=raw.replace('XI0 iovss sub! / leaf0','XI0 iovss sub! / nonexistent')
    pin(monkeypatch,raw)
    if fault=='hash':monkeypatch.setattr(p,'CDL_SHA','0'*64)
    with pytest.raises(ValueError):p.reference(raw)


def parent_fixture(tmp_path,monkeypatch,fault=None):
    proof=dict(status='ACTUAL_PARENT_TRANSFORMS_VERIFIED',source_cells_changed=False,
        actual_parent_instances=list(p.CHAIN),all_selected_polygon_layers_equal=False)
    if fault=='placement':proof['actual_parent_instances']=[dict(r) for r in p.CHAIN];proof['actual_parent_instances'][0]['y_nm']+=1
    result=dict(status='COMPLETED_PARENT_PATH_DIAGNOSTIC',source_sha=p.PARENT_SOURCE,run_id=str(p.PARENT_RUN),
        analysis=dict(status='PARENT_SUBGRAPH_JOIN_PROVEN'),output_sha256={'actual-adjacency.gds':hashlib.sha256(b'fixture-only').hexdigest()})
    if fault=='run':result['run_id']='1'
    if fault=='source':result['source_sha']='0'*40
    if fault=='missing-join':result['analysis']['status']='INCONCLUSIVE_EXPAND_PARENT_CONTEXT'
    files={'actual-adjacency.gds':b'fixture-only','result.json':json.dumps(result).encode(),
      'source-reconciliation.json':json.dumps(proof).encode(),'actual-masters/receipt.json':b'{}'}
    for name,data in files.items():
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    monkeypatch.setattr(p,'PARENT_INPUTS',{k:hashlib.sha256(v).hexdigest() for k,v in files.items()})
    if fault=='gds-bytes':(tmp_path/'actual-adjacency.gds').write_bytes(b'changed')
    return tmp_path


@pytest.mark.parametrize('fault',[None,'placement','run','source','missing-join','gds-bytes'])
def test_actual_parent_identity_gate(tmp_path,monkeypatch,fault):
    directory=parent_fixture(tmp_path,monkeypatch,fault)
    if fault:
        with pytest.raises(ValueError):p.validate_parent(directory)
    else:assert p.validate_parent(directory)[0]['run_id']==str(p.PARENT_RUN)


def test_native_commands_keep_strict_taps_ports_and_actual_top(tmp_path):
    for mode in ('deep','flat'):
        args=p.command(tmp_path/'sg13g2.lvs',tmp_path/'inputs',tmp_path/'case',mode)
        options=[args[i+1] for i,v in enumerate(args) if v=='-rd']
        assert 'disable_tap_extraction=false' in options and 'ignore_top_ports_mismatch=false' in options
        assert 'topcell=ACTUAL_IO_ADJACENCY' in options and f'run_mode={mode}' in options
    with pytest.raises(ValueError):p.command(tmp_path,tmp_path,tmp_path,'waive')


def test_baseline_has_no_candidate_or_geometry_rewrite():
    text=inspect.getsource(p)
    assert 'connect_implicit(' not in text and 'canonicalize_straight_spacing(' not in text
    assert 'full_chip_lvs_accepted=False' in text and 'manufacturing_approval=False' in text
    assert "verdict(case,detail['native'],detail['audit_process'])" in text
    assert "native.validate_controls(output/'controls/result.json')" in text
    workflow=(ROOT/'.github/workflows/io-strict-parent-lvs.yml').read_text()
    assert "run-id: '36989535029'" in workflow and '  actions: read' in workflow
