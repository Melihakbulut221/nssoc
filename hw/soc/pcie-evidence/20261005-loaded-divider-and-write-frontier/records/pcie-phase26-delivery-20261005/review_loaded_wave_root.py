# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent binary-table readback and plotted observations, no simulation."""
from pathlib import Path
import gzip,hashlib,json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path.cwd();B=Path(__file__).resolve().parent;P=Path('/dev/shm/nssoc-vco-v6-divider-wire-06-01');C=R/'hw/soc/pcie-evidence/20261005-loaded-divider-and-write-frontier'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
result=json.loads((P/'result.json').read_text());assert result['status']=='FAIL_NATIVE_LOADED_FEEDBACK_SCREEN'
raw=gzip.decompress((P/'wave.raw.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==result['raw_sha256']
head,blob=raw.split(b'Binary:\n',1);assert head.count(b'Variables:\n')==1 and b'Flags: real\n' in head
n=int(re.search(rb'No\. Variables: (\d+)',head)[1]);declared=int(re.search(rb'No\. Points: (\d+)',head)[1]);assert n==957 and declared==0
fields=[]
for line in head.split(b'Variables:\n',1)[1].splitlines():
 row=line.decode('ascii').split();assert int(row[0])==len(fields) and len(row)==3;fields.append(row[1])
assert len(fields)==len(set(fields))==n
rows,trailer=divmod(len(blob),8*n);assert blob[-trailer:]==str(rows).encode() and rows==6817
values=np.frombuffer(blob[:rows*n*8],dtype='<f8').reshape(rows,n);assert np.isfinite(values).all()
assert rows*n==result['values']==6523869
columns={name:values[:,i] for i,name in enumerate(fields)};t=columns['time'];assert np.all(np.diff(t)>0) and abs(t[-1]-34e-9)<1e-18
window=(t>=4e-9)&(t<=34e-9);assert window.any()
# Compute every HBT voltage headroom directly from physical terminal voltages.
hbt=[]
for device in result['devices']:
 if device['model']!='npn13g2':continue
 c,b,e,_=device['nets'];vc=columns['v('+c+')'] if c!='0' else np.zeros(rows);ve=columns['v('+e+')'] if e!='0' else np.zeros(rows)
 vce=vc-ve;minimum=float(vce[window].min());hbt.append(dict(path=device['path'],minimum_settled_vce=minimum))
 saved=next(row for row in result['safety']['all_device_bounds'] if row['path']==device['path'])
 assert abs(minimum-saved['min_settled_vce'])<1e-12
bad=[row for row in hbt if row['minimum_settled_vce']<.4]
assert len(bad)==4 and {row['path'] for row in bad}=={row['path'] for row in result['safety']['all_device_bounds'] if not row['passed']}
fixture=R/'sw/tests/fixtures/pcie_clock_div4_v7_hybrid_v1';composition=json.loads((fixture/'composition.json').read_text());binding=json.loads((fixture/'source-native-bijection.json').read_text());records={row['native_id']:row for row in composition['records']};assert len(records)==91
nets={}
for device in binding['devices']:
 native=records[device['native_id']]
 for logical,terminal in zip(device['source_nets'],native['terminals'],strict=True):
  if terminal['node']=='BODY_SUBSTRATE':continue
  net='v(xchain.xdiv.'+terminal['node'].lower()+')';assert net in columns;nets.setdefault(logical,set()).add(net)
rail={}
for logical in ['AVSS','DIV_AVDD']:
 data=np.stack([columns[name] for name in sorted(nets[logical])]);rail[logical]=data
rail_summary={name:dict(terminals=len(nets[name]),minimum=float(v[:,window].min()),maximum=float(v[:,window].max()),max_simultaneous_span=float((v.max(axis=0)-v.min(axis=0))[window].max())) for name,v in rail.items()}
delta=columns['v(clkp)']-columns['v(clkn)'];ix=np.flatnonzero((delta[:-1]<=0)&(delta[1:]>0));cross=t[ix]+(-delta[ix])*(t[ix+1]-t[ix])/(delta[ix+1]-delta[ix]);cross=cross[(cross>=4e-9)&(cross<34e-9)];frequency=float((len(cross)-1)/(cross[-1]-cross[0]));assert abs(frequency-8102380710.362595)<1
sel=(t>=20e-9)&(t<=22e-9);ns=t[sel]*1e9
fig,axs=plt.subplots(4,1,figsize=(11,9),sharex=True,layout='constrained')
fig.suptitle('Loaded VCO and divider: measured wire-RC failure',fontsize=15)
axs[0].plot(ns,delta[sel]*1000,label='VCO 8.102 GHz',color='#0072B2',lw=1.3)
axs[0].plot(ns,(columns['v(xchain.xdiv.w_t0012)']-columns['v(xchain.xdiv.w_t0013)'])[sel]*1000,label='First /2 output',color='#E69F00',lw=1.3)
axs[0].set_ylabel('Differential (mV)');axs[0].legend(loc='upper right',ncol=2,fontsize=9)
axs[1].plot(ns,(columns['v(xchain.xdiv.w_t0081)']-columns['v(xchain.xdiv.w_t0077)'])[sel]*1000,label='Second-stage clock',color='#009E73',lw=1.3)
axs[1].plot(ns,(columns['v(qp)']-columns['v(qn)'])[sel]*1000,label='Divider output (incorrect /4)',color='#CC79A7',lw=1.3)
axs[1].set_ylabel('Differential (mV)');axs[1].legend(loc='upper right',ncol=2,fontsize=9)
for name,colour,label in [('AVSS','#D55E00','Local ground rise'),('DIV_AVDD','#0072B2','Local supply drop from 2.5 V')]:
 data=rail[name] if name=='AVSS' else 2.5-rail[name]
 axs[2].fill_between(ns,data.min(axis=0)[sel],data.max(axis=0)[sel],color=colour,alpha=.25,label=label)
 axs[2].plot(ns,data.max(axis=0)[sel],color=colour,lw=1)
axs[2].set_ylabel('Rail error (V)');axs[2].legend(loc='upper right',ncol=2,fontsize=9)
for row,colour in zip(bad,['#0072B2','#E69F00','#009E73','#CC79A7'],strict=True):
 device=next(d for d in result['devices'] if d['path']==row['path']);c,_,e,_=device['nets'];vce=columns['v('+c+')']-columns['v('+e+')'];axs[3].plot(ns,vce[sel],color=colour,lw=1.2,label=row['path'].split('.')[-1])
axs[3].axhline(.4,color='#555555',ls='--',lw=1,label='Declared 0.4 V screen');axs[3].set_ylabel('HBT VCE (V)');axs[3].set_xlabel('Time (ns)');axs[3].legend(loc='upper right',ncol=5,fontsize=8)
for ax in axs:ax.grid(alpha=.2);ax.set_xlim(20,22)
fig.text(.02,-.015,'Nominal model, VCTRL 0.6 V. Existing device screens unchanged. Two block wire models; ideal inter-block links and body boundaries.',fontsize=9)
figpath=C/'figures/loaded455-waveforms.png';figpath.parent.mkdir(parents=True,exist_ok=True);fig.savefig(figpath,dpi=160,bbox_inches='tight');plt.close(fig)
r=dict(status='PASS_INDEPENDENT_RAW_READBACK_CONFIRMS_FOUR_HBT_HEADROOM_FAILURES',raw_sha256=result['raw_sha256'],compressed=pin(P/'wave.raw.gz'),samples=rows,columns=n,values=rows*n,finite_values=True,strictly_increasing_time=True,HBT_voltage_bounds_recomputed=len(hbt),headroom_below_point4=bad,rails=rail_summary,vco_frequency_hz=frequency,method=pin(__file__),source_result=pin(P/'result.json'),composition=pin(fixture/'composition.json'),binding=pin(fixture/'source-native-bijection.json'),plot=pin(figpath),scope='Independent raw binary reader; all values scanned, every HBT VCE recalculated. Plot is a saved 20-22ns slice, not new simulation. Does not independently recalculate every MOS/current screen or qualify RC/body/inter-block wiring.')
(B/'root-loaded-wave-review.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
