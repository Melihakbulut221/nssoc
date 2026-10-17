#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure loaded physical C8 clock tuning with an explicit external clamp.

This is an open-loop characterization bench, not the unchanged acquisition
bench. No capacitor, resistance, intrinsic device or original gate is changed.
"""
import argparse,json,os,re,shutil,subprocess,time
from pathlib import Path
import numpy as np
import cloud_pll_pump_current as pump
import compare_cloud_routed_endpoints as reports
import run_cloud_pll865_snapshot as pll
from cloud_pll_terminal_diagnosis import crossing_times,controls as crossing_controls
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'cloud-pll-snapshot'
SUMMARY='d5eed10a190213d552fa410db5eece05cd2c39f0b8c5e8266ecee050c3ba4025'
PARTS='791cd593eac42eae8b9bf629b9ec90355b167a557910dcb5be4a441d30e01961'
COMPARE_SUMMARY='efe0a285b3ad52ca4f1550ef3e5bc6db9bda9968a68750998e57a6b69a093208'
COMPARE_PARTS='2e470bc982a3ed11742ea2ca9f9f1f730446f87d0c0b9c632cc3b0bc70e13c72'
PARENT='3d2dfdd6d27a05fc5d911461c84471b1e05f62e976b7ae31de9d01595a503b60'
CASES={'low':(.525,3.125e-13),'center':(.535,3.125e-13),
       'high':(.545,3.125e-13),'center_half':(.535,1.5625e-13)}

def measure(names,a,target,step):
    assert names[0]=='time'and len(names)==36 and len(set(names))==36
    assert a.shape[1]==len(names)and len(a)>150000 and np.isfinite(a).all()
    d={n:a[:,i]for i,n in enumerate(names)};t=d['time']
    assert t[0]==0 and abs(t[-1]-50e-9)<1e-15
    assert np.all(np.diff(t)>0)and np.diff(t).max()<=step*1.00001
    settled=t>=1e-9
    clamp_error=float(np.max(np.abs(d['v(vctrl)'][settled]-target)))
    assert clamp_error<1e-9,'Physical public control clamp not at commanded voltage'
    clock=d['v(clkp)']-d['v(clkn)'];edges=crossing_times(t,clock,0.)
    rows=[]
    for start in (10,20,30,40):
        lo,hi=start*1e-9,(start+10)*1e-9
        ix=np.flatnonzero((t>=lo)&(t<=hi+1e-20));assert len(ix)>1000
        e=edges[(edges>=lo)&(edges<hi)]
        assert len(e)>50,'Too few actual loaded clock transitions for tuning measurement'
        period=np.diff(e)
        values={}
        tt=t[ix]
        for key in ('v(vctrl)','i(vtune)','v(up)','v(down)'):
            y=d[key][ix];values[key]=dict(minimum=float(y.min()),maximum=float(y.max()),
                mean=float(np.trapezoid(y,tt)/(tt[-1]-tt[0])))
        rows.append(dict(interval_s=[lo,hi],clock_rises=len(e),frequency_hz=float((len(e)-1)/(e[-1]-e[0])),
            minimum_period_s=float(period.min()),maximum_period_s=float(period.max()),signals=values))
    return dict(rows=len(t),maximum_step_s=float(np.diff(t).max()),clamp_error_v=clamp_error,windows=rows,
        scope='Finite deterministic, externally clamped loaded clock response. Clamp source current is measured; logic voltage duty is not a current estimate. No acquisition, noise, jitter, CDR or device safety qualification.')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',choices=CASES,required=True);args=ap.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    target,step=CASES[args.case];out=ROOT/('cloud-pll-loaded-tuning-'+args.case)
    out.mkdir(exist_ok=False);reports.OUT=out
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,
        control_v=target,step_s=step,stop_s=50e-9,accepted=False,acquisition_accepted=False,
        full_device_safety_accepted=False,full_phy_accepted=False,qualified_pex=False,
        scope='New externally clamped tuning diagnostic of exact physical C8 parent, all845devices/wires and actual divider/PFD/pump loads. Original one-us acquisition bench and failing windows remain unchanged.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['controls']=dict(crossings=crossing_controls(),readback=readback_controls())
        fetch(pump.BASE+'cloud-results-39029337682-1-pll-pump-current/pll-pump-current-39029337682-1.summary.json',SUMMARY,out/'models-pin.json')
        pin=json.loads((out/'models-pin.json').read_text())
        assert pin['source_head']=='e29107296dc3abe0bcb15c57de0a7cbac67dc0e7'
        selected=[n for n in pin['outputs']if n.startswith('source/model-sources/')]
        selected+=['source-pin.json','source/runtime/patched-ngspice']
        restored,proof=reports.restore_report('pll-pump-current',39029337682,SUMMARY,PARTS,out/'models-source',selected)
        assert restored==pin;r['models_source']=proof
        original=json.loads((out/'models-source/source-pin.json').read_text())
        assert sha(out/'models-source/source-pin.json')==pump.SUMMARY
        assert not LIB.exists();shutil.copytree(out/'models-source/source/model-sources',LIB)
        assert all(sha(LIB/p)==d for p,d in original['preparation']['model_sources'].items())
        engine=out/'models-source/source/runtime/patched-ngspice';engine.chmod(0o755)
        assert sha(engine)=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        paired,proof=reports.restore_report('pll-c8-c9-comparison',39027779013,
            COMPARE_SUMMARY,COMPARE_PARTS,out/'physical-source',('c8/case/circuit.cir','c8/case/parent865.spice'))
        assert paired['status']=='COMPLETE_BOTH_EXACT_PHYSICAL_PLL_CAPTURE_COMPARISON_NOT_REPAIR_OR_ACCEPTANCE'
        assert paired['source_unchanged'];r['physical_source']=proof
        case=out/'case';case.mkdir()
        shutil.copyfile(out/'physical-source/c8/case/parent865.spice',case/'parent865.spice')
        assert sha(case/'parent865.spice')==PARENT==original['outputs']['case/parent865.spice']
        original_deck=(out/'physical-source/c8/case/circuit.cir').read_text()
        assert sha(out/'physical-source/c8/case/circuit.cir')==original['outputs']['case/circuit.cir']
        lines=original_deck.splitlines();saves=[l for l in lines if l.startswith('save ')]
        assert len(saves)==1;vectors=saves[0].split()[1:]
        assert len(vectors)==34 and len(set(vectors))==34
        flags=re.findall(r'(?m)^alter @(\S+)\[off\] = 1$',original_deck);assert len(flags)==102
        oldtran='.tran 3.125e-13 1e-06 0 3.125e-13';assert lines.count(oldtran)==1
        changes={oldtran:f'.tran {step:.14g} 5e-8 0 {step:.14g}'}
        body='\n'.join(changes.get(l,l)for l in lines)+'\n'
        anchor='.control\n';assert body.count(anchor)==1
        clamp=f'VTUNE vctrl 0 PWL(0 0 500p {target:.12g})\n'
        body=body.replace(anchor,clamp+anchor)
        control='op\nwrite op.raw all\nsave '+' '.join(vectors+['i(vtune)'])+'\nrun\nwrite tuning.raw all\necho NSSOC_BACKEND_OPTIONS_BEGIN\noption\necho NSSOC_BACKEND_OPTIONS_END\nquit\n'
        assert body.count('.endc\n')==1;body=body.replace('.endc\n',control+'.endc\n')
        reconstructed=body.replace(control,'').replace(clamp,'').replace(changes[oldtran],oldtran)
        assert reconstructed==original_deck,'Undeclared original bench change'
        (case/'bench.cir').write_text(body);(case/'spinit').write_text('set num_threads=1\n')
        protected={str(p):sha(p)for p in [Path(__file__),case/'parent865.spice',case/'bench.cir',engine,*LIB.rglob('*')]if p.is_file()}
        r.update(parent_sha256=PARENT,source_models=original['preparation']['model_sources'],
            protected_inputs=protected,bench_changes=dict(external_control_clamp=clamp.strip(),
            transient=changes[oldtran],original_34_voltage_probes=True,additional_probe='i(vtune)',
            original_physical_circuit_unchanged=True,original_acquisition_gates_unchanged=True));save()
        env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')}
        env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
        start=time.monotonic()
        with(case/'native.log').open('w')as log:
            proc=subprocess.Popen([str(engine),'-n','-b','bench.cir'],cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT)
            while proc.poll()is None:
                print(json.dumps(dict(case=args.case,elapsed_s=time.monotonic()-start,native_pid=proc.pid)),flush=True)
                time.sleep(60)
        r.update(returncode=proc.returncode,elapsed_s=time.monotonic()-start);save()
        text=(case/'native.log').read_text(errors='replace')
        options,diagnostics,_=backend_readback(text,'klu');r.update(native_options=options,diagnostics=diagnostics);save()
        assert proc.returncode==0 and not diagnostics,'Native execution or diagnostic failure'
        observed=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
        assert [a for a,b in observed]==flags
        assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',b)==['1']for a,b in observed)
        r['zero_source_operating_point']=pll.zero_source_operating_point((case/'op.raw').read_bytes(),vectors)
        raw=(case/'tuning.raw').read_bytes();names,a,meta=pll.decode_prefix(raw)
        assert meta['header_matches_observed']and meta['payload_has_only_complete_rows']
        assert set(names)=={'time',*vectors,'i(vtune)'}
        r['measurement']=measure(names,a,target,step);r['capture']=dict(meta,sha256=sha(case/'tuning.raw'))
        # Real captured-wave corruption must not masquerade as tuning evidence.
        bad=a.copy();bad[:,names.index('v(clkp)')]=bad[:,names.index('v(clkn)')]
        try:measure(names,bad,target,step)
        except AssertionError:r['actual_stopped_clock_control_rejected']=True
        else:raise AssertionError('Stopped measured clock accepted')
        assert all(sha(Path(p))==d for p,d in protected.items())
        r.update(status='COMPLETE_NATIVE_LOADED_TUNING_POINT_NOT_PLL_ACQUISITION_OR_PHY_ACCEPTANCE',
            sources_unchanged=True,native_off_flags_verified=len(flags))
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
