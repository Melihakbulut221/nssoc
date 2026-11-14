# SPDX-License-Identifier: Apache-2.0
"""Cloud-only fixed-phase XOR interface diagnosis; frozen acceptance reproduced."""
import copy,hashlib,json,pathlib,sys,zipfile,shutil
import numpy as np
import cdr_mos650_full650_loaded as loaded
P=pathlib.Path;variant=sys.argv[1]
configs={'bd10_lowz8_xor2_cdata3':(14112762376,'29605a3d0eda6de2a348d2619d5f009edb87594d9581883be105d03d1bd6449f'),'bd10_lowz8_xor2_cslave3':(14112317745,'e75dfba4fbd10c671f23764bd580bb5225f2fd848357e0914fb316981c5a6ab2')}
aid,digest=configs[variant];assert loaded.digest('native.zip')==digest
z=zipfile.ZipFile('native.zip')
def member(suffix):
 hits=[n for n in z.namelist() if n.endswith(suffix)];assert len(hits)==1;return hits[0]
meta=json.loads(z.read(member('derived/loaded-n1-nominal_late.json')));model=z.read(member('composition-n1/model.cir')).decode()
with z.open(member('loaded-n1-nominal_late/wave.raw')) as src,open('wave.raw','wb') as dst:shutil.copyfileobj(src,dst,1024*1024)
z.close();result=json.loads(P('result.json').read_text());assert result['variant']==variant and result['returncode']==0 and not result['passed']
assert loaded.digest('wave.raw')==result['raw']['sha256']
bound=copy.deepcopy(meta['binding'])
for name,change in result['current_density_binding_changes'].items():
 dev=bound['groups']['npn13g2'][name];assert dev['nx']==change['old_nx']
 lines=[l for l in model.splitlines() if l.split()[:1]==[change['native_id']]];assert len(lines)==1 and ('nx='+str(change['new_nx'])) in lines[0].split()
 dev['nx']=change['new_nx']
bits=meta['source_bits'];assert hashlib.sha256(bytes(bits)).hexdigest()==meta['source_bits_sha256']
t,d,info=loaded.read_streamed_wave('wave.raw',meta['vectors'],loaded.STOP,loaded.STEP)
r={}
try:loaded.measure_wave(bound,t,d,bits,meta['data_offset_s'],{},r,False,False)
except AssertionError:pass
for key in ['data_passed','devices_passed','phase_passed']:assert r[key]==result[key]
for group in ['sampler_checks','comparisons']:
 for k,value in r[group].items():
  for field in ['samples','wrong_sign_samples','below_100mv_samples','minimum_signed_margin_v','maximum_clock_to_valid_s','passed']:assert value[field]==result[group][k][field],(group,k,field)
def v(n):
 n=bound['aliases'].get(n,n);return np.zeros(len(t)) if n=='0' else d['v('+n+')']
def diff(p,n):return v(p)-v(n)
indices=np.arange(1,256);assert meta['data_offset_s']>0
current=np.array(bits)[indices];previous=np.array(bits)[indices-1]
rows=[]
for tag,pa,na,pb,nb,po,no,first in [('x','xpd.adp','xpd.adn','xpd.s0p','xpd.s0n','xp','xn',current),('y','xpd.cdp','xpd.cdn','xpd.s1p','xpd.s1n','yp','yn',previous)]:
 second=previous
 for phase in [.6,.75,.9]:
  times=loaded.START+(indices+.5+phase)*loaded.UI
  av,bv,ov=[np.interp(times,t,signal) for signal in [diff(pa,na),diff(pb,nb),diff(po,no)]]
  for a in [0,1]:
   for b in [0,1]:
    mask=(first==a)&(second==b)
    if not mask.any():continue
    actual=(av>0)^(bv>0);ideal=first^second
    strong=(abs(av)>=.1)&(abs(bv)>=.1)&mask
    signed=ov*(2*ideal-1);actual_signed=ov*(2*actual.astype(int)-1)
    def stats(x):return {str(q):float(np.percentile(x[mask],q)) for q in [0,50,100]}
    rows.append({'interface':tag,'phase_ui':phase,'expected_input_bits':[a,b],'samples':int(mask.sum()),'first_input_diff_v':stats(av),'second_input_diff_v':stats(bv),'output_diff_v':stats(ov),'output_ideal_signed_v':stats(signed),'input_sign_disagreement_with_ideal':int((((av>0)!=first)|((bv>0)!=second))[mask].sum()),'strong_input_samples':int(strong.sum()),'output_wrong_vs_simultaneous_input_xor_strong_only':int(((actual_signed<=0)&strong).sum()),'output_below_100mv_vs_simultaneous_input_xor_strong_only':int(((actual_signed<.1)&strong).sum())})

