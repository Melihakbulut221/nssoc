#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare an actual source-measured native sizing ECO; never claim timing from it."""
import json,os,re,shutil,subprocess,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
from select_onehot_routed_loads import select,controls
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-onehot-logic-resize-prepare'
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
        pin=json.loads((ROOT/'docs/evidence/onehot-resize-route-report-rejection-20261019.json').read_text())
        validated=json.loads((ROOT/'docs/evidence/onehot-resize-saved-validation-20261019.json').read_text())['report']
        assert validated['source']['run']==pin['run'] and validated['source']['summary_sha256']==pin['summary_sha256']
        assert validated['sources_unchanged'] and validated['physical']==dict(drc_errors=0,critical_disconnected_pins=0)
        names=['run/2-openroad-detailedrouting/soc_top.odb','run/2-openroad-detailedrouting/soc_top.nl.v','run/2-openroad-detailedrouting/state_out.json','trial-config.json']
        rel='run/6-nssoc-onehotroutedsta/nom_slow_1p08V_125C/max.rpt';names.append(rel)
        source,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',names)
        assert source==pin['report'] and source['returncode']==0 and source['status']=='FAIL_OR_ERROR_NO_SOURCE_RESTART'
        odb=OUT/'source'/names[0];netlist=OUT/'source'/names[1]
        assert sha(odb)=='4acbb9969285c715969619795ec7a45305de1bd4a3f6ac97a91139cf0024b723'
        assert sha(netlist)=='c05e6321a4aed063e5e69b902a3b7ed08863bd2a39189f8b17ded5bfc33b9756'
        cfg=json.loads((OUT/'source/trial-config.json').read_text())
        assert cfg['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']and cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5
        assert cfg['SETUP_VIOLATION_CORNERS']==cfg['HOLD_VIOLATION_CORNERS']==['*']
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        openroad=shutil.which('openroad');assert openroad
        helper=ROOT/'scripts/prepare_onehot_logic_resized_drivers.py'
        run([openroad,'-exit','-python',helper],'native-master-inventory','inventory')
        inventory=json.loads((OUT/'master-inventory.json').read_text())
        assert inventory['instances']==147858 and inventory['source_sha256']==sha(odb)
        candidates=select((OUT/'source'/rel).read_text());assert candidates
        targets=[];skipped=[]
        allowed={'sg13g2_buf','sg13g2_nand2','sg13g2_nand3','sg13g2_nand4','sg13g2_nor2','sg13g2_nor3','sg13g2_nor4','sg13g2_and2','sg13g2_or2','sg13g2_xor2','sg13g2_xnor2','sg13g2_a21oi','sg13g2_o21ai','sg13g2_a22oi','sg13g2_o22ai'}
        for x in candidates:
            family,strength=x['master'].rsplit('_',1)
            if family not in allowed:continue
            choices=[family+'_'+str(n)for n in ((16,8,4)if family=='sg13g2_buf'else(4,2))if n>int(strength)]
            choices=[n for n in choices if n in inventory['masters'] and inventory['masters'][n]['pins']==inventory['masters'][x['master']]['pins']]
            if not choices:skipped.append(dict(instance=x['instance'],master=x['master'],reason='No stronger same-pin native master'));continue
            x['new_master']=choices[0];targets.append(x)
            if len(targets)==32:break
        assert targets and any(t['master'].startswith('sg13g2_buf_') for t in targets)
        assert any(not t['master'].startswith('sg13g2_buf_') for t in targets)
        selection=dict(source_report_sha256=sha(OUT/'source'/rel),controls=controls(),eligible=len(candidates),targets=targets,scope='Existing selector: negative source-measured slow data paths, cap>=0.1pF delay>=1ns. Includes weak buffers and actual NAND/NOR/complex data gates. At most32 stronger same-pin native combinational masters on actual slow violating data paths; clock/state/macro untouched. Not timing acceptance.')
        (OUT/'targets.json').write_text(json.dumps(selection,indent=2)+'\n');r.update(source=proof,selection=selection,original_route=dict(odb_sha256=sha(odb),netlist_sha256=sha(netlist)),original_measurements=validated['corners'],unavailable_stronger_masters=skipped);save()
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');helper=ROOT/'scripts/prepare_onehot_logic_resized_drivers.py'
        # Already inside the verified AppImage environment; do not nest FUSE mounts.
        openroad=shutil.which('openroad');assert openroad, 'Pinned runtime did not expose OpenROAD'
        r['native_openroad']=dict(path=openroad,sha256=sha(Path(openroad)));save()
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
        text=(OUT/'candidate.v').read_text();t=next(x for x in targets if x['master'].startswith('sg13g2_buf_'))
        pattern=re.escape(t['new_master'])+r'\s+(?:\\)?'+re.escape(t['instance'])+r'\s*\((.*?)\);';match=re.search(pattern,text,re.S);assert match
        bad=text[:match.start()]+'sg13g2_inv_1 '+('\\'if t['instance'].startswith('$')else'')+t['instance']+' ('+re.sub(r'\.X\s*\(','.Y(',match[1])+');'+text[match.end():]
        (OUT/'inverted.v').write_text(bad);negative=list(cmd);negative[negative.index(OUT/'candidate.v')]=OUT/'inverted.v';negative[negative.index(OUT/'proof')]=OUT/'negative-proof'
        code=run(negative,'actual-resized-driver-inversion-control',success=False);assert code!=0;r['inversion_control']=dict(rejected=True,returncode=code)
        state=json.loads((OUT/'source'/names[2]).read_text());state.update(odb=str(OUT/'candidate.odb'),nl=str(OUT/'candidate.v'),spef=None,def_=None,metrics={});state.pop('def_',None);state['def']=None
        (OUT/'candidate-state.json').write_text(json.dumps(state,indent=2)+'\n')
        (OUT/'trial-config.json').write_text(json.dumps(cfg,indent=2)+'\n')
        assert all(sha(Path(p))==d for p,d in protected.items())
        r.update(status='PASS_NATIVE_MEASURED_LOGIC_RESIZING_REQUIRES_ROUTE_RC_ALL_CORNER_STA',sources_unchanged=True,candidate_odb_sha256=sha(OUT/'candidate.odb'),candidate_netlist_sha256=sha(OUT/'candidate.v'),candidate_state='candidate-state.json',protected_inputs=protected,dependencies_require_original_provenance_restore=True)
    except BaseException as e:r.update(status='FAIL_RESIZE_PREPARATION',error=repr(e));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
