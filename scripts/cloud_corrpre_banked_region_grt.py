#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound conservative Metal5 regional routing trial after native geometry diagnosis."""
import argparse,json,os,re,subprocess,time
from pathlib import Path
import cloud_corrpre_banked_logic as logic
import compare_cloud_routed_endpoints as reports
from cloud_corrpre_banked_handoff import api,wait_success
from cloud_corrpre_banked_postcts import require_candidate,relative,sha
from route_cloud_newer_postcts import native_ndr_screen
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-corrpre-banked-region-grt'
PLACE=ROOT/'hw/soc/out/cloud-corrpre-mbist-placement'
REPAIR=ROOT/'hw/soc/out/cloud-corrpre-banked-postcts'
PROOF_RUN=39031081958
PROOF_HEAD='f9eb01a2589c2aef9ee0c670c862b2dac36bb6f4'
PROOF_STATUS='PASS_NEW_BANKED_CTS_TO_REPAIR_LOGIC_NOT_ROUTE_OR_TIMING_SIGNOFF'

def proof_source(result,save,wait):
    run=wait_success(PROOF_RUN,'.github/workflows/corrpre-banked-logic-cloud.yml',
        time.monotonic()+(18000 if wait else 0),result,save)
    assert run['head_sha']==PROOF_HEAD and run['run_attempt']==1
    proof,digest,parts=logic.summary('corrpre-banked-logic',run)
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
        scope='Separate clock-layer routing experiment on exact proven banked PCIe packet interface/Ethernet mainchip: clockMetal4..TopMetal2; signalMetal2..TopMetal2,20percent capacity reserve,200iterations andallNDR/overflow gates retained. Original20/4/8/8ns clocks,5percent derate,20SRAM. Not serial PHY integration, detailed routing, extracted timing or signoff.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        proof,proof_sha,proof_parts=proof_source(r,save,args.wait)
        if args.wait:
            r['status']='EXACT_LOGIC_SOURCE_READY_FOR_SEPARATE_NATIVE_JOB';return
        original,proof_archive=reports.restore_report('corrpre-banked-logic',PROOF_RUN,
            proof_sha,proof_parts,OUT/'logic-proof',('proof/result.json','controls/result.json'))
        assert original==proof
        assert json.loads((OUT/'logic-proof/proof/result.json').read_text())==proof['proof']
        assert json.loads((OUT/'logic-proof/controls/result.json').read_text())==proof['controls']
        r['logic_archive']=proof_archive
        source_reports={}
        for label,group,run_id,head,destination in (
            ('placement','corrpre-banked-placement',logic.PLACEMENT_RUN,logic.PLACEMENT_HEAD,PLACE),
            ('repair','corrpre-banked-postcts',logic.REPAIR_RUN,logic.REPAIR_HEAD,REPAIR)):
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
        prior=api('actions/runs/39031588904')
        assert prior['status']=='completed' and prior['conclusion']=='failure' and prior['head_sha']=='d46ab620a9876b53e1c9667f34053d66f9c0929f'
        receipt=json.loads((ROOT/'docs/evidence/corrpre-banked-grt-congestion-20261017.json').read_text())
        blob=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/650591490','-H','Accept: application/octet-stream'])
        assert __import__('hashlib').sha256(blob).hexdigest()==receipt['summary_sha256']
        diagnosis=json.loads(blob);assert diagnosis==receipt['report']
        assert '[GRT-0116]' in diagnosis['flow_errors']['run/error.log']
        assert '[GRT-0273]' in diagnosis['flow_errors']['run/warning.log']
        assert cfg.get('RT_CLOCK_MIN_LAYER') is None and cfg.get('RT_CLOCK_MAX_LAYER') is None
        assert cfg['GRT_ADJUSTMENT']==0.2 and cfg.get('GRT_OVERFLOW_ITERS',50)==50
        clock_run=api('actions/runs/39038463008')
        assert clock_run['status']=='completed' and clock_run['conclusion']=='failure' and clock_run['head_sha']=='6eda7245dd9ad45f6a2e3a366e6914a98cf51ed8'
        clock_blob=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/650671065','-H','Accept: application/octet-stream'])
        assert __import__('hashlib').sha256(clock_blob).hexdigest()=='2cfabbea3c2948f31cc0f957a66db1829709d409ca059d1e4f490fd2382b7dd7'
        clock_prior=json.loads(clock_blob)
        assert clock_prior['native_ndr_screen']['preserved'] and clock_prior['native_clock_layer_selection_verified']
        assert any('[ERROR GRT-0116]' in line for line in clock_prior['native_route_tail'])
        totals=[line for line in clock_prior['native_route_tail'] if line.startswith('Total ')]
        assert len(totals)==1 and totals[0].split()[-1]=='328'
        r['clock50_failure_source']=dict(run=39038463008,summary_sha256=__import__('hashlib').sha256(clock_blob).hexdigest(),overflow=328,ndr_preserved=True)
        geometry_pin=json.loads((ROOT/'docs/evidence/corrpre-clock200-native-geometry-20261017.json').read_text())
        geometry_blob=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/650820859','-H','Accept: application/octet-stream'])
        assert __import__('hashlib').sha256(geometry_blob).hexdigest()==geometry_pin['summary_sha256']=='264493232e08272979c3649d74ac8942347f0458e669286d6814f27729fb8e7d'
        geo=json.loads(geometry_blob);assert geo==geometry_pin['report']
        assert geo['geometry']['odb_sha256']==sha(odb)and not geo['geometry']['unresolved_nets']
        regions=geo['geometry']['regions'];assert len(regions)==96 and sum(x['overflow']for x in regions)==142
        assert sum(x['overflow']for x in regions if x['bbox_um'][0]==3096.0)==53
        assert sum(x['overflow']for x in regions if x['bbox_um'][0]==2340.0)==29
        r['regional_reserve']=dict(source_geometry_run=39045205430,source_failed_route=39041556309,
            boxes_um=[[2325.6,1692.0,2368.8,2174.4],[3081.6,1692.0,3124.8,2174.4]],layer='Metal5',adjustment=0.5,
            scope='Two observed congestion columns plus two7.2um grid tiles each side, covering actual y-range plus14.4um halo. Additional positive regional reduction only; no capacity increase, NDR/clock relaxation or physical blockage deletion. Hypothesis: move long replay routes away from SRAM6/7 pin corridors. Must pass actual zero-overflow routing.')
        unchanged=dict(cfg)
        cfg.update(RT_CLOCK_MIN_LAYER='Metal4',RT_CLOCK_MAX_LAYER='TopMetal2',GRT_OVERFLOW_ITERS=200)
        assert {k:v for k,v in cfg.items() if k not in ('RT_CLOCK_MIN_LAYER','RT_CLOCK_MAX_LAYER','GRT_OVERFLOW_ITERS')}=={k:v for k,v in unchanged.items() if k not in ('RT_CLOCK_MIN_LAYER','RT_CLOCK_MAX_LAYER','GRT_OVERFLOW_ITERS')}
        r['route_experiment']=dict(source_failure_run=39038463008,diagnosis_run=39038196457,
            clock_layers=['Metal4','TopMetal2'],signal_layers=['Metal2','TopMetal2'],capacity_reserve=0.2,overflow_iterations=200,
            only_config_delta={k:dict(before=unchanged.get(k),after=cfg[k])for k in ('RT_CLOCK_MIN_LAYER','RT_CLOCK_MAX_LAYER','GRT_OVERFLOW_ITERS')},
            rationale='ClockMetal4 restores NDR and lowers overflow385to328 but50iterations exhaust. Increase only search iterations50to200 versus that failed trial, capture native congestion regions every25iterations. Same exact placement, clocks,capacity,NDR,zerooverflow gate; no DRT/STA acceptance.')
        r['route_experiment']['regional_reserve']=r['regional_reserve']
        r['route_experiment']['rationale']='Native ODB and142overflows identify two columns carrying82overflows. Add Metal5 regional50percent capacity reductions only versus clock200; original20percent global reserve, allsignal/clocklayers, NDR, zerooverflow, clocks andderate preserved.'
        cfg['TIME_DERATING_CONSTRAINT']=5.0
        trial=OUT/'trial-config.json';trial.write_text(json.dumps(cfg,indent=2)+'\n')
        r['discarded_inherited_metrics']=len(state['metrics']);state['metrics']={}
        initial=OUT/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        flow=ROOT/'hw/soc/pnr/corrpre_banked_region_grt_flow.py'
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
        r['native_regional_reserves_verified']=all(marker in observed for marker in ['NSSOC_REGION_RESERVE_APPLIED Metal5 2325.6 1692.0 2368.8 2174.4 0.5','NSSOC_REGION_RESERVE_APPLIED Metal5 3081.6 1692.0 3124.8 2174.4 0.5'])
        r['native_200_iterations_verified']='global_route -congestion_iterations 200' in observed
        r['native_congestion_reports']={str(p.relative_to(OUT)):sha(p)for p in (OUT/'run').rglob('*congestion*.rpt')if p.is_file()}
        r['native_report_options_verified']='NSSOC_CONGESTION_REPORT_EVERY_25_ITERATIONS' in observed
        r['native_clock_layer_selection_verified']='clock min routing layer to Metal4.' in observed and 'clock max routing layer to TopMetal2.' in observed
        save()
        if code:print('\n'.join(r['native_route_tail']),flush=True)
        assert code==0,'Native global route failed; every completed state retained'
        assert r['native_regional_reserves_verified'],'Native regional reserve commands not applied'
        assert r['native_clock_layer_selection_verified'],'Native clock layer selection not applied'
        assert r['native_200_iterations_verified']and r['native_report_options_verified'],'Native search/report options missing'
        states=list((OUT/'run').glob('*-openroad-globalrouting/state_out.json'));assert len(states)==1
        folder=states[0].parent
        logs=list(folder.glob('*.log'));assert logs
        text='\n'.join(p.read_text(errors='replace')for p in logs)
        ndr=native_ndr_screen(text);r['native_ndr_screen']=ndr;save()
        assert ndr['preserved'],'Native router relaxed NDR; route rejected'
        assert not re.search(r'(?m)^(Error:|\[ERROR)',text)
        counts=re.findall(r'\[INFO GRT-0014\] Routed nets: (\d+)',text)
        assert len(counts)==1 and int(counts[0])>0,'Missing native routed-net count'
        guide=folder/'after_grt.guide';assert guide.is_file()and guide.stat().st_size>0
        final=json.loads(states[0].read_text());db=Path(final['odb'])
        assert db.is_relative_to(OUT/'run')and db.is_file()
        assert all(sha(p)==digest for p,digest in protected.items())
        r.update(status='COMPLETE_NATIVE_BANKED_REGIONAL_GLOBAL_ROUTE_REQUIRES_DRT_EXTRACTED_STA_AND_SIGNOFF',
            sources_unchanged=True,global_route_state=str(states[0].relative_to(OUT)),
            global_route_odb_sha256=sha(db),guide_sha256=sha(guide),
            native_routed_nets=int(counts[0]),metrics=final['metrics'])
    except BaseException as error:
        r.update(status='FAIL_OR_ERROR_NO_SOURCE_RESTART',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
