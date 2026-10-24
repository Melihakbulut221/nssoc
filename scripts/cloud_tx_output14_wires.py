#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Extract actual TX output14 metal graph without merging by logical labels."""
import json,os,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output14-wires'
TOP='nssoc_tx_cml_layout'
METHOD_SHA='171fba4772907101b840342696477c377e4f249dd915a9761a2f6f1b9b479225'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,wire_rc_extracted=False,terminal_reference_planes_complete=False,full_phy_accepted=False,parent_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-output14-physical-pass-20261021.json').read_text())
        assert pin['run']==39564026768 and pin['summary_sha256']=='8f434b1368bcf613ca2f32c4eeebc528d3e131a243299bf6df09f609c293f9fa'
        selected=('layout/'+TOP+'.gds','layout/result.json','layout/schematic.cir','check/lvs_flat/result.lvsdb','check/lvs_flat/audit.json','check/lvs/result.lvsdb')
        source=OUT/'source'
        prior,proof=reports.restore_report('tx-output14-physical',pin['run'],pin['summary_sha256'],pin['parts_sha256'],source,selected);r['physical_source']=proof
        assert prior==pin['report']and prior['sources_unchanged']
        assert prior['source_head']=='3d8c55b8830336e654d907ff115a807f760e8094'
        assert prior['status']=='PASS_ACTUAL_TX_OUTPUT14_NATIVE_PHYSICAL_AND_PARENT_ENDPOINT_BINDING_REQUIRES_FRESH_RC_AND_PARENT_ROUTE'
        assert len(prior['actual_output_binding']['controls'])==6 and all(x['rejected']for x in prior['actual_output_binding']['controls'])
        steps=prior['physical_checks']['steps'];assert len(steps)==9
        assert all(s['status']==('PASS'if n in ('drc','lvs','lvs_flat')else'REJECTED_EXPECTED_FAULT')for n,s in steps.items())
        gds=source/'layout'/(TOP+'.gds')
        assert sha(gds)==pin['gds_sha256']=='e3502ee90dae5af99e7ab03ef443197f84c71613189703e8a4b112db77053ef5'
        method=ROOT/'scripts/tx_driver_localpins_wire_native.py';assert sha(method)==METHOD_SHA
        original=method.read_text();adapted=original
        edits=[
          ('nssoc_tx_input_driver_v7_physical_localpins_v1',TOP),
          ("P=B/'inputs/tx-input-driver-localpins/cloud-tx-input-driver-localpins'","P=B/'source'"),
          ("P/'base/layout.gds'","P/'layout/nssoc_tx_cml_layout.gds'"),
          ('check-raw_flat_lvs','check/lvs_flat'),
          ('6f7a7cf92c1dc25a259acdbff779c7cce841128991abb780e13478aa84b4eb62',pin['gds_sha256']),
          ('c.pin_count()==6','c.pin_count()==8'),
          ('dict(sg13_hv_nmos=40,sg13_lv_nmos=22,sg13_lv_pmos=22,ptap1=10,ntap1=2,rppd=4)','dict(npn13G2=4,rsil=2,ptap1=8)'),
          ("'full_driver_wires'","'tx_output_wires'"),
          ("'DRIVERWIRES'","'TXOUTPUTWIRES'"),
          ('PASS_FULL_DRIVER_METAL_VIA_GRAPH_BOUND_TO_ALL100_NATIVE_DEVICES_NO_RC','PASS_TX_OUTPUT_METAL_VIA_GRAPH_BOUND_TO_ALL14_NATIVE_DEVICES_NO_RC')]
        for a,b in edits:
            assert adapted.count(a)==(2 if a=='check-raw_flat_lvs'else 1),(a,adapted.count(a));adapted=adapted.replace(a,b)
        back=adapted
        for a,b in reversed(edits):back=back.replace(b,a)
        assert back==original,'Undeclared conductor algorithm change'
        native=OUT/'probe.py';native.write_text(adapted)
        r['method']=dict(original_sha256=METHOD_SHA,adapted_sha256=sha(native),exact_edits=edits,conductor_geometry_algorithm_unchanged=True)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256']
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from check_pcie_rx_cell import execute
        r['native_execution']=execute([app,'python',native],OUT,'native');save()
        assert r['native_execution']['returncode']==0,(OUT/'native.log').read_text()[-10000:]
        geometry=json.loads((OUT/'native01/result.json').read_text());r['geometry']=geometry;save()
        assert geometry['status']=='PASS_TX_OUTPUT_METAL_VIA_GRAPH_BOUND_TO_ALL14_NATIVE_DEVICES_NO_RC'
        assert geometry['native_device_count']==14 and geometry['native_terminal_count']==38 and geometry['wire_component_count']==9
        assert set(geometry['native_ports'])==set('INP INN OUTP OUTN AVDD AVSS SUB IREF'.split())
        assert geometry['no_wire_geometry_change']and geometry['no_component_union_by_native_label']
        assert all(sha(source/p)==prior['outputs'][p]for p in selected)and sha(method)==METHOD_SHA
        r.update(sources_unchanged=True,status='PASS_ACTUAL_TX_OUTPUT14_WIRE_GRAPH_NINE_COMPONENTS_REQUIRES_TERMINAL_PLANES_RC_AND_PARENT_ROUTE')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
