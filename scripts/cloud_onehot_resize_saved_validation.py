#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finish native verification from saved route states without rerouting."""
import json,os,re,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
import check_final_native_antenna_counts as ant
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-onehot-resize-saved-validation'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,final_timing_complete=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['antenna_controls']=ant.controls()
        pin=json.loads((ROOT/'docs/evidence/onehot-resize-route-report-rejection-20261019.json').read_text())
        selected=[n for n in pin['report']['outputs']if n.startswith('run/')and (n.endswith('state_out.json')or n.endswith('antenna.rpt')or n.endswith('native-spef-integrity.json')or n.endswith('native-sta-script-proof.json')or n.endswith('/max.rpt')or n.endswith('/min.rpt')or n.endswith('/sta.log')or n.endswith('/unpropagated.rpt'))]
        routeodb='run/2-openroad-detailedrouting/soc_top.odb';selected.append(routeodb)
        source=OUT/'source'
        prior,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],source,selected)
        assert prior==pin['report']and prior['returncode']==0 and prior['status']=='FAIL_OR_ERROR_NO_SOURCE_RESTART'
        r['source']=proof
        pp=json.loads((ROOT/'docs/evidence/onehot-resize-prepare-pass-20261018.json').read_text())
        assert prior['resize_source']['run']==pp['run']and prior['resize_source']['summary_sha256']==pp['summary_sha256']and prior['resize_source']['manifest_sha256']==pp['parts_sha256']
        before=OUT/'prepared'
        prep,pf=reports.restore_report('onehot-resize-prepare',pp['run'],pp['summary_sha256'],pp['parts_sha256'],before,['candidate.odb'])
        assert prep==pp['report']and prep['sources_unchanged']
        assert sha(before/'candidate.odb')==prep['candidate_odb_sha256']
        r['preparation']=pf
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        method=ROOT/'scripts/check_onehot_resize_routed_topology.py'
        assert sha(method)=='a2a814ed06ce7fdebce8e1e7ffdfea3ae17a5e4b0daea1473e6b1ced00c0ab85'
        protected={str(p):sha(p)for p in (Path(__file__),Path(ant.__file__),app,method,before/'candidate.odb',source/routeodb)}
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        env.update(NSSOC_TOPOLOGY_BEFORE=str(before/'candidate.odb'),NSSOC_TOPOLOGY_AFTER=str(source/routeodb),NSSOC_TOPOLOGY_OUT=str(OUT/'topology.json'))
        with(OUT/'topology.log').open('w')as log:
            code=subprocess.call([str(app),'openroad','-exit','-python',str(method)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        if code:print((OUT/'topology.log').read_text()[-10000:],flush=True)
        assert code==0
        r['routed_topology']=json.loads((OUT/'topology.json').read_text())
        assert r['routed_topology']['proof']['retained_instances']==146728 and len(r['routed_topology']['rejected'])==4
        antenna=json.loads((source/'run/3-openroad-checkantennas/state_out.json').read_text())
        text=(source/'run/3-openroad-checkantennas/reports/antenna.rpt').read_text()
        r['final_antenna']=ant.validate(text,antenna['metrics']);r['original_rejected_count_comparison']=dict(net_headings=len(re.findall(r'(?m)^\s*Net:\s*\S+',text)),earlier_route_metric=antenna['metrics']['route__antenna_violation__count'])
        physical=json.loads((source/'run/4-odb-reportdisconnectedpins/state_out.json').read_text())['metrics']
        r['physical']=dict(drc_errors=physical['route__drc_errors'],critical_disconnected_pins=physical['design__critical_disconnected_pin__count'])
        r['spef_integrity']=json.loads((source/'run/5-nssoc-onehotroutercx/native-spef-integrity.json').read_text())
        sta=source/'run/6-nssoc-onehotroutedsta'
        r['sta_script_proof']=json.loads((sta/'native-sta-script-proof.json').read_text())
        state=json.loads((sta/'state_out.json').read_text());r['corners']={}
        for corner in ['nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C']:
            folder=sta/corner;assert not(folder/'unpropagated.rpt').read_text().strip()
            assert 'NSSOC_ROUTED_ORIGINAL_CLOCKS_PROPAGATED'in(folder/'sta.log').read_text()
            paths={}
            for kind in ['max','min']:
                text=(folder/(kind+'.rpt')).read_text()
                blocks=re.split(r'(?m)(?=^Startpoint:)',text);blocks=[b for b in blocks if b.startswith('Startpoint:')]
                assert blocks,('Missing native detailed timing paths',corner,kind)
                paths[kind]=dict(path_count=len(blocks),first_eight_native_paths=blocks[:8],sha256=sha(folder/(kind+'.rpt')))
            r['corners'][corner]=dict(metrics={k:v for k,v in state['metrics'].items()if k.endswith('__corner:'+corner)},native_paths=paths)
        assert all(sha(source/n)==prior['outputs'][n]for n in selected)
        assert all(sha(Path(p))==v for p,v in protected.items())
        r.update(status='COMPLETE_NATIVE_SAVED_ROUTE_TOPOLOGY_FINAL_ANTENNA_AND_PATHS_NOT_SIGNOFF',sources_unchanged=True,scope='Original route rejection retained. Actual routed ODB compared to exact prepared candidate. Fresh antenna net/pin counts independently reproduced; earlier route counter retained separately. Original all-corner timing and complete max/min reports retained; no gates waived, no reroute, no full LVS/RC qualification or signoff.')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
