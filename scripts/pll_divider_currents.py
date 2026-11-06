# SPDX-License-Identifier: Apache-2.0
"""First-divider current probes on the unchanged RHI120-C8 PLL deck; diagnosis only.

prepare: rewrite only the save list of the preserved candidate deck (stimuli,
loads, solver, 1 us duration and native OFF flags unchanged) and write the
same op-then-run wrapper as the original capture.
analyze: reproduce the original 0.9-1.0 us feedback frequency and phase span,
then report per-HBT terminal currents and divider transitions.
"""
import json,os,re,sys
from pathlib import Path
import numpy as np
VARIANTS={'original':{},
 'cond_lowz4':{'XD0497':'16u','XD0498':'16u','XD0488':'4u','XD0489':'4u'},
 'cond_series4':{'XD0497':'16u','XD0498':'16u'},
 'series4_cp8':{'XD0497':'16u','XD0498':'16u','XD0375':'8u'},
 'series4_cpmatch':{'XD0497':'16u','XD0498':'16u','XD0375':'10.4u'}}
# VCO ring-node MIMs (XD0572/0575/0578/0584/0593 at 11x11 um, XD0576 at 11.2x11 um) scaled up so that
# 8 GHz falls where the current-tuned ring still has full swing.
RING_MIMS={'XD0572':(11,11),'XD0575':(11,11),'XD0576':(11.2,11),'XD0578':(11,11),'XD0584':(11,11),'XD0593':(11,11)}
def mims(scale):return{k:dict(w=f'{w*scale:.3f}u',l=f'{l*scale:.3f}u')for k,(w,l)in RING_MIMS.items()}
VARIANTS['cpmatch_mim105']={**VARIANTS['series4_cpmatch'],**mims(1.055)}
VARIANTS['cpmatch_mim109']={**VARIANTS['series4_cpmatch'],**mims(1.09)}
VARIANTS['cp8_mim105']={**VARIANTS['series4_cp8'],**mims(1.055)}
# Exploratory, not a layout: the control node's resistive bias (XD0567 to vco_avdd,
# XD0568 to avss) weakened tenfold, plus an ideal series-RC integrating branch
# from vctrl to avss. Tests whether an integrating loop filter acquires 8 GHz.
WEAK_BIAS={'XD0567':dict(l='1200u'),'XD0568':dict(l='470u')}
VARIANTS['cp8_int2k1']={**VARIANTS['series4_cp8'],**WEAK_BIAS,'__extra__':['Rnssoc_int vctrl nssoc_int 2100','Cnssoc_int nssoc_int avss 30p']}
VARIANTS['cp8_int1k']={**VARIANTS['series4_cp8'],**WEAK_BIAS,'__extra__':['Rnssoc_int vctrl nssoc_int 1000','Cnssoc_int nssoc_int avss 60p']}
# Same integrating branch, started near the operating point: the integrating
# capacitor and vctrl are initialised so the 1.5 us window covers lock, not slew.
VARIANTS['cp8_int2k1_ic080']={**VARIANTS['cp8_int2k1'],'__ic__':'.ic v(xloop.nssoc_int)=0.80 v(vctrl)=0.80'}
VARIANTS['cp8_int2k1_ic088']={**VARIANTS['cp8_int2k1'],'__ic__':'.ic v(xloop.nssoc_int)=0.88 v(vctrl)=0.88'}
# Ring load resistors (XD0480-0482, XD0490-0492, 8 x 4.4 um rppd) lengthened:
# a larger RC lowers the ring frequency at full tail current while I*R raises
# the swing, so 8 GHz can fall where the divider still counts. Integrating
# filter as above, started at 0.70 V where the swing is still full.
RING_LOADS=['XD0480','XD0481','XD0482','XD0490','XD0491','XD0492']
def loads(l):return{k:dict(l=l)for k in RING_LOADS}
VARIANTS['int2k1_rl112']={**VARIANTS['cp8_int2k1'],**loads('4.93u'),'__ic__':'.ic v(xloop.nssoc_int)=0.70 v(vctrl)=0.70'}
VARIANTS['int2k1_rl125']={**VARIANTS['cp8_int2k1'],**loads('5.5u'),'__ic__':'.ic v(xloop.nssoc_int)=0.70 v(vctrl)=0.70'}
def patch_parent(case,variant):
    lines=(case/'parent865.spice').read_text().split('\n');changed={}
    for name,w in VARIANTS[variant].items():
        if name=='__ic__':changed[name]=w;continue
        if name=='__extra__':
            ends=[i for i,l in enumerate(lines)if l.strip().lower().startswith('.ends')];assert len(ends)==1,len(ends)
            lines[ends[0]:ends[0]]=w;changed[name]=w;continue
        hits=[i for i,l in enumerate(lines)if l.split(maxsplit=1)[:1]==[name]];assert len(hits)==1,(name,len(hits))
        old=new=lines[hits[0]]
        for k,v in(w.items()if isinstance(w,dict)else[('w',w)]):new,n=re.subn(r'(\s'+k+r'=)\S+',r'\g<1>'+v,new);assert n==1,(old,k)
        lines[hits[0]]=new;changed[name]=[old,new]
    (case/'parent865.spice').write_text('\n'.join(lines));return changed
