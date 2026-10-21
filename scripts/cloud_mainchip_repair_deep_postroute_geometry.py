#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify completed repaired-chip DRT against its exact proved global input."""
import json,os,subprocess,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
from cloud_mainchip_postroute_review import api,source_hash
from check_mainchip_repair_deep_completed_source import validate
from cloud_mainchip_repair_deep_drt import log_proof
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-repair-deep-postroute-geometry'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
        route_complete=False,final_timing_complete=False,full_phy_accepted=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        methods=json.loads((ROOT/'scripts/mainchip-repair-deep-postroute-methods.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in methods.items())
        gp=json.loads((ROOT/'docs/evidence/mainchip-repair-deep-global-pass-20261021.json').read_text())
        gs=gp['report']['step_path']
        before,bproof=reports.restore_report(gp['group'],gp['run'],gp['summary_sha256'],gp['parts_sha256'],
            OUT/'global',[gs+'/fresh-fanout-global.odb',gs+'/config.json'])
        assert before==gp['report']and before['sources_unchanged']and before['native_global_complete']
        assert before['geometry']['instance_count']==153130 and before['fixed_clock']['original_physical_route_preserved']
        a=OUT/'global'/gs/'fresh-fanout-global.odb'
        assert sha(a)==before['global_odb_sha256']=='6bf5a055467ffea2e4fb0059ffcac4293d939171b0e17af6e224aee13b41c00c'
        hp=json.loads((ROOT/'docs/evidence/mainchip-repair-deep-handoff-pass-20261021.json').read_text())
        handoff,hproof=reports.restore_report(hp['group'],hp['run'],hp['summary_sha256'],hp['parts_sha256'],OUT/'handoff',['repair/candidate.v'])
        nl=OUT/'handoff/repair/candidate.v'
        assert handoff['sources_unchanged']and handoff['status']=='PASS_PROVEN_REPAIR_INPUT_READY_FOR_FRESH_GLOBAL_AND_DETAIL_ROUTE'
        assert sha(nl)==handoff['candidate_netlist_sha256']==before['candidate_netlist_sha256']=='3a200ea79143bc3b723905495085c317083deac7cc6b10ad3033b186293d7030'
        selected=json.loads(os.environ['NSSOC_COMPLETED_DRT'])
        live=api('actions/runs/'+str(selected['run']))
        assert live['status']=='completed'and live['conclusion']=='success','Never consume unfinished route'
        names=['work/detailed-route.odb','work/detailed-route.drc','work/native.log','work/boots.log','work/before-guide-read.odb','work/drt-done']
        actual,aproof=reports.restore_report(selected['group'],selected['run'],selected['summary_sha256'],selected['parts_sha256'],OUT/'routed',names)
        portable=json.loads((ROOT/'docs/evidence/mainchip-portable-runtime-pass-20261020.json').read_text())
        validate(selected,live,actual,portable['report']['image_id'])
        controller='scripts/cloud_mainchip_repair_deep_drt'+('_continuation'if 'continuation' in live['path']else'')+'.py'
        assert source_hash(controller,selected['source_head'])==selected['controller_sha256']==sha(ROOT/controller)
        native=log_proof((OUT/'routed/work/native.log').read_bytes(),(OUT/'routed/work/boots.log').read_bytes())
        assert native==actual['native_log']
        drc=OUT/'routed/work/detailed-route.drc'
        if native['completed_violation_counts'][-1]==0:
            assert not drc.read_text().strip(),'Zero native count but nonempty final DRC report'
        else:
            assert drc.read_text().strip(),'Nonzero native count but empty final DRC report'
        r['native_drc_report']=dict(sha256=sha(drc),bytes=drc.stat().st_size,
            final_native_count=native['completed_violation_counts'][-1],zero_count_and_empty_report_consistent=True)
        assert(OUT/'routed/work/drt-done').read_text().strip()
        assert sha(OUT/'routed/work/before-guide-read.odb')==sha(a)
        b=OUT/'routed/work/detailed-route.odb';assert sha(b)==actual['routed_odb_sha256']
        r.update(route_complete=True,completed_route_source=aproof,completed_route_descriptor=selected,
            global_source=bproof,handoff_source=hproof,candidate_netlist_path=str(nl),
            candidate_netlist_sha256=sha(nl),reported_native_drt_violation_counts=native['completed_violation_counts'])
        app=Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        protected={str(p):sha(p)for p in [a,b,nl,*[ROOT/p for p in methods]]}
        def run(method,label,extra):
            env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
            env.update(NSSOC_TOPOLOGY_BEFORE=str(a),NSSOC_TOPOLOGY_AFTER=str(b),**extra)
            with(OUT/(label+'.log')).open('w')as log:
                code=subprocess.call([str(app),'openroad','-exit','-python',str(ROOT/method)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            r.setdefault('commands',[]).append(dict(label=label,returncode=code));save()
            if code:print((OUT/(label+'.log')).read_text(errors='replace')[-14000:],flush=True)
            assert code==0,(label,code)
        run('scripts/check_mainchip_repair_deep_routed_topology.py','native-topology',dict(NSSOC_TOPOLOGY_OUT=str(OUT/'topology.json')))
        topology=json.loads((OUT/'topology.json').read_text())
        assert topology['status']=='PASS_NATIVE_FANOUT_ROUTED_TOPOLOGY_AND_GEOMETRY_NOT_LVS'
        assert topology['proof']['retained_instances']==153130 and topology['proof']['added_diode_count']==0
        assert set(topology['rejected'])=={'changed_master','changed_pin','changed_location','non_diode_addition'}
        run('scripts/check_onehot_fixed_clock_route.py','native-fixed-clock',dict(NSSOC_CLOCK_ROUTE_PROOF_OUT=str(OUT/'fixed-clock.json')))
        fixed=json.loads((OUT/'fixed-clock.json').read_text());assert fixed['original_physical_route_preserved']
        assert all(sha(p)==h for p,h in protected.items())
        r.update(status='PASS_COMPLETED_NATIVE_ROUTE_GEOMETRY_REQUIRES_DRC_ANTENNA_RC_STA',
            topology=topology,fixed_clock=fixed,sources_unchanged=True,protected_inputs=protected)
    except BaseException as e:r.update(status='FAIL_REPAIRED_ROUTE_GEOMETRY',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