import math
logical=[]
for line in model.splitlines():
 line=line.strip()
 if not line or line.startswith('*'):continue
 if line.startswith('+'):assert logical;logical[-1]+=' '+line[1:]
 else:logical.append(line)
parent={}
def local(n):
 # Resolve logical interface names through the same native binding used by v().
 n=n.lower()
 aliases={k.lower():val.lower() for k,val in bound['aliases'].items()}
 n=aliases.get(n,aliases.get('xpd.'+n,n))
 return n[4:] if n.startswith('xpd.') else n
def find(n):
 n=local(n);parent.setdefault(n,n)
 if parent[n]!=n:parent[n]=find(parent[n])
 return parent[n]
inside=False;seen=0;wires=0
for line in logical:
 tok=line.lower().split()
 if tok[0]=='.subckt':inside=tok[1]=='nssoc_cdr650_gate_n1';seen+=int(inside)
 elif tok[0]=='.ends':inside=False
 elif inside and tok[0].startswith('r'):
  assert len(tok)==4 and math.isfinite(float(tok[3])) and float(tok[3])>=0
  parent[find(tok[1])]=find(tok[2]);wires+=1
assert seen==1 and wires>0
ports=['aqp','aqn','bqp','bqn','adp','adn','s0p','s0n','xp','xn']
port_roots={port:find(port) for port in ports}
paths={}
for output in ['adp','adn','s0p','s0n']:
 selected={};frontier={find(output)};reach=set(frontier)
 for depth in range(12):
  next_roots=set()
  for kind,group in bound['groups'].items():
   if kind=='npn13g2':terminals=[('C',0),('E',2)];inputs=[1]
   elif kind=='sg13_lv_nmos':terminals=[('D',0),('S',2)];inputs=[1]
   else:continue
   for name,dev in group.items():
    hits=[label for label,idx in terminals if find(dev['nodes'][idx]) in frontier]
    if hits:
     selected.setdefault(name,{'kind':kind,'depth':depth,'connected_output_terminals':hits,'nodes':dev['nodes'],'nx':dev.get('nx')})
     next_roots.update(find(dev['nodes'][i]) for i in inputs)
  frontier=next_roots-reach;reach.update(next_roots)
  if not frontier:break
 assert selected
 paths[output]={'devices':selected,'sampler_ports_reached':[n for n in ['aqp','aqn','bqp','bqn'] if port_roots[n] in reach],'root_count':len(reach),'unresolved_frontier':sorted(frontier)}
selected_names=sorted({n for row in paths.values() for n,dev in row['devices'].items() if dev['kind']=='npn13g2'})
phase_groups=[]
for phase in [.6,.75,.9]:
 times=loaded.START+(indices+.5+phase)*loaded.UI
 for a in [0,1]:
  for b in [0,1]:
   mask=(current==a)&(previous==b)
   if not mask.any():continue
   def stats(signal):
    values=np.interp(times[mask],t,signal);return {str(q):float(np.percentile(values,q)) for q in [0,50,100]}
   signals={label:stats(diff(pos,neg)) for label,pos,neg in [('a_sampler','xpd.aqp','xpd.aqn'),('b_sampler','xpd.bqp','xpd.bqn'),('a_data_interface','xpd.adp','xpd.adn'),('b_select_interface','xpd.s0p','xpd.s0n'),('xor_x','xp','xn')]}
   devices={}
   for name in selected_names:
    dev=bound['groups']['npn13g2'][name];vc,vb,ve,_=map(v,dev['nodes'])
    devices[name]={'collector_v':stats(vc),'base_v':stats(vb),'emitter_v':stats(ve),'vce_v':stats(vc-ve),'ic_a':stats(d['@q.'+name+'.qnpn13g2[ic]'])}
   phase_groups.append({'phase_ui':phase,'expected_a_b':[a,b],'samples':int(mask.sum()),'differentials_v':signals,'devices':devices})
out={'status':'FIXED_PHASE_PHYSICAL_BUFFER_TRACE','accepted':False,'variant':variant,'source_run':43584735530,'native_artifact':aid,'native_sha256':digest,'raw_sha256':info['raw_sha256'],'original_gates_reproduced':True,'wire_resistors_collapsed_for_connectivity_only':wires,'group_counts':{k:len(g) for k,g in bound['groups'].items()},'paths':paths,'phase_groups':phase_groups,'scope':'HBT C/E-to-base and NMOS D/S-to-gate backtrace includes feedback and shared bias branches; does not assume forward gain. All original frozen gates reproduced. Numeric wires collapsed only for reachability; measured physical-terminal waveforms retain all RC. Original phases/gates unchanged. No new simulation/layout/PHY acceptance.'}
P('out').mkdir();P('out/xor-physical-path.json').write_text(json.dumps(out,indent=2))
