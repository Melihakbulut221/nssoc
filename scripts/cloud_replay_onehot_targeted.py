#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure source-bound critical-buffer contraction after original repair."""
import argparse,json,os,re,subprocess,time
from pathlib import Path
import cloud_replay_onehot_logic as logic
import compare_cloud_routed_endpoints as reports
from cloud_corrpre_banked_handoff import api,wait_success
from cloud_replay_onehot_postcts import require_candidate,relative,sha
from route_cloud_newer_postcts import native_ndr_screen
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-replay-onehot-targeted'
PLACE=ROOT/'hw/soc/out/cloud-corrpre-mbist-placement'
REPAIR=ROOT/'hw/soc/out/cloud-replay-onehot-postcts'
PROOF_RUN=39079184710
PROOF_HEAD='35eea50cae3ec44fae90dd179b369e103630e6a2'
PROOF_STATUS='PASS_NEW_BANKED_CTS_TO_REPAIR_LOGIC_NOT_ROUTE_OR_TIMING_SIGNOFF'

def proof_source(result,save,wait):
    run=wait_success(PROOF_RUN,'.github/workflows/replay-onehot-logic-cloud.yml',
        time.monotonic()+(18000 if wait else 0),result,save)
    assert run['head_sha']==PROOF_HEAD and run['run_attempt']==1
    proof,digest,parts=logic.summary('replay-onehot-logic',run)
    assert proof['status']==PROOF_STATUS and proof['source_head']==PROOF_HEAD
    assert proof['sources_unchanged'] is True
    assert proof['proof']['status']=='PASS within scope'and proof['proof']['retained_cells']>10000
    assert proof['controls']['status']=='PASS_NATIVE_ECO_CONTROLS'
    assert proof['proof']['macro_verilog_defines']==['FUNCTIONAL']
    assert [s['archive']['run']for s in proof['sources']]==[logic.PLACEMENT_RUN,logic.REPAIR_RUN]
    result['logic_source']=dict(run=PROOF_RUN,head=PROOF_HEAD,summary_sha256=digest,parts_sha256=parts)
    save()
    return proof,digest,parts

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--wait',action='store_true');args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);logic.OUT=OUT;reports.OUT=OUT
    r=dict(status='WAITING_FOR_EXACT_LOGIC_PROOF'if args.wait else'RESTORING_EXACT_REPAIRED_SOURCE',
        source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
        detailed_route_complete=False,final_timing_complete=False,qualified_pex=False,
        scope='9 exact positive data buffers on measured slow onehot mainchip setup paths, then native electrical/setup/hold repair and fresh three-corner placement-estimate STA plus equation proof. Original clocks/SDC/derate/source preserved. Not routed timing or serial PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        target_record=json.loads((ROOT/'docs/evidence/replay-onehot-target-buffers-20261018.json').read_text())
        assert target_record['source_review_sha256']=='9b2066b60ca97ec78fced26065d09c37185d4ae8587ac5e2cdbd67e725b01bc0'
        assert sha(ROOT/'hw/soc/flow/replay_onehot_targeted_unbuffer.tcl')==target_record['helper_sha256']
        assert len(target_record['targets'])==9
        r['target_record']=target_record
        proof,proof_sha,proof_parts=proof_source(r,save,args.wait)
        if args.wait:
            r['status']='EXACT_LOGIC_SOURCE_READY_FOR_SEPARATE_NATIVE_JOB';return
        original,proof_archive=reports.restore_report('replay-onehot-logic',PROOF_RUN,
            proof_sha,proof_parts,OUT/'logic-proof',('proof/result.json','controls/result.json'))
        assert original==proof
        assert json.loads((OUT/'logic-proof/proof/result.json').read_text())==proof['proof']
        assert json.loads((OUT/'logic-proof/controls/result.json').read_text())==proof['controls']
        r['logic_archive']=proof_archive
        source_reports={}
        for label,group,run_id,head,destination in (
            ('placement','replay-onehot-placement',logic.PLACEMENT_RUN,logic.PLACEMENT_HEAD,PLACE),
            ('repair','replay-onehot-postcts',logic.REPAIR_RUN,logic.REPAIR_HEAD,REPAIR)):
            run=api('actions/runs/'+str(run_id))
            assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']==head
            assert run['path']=='.github/workflows/'+group+'-cloud.yml'and run['run_attempt']==1
            report,digest,parts=logic.summary(group,run)
            bound=proof['sources'][0 if label=='placement'else 1]['archive']
            assert digest==bound['summary_sha256']and parts==bound['manifest_sha256']
            restored,archive=reports.restore_report(group,run_id,digest,parts,destination,tuple(report['outputs']))
            assert restored==report and report['source_head']==head
            source_reports[label]=report;r[label+'_source']=archive;save()
        before=source_reports['placement'];after=source_reports['repair']
        spec=require_candidate(before,logic.PLACEMENT_HEAD)
        assert spec==proof['boot_spec']==after['placement_source']['boot_spec']
        assert after['status']==logic.REPAIR_STATUS and after['sources_unchanged']and after['returncode']==0
        assert after['placement_source']['run']==logic.PLACEMENT_RUN
        # Revalidate all current RTL/protocol/native-boot receipts before mutation.
        from cloud_replay_onehot_postcts import require_same_proofs
        import cloud_replay_onehot_handoff as handoff
        handoff.OUT.mkdir(exist_ok=False)
        for number,workflow,source_head in handoff.SOURCES:
            observed=api('actions/runs/'+str(number))
            assert observed['status']=='completed' and observed['conclusion']=='success'
            assert observed['head_sha']==source_head and observed['event']=='push' and observed['run_attempt']==1
            assert observed['path']=='.github/workflows/'+workflow+'.yml'
        r['nine_source_proof_revalidation']=handoff.collect_proofs()
        verified=OUT/'verified-current-boot.json'
        subprocess.run(list(map(str,[os.sys.executable,ROOT/'scripts/check_pcie_onehot_banked_boot_source.py',
            '--boot-run',spec['run'],'--boot-head',spec['head'],'--artifact',spec['artifact'],
            '--zip-sha256',spec['zip_sha256'],'--protocol-run',spec['protocol_run'],'--out',verified])),check=True,cwd=ROOT)
        current_spec=json.loads(verified.read_text())
        require_same_proofs(spec,current_spec)
        require_same_proofs(spec,proof['current_boot_source_revalidation'])
        r['current_boot_source_revalidation']=current_spec
        review_blob=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/651919578','-H','Accept: application/octet-stream'])
        assert __import__('hashlib').sha256(review_blob).hexdigest()==target_record['source_review_sha256']
        assert json.loads(review_blob)['repaired_odb_sha256']==after['repaired_odb_sha256']
        save()
        state_path=REPAIR/relative(after['repaired_state']);state=json.loads(state_path.read_text())
        odb=Path(state['odb']);netlist=Path(state['nl'])
        assert odb.is_relative_to(REPAIR)and netlist.is_relative_to(REPAIR)
        assert sha(odb)==after['repaired_odb_sha256']==proof['sources'][1]['native_odb_sha256']
        assert sha(netlist)==proof['sources'][1]['netlist_sha256']
        config_path=REPAIR/'trial-config.json';cfg=json.loads(config_path.read_text())
        assert cfg['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
        assert cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5
        assert cfg['SETUP_VIOLATION_CORNERS']==cfg['HOLD_VIOLATION_CORNERS']==['*']
        assert cfg['PNR_SDC_FILE']==cfg['SIGNOFF_SDC_FILE']==str(PLACE/'prepared/physical.sdc')
        assert len(before['preparation']['macros'])==20
        assert cfg.get('GRT_ALLOW_CONGESTION',False) is False,'Do not accept an overflowing route'
        assert cfg['DESIGN_REPAIR_REMOVE_BUFFERS'] is False
        cfg['TIME_DERATING_CONSTRAINT']=5.0
        trial=OUT/'trial-config.json';trial.write_text(json.dumps(cfg,indent=2)+'\n')
        r['discarded_inherited_metrics']=len(state['metrics']);state['metrics']={}
        initial=OUT/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        flow=ROOT/'hw/soc/pnr/replay_onehot_targeted_flow.py'
        protected={str(p):sha(p)for p in [Path(__file__),flow,
            ROOT/'hw/soc/pnr/corrpre_postcts_flow.py',ROOT/'hw/soc/pnr/interface_flow.py',
            ROOT/'hw/soc/flow/check_timing_derate.tcl',ROOT/'hw/soc/flow/replay_onehot_targeted_unbuffer.tcl',config_path,PLACE/'prepared/physical.sdc',
            state_path,odb,netlist,trial,initial]}
        command=[str(app),'python',str(flow),'--flow','CorrpreBankedTargetedRebuffer',
            '--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2',
            '--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),
            '--with-initial-state',str(initial),str(trial)]
        r.update(status='RUNNING_NATIVE_TARGETED_REBUFFER',protected_inputs=protected,command=command);save()
        (OUT/'run').mkdir();start=time.monotonic()
        with(OUT/'native.log').open('w')as log:
            code=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.update(returncode=code,elapsed_s=time.monotonic()-start);save()
        if code:
            r['native_failure_tail']=(OUT/'native.log').read_text(errors='replace')[-20000:];save()
            print(r['native_failure_tail'],flush=True)
        assert code==0,'Native targeted repair failed; every completed state retained'
        phases={}
        for phase in ('before','after'):
            phases[phase]={}
            for short,corner in [('slow','nom_slow_1p08V_125C'),('typical','nom_typ_1p20V_25C'),('fast','nom_fast_1p32V_m40C')]:
                folders=list((OUT/'run').glob('*-nssoc-corrpretarget'+phase+short));assert len(folders)==1
                folder=folders[0];assert not (folder/'unpropagated.rpt').read_text().strip()
                data=json.loads((folder/'state_out.json').read_text())
                metrics={k:v for k,v in data['metrics'].items()if k.endswith('__corner:'+corner)}
                for key in ('timing__setup__ws','timing__hold__ws','timing__setup_vio__count','timing__hold_vio__count'):
                    assert __import__('math').isfinite(float(metrics[key+'__corner:'+corner]))
                if phase=='before':
                    for key,value in after['measurements']['after'][corner]['metrics'].items():
                        assert metrics[key]==value,('Original repair timing not reproduced',key,metrics[key],value)
                phases[phase][corner]=dict(metrics=metrics,directory=str(folder.relative_to(OUT)))
        r['measurements']=phases;save()
        electrical=list((OUT/'run').glob('*-nssoc-corrpretargetedunbuffer'));assert len(electrical)==1
        native='\n'.join(p.read_text(errors='replace')for p in electrical[0].glob('*.log'))
        markers=re.findall(r'NSSOC_TARGETED_UNBUFFER_PASS removed=9 retained=(\d+) clock_nets=(\d+)',native)
        assert len(markers)==1 and int(markers[0][1])>0
        states=list((OUT/'run').glob('*-openroad-resizertimingpostcts/state_out.json'));assert len(states)==1
        final=json.loads(states[0].read_text());new_nl=Path(final['nl']);new_db=Path(final['odb'])
        def execute(command,label):
            with(OUT/(label+'.log')).open('w')as log:
                done=subprocess.run(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            r.setdefault('proof_commands',[]).append(dict(command=list(map(str,command)),returncode=done.returncode));save()
            assert done.returncode==0,label+' failed; original results retained'
        execute([os.sys.executable,ROOT/'hw/soc/flow/prepare_ihp_native_boot.py'],'native-models')
        pdk=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2'
        liberty=pdk/'libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        assert sha(liberty)=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
        checker=ROOT/'hw/soc/flow/check_eco_logic_clones.py'
        execute([os.sys.executable,ROOT/'sw/tests/eco_logic_native.py','--checker',checker,'--liberty',liberty,'--output',OUT/'controls'],'logic-controls')
        controls=json.loads((OUT/'controls/result.json').read_text());assert controls['status']=='PASS_NATIVE_ECO_CONTROLS'
        cmd=[os.sys.executable,checker,netlist,new_nl,'--liberty',liberty,'--output',OUT/'proof','--macro-verilog-define','FUNCTIONAL']
        for name in ['RM_IHPSG13_1P_2048x64_c2_bm_bist.v','RM_IHPSG13_2P_256x16_c2_bm_bist.v']:
            cmd+=['--macro-verilog',pdk/'libs.ref/sg13g2_sram/verilog'/name]
        execute(cmd,'targeted-equation-proof')
        equation=json.loads((OUT/'proof/result.json').read_text())
        assert equation['status']=='PASS within scope' and equation['retained_cells']>10000
        assert all(sha(p)==digest for p,digest in protected.items())
        r.update(status='COMPLETE_NATIVE_TARGETED_REBUFFER_AND_LOGIC_REQUIRES_TIMING_REVIEW',sources_unchanged=True,
            proof=equation,controls=controls,targeted_removed=9,clock_nets_preserved_during_removal=int(markers[0][1]),
            candidate_state=str(states[0].relative_to(OUT)),candidate_odb_sha256=sha(new_db),candidate_netlist_sha256=sha(new_nl))
    except BaseException as error:
        r.update(status='FAIL_OR_ERROR_NO_SOURCE_RESTART',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
