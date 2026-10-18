#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare an actual source-measured native sizing ECO; never claim timing from it."""
import json,os,re,shutil,subprocess,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
from select_onehot_routed_loads import select,controls
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-onehot-resize-prepare'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,final_timing_complete=False,detailed_route_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label,mode=None,success=True):
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        if mode:env['NSSOC_RESIZE_MODE']=mode
        with(OUT/(label+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code));save()
        if code:print((OUT/(label+'.log')).read_text()[-10000:],flush=True)
        if success:assert code==0,(label,code)
        return code
    try:
        pin=json.loads((ROOT/'docs/evidence/onehot-load-resume-route-result-20261018.json').read_text())
        names=['run/1-openroad-detailedrouting/soc_top.odb','run/1-openroad-detailedrouting/soc_top.nl.v','run/1-openroad-detailedrouting/state_out.json','trial-config.json']
        rel='run/5-nssoc-onehotroutedsta/nom_slow_1p08V_125C/max.rpt';names.append(rel)
        source,proof=reports.restore_report('onehot-load-resume',pin['run_id'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',names)
        assert source['source_head']==pin['source_head']and source['status']==pin['observed']['status']and source['sources_unchanged']
        assert source['detailed_route_complete']and source['native_routing_drc_errors']==0 and source['critical_disconnected_pins']==0
        odb=OUT/'source'/names[0];netlist=OUT/'source'/names[1]
        assert sha(odb)==source['routed_odb_sha256']and sha(netlist)==source['routed_netlist_sha256']
        cfg=json.loads((OUT/'source/trial-config.json').read_text())
        assert cfg['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']and cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5
        assert cfg['SETUP_VIOLATION_CORNERS']==cfg['HOLD_VIOLATION_CORNERS']==['*']
        candidates=[x for x in select((OUT/'source'/rel).read_text())if x['master']in ('sg13g2_buf_1','sg13g2_buf_2')]
        assert candidates
        targets=candidates[:50]
        for x in targets:x['new_master']='sg13g2_buf_16'if max(o['cap_pf']for o in x['observations'])>=.25 else'sg13g2_buf_8'
        selection=dict(source_report_sha256=sha(OUT/'source'/rel),controls=controls(),eligible=len(candidates),targets=targets,scope='Existing selector: negative source-measured slow data paths, cap>=0.1pF delay>=1ns. Positive buf1/buf2 only. At most50; no clock/logic/state/macro changes. Not exhaustive closure.')
        (OUT/'targets.json').write_text(json.dumps(selection,indent=2)+'\n');r.update(source=proof,selection=selection,original_route=dict(odb_sha256=sha(odb),netlist_sha256=sha(netlist)),original_measurements=source['measurements']);save()
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');helper=ROOT/'scripts/prepare_onehot_resized_drivers.py'
        # Already inside the verified AppImage environment; do not nest FUSE mounts.
        openroad=shutil.which('openroad');assert openroad, 'Pinned runtime did not expose OpenROAD'
        r['native_openroad']=dict(path=openroad,sha256=sha(openroad));save()
        protected={str(p):sha(p)for p in [Path(__file__),helper,ROOT/'scripts/select_onehot_routed_loads.py',*[OUT/'source'/n for n in names],OUT/'targets.json']}
        run([openroad,'-exit','-python',helper],'native-resize')
        tcl=OUT/'legalize.tcl';tcl.write_text('read_db {'+str(OUT/'proposed.odb')+'}\nset_thread_count 2\ndetailed_placement -max_displacement {1000 200}\ncheck_placement -verbose\nwrite_db {'+str(OUT/'legalized.odb')+'}\n')
        run([openroad,'-exit',tcl],'legalize-resized-drivers')
        run([openroad,'-exit','-python',helper],'native-geometry-proof','audit')
        r['geometry']=json.loads((OUT/'geometry-proof.json').read_text());assert len(r['geometry']['changes'])==len(targets)
        tcl=OUT/'export.tcl';tcl.write_text('read_db {'+str(OUT/'candidate.odb')+'}\nwrite_verilog {'+str(OUT/'candidate.v')+'}\n')
        run([openroad,'-exit',tcl],'export-resized-netlist')
        run([sys.executable,ROOT/'hw/soc/flow/prepare_ihp_native_boot.py'],'native-models')
        pdk=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2';lib=pdk/'libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        assert sha(lib)=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
        checker=ROOT/'hw/soc/flow/check_eco_logic_clones.py'
        run([sys.executable,ROOT/'sw/tests/eco_logic_native.py','--checker',checker,'--liberty',lib,'--output',OUT/'controls'],'logic-controls')
        r['controls']=json.loads((OUT/'controls/result.json').read_text());assert r['controls']['status']=='PASS_NATIVE_ECO_CONTROLS'
        cmd=[sys.executable,checker,netlist,OUT/'candidate.v','--liberty',lib,'--output',OUT/'proof','--macro-verilog-define','FUNCTIONAL']
        for name in ('RM_IHPSG13_1P_2048x64_c2_bm_bist.v','RM_IHPSG13_2P_256x16_c2_bm_bist.v'):cmd+=['--macro-verilog',pdk/'libs.ref/sg13g2_sram/verilog'/name]
        run(cmd,'native-equation-proof');r['proof']=json.loads((OUT/'proof/result.json').read_text());assert r['proof']['status']=='PASS within scope'
        text=(OUT/'candidate.v').read_text();t=targets[0]
        pattern=re.escape(t['new_master'])+r'\s+(?:\\)?'+re.escape(t['instance'])+r'\s*\((.*?)\);';match=re.search(pattern,text,re.S);assert match
        bad=text[:match.start()]+'sg13g2_inv_1 '+('\\'if t['instance'].startswith('$')else'')+t['instance']+' ('+re.sub(r'\.X\s*\(','.Y(',match[1])+');'+text[match.end():]
        (OUT/'inverted.v').write_text(bad);negative=list(cmd);negative[negative.index(OUT/'candidate.v')]=OUT/'inverted.v';negative[negative.index(OUT/'proof')]=OUT/'negative-proof'
        code=run(negative,'actual-resized-driver-inversion-control',success=False);assert code!=0;r['inversion_control']=dict(rejected=True,returncode=code)
        state=json.loads((OUT/'source'/names[2]).read_text());state.update(odb=str(OUT/'candidate.odb'),nl=str(OUT/'candidate.v'),spef=None,def_=None,metrics={});state.pop('def_',None);state['def']=None
        (OUT/'candidate-state.json').write_text(json.dumps(state,indent=2)+'\n')
        (OUT/'trial-config.json').write_text(json.dumps(cfg,indent=2)+'\n')
        assert all(sha(p)==d for p,d in protected.items())
        r.update(status='PASS_NATIVE_MEASURED_BUFFER_RESIZING_REQUIRES_ROUTE_RC_ALL_CORNER_STA',sources_unchanged=True,candidate_odb_sha256=sha(OUT/'candidate.odb'),candidate_netlist_sha256=sha(OUT/'candidate.v'),candidate_state='candidate-state.json',protected_inputs=protected,dependencies_require_original_provenance_restore=True)
    except BaseException as e:r.update(status='FAIL_RESIZE_PREPARATION',error=repr(e));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
