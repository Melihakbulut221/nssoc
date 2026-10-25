#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Extract actual pullup GDS raw devices and junctions, never substitute old wires."""
import argparse,copy,json,os,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_tx_driver_localpins_junctions as junctions
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'l2p4-series-l6p2':dict(run=38944147428,summary='05b76749dd3bf044096a98724e4bc2fb37d261849871e002d9be69b823c36b7b',parts='08b4af56bd30b4124e1c0dda572cc5498ce3148b1f67389de34004fb02ba4b0f',gds='a151458075fc0ae554b34151bc785525a87e336d0e6df3ddecd3d59189654262',length=2.4,pullup='l2p4',series='l6p2',series_length=6.2,top='nssoc_tx_input_driver_v7_physical_pullup_l2p4_series_l6p2_v1',source_head='4f17848a3ac042528fb92d978697808c0584ad22'),
 'l2p7':dict(run=38932966041,summary='67517379dac5dfc5f0f538af4ba4bd597a12690e69b3460698b954db5f6a7788',parts='a837e7567842c0a731d1fe0881edb08cc475a7ea36d1c9bbb3ea6a8a84ce15a4',gds='1c55f7274f9df9d5b54cddf6abcfd34e6c061c9c4a64d88e842af1885bc81d89',length=2.7),
 'l2p4':dict(run=38932966041,summary='09e20aaac5ba975b5023c84c9009a23ece57b5105ac07f267fbc95a81720119e',parts='80378f2f3f8e5436875bb80792bab541aacbb0ea0c14dc89ef021f4f62b1866f',gds='173a68c27119333f013de4a57b3a9cf7892f8655f98f74b0e8fbdc95042a3215',length=2.4),
}
SELECTED=('base/layout.gds','base/result.json','base/effective-driver.inc','base/raw.cir','base/aggregate.cir','check-raw_flat_lvs/result.lvsdb','check-aggregate_flat_lvs/result.lvsdb')

def verify_resistors(record):
    raw=record['native']['raw_flat_lvs']['devices']
    actual=[r for r in raw if r['model']=='rppd']
    cores=[r for r in record['source_core_rows'] if r['model']=='rppd']
    assert len(actual)==len(cores)==4,'Resistor census changed'
    used=set();bound=[]
    for core in cores:
        endpoints=set(core['nets'][:2]);matches=[]
        for r in actual:
            terminals=r['terminals']
            assert set(terminals)=={'rppd_1','rppd_2','rppd_sub'}
            if {terminals[k]['logical_net'] for k in ('rppd_1','rppd_2')}==endpoints:matches.append(r)
        assert len(matches)==1,'Resistor endpoint ownership changed'
        r=matches[0];assert r['id'] not in used;used.add(r['id'])
        assert r['terminals']['rppd_sub']['logical_net']=='BULK','Resistor body changed'
        p=r['parameters'];assert set(p)=={'w','l','ps','b','m'}
        assert abs(p['w']-junctions.microns(core['params']['w']))<1e-9,'Actual resistor width mismatch'
        assert abs(p['l']-junctions.microns(core['params']['l']))<1e-9,'Actual resistor length mismatch'
        assert p['ps']==p['b']==0 and p['m']==1,'Resistor parasitic or multiplicity mismatch'
        bound.append(dict(path=core['path'],native_id=r['id'],parameters=p,terminals=r['terminals']))
    assert len(used)==4
    return bound

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=sorted(SOURCES),required=True);parser.add_argument('--export',action='store_true');args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    spec=SOURCES[args.variant];out=ROOT/('hw/soc/out/cloud-tx-driver-pullup-junctions-'+args.variant);source=out/'source'
    junctions.OUT=out;junctions.TOP=spec.get('top','nssoc_tx_input_driver_v7_physical_pullup_'+args.variant+'_v1');junctions.SOURCE=spec
    if args.export:junctions.export(source=source);return
    out.mkdir(parents=True,exist_ok=False);reports.OUT=out
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=args.variant,source=spec,qualified_pex=False,serial_phy_complete=False,mainchip_integrated=False,wire_parasitics_included=False,simulator_checked=False)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        prior,proof=reports.restore_report('tx-input-driver-pullup-'+args.variant,spec['run'],spec['summary'],spec['parts'],source,SELECTED)
        result['restore']=proof
        assert prior['status']=='PASS_FULL_DRIVER_NATIVE_PHYSICAL_GATES_NOT_EXTRACTED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        assert prior['pullup_variant']==spec.get('pullup',args.variant) and prior['geometry']['physical_resistor_length_um']==spec['length']
        if 'series' in spec:
            assert prior['series_variant']==spec['series'] and prior['geometry']['physical_series_length_um']==spec['series_length']
            assert prior['source_head']==spec['source_head']
        checks={k:v for k,v in prior['steps'].items() if 'expected_verdict_observed' in v}
        expected_checks={'raw_lvs','raw_flat_lvs','aggregate_lvs','aggregate_flat_lvs','wrong_width','hv_gate_open','input_open','missing_well_tap','missing_body_marker','body_short','drc','offgrid','wrong_pullup'}
        if 'series' in spec:expected_checks.add('wrong_series')
        assert set(checks)==expected_checks
        assert all(v['expected_verdict_observed'] for v in checks.values())
        assert json.loads((source/'base/result.json').read_text())==prior['geometry']
        assert sha(source/'base/layout.gds')==spec['gds']
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256']=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        result['export']=execute([app,'python',Path(__file__).resolve(),'--variant',args.variant,'--export'],out,'export');save()
        if result['export']['returncode']:
            print((out/'export.log').read_text(errors='replace')[-14000:]);raise RuntimeError('Actual pullup native export failed')
        junctions.audit();result['junction_audit']=json.loads((out/'audit.json').read_text())
        native=json.loads((out/'native.json').read_text());assert native['gds_sha256']==spec['gds'] and native['source_run']==spec['run']
        result['resistors']=verify_resistors(native)
        pullup=next(r for r in result['resistors'] if r['path']=='xdriver.xup');assert abs(pullup['parameters']['l']-spec['length'])<1e-9
        targets=[('old_pullup_length',pullup,3.08),('wrong_pullup_body',pullup,None)]
        if 'series' in spec:
            series=next(r for r in result['resistors'] if r['path']=='xdriver.xin')
            assert abs(series['parameters']['l']-spec['series_length'])<1e-9
            targets.append(('old_series_length',series,6.92))
        controls=[]
        for fault,target,wrong_length in targets:
            altered=copy.deepcopy(native);r=next(r for r in altered['native']['raw_flat_lvs']['devices'] if r['id']==target['native_id'])
            if wrong_length is not None:r['parameters']['l']=wrong_length
            else:r['terminals']['rppd_sub']['logical_net']='avss'
            (out/(fault+'.json')).write_text(json.dumps(altered,indent=2)+'\n')
            try:verify_resistors(altered)
            except AssertionError as error:controls.append(dict(fault=fault,rejected=True,reason=str(error)))
            else:raise AssertionError('Accepted actual native resistor corruption '+fault)
        result['resistor_controls']=controls
        assert all(sha(source/p)==prior['outputs'][p] for p in SELECTED)
        result['source_unchanged']=True
        result['status']='PASS_ACTUAL_PULLUP_RAW100_JUNCTIONS_AND_RESISTOR_BINDINGS_NOT_WIRE_RC_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p!=out/'result.json'};save()
if __name__=='__main__':main()
