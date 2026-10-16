#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual clock metal graph, with unchanged native conductor ownership method."""
import argparse,json,os,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from cloud_tx_clock_reference_lef import SOURCES,TOP
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
METHOD_SHA='171fba4772907101b840342696477c377e4f249dd915a9761a2f6f1b9b479225'
def main():
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=sorted(SOURCES),required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true';out=ROOT/('hw/soc/out/cloud-tx-clock-reference-wires-'+args.variant);out.mkdir(parents=True,exist_ok=False);reports.OUT=out
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=args.variant,qualified_pex=False,wire_rc_extracted=False,terminal_reference_planes_complete=False,serial_phy_complete=False)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        spec=SOURCES[args.variant];source=out/'source';selected=('layout/'+TOP+'.gds','layout/result.json','check/lvs_flat/result.lvsdb','check/lvs_flat/audit.json')
        prior,proof=reports.restore_report('tx-clock-reference-'+args.variant,38941785196,spec['summary'],spec['parts'],source,selected);result['source']=proof
        assert prior['source_head']=='4a6550887640d452523888967c76eb709ef60277'and prior['source_unchanged']and prior['variant']==args.variant
        assert prior['status']=='PASS_NATIVE_CLOCK_REFERENCE_PHYSICAL_GATES_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert sha(source/'layout'/(TOP+'.gds'))==spec['gds']
        method=ROOT/'scripts/tx_driver_localpins_wire_native.py';assert sha(method)==METHOD_SHA;original=method.read_text();adapted=original
        edits=[
          ("P=B/'inputs/tx-input-driver-localpins/cloud-tx-input-driver-localpins'","P=B/'source'"),
          ("P/'base/layout.gds'","P/'layout/nssoc_tx_clock_reference_layout_v1.gds'"),
          ('check-raw_flat_lvs','check/lvs_flat'),
          ('6f7a7cf92c1dc25a259acdbff779c7cce841128991abb780e13478aa84b4eb62',spec['gds']),
          ('nssoc_tx_input_driver_v7_physical_localpins_v1',TOP),
          ('c.pin_count()==6','c.pin_count()==4'),
          ('dict(sg13_hv_nmos=40,sg13_lv_nmos=22,sg13_lv_pmos=22,ptap1=10,ntap1=2,rppd=4)','dict(npn13G2=1,rppd=2,ptap1=3)'),
          ("'full_driver_wires'","'clock_reference_wires'"),
          ("'DRIVERWIRES'","'CLOCKWIRES'"),
          ('PASS_FULL_DRIVER_METAL_VIA_GRAPH_BOUND_TO_ALL100_NATIVE_DEVICES_NO_RC','PASS_CLOCK_METAL_VIA_GRAPH_BOUND_TO_ALL6_NATIVE_DEVICES_NO_RC')]
        for old,new in edits:
            assert adapted.count(old)==(2 if old=='check-raw_flat_lvs'else 1),(old,adapted.count(old));adapted=adapted.replace(old,new)
        back=adapted
        for old,new in reversed(edits):back=back.replace(new,old)
        assert back==original,'Undeclared extraction algorithm change'
        native=out/'probe.py';native.write_text(adapted)
        result['method']=dict(original_sha256=METHOD_SHA,adapted_sha256=sha(native),exact_edits=edits,conductor_geometry_algorithm_unchanged=True)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256']
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        result['native_execution']=execute([app,'python',native],out,'native');save()
        assert result['native_execution']['returncode']==0,(out/'native.log').read_text()[-10000:]
        geometry=json.loads((out/'native01/result.json').read_text());assert geometry['status']=='PASS_CLOCK_METAL_VIA_GRAPH_BOUND_TO_ALL6_NATIVE_DEVICES_NO_RC'
        assert geometry['native_device_count']==6 and geometry['native_terminal_count']==16 and geometry['wire_component_count']==5
        assert set(geometry['native_ports'])=={'avdd','cm','avss','sub'}
        assert geometry['no_wire_geometry_change']and geometry['no_component_union_by_native_label']
        assert all(sha(source/p)==prior['outputs'][p]for p in selected)and sha(method)==METHOD_SHA
        result.update(geometry=geometry,source_unchanged=True,status='PASS_ACTUAL_CLOCK6_WIRE_GRAPH_FIVE_COMPONENTS_NOT_TERMINAL_RC_OR_ELECTRICAL_ACCEPTANCE')
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
