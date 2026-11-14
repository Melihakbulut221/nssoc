# SPDX-License-Identifier: Apache-2.0
"""Cloud-only fixed-phase XOR interface diagnosis; frozen acceptance reproduced."""
import copy,hashlib,json,pathlib,sys,zipfile,shutil
import numpy as np
import cdr_mos650_full650_loaded as loaded
P=pathlib.Path;variant=sys.argv[1]
configs={'bd10_lowz8_xor2_cdata3':(14112762376,'29605a3d0eda6de2a348d2619d5f009edb87594d9581883be105d03d1bd6449f'),'bd10_lowz8_xor2_cslave3':(14112317745,'e75dfba4fbd10c671f23764bd580bb5225f2fd848357e0914fb316981c5a6ab2')}
configs['bd10_lowz8_xor2_cdata3_sel15']=(14116918270,'2f2dd3cffcadde6e7111065c3e5c79580ec245f5bffa14a54116cb66c6587868')
configs['bd10_lowz8_xor1_cdata3_sel15']=(14121577984,'d5e62c25486ba447781a5e4cdc12c00b303e890fb3cb51de1c8cdf77f32d1615')
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
 for phase in [.1,.2,.3,.4,.49,.51,.6,.75,.9]:
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
rail_roots={find(n) for n in ['avdd','avss','vdd','vss','0']}
paths={}
for output in ['adp','adn','s0p','s0n']:
 selected={};frontier={find(output)};reach=set(frontier)
 for depth in range(12):
  next_roots=set()
  for name,dev in bound['groups']['rppd'].items():
   # Trace both physical resistor terminals without shorting them in measurement.
   ends=[find(n) for n in dev['nodes'][:2]]
   if any(n in frontier for n in ends):
    selected.setdefault(name,{'kind':'rppd','depth':depth,'nodes':dev['nodes']})
    next_roots.update(ends)
  for kind,group in bound['groups'].items():
   if kind=='npn13g2':terminals=[('C',0),('E',2)];inputs=[1]
   elif kind=='sg13_lv_nmos':terminals=[('D',0),('S',2)];inputs=[1]
   else:continue
   for name,dev in group.items():
    hits=[label for label,idx in terminals if find(dev['nodes'][idx]) in frontier]
    if hits:
     selected.setdefault(name,{'kind':kind,'depth':depth,'connected_output_terminals':hits,'nodes':dev['nodes'],'nx':dev.get('nx')})
     next_roots.update(find(dev['nodes'][i]) for i in inputs)
  frontier=next_roots-reach-rail_roots;reach.update(next_roots-rail_roots)
  if not frontier:break
 assert selected
 paths[output]={'devices':selected,'sampler_ports_reached':[n for n in ['aqp','aqn','bqp','bqn'] if port_roots[n] in reach],'root_count':len(reach),'unresolved_frontier':sorted(frontier)}
selected_names=sorted({n for row in paths.values() for n,dev in row['devices'].items() if dev['kind']=='npn13g2'})
phase_groups=[]
for phase in [.1,.2,.3,.4,.49,.51,.6,.75,.9]:
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
out={'status':'FIXED_PHASE_PHYSICAL_BUFFER_TRACE','accepted':False,'variant':variant,'source_run':43603972722 if variant=='bd10_lowz8_xor1_cdata3_sel15' else (43596398222 if variant.endswith('_sel15') else 43584735530),'native_artifact':aid,'native_sha256':digest,'raw_sha256':info['raw_sha256'],'original_gates_reproduced':True,'wire_resistors_collapsed_for_connectivity_only':wires,'group_counts':{k:len(g) for k,g in bound['groups'].items()},'paths':paths,'phase_groups':phase_groups,'interface_truth_rows':rows,'scope':'HBT C/E-to-base, NMOS D/S-to-gate and two-terminal rppd resistor reachability, stopping at supply rails. Includes feedback and shared bias branches; does not assume forward gain. All original frozen gates reproduced. Numeric wires collapsed only for reachability; measured physical-terminal waveforms retain all RC. Original phases/gates unchanged. No new simulation/layout/PHY acceptance.'}
# Preserve exact failed HBT criteria and the actual extrema times. A
# startup peak is not interchangeable with active-window headroom failure.
failed={}
for name in result['failing_hbt']:
 dev=bound['groups']['npn13g2'][name];vc,vb,ve,_=map(v,dev['nodes'])
 ic=d['@q.'+name+'.qnpn13g2[ic]'];active=np.flatnonzero(t>=loaded.START)
 series={'minimum_active_vce_v':(vc-ve,active,False),'maximum_alltime_abs_vce_v':(abs(vc-ve),np.arange(len(t)),True),'maximum_alltime_abs_vbe_v':(abs(vb-ve),np.arange(len(t)),True),'maximum_alltime_abs_ic_per_emitter_a':(abs(ic)/dev['nx'],np.arange(len(t)),True)}
 extrema={}
 for label,(values,ids,maximum) in series.items():
  k=ids[int(np.argmax(values[ids]) if maximum else np.argmin(values[ids]))]
  extrema[label]={'value':float(values[k]),'time_s':float(t[k]),'collector_v':float(vc[k]),'base_v':float(vb[k]),'emitter_v':float(ve[k]),'collector_current_a':float(ic[k])}
  assert abs(extrema[label]['value']-r['device_checks'][name][label])<1e-14
 native_id=name.split('.')[-1].upper();records=[line for line in logical if line.split()[0].upper()==native_id];assert len(records)==1
 failed[name]={'native_record':records[0],'nx':dev['nx'],'nodes':dev['nodes'],'checks':r['device_checks'][name],'extrema':extrema}
