#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Constant-bias VBIC charge companion counterexample, not PDK/PHY approval."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-vbic-companion'
UPSTREAM='a80f6e3e95d51534905b1f23410a951802666656'
SOURCE_SHA='ae2fca22ca7178bce26f31b4e433307945cafa9d8661d55007eed8fc096ff866'
OLD='cbcx = *(ckt->CKTstate0 + here->VBICcqbcx);'
NEW='cbcx = model->VBICtype * (*(ckt->CKTstate0 + here->VBICcqbcx) - gbcx * Vbcx);'
VECTORS=['v(c)','v(b)','v(e)','v(s)','i(vc)','i(vb)','i(ve)','i(vs)','@q1[cbcx]']

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def patch(path):
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
    source=raw.decode();assert source.count(OLD)==1 and NEW not in source
    changed=source.replace(OLD,NEW);assert changed.replace(NEW,OLD)==source
    path.write_text(changed)
    return dict(original_sha256=SOURCE_SHA,patched_sha256=sha(path),old=OLD,new=NEW,
        physical_model_parameters_changed=False,one_expression_only=True)

def deck(sign,qco,step):
    kind='npn' if sign==1 else 'pnp'
    # Synthetic passive charge storage must not generate current at constant bias.
    # QCO=0 is the matched negative control; all other model parameters are identical.
    return f"""NSSOC VBIC constant-bias companion diagnostic NOT PHY ACCEPTANCE
.model dut {kind} level=9 is=1e-16 nf=1 nr=1 rcx=1 rci=10 rbx=10 rbi=10 re=1 rs=10 rbp=10
+ gamm=1e-6 qco={qco:g} cjc=1e-14 cje=1e-14 tf=1e-12 itf=.1 vo=10 hrcf=1 selft=0
Q1 c b e s dut
VC c 0 {sign*.3:g}
VB b 0 {sign*.6:g}
VE e 0 0
VS s 0 0
.options method=trap maxord=2 reltol=1e-8 abstol=1e-15 vntol=1e-10 trtol=1 itl4=100
.control
set wr_singlescale
set wr_vecnames
set numdgt=17
save {' '.join(VECTORS)}
op
wrdata op.dat {' '.join(VECTORS)}
tran 5e-13 5e-11 0 {step:g}
wrdata wave.dat {' '.join(VECTORS)}
option
showmod > model-readback.txt
quit
.endc
.end
"""

def capture(path,transient):
    with path.open() as stream:
        header=stream.readline().split();assert header[1:]==VECTORS,header
        a=np.loadtxt(stream,ndmin=2)
    assert a.shape[1]==len(VECTORS)+1 and np.isfinite(a).all()
    if transient:
        assert header[0]=='time' and len(a)>1 and a[0,0]==0 and abs(a[-1,0]-5e-11)<1e-20
        assert np.all(np.diff(a[:,0])>0)
    else:assert len(a)==1
    return a

