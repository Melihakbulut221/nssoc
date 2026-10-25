#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare physically nearby positive buffers from exact all-corner routed measurements."""
import json,os,re,shutil,subprocess,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-routed-drive-prepare'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,final_timing_complete=False,detailed_route_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label,mode=None,success=True):
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        if mode:env['NSSOC_CRITICAL_ECO_MODE']=mode
        with(OUT/(label+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code));save()
        if code:print((OUT/(label+'.log')).read_text()[-12000:],flush=True)
        if success:assert code==0,(label,code)
        return code
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/onehot-logic-resize-route-result-20261019.json').read_text())
        gp=json.loads((ROOT/'docs/evidence/onehot-routed-load-geometry-pass-20261019.json').read_text())
        assert pin['run']==39202263552 and gp['run']==39241091888
        diag=gp['report'];assert diag['status']=='COMPLETE_READ_ONLY_ROUTED_LOAD_GEOMETRY_NOT_REPAIR'and diag['sources_unchanged']
        assert diag['source']['run']==pin['run']and diag['source']['summary_sha256']==pin['summary_sha256']
        assert diag['geometry']['source_instance_count']==148832 and all(diag['geometry']['controls'].values())
        assert pin['report']['routed_candidate_topology']['proof']['retained_instances']==147858
        assert pin['report']['routed_candidate_topology']['proof']['added_diode_count']==974
        geometry,geometry_proof=reports.restore_report(gp['group'],gp['run'],gp['summary_sha256'],gp['parts_sha256'],OUT/'measurement',['geometry.json','targets.json'])
        assert geometry==diag
        assert json.loads((OUT/'measurement/geometry.json').read_text())==diag['geometry']
        targets=[]
        for row in diag['geometry']['rows']:
            assert row['ndr']is None and not row['ports']
            assert len(row['sinks'])==row['selection']['reported_fanout']
            assert all(s['direction']=='INPUT'for s in row['sinks'])
            assert row['routed_wire_total_um']>0
            targets.append(row['selection'])
        assert len(targets)==39
        selection=dict(targets=targets,source_geometry_summary_sha256=gp['summary_sha256'],scope='All39 actual source-measured weak data drivers from three-corner routed geometry diagnosis. Add positive buf16 near driver; never touch clock/state/macro logic or change constraints. All original148832cells including974new route diodes retained.')
        (OUT/'targets.json').write_text(json.dumps(selection,indent=2)+'\n')
        names=['run/2-openroad-detailedrouting/soc_top.odb','run/2-openroad-detailedrouting/soc_top.nl.v','run/2-openroad-detailedrouting/state_out.json','trial-config.json']
        source,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',names)
        assert source==pin['report']and source['sources_unchanged']and source['returncode']==0
        assert source['detailed_route_complete']and source['native_routing_drc_errors']==0 and source['critical_disconnected_pins']==0
        odb=OUT/'source'/names[0];netlist=OUT/'source'/names[1]
        assert sha(odb)=='1f6f3a87a157e8829d4248faef249907712d8ec1d33b87ee01271fc3a8be4236'
        assert sha(odb)==source['routed_odb_sha256']and sha(netlist)==source['routed_netlist_sha256']
        cfg=json.loads((OUT/'source/trial-config.json').read_text())
        assert cfg['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']and cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5
        assert cfg['SETUP_VIOLATION_CORNERS']==cfg['HOLD_VIOLATION_CORNERS']==['*']
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        openroad=shutil.which('openroad');assert openroad
        helper=ROOT/'scripts/prepare_onehot_routed_drive_buffers.py'
        protected={str(p):sha(p)for p in [Path(__file__),helper,OUT/'targets.json',*[OUT/'source'/n for n in names],OUT/'measurement/geometry.json',OUT/'measurement/targets.json']}
        r.update(source=proof,measurement_source=geometry_proof,selection=selection,original_route=dict(odb_sha256=sha(odb),netlist_sha256=sha(netlist)),original_measurements=source['measurements'],native_openroad=dict(path=openroad,sha256=sha(Path(openroad))));save()
        run([openroad,'-exit','-python',helper],'native-near-driver-buffers')
        tcl=OUT/'legalize.tcl';tcl.write_text('read_db {'+str(OUT/'proposed.odb')+'}\nset_thread_count 2\ndetailed_placement -max_displacement {50 20}\ncheck_placement -verbose\nwrite_db {'+str(OUT/'legalized.odb')+'}\n')
        run([openroad,'-exit',tcl],'legalize-near-driver-buffers')
        run([openroad,'-exit','-python',helper],'native-buffer-geometry-proof','audit')
        r['geometry']=json.loads((OUT/'geometry-proof.json').read_text());assert len(r['geometry']['added'])==39 and r['geometry']['original_instances']==148832
        tcl=OUT/'export.tcl';tcl.write_text('read_db {'+str(OUT/'candidate.odb')+'}\nwrite_verilog {'+str(OUT/'candidate.v')+'}\n')
        run([openroad,'-exit',tcl],'export-buffered-netlist')
        run([sys.executable,ROOT/'hw/soc/flow/prepare_ihp_native_boot.py'],'native-models')
        pdk=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2';lib=pdk/'libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        assert sha(lib)=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
        checker=ROOT/'hw/soc/flow/check_eco_logic_clones.py'
        run([sys.executable,ROOT/'sw/tests/eco_logic_native.py','--checker',checker,'--liberty',lib,'--output',OUT/'controls'],'logic-controls')
        r['controls']=json.loads((OUT/'controls/result.json').read_text());assert r['controls']['status']=='PASS_NATIVE_ECO_CONTROLS'
        cmd=[sys.executable,checker,netlist,OUT/'candidate.v','--liberty',lib,'--output',OUT/'proof','--macro-verilog-define','FUNCTIONAL']
        for name in ('RM_IHPSG13_1P_2048x64_c2_bm_bist.v','RM_IHPSG13_2P_256x16_c2_bm_bist.v'):cmd+=['--macro-verilog',pdk/'libs.ref/sg13g2_sram/verilog'/name]
        run(cmd,'native-equation-proof');r['proof']=json.loads((OUT/'proof/result.json').read_text());assert r['proof']['status']=='PASS within scope'
        text=(OUT/'candidate.v').read_text();name='nssoc_routed_drive_buffer_0'
        pattern=r'sg13g2_buf_16\s+'+name+r'\s*\((.*?)\);';match=re.search(pattern,text,re.S);assert match
        bad=text[:match.start()]+'sg13g2_inv_1 '+name+' ('+re.sub(r'\.X\s*\(','.Y(',match[1])+');'+text[match.end():]
        (OUT/'inverted.v').write_text(bad)
        negative=list(cmd);negative[negative.index(OUT/'candidate.v')]=OUT/'inverted.v';negative[negative.index(OUT/'proof')]=OUT/'negative-proof'
        code=run(negative,'actual-new-buffer-inversion-control',success=False);assert code!=0
        r['inversion_control']=dict(rejected=True,returncode=code)
        state=json.loads((OUT/'source'/names[2]).read_text());state.update(odb=str(OUT/'candidate.odb'),nl=str(OUT/'candidate.v'),spef=None,metrics={});state['def']=None
        (OUT/'candidate-state.json').write_text(json.dumps(state,indent=2)+'\n')
        (OUT/'trial-config.json').write_text(json.dumps(cfg,indent=2)+'\n')
        assert all(sha(Path(p))==d for p,d in protected.items())
        r.update(status='PASS_NATIVE_NEAR_DRIVER_BUFFER_PREPARATION_REQUIRES_ROUTE_RC_ALL_CORNERS',sources_unchanged=True,candidate_odb_sha256=sha(OUT/'candidate.odb'),candidate_netlist_sha256=sha(OUT/'candidate.v'),candidate_state='candidate-state.json',protected_inputs=protected,dependencies_require_original_provenance_restore=True)
    except BaseException as e:r.update(status='FAIL_NEAR_DRIVER_BUFFER_PREPARATION',error=repr(e));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
