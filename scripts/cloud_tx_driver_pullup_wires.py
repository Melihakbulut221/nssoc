#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh pullup metal/via graph and actual contact planes, before wire RC."""
import argparse,json,os,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_tx_driver_localpins_anchors as anchors
from cloud_tx_driver_pullup_junctions import SOURCES,SELECTED
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
METHOD_SHA='171fba4772907101b840342696477c377e4f249dd915a9761a2f6f1b9b479225'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=sorted(SOURCES),required=True);parser.add_argument('--anchors',action='store_true');args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    spec=SOURCES[args.variant];out=ROOT/('hw/soc/out/cloud-tx-driver-pullup-wires-'+args.variant);source=out/'source'
    top=spec.get('top','nssoc_tx_input_driver_v7_physical_pullup_'+args.variant+'_v1')
    if args.anchors:
        anchors.OUT=out;anchors.physical.TOP=top;anchors.generate(source=out,physical_source=source);return
    out.mkdir(parents=True,exist_ok=False);reports.OUT=out
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=args.variant,source=spec,qualified_pex=False,serial_phy_complete=False,wire_rc_extracted=False,mainchip_integrated=False)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        selected=SELECTED+('check-raw_flat_lvs/audit.json',)
        prior,proof=reports.restore_report('tx-input-driver-pullup-'+args.variant,spec['run'],spec['summary'],spec['parts'],source,selected);result['restore']=proof
        assert prior['status']=='PASS_FULL_DRIVER_NATIVE_PHYSICAL_GATES_NOT_EXTRACTED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert prior['pullup_variant']==spec.get('pullup',args.variant) and sha(source/'base/layout.gds')==spec['gds']
        if 'series' in spec:
            assert prior['series_variant']==spec['series'] and prior['geometry']['physical_series_length_um']==spec['series_length']
            assert prior['source_head']==spec['source_head'] and prior['steps']['wrong_series']['expected_verdict_observed']
        assert all(v['expected_verdict_observed'] for v in prior['steps'].values() if 'expected_verdict_observed' in v)
        assert prior['steps']['wrong_pullup']['expected_verdict_observed']
        method=ROOT/'scripts/tx_driver_localpins_wire_native.py';assert sha(method)==METHOD_SHA
        original=method.read_text();adapted=original
        edits=[("P=B/'inputs/tx-input-driver-localpins/cloud-tx-input-driver-localpins'","P=B/'source'"),
          ('6f7a7cf92c1dc25a259acdbff779c7cce841128991abb780e13478aa84b4eb62',spec['gds']),
          ('nssoc_tx_input_driver_v7_physical_localpins_v1',top)]
        for old,new in edits:
            assert adapted.count(old)==1;adapted=adapted.replace(old,new)
        restored=adapted
        for old,new in reversed(edits):
            assert restored.count(new)==1;restored=restored.replace(new,old)
        assert restored==original
        native=out/'probe.py';native.write_text(adapted)
        result['method']=dict(original_sha256=METHOD_SHA,adapted_sha256=sha(native),exact_edits=edits,physics_or_coverage_changes=False)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256']=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        for label,cmd in [('native',[app,'python',native]),('anchors',[app,'python',Path(__file__).resolve(),'--variant',args.variant,'--anchors'])]:
            result[label+'_execution']=execute(cmd,out,label);save()
            if result[label+'_execution']['returncode']:
                print((out/(label+'.log')).read_text(errors='replace')[-14000:]);raise RuntimeError('Actual pullup '+label+' failed')
        geometry=json.loads((out/'native01/result.json').read_text());binding=json.loads((out/'anchors.json').read_text())
        assert geometry['status']=='PASS_FULL_DRIVER_METAL_VIA_GRAPH_BOUND_TO_ALL100_NATIVE_DEVICES_NO_RC'
        assert geometry['native_device_count']==100 and len(geometry['native_ports'])==6 and geometry['wire_component_count']==10
        assert binding['status']=='PASS_ALL372_DRIVER_TERMINALS_BOUND_WITH272_METAL100_BODY_AND_FOUR_FAULTS_NOT_RC_ACCEPTANCE'
        counts=binding['counts'];assert counts['devices']==100 and counts['terminals']==372 and counts['metal_terminals']==272 and counts['body_terminals']==100
        assert len(binding['negative_controls'])==4 and all(x['rejected']for x in binding['negative_controls'])
        assert all(sha(Path(p))==digest for p,digest in binding['inputs'].items())
        assert all(sha(source/p)==prior['outputs'][p]for p in selected) and sha(method)==METHOD_SHA
        result.update(geometry=geometry,binding=binding,source_unchanged=True,status='PASS_ACTUAL_PULLUP_WIRE_GRAPH_AND372_TERMINAL_ANCHORS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE')
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
