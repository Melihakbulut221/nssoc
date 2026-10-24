#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Original full acquisition using the independently proven physical C9 PLL845."""
import copy,hashlib,json,os
from pathlib import Path
from run_cloud_tx_layout_repair import sha
import run_cloud_pll_filter_parent_rc as restoration
MODEL_SHA='8147a7cbae9d1a43b362733a3b52c218c5d04ef519cedf9abf35cd17ff27911e'
SUMMARY_SHA='05211617b84f8545bbaec4acfff8a6bc5fde01d795f00f96dd33256ca136a432'
ARCHIVE_SHA='53c840bd15b41f1f08055e44a65481bb2815a6d7e3ea2524f5be73e047b98633'
BASELINE_SHA='91364a351fad4d376e6d168d85af6f63ff4076bfecd5af83192492bc514073fc'
def validate(report,model):
    assert report['status']=='PASS_C9_ACTUAL845_MODEL_EXACT_GRAPH_AND_COMPONENT_FAULTS_NOT_ELECTRICAL_ACCEPTANCE'
    assert report['candidate_sha256']==MODEL_SHA==hashlib.sha256(model.encode()).hexdigest()
    assert report['counts']==dict(devices=845,wires=8648,public_ports=17)
    assert report['exact_graph']['devices']==845 and report['exact_graph']['public_ports']==17 and report['exact_graph']['nodes']==3906
    mapping=report['exact_graph']['mapping'];assert len(mapping)==len(set(mapping.values()))==3906
    assert {r['name']for r in report['graph_faults']}=={'missing_pump_device','wrong_pump_cap_width','pump_up_down_swapped','private_pump_bulk','short_vctrl_avss','wrong_other_width'}
    assert {r['name']for r in report['component_faults']}=={'drop_parent_R','change_parent_R','change_parent_C','move_pump_C','change_pump_R','change_other_device','change_other_wire'}
    assert report['component_preservation']['unchanged_devices']==815
    assert report['qualified_pex'] is False and report['electrical_acquisition_passed'] is False
    return True
def verify_prepared(out,receipt,model):
    folder=out/'physical-parent-proof';report=json.loads((folder/'result.json').read_text())
    assert sha(folder/'result.json')==SUMMARY_SHA==receipt['summary_sha256']
    assert all(sha(folder/n)==v for n,v in report['outputs'].items())
    assert validate(report,model)
    return True
def prepare(original,out):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert hashlib.sha256(original.encode()).hexdigest()==BASELINE_SHA
    restoration.OUT=out
    restoration.restore('cloud-results-38857275591-1-pll-filter-parent-compose-9/pll-filter-parent-compose-9-38857275591-1.tar.gz.part0000',ARCHIVE_SHA,25482210,'cloud-pll-filter-parent-compose/',out/'physical-parent-proof')
    folder=out/'physical-parent-proof';assert sha(folder/'result.json')==SUMMARY_SHA
    report=json.loads((folder/'result.json').read_text());model=(folder/'parent845.spice').read_text();validate(report,model)
    from build_pcie_local_vco_hybrid_v6 import statements
    before=statements(original);after=statements(model);assert before[0]==after[0]and before[-1]==after[-1]
    # All102HBT instances referenced by the original OFF controls are unchanged.
    hbts=lambda rows:[w for w in rows if 'npn13g2'in w]
    assert hbts(before)==hbts(after)and len(hbts(before))==102
    controls=[]
    for name in ('changed_model','missing_graph_fault','missing_component_fault','wrong_device_count','false_pex_acceptance','wrong_model_hash','nonbijective_mapping'):
        bad=copy.deepcopy(report);text=model
        if name=='changed_model':text+='* unauthorized change\n'
        elif name=='missing_graph_fault':bad['graph_faults'].pop()
        elif name=='missing_component_fault':bad['component_faults'].pop()
        elif name=='wrong_device_count':bad['counts']['devices']=844
        elif name=='false_pex_acceptance':bad['qualified_pex']=True
        elif name=='wrong_model_hash':bad['candidate_sha256']='0'*64
        else:
            keys=list(bad['exact_graph']['mapping']);bad['exact_graph']['mapping'][keys[0]]=bad['exact_graph']['mapping'][keys[1]]
        try:validate(bad,text)
        except AssertionError:controls.append(dict(name=name,rejected=True))
        else:raise AssertionError('Accepted corrupt physical model receipt '+name)
    receipt=dict(run_id=38857275591,summary_sha256=SUMMARY_SHA,archive_sha256=ARCHIVE_SHA,model_sha256=MODEL_SHA,baseline_model_sha256=BASELINE_SHA,controls=controls,unchanged_hbt_off_targets=102,physical_model_exact_graph_passed=True,qualified_pex=False,full_phy_accepted=False)
    verify_prepared(out,receipt,model)
    return model,receipt
if __name__=='__main__':
    import cloud_pll_vbic_acquisition as acquisition
    acquisition.main(physical_parent=True)
