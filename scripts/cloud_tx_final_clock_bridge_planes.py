#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Extract unchanged bridge wire geometry and actual terminal reference planes."""
import json,os,shutil,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from cloud_tx_final_clock_bridge_native import SOURCE,TOP,bind
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-final-clock-bridge-planes'
NATIVE=dict(run=39374716164,head='a71dfc2406400d53f585a0c51a726ac701cb599f',
 summary='11c921b760b5c6ea901c2bf948a6dc752eda2aac8d0878cabdc2ba92e7909b23',
 parts='02d7051f7b35161cc6815a73a3a07242d69aa8137c6b3b3035b3c744517e61eb',
 model='41829ea61c863aff655b216d0b17e86fff0594cf385ea68ab09622d12d098679')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
           wire_rc_extracted=False,qualified_pex=False,qualified_substrate=False,
           electrically_validated=False,serial_phy_complete=False,mainchip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        methods=json.loads((ROOT/'scripts/tx-final-clock-bridge-planes-methods.json').read_text())
        for m in methods:
            original=(ROOT/m['baseline']).read_text()
            assert sha(ROOT/m['baseline'])==m['baseline_sha256']
            adapted=original
            for old,new in m['edits']:
                assert adapted.count(old)==m['occurrences'][old],old
                adapted=adapted.replace(old,new)
            assert adapted==(ROOT/m['path']).read_text()
            assert sha(ROOT/m['path'])==m['sha256']
        physical=OUT/'source'
        selected=('layout/'+TOP+'.gds','layout/result.json','check/lvs_flat/result.lvsdb','check/lvs_flat/audit.json')
        prior,proof=reports.restore_report('tx-final-clock-bridge',SOURCE['run'],SOURCE['summary'],SOURCE['parts'],physical,selected)
        assert prior['source_head']==SOURCE['head'] and prior['source_unchanged']
        assert prior['status']=='PASS_NATIVE_CLOCK_BRIDGE_PHYSICAL_GATES_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
        r['physical_source']=proof
        dest=OUT/'native-source'
        native_prior,native_proof=reports.restore_report('tx-final-clock-bridge-native',NATIVE['run'],NATIVE['summary'],NATIVE['parts'],dest,('native.json','bridge2.spice'))
        assert native_prior['source_head']==NATIVE['head'] and native_prior['source_unchanged']
        assert native_prior['status']=='PASS_NATIVE_BRIDGE2_TERMINALS_FINITE_CONTACT_MODEL_AND_30_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
        assert len(native_prior['binding_controls'])==20 and all(c['rejected']for c in native_prior['binding_controls'])
        assert len(native_prior['model_controls'])==10 and all(c['rejected']for c in native_prior['model_controls'])
        native=json.loads((dest/'native.json').read_text())
        assert bind(native)==native_prior['bindings']
        assert sha(dest/'bridge2.spice')==NATIVE['model']
        r['native_source']=native_proof
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256']
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        probe=OUT/'probe.py';shutil.copyfile(ROOT/'scripts/tx_final_clock_bridge_wires_native.py',probe)
        r['wire_execution']=execute([app,'python',probe],OUT,'wires');save()
        assert r['wire_execution']['returncode']==0,(OUT/'wires.log').read_text()[-10000:]
        geometry=json.loads((OUT/'native01/result.json').read_text())
        assert geometry['status']=='PASS_BRIDGE_METAL_VIA_GRAPH_BOUND_TO_ALL2_NATIVE_DEVICES_NO_RC'
        assert geometry['native_device_count']==2 and geometry['native_terminal_count']==5 and geometry['wire_component_count']==3
        assert set(geometry['native_ports'])=={'sp','sn','sub'}
        assert geometry['no_wire_geometry_change'] and geometry['no_component_union_by_native_label']
        r['geometry']=geometry
        pcell=OUT/'rppd_code.py'
        fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/rppd_code.py','58d53384ef0bb92a4fa413d3c92e8dcbcb8f422c5205da9260129049f07f1d6b',pcell)
        r['anchor_execution']=execute([app,'python',ROOT/'scripts/tx_final_clock_bridge_anchors_native.py',OUT],OUT,'anchors');save()
        assert r['anchor_execution']['returncode']==0,(OUT/'anchors.log').read_text()[-10000:]
        planes=json.loads((OUT/'anchors.json').read_text())
        assert planes['status']=='PASS_ALL5_BRIDGE_TERMINALS_BOUND_WITH3_METAL2_BODY_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE'
        assert planes['counts']==dict(devices=2,terminals=5,metal_terminals=3,body_terminals=2,public_ports=3,unique_reference_planes=6,wire_components=3)
        assert len(planes['negative_controls'])==6 and all(c['rejected']for c in planes['negative_controls'])
        native_rows={d['id']:d for d in native['modes']['lvs_flat']['devices']}
        for row in planes['rows']:
            d=native_rows[row['device']];t=d['terminals'][row['terminal']]
            assert d['model']==row['model'] and t['cluster']==str(row['native_cluster'])
        assert all(sha(Path(p))==v for p,v in planes['inputs'].items())
        assert all(sha(physical/p)==prior['outputs'][p] for p in selected)
        assert sha(dest/'native.json')==native_prior['outputs']['native.json']
        assert sha(dest/'bridge2.spice')==NATIVE['model']
        assert all(sha(ROOT/m['path'])==m['sha256'] and sha(ROOT/m['baseline'])==m['baseline_sha256'] for m in methods)
        r.update(status='PASS_NATIVE_BRIDGE2_WIRE_GRAPH_ALL5_TERMINAL_PLANES_AND_SIX_FAULTS_NOT_RC_ACCEPTANCE',
                 binding=planes,source_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