STOP=os.environ.get('NSSOC_PLL_STOP','1e-06')
def prepare(case,probes,variant='original'):
    json.dump(patch_parent(case,variant),open(case/'variant-patch.json','w'),indent=1)
    p=json.load(open(probes));deck=(case/'candidate-circuit.cir').read_text().split('\n')
    tran=[i for i,l in enumerate(deck)if l.startswith('.tran ')];assert len(tran)==1 and deck[tran[0]]=='.tran 3.125e-13 1e-06 0 3.125e-13',deck[tran[0]]
    step=os.environ.get('NSSOC_PLL_MAXSTEP','3.125e-13');deck[tran[0]]='.tran 3.125e-13 '+STOP+' 0 '+step
    ic=VARIANTS[variant].get('__ic__')
    if ic:deck.insert(tran[0]+1,ic)
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
    t=np.asarray(m[:,0]);end=float(t[-1]);lo=end-0.1e-6
    late=(t>=lo)&(t<=end)
    fb=col('v(fb)')-col('v(fbbar)');ref=col('v(reference)')
    fe_all=crossings(t,fb);fe=fe_all[(fe_all>=lo)&(fe_all<=end)];re_=crossings(t,ref,1.25);re_=re_[(re_>=lo-10e-9)&(re_<=end)]
    freq=(len(fe)-1)/(fe[-1]-fe[0]) if len(fe)>1 else None
    lag=[float(f-re_[re_<=f][-1])for f in fe if (re_<=f).any()]
    traj=[]
    clk_all=col('v(clkp)')-col('v(clkn)');up_all=col('v(up)');dn_all=col('v(down)');vc_all=col('v(vctrl)');re_all=crossings(t,col('v(reference)'),1.25)
    for a in np.arange(0.1e-6,end-1e-12,50e-9):
        w=(t>=a)&(t<a+50e-9);ce_=crossings(t[w],clk_all[w]);fw=fe_all[(fe_all>=a)&(fe_all<a+50e-9)]
        tw=t[w];dtw=np.diff(tw);uh=(up_all[w]>1.25)[:-1];dh=(dn_all[w]>1.25)[:-1];vw=vc_all[w]
        frac=lambda m:float(np.sum(dtw[m])/np.sum(dtw))
        rw=re_all[(re_all>=a)&(re_all<a+50e-9)]
        traj.append(dict(start_s=float(a),vco_hz=float((len(ce_)-1)/(ce_[-1]-ce_[0]))if len(ce_)>1 else None,
            feedback_hz=float((len(fw)-1)/(fw[-1]-fw[0]))if len(fw)>1 else None,vctrl_v=float(np.mean(vw)),
            vctrl_start_v=float(vw[0]),vctrl_end_v=float(vw[-1]),up_only=frac(uh&~dh),down_only=frac(dh&~uh),both=frac(uh&dh),
            reference_edges=len(rw),feedback_edges=len(fw)))
    r=dict(points=len(t),end_s=end,window_s=[lo,end],trajectory=traj,feedback_frequency_hz=freq,feedback_edges=len(fe),phase_lag_s=[min(lag),max(lag)]if lag else None,
           phase_span_s=(max(lag)-min(lag))if lag else None,reference_original=dict(feedback_frequency_hz=104152221.297,phase_span_s=5.002708790e-9))
    (out/'result.json').write_text(json.dumps(r,indent=1,sort_keys=True))
    p=json.load(open(probes));roles=p['roles'];dev={}
    for q in p['currents']:
        name=q.split('.')[2];kind=q[-3:-1]
        x=col(q)[late];dev.setdefault(name,dict(role=roles.get(name)))[kind]=dict(min=float(x.min()),max=float(x.max()),mean=float(x.mean()))
    r['late_window_currents_a']=dev
    clk=col('v(clkp)')-col('v(clkn)');ce=crossings(t[late],clk[late]);r['clock_frequency_hz']=float((len(ce)-1)/(ce[-1]-ce[0]))if len(ce)>1 else None
    sl=col('v(xloop.w_t494_rppd_2)')-col('v(xloop.w_t493_rppd_2)');tl=t[late];x=sl[late]-np.median(sl[late])
    edges=tl[np.flatnonzero(np.sign(x[:-1])!=np.sign(x[1:]))];rises=crossings(tl,clk[late])
    hist=np.histogram(edges,bins=rises)[0];r['divider_transitions_per_clock_period']={int(k):int(n)for k,n in zip(*np.unique(hist,return_counts=True))}
    r['vco_over_feedback_ratio']=(r['clock_frequency_hz']/freq)if freq and r['clock_frequency_hz']else None
    cb=col('v(xloop.w_t387_b)')-col('v(xloop.w_t388_b)');r['divider_clock_base_diff_v']=[float(cb[late].min()),float(cb[late].max())]
    tail=t>=end-0.02e-6
    np.savez_compressed(out/'late-window.npz',t=t[tail].astype(np.float64),names=np.array(names[1:]),
        samples=np.array([np.asarray(m[tail,i])for i in range(1,len(names))],dtype=np.float32))
    (out/'result.json').write_text(json.dumps(r,indent=1,sort_keys=True));print(json.dumps({k:r[k]for k in('feedback_frequency_hz','phase_span_s','clock_frequency_hz','end_s')}))
if __name__=='__main__':
    stage,case,probes=sys.argv[1:4]
    prepare(Path(case),probes,*sys.argv[4:5]) if stage=='prepare' else analyze(Path(case),probes,sys.argv[4])
