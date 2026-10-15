#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hosted source-bound TSTEP/TMAX factorial startup diagnosis, never acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import tarfile
import time
import numpy as np
from run_cloud_tx_operating_point import fetch, sha
from cloud_tx_stream import read_streamed_wave
from run_cloud_tx_mux4 import verify_solver_options, native_diagnostics

ROOT = Path(__file__).resolve().parents[1]
STOP = 1.2e-9
SOURCE_STOP = 34e-9
PROFILE = 'breakpoint_tight_trap'
STEPS = (.125e-12, .0625e-12)

def replace_analysis(deck, tstep, tmax, method="trap"):
    assert tstep in STEPS and tmax in (*STEPS, .03125e-12, .015625e-12)
    assert method in ("trap", "gear")
    rows = re.findall(r'(?m)^\.tran ([^\n]+)$', deck)
    assert len(rows) == 1 and not re.search(r'(?m)^tran ', deck)
    fields = rows[0].split()
    assert len(fields) == 4 and list(map(float, fields)) == [STEPS[0], SOURCE_STOP, 0., STEPS[0]]
    line = '.tran '+rows[0]
    replacement = f'.tran {tstep:.14g} {STOP:.14g} 0 {tmax:.14g}'
    changed = deck.replace(line, replacement)
    assert changed.replace(replacement, line) == deck
    if method == 'gear':
        assert changed.count('method=trap') == 1
        changed = changed.replace('method=trap', 'method=gear')
        assert changed.replace(replacement, line).replace('method=gear','method=trap') == deck
    return changed

def wave_difference(a, b, vectors, end=STOP):
    ta, va = a; tb, vb = b
    assert ta[0] == tb[0] == 0 and ta[-1] >= end-1e-18 and tb[-1] >= end-1e-18
    assert np.all(np.diff(ta)>0) and np.all(np.diff(tb)>0)
    assert set(va) == set(vb) == set(vectors)
    mask = ta <= end
    result = {}
    for name in vectors:
        assert len(va[name]) == len(ta) and len(vb[name]) == len(tb)
        assert np.isfinite(va[name]).all() and np.isfinite(vb[name]).all()
        values = np.interp(ta[mask], tb, vb[name])
        delta = va[name][mask]-values
        index = int(np.argmax(abs(delta)))
        result[name] = dict(maximum_absolute_difference=float(abs(delta[index])),
            time_s=float(ta[mask][index]), a_native=float(va[name][mask][index]),
            b_interpolated=float(values[index]))
    voltage = {n:v for n,v in result.items() if n.startswith('v(')}
    worst = max(voltage, key=lambda n:voltage[n]['maximum_absolute_difference'])
    return dict(end_s=end, every_vector=result, worst_voltage_vector=worst,
        worst_voltage_difference_v=voltage[worst]['maximum_absolute_difference'],
        interpolation_for_comparison_only=True, acceptance=False)

def controls():
    deck='title\nV1 a 0 PWL(0 0 1n 2)\n.tran 1.25e-13 3.4e-08 0 1.25e-13\n.control\nrun wave.raw\nquit\n.endc\n.end\n'
    for a in STEPS:
        for b in STEPS:
            changed=replace_analysis(deck,a,b)
            assert changed.split('.tran ')[0]==deck.split('.tran ')[0]
            assert changed.split('.control')[1]==deck.split('.control')[1]
    solver_deck=deck.replace('.control', '.options method=trap maxord=2 minbreak=1e-18\n.control')
    for step in (.03125e-12,.015625e-12):
        assert f'{step:.14g}' in replace_analysis(solver_deck,STEPS[0],step)
    gear=replace_analysis(solver_deck,*STEPS,method='gear')
    assert 'method=gear' in gear and 'method=trap' not in gear
    rejected=[]
    for name,bad in [('missing',deck.replace('.tran ','.ac ')),('duplicate',deck+deck),
                     ('uic',deck.replace('0 1.25e-13','0 1.25e-13 uic')),
                     ('wrong_source_step',deck.replace('1.25e-13','2.5e-13'))]:
        try:replace_analysis(bad,*STEPS)
        except (AssertionError,ValueError):rejected.append(name)
        else:raise AssertionError('Bad analysis accepted: '+name)
    t=np.array([0., .5e-9, STOP]);v={'v(a)':np.array([0.,.2,.3])}
    assert wave_difference((t,v),(t,v),list(v))['worst_voltage_difference_v']==0
    assert wave_difference((t,v),(t,{'v(a)':v['v(a)']+.01}),list(v))['worst_voltage_difference_v']>.009
    for name,bad in [('nan',{'v(a)':np.array([0.,np.nan,.3])}),('missing_vector',{})]:
        try:wave_difference((t,v),(t,bad),list(v))
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Bad wave accepted: '+name)
    return dict(four_factorial_decks_preserve_all_other_bytes=True,
        known_voltage_difference_detected=True,rejected=rejected,acceptance=False)

