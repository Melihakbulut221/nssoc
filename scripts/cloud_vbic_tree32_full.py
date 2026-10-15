#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Full original32:1 frozen macro-RC tree using a measured paired runtime.

This is a full34ns component check, not whole-tree physical/four-lane signoff.
"""
import argparse,copy,hashlib,json,os,re,resource,shutil,subprocess,time
from pathlib import Path
import numpy as np
import cloud_vbic_tree32_backend as source
import cloud_tx_companion_replay as runtime
from cloud_tx_stream import streaming_deck,read_streamed_wave
from run_cloud_tx_mux4 import review,native_diagnostics
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-vbic-tree32-full'
def study_url(run):
    assert isinstance(run,int) and run>0
    return f'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-{run}-1-vbic-tree32-backend/vbic-tree32-backend-{run}-1.summary.json'

def main(backend,tmax,study_sha,study_run):
    assert os.environ.get('GITHUB_ACTIONS')=='true' and backend in ('sparse','klu') and tmax in (.5,.25)
    assert re.fullmatch(r'[0-9a-f]{64}',study_sha);OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],backend=backend,tmax_ps=tmax,
        scope='Exact original32:1 tree with per-macro extracted RC, ideal intermacro wires and imposed clocks. Full34ns, all original768sample/device/interface gates. Not whole-tree physical integration, independentPVT, PLL/CDR, x4PHY or mainchip timing acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        runtime.OUT=OUT;source.OUT=OUT;paths,provenance=runtime.restore_engines();result['runtime_provenance']=provenance
        gate=OUT/'backend-study.json';fetch(study_url(study_run),study_sha,gate);study=json.loads(gate.read_text())
        assert study['controller_sha256']==sha(Path(source.__file__)), 'Backend study controller differs'
        assert study['all_native_cases_complete'] and study['protected_inputs_unchanged'] and study['pristine_reproduces_packaged_to_1nv']
        if backend=='klu':
            assert study['backend_voltage_agreement_to_1nv'],'Matched native backend proof required before adopting KLU'
        else:
            # Preserve the original Sparse backend. A rejected KLU optimization
            # cannot prohibit measuring the unchanged backend's full waveform.
            # The cross-backend gate stays failed; no full engineering or
            # timestep-convergence gate is changed by this diagnostic dispatch.
            assert study['cases']['patched-sparse']['complete']
            for key in ('numeric','method'):
                assert study['cases']['patched-sparse']['native_options'][key]==study['cases']['pristine-sparse']['native_options'][key]
            result['backend_choice']=dict(original_sparse_retained=True,klu_adopted=False,
                cross_backend_guard_passed=study['backend_voltage_agreement_to_1nv'],
                cross_backend_worst_voltage_difference_v=study['patched_backend_comparison']['worst_voltage_difference_v'])
        for label in ('patched-sparse','patched-klu'):
            assert study['cases'][label]['executable_sha256']==sha(paths['patched']) and not study['cases'][label].get('error')
        result['backend_prerequisite']=dict(run=study_run,summary_sha256=study_sha,measured_speed_ratio=study['sparse_over_klu_elapsed_ratio'])
        original,contract,protected,receipt=source.restore_source(paths['packaged']);result.update(source_receipt=receipt,protected_inputs=protected)
        case=OUT/'native';case.mkdir();original_deck=(original/'native/bench.cir').read_text();deck=streaming_deck(original_deck,contract)
        rows=re.findall(r'(?m)^\.tran ([^\n]+)$',deck);assert len(rows)==1 and list(map(float,rows[0].split()))==[.5e-12,34e-9,0.,.5e-12]
        old='.tran '+rows[0];new=f'.tran 5e-13 3.4e-08 0 {tmax*1e-12:.14g}';changed=deck.replace(old,new);assert changed.replace(new,old)==deck
        if backend=='klu':
            assert '.options klu' not in changed;changed=changed.replace('.control\n','.options klu\n.control\n')
        assert changed.count('quit\n.endc')==1;changed=changed.replace('quit\n.endc','echo NSSOC_BACKEND_OPTIONS_BEGIN\noption\necho NSSOC_BACKEND_OPTIONS_END\nrusage > native-resources.txt\nquit\n.endc')
        (case/'bench.cir').write_text(changed);shutil.copyfile(original/'native/spinit',case/'spinit')
        contract=copy.deepcopy(contract);contract['condition']['step_ps']=tmax;(case/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
        env={k:v for k,v in os.environ.items() if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
        def limits():
            resource.setrlimit(resource.RLIMIT_AS,(12*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        save();started=time.monotonic()
        with (case/'run.log').open('w') as log:proc=subprocess.run([str(paths['patched']),'-n','-b','bench.cir'],cwd=case,env=env,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT,timeout=19800)
        result.update(elapsed_s=time.monotonic()-started,returncode=proc.returncode,executable_sha256=sha(paths['patched']))
        text=(case/'run.log').read_text(errors='replace')
        option,result['diagnostics'],option_block=source.backend_readback(text,backend)
        (case/'native-options.txt').write_text(option_block)
        assert proc.returncode==0 and not result['diagnostics'],'Native process/diagnostic failure'
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
        assert [a for a,b in flags]==['q.'+n+'.qnpn13g2' for n in contract['hbt']]
        assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',b)==['1'] for a,b in flags)
        option=source.options(case/'native-options.txt',backend);previous=study['cases']['patched-'+backend]['native_options']
        assert option['numeric']==previous['numeric'] and option['method']==previous['method'];result['native_options']=option
        result['review']=review(case,contract)
        assert all(sha(Path(p))==d for p,d in protected.items());result['protected_inputs_unchanged']=True
        result['component_screen_passed']=result['review']['all_engineering_gates_passed']
        result['status']='COMPLETE_FULL34NS_TREE32_COMPONENT_SCREEN_NOT_PHYSICAL_OR_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--backend',choices=['sparse','klu'],required=True);p.add_argument('--tmax-ps',type=float,choices=[.5,.25],required=True);p.add_argument('--study-sha256',required=True);p.add_argument('--study-run',type=int,required=True);a=p.parse_args();main(a.backend,a.tmax_ps,a.study_sha256,a.study_run)