assert set(failed)==set(result['failing_hbt'])
out['failing_hbt_exact_criteria']=failed
# Audit observation times independently of the frozen pass/fail oracle.
# No expected-bit or electrical acceptance rule is modified here.
clock_aliases={k:n for k,n in bound['aliases'].items() if any(token in k.lower() for token in ('clk','clock','ckp','ckn'))}
clock_vectors={k:n for k,n in clock_aliases.items() if 'v('+n+')' in d}
clock_rows=[]
for phase in [0,.1,.4,.49,.51,.6,.75,.9]:
 times=loaded.START+(indices+.5+phase)*loaded.UI
 row={'phase_after_rising_ui':phase,'relative_to_next_falling_ui':phase-.5,'source_clock_levels_v':{},'sampler_b_sign_agreement':{}}
 for alias,n in clock_vectors.items():
  values=np.interp(times,t,d['v('+n+')']);row['source_clock_levels_v'][alias]={'minimum':float(values.min()),'median':float(np.median(values)),'maximum':float(values.max())}
 bv=np.interp(times,t,diff('xpd.bqp','xpd.bqn'))
 changed=current!=previous
 row['sampler_b_sign_agreement']={'transition_samples':int(changed.sum()),'with_previous_bit':int(((bv>0)==previous)[changed].sum()),'with_current_bit':int(((bv>0)==current)[changed].sum()),'weak_under_100mv':int((abs(bv)<.1)[changed].sum())}
 clock_rows.append(row)
out['observation_schedule_audit']={'clock_generator_contract':'loaded.clock: rising START+(i+.5)*UI, falling START+(i+1)*UI, finite 5ps transition','unchanged_original_xor_sample_phases_ui':[.6,.75,.9],'clock_aliases':clock_aliases,'available_clock_vectors':clock_vectors,'rows':clock_rows,'model_subcircuit_headers':[line for line in logical if line.lower().startswith('.subckt ')],'acceptance_changed':False,'requires_physical_topology_interpretation':True}
# Actual clock-connected transistor bases, not guessed friendly aliases.
clock_bases={}
for name,dev in bound['groups']['npn13g2'].items():
 for port in ['cp','cn']:
  if find(dev['nodes'][1])==find(port):
   node=bound['aliases'].get(dev['nodes'][1],dev['nodes'][1])
   if 'v('+node+')' in d:clock_bases[name]={'clock_port':port,'base_node':node}
assert clock_bases,'No observed physical clock-connected HBT bases'
clock_samples=[]
for phase in [0,.1,.4,.49,.51,.6,.75,.9]:
 times=loaded.START+(indices+.5+phase)*loaded.UI
 row={'phase_ui':phase,'devices':{}}
 for name,dev in clock_bases.items():
  values=np.interp(times,t,d['v('+dev['base_node']+')'])
  row['devices'][name]={'clock_port':dev['clock_port'],'minimum_v':float(values.min()),'median_v':float(np.median(values)),'maximum_v':float(values.max())}
 clock_samples.append(row)
out['physical_clock_base_observations']={'bases':clock_bases,'samples':clock_samples,'wire_connectivity_only':True}
# Expand only native passive gp_* subcircuits. Semiconductor and PDK resistor
# models remain devices. Incident capacitance is not a grounded RC pole.
import re
subcircuits={};current_sub=None
for line in logical:
 tok=line.lower().split()
 if tok[0]=='.subckt':
  assert tok[1] not in subcircuits;current_sub=tok[1];subcircuits[current_sub]={'ports':tok[2:],'rows':[]}
 elif tok[0]=='.ends':current_sub=None
 elif current_sub:subcircuits[current_sub]['rows'].append(tok)
def scalar(value):
 match=re.fullmatch(r'([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:e[+-]?[0-9]+)?)(meg|[tgkmunpf]?)',value)
 assert match,value
 factor={'':1.,'t':1e12,'g':1e9,'meg':1e6,'k':1e3,'m':1e-3,'u':1e-6,'n':1e-9,'p':1e-12,'f':1e-15}[match[2]]
 value=float(match[1])*factor;assert math.isfinite(value) and value>=0;return value