def restore(record, out):
    packed=out/'source.tar.gz';fetch(record['url'],record['sha256'],packed)
    assert packed.stat().st_size==record['bytes']
    source=ROOT/'cloud-tx-mux4';assert not source.exists()
    seen=set()
    with tarfile.open(packed) as tar:
        for member in tar:
            name=Path(member.name)
            assert not name.is_absolute() and '..' not in name.parts
            assert name.parts[0]=='cloud-tx-mux4' and member.name not in seen
            seen.add(member.name)
            assert member.isdir() or member.isfile(), 'Unexpected link or special member'
            tar.extract(member, ROOT, filter='data')
    packed.unlink()
    summary_path=source/'result.json';assert sha(summary_path)==record['summary_sha256']
    summary=json.loads(summary_path.read_text())
    assert summary['solver_profile']==PROFILE and summary['condition']=='hot_low_eighth_step'
    assert summary['assembled_core_scope']['mode']=='compact' and summary['assembled_core_scope']['placement_profile']=='compact_edge_supply'
    assert summary['component_screen_passed'] and summary['fault']=='none'
    for rel,digest in summary['outputs'].items():assert sha(source/rel)==digest,rel
    verified={}
    for path,digest in summary['inputs'].items():
        p=Path(path)
        # Restore every archived input and every repository circuit file exactly.
        # Historical controller Python/evidence files are provenance, not executed.
        if p.is_relative_to(source) or p.suffix in ('.spice','.inc','.lib','.osdi'):
            assert p.is_relative_to(ROOT) and sha(p)==digest,path
            verified[path]=digest
    runtime=Path(os.environ['CLOUD_NGSPICE'])
    runtime_hashes=[digest for path,digest in summary['inputs'].items() if path.endswith('/ngspice')]
    assert runtime_hashes==[sha(runtime)]
    contract=json.loads((source/'native/contract.json').read_text())
    assert contract['condition']['step_ps']==.125 and contract['fault']=='none'
    assert len(contract['hbt'])==62 and len(contract['mos'])==64
    assert hashlib.sha256(bytes(contract['bits'])).hexdigest()==record['signals']['source_bits_sha256']
    return source,summary,contract,verified

