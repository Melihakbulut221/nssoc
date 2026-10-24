# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Saved full waveform diagnostic; actual source/native terminals, no native run."""
from pathlib import Path
import gzip,hashlib,json,re,os,resource
import numpy as np
os.sched_setaffinity(0,{10});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def stats(x,mask):
 v=x[mask];return dict(min=float(v.min()),max=float(v.max()),mean=float(v.mean()),rms=float(np.sqrt(np.mean(v*v))))
def edges(t,v,h):
 # Require a full negative-to-positive excursion for every diagnostic edge.
 armed=False;out=[]
 for i in range(1,len(t)):
  if v[i-1]<=-h:armed=True
  if armed and v[i-1]<=h<v[i]:
   out.append(float(t[i-1]+(h-v[i-1])*(t[i]-t[i-1])/(v[i]-v[i-1])));armed=False
 return np.array(out)
results=[];series={};maps={}
for label,stem,fixture in [('Bias8','bias8','pcie_clock_div4_v9_bias8_v1_hybrid_v1'),('Tail115','tail115','pcie_clock_div4_v10_tail115_v1_hybrid_v1')]:
 N=Path('/dev/shm/nssoc-vco-v6-divider-'+stem+'-v1-wire-06-01');F=R/'sw/tests/fixtures'/fixture
 r=json.loads((N/'result.json').read_text());assert r['status'] in ('FAIL_NATIVE_LOADED_FEEDBACK_SCREEN','PASS_NATIVE_LOADED_FEEDBACK_SCREEN')
 raw=gzip.decompress((N/'wave.raw.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==r['raw_sha256']
 header,payload=raw.split(b'Binary:\n',1);names=[x.decode().split()[1] for x in header.split(b'Variables:\n')[1].splitlines()]
 assert len(names)==957 and len(set(names))==957;size=r['rows']*957*8
 assert payload[size:]==str(r['rows']).encode()
 a=np.frombuffer(payload[:size],'<f8').reshape(r['rows'],957);assert np.isfinite(a).all();d=dict(zip(names,a.T));t=d['time'];assert np.all(np.diff(t)>0) and abs(t[-1]-34e-9)<1e-18
 for p in [F/'composition.json',F/'source-native-bijection.json']:assert r['inputs'][str(p)]==pin(p)
 comp=json.loads((F/'composition.json').read_text());binding=json.loads((F/'source-native-bijection.json').read_text())
 records={x['native_id']:x for x in comp['records']};devices={x['source_name']:x for x in binding['devices']};witness={}
 def node(name,term):
  dev=devices[name];i=dev['terminal_order'].index(term);record=records[dev['native_id']];endpoint=record['terminals'][i];assert endpoint['terminal']==term
  k='v(xchain.xdiv.'+endpoint['node'].lower()+')';assert k in d
  witness[name+'.'+term]=dict(native_id=dev['native_id'],logical=dev['source_nets'][i],column=k);return d[k]
 def current(name):
  id=devices[name]['native_id'];k=f'i(@q.xchain.xdiv.xd{int(id):04d}.qnpn13g2[ic])';assert k in d
  witness[name+'.IC']=dict(native_id=id,column=k);return d[k]
 sig={};
 for stage,prefix in [('FIRST','DIV__XFIRST__XCORE'),('SECOND','DIV__XSECOND')]:
  for latch in ('XM','XS'):
   p=prefix+'__'+latch
   ch=node(p+'__XCH','B');cs=node(p+'__XCS','B');qp=node(p+'__XDN','C');qn=node(p+'__XDP','C')
   sig[stage+'_'+latch+'_clock_cm']=(ch+cs)/2;sig[stage+'_'+latch+'_clock_diff']=ch-cs
   sig[stage+'_'+latch+'_collector_cm']=(qp+qn)/2;sig[stage+'_'+latch+'_collector_diff']=qp-qn
   sig[stage+'_'+latch+'_tail_IC']=current(p+'__XT')
   ih=current(p+'__XCH');is_=current(p+'__XCS');sig[stage+'_'+latch+'_switch_current_balance']=(ih-is_)/(ih+is_)
   sig[stage+'_'+latch+'_tail_VBE']=node(p+'__XT','B')-node(p+'__XT','E')
   sig[stage+'_'+latch+'_clock_emitter_cm']=(node(p+'__XCH','E')+node(p+'__XCS','E'))/2
 for cap in ('XCP','XCN'):
  sig[cap+'_voltage']=node('DIV__'+cap,'mim_top')-node('DIV__'+cap,'mim_btm')
 for n in ('XLP','XLN','XLT','XLREF'):
  sig[n+'_B']=node('DIV__'+n,'B');sig[n+'_C']=node('DIV__'+n,'C');sig[n+'_IC']=current('DIV__'+n)
 sig['VCO_diff']=d['v(clkp)']-d['v(clkn)'];sig['PUBLIC_diff']=d['v(qp)']-d['v(qn)']
 wins=[]
 for lo,hi in [(4,8),(12,16),(18,20),(20,22),(22,23.5),(24,26),(30,34)]:
  mask=(t>=lo*1e-9)&(t<hi*1e-9);row={'window_ns':[lo,hi],'stats':{k:stats(v,mask) for k,v in sig.items()},'crossings':{}}
  for k in ['FIRST_XS_collector_diff','SECOND_XM_collector_diff','SECOND_XS_collector_diff','PUBLIC_diff']:
   hh={}
   for h in (0,.05,.1,.15):
    e=edges(t,sig[k],h);e=e[(e>=lo*1e-9)&(e<hi*1e-9)];hh[str(h)]=dict(count=len(e),frequency_hz=float((len(e)-1)/(e[-1]-e[0])) if len(e)>1 else None)
   row['crossings'][k]=hh
  mask_delta=sig['SECOND_XM_collector_diff'][mask];slave=sig['SECOND_XS_collector_diff'][mask];row['second_master_slave_correlation']=float(np.corrcoef(mask_delta,slave)[0,1])
  wins.append(row)
 results.append({'name':label,'native_status':r['status'],'values':int(a.size),'inputs':{str(p):pin(p) for p in [N/'result.json',N/'wave.raw.gz',F/'composition.json',F/'source-native-bijection.json']},'source_terminal_witnesses':witness,'windows':wins})
 # Small plotting vectors copied before releasing full raw.
 keys=['SECOND_XS_clock_cm','XCP_voltage','XCN_voltage','SECOND_XS_tail_IC','SECOND_XS_switch_current_balance','SECOND_XS_collector_diff']
 series[label]=(t.copy(),{k:sig[k].copy() for k in keys})
 del raw,payload,a,d,sig
out={'status':'SAVED_TAIL115_CHARGE_AND_FULL_EXCURSION_DIAGNOSIS','method':pin(__file__),'captures':results,'scope':'Descriptive post-hoc windows only; each original full34ns source verdict retained unchanged. Actual capacitor terminal voltage is reported, not inferred foundry charge. Native collector currents use exact source/native device mapping. Hysteresis checks require complete +/-h excursions and distinguish voltage oscillations from tiny threshold chatter. No native rerun or relaxed screen.'}
(B/'charge-diagnosis06.json').write_text(json.dumps(out,indent=2)+'\n')
for capture in results:
 print(capture['name'])
 for w in capture['windows']:
  st=w['stats'];print(w['window_ns'], 'CM',st['SECOND_XS_clock_cm']['mean'],'cap',st['XCP_voltage']['mean'],st['XCN_voltage']['mean'],'tail',st['SECOND_XS_tail_IC']['mean'],'balance',st['SECOND_XS_switch_current_balance']['min'],st['SECOND_XS_switch_current_balance']['max'],'freq',w['crossings']['SECOND_XS_collector_diff'],'corr',w['second_master_slave_correlation'])
# Diagnostic plot; scientific artifact, no generated image editing.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(3,2,figsize=(12,10),layout='constrained')
for label,(t,sig) in series.items():
 for ax,key in zip(axes.flat,sig):
  if key=='SECOND_XS_collector_diff':
   mask=(t>=23e-9)&(t<25e-9);ax.plot(t[mask]*1e9,sig[key][mask],lw=.6,label=label)
  else:
   # 0.5ns bins, integrated sample means for readable bias envelope.
   bins=np.arange(4,34,.5);mean=[]
   for lo in bins:
    mask=(t>=lo*1e-9)&(t<(lo+.5)*1e-9);mean.append(float(np.mean(sig[key][mask])))
   ax.plot(bins+.25,mean,label=label)
  ax.set_title(key,fontsize=9);ax.set_xlabel('Time (ns)');ax.grid(alpha=.2);ax.legend()
fig.suptitle('Saved Bias8 vs Tail115: full34ns source verdicts retained')
fig.savefig(B/'charge-and-clock-diagnosis06.png',dpi=130);plt.close(fig)
