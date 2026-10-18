#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Continue exact completed50-buffer geometry with pinned Yosys, never regenerate it."""
import json,os,re,shutil,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-onehot-load-logic'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and shutil.which('yosys')
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,detailed_route_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label,expect=True):
        with(OUT/(label+'.log')).open('w')as log:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        text=(OUT/(label+'.log')).read_text(errors='replace');r.setdefault('commands',[]).append(dict(label=label,returncode=code));save()
        if code:print(text[-14000:],flush=True)
        if expect:assert code==0,(label,code)
        return code,text
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/onehot-load-prepare-logic-runtime-rejection-20261018.json').read_text())
        selected=['candidate.odb','candidate.v','geometry-proof.json','targets.json','trial-config.json','initial-state.json','controls/buffered_macro.log','preparation.json']
        prior,proof=reports.restore_report('onehot-load-prepare',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'prepared',selected)
        assert prior['source_head']==pin['source_head']and prior['outputs']==pin['outputs']
        assert {k:prior[k]for k in pin['report_excerpt']}==pin['report_excerpt']
        geometry=json.loads((OUT/'prepared/geometry-proof.json').read_text());assert geometry==prior['geometry']and len(geometry['added'])==50 and geometry['original_instances']==145038
        failure=(OUT/'prepared/controls/buffered_macro.log').read_text();r['prior_native_control_failure']=failure
        assert 'IsADirectoryError'in failure or 'yosys'in failure
        r['preparation_source']=proof;r['geometry']=geometry
        rp=json.loads((ROOT/'docs/evidence/replay-onehot-antenna-round4-result-20261018.json').read_text());name='run/1-openroad-detailedrouting/soc_top.nl.v'
        route,route_proof=reports.restore_report('replay-onehot-antenna-round4',rp['run'],rp['summary_sha256'],rp['parts_sha256'],OUT/'original',[name])
        assert route['sources_unchanged']and route['antenna_closure_proven']and route['native_routing_drc_errors']==0
        before=OUT/'original'/name;after=OUT/'prepared/candidate.v'
        assert sha(before)=='f7bb33ce5ea9c1f947ea582151e2086b4b031f284ee50ba667c4c291f3ee0846'
        r['original_route_source']=route_proof
        run([os.sys.executable,ROOT/'hw/soc/flow/prepare_ihp_native_boot.py'],'native-models')
        pdk=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2';liberty=pdk/'libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        assert sha(liberty)=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
        checker=ROOT/'hw/soc/flow/check_eco_logic_clones.py'
        run([os.sys.executable,ROOT/'sw/tests/eco_logic_native.py','--checker',checker,'--liberty',liberty,'--output',OUT/'controls'],'native-logic-controls')
        r['controls']=json.loads((OUT/'controls/result.json').read_text());assert r['controls']['status']=='PASS_NATIVE_ECO_CONTROLS'
        cmd=[os.sys.executable,checker,before,after,'--liberty',liberty,'--output',OUT/'proof','--macro-verilog-define','FUNCTIONAL']
        for n in ('RM_IHPSG13_1P_2048x64_c2_bm_bist.v','RM_IHPSG13_2P_256x16_c2_bm_bist.v'):cmd+=['--macro-verilog',pdk/'libs.ref/sg13g2_sram/verilog'/n]
        run(cmd,'actual-native50-buffer-equation-proof');r['proof']=json.loads((OUT/'proof/result.json').read_text());assert r['proof']['status']=='PASS within scope';save()
        text=after.read_text();m=re.search(r'sg13g2_buf_16\s+nssoc_onehot_load_buffer_0\s*\((.*?)\);',text,re.S);assert m
        bad=text[:m.start()]+'sg13g2_inv_1 nssoc_onehot_load_buffer_0 ('+re.sub(r'\.X\s*\(','.Y(',m[1])+');'+text[m.end():]
        (OUT/'inverted.v').write_text(bad);negative=cmd.copy();negative[negative.index(after)]=OUT/'inverted.v';negative[negative.index(OUT/'proof')]=OUT/'negative-proof'
        code,log=run(negative,'actual-inversion-control',False)
        assert code!=0 and 'ValueError'in log and (OUT/'negative-proof/before.json').is_file()and(OUT/'negative-proof/after.json').is_file()
        r['inversion_control']=dict(rejected=True,returncode=code,log_tail=log[-5000:])
        state=json.loads((OUT/'prepared/initial-state.json').read_text());state.update(odb=str(OUT/'prepared/candidate.odb'),nl=str(after),spef=None,**{'def':None,'metrics':{}})
        (OUT/'candidate-state.json').write_text(json.dumps(state,indent=2)+'\n')
        assert all(sha(OUT/'prepared'/n)==prior['outputs'][n]for n in selected)and sha(before)==route['outputs'][name]
        r.update(status='PASS_SAVED50_NATIVE_GEOMETRY_AND_LOGIC_REQUIRES_ROUTING_AND_EXTRACTED_STA',sources_unchanged=True,candidate_odb_sha256=sha(OUT/'prepared/candidate.odb'),candidate_netlist_sha256=sha(after),candidate_state='candidate-state.json')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
