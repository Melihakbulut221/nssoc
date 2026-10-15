#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound single-VBIC terminal playback; never full-circuit acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import time
import numpy as np
from cloud_tx_step_factorial import restore, STOP, SOURCE_STOP, STEPS, PROFILE, charge_readback
from cloud_tx_stream import read_streamed_wave
from run_cloud_tx_mux4 import solver_options,verify_solver_options,native_diagnostics
from run_cloud_tx_operating_point import sha

ROOT=Path(__file__).resolve().parents[1]
TARGET='xtree.xd0002'
DEVICE='q.xtarget.qnpn13g2'
PORTS=('c','b','e','sub')
VECTORS=[*(f'v({p})' for p in PORTS),'v(xtarget.t)',
    'i(vc)','i(vb)','i(ve)','i(vs)',
    *(f'@{DEVICE}[{p}]' for p in ('ic','ib','ie','is','qbe','qbc','cbe','cbc'))]


def pwl(t,v):
    assert len(t)==len(v) and len(t)>1 and t[0]==0 and t[-1]==STOP
    assert np.isfinite(t).all() and np.isfinite(v).all() and np.all(np.diff(t)>0)
    # Exact binary64 roundtrip, no original-time rounding or point decimation.
    values=[(format(float(a),'.17g'),format(float(b),'.17g')) for a,b in zip(t,v,strict=True)]
    assert np.array_equal(np.array([float(a) for a,b in values]),t)
    assert np.array_equal(np.array([float(b) for a,b in values]),v)
    return 'PWL(\n+ '+'\n+ '.join(a+' '+b for a,b in values)+')'


def deck(library,condition,row,t,terminal_values,step,charge):
    assert row['model']=='npn13g2' and row['nx']==6 and len(row['terminals'])==4
    assert set(terminal_values)==set(PORTS) and step in STEPS and charge in (1e-14,1e-20)
    lines=['NSSOC isolated original VBIC terminal playback NOT CIRCUIT ACCEPTANCE',
        f'.lib "{library}" {condition["hbt"]}',f'.temp {condition["temperature_c"]}',
        solver_options(PROFILE)+f' chgtol={charge:.14g}',
        'XTARGET c b e sub npn13g2 Nx=6']
    for name,port in zip(('VC','VB','VE','VS'),PORTS,strict=True):
        lines.append(f'{name} {port} 0 '+pwl(t,terminal_values[port]))
    lines+=['.control','set wr_singlescale','set wr_vecnames','set numdgt=17',
        'save '+' '.join(VECTORS),f'alter @{DEVICE}[off] = 1',
        f'echo NSSOC_NATIVE_FLAG_BEGIN {DEVICE}',f'show {DEVICE} : off','echo NSSOC_NATIVE_FLAG_END',
        'op','wrdata op.dat '+' '.join(VECTORS),
        f'tran {STEPS[0]:.14g} {STOP:.14g} 0 {step:.14g}',
        'wrdata wave.dat '+' '.join(VECTORS),
        'echo NSSOC_SOLVER_OPTIONS_BEGIN','option','echo NSSOC_NATIVE_MINBREAK $minbreak','echo NSSOC_SOLVER_OPTIONS_END',
        'showmod > native-models.txt','quit','.endc','.end']
    return '\n'.join(lines)+'\n'


def parse_wave(path,step,require_complete=True):
    with path.open() as stream:
        assert stream.readline().split()==['time',*VECTORS]
        data=np.loadtxt(stream,ndmin=2)
    assert data.shape[1]==len(VECTORS)+1 and len(data)>1 and np.isfinite(data).all()
    t=data[:,0];assert t[0]==0 and np.all(np.diff(t)>0)
    assert np.max(np.diff(t))<=step*1.00001
    complete=abs(t[-1]-STOP)<1e-18
    if require_complete:assert complete,'Incomplete native playback'
    return t,dict(zip(VECTORS,data[:,1:].T,strict=True)),dict(rows=len(t),end_s=float(t[-1]),
        complete=complete,sha256=sha(path),all_rows_retained=True)


