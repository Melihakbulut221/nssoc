#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind the proved repaired chip to original inputs and invalidate stale data wires."""
import hashlib,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_replay_onehot_logic as logic
from cloud_mainchip_postroute_review import api,source_hash
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-repair-deep-handoff'
RUN=39674630712
HEAD='6fbd221520a35d6b5ef01cc1c67796175093ee3c'
SUMMARY='cff0a3533c622f4ecf9951f205e046ba8ad35ab0ca326b6e2f82371559f2cade'
PARTS='997ee6b2b8b5f9fd971a1901a68cf49465b80bf8f0914ae461f347e915b34123'
ODB='25b1e56fe0667adc84b7c2bd5397a755d6cfdf7375b3d5c1444e56bd9252e279'
NETLIST='3a200ea79143bc3b723905495085c317083deac7cc6b10ad3033b186293d7030'
SDC='19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597'
def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def validate_candidate(r):
    assert r['source_head']==HEAD and r['sources_unchanged']
    assert r['status']=='PASS_NATIVE_RESIZER_CANDIDATE_REQUIRES_ROUTE_FRESH_RC_ALL_CORNER_STA'
    assert r['native_version']=='dcf36133a369abc8f3c5e5738cd4d82e4903c0e0'
    assert r['verified_postroute_run']==39654204345
    assert r['candidate_odb_sha256']==ODB and r['candidate_netlist_sha256']==NETLIST
    assert r['source_sdc_sha256']==SDC
    assert r['actual_inversion_control_rejected']and r['logic_controls']['status']=='PASS_NATIVE_ECO_CONTROLS'
    assert r['proof']['status']=='PASS within scope'and r['proof']['unobserved_output_port_changes']==0
    assert r['proof']['positive_buffers_after']-r['proof']['positive_buffers_before']==368
    g=r['geometry']
    assert g['original_instances']==152762 and len(g['added'])==368
    assert g['pg_ndr_ports_preserved']and g['clock_pins_and_clock_sram_geometry_preserved']
    assert g['candidate_sha256']==ODB
    assert r['fixed_clock']['original_physical_route_preserved']
    assert r['routing_initialization']['physical_def_preserved_excluding_gcellgrid']
    assert len(r['routing_initialization']['six_native_reports_literal_identity'])==6
    for c,v in r['native_baseline'].items():
        for mode in ('max','min'):assert abs(v[mode]-r['expected_baseline'][c][mode])<=.001
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT;logic.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
        full_phy_accepted=False,final_timing_complete=False,detailed_route_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label,extra=None):
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        if extra:env.update(extra)
        with(OUT/(label+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code));save()
        if code:print((OUT/(label+'.log')).read_text(errors='replace')[-14000:],flush=True)
        assert code==0,(label,code)
    save()
    try:
        methods=json.loads((ROOT/'scripts/mainchip-repair-deep-handoff-methods.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in methods.items())
        live=api('actions/runs/'+str(RUN))
        assert live['status']=='completed'and live['conclusion']=='success'and live['run_attempt']==1
        assert live['head_sha']==HEAD and live['path']=='.github/workflows/mainchip-postroute-repair-deep-cloud.yml'
        assert source_hash('scripts/cloud_mainchip_postroute_repair_deep.py',HEAD)==sha(ROOT/'scripts/cloud_mainchip_postroute_repair_deep.py')
        candidate,digest,parts=logic.summary('mainchip-postroute-repair-deep',live)
        assert digest==SUMMARY and parts==PARTS
        validate_candidate(candidate)
        names=['candidate.odb','candidate.v','geometry.json','proof/result.json','controls/result.json','fixed-clock.json',
               'native-repair.log','repair-timing-native-body.tcl','repair-timing-candidate-body.tcl']
        actual,receipt=reports.restore_report('mainchip-postroute-repair-deep',RUN,SUMMARY,PARTS,OUT/'repair',names)
        assert actual==candidate
        for path,key in [('geometry.json','geometry'),('proof/result.json','proof'),('controls/result.json','logic_controls'),('fixed-clock.json','fixed_clock')]:
            assert json.loads((OUT/'repair'/path).read_text())==candidate[key]
        # Exercise rejection on real observed evidence, never synthetic pass claims.
        import copy
        rejected=[]
        for label,change in [
            ('wrong-netlist',lambda x:x.update(candidate_netlist_sha256='0'*64)),
            ('missing-inversion-proof',lambda x:x.update(actual_inversion_control_rejected=False)),
            ('changed-clock-route',lambda x:x['fixed_clock'].update(original_physical_route_preserved=False)),
            ('changed-sram-geometry',lambda x:x['geometry'].update(clock_pins_and_clock_sram_geometry_preserved=False))]:
            bad=copy.deepcopy(candidate);change(bad)
            try:validate_candidate(bad)
            except AssertionError:rejected.append(label)
            else:raise AssertionError('Accepted corrupt native candidate: '+label)
        assert len(rejected)==4
        r.update(candidate_source=receipt,candidate_proof=candidate['proof'],
            geometry=candidate['geometry'],fixed_clock=candidate['fixed_clock'],
            rejected_candidate_controls=rejected,native_optimizer_log=(OUT/'repair/native-repair.log').read_text())
        save()
        pin=json.loads((ROOT/'docs/evidence/mainchip-postroute-inputs-pass-20261021.json').read_text())
        descriptor={k:pin[k]for k in ('run','group','source_head','controller_sha256','summary_sha256','parts_sha256')}
        descriptor['attempt']=1
        # Existing source-bound native preflight restores and verifies every PDK,
        # SRAM, SDC and tool dependency. It starts no routing or timing analysis.
        env=dict(os.environ,NSSOC_INPUT_PACKAGE=json.dumps(descriptor))
        env.pop('NSSOC_COMPLETED_DRT',None)
        with(OUT/'original-inputs.log').open('w')as log:
            code=subprocess.call([sys.executable,str(ROOT/'scripts/cloud_mainchip_postroute_review.py'),'--preflight-inputs'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        if code:print((OUT/'original-inputs.log').read_text(errors='replace')[-14000:],flush=True)
        assert code==0,'Exact native input preflight failed'
        preflight=ROOT/'cloud-mainchip-postroute-review'
        source=json.loads((preflight/'result.json').read_text())
        assert source['status']=='PASS_NATIVE_POSTROUTE_INPUT_CONFIG_PREFLIGHT_NOT_ROUTED'and source['sources_unchanged']
        shutil.copyfile(preflight/'result.json',OUT/'original-input-preflight.json')
        for name in ('result.json','resolved.json'):
            p=preflight/'native-config'/name
            if p.is_file():shutil.copyfile(p,OUT/('native-config-'+name))
        package=preflight/'inputs/postroute-inputs';contract=source['input_contract']
        assert contract['clocks_ns']==[20,4,8,8]and contract['derating_percent']==5
        r.update(original_input_descriptor=descriptor,original_input_contract=contract,
            original_input_preflight_sha256=sha(preflight/'result.json'))
        app=Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        odb=OUT/'repair/candidate.odb';nl=OUT/'repair/candidate.v'
        assert sha(odb)==ODB and sha(nl)==NETLIST
        helper=ROOT/'scripts/prepare_mainchip_repair_deep_fresh_route.py'
        fresh=OUT/'fresh'
        run([app,'openroad','-exit','-python',helper],'fresh-native-data-wires',
            dict(NSSOC_FRESH_ROUTE_SOURCE=str(odb),NSSOC_FRESH_ROUTE_OUT=str(fresh)))
        prepared=json.loads((fresh/'result.json').read_text())
        assert prepared['status']=='PASS_ONLY_STALE_DATA_WIRES_REMOVED_REQUIRES_FRESH_GLOBAL_AND_DETAIL_ROUTE'
        assert prepared['source_sha256']==ODB and prepared['source_unchanged']
        assert prepared['proof']['all_non_wire_physical_def_preserved']and prepared['proof']['all_other_net_records_preserved']
        assert len(prepared['controls'])==3 and all(v['rejected']for v in prepared['controls'])
        run([app,'openroad','-exit','-python',ROOT/'scripts/check_onehot_fixed_clock_route.py'],
            'fresh-fixed-clock',dict(NSSOC_TOPOLOGY_BEFORE=str(odb),NSSOC_TOPOLOGY_AFTER=str(fresh/'candidate.odb'),NSSOC_CLOCK_ROUTE_PROOF_OUT=str(OUT/'fresh-fixed-clock.json')))
        fixed=json.loads((OUT/'fresh-fixed-clock.json').read_text())
        assert fixed['original_physical_route_preserved']
        state=json.loads((package/'candidate-state.json').read_text())
        assert sha(state['sdc'])==SDC and not state['metrics']
        state.update(odb=str(fresh/'candidate.odb'),nl=str(nl),metrics={})
        for k in ('def','spef','pnl','sdf'):state[k]=None
        (OUT/'candidate-state.json').write_text(json.dumps(state,indent=2)+'\n')
        (OUT/'trial-config.json').write_bytes((package/'trial-config.json').read_bytes())
        def paths(x):
            if isinstance(x,dict):
                for v in x.values():yield from paths(v)
            elif isinstance(x,list):
                for v in x:yield from paths(v)
            elif isinstance(x,str)and x.startswith('/'):yield x
        dependencies={p:sha(p)for p in paths(state)}
        assert sha(OUT/'trial-config.json')==contract['configuration_sha256']
        assert all(sha(ROOT/p)==h for p,h in methods.items())
        assert sha(odb)==ODB and sha(nl)==NETLIST
        r.update(status='PASS_PROVEN_REPAIR_INPUT_READY_FOR_FRESH_GLOBAL_AND_DETAIL_ROUTE',
            source_candidate_odb_sha256=ODB,candidate_netlist_sha256=NETLIST,source_sdc_sha256=SDC,
            candidate_instance_count=153130,fresh_preparation=prepared,fresh_fixed_clock=fixed,
            fresh_odb_sha256=sha(fresh/'candidate.odb'),state_dependencies=dependencies,
            candidate_state_sha256=sha(OUT/'candidate-state.json'),configuration_sha256=sha(OUT/'trial-config.json'),
            sources_unchanged=True,native_routing_started=False,stale_spef_and_metrics_discarded=True,
            next_action='Generate fresh native global routing from all current pins, then resumable native DRT; require fresh RC and original-clock all-corner STA. No final timing or PHY acceptance.')
    except BaseException as e:r.update(status='FAIL_REPAIR_HANDOFF',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