def main(study):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/'cloud-tx-step-factorial';out.mkdir(exist_ok=False)
    result=dict(status='RUNNING',study=study,source_head=os.environ['GITHUB_SHA'],accepted=False,
        serial_phy_complete=False,original_engineering_gates_changed=False,cases={},
        scope='Unchanged native circuit startup prefix only. TSTEP and TMAX varied independently; TSTOP shortened to1.2ns for diagnosis only. Does not replace full34ns waveform, original bit/device gates, physical validation or qualified SOA.',
        manual='https://ngspice.sourceforge.io/docs/ngspice-manual.pdf')
    try:
        result['controls']=controls()
        spec=json.loads((ROOT/'docs/evidence/pcie-tree4-assembly-input-20261015.json').read_text())
        studies=spec['placement_variants']['compact_edge_supply']['loaded_studies']
        records=[c for study in studies if study['run']==38763917040 for c in study['cases']
            if c['mode']=='compact' and c['condition']=='hot_low_eighth_step' and c['fault']=='none']
        assert len(records)==1
        record=records[0];result['source_run']=38763917040;result['source_receipt']=record
        source,summary,contract,verified=restore(record,out)
        result['verified_circuit_inputs']=verified;result['source_native_outputs']=summary['outputs']
        original=(source/'native/bench.cir').read_text()
        shutil.copyfile(source/'native/bench.cir',out/'original-bench.cir')
        shutil.copyfile(source/'native/contract.json',out/'original-contract.json')
        captures={}
        cases = [(a,b,'trap') for a in STEPS for b in STEPS] if study=='factorial' else [
            (STEPS[0],b,'trap') for b in (*STEPS,.03125e-12,.015625e-12)] + [
            (STEPS[0],b,'gear') for b in STEPS]
        for a,b,method in cases:
                label=f'tstep{a*1e12:g}-tmax{b*1e12:g}'+('-gear' if method=='gear' else '')
                profile = 'tight_gear2' if method=='gear' else PROFILE
                case=out/label;case.mkdir()
                (case/'bench.cir').write_text(replace_analysis(original,a,b,method))
                shutil.copyfile(source/'native/spinit',case/'spinit')
                env={k:v for k,v in os.environ.items() if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')}
                env.update(SPICE_SCRIPTS=str(case),RAYON_NUM_THREADS='1',OMP_NUM_THREADS='1')
                def limits():
                    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
                    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
                    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
                started=time.monotonic()
                with (case/'run.log').open('w') as log:
                    proc=subprocess.run([os.environ['CLOUD_NGSPICE'],'-n','-b','bench.cir'],cwd=case,env=env,
                        stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,timeout=1800)
                row=dict(tstep_s=a,tmax_s=b,tstop_s=STOP,method=method,returncode=proc.returncode,elapsed_s=time.monotonic()-started,accepted=False)
                result['cases'][label]=row
                log=(case/'run.log').read_text(errors='replace')
                row['diagnostics']=native_diagnostics(log,profile)
                assert proc.returncode==0 and not row['diagnostics'],log[-6000:]
                row['solver_options']=verify_solver_options(log,profile)
                assert [float(x) for x in re.findall(r'(?m)^NSSOC_NATIVE_MINBREAK (\S+)\s*$',log)]==[1e-18]
                row['native_minbreak_s']=1e-18
                flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
                assert [x[0] for x in flags]==['q.'+n+'.qnpn13g2' for n in contract['hbt']]
                assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',body)==['1'] for _,body in flags)
                row['native_off_flags_count']=len(flags)
                op=np.loadtxt(case/'op.dat',skiprows=1)
                assert op.size==len(contract['vectors'])+1 and np.isfinite(op).all() and abs(op).max()<=1e-10
                t,v,transport=read_streamed_wave(case/'wave.raw',contract['vectors'],STOP,b)
                captures[label]=(t,v);row['capture']=transport
                print(json.dumps(dict(case=label,rows=len(t),elapsed_s=row['elapsed_s'])),flush=True)
        original_t,original_v,transport=read_streamed_wave(source/'native/wave.raw',contract['vectors'],SOURCE_STOP,STEPS[0])
        baseline=captures['tstep0.125-tmax0.125']
        result['short_vs_full_same_settings']=wave_difference(baseline,(original_t,original_v),contract['vectors'],1.1e-9)
        # Detect whether shortening TSTOP itself changed the region of interest.
        result['short_prefix_reproduces_original_to_1nv']=result['short_vs_full_same_settings']['worst_voltage_difference_v']<=1e-9
        pairs=[('change_tstep_fixed_tmax_coarse','tstep0.125-tmax0.125','tstep0.0625-tmax0.125'),
            ('change_tstep_fixed_tmax_fine','tstep0.125-tmax0.0625','tstep0.0625-tmax0.0625'),
            ('change_tmax_fixed_tstep_coarse','tstep0.125-tmax0.125','tstep0.125-tmax0.0625'),
            ('change_tmax_fixed_tstep_fine','tstep0.0625-tmax0.125','tstep0.0625-tmax0.0625'),
            ('original_diagonal','tstep0.125-tmax0.125','tstep0.0625-tmax0.0625')]
        if study=='refinement':
            pairs=[('trap_125_to_62p5','tstep0.125-tmax0.125','tstep0.125-tmax0.0625'),
                ('trap_62p5_to_31p25','tstep0.125-tmax0.0625','tstep0.125-tmax0.03125'),
                ('trap_31p25_to_15p625','tstep0.125-tmax0.03125','tstep0.125-tmax0.015625'),
                ('gear_125_to_62p5','tstep0.125-tmax0.125-gear','tstep0.125-tmax0.0625-gear'),
                ('method_at_125','tstep0.125-tmax0.125','tstep0.125-tmax0.125-gear'),
                ('method_at_62p5','tstep0.125-tmax0.0625','tstep0.125-tmax0.0625-gear')]
        result['comparisons']={name:wave_difference(captures[a],captures[b],contract['vectors']) for name,a,b in pairs}
        assert all(sha(path)==digest for path,digest in verified.items())
        result['status']='COMPLETE_NATIVE_TSTEP_TMAX_STARTUP_DIAGNOSIS_NOT_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='result.json'}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k] for k in ('status','accepted')}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controls-only',action='store_true')
    parser.add_argument('--study',choices=('factorial','refinement'),default='factorial')
    args=parser.parse_args()
    if args.controls_only:print(json.dumps(controls()))
    else:main(args.study)