def compare(a,b):
    ta,va=a;tb,vb=b;assert abs(ta[-1]-STOP)<1e-18 and abs(tb[-1]-STOP)<1e-18
    result={}
    for name in VECTORS:
        interp=np.interp(ta,tb,vb[name]);diff=va[name]-interp;i=int(np.argmax(abs(diff)))
        result[name]=dict(maximum_absolute_difference=float(abs(diff[i])),time_s=float(ta[i]),
            coarse_native=float(va[name][i]),fine_interpolated=float(interp[i]))
    return dict(vectors=result,accepted=False,scope='Same recorded terminal playback only; no full-circuit output oracle or physical acceptance.')


def controls():
    t=np.array([0.,1.25e-16,.5e-9,STOP]);v=np.array([0.,1e-8,.7,.9])
    s=pwl(t,v);assert len(s.splitlines())==len(t)+1
    rejected=[]
    for name,a,b in [('duplicate_time',np.array([0.,0.,.5e-9,STOP]),v),('nan',t,np.array([0.,np.nan,.7,.9])),
                     ('incomplete',t[:-1],v[:-1]),('length',t,v[:-1])]:
        try:pwl(a,b)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Corrupt playback accepted')
    row=dict(model='npn13g2',nx=6,terminals=['c','b','e','s'])
    a=deck('/frozen/cornerHBT.lib',dict(hbt='hbt_wcs',temperature_c=125),row,t,{p:v for p in PORTS},STEPS[0],1e-14)
    b=deck('/frozen/cornerHBT.lib',dict(hbt='hbt_wcs',temperature_c=125),row,t,{p:v for p in PORTS},STEPS[1],1e-14)
    assert a.replace('0 1.25e-13\n','0 STEP\n')==b.replace('0 6.25e-14\n','0 STEP\n')
    return dict(all_original_time_value_bits_preserved=True,same_stimulus_across_steps=True,
        rejected=rejected,accepted=False)


