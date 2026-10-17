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


r,t,signals=read('Bias8',Path('/dev/shm/nssoc-vco-v6-divider-bias8-v1-wire-06-01'),R/'sw/tests/fixtures/pcie_clock_div4_v9_bias8_v1_hybrid_v1')
windows={}
for label,lo,hi in [('early',4,20),('late',26,34)]:
 mask=(t>=lo*1e-9)&(t<=hi*1e-9);out={}
 for name,v,nodes in signals:
  ix=np.flatnonzero((v[:-1]<=0)&(v[1:]>0));edges=t[ix]+(-v[ix])*(t[ix+1]-t[ix])/(v[ix+1]-v[ix]);edges=edges[(edges>=lo*1e-9)&(edges<hi*1e-9)];periods=np.diff(edges)*1e9
  out[name]=dict(nodes=nodes,minimum_v=float(v[mask].min()),maximum_v=float(v[mask].max()),positive_edges=len(edges),crossing_times_ns=(edges*1e9).tolist(),mean_crossing_rate_hz=float((len(edges)-1)/(edges[-1]-edges[0])) if len(edges)>1 else None,period_quantiles_ns={str(q):float(np.quantile(periods,q)) for q in [0,.1,.5,.9,1]} if len(periods) else None)
 windows[label]=dict(start_ns=lo,end_ns=hi,signals=out)
fig,axes=plt.subplots(6,3,figsize=(16,14),layout='constrained')
for j,(lo,hi) in enumerate([(4,6),(21,25),(30,32)]):
 mask=(t>=lo*1e-9)&(t<=hi*1e-9)
 for i,(label,v,_) in enumerate(signals):
  ax=axes[i,j];ax.plot(t[mask]*1e9,v[mask]*1e3,lw=.8,color=['#0072B2','#D55E00','#009E73'][j]);ax.axhline(0,color='#888888',lw=.5);ax.grid(alpha=.2);ax.set_xlim(lo,hi);ax.set_title(label,fontsize=9);ax.set_ylabel('Differential mV')
  if i==0:ax.set_title(f'{lo}–{hi} ns: '+label,fontsize=10)
  if i==5:ax.set_xlabel('Time, ns')
for i in range(6):
 lo=min(ax.get_ylim()[0] for ax in axes[i,:]);hi=max(ax.get_ylim()[1] for ax in axes[i,:])
 for ax in axes[i,:]:ax.set_ylim(lo,hi)
fig.suptitle('Bias8 actual clock and latch terminals — full 34 ns division screen still FAIL',fontsize=14)
plot=O/'bias8-latch-loss-over-time.png';fig.savefig(plot,dpi=130);plt.close(fig)
x=dict(status='PASS_INDEPENDENT_BIAS8_RAW_TERMINAL_READBACK_FUNCTIONAL_FAIL_RETAINED',capture=r,diagnostic_windows=windows,method=pin(__file__),inherited_reader=pin(R/'hw/soc/out/pcie-compact-wave-root-20261006/review.py'),plot=pin(plot),scope='All saved waveform values finite and exactrawhash verified; all64HBT VCE minima independently recomputed. Exactnative/source terminalbijection selects all plottednodes. Post-hoc4–20/26–34ns windows only characterize loss; unchanged4–34ns acceptance remainsFAIL. No model/threshold change or native rerun; not independent every455device/current qualification.')
(O/'result.json').write_text(json.dumps(x,indent=2)+'\n');print([(k,{n:{kk:vv for kk,vv in s.items() if kk in ['mean_crossing_rate_hz','period_quantiles_ns','positive_edges']} for n,s in v['signals'].items()}) for k,v in windows.items()])
