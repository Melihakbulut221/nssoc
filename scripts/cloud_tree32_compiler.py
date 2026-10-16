#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Paired strict-O3 performance experiment for the timed-out full tree capture.

Same Sparse solver, exact patched upstream, PDK, all vectors and original fine
step. A four-nanosecond comparison is not a full capture or PHY acceptance.
"""
import argparse,copy,hashlib,json,os,re,resource,shutil,subprocess,time
from pathlib import Path
import numpy as np
import cloud_vbic_tree32_backend as source
import cloud_tx_companion_replay as runtime
import cloud_vbic_companion as companion
from cloud_tx_step_factorial import wave_difference
from cloud_tx_stream import read_streamed_wave
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-tree32-compiler'
FLAGS='-O3 -fno-fast-math -ffp-contract=off -march=x86-64-v3 -mtune=generic'
STOP=4e-9;STEP=.25e-12
REFERENCE_SHA='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'

def fine_deck(original,contract):
    deck=source.make_deck(original,contract,STOP,'sparse')
    rows=re.findall(r'(?m)^\.tran ([^\n]+)$',deck)
    assert len(rows)==1 and list(map(float,rows[0].split()))==[.5e-12,STOP,0.,.5e-12]
    before='.tran '+rows[0];after='.tran 5e-13 4e-09 0 2.5e-13'
    changed=deck.replace(before,after);assert changed.replace(after,before)==deck
    return changed

def comparison_gate(comparison):
    difference=comparison['worst_voltage_difference_v']
    assert np.isfinite(difference) and difference>=0
    return difference<=1e-9

def controls():
    assert comparison_gate(dict(worst_voltage_difference_v=0.))
    assert comparison_gate(dict(worst_voltage_difference_v=1e-9))
    assert not comparison_gate(dict(worst_voltage_difference_v=2e-9))
    for value in (float('nan'),float('inf'),-1.):
        try:comparison_gate(dict(worst_voltage_difference_v=value))
        except AssertionError:pass
        else:raise AssertionError('Invalid comparison accepted')
    source.readback_controls()
    return dict(voltage_guard_v=1e-9,above_limit_rejected=True,nonfinite_and_negative_rejected=True,original_sparse_option_controls=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=True)
    assert not (OUT/'result.json').exists()
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],cases={},full_serial_phy_complete=False,final_timing_complete=False,
        scope='Paired4ns/0.25ps exact original32:1 macro-RC tree. Reference and strict-O3 engines share Sparse, source patch, input decks, models, all vectors and solver tolerances. Compiler/runtime experiment only; no full34ns, qualified intermacro extraction, PVT, PLL/CDR, x4PHY or mainchip acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        result['controls']=controls()
        build=json.loads((OUT/'build.json').read_text());result['build']=build
        assert build['upstream']==companion.UPSTREAM and build['flags']==FLAGS
        assert build['configure_options']==['--without-x','--with-readline=no','--disable-openmp']
        patch=json.loads((OUT/'patch.json').read_text())
        assert patch['original_sha256']==companion.SOURCE_SHA and patch['patched_sha256']=='aafdf5b06a6965c995a70321dc6edaab34ad1f0698dd42e8e15adca22088cb25'
        assert patch['one_expression_only'] and not patch['physical_model_parameters_changed']
        config=(OUT/'config.log').read_text();assert ("CFLAGS='"+FLAGS+"'") in config
        optimized=OUT/'build-runtime/optimized-ngspice';assert sha(optimized)==build['optimized_sha256']
        result['optimized_runtime_sha256']=sha(optimized)
        # Run the existing NPN/PNP zero/nonzero-charge invariant without changing
        # its equations, 1nA current criterion or original native decks.
        companion.OUT=OUT/'synthetic';companion.run_variant('patched',optimized.resolve())
        synthetic=json.loads((companion.OUT/'patched.json').read_text())
        assert all(r['complete'] and r['current_dc_invariance_1na'] and not r['diagnostics'] for r in synthetic['cases'].values())
        result['optimized_synthetic_controls']=synthetic;save()
        runtime.OUT=OUT;source.OUT=OUT;paths,provenance=runtime.restore_engines();result['runtime_provenance']=provenance
        assert sha(paths['patched'])==REFERENCE_SHA
        original,contract,protected,receipt=source.restore_source(paths['packaged'])
        result.update(source_receipt=receipt,protected_inputs=protected,native_vector_count=len(contract['vectors']),hbt_count=len(contract['hbt']),mos_count=len(contract['mos']))
        deck=fine_deck((original/'native/bench.cir').read_text(),contract)
        frozen_contract=copy.deepcopy(contract);frozen_contract['condition']['step_ps']=.25
        captures={};chosen_cpu=min(os.sched_getaffinity(0));result['cpu_affinity']=[chosen_cpu]
        result['cpu_info']=Path('/proc/cpuinfo').read_text();save()
        for name,exe in [('reference',paths['patched']),('strict_o3',optimized.resolve())]:
            case=OUT/name;case.mkdir();(case/'bench.cir').write_text(deck)
            shutil.copyfile(original/'native/spinit',case/'spinit')
            (case/'contract.json').write_text(json.dumps(frozen_contract,indent=2)+'\n')
            row=dict(complete=False,accepted=False,backend='sparse',stop_s=STOP,tstep_s=.5e-12,tmax_s=STEP,executable_sha256=sha(exe),deck_sha256=sha(case/'bench.cir'),spinit_sha256=sha(case/'spinit'));result['cases'][name]=row;save()
            env={k:v for k,v in os.environ.items() if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
            def limits():
                resource.setrlimit(resource.RLIMIT_AS,(12*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{chosen_cpu})
            started=time.monotonic();usage=resource.getrusage(resource.RUSAGE_CHILDREN)
            try:
                with (case/'run.log').open('w') as log:
                    proc=subprocess.run([str(exe),'-n','-b','bench.cir'],cwd=case,env=env,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT,timeout=8400)
                row['returncode']=proc.returncode
                text=(case/'run.log').read_text(errors='replace');row['native_options'],row['diagnostics'],option_block=source.backend_readback(text,'sparse')
                (case/'native-options.txt').write_text(option_block)
                assert proc.returncode==0 and not row['diagnostics'],'Native process or diagnostic failure'
                flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
                assert [a for a,b in flags]==['q.'+n+'.qnpn13g2' for n in contract['hbt']]
                assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',b)==['1'] for a,b in flags)
                op=np.loadtxt(case/'op.dat',skiprows=1);assert op.size==len(contract['vectors'])+1 and np.isfinite(op).all() and abs(op).max()<=1e-10
                t,v,capture=read_streamed_wave(case/'wave.raw',contract['vectors'],STOP,STEP)
                captures[name]=(t,v);row.update(complete=True,capture=capture)
            except BaseException as error:
                row['error']=repr(error);raise
            finally:
                current=resource.getrusage(resource.RUSAGE_CHILDREN)
                row.update(elapsed_s=time.monotonic()-started,cpu_user_s=current.ru_utime-usage.ru_utime,cpu_system_s=current.ru_stime-usage.ru_stime);save()
                print(json.dumps(dict(case=name,complete=row['complete'],elapsed_s=row['elapsed_s'],error=row.get('error'))),flush=True)
        a=result['cases']['reference'];b=result['cases']['strict_o3']
        assert a['deck_sha256']==b['deck_sha256'] and a['spinit_sha256']==b['spinit_sha256']
        for key in ('numeric','method'):assert a['native_options'][key]==b['native_options'][key]
        forward=wave_difference(captures['reference'],captures['strict_o3'],contract['vectors'],end=STOP)
        reverse=wave_difference(captures['strict_o3'],captures['reference'],contract['vectors'],end=STOP)
        result['comparison']=forward;result['reverse_comparison']=reverse
        result['same_native_time_grid']=bool(np.array_equal(captures['reference'][0],captures['strict_o3'][0]))
        result['voltage_agreement_to_1nv']=comparison_gate(forward) and comparison_gate(reverse)
        result['wall_speed_ratio']=a['elapsed_s']/b['elapsed_s']
        result['cpu_speed_ratio']=(a['cpu_user_s']+a['cpu_system_s'])/(b['cpu_user_s']+b['cpu_system_s'])
        result['runtime_candidate_for_full_fine_capture']=result['voltage_agreement_to_1nv'] and result['wall_speed_ratio']>1 and result['cpu_speed_ratio']>1
        assert all(sha(Path(p))==d for p,d in protected.items());result['protected_inputs_unchanged']=True
        assert sha(optimized)==build['optimized_sha256'] and sha(paths['patched'])==REFERENCE_SHA
        result['status']='COMPLETE_PAIRED_FINE_STEP_COMPILER_DIAGNOSIS_NOT_FULL_CAPTURE_OR_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls-only',action='store_true');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.controls_only:print(json.dumps(controls()))
    else:main()