resistors=[];capacitors=[];expanded=[]
def expand(name,ports,prefix,depth=0):
 assert depth<10
 sub=subcircuits[name];assert len(ports)==len(sub['ports'])
 pins=dict(zip(sub['ports'],ports));assert len(pins)==len(ports)
 def node(n):return '0' if n=='0' else pins.get(n,prefix+n)
 for row in sub['rows']:
  if row[0].startswith(('r','c')):
   assert len(row)==4,row
   item={'name':prefix+row[0],'nodes':[node(row[1]),node(row[2])],'value':scalar(row[3])}
   (resistors if row[0].startswith('r') else capacitors).append(item)
  elif row[0].startswith('x') and row[-1].startswith('gp_'):
   assert row[-1] in subcircuits
   expanded.append(prefix+row[0]);expand(row[-1],[node(n) for n in row[1:-1]],prefix+row[0]+'.',depth+1)
name='nssoc_cdr650_gate_n1';expand(name,subcircuits[name]['ports'],'')
assert expanded and capacitors and resistors
assert len({x['name'] for x in resistors+capacitors})==len(resistors)+len(capacitors)
parents={}
def root(n):
 n=local(n);parents.setdefault(n,n)
 if parents[n]!=n:parents[n]=root(parents[n])
 return parents[n]
for row in resistors:parents[root(row['nodes'][0])]=root(row['nodes'][1])
loads={}
for port in ['aqp','aqn','adp','adn','bqp','bqn','s0p','s0n','cdp','cdn','s1p','s1n']:
 target=root(port);caps=[row for row in capacitors if (root(row['nodes'][0])==target) != (root(row['nodes'][1])==target)]
 devices={}
 for kind,group in bound['groups'].items():
  for name,dev in group.items():
   touched=[i for i,n in enumerate(dev['nodes']) if root(n)==target]
   if touched:devices[name]={'kind':kind,'terminal_indices':touched,'nodes':dev['nodes'],'nx':dev.get('nx')}
 loads[port]={'incident_explicit_capacitance_f':sum(x['value'] for x in caps),'incident_capacitor_count':len(caps),'largest_incident_caps':sorted(caps,key=lambda x:x['value'],reverse=True)[:12],'connected_devices':devices}
out['passive_load_inventory']={'expanded_passive_instances':len(expanded),'explicit_capacitors':len(capacitors),'numeric_wire_resistors':len(resistors),'ports':loads,'scope':'All explicitly numeric C and R in top and recursively expanded gp_* subcircuits. PDK device intrinsic capacitance is excluded; coupling is not treated as ground. Wire R collapsed only for connectivity, not electrical measurement.'}
# Identify buffer inputs without walking backwards through active latches.
# Traverse only PDK resistor divider edges, stopping at every sampler port
# and supply. This distinguishes raw B from retimed D explicitly.
from collections import defaultdict,deque
adj=defaultdict(list)
for name,dev in bound['groups']['rppd'].items():
 a,b=map(root,dev['nodes'][:2]);adj[a].append((b,name));adj[b].append((a,name))
sampler_ports=[tag+'q'+pol for tag in 'abcd' for pol in 'pn']
sampler_roots=defaultdict(list)
for name in sampler_ports:sampler_roots[root(name)].append(name)
rails={root(name) for name in ['avdd','avss','vdd','vss','0','sub','body_1']}
traces={}
for output in ['adp','adn','cdp','cdn','s0p','s0n','s1p','s1n']:
 drivers={name:dev for name,dev in bound['groups']['npn13g2'].items() if root(dev['nodes'][0])==root(output)}
 assert drivers,output
 traces[output]={}
 for name,dev in drivers.items():
  start=root(dev['nodes'][1]);queue=deque([(start,[])]);seen={start};hits={}
  while queue:
   node,path=queue.popleft()
   if node in sampler_roots:
    for sampler in sampler_roots[node]:hits[sampler]=path
    continue
   if node in rails:continue
   for nxt,resistor in adj[node]:
    if nxt not in seen:seen.add(nxt);queue.append((nxt,path+[resistor]))
  assert hits,(output,name,'No sampler through input divider')
  traces[output][name]={'base_node':dev['nodes'][1],'sampler_ports_through_resistors_only':hits,'semiconductor_edges_traversed':0}
out['buffer_input_sampler_binding']=traces
sampler_rows=[]
for phase in [.1,.3,.49,.6,.75,.9]:
 times=loaded.START+(indices+.5+phase)*loaded.UI
 for a,b in [(0,1),(1,0)]:
  mask=(current==a)&(previous==b);row={'phase_ui':phase,'current_previous':[a,b],'samplers':{}}
  for tag in 'abcd':
   values=np.interp(times,t,diff('xpd.'+tag+'qp','xpd.'+tag+'qn'))[mask]
   row['samplers'][tag]={'minimum_v':float(values.min()),'median_v':float(np.median(values)),'maximum_v':float(values.max())}
  sampler_rows.append(row)
out['all_sampler_transition_rows']=sampler_rows
out['native_metadata_keys']=sorted(meta)
out['native_metadata_provenance']={k:value for k,value in meta.items() if any(word in k for word in ['source','sha','file']) and isinstance(value,(str,int,float,bool))}
with zipfile.ZipFile('native.zip') as archive:
 out['native_report_member_names']=[n for n in archive.namelist() if n.endswith(('.json','.cir','.gds','.spice'))]
P('out').mkdir();P('out/xor-physical-path.json').write_text(json.dumps(out,indent=2))
