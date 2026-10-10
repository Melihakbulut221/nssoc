# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independently compare actual latch terminal waveforms in two closed captures."""
from pathlib import Path
import gzip,hashlib,json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path.cwd();O=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

def read(name,root,fixture):
 r=json.loads((root/'result.json').read_text());assert r['status']=='FAIL_NATIVE_LOADED_FEEDBACK_SCREEN'
 raw=gzip.decompress((root/'wave.raw.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==r['raw_sha256']
 header,payload=raw.split(b'Binary:\n',1);assert b'Flags: real\n' in header
 n=int(re.search(rb'No\. Variables: (\d+)',header)[1]);assert n==957
 assert int(re.search(rb'No\. Points: (\d+)',header)[1])==0
 names=[]
 for line in header.split(b'Variables:\n')[1].splitlines():
  field=line.decode('ascii').split();assert len(field)==3 and int(field[0])==len(names);names.append(field[1])
 assert len(names)==len(set(names))==n
 rows,tail=divmod(len(payload),8*n);assert payload[-tail:]==str(rows).encode();assert rows==r['rows']
 a=np.frombuffer(payload[:rows*n*8],dtype='<f8').reshape(rows,n);assert np.isfinite(a).all() and rows*n==r['values']
 col={k:a[:,i] for i,k in enumerate(names)};t=col['time'];assert np.all(np.diff(t)>0) and abs(t[-1]-34e-9)<1e-18
 mask=(t>=4e-9)&(t<=34e-9);hbt=[]
 for dev in r['devices']:
  if dev['model']!='npn13g2':continue
  c,b,e,_=dev['nets'];vc=col['v('+c+')'] if c!='0' else np.zeros(rows);ve=col['v('+e+')'] if e!='0' else np.zeros(rows)
  vce=vc-ve;low=float(vce[mask].min());saved=next(x for x in r['safety']['all_device_bounds'] if x['path']==dev['path']);assert abs(low-saved['min_settled_vce'])<1e-12
  hbt.append(dict(path=dev['path'],minimum_vce=low))
 assert len(hbt)==64 and all(x['minimum_vce']>=.4 for x in hbt)
 cpath=fixture/'composition.json';bpath=fixture/'source-native-bijection.json'
 for p in [cpath,bpath]:assert pin(p)==r['inputs'][str(p)]
 composition=json.loads(cpath.read_text());binding=json.loads(bpath.read_text());records={x['native_id']:x for x in composition['records']};devices={x['source_name']:x for x in binding['devices']};assert len(records)==len(devices)==91
 def endpoint(name,terminal):
  d=devices[name];i=d['terminal_order'].index(terminal);node=records[d['native_id']]['terminals'][i]['node'].lower();k='v(xchain.xdiv.'+node+')';assert k in col
  return k,dict(source_device=name,terminal=terminal,logical=d['source_nets'][i],native_id=d['native_id'],node=k)
 def diff(label,a,ta,b,tb):
  ka,ra=endpoint(a,ta);kb,rb=endpoint(b,tb);return (label,col[ka]-col[kb],[ra,rb])
 signals=[('VCO source',col['v(clkp)']-col['v(clkn)'],['v(clkp)','v(clkn)']),
 diff('First latch slave collector /2','DIV__XFIRST__XCORE__XS__XDN','C','DIV__XFIRST__XCORE__XS__XDP','C'),
 diff('Second latch MASTER clock bases','DIV__XSECOND__XM__XCH','B','DIV__XSECOND__XM__XCS','B'),
 diff('Second latch SLAVE clock bases','DIV__XSECOND__XS__XCS','B','DIV__XSECOND__XS__XCH','B'),
 diff('Second latch MASTER collectors','DIV__XSECOND__XM__XDN','C','DIV__XSECOND__XM__XDP','C'),
 diff('Second latch SLAVE collectors','DIV__XSECOND__XS__XDN','C','DIV__XSECOND__XS__XDP','C')]
 summary={}
 for label,v,nodes in signals:
  ix=np.flatnonzero((v[:-1]<=0)&(v[1:]>0));edges=t[ix]+(-v[ix])*(t[ix+1]-t[ix])/(v[ix+1]-v[ix]);edges=edges[(edges>=4e-9)&(edges<34e-9)]
  summary[label]=dict(nodes=nodes,minimum_v=float(v[mask].min()),maximum_v=float(v[mask].max()),positive_edges=len(edges),frequency_hz=float((len(edges)-1)/(edges[-1]-edges[0])) if len(edges)>1 else None)
 return dict(name=name,rows=rows,columns=n,values=rows*n,minimum_hbt_vce=min(x['minimum_vce'] for x in hbt),all64_HBT_bounds_recomputed=hbt,signals=summary,result=pin(root/'result.json'),raw=pin(root/'wave.raw.gz'),composition=pin(cpath),binding=pin(bpath)),t,signals

results=[];wave=[]
for name,capture,fixture in [('PowerV2','nssoc-vco-v6-divider-power-v2-wire-06-01','pcie_clock_div4_v7_power_v2_hybrid_v1'),('CompactV2','nssoc-vco-v6-divider-compact-v2-wire-06-01','pcie_clock_div4_v7_compact_v2_hybrid_v1')]:
 r,t,signals=read(name,Path('/dev/shm')/capture,R/'sw/tests/fixtures'/fixture);results.append(r);wave.append((t,signals))
fig,axes=plt.subplots(6,2,figsize=(13,13),sharex=True,layout='constrained')
for j,(t,signals) in enumerate(wave):
 mask=(t>=20e-9)&(t<=22e-9)
 for i,(label,v,_) in enumerate(signals):
  ax=axes[i,j];ax.plot(t[mask]*1e9,v[mask]*1e3,lw=1,color=['#0072B2','#D55E00'][j]);ax.axhline(0,color='#888888',lw=.6);ax.grid(alpha=.2);ax.set_xlim(20,22)
  ax.set_title(label,fontsize=9);ax.set_ylabel('Differential mV');
  if i==0:ax.set_title(results[j]['name']+' — '+label,fontsize=11)
 for ax in axes[-1,:]:ax.set_xlabel('Time, ns')
for i in range(6):
 lo=min(axes[i,0].get_ylim()[0],axes[i,1].get_ylim()[0]);hi=max(axes[i,0].get_ylim()[1],axes[i,1].get_ylim()[1]);axes[i,0].set_ylim(lo,hi);axes[i,1].set_ylim(lo,hi)
fig.suptitle('Actual clock-base and collector terminals: divider still fails',fontsize=14)
plot=O/'actual-latch-clock-comparison.png';fig.savefig(plot,dpi=150);plt.close(fig)
r=dict(status='PASS_INDEPENDENT_RAW_TERMINAL_READBACK_BOTH_DIVIDER_FAILURES_RETAINED',captures=results,method=pin(__file__),plot=pin(plot),scope='Allvaluesfinite, rawhashes andall64HBTbounds checked in eachcapture. Signalpairs selectedbyactualintrinsicdevice+terminal, notarbitrary samenetwitness; exactbindings recorded. No simulation, model or thresholds changed. Doesnot independently requalify everycurrent/MOSscreen orqualifiedRC.')
(O/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps([dict(name=x['name'],minimum_hbt_vce=x['minimum_hbt_vce'],signals=x['signals']) for x in results],indent=2))
