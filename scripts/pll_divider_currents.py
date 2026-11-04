# SPDX-License-Identifier: Apache-2.0
"""First-divider current probes on the unchanged RHI120-C8 PLL deck; diagnosis only.

prepare: rewrite only the save list of the preserved candidate deck (stimuli,
loads, solver, 1 us duration and native OFF flags unchanged) and write the
same op-then-run wrapper as the original capture.
analyze: reproduce the original 0.9-1.0 us feedback frequency and phase span,
then report per-HBT terminal currents and divider transitions.
"""
import json,re,sys
from pathlib import Path
import numpy as np
def prepare(case,probes):
    p=json.load(open(probes));deck=(case/'candidate-circuit.cir').read_text().split('\n')
    hits=[i for i,l in enumerate(deck)if l.startswith('save ')];assert len(hits)==1,len(hits)
    deck[hits[0]]='save '+' '.join(p['voltages']+p['currents'])
    (case/'probe-circuit.cir').write_text('\n'.join(deck))
    (case/'probe.cir').write_text('NSSOC first-divider current probes\n.include "probe-circuit.cir"\n.control\nop\nwrite op.raw all\nrun probe.raw\nquit\n.endc\n.end\n')
    (case/'spinit').write_text('set num_threads=1\n')
def read_raw(path):
    with open(path,'rb')as s:
        parts=[]
        while True:
            row=s.readline(1<<20);assert row.endswith(b'\n');parts.append(row)
            if row==b'Binary:\n':break
        off=s.tell()
    h=b''.join(parts).decode('ascii');field=lambda k:[l.split(':',1)[1].strip()for l in h.splitlines()if l.startswith(k+':')][0]
    w=int(field('No. Variables'));n=int(field('No. Points'))
    names=[r.split()[1]for r in h.split('Variables:\n')[1].split('Binary:\n')[0].splitlines()]
    assert len(names)==w and Path(path).stat().st_size-off==n*w*8
    return np.memmap(path,mode='r',dtype='<f8',offset=off,shape=(n,w)),names
def crossings(t,x,level=0.0):
    i=np.flatnonzero((x[:-1]<level)&(x[1:]>=level));return t[i]+(level-x[i])*(t[i+1]-t[i])/(x[i+1]-x[i])
def analyze(case,probes,out):
    m,names=read_raw(case/'probe.raw');idx={n.lower():i for i,n in enumerate(names)}
    out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'raw-names.json').write_text(json.dumps(names))
    def col(n):
        n=n.lower();key=n if n in idx else 'i('+n+')'
        return np.asarray(m[:,idx[key]])
    t=np.asarray(m[:,0])
    late=(t>=0.9e-6)&(t<=1.0e-6)
    fb=col('v(fb)')-col('v(fbbar)');ref=col('v(reference)')
    fe=crossings(t,fb);fe=fe[(fe>=0.9e-6)&(fe<=1.0e-6)];re_=crossings(t,ref,1.25);re_=re_[(re_>=0.9e-6-10e-9)&(re_<=1.0e-6)]
    freq=(len(fe)-1)/(fe[-1]-fe[0]) if len(fe)>1 else None
    lag=[float(f-re_[re_<=f][-1])for f in fe if (re_<=f).any()]
    r=dict(points=len(t),end_s=float(t[-1]),feedback_frequency_hz=freq,feedback_edges=len(fe),phase_lag_s=[min(lag),max(lag)]if lag else None,
           phase_span_s=(max(lag)-min(lag))if lag else None,reference_original=dict(feedback_frequency_hz=104152221.297,phase_span_s=5.002708790e-9))
    (out/'result.json').write_text(json.dumps(r,indent=1,sort_keys=True))
    p=json.load(open(probes));roles=p['roles'];dev={}
    for q in p['currents']:
        name=q.split('.')[2];kind=q[-3:-1]
        x=col(q)[late];dev.setdefault(name,dict(role=roles.get(name)))[kind]=dict(min=float(x.min()),max=float(x.max()),mean=float(x.mean()))
    r['late_window_currents_a']=dev
    clk=col('v(clkp)')-col('v(clkn)');ce=crossings(t[late],clk[late]);r['clock_frequency_hz']=float((len(ce)-1)/(ce[-1]-ce[0]))if len(ce)>1 else None
    tail=t>=0.98e-6
    np.savez_compressed(out/'late-window.npz',t=t[tail].astype(np.float64),names=np.array(names[1:]),
        samples=np.array([np.asarray(m[tail,i])for i in range(1,len(names))],dtype=np.float32))
    (out/'result.json').write_text(json.dumps(r,indent=1,sort_keys=True));print(json.dumps({k:r[k]for k in('feedback_frequency_hz','phase_span_s','clock_frequency_hz','end_s')}))
if __name__=='__main__':
    stage,case,probes=sys.argv[1:4]
    prepare(Path(case),probes) if stage=='prepare' else analyze(Path(case),probes,sys.argv[4])
