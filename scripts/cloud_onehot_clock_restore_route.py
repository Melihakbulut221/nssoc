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
OUT=ROOT/'hw/soc/out/cloud-onehot-clock-restore-route'
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
    parser=argparse.ArgumentParser();parser.add_argument('--summary-sha256',required=True);parser.add_argument('--parts-sha256',required=True);parser.add_argument('--resize-run',required=True,type=int);parser.add_argument('--resize-head',required=True);parser.add_argument('--resize-summary-sha256',required=True);parser.add_argument('--resize-parts-sha256',required=True);args=parser.parse_args()
    assert all(re.fullmatch('[0-9a-f]{64}',v)for v in (args.summary_sha256,args.parts_sha256))
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);logic.OUT=OUT;reports.OUT=OUT
    r=dict(status='RESTORING_EXACT_ROUTED_SOURCE',
        source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
        detailed_route_complete=False,final_timing_complete=False,qualified_pex=False,
        scope='Legalize one physically proven restored short clock route in actual routed128-buffer chip. Preserve all150419 source cells and exact fixed clock geometry. Reuse actual existing global guides, not a fresh whole-chip global route. Original20/4/8/8ns clocks,5percent derate,20SRAM and complete RTL/route ancestry remain. Fresh nominal OpenRCX and three cell corners; topology is not LVS, qualifiedRC or fullPHY/signoff.')
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
        grt_odb=odb
        route_run=api('actions/runs/39115222502')
        assert route_run['status']=='completed' and route_run['conclusion']=='success'
        assert route_run['head_sha']=='85c2a70f1d625fab59bc7266aa5ef6894e3aa575' and route_run['run_attempt']==1
        assert route_run['path']=='.github/workflows/replay-onehot-antenna-round4-cloud.yml'
        route,digest,parts=logic.summary('replay-onehot-antenna-round4',route_run)
        assert digest==args.summary_sha256 and parts==args.parts_sha256
        route_pin=json.loads((ROOT/'docs/evidence/replay-onehot-antenna-round4-result-20261018.json').read_text())
        assert route_pin['run']==39115222502 and route_pin['source_head']==route_run['head_sha']
        assert digest==route_pin['summary_sha256']and parts==route_pin['parts_sha256']
        assert {k:route[k]for k in route_pin['report_excerpt']}==route_pin['report_excerpt']
        assert route['completed_antenna_round']==4 and route['antenna_closure_proven']
        assert route['source_head']==route_run['head_sha'] and route['sources_unchanged'] and route['returncode']==0
        assert route['status']=='COMPLETE_NATIVE_ROUND4_ROUTE_NEEDS_EXTRACTED_STA_AND_SIGNOFF'
        assert route['detailed_route_complete'] and route['native_routing_drc_errors']==0 and route['native_antenna_nets']==0 and route['critical_disconnected_pins']==0
        assert route['global_route_source']['summary_sha256']==gp['summary_sha256']
        assert route['global_route_input']==dict(odb_sha256=sha(odb),guide_sha256=sha(guide),netlist_sha256=sha(netlist),native_ndr_screen=grt['native_ndr_screen'])
        require_same_proofs(current_spec,route['current_boot_source_revalidation'])
        route_root=ROOT/'hw/soc/out/cloud-replay-onehot-antenna-round4'
        restored,route_proof=reports.restore_report('replay-onehot-antenna-round4',39115222502,digest,parts,route_root,list(route['outputs']))
        assert restored==route
        r['actual_detailed_route_source']=route_proof
        r['detailed_route_complete']=True
        state_path=route_root/relative(route['detailed_route_state']);state=json.loads(state_path.read_text())
        final=json.loads((route_root/relative(route['final_state'])).read_text())
        odb=Path(state['odb']);deffile=Path(state['def']);netlist=Path(state['nl'])
        assert all(p.is_relative_to(route_root)for p in (odb,deffile,netlist))
        assert sha(odb)==route['routed_odb_sha256'] and sha(deffile)==route['routed_def_sha256']
        assert sha(final['odb'])==sha(odb) and sha(final['def'])==sha(deffile) and sha(final['nl'])==sha(netlist)
        for p in (odb,deffile,netlist):assert sha(p)==route['outputs'][str(p.relative_to(route_root))]
        assert sha(netlist)=='f7bb33ce5ea9c1f947ea582151e2086b4b031f284ee50ba667c4c291f3ee0846'
        assert sha(odb)=='b5a244a5e24109c2c5fb0ed5e92d98b999e7adbed50eaa9e70db5cdc50531835'
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        topology_method=ROOT/'scripts/check_onehot_round4_saved_topology.py'
        topology_path=OUT/'final-route-topology.json'
        with(OUT/'final-route-topology.log').open('w')as stream:
            code=subprocess.call(list(map(str,[app,'openroad','-exit','-python',topology_method])),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,env={**{k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')},'NSSOC_TOPOLOGY_BEFORE':str(grt_odb),'NSSOC_TOPOLOGY_AFTER':str(odb),'NSSOC_TOPOLOGY_OUT':str(topology_path)})
        if code:print((OUT/'final-route-topology.log').read_text()[-12000:],flush=True)
        assert code==0,'Actual final route topology proof failed; never extract an unproven candidate'
        topology=json.loads(topology_path.read_text());assert topology['status']=='PASS_NATIVE_SAVED_ROUTE_TOPOLOGY_ONLY_NOT_TIMING_OR_LVS'
        assert topology['proof']['added_diode_count']==3384 and len(topology['rejected'])==3
        r['actual_final_topology']=topology;save()
        cfg=json.loads((route_root/'trial-config.json').read_text())
        assert cfg['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
        assert cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5
        assert cfg['SETUP_VIOLATION_CORNERS']==cfg['HOLD_VIOLATION_CORNERS']==['*']
        assert cfg['PNR_SDC_FILE']==cfg['SIGNOFF_SDC_FILE']==str(PLACE/'prepared/physical.sdc')
        r['execution_config_changes']={'STA_THREADS':dict(before=cfg.get('STA_THREADS'),after=1)}
        cfg['STA_THREADS']=1;cfg['TIME_DERATING_CONSTRAINT']=5.0
        lp=json.loads((ROOT/'docs/evidence/onehot-load-logic-pass-20261018.json').read_text())
        source_root=ROOT/'hw/soc/out/cloud-onehot-load-logic'
        prepared,pproof=reports.restore_report('onehot-load-logic',lp['run'],lp['summary_sha256'],lp['parts_sha256'],source_root,list(lp['report']['outputs']))
        assert prepared==lp['report']and prepared['sources_unchanged']and prepared['inversion_control']['rejected']
        assert prepared['proof']['status']=='PASS within scope'and prepared['controls']['status']=='PASS_NATIVE_ECO_CONTROLS'
        assert prepared['proof']['positive_buffers_after']-prepared['proof']['positive_buffers_before']==50
        assert prepared['original_route_source']['summary_sha256']==route_pin['summary_sha256']
        assert prepared['preparation_source']['run']==39120628517 and prepared['geometry']['original_instances']==145038
        candidate_config=json.loads((source_root/'prepared/trial-config.json').read_text());assert candidate_config==cfg
        original_odb_for_comparison=odb
        state=json.loads((source_root/'candidate-state.json').read_text());odb=Path(state['odb']);netlist=Path(state['nl'])
        assert odb.is_relative_to(source_root)and netlist.is_relative_to(source_root)
        assert sha(odb)==prepared['candidate_odb_sha256']=='ef4a2cd71dcb448a104b2abacaf6a44848e3342b1ac0b23461ad926070a116ae'
        assert sha(netlist)==prepared['candidate_netlist_sha256']=='547eee3ac9cf503723f78b985f87841c2bde5277808f8716d0b6459bac55a62a'
        r['native_load_preparation']=pproof;r['native_load_equation_proof']=prepared['proof'];r['native_load_geometry_proof']=prepared['geometry']
        r['detailed_route_complete']=False
        # All original boot/placement/logic/route ancestry above remains mandatory.
        # Bind the new sizing proof to the intervening actually routed baseline.
        assert re.fullmatch('[0-9a-f]{40}',args.resize_head)
        assert all(re.fullmatch('[0-9a-f]{64}',v)for v in (args.resize_summary_sha256,args.resize_parts_sha256))
        latest_pin=json.loads((ROOT/'docs/evidence/onehot-load-resume-route-result-20261018.json').read_text())
        latest_run=api('actions/runs/'+str(latest_pin['run_id']))
        assert latest_run['status']=='completed'and latest_run['conclusion']=='success'and latest_run['head_sha']==latest_pin['source_head']and latest_run['run_attempt']==1
        assert latest_run['path']=='.github/workflows/onehot-load-resume-cloud.yml'
        latest,latest_sha,latest_parts=logic.summary('onehot-load-resume',latest_run)
        assert latest_sha==latest_pin['summary_sha256']and latest_parts==latest_pin['parts_sha256']
        assert latest['sources_unchanged']and latest['detailed_route_complete']and latest['native_routing_drc_errors']==0 and latest['critical_disconnected_pins']==0
        assert latest['native_load_preparation']['summary_sha256']==lp['summary_sha256']
        assert latest['native_load_equation_proof']==prepared['proof']and latest['native_load_geometry_proof']==prepared['geometry']
        assert latest['routed_candidate_topology']['proof']['retained_instances']==145088 and len(latest['routed_candidate_topology']['rejected'])==4
        assert latest['routed_candidate_topology']['inputs'][str(odb)]==sha(odb)
        sized_run=api('actions/runs/'+str(args.resize_run))
        assert sized_run['status']=='completed'and sized_run['conclusion']=='success'and sized_run['head_sha']==args.resize_head and sized_run['run_attempt']==1
        assert sized_run['path']=='.github/workflows/onehot-resize-prepare-cloud.yml'
        sized,sized_sha,sized_parts=logic.summary('onehot-resize-prepare',sized_run)
        assert sized_sha==args.resize_summary_sha256 and sized_parts==args.resize_parts_sha256
        assert sized['source_head']==args.resize_head and sized['sources_unchanged']
        assert sized['status']=='PASS_NATIVE_MEASURED_BUFFER_RESIZING_REQUIRES_ROUTE_RC_ALL_CORNER_STA'
        assert sized['proof']['status']=='PASS within scope'and sized['controls']['status']=='PASS_NATIVE_ECO_CONTROLS'and sized['inversion_control']['rejected']
        assert sized['source']['summary_sha256']==latest_sha and sized['source']['manifest_sha256']==latest_parts
        assert sized['original_route']['odb_sha256']==latest['routed_odb_sha256']and sized['original_route']['netlist_sha256']==latest['routed_netlist_sha256']
        assert sized['original_measurements']==latest['measurements']
        assert sized['geometry']['instances']==146728 and 1<=len(sized['geometry']['changes'])<=50
        assert all(sized['geometry'][k]for k in ('all_net_memberships_unchanged','all_other_instances_unchanged','pg_ports_ndr_unchanged'))
        sized_root=ROOT/'hw/soc/out/cloud-onehot-resize-prepare'
        restored,sized_proof=reports.restore_report('onehot-resize-prepare',args.resize_run,sized_sha,sized_parts,sized_root,list(sized['outputs']))
        assert restored==sized
        assert json.loads((sized_root/'proof/result.json').read_text())==sized['proof']and json.loads((sized_root/'geometry-proof.json').read_text())==sized['geometry']
        new_cfg=json.loads((sized_root/'trial-config.json').read_text())
        assert {k:v for k,v in new_cfg.items()if k!='DRT_ANTENNA_REPAIR_ITERS'}=={k:v for k,v in cfg.items()if k!='DRT_ANTENNA_REPAIR_ITERS'}
        assert cfg['DRT_ANTENNA_REPAIR_ITERS']==8 and new_cfg['DRT_ANTENNA_REPAIR_ITERS']==1
        cfg=new_cfg
        r['execution_config_changes']['DRT_ANTENNA_REPAIR_ITERS']=dict(before=8,after=1,reason='Continue one saved native antenna repair round per hosted run; zero-violation acceptance unchanged.')
        state_path=sized_root/'candidate-state.json';state=json.loads(state_path.read_text());odb=Path(state['odb']);netlist=Path(state['nl'])
        assert odb==sized_root/'candidate.odb'and netlist==sized_root/'candidate.v'
        assert sha(odb)==sized['candidate_odb_sha256']and sha(netlist)==sized['candidate_netlist_sha256']
        assert state['spef']is None and state['def']is None and not state['metrics']
        # State views also retain the original propagated SDC. Restore exact
        # missing views from the routed source archive instead of replacing
        # constraints or requiring its old route to be inherited by this ECO.
        latest_root=ROOT/'hw/soc/out/cloud-onehot-load-resume';missing=set()
        def inspect_view(value):
            if isinstance(value,dict):
                for v in value.values():inspect_view(v)
            elif isinstance(value,list):
                for v in value:inspect_view(v)
            elif isinstance(value,str)and value.startswith('/')and not Path(value).is_file():
                view=Path(value)
                assert view.is_relative_to(latest_root),('Unbound missing candidate-state dependency',value)
                rel=str(view.relative_to(latest_root));assert rel in latest['outputs'];missing.add(rel)
        inspect_view(state)
        assert missing,'Expected archived propagated SDC dependency'
        restored_latest,dependency_proof=reports.restore_report('onehot-load-resume',latest_pin['run_id'],latest_sha,latest_parts,latest_root,sorted(missing))
        assert restored_latest==latest
        dependency_hashes={str(latest_root/n):latest['outputs'][n]for n in sorted(missing)}
        assert all(sha(p)==v for p,v in dependency_hashes.items())
        r['restored_exact_state_dependencies']=dict(source=dependency_proof,files=dependency_hashes)

        # Chain the newly legalized logic candidate to the exact completed
        # resized baseline. Old route/boot/RTL ancestry above is preserved.
        r['previous_resize_source']=sized_proof
        r['previous_resize_geometry']=sized['geometry']
        old_route_pin=json.loads((ROOT/'docs/evidence/onehot-resize-route-report-rejection-20261019.json').read_text())
        verified_route=json.loads((ROOT/'docs/evidence/onehot-resize-saved-validation-20261019.json').read_text())['report']
        assert old_route_pin['report']['returncode']==0 and old_route_pin['report']['status']=='FAIL_OR_ERROR_NO_SOURCE_RESTART'
        assert old_route_pin['report']['resize_source']['summary_sha256']==sized_sha
        assert verified_route['sources_unchanged'] and verified_route['source']['summary_sha256']==old_route_pin['summary_sha256']
        assert verified_route['physical']==dict(drc_errors=0,critical_disconnected_pins=0)
        assert verified_route['routed_topology']['proof']['retained_instances']==146728
        assert verified_route['routed_topology']['proof']['added_diode_count']==1130
        np=json.loads((ROOT/'docs/evidence/onehot-logic-resize-prepare-pass-20261019.json').read_text())
        nr=api('actions/runs/'+str(np['run']))
        assert nr['status']=='completed' and nr['conclusion']=='success' and nr['head_sha']==np['source_head'] and nr['run_attempt']==1
        assert nr['path']=='.github/workflows/onehot-logic-resize-prepare-cloud.yml'
        new_root=ROOT/'hw/soc/out/cloud-onehot-logic-resize-prepare'
        new_sized,new_proof=reports.restore_report('onehot-logic-resize-prepare',np['run'],np['summary_sha256'],np['parts_sha256'],new_root,list(np['report']['outputs']))
        assert new_sized==np['report'] and new_sized['sources_unchanged']
        assert new_sized['status']=='PASS_NATIVE_MEASURED_LOGIC_RESIZING_REQUIRES_ROUTE_RC_ALL_CORNER_STA'
        assert new_sized['proof']['status']=='PASS within scope' and new_sized['controls']['status']=='PASS_NATIVE_ECO_CONTROLS' and new_sized['inversion_control']['rejected']
        assert new_sized['source']['summary_sha256']==old_route_pin['summary_sha256'] and new_sized['source']['manifest_sha256']==old_route_pin['parts_sha256']
        assert new_sized['original_route']==dict(odb_sha256='4acbb9969285c715969619795ec7a45305de1bd4a3f6ac97a91139cf0024b723',netlist_sha256='c05e6321a4aed063e5e69b902a3b7ed08863bd2a39189f8b17ded5bfc33b9756')
        assert new_sized['original_measurements']==verified_route['corners']
        assert new_sized['geometry']['instances']==147858 and len(new_sized['geometry']['changes'])==32
        assert all(new_sized['geometry'][k] for k in ('all_net_memberships_unchanged','all_other_instances_unchanged','pg_ports_ndr_unchanged'))
        assert json.loads((new_root/'proof/result.json').read_text())==new_sized['proof']
        assert json.loads((new_root/'geometry-proof.json').read_text())==new_sized['geometry']
        assert json.loads((new_root/'trial-config.json').read_text())==cfg
        sized=new_sized;sized_proof=new_proof;sized_root=new_root
        state_path=sized_root/'candidate-state.json';state=json.loads(state_path.read_text())
        odb=Path(state['odb']);netlist=Path(state['nl'])
        assert odb==sized_root/'candidate.odb' and netlist==sized_root/'candidate.v'
        assert sha(odb)==sized['candidate_odb_sha256'] and sha(netlist)==sized['candidate_netlist_sha256']
        assert state['spef']is None and state['def']is None and not state['metrics']
        # Missing views must belong to a pinned source archive at their original path.
        old_route_root=ROOT/'hw/soc/out/cloud-onehot-resize-route';new_missing=set()
        def collect_new_missing(value):
            if isinstance(value,dict):
                for v in value.values():collect_new_missing(v)
            elif isinstance(value,list):
                for v in value:collect_new_missing(v)
            elif isinstance(value,str)and value.startswith('/')and not Path(value).is_file():
                p=Path(value);assert p.is_relative_to(old_route_root),('Unbound new candidate dependency',value)
                rel=str(p.relative_to(old_route_root));assert rel in old_route_pin['report']['outputs'];new_missing.add(rel)
        collect_new_missing(state)
        if new_missing:
            old_restored,old_restore_proof=reports.restore_report(old_route_pin['group'],old_route_pin['run'],old_route_pin['summary_sha256'],old_route_pin['parts_sha256'],old_route_root,sorted(new_missing))
            assert old_restored==old_route_pin['report']
            dependency_hashes.update({str(old_route_root/n):old_restored['outputs'][n] for n in new_missing})
            r['new_state_dependency_source']=old_restore_proof
        assert all(sha(p)==v for p,v in dependency_hashes.items())
        r['restored_exact_state_dependencies']['files']=dependency_hashes
        r['source_routed_measurements']=verified_route['corners']
        r['resize_source']=sized_proof;r['resize_geometry']=sized['geometry'];r['resize_equation_proof']=sized['proof']

        # Bind the physically nearby positive-buffer candidate to the complete
        # previous native routed design. All older ancestry above still applies.
        baseline_pin=json.loads((ROOT/'docs/evidence/onehot-logic-resize-route-result-20261019.json').read_text())
        baseline_run=api('actions/runs/'+str(baseline_pin['run']))
        assert baseline_run['status']=='completed'and baseline_run['conclusion']=='success'and baseline_run['head_sha']==baseline_pin['source_head']and baseline_run['run_attempt']==1
        assert baseline_run['path']=='.github/workflows/onehot-logic-resize-route-cloud.yml'
        baseline,baseline_sha,baseline_parts=logic.summary(baseline_pin['group'],baseline_run)
        assert baseline==baseline_pin['report']and baseline_sha==baseline_pin['summary_sha256']and baseline_parts==baseline_pin['parts_sha256']
        assert baseline['sources_unchanged']and baseline['returncode']==0 and baseline['detailed_route_complete']
        assert baseline['resize_source']['summary_sha256']==np['summary_sha256']
        assert baseline['resize_equation_proof']==sized['proof']and baseline['resize_geometry']==sized['geometry']
        assert baseline['routed_candidate_topology']['proof']['retained_instances']==147858
        assert baseline['routed_candidate_topology']['proof']['added_diode_count']==974
        assert baseline['routed_candidate_topology']['inputs'][str(odb)]==sha(odb)
        assert baseline['native_routing_drc_errors']==0 and baseline['critical_disconnected_pins']==0
        bp=json.loads((ROOT/'docs/evidence/onehot-routed-drive-prepare-pass-20261019.json').read_text())
        br=api('actions/runs/'+str(bp['run']))
        assert bp['run']==39242341481 and bp['source_head']=='6163ef917ff57f346f88b873dd5df0f019e7fe5b'
        assert br['status']=='completed'and br['conclusion']=='success'and br['head_sha']==bp['source_head']and br['run_attempt']==1
        assert br['path']=='.github/workflows/onehot-routed-drive-prepare-cloud.yml'
        buffer_root=ROOT/'hw/soc/out/cloud-onehot-routed-drive-prepare'
        buffer_names=['candidate.odb','candidate.v','candidate-state.json','trial-config.json','proof/result.json','controls/result.json','geometry-proof.json','targets.json','actual-new-buffer-inversion-control.log']
        buffered,buffer_proof=reports.restore_report(bp['group'],bp['run'],bp['summary_sha256'],bp['parts_sha256'],buffer_root,buffer_names)
        assert buffered==bp['report']and buffered['sources_unchanged']
        assert buffered['status']=='PASS_NATIVE_NEAR_DRIVER_BUFFER_PREPARATION_REQUIRES_ROUTE_RC_ALL_CORNERS'
        assert buffered['source']['summary_sha256']==baseline_sha and buffered['source']['manifest_sha256']==baseline_parts
        assert buffered['original_route']==dict(odb_sha256=baseline['routed_odb_sha256'],netlist_sha256=baseline['routed_netlist_sha256'])
        assert buffered['original_measurements']==baseline['measurements']
        assert buffered['proof']['status']=='PASS within scope'and buffered['controls']['status']=='PASS_NATIVE_ECO_CONTROLS'and buffered['inversion_control']['rejected']
        assert buffered['proof']['positive_buffers_after']-buffered['proof']['positive_buffers_before']==39
        assert buffered['proof']['unobserved_output_port_changes']==0
        bg=buffered['geometry']
        assert bg['original_instances']==148832 and len(bg['added'])==len(bg['changes'])==39 and bg['maximum_driver_to_buffer_um']<=80
        assert all(bg[k]for k in ('all_original_cells_geometry_preserved','all_expected_net_memberships_preserved','pg_ports_ndr_unchanged'))
        assert json.loads((buffer_root/'proof/result.json').read_text())==buffered['proof']
        assert json.loads((buffer_root/'geometry-proof.json').read_text())==bg
        assert json.loads((buffer_root/'controls/result.json').read_text())==buffered['controls']
        assert json.loads((buffer_root/'trial-config.json').read_text())==cfg
        state_path=buffer_root/'candidate-state.json';state=json.loads(state_path.read_text())
        odb=Path(state['odb']);netlist=Path(state['nl'])
        assert odb==buffer_root/'candidate.odb'and netlist==buffer_root/'candidate.v'
        assert sha(odb)==buffered['candidate_odb_sha256']and sha(netlist)==buffered['candidate_netlist_sha256']
        assert state['spef']is None and state['def']is None and not state['metrics']
        baseline_root=ROOT/'hw/soc/out/cloud-onehot-logic-resize-route';buffer_missing=set()
        def collect_buffer_missing(value):
            if isinstance(value,dict):
                for v in value.values():collect_buffer_missing(v)
            elif isinstance(value,list):
                for v in value:collect_buffer_missing(v)
            elif isinstance(value,str)and value.startswith('/')and not Path(value).is_file():
                p=Path(value);assert p.is_relative_to(baseline_root),('Unbound buffered candidate dependency',value)
                rel=str(p.relative_to(baseline_root));assert rel in baseline['outputs'];buffer_missing.add(rel)
        collect_buffer_missing(state)
        if buffer_missing:
            restored_baseline,baseline_view_proof=reports.restore_report(baseline_pin['group'],baseline_pin['run'],baseline_sha,baseline_parts,baseline_root,sorted(buffer_missing))
            assert restored_baseline==baseline
            dependency_hashes.update({str(baseline_root/n):baseline['outputs'][n]for n in buffer_missing})
            r['buffer_state_dependency_source']=baseline_view_proof
        assert all(sha(p)==v for p,v in dependency_hashes.items())
        r['restored_exact_state_dependencies']['files']=dependency_hashes
        r['source_routed_measurements']=baseline['measurements']
        r['near_driver_buffer_source']=buffer_proof
        r['near_driver_buffer_geometry']=bg
        r['near_driver_buffer_equation_proof']=buffered['proof']
        r['native_routed_baseline']=dict(run=baseline_pin['run'],summary_sha256=baseline_sha,parts_sha256=baseline_parts,antenna=baseline['final_antenna'],timing_and_electrical_counts_met=baseline['all_reported_timing_and_electrical_gates_met'])


        # Continue from the exact measured route, preserving every earlier proof.
        critical_baseline_pin=json.loads((ROOT/'docs/evidence/onehot-near-driver-route-result-20261019.json').read_text())
        critical_baseline_run=api('actions/runs/'+str(critical_baseline_pin['run']))
        assert critical_baseline_pin['run']==39243328773
        assert critical_baseline_run['status']=='completed'and critical_baseline_run['conclusion']=='success'
        assert critical_baseline_run['head_sha']==critical_baseline_pin['source_head']=='25874ce85d044e5297a2be157eb078c2f595b9ef'
        assert critical_baseline_run['run_attempt']==1 and critical_baseline_run['path']=='.github/workflows/onehot-routed-drive-route-cloud.yml'
        critical_baseline,critical_baseline_sha,critical_baseline_parts=logic.summary(critical_baseline_pin['group'],critical_baseline_run)
        assert critical_baseline==critical_baseline_pin['report']
        assert critical_baseline_sha==critical_baseline_pin['summary_sha256']and critical_baseline_parts==critical_baseline_pin['parts_sha256']
        assert critical_baseline['sources_unchanged']and critical_baseline['returncode']==0 and critical_baseline['detailed_route_complete']
        assert critical_baseline['native_routing_drc_errors']==0 and critical_baseline['critical_disconnected_pins']==0
        assert critical_baseline['near_driver_buffer_source']['summary_sha256']==bp['summary_sha256']
        assert critical_baseline['near_driver_buffer_geometry']==bg
        assert critical_baseline['near_driver_buffer_equation_proof']==buffered['proof']
        cb_topology=critical_baseline['routed_candidate_topology']
        assert cb_topology['proof']['retained_instances']==148871 and cb_topology['proof']['added_diode_count']==721
        assert cb_topology['inputs'][str(odb)]==sha(odb)
        cp=json.loads((ROOT/'docs/evidence/onehot-critical-data-prepare-pass-20261019.json').read_text())
        cr=api('actions/runs/'+str(cp['run']))
        assert cp['run']==39292665637 and cp['source_head']=='173311bb553b200285893690a3feca7aa47fcc36'
        assert cr['status']=='completed'and cr['conclusion']=='success'and cr['head_sha']==cp['source_head']and cr['run_attempt']==1
        assert cr['path']=='.github/workflows/onehot-critical-data-prepare-cloud.yml'
        critical_root=ROOT/'hw/soc/out/cloud-onehot-critical-data-prepare'
        critical_names=['candidate.odb','candidate.v','candidate-state.json','trial-config.json','proof/result.json','controls/result.json','geometry-proof.json','geometry.json','targets.json','actual-new-buffer-inversion-control.log']
        critical,critical_proof=reports.restore_report(cp['group'],cp['run'],cp['summary_sha256'],cp['parts_sha256'],critical_root,critical_names)
        assert critical==cp['report']and critical['sources_unchanged']
        assert critical['status']=='PASS_NATIVE_CRITICAL_DATA_BUFFER_PREPARATION_REQUIRES_ROUTE_RC_ALL_CORNERS'
        assert critical['source']['summary_sha256']==critical_baseline_sha and critical['source']['manifest_sha256']==critical_baseline_parts
        assert critical['original_route']==dict(odb_sha256=critical_baseline['routed_odb_sha256'],netlist_sha256=critical_baseline['routed_netlist_sha256'])
        assert critical['original_measurements']==critical_baseline['measurements']
        assert critical['proof']['status']=='PASS within scope'and critical['controls']['status']=='PASS_NATIVE_ECO_CONTROLS'and critical['inversion_control']['rejected']
        assert critical['proof']['positive_buffers_after']-critical['proof']['positive_buffers_before']==33
        assert critical['proof']['unobserved_output_port_changes']==0
        cg=critical['geometry']
        assert cg['original_instances']==149592 and len(cg['added'])==len(cg['changes'])==33 and cg['maximum_driver_to_buffer_um']<=80
        assert all(cg[k]for k in ('all_original_cells_geometry_preserved','all_expected_net_memberships_preserved','pg_ports_ndr_unchanged'))
        assert json.loads((critical_root/'proof/result.json').read_text())==critical['proof']
        assert json.loads((critical_root/'geometry-proof.json').read_text())==cg
        assert json.loads((critical_root/'controls/result.json').read_text())==critical['controls']
        assert json.loads((critical_root/'geometry.json').read_text())==critical['source_geometry']
        assert json.loads((critical_root/'targets.json').read_text())==critical['selection']
        assert critical['source_geometry']['source_instance_count']==149592
        assert json.loads((critical_root/'trial-config.json').read_text())==cfg
        state_path=critical_root/'candidate-state.json';state=json.loads(state_path.read_text())
        odb=Path(state['odb']);netlist=Path(state['nl'])
        assert odb==critical_root/'candidate.odb'and netlist==critical_root/'candidate.v'
        assert sha(odb)==critical['candidate_odb_sha256']=='d53c65ecd69fa09f8d0112653fc4c2143ebf0f2116c819408bb784ba37e37d34'
        assert sha(netlist)==critical['candidate_netlist_sha256']=='be29f14ebae7a4685b16f854e0db8192f6313ce9ec14a9bcc61c902c4f425ecc'
        assert state['spef']is None and state['def']is None and not state['metrics']
        critical_baseline_root=ROOT/'hw/soc/out/cloud-onehot-routed-drive-route';critical_missing=set()
        def collect_critical_missing(value):
            if isinstance(value,dict):
                for v in value.values():collect_critical_missing(v)
            elif isinstance(value,list):
                for v in value:collect_critical_missing(v)
            elif isinstance(value,str)and value.startswith('/')and not Path(value).is_file():
                p=Path(value);assert p.is_relative_to(critical_baseline_root),('Unbound critical-data state dependency',value)
                rel=str(p.relative_to(critical_baseline_root));assert rel in critical_baseline['outputs'];critical_missing.add(rel)
        collect_critical_missing(state)
        if critical_missing:
            restored_cb,cb_view_proof=reports.restore_report(critical_baseline_pin['group'],critical_baseline_pin['run'],critical_baseline_sha,critical_baseline_parts,critical_baseline_root,sorted(critical_missing))
            assert restored_cb==critical_baseline
            dependency_hashes.update({str(critical_baseline_root/n):critical_baseline['outputs'][n]for n in critical_missing})
            r['critical_state_dependency_source']=cb_view_proof
        assert all(sha(p)==v for p,v in dependency_hashes.items())
        r['restored_exact_state_dependencies']['files']=dependency_hashes
        r['source_routed_measurements']=critical_baseline['measurements']
        r['critical_data_buffer_source']=critical_proof
        r['critical_data_buffer_geometry']=cg
        r['critical_data_buffer_equation_proof']=critical['proof']
        r['previous_native_routed_baseline']=r['native_routed_baseline']
        r['native_routed_baseline']=dict(run=critical_baseline_pin['run'],summary_sha256=critical_baseline_sha,parts_sha256=critical_baseline_parts,antenna=critical_baseline['final_antenna'],timing_and_electrical_counts_met=critical_baseline['all_reported_timing_and_electrical_gates_met'])


        # Add the new prepared candidate after revalidating every original
        # boot/logic/placement/route/RC dependency above.
        coverage_baseline_pin=json.loads((ROOT/'docs/evidence/onehot-critical-data-route-result-20261020.json').read_text())
        coverage_baseline_run=api('actions/runs/'+str(coverage_baseline_pin['run']))
        assert coverage_baseline_pin['run']==39293720171
        assert coverage_baseline_run['status']=='completed' and coverage_baseline_run['conclusion']=='success'
        assert coverage_baseline_run['head_sha']==coverage_baseline_pin['source_head']=='ca6a4d0e143ec95d836201887b96d187ecdccb39'
        assert coverage_baseline_run['run_attempt']==1 and coverage_baseline_run['path']=='.github/workflows/onehot-critical-data-route-cloud.yml'
        coverage_baseline,coverage_baseline_sha,coverage_baseline_parts=logic.summary(coverage_baseline_pin['group'],coverage_baseline_run)
        assert coverage_baseline==coverage_baseline_pin['report']
        assert coverage_baseline_sha==coverage_baseline_pin['summary_sha256'] and coverage_baseline_parts==coverage_baseline_pin['parts_sha256']
        assert coverage_baseline['sources_unchanged'] and coverage_baseline['returncode']==0 and coverage_baseline['detailed_route_complete']
        assert coverage_baseline['native_routing_drc_errors']==0 and coverage_baseline['critical_disconnected_pins']==0
        assert coverage_baseline['critical_data_buffer_source']['summary_sha256']==cp['summary_sha256']
        assert coverage_baseline['critical_data_buffer_geometry']==cg
        assert coverage_baseline['critical_data_buffer_equation_proof']==critical['proof']
        cbtop=coverage_baseline['routed_candidate_topology']
        assert cbtop['proof']['retained_instances']==149625 and cbtop['proof']['added_diode_count']==666
        assert cbtop['inputs'][str(odb)]==sha(odb)
        vp=json.loads((ROOT/'docs/evidence/onehot-coverage-data-prepare-pass-20261020.json').read_text())
        vr=api('actions/runs/'+str(vp['run']))
        assert vp['run']==39330987654 and vp['source_head']=='f98f85cc304119f256c1406ffda6774f5d43d32c'
        assert vr['status']=='completed' and vr['conclusion']=='success' and vr['head_sha']==vp['source_head'] and vr['run_attempt']==1
        assert vr['path']=='.github/workflows/onehot-coverage-data-prepare-cloud.yml'
        coverage_root=ROOT/'hw/soc/out/cloud-onehot-coverage-data-prepare'
        coverage_names=['candidate.odb','candidate.v','candidate-state.json','trial-config.json','proof/result.json','controls/result.json','geometry-proof.json','geometry.json','targets.json','native-site-attempts.json','actual-new-buffer-inversion-control.log']
        coverage,coverage_proof=reports.restore_report(vp['group'],vp['run'],vp['summary_sha256'],vp['parts_sha256'],coverage_root,coverage_names)
        assert {k:coverage[k]for k in vp['report_excerpt']}==vp['report_excerpt']
        assert coverage['source_head']==vp['source_head'] and coverage['sources_unchanged']
        assert coverage['status']=='PASS_NATIVE_HOLD_SCREENED_COVERAGE_BUFFER_PREPARATION_REQUIRES_ROUTE_RC_ALL_CORNERS'
        assert coverage['source']['summary_sha256']==coverage_baseline_sha and coverage['source']['manifest_sha256']==coverage_baseline_parts
        assert coverage['original_route']==dict(odb_sha256=coverage_baseline['routed_odb_sha256'],netlist_sha256=coverage_baseline['routed_netlist_sha256'])
        assert coverage['original_measurements']==coverage_baseline['measurements']
        assert coverage['proof']['status']=='PASS within scope' and coverage['controls']['status']=='PASS_NATIVE_ECO_CONTROLS' and coverage['inversion_control']['rejected']
        assert coverage['proof']['positive_buffers_after']-coverage['proof']['positive_buffers_before']==128
        assert coverage['proof']['unobserved_output_port_changes']==0
        vg=coverage['geometry']
        assert vg['original_instances']==150291 and len(vg['added'])==len(vg['changes'])==128 and vg['maximum_driver_to_buffer_um']<=80
        assert all(vg[k]for k in ('all_original_cells_geometry_preserved','all_expected_net_memberships_preserved','pg_ports_ndr_unchanged'))
        assert sum(x['buffer_master']=='sg13g2_buf_16'for x in vg['changes'])==124
        assert sum(x['buffer_master']=='sg13g2_buf_8'for x in vg['changes'])==4
        for path,key in [('proof/result.json','proof'),('controls/result.json','controls'),('geometry-proof.json','geometry'),('geometry.json','source_geometry'),('targets.json','selection')]:
            assert json.loads((coverage_root/path).read_text())==coverage[key]
        assert coverage['source_geometry']['source_instance_count']==150291 and coverage['source_geometry']['selected_net_count']==128
        assert coverage['selection']['hold_screen_ns']==.2 and len(coverage['selection']['targets'])==128
        attempts=json.loads((coverage_root/'native-site-attempts.json').read_text())
        assert len(attempts)==128 and all(a['attempts'][-1]['accepted'] and a['attempts'][-1]['distance_um']<=80 for a in attempts)
        assert json.loads((coverage_root/'trial-config.json').read_text())==cfg
        state_path=coverage_root/'candidate-state.json';state=json.loads(state_path.read_text())
        odb=Path(state['odb']);netlist=Path(state['nl'])
        assert odb==coverage_root/'candidate.odb' and netlist==coverage_root/'candidate.v'
        assert sha(odb)==coverage['candidate_odb_sha256']=='6e9ee73448e4cfb0e63129984278b084605f314bc5caa5054b0a72a1e66a5a3b'
        assert sha(netlist)==coverage['candidate_netlist_sha256']=='97cdc9677282fa0330a752de12b66be3f5ab1659e02d2245184b69ab8d98e97e'
        assert state['spef']is None and state['def']is None and not state['metrics']
        coverage_baseline_root=ROOT/'hw/soc/out/cloud-onehot-critical-data-route';coverage_missing=set()
        def collect_coverage_missing(value):
            if isinstance(value,dict):
                for v in value.values():collect_coverage_missing(v)
            elif isinstance(value,list):
                for v in value:collect_coverage_missing(v)
            elif isinstance(value,str)and value.startswith('/')and not Path(value).is_file():
                p=Path(value);assert p.is_relative_to(coverage_baseline_root),('Unbound coverage state dependency',value)
                rel=str(p.relative_to(coverage_baseline_root));assert rel in coverage_baseline['outputs'];coverage_missing.add(rel)
        collect_coverage_missing(state)
        if coverage_missing:
            restored_cv,cv_view_proof=reports.restore_report(coverage_baseline_pin['group'],coverage_baseline_pin['run'],coverage_baseline_sha,coverage_baseline_parts,coverage_baseline_root,sorted(coverage_missing))
            assert restored_cv==coverage_baseline
            dependency_hashes.update({str(coverage_baseline_root/n):coverage_baseline['outputs'][n]for n in coverage_missing})
            r['coverage_state_dependency_source']=cv_view_proof
        assert all(sha(p)==v for p,v in dependency_hashes.items())
        r['restored_exact_state_dependencies']['files']=dependency_hashes
        r['source_routed_measurements']=coverage_baseline['measurements']
        r['coverage_data_buffer_source']=coverage_proof
        r['coverage_data_buffer_geometry']=vg
        r['coverage_data_buffer_equation_proof']=coverage['proof']
        r['coverage_original_native_routed_baseline']=r['native_routed_baseline']
        r['native_routed_baseline']=dict(run=coverage_baseline_pin['run'],summary_sha256=coverage_baseline_sha,parts_sha256=coverage_baseline_parts,antenna=coverage_baseline['final_antenna'],timing_and_electrical_counts_met=coverage_baseline['all_reported_timing_and_electrical_gates_met'])


        # The source above is the immutable boot-to-128-buffer provenance.
        # Route only the physically proven single-clock transfer below.
        clock_pin=json.loads((ROOT/'docs/evidence/onehot-clock-restore-pass-20261020.json').read_text())
        clock_run=api('actions/runs/'+str(clock_pin['run']))
        assert clock_run['status']=='completed'and clock_run['conclusion']=='success'
        assert clock_run['head_sha']==clock_pin['source_head']and clock_run['run_attempt']==1
        assert clock_run['path']=='.github/workflows/onehot-clock-restore-cloud.yml'
        clock_root=ROOT/'hw/soc/out/cloud-onehot-clock-restore'
        clock_names=['candidate.odb','candidate.v','candidate.def','candidate-state.json','trial-config.json',
          'transfer-plan.json','transfer-proof.json','clock-statement-proof.json','clock-patch.def','sources.json']
        clock,clock_proof=reports.restore_report(clock_pin['group'],clock_pin['run'],clock_pin['summary_sha256'],
          clock_pin['parts_sha256'],clock_root,clock_names)
        assert clock==clock_pin['report']and clock['sources_unchanged']
        assert clock['status']=='PASS_NATIVE_CLOCK_ROUTE_TRANSFER_REQUIRES_PHYSICAL_LEGALIZATION_RC_AND_STA'
        assert clock['netlist_literal_identity']and all(clock['controls'].values())
        assert clock['sources']['before']['run']==39293720171
        assert clock['sources']['after']['run']==39331918238
        assert json.loads((clock_root/'trial-config.json').read_text())==cfg
        transfer=clock['proof']
        assert transfer['net']=='clknet_3_5_0_pcie_clk_i'
        assert all(transfer[k]for k in ('source_pin_positions_unchanged','all_unrelated_def_content_unchanged',
            'original_clock_route_restored_exactly','physical_via_definitions_exact'))
        assert json.loads((clock_root/'transfer-proof.json').read_text())==transfer
        current_pin=json.loads((ROOT/'docs/evidence/onehot-coverage-data-route-result-20261020.json').read_text())
        assert current_pin['run']==39331918238 and current_pin['summary_sha256']==clock['sources']['after']['summary']
        current_run=api('actions/runs/'+str(current_pin['run']))
        assert current_run['status']=='completed'and current_run['conclusion']=='success'
        assert current_run['head_sha']==current_pin['source_head']and current_run['run_attempt']==1
        assert current_run['path']=='.github/workflows/onehot-coverage-data-route-cloud.yml'
        # This receipt deliberately contains metrics, not the full report.
        # Restore the immutable report and verify both pinned asset digests.
        current,current_summary_sha,current_parts_sha=logic.summary(current_pin['group'],current_run)
        assert current_summary_sha==current_pin['summary_sha256']==clock['sources']['after']['summary']
        assert current_parts_sha==current_pin['parts_sha256']==clock['sources']['after']['parts']
        assert current['source_head']==current_pin['source_head']
        r['clock_current_route_report_source']=dict(run=current_pin['run'],
            summary_sha256=current_summary_sha,parts_sha256=current_parts_sha)
        assert current['sources_unchanged']and current['returncode']==0 and current['detailed_route_complete']
        assert current['native_routing_drc_errors']==0 and current['critical_disconnected_pins']==0
        assert current['measurements']==clock['original_measurements']
        state_path=clock_root/'candidate-state.json';state=json.loads(state_path.read_text())
        odb=Path(state['odb']);netlist=Path(state['nl'])
        assert odb==clock_root/'candidate.odb'and netlist==clock_root/'candidate.v'
        assert sha(odb)==clock['candidate_odb_sha256']==transfer['candidate_odb_sha256']
        assert sha(netlist)==clock['candidate_netlist_sha256']
        assert state['spef']is None and not state['metrics']
        current_root=ROOT/'hw/soc/out/cloud-onehot-coverage-data-route';clock_missing=set()
        def collect_clock_missing(value):
            if isinstance(value,dict):
                for v in value.values():collect_clock_missing(v)
            elif isinstance(value,list):
                for v in value:collect_clock_missing(v)
            elif isinstance(value,str)and value.startswith('/')and not Path(value).is_file():
                p=Path(value);assert p.is_relative_to(current_root),('Unbound clock transfer state dependency',value)
                rel=str(p.relative_to(current_root));assert rel in current['outputs'];clock_missing.add(rel)
        collect_clock_missing(state)
        if clock_missing:
            restored_clock_baseline,clock_dependency_proof=reports.restore_report(current_pin['group'],current_pin['run'],
              current_pin['summary_sha256'],current_pin['parts_sha256'],current_root,sorted(clock_missing))
            assert restored_clock_baseline==current
            dependency_hashes.update({str(current_root/n):current['outputs'][n]for n in clock_missing})
            r['clock_state_dependency_source']=clock_dependency_proof
        assert all(sha(p)==v for p,v in dependency_hashes.items())
        r['restored_exact_state_dependencies']['files']=dependency_hashes
        r['source_routed_measurements']=current['measurements']
        r['clock_route_transfer_source']=clock_proof;r['clock_route_transfer_proof']=transfer
        r['clock_original_native_routed_baseline']=r['native_routed_baseline']
        r['native_routed_baseline']=dict(run=current_pin['run'],summary_sha256=current_pin['summary_sha256'],
           parts_sha256=current_pin['parts_sha256'],antenna=current['final_antenna'],
           timing_and_electrical_counts_met=current['all_reported_timing_and_electrical_gates_met'])
        r['detailed_route_complete']=False

        saved_candidate_odb=odb
        trial=OUT/'trial-config.json';trial.write_text(json.dumps(cfg,indent=2)+'\n')
        r['discarded_inherited_metric_count']=len(state['metrics']);state['metrics']={}
        state['spef']=None
        initial=OUT/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        flow=ROOT/'hw/soc/pnr/onehot_clock_restore_route_flow.py'
        protected={str(p):sha(p)for p in [Path(__file__),flow,topology_method,topology_path,ROOT/'hw/soc/pnr/interface_flow.py',ROOT/'hw/soc/flow/audit_estimated_spef.py',ROOT/'hw/soc/flow/check_timing_derate.tcl',PLACE/'prepared/physical.sdc',state_path,odb,deffile,netlist,trial,initial]}
        protected.update({str(buffer_root/n):buffered['outputs'][n]for n in buffer_names})
        protected.update({str(critical_root/n):critical['outputs'][n]for n in critical_names})
        protected.update({str(coverage_root/n):coverage['outputs'][n]for n in coverage_names})
        protected.update({str(clock_root/n):clock['outputs'][n]for n in clock_names})
        for path in (ROOT/'scripts/check_onehot_fixed_clock_route.py',ROOT/'scripts/prepare_onehot_clock_restore.py',
          ROOT/'docs/evidence/onehot-clock-restore-pass-20261020.json',ROOT/'docs/evidence/onehot-coverage-data-route-result-20261020.json'):
            protected[str(path)]=sha(path)
        command=[str(app),'python',str(flow),'--flow','OnehotClockRestoreRoute','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(trial)]
        r.update(status='RUNNING_NATIVE_FIXED_CLOCK_LEGALIZATION_AND_FRESH_RC_STA',protected_inputs=protected,command=command);save()
        (OUT/'run').mkdir();start=time.monotonic()
        with(OUT/'native.log').open('w')as log:code=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.update(returncode=code,elapsed_s=time.monotonic()-start);save()
        if code:print((OUT/'native.log').read_text(errors='replace')[-16000:],flush=True)
        assert code==0,'Native extraction or STA failed; retain all outputs'
        dr=list((OUT/'run').glob('*-openroad-detailedrouting/state_out.json'));ar=list((OUT/'run').glob('*-openroad-checkantennas/state_out.json'));pr=list((OUT/'run').glob('*-odb-reportdisconnectedpins/state_out.json'))
        assert len(dr)==len(ar)==len(pr)==1
        routed=json.loads(dr[0].read_text());physical=json.loads(pr[0].read_text())['metrics'];antenna=json.loads(ar[0].read_text())
        antenna_report=ar[0].parent/'reports/antenna.rpt';count=len(re.findall(r'(?m)^\s*Net:\s*\S+',antenna_report.read_text()))
        from check_final_native_antenna_counts import validate as final_antenna_counts
        r['final_antenna']=final_antenna_counts(antenna_report.read_text(),antenna['metrics'])
        assert count==r['final_antenna']['final_violating_nets']
        r.update(native_antenna_nets=count,native_routing_drc_errors=physical['route__drc_errors'],critical_disconnected_pins=physical['design__critical_disconnected_pin__count'],detailed_route_complete=True,routed_odb_sha256=sha(routed['odb']),routed_netlist_sha256=sha(routed['nl']));save()
        method=ROOT/'scripts/check_onehot_coverage_data_routed_topology.py';output=OUT/'routed-candidate-topology.json'
        with(OUT/'routed-candidate-topology.log').open('w')as log:ret=subprocess.call([str(app),'openroad','-exit','-python',str(method)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**{k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')},'NSSOC_TOPOLOGY_BEFORE':str(saved_candidate_odb),'NSSOC_TOPOLOGY_AFTER':routed['odb'],'NSSOC_TOPOLOGY_OUT':str(output)})
        if ret:print((OUT/'routed-candidate-topology.log').read_text()[-12000:],flush=True)
        assert ret==0,'Actual routed candidate geometry or topology changed'
        r['routed_candidate_topology']=json.loads(output.read_text());assert r['routed_candidate_topology']['proof']['retained_instances']==150419 and len(r['routed_candidate_topology']['rejected'])==4
        fixed_method=ROOT/'scripts/check_onehot_fixed_clock_route.py';fixed_output=OUT/'fixed-clock-route-proof.json'
        with(OUT/'fixed-clock-route-proof.log').open('w')as log:
            fixed_code=subprocess.call([str(app),'openroad','-exit','-python',str(fixed_method)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
              env={**{k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')},
                'NSSOC_TOPOLOGY_BEFORE':str(saved_candidate_odb),'NSSOC_TOPOLOGY_AFTER':routed['odb'],
                'NSSOC_CLOCK_ROUTE_PROOF_OUT':str(fixed_output)})
        if fixed_code:print((OUT/'fixed-clock-route-proof.log').read_text()[-12000:],flush=True)
        assert fixed_code==0,'Native DRT changed original physical fixed clock route'
        r['fixed_clock_route_proof']=json.loads(fixed_output.read_text())
        assert r['fixed_clock_route_proof']['original_physical_route_preserved']
        r['native_physical_gates_met']=count==0 and r['native_routing_drc_errors']==0 and r['critical_disconnected_pins']==0
        assert all(sha(source_root/n)==v for n,v in prepared['outputs'].items())
        assert all(sha(sized_root/n)==v for n,v in sized['outputs'].items())
        assert all(sha(p)==v for p,v in dependency_hashes.items())
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
        r.update(status='COMPLETE_NATIVE_FIXED_CLOCK_ROUTE_RC_THREE_CORNERS_NOT_SIGNOFF',measurements=measurements,all_reported_timing_and_electrical_gates_met=all_met,sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR_NO_SOURCE_RESTART',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
