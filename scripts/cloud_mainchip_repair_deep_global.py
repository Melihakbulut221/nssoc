#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run original fresh global router on the deep repair's proved handoff."""
import hashlib,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_replay_onehot_logic as logic
from cloud_mainchip_postroute_review import api,source_hash
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-repair-deep-global'
HANDOFF=ROOT/'cloud-mainchip-repair-deep-handoff'
RUN=39678505610
HEAD='7fa406886aeffd0ee5822764e8abb0031ad8e5ba'
SUMMARY='90a1b21adb413d239ed80b74322242f925e53109b82f3352076fa9678a6ebde7'
PARTS='b6ebd219945fa614f5a0da8b2df02dc66fe604c256067badf3958075bbbb371f'
FRESH='22a6238e7786b75a715ac69ef06c0dc3ec17e590260d62ba869732e0f1d35551'
NETLIST='3a200ea79143bc3b723905495085c317083deac7cc6b10ad3033b186293d7030'
SDC='19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597'
def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def validate(r):
    assert r['source_head']==HEAD and r['sources_unchanged']
    assert r['status']=='PASS_PROVEN_REPAIR_INPUT_READY_FOR_FRESH_GLOBAL_AND_DETAIL_ROUTE'
    assert r['candidate_instance_count']==153130 and r['fresh_odb_sha256']==FRESH
    assert r['candidate_netlist_sha256']==NETLIST and r['source_sdc_sha256']==SDC
    assert r['fresh_fixed_clock']['original_physical_route_preserved']
    assert r['fresh_preparation']['proof']['all_non_wire_physical_def_preserved']
    assert r['fresh_preparation']['proof']['all_other_net_records_preserved']
    assert len(r['rejected_candidate_controls'])==4
    assert len(r['fresh_preparation']['controls'])==3
    assert all(v['rejected']for v in r['fresh_preparation']['controls'])
    assert r['candidate_proof']['status']=='PASS within scope'
    assert not r['native_routing_started'] and r['stale_spef_and_metrics_discarded']
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT;logic.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
        full_phy_accepted=False,final_timing_complete=False,detailed_route_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label,extra=None,auth=False):
        env=dict(os.environ)if auth else{k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        if extra:env.update(extra)
        with(OUT/(label+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code));save()
        if code:print((OUT/(label+'.log')).read_text(errors='replace')[-16000:],flush=True)
        assert code==0,(label,code)
    save()
    try:
        methods=json.loads((ROOT/'scripts/mainchip-repair-deep-global-methods.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in methods.items())
        live=api('actions/runs/'+str(RUN))
        assert live['status']=='completed'and live['conclusion']=='success'and live['run_attempt']==1
        assert live['head_sha']==HEAD and live['path']=='.github/workflows/mainchip-repair-deep-handoff-cloud.yml'
        assert source_hash('scripts/cloud_mainchip_repair_deep_handoff.py',HEAD)==sha(ROOT/'scripts/cloud_mainchip_repair_deep_handoff.py')
        source,digest,parts=logic.summary('mainchip-repair-deep-handoff',live)
        assert digest==SUMMARY and parts==PARTS;validate(source)
        import copy
        rejected=[]
        for name,change in [
            ('wrong-fresh-odb',lambda x:x.update(fresh_odb_sha256='0'*64)),
            ('changed-clock',lambda x:x['fresh_fixed_clock'].update(original_physical_route_preserved=False)),
            ('changed-census',lambda x:x.update(candidate_instance_count=152988)),
            ('stale-parasitics',lambda x:x.update(stale_spef_and_metrics_discarded=False))]:
            bad=copy.deepcopy(source);change(bad)
            try:validate(bad)
            except AssertionError:rejected.append(name)
            else:raise AssertionError('Accepted corrupt handoff: '+name)
        names=['fresh/candidate.odb','repair/candidate.v','candidate-state.json','trial-config.json','repair/native-repair.log']
        actual,receipt=reports.restore_report('mainchip-repair-deep-handoff',RUN,SUMMARY,PARTS,HANDOFF,names)
        assert actual==source
        r.update(handoff_source=receipt,rejected_handoff_controls=rejected);save()
        descriptor=source['original_input_descriptor']
        pin=json.loads((ROOT/'docs/evidence/mainchip-postroute-inputs-pass-20261021.json').read_text())
        assert all(descriptor[k]==pin[k]for k in ('run','group','source_head','controller_sha256','summary_sha256','parts_sha256'))
        assert not os.environ.get('NSSOC_COMPLETED_DRT')
        run([sys.executable,ROOT/'scripts/cloud_mainchip_postroute_review.py','--preflight-inputs'],
            'original-input-preflight',dict(NSSOC_INPUT_PACKAGE=json.dumps(descriptor)),auth=True)
        preflight=ROOT/'cloud-mainchip-postroute-review'
        pr=json.loads((preflight/'result.json').read_text())
        assert pr['status']=='PASS_NATIVE_POSTROUTE_INPUT_CONFIG_PREFLIGHT_NOT_ROUTED'and pr['sources_unchanged']
        contract=pr['input_contract'];assert contract==source['original_input_contract']
        package=preflight/'inputs/postroute-inputs'
        app=Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        state=json.loads((HANDOFF/'candidate-state.json').read_text())
        assert sha(state['odb'])==FRESH and sha(state['nl'])==NETLIST and sha(state['sdc'])==SDC
        assert not state['metrics'] and all(state[k]is None for k in ('spef','def','pnl','sdf'))
        assert all(sha(p)==h for p,h in source['state_dependencies'].items())
        trial=OUT/'trial-config.json';shutil.copyfile(HANDOFF/'trial-config.json',trial)
        assert sha(trial)==contract['configuration_sha256']
        initial=OUT/'initial-state.json';shutil.copyfile(HANDOFF/'candidate-state.json',initial)
        flow=ROOT/'hw/soc/pnr/mainchip_repair_fresh_global_flow.py'
        run([app,'python',flow,'--audit-config',package,OUT/'native-config.json'],'native-config')
        run([app,'openroad','-version'],'native-version')
        assert(OUT/'native-version.log').read_text().strip()=='dcf36133a369abc8f3c5e5738cd4d82e4903c0e0'
        protected={str(ROOT/n):v['sha256']for n,v in contract['input_files'].items()}
        protected.update({str(ROOT/n):v for n,v in methods.items()})
        protected.update({str(p):sha(p)for p in [Path(state['odb']),Path(state['nl']),Path(state['sdc']),trial,initial]})
        r.update(original_input_descriptor=descriptor,original_input_contract=contract,protected_inputs=protected,
            original_clock_periods_ns=[20,4,8,8],derating_percent=5,
            source_candidate_odb_sha256=FRESH,candidate_netlist_sha256=NETLIST,source_sdc_sha256=SDC)
        run_dir=OUT/'run';run_dir.mkdir(exist_ok=False)
        cmd=[app,'python',flow,'--flow','MainchipRepairFreshGlobal',
            '--pdk-root',ROOT/'hw/soc/tools/ciel-corrpre','--pdk','ihp-sg13g2','--scl','sg13g2_stdcell',
            '--force-run-dir',run_dir,'--with-initial-state',initial,'--to','NSSOC.RepairFreshGlobal',trial]
        r['status']='RUNNING_ORIGINAL_NATIVE_FRESH_GLOBAL_ON_PROVED_DEEP_REPAIR';save()
        run(cmd,'native-global')
        steps=[p for p in run_dir.iterdir()if p.is_dir()and p.name[0].isdigit()]
        assert len(steps)==1 and steps[0].name.endswith('nssoc-repairfreshglobal'),[p.name for p in steps]
        step=steps[0];odb=step/'fresh-fanout-global.odb';guides=step/'fresh-fanout.guide'
        assert odb.is_file()and guides.is_file()and guides.stat().st_size>0
        assert sha(odb)!=FRESH
        script=json.loads((step/'global-script-proof.json').read_text())
        assert script['native_global_unchanged'] and not script['native_detailed_route_started']
        native='\n'.join(p.read_text(errors='replace')for p in step.glob('*.log'))
        assert 'NSSOC_REPAIRED_FRESH_GLOBAL_ONLY_COMPLETE'in native
        assert 'NSSOC_FRESH_FANOUT_GUIDES_FROM_CURRENT_NATIVE_PINS'in native
        assert 'Start 0th optimization iteration'not in native
        geom=OUT/'geometry'
        run([app,'openroad','-exit','-python',ROOT/'scripts/check_mainchip_repair_global_geometry.py'],'native-geometry',
            dict(NSSOC_GLOBAL_BEFORE=state['odb'],NSSOC_GLOBAL_AFTER=str(odb),NSSOC_GLOBAL_GEOMETRY_OUT=str(geom)))
        geometry=json.loads((geom/'result.json').read_text())
        assert geometry['status']=='PASS_GLOBAL_GUIDE_STAGE_PHYSICAL_DEF_EXACT_EXCEPT_GCELLGRID'
        run([app,'openroad','-exit','-python',ROOT/'scripts/check_onehot_fixed_clock_route.py'],'native-fixed-clock',
            dict(NSSOC_TOPOLOGY_BEFORE=state['odb'],NSSOC_TOPOLOGY_AFTER=str(odb),NSSOC_CLOCK_ROUTE_PROOF_OUT=str(OUT/'fixed-clock.json')))
        fixed=json.loads((OUT/'fixed-clock.json').read_text());assert fixed['original_physical_route_preserved']
        # Preserve a compact complete routing handoff without silently reusing
        # any placement-derived metrics or old extracted SPEF.
        state.update(odb=str(odb),metrics={})
        (OUT/'candidate-state.json').write_text(json.dumps(state,indent=2)+'\n')
        assert all(sha(p)==h for p,h in protected.items())
        r.update(status='PASS_NATIVE_FRESH_GLOBAL_REQUIRES_RESUMABLE_DETAIL_ROUTE_AND_FRESH_RC_STA',
            global_odb_sha256=sha(odb),global_guides_sha256=sha(guides),candidate_instance_count=153130,
            native_global_script=script,geometry=geometry,fixed_clock=fixed,sources_unchanged=True,
            native_global_complete=True,detailed_route_complete=False,
            step_path=str(step.relative_to(OUT)),state_sha256=sha(OUT/'candidate-state.json'),
            next_action='Start separate exact-native resumable detailed routing from these new guides, then antenna/connectivity/fresh RC/three-corner original-clock STA. Not timing, full PHY or production acceptance.')
    except BaseException as e:r.update(status='FAIL_NATIVE_REPAIRED_GLOBAL',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
