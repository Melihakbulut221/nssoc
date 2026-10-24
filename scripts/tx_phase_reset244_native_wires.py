#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh all-metal graph and1010 actual terminal planes; no RC/electrical claim."""
import ast,json,shutil
from pathlib import Path
from run_cloud_tx_layout_repair import sha
from cloud_tx_phase_divider_wires import derive
ROOT=Path(__file__).resolve().parents[1]
PORTS={"CLKP","CLKN","MP","MN","QP","QN","ARM_P","ARM_N","DIV_AVDD","AVSS","SUB"}
def graph_source(top,gds_hash):
    edits=[
      ('nssoc_tx_input_driver_v7_physical_localpins_v1',top,1),
      ("P=B/'inputs/tx-input-driver-localpins/cloud-tx-input-driver-localpins'","P=B",1),
      ("P/'base/layout.gds'","P/'layout/"+top+".gds'",1),
      ("P/'check-raw_flat_lvs/","P/'flat_lvs/",2),
      ('6f7a7cf92c1dc25a259acdbff779c7cce841128991abb780e13478aa84b4eb62',gds_hash,1),
      ('c.pin_count()==6','c.pin_count()==11',1),
      ('dict(sg13_hv_nmos=40,sg13_lv_nmos=22,sg13_lv_pmos=22,ptap1=10,ntap1=2,rppd=4)','dict(npn13G2=106,rppd=130,cap_cmim=8,ptap1=90)',1),
      ("'full_driver_wires'","'phase_reset334_wires'",1),
      ("'DRIVERWIRES'","'PHASERESET334WIRES'",1),
      ('PASS_FULL_DRIVER_METAL_VIA_GRAPH_BOUND_TO_ALL100_NATIVE_DEVICES_NO_RC','PASS_RESET334_METAL_VIA_GRAPH_BOUND_TO_ALL334_NATIVE_DEVICES_NO_RC',1)]
    source=ROOT/'scripts/tx_driver_localpins_wire_native.py'
    result=derive(source.read_text(),edits);ast.parse(result)
    return result,dict(source_sha256=sha(source),exact_reversible_edits=edits)
def anchor_source(top,components):
    assert type(components)is int and components>0
    edits=[
      ('All91 divider devices:283 terminal planes','All334 reset-divider devices:1010 terminal planes',1),
      ('nssoc_clock_div4_load3p2_v1_layout',top,1),
      ("db=source/'raw_flat/result.lvsdb'","db=physical_source/'flat_lvs/result.lvsdb'",1),
      ('assert len(devices)==91','assert len(devices)==334',1),
      ('Counter(npn13G2=34,rppd=33,cap_cmim=6,ptap1=18)','Counter(npn13G2=106,rppd=130,cap_cmim=8,ptap1=90)',1),
      ('assert len(owner)==37','assert len(owner)=='+str(components),1),
      ("assert len(rows)==283 and sum('reference_label'in r for r in rows)==198 and len(public)==7","assert len(rows)==1010 and sum('reference_label'in r for r in rows)==684 and len(public)==11",1),
      ("assert len(observed)==283 and len({(r['device'],r['terminal']) for r in observed})==283","assert len(observed)==1010 and len({(r['device'],r['terminal']) for r in observed})==1010",1),
      ('PASS_ALL283_DIVIDER_TERMINALS_BOUND_WITH198_METAL85_BODY_AND_SEVEN_FAULTS_NOT_RC_ACCEPTANCE','PASS_ALL1010_RESET_TERMINALS_BOUND_WITH684_METAL326_BODY_AND_SEVEN_FAULTS_NOT_RC_ACCEPTANCE',1),
      ('devices=91,terminals=283,metal_terminals=198,body_terminals=85,public_ports=7','devices=334,terminals=1010,metal_terminals=684,body_terminals=326,public_ports=11',1),
      ('wire_components=37','wire_components='+str(components),1),
      ('OUT=Path(sys.argv[1]);generate()',"OUT=Path(sys.argv[1]);generate(OUT,OUT)",1)]
    source=ROOT/'scripts/pll_divider_load3p2_anchors_native.py'
    result=derive(source.read_text(),edits);ast.parse(result)
    return result,dict(source_sha256=sha(source),exact_reversible_edits=edits)
def run(out,top,app,execute,pcell):
    gds=out/'layout'/(top+'.gds');before=sha(gds)
    source,graph_proof=graph_source(top,before);script=out/'wire-native.py';script.write_text(source);graph_proof['generated_sha256']=sha(script)
    execute([app,'python',script],out,'wire-graph')
    graph=json.loads((out/'native01/result.json').read_text())
    assert graph['native_device_count']==334 and graph['native_terminal_count']==1010 and set(graph['native_ports'])==PORTS
    assert graph['no_wire_geometry_change']and graph['no_component_union_by_native_label']
    components=graph['wire_component_count'];assert type(components)is int and components==len(graph['wire_components'])>0
    assert graph['native_electrical_net_count']==len({t['native_cluster']for t in graph['native_net_coverage']if t['device_terminals']})
    assert graph['wire_rc_extracted']is graph['full_pex_qualified']is False
    shutil.copyfile(pcell,out/'npn13G2_code.py')
    source,anchor_proof=anchor_source(top,components);script=out/'anchors-native.py';script.write_text(source);anchor_proof['generated_sha256']=sha(script)
    execute([app,'python',script,out],out,'all-terminal-anchors')
    anchors=json.loads((out/'anchors.json').read_text())
    assert len(anchors['negative_controls'])==7 and all(v['rejected']for v in anchors['negative_controls'])
    for k,v in dict(devices=334,terminals=1010,metal_terminals=684,body_terminals=326,public_ports=11,wire_components=components).items():assert anchors['counts'][k]==v,(k,anchors['counts'][k])
    assert len(anchors['rows'])==1010 and sha(gds)==before
    assert sum(v['model']=='cap_cmim'for v in anchors['rows'])==16
    assert anchors['wire_rc_extracted']is anchors['qualified_pex']is anchors['serial_phy_complete']is False
    assert sha(out/'wire-native.py')==graph_proof['generated_sha256']and sha(out/'anchors-native.py')==anchor_proof['generated_sha256']
    return dict(status='PASS_FRESH334_ALL_METAL1010_TERMINALS_AND7_FAULTS_NOT_RC',
      graph=graph,anchors=anchors,graph_derivation=graph_proof,anchor_derivation=anchor_proof,
      sources_unchanged=True,physical_GDS_sha256=before,wire_rc_extracted=False,electrical_accepted=False,full_phy_accepted=False)
