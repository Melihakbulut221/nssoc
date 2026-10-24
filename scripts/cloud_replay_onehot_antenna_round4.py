#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Detailed route the exact zero-overflow onehot GRT state; retain failed stages."""
import argparse,json,os,re,subprocess,time
from pathlib import Path
import cloud_replay_onehot_logic as logic
import compare_cloud_routed_endpoints as reports
from cloud_corrpre_banked_handoff import api,wait_success
from cloud_replay_onehot_postcts import require_candidate,relative,sha
from route_cloud_newer_postcts import native_ndr_screen
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-replay-onehot-antenna-round4'
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
        scope='Actual continuation of completed39111280543 round3 after native topology proof, performing only antenna round4. Original provenance from zero-overflow GRT39082708488 with proven original20/4/8/8ns clocks,5percent derate,20SRAM and NDR. Native antenna repair and disconnected-pin checks remain enabled. No final timing, LVS, qualified PEX or serial PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
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
        save()
        state_path=REPAIR/relative(after['repaired_state']);state=json.loads(state_path.read_text())
        odb=Path(state['odb']);netlist=Path(state['nl'])
        assert odb.is_relative_to(REPAIR)and netlist.is_relative_to(REPAIR)
        assert sha(odb)==after['repaired_odb_sha256']==proof['sources'][1]['native_odb_sha256']
        assert sha(netlist)==proof['sources'][1]['netlist_sha256']
        # The original CTS/repair proof is provenance only. Route the newer,
        # independently proven targeted state and bind its old/new netlists.
        tp=json.loads((ROOT/'docs/evidence/replay-onehot-targeted-pass-20261018.json').read_text())
        tr=api('actions/runs/'+str(tp['run']))
        assert tr['status']=='completed' and tr['conclusion']=='success' and tr['head_sha']==tp['source_head'] and tr['run_attempt']==1
        assert tr['path']=='.github/workflows/replay-onehot-targeted-cloud.yml'
        target_root=ROOT/'hw/soc/out/cloud-replay-onehot-targeted'
        target,target_proof=reports.restore_report('replay-onehot-targeted',tp['run'],tp['summary_sha256'],tp['parts_sha256'],target_root,list(tp['report']['outputs']))
        assert target==tp['report'] and target['sources_unchanged'] and target['returncode']==0
        assert target['status']=='COMPLETE_NATIVE_TARGETED_REBUFFER_AND_LOGIC_REQUIRES_TIMING_REVIEW'
        assert target['proof']['status']=='PASS within scope' and target['proof']['retained_cells']==97622
        assert target['controls']['status']=='PASS_NATIVE_ECO_CONTROLS' and target['targeted_removed']==9
        assert json.loads((target_root/'proof/result.json').read_text())==target['proof']
        assert json.loads((target_root/'controls/result.json').read_text())==target['controls']
        assert target['protected_inputs'][str(netlist)]==sha(netlist)
        assert target['repair_source']['summary_sha256']==proof['sources'][1]['archive']['summary_sha256']
        require_same_proofs(current_spec,target['current_boot_source_revalidation'])
        for corner,values in target['measurements']['before'].items():
            assert values['metrics']==after['measurements']['after'][corner]['metrics']
        original_odb=odb;original_netlist=netlist
        state_path=target_root/relative(target['candidate_state']);state=json.loads(state_path.read_text())
        odb=Path(state['odb']);netlist=Path(state['nl'])
        assert odb.is_relative_to(target_root) and netlist.is_relative_to(target_root)
        assert sha(odb)==target['candidate_odb_sha256'] and sha(netlist)==target['candidate_netlist_sha256']
        config_path=target_root/'trial-config.json';cfg=json.loads(config_path.read_text())
        r['routed_candidate_source']=target_proof
        r['routed_candidate_logic']=target['proof']
        r['placement_estimate_before_route']=target['measurements']['after']

        gp=json.loads((ROOT/'docs/evidence/replay-onehot-global-route-pass-20261018.json').read_text())
        gr=api('actions/runs/'+str(gp['run']))
        assert gr['status']=='completed'and gr['conclusion']=='success'and gr['head_sha']==gp['source_head']and gr['run_attempt']==1
        assert gr['path']=='.github/workflows/replay-onehot-global-route-cloud.yml'
        grt_root=ROOT/'hw/soc/out/cloud-replay-onehot-global-route'
        grt,gproof=reports.restore_report('replay-onehot-global-route',gp['run'],gp['summary_sha256'],gp['parts_sha256'],grt_root,list(gp['report']['outputs']))
        assert grt==gp['report']and grt['sources_unchanged']and grt['returncode']==0
        assert grt['status']=='COMPLETE_NATIVE_ONEHOT_GLOBAL_ROUTE_REQUIRES_DRT_EXTRACTED_STA_AND_SIGNOFF'
        assert grt['native_ndr_screen']['preserved']and grt['native_final_congestion_total'].split()[-1]=='0'
        assert grt['routed_candidate_source']['summary_sha256']==tp['summary_sha256']and grt['routed_candidate_logic']==target['proof']
        require_same_proofs(current_spec,grt['current_boot_source_revalidation'])
        prior_target_config=dict(cfg)
        cfg=json.loads((grt_root/'trial-config.json').read_text())
        allowed={'RT_CLOCK_MIN_LAYER','RT_CLOCK_MAX_LAYER','GRT_OVERFLOW_ITERS'}
        assert {k:v for k,v in cfg.items()if k not in allowed}=={k:v for k,v in prior_target_config.items()if k not in allowed}
        assert cfg['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
        assert cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5
        assert cfg['SETUP_VIOLATION_CORNERS']==cfg['HOLD_VIOLATION_CORNERS']==['*']
        assert cfg['PNR_SDC_FILE']==cfg['SIGNOFF_SDC_FILE']==str(PLACE/'prepared/physical.sdc')
        assert cfg.get('GRT_ALLOW_CONGESTION',False)is False and cfg['GRT_ADJUSTMENT']==.2
        assert cfg['RT_CLOCK_MIN_LAYER']=='Metal4'and cfg['RT_CLOCK_MAX_LAYER']=='TopMetal2'
        assert len(before['preparation']['macros'])==20
        state_path=grt_root/grt['global_route_state'];state=json.loads(state_path.read_text())
        odb=Path(state['odb']);netlist=Path(state['nl'])
        assert odb.is_relative_to(grt_root)and sha(odb)==grt['global_route_odb_sha256']
        assert sha(netlist)==target['candidate_netlist_sha256']
        guide=state_path.parent/'after_grt.guide';assert sha(guide)==grt['guide_sha256']
        r['global_route_source']=gproof
        r['global_route_input']=dict(odb_sha256=sha(odb),guide_sha256=sha(guide),netlist_sha256=sha(netlist),native_ndr_screen=grt['native_ndr_screen'])
        # Keep original native DRT/antenna optimization limits. Resource count and
        # diagnostic report frequency do not alter acceptance criteria.
        r['detailed_route_config_delta']={k:dict(before=cfg.get(k),after=v)for k,v in dict(DRT_THREADS=2,DRT_SAVE_DRC_REPORT_ITERS=5).items()}
        cfg.update(DRT_THREADS=2,DRT_SAVE_DRC_REPORT_ITERS=5)
        assert cfg.get('DRT_OPT_ITERS',64)==64
        assert cfg.get('DRT_ANTENNA_REPAIR_ITERS',3)>0
        # Continue the completed round3 routing, not the initial global route.
        receipt=json.loads((ROOT/'docs/evidence/replay-onehot-antenna-round3-result-20261018.json').read_text())
        terminal=api('actions/runs/'+str(receipt['run']))
        assert receipt['run']==39111280543 and receipt['source_head']=='f667bcc365c7d58b8aad7b4087a1d125891931fb'
        assert terminal['status']=='completed'and terminal['conclusion']=='success'and terminal['head_sha']==receipt['source_head']and terminal['run_attempt']==1
        assert terminal['path']=='.github/workflows/replay-onehot-antenna-round3-cloud.yml'
        checkpoint=OUT/'saved-round3'
        selected=('run/1-openroad-detailedrouting/drt-run-3/soc_top.odb','run/1-openroad-detailedrouting/drt-run-3/soc_top.drc','run/1-openroad-detailedrouting/openroad-detailedrouting.log','run/2-openroad-checkantennas/reports/antenna.rpt')
        previous,checkpoint_proof=reports.restore_report('replay-onehot-antenna-round3',receipt['run'],receipt['summary_sha256'],receipt['parts_sha256'],checkpoint,selected)
        assert {k:previous[k]for k in receipt['report_excerpt']}==receipt['report_excerpt']
        assert previous['status']=='COMPLETE_NATIVE_ROUND3_ROUTE_REQUIRES_NEXT_ANTENNA_ROUND'
        assert previous['sources_unchanged']and previous['returncode']==0
        assert previous['native_routing_drc_errors']==previous['critical_disconnected_pins']==0 and previous['native_antenna_nets']==2
        assert previous['global_route_source']==gproof and previous['global_route_input']['odb_sha256']==sha(odb)
        saved=checkpoint/selected[0]
        assert sha(saved)=='c96f5e3c557e1851fc530b450b731aac4ce09e50b06ffdd426f4cbc694256e2d'
        assert (checkpoint/selected[1]).stat().st_size==0
        prior_log=(checkpoint/selected[2]).read_text()
        assert '[INFO GRT-0015] Inserted 47 diodes.'in prior_log
        assert len(re.findall(r'(?m)^\s*Net:\s*\S+',(checkpoint/selected[3]).read_text()))==2
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        proof_path=OUT/'saved-route-topology.json'
        topology_method=ROOT/'scripts/check_onehot_round3_saved_topology.py'
        with (OUT/'saved-route-topology.log').open('w')as log:
            code=subprocess.call(list(map(str,[app,'openroad','-exit','-python',topology_method])),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**{k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')},'NSSOC_TOPOLOGY_BEFORE':str(odb),'NSSOC_TOPOLOGY_AFTER':str(saved),'NSSOC_TOPOLOGY_OUT':str(proof_path)})
        if code:print((OUT/'saved-route-topology.log').read_text()[-12000:],flush=True)
        assert code==0,'Actual saved ODB topology proof failed'
        topology=json.loads(proof_path.read_text());assert topology['status']=='PASS_NATIVE_SAVED_ROUTE_TOPOLOGY_ONLY_NOT_TIMING_OR_LVS'
        assert topology['proof']['added_diode_count']==3374 and len(topology['rejected'])==3
        assert previous['resume_checkpoint']['topology']['proof']['added_diode_count']==3327
        r['resume_checkpoint']=dict(source=checkpoint_proof,odb_sha256=sha(saved),completed_antenna_round=3,next_antenna_round=4,prior_antenna_nets=2,topology=topology)
        state['odb']=str(saved);odb=saved
        assert cfg['DRT_ANTENNA_REPAIR_ITERS']==8
        r['job_partition']='Only antenna round4 in this job; original maximum8 and zero final antenna gate retained. Not a cold routing restart.'
        cfg['TIME_DERATING_CONSTRAINT']=5.0
        trial=OUT/'trial-config.json';trial.write_text(json.dumps(cfg,indent=2)+'\n')
        r['discarded_inherited_metrics']=len(state['metrics']);state['metrics']={}
        initial=OUT/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        flow=ROOT/'hw/soc/pnr/replay_onehot_antenna_round4_flow.py'
        protected={str(p):sha(p)for p in [Path(__file__),flow,topology_method,proof_path,ROOT/'hw/soc/pnr/corrpre_postcts_flow.py',ROOT/'hw/soc/pnr/interface_flow.py',ROOT/'hw/soc/flow/prune_orphan_guides.tcl',ROOT/'hw/soc/flow/check_timing_derate.tcl',PLACE/'prepared/physical.sdc',state_path,odb,netlist,guide,trial,initial]}
        command=[str(app),'python',str(flow),'--flow','ReplayOnehotAntennaRound4','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(trial)]
        r.update(status='RUNNING_NATIVE_ONEHOT_DETAILED_ROUTE',protected_inputs=protected,command=command);save()
        (OUT/'run').mkdir();start=time.monotonic()
        with(OUT/'native.log').open('w')as log:code=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.update(returncode=code,elapsed_s=time.monotonic()-start);save()
        states=list((OUT/'run').glob('*-openroad-detailedrouting/state_out.json'))
        logs=list((OUT/'run').glob('*-openroad-detailedrouting/*.log'))
        text='\n'.join(p.read_text(errors='replace')for p in logs)
        r['native_route_tail']=text.splitlines()[-120:]
        assert code==0,'Native detailed routing/check stages failed; preserve completed views'
        assert len(states)==1
        routed=json.loads(states[0].read_text());db=Path(routed['odb']);deffile=Path(routed['def'])
        assert db.is_relative_to(OUT/'run')and deffile.is_relative_to(OUT/'run')
        assert db.is_file()and deffile.is_file()
        antenna_states=list((OUT/'run').glob('*-openroad-checkantennas/state_out.json'));assert len(antenna_states)==1
        antenna=json.loads(antenna_states[0].read_text())
        pin_states=list((OUT/'run').glob('*-odb-reportdisconnectedpins/state_out.json'));assert len(pin_states)==1
        final=json.loads(pin_states[0].read_text());metrics=final['metrics']
        r['metrics']=metrics
        ar=antenna_states[0].parent/'reports/antenna.rpt';assert ar.is_file()
        native_antennas=len(re.findall(r'(?m)^\s*Net:\s*\S+',ar.read_text()))
        assert native_antennas==antenna['metrics']['route__antenna_violation__count'],'Native antenna report/count discrepancy'
        r.update(detailed_route_state=str(states[0].relative_to(OUT)),final_state=str(pin_states[0].relative_to(OUT)),routed_odb_sha256=sha(db),routed_def_sha256=sha(deffile),native_antenna_nets=native_antennas,
            native_routing_drc_errors=metrics['route__drc_errors'],critical_disconnected_pins=metrics['design__critical_disconnected_pin__count'])
        assert all(sha(p)==digest for p,digest in protected.items())
        r['sources_unchanged']=True;r['detailed_route_complete']=True;save()
        assert r['native_routing_drc_errors']==0 and r['critical_disconnected_pins']==0,'Native route DRC or logical-pin gate failed'
        r['remaining_antenna_nets']=native_antennas
        r['completed_antenna_round']=4
        r['antenna_closure_proven']=native_antennas==0
        r['status']='COMPLETE_NATIVE_ROUND4_ROUTE_NEEDS_EXTRACTED_STA_AND_SIGNOFF'if native_antennas==0 else'COMPLETE_NATIVE_ROUND4_ROUTE_REQUIRES_NEXT_ANTENNA_ROUND'
    except BaseException as error:
        r.update(status='FAIL_OR_ERROR_NO_SOURCE_RESTART',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