def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/'cloud-tx-vbic-playback';out.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],target=TARGET,accepted=False,
        serial_phy_complete=False,original_circuit_acceptance_changed=False,cases={},
        scope='Single original Nx6 npn13g2 VBIC at original125C/hbt_wcs corner, driven by PWL of original native collector/base/emitter/substrate terminal samples from0 to1.2ns. Circuit feedback removed for diagnosis only. Source terminal sample interpolation is explicit; neither this reduction nor a successful result replaces full34ns transistor/bit/physical gates.')
    try:
        result['controls']=controls()
        spec=json.loads((ROOT/'docs/evidence/pcie-tree4-assembly-input-20261015.json').read_text())
        rows=[c for study in spec['placement_variants']['compact_edge_supply']['loaded_studies'] if study['run']==38763917040
            for c in study['cases'] if c['mode']=='compact' and c['condition']=='hot_low_eighth_step' and c['fault']=='none']
        assert len(rows)==1
        record=rows[0];source,summary,contract,verified=restore(record,out)
        result['source_receipt']=record;result['source_run']=38763917040
        result['verified_input_hashes']=verified
        original_t,original_v,transport=read_streamed_wave(source/'native/wave.raw',contract['vectors'],SOURCE_STOP,STEPS[0])
        row=contract['hbt'][TARGET];assert row['model']=='npn13g2' and row['nx']==6
        assert contract['condition']['temperature_c']==125 and contract['condition']['hbt']=='hbt_wcs'
        t=np.append(original_t[original_t<STOP],STOP)
        terminal_values={port:np.interp(t,original_t,original_v['v('+node+')']) if node!='0' else np.zeros_like(t)
            for port,node in zip(PORTS,row['terminals'],strict=True)}
        assert all(value[0]==0 for value in terminal_values.values())
        result['device_binding']=row;result['source_capture']=transport
        result['playback']=dict(original_native_points=int(np.sum(original_t<STOP)),points=len(t),
            terminal_nodes=dict(zip(PORTS,row['terminals'],strict=True)),endpoint_interpolated_s=STOP,
            interior_points_decimated=False,source_bits_oracle_used=False)
        np.savetxt(out/'terminal-playback.dat',np.column_stack([t,*terminal_values.values()]),fmt='%.17g',header='time '+' '.join(PORTS),comments='')
        library=source/'inputs/models/cornerHBT.lib';assert sha(library)==verified[str(library)]
        captures={}
        for charge in (1e-14,1e-20):
            for step in STEPS:
                label=f'charge{charge:g}-step{step*1e12:g}'
                case=out/label;case.mkdir();(case/'bench.cir').write_text(deck(library,contract['condition'],row,t,terminal_values,step,charge))
                (case/'spinit').write_text('set num_threads=1\n')
                info=dict(step_s=step,charge_c=charge,complete=False,accepted=False)
                result['cases'][label]=info
                try:
                    env={k:v for k,v in os.environ.items() if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')}
                    env.update(SPICE_SCRIPTS=str(case),RAYON_NUM_THREADS='1',OMP_NUM_THREADS='1')
                    def limits():
                        resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
                        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
                        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
                    started=time.monotonic()
                    with (case/'run.log').open('w') as log:
                        proc=subprocess.run([os.environ['CLOUD_NGSPICE'],'-n','-b','bench.cir'],cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limits,timeout=1800)
                    info.update(returncode=proc.returncode,elapsed_s=time.monotonic()-started)
                    log=(case/'run.log').read_text(errors='replace')
                    info['solver_options']=verify_solver_options(log,PROFILE)
                    info['charge_readback']=charge_readback(info['solver_options']['native_text'],charge)
                    info['diagnostics']=native_diagnostics(log,PROFILE)
                    flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
                    assert len(flags)==1 and flags[0][0]==DEVICE and re.findall(r'(?m)^\s*off\s+([01])\s*$',flags[0][1])==['1']
                    assert proc.returncode==0 and not info['diagnostics'],'Native playback diagnostic or process failure'
                    tc,vc,capture=parse_wave(case/'wave.dat',step)
                    errors={port:float(np.max(abs(vc['v('+port+')']-np.interp(tc,t,terminal_values[port])))) for port in PORTS}
                    assert max(errors.values())<1e-9,'Native forced terminal differs from recorded waveform'
                    info.update(complete=True,capture=capture,terminal_playback_error_v=errors,
                        native_model_parameter_dump_sha256=sha(case/'native-models.txt'))
                    info['ranges']={name:[float(v.min()),float(v.max())] for name,v in vc.items()}
                    old=original_v['@q.'+TARGET+'.qnpn13g2[ic]']
                    delta=vc['@'+DEVICE+'[ic]']-np.interp(tc,original_t,old);i=int(np.argmax(abs(delta)))
                    info['current_difference_from_coupled_capture']=dict(maximum_absolute_a=float(abs(delta[i])),time_s=float(tc[i]),
                        scope='Diagnostic only: recorded voltage PWL introduces slope knots and does not replay hidden thermal states explicitly.')
                    captures[label]=(tc,vc)
                except Exception as error:
                    info['error']=repr(error)
                    if (case/'wave.dat').exists():
                        try:info['partial_capture']=parse_wave(case/'wave.dat',step,False)[2]
                        except Exception as tail_error:info['partial_capture_error']=repr(tail_error)
                print(json.dumps(dict(case=label,complete=info['complete'],error=info.get('error'))),flush=True)
        result['comparisons']={}
        for charge in (1e-14,1e-20):
            a=f'charge{charge:g}-step0.125';b=f'charge{charge:g}-step0.0625'
            if a in captures and b in captures:result['comparisons'][f'charge{charge:g}']=compare(captures[a],captures[b])
        assert all(sha(path)==digest for path,digest in verified.items())
        result['all_simulations_complete']=all(row['complete'] for row in result['cases'].values())
        result['status']='COMPLETE_SOURCE_BOUND_VBIC_PLAYBACK_DIAGNOSIS_NOT_ACCEPTANCE'
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='result.json'}
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k] for k in ('status','accepted')}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--controls-only',action='store_true')
    if parser.parse_args().controls_only:print(json.dumps(controls()))
    else:main()
