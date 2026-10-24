#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove the exact NEW banked CTS-to-repair logic after its live run completes."""
import json,os,subprocess,sys,time
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from cloud_corrpre_banked_handoff import api,get_asset,wait_success
from cloud_replay_crc_postcts import require_candidate,require_same_proofs,relative,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-replay-crc-logic'
REPAIR_RUN=39052168254
REPAIR_HEAD='2f32b51eec3d0dfc0c5d695c1aec921044e6a90b'
PLACEMENT_RUN=39042752404
PLACEMENT_HEAD='a39447804f23c1cb7d0bdd4d6fb49f5ceac01c9f'
REPAIR_STATUS='COMPLETE_NATIVE_BANKED_POSTCTS_REQUIRES_EQUIVALENCE_ROUTING_EXTRACTED_STA'

def summary(group,run):
    assert run['run_attempt']==1,'Unexpected retry requires independent review'
    stem=f"{group}-{run['id']}-1"
    release=api(f"releases/tags/cloud-results-{run['id']}-1-{group}")
    values=[]
    for suffix in ('.summary.json','.parts.json'):
        matches=[a for a in release['assets']if a['name']==stem+suffix]
        assert len(matches)==1
        raw,digest=get_asset(matches[0]);(OUT/(stem+suffix)).write_bytes(raw)
        values.append((json.loads(raw),digest))
    report,report_sha=values[0];parts,parts_sha=values[1]
    assert parts['stem']==stem and parts['format']=='ordered-tar-gzip-parts-v1'
    return report,report_sha,parts_sha

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='WAITING_FOR_EXACT_BANKED_REPAIR',source_head=os.environ['GITHUB_SHA'],
        accepted=False,full_phy_accepted=False,final_timing_complete=False,
        scope='NEW banked mainchip CTS to its exact electrical/setup/hold repair only. Full retained cell equations/state, positive buffer contraction and combinational clone proof. SRAM interiors, analog, initialization, CDC, delay and physical connectivity excluded. No previous CRC/banked proof reused. The repaired replay-residue candidate must prove its own exact retained equations.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def execute(cmd,label):
        cmd=list(map(str,cmd))
        with(OUT/(label+'.log')).open('w')as log:
            proc=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(command=cmd,returncode=proc.returncode));save()
        if proc.returncode:print((OUT/(label+'.log')).read_text(errors='replace')[-6000:],flush=True)
        assert proc.returncode==0,label+' failed; original evidence retained'
    save()
    try:
        run=wait_success(REPAIR_RUN,'.github/workflows/replay-crc-postcts-cloud.yml',time.monotonic()+18000,r,save)
        assert run['head_sha']==REPAIR_HEAD and run['event']=='push'
        after,after_sha,after_parts=summary('replay-crc-postcts',run)
        assert after['status']==REPAIR_STATUS and after['source_head']==REPAIR_HEAD
        assert after['returncode']==0 and after['sources_unchanged'] is True
        parent=after['placement_source']
        assert parent['run']==PLACEMENT_RUN and parent['head']==PLACEMENT_HEAD
        place=api('actions/runs/'+str(PLACEMENT_RUN))
        assert place['status']=='completed'and place['conclusion']=='success'
        assert place['head_sha']==PLACEMENT_HEAD and place['path']=='.github/workflows/replay-crc-placement-cloud.yml'
        before,before_sha,before_parts=summary('replay-crc-placement',place)
        assert parent['summary_sha256']==before_sha and parent['parts_sha256']==before_parts
        spec=require_candidate(before,PLACEMENT_HEAD)
        assert spec==parent['boot_spec']
        verified=OUT/'verified-boot-source.json'
        execute([sys.executable,ROOT/'scripts/check_pcie_residue_banked_boot_source.py',
            '--boot-run',spec['run'],'--boot-head',spec['head'],'--artifact',spec['artifact'],
            '--zip-sha256',spec['zip_sha256'],'--protocol-run',spec['protocol_run'],
            '--out',verified],'verify-six-proofs-protocol-native-boot')
        current_spec=json.loads(verified.read_text())
        require_same_proofs(spec,current_spec)
        require_same_proofs(spec,after['current_boot_source_revalidation'])
        r['current_boot_source_revalidation']=current_spec
        netlists=[];receipts=[]
        for label,group,number,report,digest,parts,state_key,source_root,odb_digest in (
            ('before','replay-crc-placement',PLACEMENT_RUN,before,before_sha,before_parts,
             'cts_state',ROOT/'hw/soc/out/cloud-corrpre-mbist-placement',before['cts_odb_sha256']),
            ('after','replay-crc-postcts',REPAIR_RUN,after,after_sha,after_parts,
             'repaired_state',ROOT/'hw/soc/out/cloud-replay-crc-postcts',after['repaired_odb_sha256'])):
            state_name=str(relative(report[state_key]))
            selection=[state_name]+[n for n in report['outputs']if n.endswith('.v')]
            assert len(selection)>1 and len(selection)==len(set(selection))
            destination=OUT/label
            restored,proof=reports.restore_report(group,number,digest,parts,destination,selection)
            assert restored==report
            state=json.loads((destination/state_name).read_text())
            original_nl=Path(state['nl']);original_odb=Path(state['odb'])
            assert original_nl.is_relative_to(source_root)and original_odb.is_relative_to(source_root)
            nl_name=str(original_nl.relative_to(source_root));odb_name=str(original_odb.relative_to(source_root))
            assert report['outputs'][odb_name]==odb_digest
            netlist=destination/relative(nl_name)
            assert sha(netlist)==report['outputs'][nl_name]
            netlists.append(netlist);receipts.append(dict(archive=proof,netlist=nl_name,
                netlist_sha256=sha(netlist),native_odb_sha256=odb_digest))
        r.update(status='PROVING_ACTUAL_BANKED_REPAIR_LOGIC',sources=receipts,boot_spec=spec);save()
        execute([sys.executable,ROOT/'hw/soc/flow/prepare_ihp_native_boot.py'],'prepare-native-models')
        pdk=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2'
        liberty=pdk/'libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        assert sha(liberty)=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
        macros=[pdk/'libs.ref/sg13g2_sram/verilog'/n for n in
            ['RM_IHPSG13_1P_2048x64_c2_bm_bist.v','RM_IHPSG13_2P_256x16_c2_bm_bist.v']]
        checker=ROOT/'hw/soc/flow/check_eco_logic_clones.py'
        protected={str(p):sha(p)for p in [*netlists,liberty,*macros,Path(__file__),checker,
            ROOT/'hw/soc/flow/eco_logic.py',ROOT/'hw/soc/flow/eco_logic_clones.py',ROOT/'sw/tests/eco_logic_native.py',ROOT/'scripts/cloud_replay_crc_postcts.py',
            ROOT/'scripts/check_pcie_residue_banked_boot_source.py']}
        r['proof_inputs']=protected;save()
        execute([sys.executable,ROOT/'sw/tests/eco_logic_native.py','--checker',checker,
            '--liberty',liberty,'--output',OUT/'controls'],'native-controls')
        controls=json.loads((OUT/'controls/result.json').read_text())
        assert controls['status']=='PASS_NATIVE_ECO_CONTROLS';r['controls']=controls;save()
        cmd=[sys.executable,checker,*netlists,'--liberty',liberty,'--output',OUT/'proof',
            '--macro-verilog-define','FUNCTIONAL']
        for macro in macros:cmd+=['--macro-verilog',macro]
        execute(cmd,'actual-banked-netlist-proof')
        proof=json.loads((OUT/'proof/result.json').read_text())
        assert proof['status']=='PASS within scope'and proof['retained_cells']>10000
        assert proof['macro_verilog_defines']==['FUNCTIONAL']
        assert all(sha(p)==digest for p,digest in protected.items())
        r.update(status='PASS_NEW_BANKED_CTS_TO_REPAIR_LOGIC_NOT_ROUTE_OR_TIMING_SIGNOFF',
            proof=proof,sources_unchanged=True)
    except BaseException as error:
        r.update(status='FAIL_OR_ERROR_NO_SOURCE_RESTART',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
