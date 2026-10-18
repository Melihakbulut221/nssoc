#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Extract the exact completed onehot route; never reuse another candidate or placement RC."""
import argparse,json,math,os,re,subprocess,time
from pathlib import Path
import cloud_replay_onehot_logic as logic
import compare_cloud_routed_endpoints as reports
from cloud_corrpre_banked_handoff import api,wait_success
from cloud_replay_onehot_postcts import require_candidate,relative,sha
from route_cloud_newer_postcts import native_ndr_screen
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-replay-onehot-routed-extraction'
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
    parser=argparse.ArgumentParser();parser.add_argument('--summary-sha256',required=True);parser.add_argument('--parts-sha256',required=True);args=parser.parse_args()
    assert all(re.fullmatch('[0-9a-f]{64}',v)for v in (args.summary_sha256,args.parts_sha256))
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);logic.OUT=OUT;reports.OUT=OUT
    r=dict(status='RESTORING_EXACT_ROUTED_SOURCE',
        source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
        detailed_route_complete=False,final_timing_complete=False,qualified_pex=False,
        scope='Fresh native nominal OpenRCX and three cell corners from exact completed detailed route39084569446. Original20/4/8/8ns clocks,5percent derate,20SRAM, RTL proofs and actual new netlist. Not qualified RCmin/max, post-route logic/LVS, SRAM interior characterization, SI, full PHY or final signoff.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        proof,proof_sha,proof_parts=proof_source(r,save,False)
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
        route_run=api('actions/runs/39084569446')
        assert route_run['status']=='completed' and route_run['conclusion']=='success'
        assert route_run['head_sha']=='92c6161af3fbb040ce6433ccae32ee614e6db1ab' and route_run['run_attempt']==1
        assert route_run['path']=='.github/workflows/replay-onehot-detailed-route-cloud.yml'
        route,digest,parts=logic.summary('replay-onehot-detailed-route',route_run)
        assert digest==args.summary_sha256 and parts==args.parts_sha256
        assert route['source_head']==route_run['head_sha'] and route['sources_unchanged'] and route['returncode']==0
        assert route['status']=='COMPLETE_NATIVE_ONEHOT_DETAILED_ROUTE_REQUIRES_EXTRACTED_STA_GEOMETRY_LVS_AND_PHY'
        assert route['detailed_route_complete'] and route['native_routing_drc_errors']==0 and route['native_antenna_nets']==0 and route['critical_disconnected_pins']==0
        assert route['global_route_source']['summary_sha256']==gp['summary_sha256']
        assert route['global_route_input']==dict(odb_sha256=sha(odb),guide_sha256=sha(guide),netlist_sha256=sha(netlist),native_ndr_screen=grt['native_ndr_screen'])
        require_same_proofs(current_spec,route['current_boot_source_revalidation'])
        route_root=ROOT/'hw/soc/out/cloud-replay-onehot-detailed-route'
        restored,route_proof=reports.restore_report('replay-onehot-detailed-route',39084569446,digest,parts,route_root,list(route['outputs']))
        assert restored==route
        r['actual_detailed_route_source']=route_proof
        state_path=route_root/relative(route['detailed_route_state']);state=json.loads(state_path.read_text())
        final=json.loads((route_root/relative(route['final_state'])).read_text())
        odb=Path(state['odb']);deffile=Path(state['def']);netlist=Path(state['nl'])
        assert all(p.is_relative_to(route_root)for p in (odb,deffile,netlist))
        assert sha(odb)==route['routed_odb_sha256'] and sha(deffile)==route['routed_def_sha256']
        assert sha(final['odb'])==sha(odb) and sha(final['def'])==sha(deffile) and sha(final['nl'])==sha(netlist)
        for p in (odb,deffile,netlist):assert sha(p)==route['outputs'][str(p.relative_to(route_root))]
        cfg=json.loads((route_root/'trial-config.json').read_text())
        assert cfg['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
        assert cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5
        assert cfg['SETUP_VIOLATION_CORNERS']==cfg['HOLD_VIOLATION_CORNERS']==['*']
        assert cfg['PNR_SDC_FILE']==cfg['SIGNOFF_SDC_FILE']==str(PLACE/'prepared/physical.sdc')
        r['execution_config_changes']={'STA_THREADS':dict(before=cfg.get('STA_THREADS'),after=1)}
        cfg['STA_THREADS']=1;cfg['TIME_DERATING_CONSTRAINT']=5.0
        trial=OUT/'trial-config.json';trial.write_text(json.dumps(cfg,indent=2)+'\n')
        r['discarded_inherited_metric_count']=len(state['metrics']);state['metrics']={}
        state['spef']=None
        initial=OUT/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        flow=ROOT/'hw/soc/pnr/replay_onehot_routed_extraction_flow.py'
        protected={str(p):sha(p)for p in [Path(__file__),flow,ROOT/'hw/soc/pnr/interface_flow.py',ROOT/'hw/soc/flow/audit_estimated_spef.py',ROOT/'hw/soc/flow/check_timing_derate.tcl',PLACE/'prepared/physical.sdc',state_path,odb,deffile,netlist,trial,initial]}
        command=[str(app),'python',str(flow),'--flow','ReplayOnehotRoutedExtraction','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(trial)]
        r.update(status='RUNNING_FRESH_ROUTED_NOMINAL_RC_AND_THREE_CELL_CORNERS',protected_inputs=protected,command=command);save()
        (OUT/'run').mkdir();start=time.monotonic()
        with(OUT/'native.log').open('w')as log:code=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.update(returncode=code,elapsed_s=time.monotonic()-start);save()
        if code:print((OUT/'native.log').read_text(errors='replace')[-16000:],flush=True)
        assert code==0,'Native extraction or STA failed; retain all outputs'
        rcdirs=list((OUT/'run').glob('*-nssoc-onehotroutercx'));stadirs=list((OUT/'run').glob('*-nssoc-onehotroutedsta'))
        assert len(rcdirs)==len(stadirs)==1
        r['native_spef_integrity']=json.loads((rcdirs[0]/'native-spef-integrity.json').read_text())
        r['native_sta_script_proof']=json.loads((stadirs[0]/'native-sta-script-proof.json').read_text())
        final_sta=json.loads((stadirs[0]/'state_out.json').read_text());measurements={};all_met=True
        for corner in ('nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C'):
            folder=stadirs[0]/corner
            assert not(folder/'unpropagated.rpt').read_text().strip()
            assert 'NSSOC_ROUTED_ORIGINAL_CLOCKS_PROPAGATED'in (folder/'sta.log').read_text()
            metrics={k:v for k,v in final_sta['metrics'].items()if k.endswith('__corner:'+corner)}
            keys=['timing__setup__ws','timing__hold__ws','timing__setup_vio__count','timing__hold_vio__count','design__max_cap_violation__count','design__max_slew_violation__count','design__max_fanout_violation__count']
            assert all(math.isfinite(float(metrics[k+'__corner:'+corner]))for k in keys)
            passed=all(float(metrics[k+'__corner:'+corner])>=0 for k in keys[:2]) and all(int(metrics[k+'__corner:'+corner])==0 for k in keys[2:])
            all_met=all_met and passed
            for name in ('max.rpt','min.rpt','checks.rpt','violator_list.rpt','clock.rpt','ws.max.rpt','ws.min.rpt'):assert(folder/name).is_file()
            measurements[corner]=dict(metrics=metrics,directory=str(folder.relative_to(OUT)),timing_and_electrical_counts_met=passed)
        assert all(sha(p)==v for p,v in protected.items())
        r.update(status='COMPLETE_FRESH_ONEHOT_ROUTED_NOMINAL_RC_THREE_CELL_CORNERS_NOT_SIGNOFF',measurements=measurements,all_reported_timing_and_electrical_gates_met=all_met,sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR_NO_SOURCE_RESTART',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