def run_variant(label,exe):
    OUT.mkdir(exist_ok=True)
    result=dict(status='RUNNING',variant=label,executable_sha256=sha(exe),accepted=False,cases={},
        scope='Synthetic NPN/PNP level9 VBIC at fixed nonzero DC biases; QCO0 matched controls. DC and transient currents should agree at every sample. No source ramp, OFF flag, PDK change, full-circuit or PHY signoff.')
    try:
        for sign in (1,-1):
            for qco in (0.,1e-15):
                for step in (1e-12,.5e-12):
                    name=f'{"npn" if sign==1 else "pnp"}-qco{qco:g}-step{step:g}'
                    case=OUT/label/name;case.mkdir(parents=True)
                    (case/'bench.cir').write_text(deck(sign,qco,step));(case/'spinit').write_text('set num_threads=1\n')
                    row=dict(sign=sign,qco=qco,step_s=step,complete=False);result['cases'][name]=row
                    env={k:v for k,v in os.environ.items() if k not in ('GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD','PYTHONPATH','PYTHONHOME')}
                    env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1')
                    try:
                        p=subprocess.run([str(exe),'-n','-b','bench.cir'],cwd=case,env=env,capture_output=True,text=True,timeout=90)
                        log=p.stdout+p.stderr;(case/'run.log').write_text(log);row['returncode']=p.returncode
                        diagnostics=[l for l in log.splitlines() if any(x in l.lower() for x in ('warning','too small','doanalyses:','fatal','error:','singular matrix'))]
                        row['diagnostics']=diagnostics;assert p.returncode==0 and not diagnostics
                        op=capture(case/'op.dat',False)[0];wave=capture(case/'wave.dat',True)
                        assert np.max(np.diff(wave[:,0]))<=step*1.00001
                        drift={n:float(np.max(abs(wave[:,i+1]-op[i+1]))) for i,n in enumerate(VECTORS)}
                        row.update(complete=True,rows=len(wave),op={n:float(op[i+1]) for i,n in enumerate(VECTORS)},max_dc_transient_difference=drift,
                            max_current_drift_a=max(v for n,v in drift.items() if n.startswith('i(')),
                            current_dc_invariance_1na=max(v for n,v in drift.items() if n.startswith('i('))<=1e-9)
                        assert (row['op']['@q1[cbcx]']==0) if qco==0 else (row['op']['@q1[cbcx]']>0)
                    except Exception as e:row['error']=repr(e)
                    print(json.dumps(dict(variant=label,case=name,complete=row['complete'],current_drift=row.get('max_current_drift_a'),error=row.get('error'))),flush=True)
        result['status']='COMPLETE_CONSTANT_BIAS_DIAGNOSIS_NOT_ACCEPTANCE'
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in (OUT/label).rglob('*') if p.is_file()}
        (OUT/(label+'.json')).write_text(json.dumps(result,indent=2)+'\n')

def compare():
    reports={name:json.loads((OUT/(name+'.json')).read_text()) for name in ('packaged','pristine','patched')}
    keys=set(reports['packaged']['cases']);assert all(set(r['cases'])==keys for r in reports.values())
    comparisons={}
    for key in sorted(keys):
        rows={name:r['cases'][key] for name,r in reports.items()}
        comparisons[key]=dict(complete={n:r['complete'] for n,r in rows.items()},drift_a={n:r.get('max_current_drift_a') for n,r in rows.items()})
        if all(r['complete'] for r in rows.values()):
            a=capture(OUT/'packaged'/key/'wave.dat',True);b=capture(OUT/'pristine'/key/'wave.dat',True)
            comparisons[key]['packaged_vs_pristine_max_original_difference']=float(np.max(abs(a[:,1:]-np.column_stack([np.interp(a[:,0],b[:,0],b[:,i]) for i in range(1,b.shape[1])]))))
    result=dict(status='COMPLETE_PAIRED_RUNTIME_COMPANION_DIAGNOSIS_NOT_ACCEPTANCE',accepted=False,
        source_commit=UPSTREAM,patch=json.loads((OUT/'patch.json').read_text()),comparisons=comparisons,
        all_native_cases_complete=all(c['complete'] for r in reports.values() for c in r['cases'].values()),
        patched_all_current_invariance_pass=all(c.get('current_dc_invariance_1na',False) for c in reports['patched']['cases'].values()),
        pristine_zero_qco_controls_pass=all(c.get('current_dc_invariance_1na',False) for c in reports['pristine']['cases'].values() if c['qco']==0),
        original_active_qco_violation_observed=any(c.get('max_current_drift_a',0)>1e-9 for c in reports['pristine']['cases'].values() if c['qco']>0),
        scope='This isolates the transient companion RHS expression only. A passing synthetic counterexample does not validate actual IHP, coupled tree startup, full34ns/PVT, physical layout or full serialPHY. Preserve both pristine and patched binaries and all native failures.')
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--variant');p.add_argument('--exe',type=Path);p.add_argument('--patch',type=Path);p.add_argument('--compare',action='store_true');args=p.parse_args()
    if args.patch:
        OUT.mkdir(exist_ok=True);(OUT/'patch.json').write_text(json.dumps(patch(args.patch),indent=2)+'\n')
    elif args.compare:compare()
    else:assert args.variant in ('packaged','pristine','patched') and args.exe;run_variant(args.variant,args.exe.resolve())
