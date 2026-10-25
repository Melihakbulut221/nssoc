#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Route the exact proven onehot targeted repair with original physical budgets."""
import argparse,json,os,re,subprocess,time
from pathlib import Path
import cloud_replay_onehot_logic as logic
import compare_cloud_routed_endpoints as reports
from cloud_corrpre_banked_handoff import api,wait_success
from cloud_replay_onehot_postcts import require_candidate,relative,sha
from route_cloud_newer_postcts import native_ndr_screen
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-replay-onehot-global-route'
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
        scope='First global routing of exact onehot targeted repair39080594759. Original20/4/8/8ns clocks,5percent derate,20SRAM,20percent routing reserve. ClockMetal4..TopMetal2,200iterations, nativeNDR andzerooverflow required. Not detailed routing, extracted timing or serial PHY acceptance.')
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

        assert cfg['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
        assert cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5
        assert cfg['SETUP_VIOLATION_CORNERS']==cfg['HOLD_VIOLATION_CORNERS']==['*']
        assert cfg['PNR_SDC_FILE']==cfg['SIGNOFF_SDC_FILE']==str(PLACE/'prepared/physical.sdc')
        assert len(before['preparation']['macros'])==20
        assert cfg.get('GRT_ALLOW_CONGESTION',False) is False,'Do not accept an overflowing route'
        assert cfg['DESIGN_REPAIR_REMOVE_BUFFERS'] is False
        assert cfg.get('RT_CLOCK_MIN_LAYER') is None and cfg.get('RT_CLOCK_MAX_LAYER') is None
        assert cfg['GRT_ADJUSTMENT']==0.2 and cfg.get('GRT_OVERFLOW_ITERS',50)==50
        unchanged=dict(cfg)
        cfg.update(RT_CLOCK_MIN_LAYER='Metal4',RT_CLOCK_MAX_LAYER='TopMetal2',GRT_OVERFLOW_ITERS=200)
        allowed={'RT_CLOCK_MIN_LAYER','RT_CLOCK_MAX_LAYER','GRT_OVERFLOW_ITERS'}
        assert {k:v for k,v in cfg.items()if k not in allowed}=={k:v for k,v in unchanged.items()if k not in allowed}
        r['route_experiment']=dict(clock_layers=['Metal4','TopMetal2'],signal_layers=['Metal2','TopMetal2'],capacity_reserve=0.2,overflow_iterations=200,
            config_delta={k:dict(before=unchanged.get(k),after=cfg[k])for k in sorted(allowed)},
            scope='Fresh new candidate route, not a restart of the rejected older CRC/regional route. No old congestion coordinates reused. Require original NDR and zero overflow; inspect fresh diagnostics before any regional change.')
        cfg['TIME_DERATING_CONSTRAINT']=5.0
        trial=OUT/'trial-config.json';trial.write_text(json.dumps(cfg,indent=2)+'\n')
        r['discarded_inherited_metrics']=len(state['metrics']);state['metrics']={}
        initial=OUT/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        flow=ROOT/'hw/soc/pnr/corrpre_banked_clock200_grt_flow.py'
        protected={str(p):sha(p)for p in [Path(__file__),flow,
            ROOT/'hw/soc/pnr/corrpre_postcts_flow.py',ROOT/'hw/soc/pnr/interface_flow.py',
            ROOT/'hw/soc/flow/check_timing_derate.tcl',config_path,PLACE/'prepared/physical.sdc',
            state_path,odb,netlist,trial,initial]}
        command=[str(app),'python',str(flow),'--flow','CorrpreBankedGlobalRouting',
            '--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2',
            '--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),
            '--with-initial-state',str(initial),str(trial)]
        r.update(status='RUNNING_NATIVE_BANKED_GLOBAL_ROUTING',protected_inputs=protected,command=command);save()
        (OUT/'run').mkdir();start=time.monotonic()
        with(OUT/'native.log').open('w')as log:
            code=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.update(returncode=code,elapsed_s=time.monotonic()-start);save()
        route_logs=list((OUT/'run').glob('*-openroad-globalrouting/openroad-globalrouting.log'))
        observed='\n'.join(p.read_text(errors='replace')for p in route_logs)
        r['native_ndr_screen']=native_ndr_screen(observed)
        r['native_route_tail']=observed.splitlines()[-160:]
        r['native_200_iterations_verified']='global_route -congestion_iterations 200' in observed
        r['native_congestion_reports']={str(p.relative_to(OUT)):sha(p)for p in (OUT/'run').rglob('*congestion*.rpt')if p.is_file()}
        r['native_report_options_verified']='NSSOC_CONGESTION_REPORT_EVERY_25_ITERATIONS' in observed
        r['native_clock_layer_selection_verified']='clock min routing layer to Metal4.' in observed and 'clock max routing layer to TopMetal2.' in observed
        save()
        if code:print('\n'.join(r['native_route_tail']),flush=True)
        assert code==0,'Native global route failed; every completed state retained'
        assert r['native_clock_layer_selection_verified'],'Native clock layer selection not applied'
        assert r['native_200_iterations_verified']and r['native_report_options_verified'],'Native search/report options missing'
        states=list((OUT/'run').glob('*-openroad-globalrouting/state_out.json'));assert len(states)==1
        folder=states[0].parent
        logs=list(folder.glob('*.log'));assert logs
        text='\n'.join(p.read_text(errors='replace')for p in logs)
        ndr=native_ndr_screen(text);r['native_ndr_screen']=ndr;save()
        assert ndr['preserved'],'Native router relaxed NDR; route rejected'
        totals=[line for line in observed.splitlines()if line.startswith('Total ')]
        assert totals and totals[-1].split()[-1]=='0','Native final congestion table is not zero overflow'
        r['native_final_congestion_total']=totals[-1]

        assert not re.search(r'(?m)^(Error:|\[ERROR)',text)
        counts=re.findall(r'\[INFO GRT-0014\] Routed nets: (\d+)',text)
        assert len(counts)==1 and int(counts[0])>0,'Missing native routed-net count'
        guide=folder/'after_grt.guide';assert guide.is_file()and guide.stat().st_size>0
        final=json.loads(states[0].read_text());db=Path(final['odb'])
        assert db.is_relative_to(OUT/'run')and db.is_file()
        assert all(sha(p)==digest for p,digest in protected.items())
        r.update(status='COMPLETE_NATIVE_ONEHOT_GLOBAL_ROUTE_REQUIRES_DRT_EXTRACTED_STA_AND_SIGNOFF',
            sources_unchanged=True,global_route_state=str(states[0].relative_to(OUT)),
            global_route_odb_sha256=sha(db),guide_sha256=sha(guide),
            native_routed_nets=int(counts[0]),metrics=final['metrics'])
    except BaseException as error:
        r.update(status='FAIL_OR_ERROR_NO_SOURCE_RESTART',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
