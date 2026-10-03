# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure source/placement/mutation contracts. No native chip work runs locally."""
from collections import Counter
import inspect
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'hw/soc/flow'))
import run_io_parent_path_probe as probe  # noqa: E402
import io_parent_path_probe as helper  # noqa: E402


def fake_deck(tmp_path):
    base=tmp_path/probe.mask.BASE; rules=base/'rule_decks';rules.mkdir(parents=True)
    names=(*probe.mask.ORDER,'custom_classes')
    for name in names:
        (rules/f'{name}.lvs').write_text('# unchanged fixture\n')
    (base/'sg13g2.lvs').write_text(''.join('  # %include rule_decks/'+n+'.lvs\n'
        for n in (*probe.mask.ORDER,'devices_connections')))
    (rules/'general_connections.lvs').write_text('\n'.join(f'connect({a}, {b})' for a,b in helper.EDGES))
    return rules


def test_exact_order_and_material_edges(tmp_path):
    fake_deck(tmp_path)
    source=probe.program(tmp_path)
    paths=[str((tmp_path/probe.mask.BASE/'rule_decks'/f'{n}.lvs').resolve()) for n in probe.mask.ORDER]
    positions=[source.index('# %include '+p+'\n') for p in paths]
    assert positions==sorted(positions)
    assert all("'"+name+"' => "+name in source for name in helper.LAYERS)
    assert ('metal5_con','topvia1_n_cap') in helper.EDGES
    assert ('topvia1_n_cap','topmetal1_con') in helper.EDGES
    for forbidden in ('connect_implicit(', 'connect_global(', 'compare(', 'schematic(', 'extract_devices('):
        assert forbidden not in source


@pytest.mark.parametrize('fault',['missing-edge','uncut-topvia','reordered-derivation'])
def test_derivation_contract_mutation(tmp_path,fault):
    rules=fake_deck(tmp_path)
    if fault=='reordered-derivation':
        p=rules.parent/'sg13g2.lvs';s=p.read_text();s=s.replace('  # %include rule_decks/tap_derivations.lvs\n','');p.write_text(s)
    else:
        p=rules/'general_connections.lvs';s=p.read_text()
        s=s.replace('topvia1_n_cap','topvia1_drw') if fault=='uncut-topvia' else s.replace('connect(cont_drw, metal1_con)','')
        p.write_text(s)
    with pytest.raises(ValueError): probe.program(tmp_path)


def test_actual_seven_instance_chain_and_all_material_layers():
    assert [r['y_nm'] for r in helper.CHAIN]==[1157000,1077000,1076000,996000,995000,915000,914000]
    assert all(r['rotation']==3 and r['x_nm']==0 for r in helper.CHAIN)
    assert len(set(r['instance'] for r in helper.CHAIN))==7
    assert len(helper.METALS)==7 and len(helper.VIAS)==6 and 'cont_drw' in helper.LAYERS
    assert ('cont_drw','metal1_con') in helper.EDGES
    assert all(not any(s in x for s in ['well','tap','text']) for edge in helper.EDGES for x in edge)


@pytest.mark.parametrize('fault',[None,'missing','duplicate','mirrored','shifted'])
def test_actual_parent_transform_gate(fault):
    expected=[('Vss','r270 0,1076000'),('Filler','r270 0,996000'),('IOVdd','r270 0,995000')]
    actual=Counter(expected)
    if fault=='missing':actual.pop(expected[0])
    if fault=='duplicate':actual[expected[0]]=2
    if fault in ('mirrored','shifted'):
        actual.pop(expected[0]);actual[('Vss','m270 0,1076000' if fault=='mirrored' else 'r270 0,1076001')]=1
    if fault:
        with pytest.raises(ValueError):helper.validate_placements(actual,expected)
    else:helper.validate_placements(actual,expected)


@pytest.mark.parametrize('fault',[None,'case','runtime','status'])
def test_tiny_native_receipt_gate(tmp_path,fault):
    row=dict(status='PASS_NATIVE_PARENT_PATH_CONTROLS',cases=helper.CASES,klayout_version='0.30.7',dbu_um=.001)
    if fault=='case':row['cases']=helper.CASES[:-1]
    if fault=='runtime':row['klayout_version']='0.30.6'
    if fault=='status':row['status']='PENDING'
    path=tmp_path/'receipt.json';path.write_text(json.dumps(row))
    if fault:
        with pytest.raises(ValueError):probe.validate_controls(path)
    else: assert probe.validate_controls(path)==row


def test_controls_gate_real_input_and_no_negative_open_claim():
    source=inspect.getsource(probe.run)
    assert source.index("validate_controls(output/'controls.json')")<source.index('fetch(asset,cache)')
    text=inspect.getsource(helper)
    assert 'INCONCLUSIVE_EXPAND_PARENT_CONTEXT' in text
    assert 'full_parent_routes_included=False' in text
    assert 'cell_lvs_accepted=False' in text
    assert 'native_joined' in text and "'Native/explicit physical graph disagree'" in text
    assert 'coherent_polygon_geometry_transfer_allowed' in text


def test_workflow_native_is_cloud_only_and_own_push_path():
    text=(ROOT/'.github/workflows/io-parent-path-probe.yml').read_text()
    assert '      - .github/workflows/io-parent-path-probe.yml\n' in text
    assert 'scripts/run_io_parent_path_probe.py\n' in text
    assert 'workflow_dispatch:' in text and 'cancel-in-progress: false' in text
