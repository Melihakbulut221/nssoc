#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound equation proof of the saved full-chip physical timing repairs."""
import json,os,subprocess,sys
from pathlib import Path
import cloud_corrpre_postcts_timing as source
ROOT=source.ROOT;OUT=ROOT/'cloud-corrpre-timing-logic';sha=source.sha

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);source.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,
        scope='Original CORRPRE/PCIe/system+EthernetMBIST CTS to saved electrical plus setup/hold repair. Full netlist retained equations/state and positive-buffer contraction with combinational clone checks. Excludes SRAM interiors, analog, initialization, CDC, timing and physical connectivity. Does not prove later RTL bank candidate.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def execute(command,label):
        with (OUT/(label+'.log')).open('w')as log:p=subprocess.run(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(command=list(map(str,command)),returncode=p.returncode));save()
        if p.returncode:print((OUT/(label+'.log')).read_text(errors='replace')[-6000:],flush=True)
        assert p.returncode==0,label+' failed; raw evidence preserved'
    save()
    try:
        before_root,br=source.restore(source.SPECS[0])
        spec=dict(run=39011120664,group='corrpre-postcts-timing',root='cloud-corrpre-postcts-timing',summary='4f6f1be972b01818f6690784a5d1f2800cedc2633df1f975a2e43e46da774a8e',archive='9eceb042ecc7f540f2802b3a73443e3b1fdc64139a82829e652eb407ccabce46',size=99485976)
        after_root,ar=source.restore(spec)
        assert br['source_head']=='8581b34b8524d3fc65ceb15c81c6f42fc37c5525'and br['sources_unchanged']
        assert ar['source_head']=='1d0caf4db137c3e290ef4c52a3230afed9cb4ab3'and ar['sources_unchanged']
        before_state=json.loads((before_root/'run/27-openroad-cts/state_out.json').read_text())
        after_state=json.loads((after_root/ar['repaired_state']).read_text())
        assert sha(before_state['odb'])=='25abfb1825f2ef8b04c373f925c432c8ad4f8bc79439352c94b2d04375932f3e'
        assert sha(after_state['odb'])=='94e4f21b7ee0018ef0cc9715ed40a2932e8ecda3d23434e770195c77029cd7a6'
        before=Path(before_state['nl']);after=Path(after_state['nl']);assert before.is_relative_to(before_root)and after.is_relative_to(after_root)
        assert sha(before)==br['outputs'][str(before.relative_to(before_root))]and sha(after)==ar['outputs'][str(after.relative_to(after_root))]
        execute([sys.executable,ROOT/'hw/soc/flow/prepare_ihp_native_boot.py'],'prepare-native-models')
        pdk=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2'
        liberty=pdk/'libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        assert sha(liberty)=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
        macros=[pdk/'libs.ref/sg13g2_sram/verilog'/n for n in ['RM_IHPSG13_1P_2048x64_c2_bm_bist.v','RM_IHPSG13_2P_256x16_c2_bm_bist.v']]
        checker=ROOT/'hw/soc/flow/check_eco_logic_clones.py'
        protected={str(p):sha(p)for p in [before,after,liberty,*macros,Path(__file__),checker,ROOT/'hw/soc/flow/eco_logic.py',ROOT/'hw/soc/flow/eco_logic_clones.py',ROOT/'sw/tests/eco_logic_native.py']}
        result.update(source_specs=[source.SPECS[0],spec],proof_inputs=protected,before_netlist_sha256=sha(before),after_netlist_sha256=sha(after));save()
        execute([sys.executable,ROOT/'sw/tests/eco_logic_native.py','--checker',checker,'--liberty',liberty,'--output',OUT/'controls'],'native-controls')
        controls=json.loads((OUT/'controls/result.json').read_text());assert controls['status']=='PASS_NATIVE_ECO_CONTROLS';result['controls']=controls;save()
        command=[sys.executable,checker,before,after,'--liberty',liberty,'--output',OUT/'proof']
        # IHP's timing-check syntax is unsupported by Yosys. Its upstream
        # FUNCTIONAL branch has the same ports; -lib still makes each macro
        # opaque. No native timing model or functional simulation is altered.
        command+=['--macro-verilog-define','FUNCTIONAL']
        for macro in macros:command+=['--macro-verilog',macro]
        execute(command,'full-netlist-proof')
        proof=json.loads((OUT/'proof/result.json').read_text());assert proof['status']=='PASS within scope'and proof['retained_cells']>10000 and proof['macro_verilog_defines']==['FUNCTIONAL']
        assert all(sha(p)==h for p,h in protected.items())
        result.update(status='PASS_SAVED_FULLCHIP_TIMING_ECO_EQUATIONS_NOT_TIMING_OR_PHYSICAL_SIGNOFF',proof=proof,sources_unchanged=True)
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
