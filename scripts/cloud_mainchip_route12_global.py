#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run original fresh global router on the deep repair's proved handoff."""
import hashlib,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_replay_onehot_logic as logic
from cloud_mainchip_postroute_review import api,source_hash
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-route12-global'
HANDOFF=ROOT/'cloud-mainchip-route12-inputs'
RUN=39909564054
HEAD='a420ff6fbba5816df3e4422f1bc237ccb9dd175d'
SUMMARY='31f3d60b610e5beb6d326a1b8fc6b1886ca6ed7474a3e6d8a9dbb368417af408'
PARTS='255ccaac9bf28004b25ced3742f5a8c9cdc2278a3e534f705047460b5fde8d4d'
FRESH='e045d10be101f672672a2d14250d6960879f932fc96ea952c826059e05aacf3d'
NETLIST='3c053c4cda51a001b926cce347b97de5c825cbff2082de550eeb9e31ff7fe5cd'
SDC='19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597'
def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def validate(r):
    assert r['source_head']==HEAD and r['sources_unchanged']
    assert r['status']=='PASS_NATIVE_MEASURED_BUFFER_RESIZING_REQUIRES_ROUTE_RC_ALL_CORNER_STA'
    assert r['candidate_odb_sha256']==FRESH and r['candidate_netlist_sha256']==NETLIST
    assert r['inversion_control']['rejected']and r['controls']['status']=='PASS_NATIVE_ECO_CONTROLS'
    assert r['proof']['status']=='PASS within scope'and r['proof']['unobserved_output_port_changes']==0
    assert r['proof']['positive_buffers_after']==r['proof']['positive_buffers_before']==36629
    g=r['geometry']
    assert g['instances']==153130 and len(g['changes'])==128
    assert g['all_net_memberships_unchanged']and g['all_other_instances_unchanged']and g['pg_ports_ndr_unchanged']
    assert r['fixed_clock']['original_physical_route_preserved']
    assert not r['detailed_route_complete']and not r['final_timing_complete']
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
        methods=json.loads((ROOT/'scripts/mainchip-route12-global-methods.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in methods.items())
        live=api('actions/runs/'+str(RUN))
        assert live['status']=='completed'and live['conclusion']=='success'and live['run_attempt']==1
        assert live['head_sha']==HEAD and live['path']=='.github/workflows/mainchip-route12-resize-cloud.yml'
        assert source_hash('scripts/cloud_mainchip_route12_resize.py',HEAD)==sha(ROOT/'scripts/cloud_mainchip_route12_resize.py')
        source,digest,parts=logic.summary('mainchip-route12-resize',live)
        assert digest==SUMMARY and parts==PARTS;validate(source)
        import copy
        rejected=[]
        for name,change in [
            ('wrong-fresh-odb',lambda x:x.update(candidate_odb_sha256='0'*64)),
            ('changed-clock',lambda x:x['fixed_clock'].update(original_physical_route_preserved=False)),
            ('changed-census',lambda x:x['geometry'].update(instances=152988)),
            ('missing-equivalence',lambda x:x['proof'].update(status='UNPROVEN'))]:
            bad=copy.deepcopy(source);change(bad)
            try:validate(bad)
            except AssertionError:rejected.append(name)
            else:raise AssertionError('Accepted corrupt handoff: '+name)
        names=['candidate.odb','candidate.v','candidate-state.json','trial-config.json','source/geometry/routed/work/detailed-route.odb']
        actual,receipt=reports.restore_report('mainchip-route12-resize',RUN,SUMMARY,PARTS,HANDOFF,names)
        assert actual==source
        r.update(handoff_source=receipt,rejected_handoff_controls=rejected);save()
        descriptor={k:v for k,v in json.loads((ROOT/'docs/evidence/mainchip-postroute-inputs-pass-20261021.json').read_text()).items()if k in ('run','group','source_head','controller_sha256','summary_sha256','parts_sha256')};descriptor['attempt']=1
        pin=json.loads((ROOT/'docs/evidence/mainchip-postroute-inputs-pass-20261021.json').read_text())
        assert all(descriptor[k]==pin[k]for k in ('run','group','source_head','controller_sha256','summary_sha256','parts_sha256'))
        assert not os.environ.get('NSSOC_COMPLETED_DRT')
        run([sys.executable,ROOT/'scripts/cloud_mainchip_postroute_review.py','--preflight-inputs'],
            'original-input-preflight',dict(NSSOC_INPUT_PACKAGE=json.dumps(descriptor)),auth=True)
        preflight=ROOT/'cloud-mainchip-postroute-review'
        pr=json.loads((preflight/'result.json').read_text())
        assert pr['status']=='PASS_NATIVE_POSTROUTE_INPUT_CONFIG_PREFLIGHT_NOT_ROUTED'and pr['sources_unchanged']
        contract=pr['input_contract'];assert contract['clocks_ns']==[20,4,8,8]and contract['derating_percent']==5
        package=preflight/'inputs/postroute-inputs'
        app=Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        for name in ('candidate.odb','candidate.v'):
            shutil.copyfile(HANDOFF/name,OUT/name)
        state=json.loads((package/'candidate-state.json').read_text())
        state.update(odb=str(OUT/'candidate.odb'),nl=str(OUT/'candidate.v'),metrics={})
        for k in ('def','spef','pnl','sdf'):state[k]=None
        run([app,'openroad','-exit','-python',ROOT/'scripts/check_mainchip_route12_all_clocks.py'],'all-source-clocks',
            dict(NSSOC_CLOCK_BEFORE=str(HANDOFF/'source/geometry/routed/work/detailed-route.odb'),NSSOC_CLOCK_AFTER=state['odb'],NSSOC_CLOCK_AUDIT=str(OUT/'all-clocks')))
        r['all_clock_preservation']=json.loads((OUT/'all-clocks/result.json').read_text())
        assert r['all_clock_preservation']['all_source_clock_and_fixed_records_preserved']
        save()
        assert sha(state['odb'])==FRESH and sha(state['nl'])==NETLIST and sha(state['sdc'])==SDC
        assert not state['metrics'] and all(state[k]is None for k in ('spef','def','pnl','sdf'))
        assert all(sha(ROOT/p)==v['sha256']for p,v in contract['input_files'].items())
        assert json.loads((HANDOFF/'trial-config.json').read_text())==json.loads((package/'trial-config.json').read_text())
        trial=OUT/'trial-config.json';shutil.copyfile(package/'trial-config.json',trial)
        assert sha(trial)==contract['configuration_sha256']
        initial=OUT/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
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
