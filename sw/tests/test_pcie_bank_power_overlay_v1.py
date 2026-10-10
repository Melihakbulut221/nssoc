# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy
import importlib.util
from pathlib import Path
import sys

import pytest

FLOW=Path(__file__).resolve().parents[2]/'hw/soc/flow'
sys.path.insert(0,str(FLOW))
spec=importlib.util.spec_from_file_location('overlay_check',FLOW/'check_pcie_bank_power_overlay_v1.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


def fixture():
    rows=[dict(label=f'T{i:04d}',wire_component=i%128+1,
               kind='INTRINSIC_DEVICE_TERMINAL_REFERENCE') for i in range(748)]
    rows += [dict(label=f'P{i:03d}',wire_component=i+1,kind='PUBLIC_PORT_REFERENCE') for i in range(56)]
    a=dict(anchors=rows,unmodeled_body_well_terminals=[{'id':i} for i in range(313)])
    probed={r['label']:1000+r['wire_component'] for r in rows}
    return a,probed


def test_geometric_cluster_numbers_may_change_but_bijection_is_total():
    a,p=fixture();m=c.component_contract(p,a)
    assert len(m)==128 and m[1]==1001 and m[128]==1128


@pytest.mark.parametrize('fault',['missing_terminal','missing_public_pad','point_without_metal',
                                  'short_conductors','split_conductor','extra_auxiliary_label',
                                  'missing_body_identity','duplicate_real_label'])
def test_actual_anchor_contract_rejects_topology_or_census_corruption(fault):
    a,p=fixture()
    if fault=='missing_terminal':p.pop('T0012')
    elif fault=='missing_public_pad':p.pop('P012')
    elif fault=='point_without_metal':p['T0012']=None
    elif fault=='short_conductors':p={k:1001 if v==1002 else v for k,v in p.items()}
    elif fault=='split_conductor':p['T0012']=9999
    elif fault=='extra_auxiliary_label':p['W001']=1001
    elif fault=='missing_body_identity':a['unmodeled_body_well_terminals'].pop()
    elif fault=='duplicate_real_label':a['anchors'][1]=copy.deepcopy(a['anchors'][0])
    with pytest.raises(ValueError):c.component_contract(p,a)


@pytest.mark.parametrize('fault',[None,'wrong_top','truncated_rule_inventory','native_violation'])
def test_native_drc_must_be_complete_and_zero(tmp_path,fault):
    top=c.method.TOP if fault!='wrong_top' else 'wrong_top'
    count=559 if fault=='truncated_rule_inventory' else 560
    text=f'<report-database><top-cell>{top}</top-cell><categories>'
    text+=''.join(f'<category><name>r{i}</name></category>' for i in range(count))
    text+='</categories><items>'
    if fault=='native_violation':text+='<item><category>TV2.b</category></item>'
    text+='</items></report-database>'
    p=tmp_path/'native.lyrdb';p.write_text(text)
    if fault:
        with pytest.raises(ValueError):c.check_drc(p)
    else:c.check_drc(p)
