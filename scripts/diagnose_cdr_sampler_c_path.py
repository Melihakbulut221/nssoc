# SPDX-License-Identifier: Apache-2.0
"""Cloud-only full saved-waveform device and bit-history diagnosis, no new acceptance."""
import copy,hashlib,json,pathlib,sys,zipfile
import numpy as np
import cdr_mos650_full650_loaded as loaded
from cdr_n1_divider_whatif import XOR_DATA
P=pathlib.Path
variant=sys.argv[1]
configs={
 'bd10_lowz8_xor2_acload12':(14107240670,'a4f8b266f11b0a48d7bda855c8a6d69933d6ea2933be82f2ec200a89925eb3d5'),
 'bd10_lowz8_xor2_acload16':(14107159021,'5dbfa37bb7560c8b363f6edf179e098c4e2469281b797aba3d0486ebcc389dcc')}
# Hashes bind the completed source run, never latest artifact by name.
aid,digest=configs[variant]
assert loaded.digest('native.zip')==digest
z=zipfile.ZipFile('native.zip')
def member(suffix):
 hits=[n for n in z.namelist() if n.endswith(suffix)];assert len(hits)==1,(suffix,hits);return hits[0]
meta=json.loads(z.read(member('derived/loaded-n1-nominal_late.json')))
model=z.read(member('composition-n1/model.cir')).decode()
wave=member('loaded-n1-nominal_late/wave.raw')
with z.open(wave) as src,open('wave.raw','wb') as dst:
 import shutil
 shutil.copyfileobj(src,dst,1024*1024)
z.close()
result=json.loads(P('result.json').read_bytes());assert result['variant']==variant and result['returncode']==0 and not result['passed']
assert loaded.digest('wave.raw')==result['raw']['sha256']
bound=copy.deepcopy(meta['binding'])
for native_id in XOR_DATA:
 marker='w_t'+native_id[3:]+'_b'
 hits=[(n,d) for n,d in bound['groups']['npn13g2'].items() if d['nodes'][1].lower().rsplit('.',1)[-1]==marker];assert len(hits)==1
 name,dev=hits[0];assert dev['nx']==4
 lines=[l for l in model.splitlines() if l.split()[:1]==[native_id]];assert len(lines)==1 and 'nx=2' in lines[0].split()
 assert result['current_density_binding_changes'][name]==dict(native_id=native_id,old_nx=4,new_nx=2)
 dev['nx']=2
bits=meta['source_bits'];assert hashlib.sha256(bytes(bits)).hexdigest()==meta['source_bits_sha256']
t,d,info=loaded.read_streamed_wave('wave.raw',meta['vectors'],loaded.STOP,loaded.STEP)
r={}
try:loaded.measure_wave(bound,t,d,bits,meta['data_offset_s'],{},r,False,False)
except AssertionError:pass
for key in ['data_passed','devices_passed','phase_passed']:
 assert r[key]==result[key],(key,r.get(key),result[key])
for group in ['sampler_checks','comparisons']:
 for k,value in r[group].items():
  for field in ['samples','wrong_sign_samples','below_100mv_samples','minimum_signed_margin_v','maximum_clock_to_valid_s','passed']:
   assert value[field]==result[group][k][field],(group,k,field)
active=t>=loaded.START
limits={'minimum_active_vce_v':(.4,'min'), 'maximum_alltime_abs_vce_v':(1.6,'max'), 'maximum_alltime_abs_vbe_v':(1.,'max'), 'maximum_alltime_abs_ic_per_emitter_a':(.003,'max_inclusive')}
def voltage(n):
 n=bound['aliases'].get(n,n)
 return np.zeros(len(t)) if n=='0' else d['v('+n+')']
failures={}
for name,checks in r['device_checks'].items():
 reasons={k:{'value':v,'limit':limits[k][0]} for k,v in checks.items() if (v<limits[k][0] if limits[k][1]=='min' else v>=limits[k][0] if limits[k][1]=='max_inclusive' else v>limits[k][0])}
 if reasons:
  dev=bound['groups']['npn13g2'][name];vc,vb,ve,_=map(voltage,dev['nodes'])
  values={'minimum_active_vce_v':np.where(active,vc-ve,np.inf),'maximum_alltime_abs_vce_v':abs(vc-ve),'maximum_alltime_abs_vbe_v':abs(vb-ve),'maximum_alltime_abs_ic_per_emitter_a':abs(d['@q.'+name+'.qnpn13g2[ic]'])/dev['nx']}
  for key in reasons:
   j=int(np.argmin(values[key]) if key=='minimum_active_vce_v' else np.argmax(values[key]));reasons[key].update(time_s=float(t[j]),collector_v=float(vc[j]),base_v=float(vb[j]),emitter_v=float(ve[j]),during_startup=bool(t[j]<loaded.START))
  failures[name]={'nx':dev['nx'],'violations':reasons}
assert set(failures)==set(result['failing_hbt'])
# Preserve original rising-edge sample times and expected values. Group history,
# not optimize alignment or reinterpret failing samples as passes.
history=[]
for tag in 'acd':
 diff=voltage('xpd.'+tag+'qp')-voltage('xpd.'+tag+'qn')
 for code in range(16):
  pattern=[(code>>j)&1 for j in (3,2,1,0)]
  ids=[i for i in range(2,255) if bits[i-2:i+2]==pattern]
  if not ids:continue
  samples=[]
  for i in ids:
   expect=bits[i] if tag=='a' else bits[i-1]
   samples.extend(float(np.interp(loaded.START+(i+.5+phase)*loaded.UI,t,diff))*(2*expect-1) for phase in [.3,.6,.9])
  history.append({'signal':tag,'bits_kminus2_to_kplus1':pattern,'bit_count':len(ids),'samples':len(samples),'wrong_sign':sum(v<=0 for v in samples),'below_100mv':sum(v<.1 for v in samples),'min_signed_margin_v':min(samples)})
out={'status':'EXACT_NATIVE_FAILURE_DIAGNOSIS_ONLY','accepted':False,'new_simulation':False,'new_layout':False,'variant':variant,'source_run':43571075470,'native_artifact_id':aid,'native_artifact_sha256':digest,'raw_sha256':info['raw_sha256'],'original_gate_reproduction':True,'device_failures':failures,'history_groups':history,'scope':'Full original transient and unchanged sampler/device gates. History groups exclude edge bits and are diagnostic only. No claimed measured internal clock timing, closed-loop CDR, PHY acceptance or manufacturing qualification.'}
# Detect actual clock ports from the frozen bench contract, not name heuristics.
clock={"scope":"Receiver cp/cn physical port voltages only; not recovered-clock closed-loop proof", "old_clk_name_filter_is_incomplete":True}
clock['bound_ports']=bound['ports']
clock['voltage_keys']={n:'v('+bound['aliases'].get(n,n)+')' for n in ['cp','cn']}
clock['available']={n:key in d for n,key in clock['voltage_keys'].items()}
if all(clock['available'].values()):
 cp,cn=voltage('cp'),voltage('cn');diff=cp-cn
 clock['active_differential_range_v']=[float(diff[active].min()),float(diff[active].max())]
 clock['active_commonmode_range_v']=[float(((cp+cn)/2)[active].min()),float(((cp+cn)/2)[active].max())]
 for direction in ['rising','falling']:
  hit=np.flatnonzero((diff[:-1]<0)&(diff[1:]>=0) if direction=='rising' else (diff[:-1]>0)&(diff[1:]<=0))
  times=t[hit]+(-diff[hit])*(t[hit+1]-t[hit])/(diff[hit+1]-diff[hit]);times=times[(times>=loaded.START)&(times<=loaded.STOP)]
  # Compare with the exact frozen ideal drive schedule, never move sampling.
  expected=np.array([loaded.START+(i+(.5 if direction=='rising' else 1))*loaded.UI for i in range(258)])
  expected=expected[expected+2.5e-12<loaded.STOP]
  delta=times-expected if len(times)==len(expected) else None
  clock[direction]={'observed_edges':len(times),'expected_edges':len(expected),'first_edge_s':float(times[0]) if len(times) else None,'last_edge_s':float(times[-1]) if len(times) else None,'edge_error_ps':{'min':float(delta.min()*1e12),'max':float(delta.max()*1e12)} if delta is not None else None,'period_ps_range':[float(np.diff(times).min()*1e12),float(np.diff(times).max()*1e12)] if len(times)>1 else None}
else:
 clock['scope']+=' Missing expected vector remains unresolved; do not infer absence from clk/clock substring search.'
# Collapse numeric wire R for connectivity only. Actual voltage measurements
# remain at each distinct captured physical device terminal, with all RC intact.
import math
rows=[]
for line in model.splitlines():
 line=line.strip()
 if not line or line.startswith('*'):continue
 if line.startswith('+'):assert rows;rows[-1]+=' '+line[1:]
 else:rows.append(line)
active_top=False;top_rows=[];seen=0
for line in rows:
 tok=line.lower().split()
 if tok[0]=='.subckt':
  assert not active_top
  active_top=tok[1]=='nssoc_cdr650_gate_n1';seen+=int(active_top)
 elif tok[0]=='.ends':active_top=False
 elif active_top:top_rows.append(tok)
assert seen==1
parent={}
def local(n):
 n=n.lower()
 return n[4:] if n.startswith('xpd.') else n
def find(n):
 n=local(n);parent.setdefault(n,n)
 if parent[n]!=n:parent[n]=find(parent[n])
 return parent[n]
wires=0
for tok in top_rows:
 if tok[0].startswith('r'):
  assert len(tok)==4 and math.isfinite(float(tok[3])) and float(tok[3])>=0
  a,b=find(tok[1]),find(tok[2]);parent[a]=b;wires+=1
assert wires>0
clock_roots={port:find(port) for port in ['cp','cn']};assert clock_roots['cp']!=clock_roots['cn']
clock_devices={port:[] for port in ['cp','cn']}
for name,dev in bound['groups']['npn13g2'].items():
 for port,root in clock_roots.items():
  if find(dev['nodes'][1])==root:clock_devices[port].append(name)
assert all(clock_devices.values()),'No verified direct clock-driven HBT bases'
pairs=[];used=set()
for pos in clock_devices['cp']:
 pd=bound['groups']['npn13g2'][pos];root=find(pd['nodes'][2])
 matches=[name for name in clock_devices['cn'] if find(bound['groups']['npn13g2'][name]['nodes'][2])==root]
 assert matches,('Missing opposite clock bank on shared emitter',pos)
 for neg in matches:
  assert (pos,neg) not in used;used.add((pos,neg));nd=bound['groups']['npn13g2'][neg]
  tails=[]
  for label,names in bound['mos_tail_groups'].items():
   match=[name for name in names if find(bound['groups']['sg13_lv_nmos'][name]['nodes'][0])==root]
   if match:
    assert len(match)==len(names),'Partial tail group connectivity'
    tails.append(label)
  vp,vn=voltage(pd['nodes'][1]),voltage(nd['nodes'][1]);delta=vp-vn
  item={'positive_base_device':pos,'negative_base_device':neg,'verified_mos_tail_group_labels':tails,'active_base_differential_range_v':[float(delta[active].min()),float(delta[active].max())],'active_base_commonmode_range_v':[float(((vp+vn)/2)[active].min()),float(((vp+vn)/2)[active].max())]}
  for direction in ['rising','falling']:
   hit=np.flatnonzero((delta[:-1]<0)&(delta[1:]>=0) if direction=='rising' else (delta[:-1]>0)&(delta[1:]<=0))
   times=t[hit]+(-delta[hit])*(t[hit+1]-t[hit])/(delta[hit+1]-delta[hit]);times=times[(times>=loaded.START)&(times<=loaded.STOP)]
   expected=np.array([loaded.START+(i+(.5 if direction=='rising' else 1))*loaded.UI for i in range(258)]);expected=expected[expected+2.5e-12<loaded.STOP]
   error=times-expected if len(times)==len(expected) else None
   item[direction]={'observed_edges':len(times),'expected_edges':len(expected),'source_relative_delay_ps':{'min':float(error.min()*1e12),'max':float(error.max()*1e12)} if error is not None else None}
  pairs.append(item)
assert {neg for pos,neg in used}==set(clock_devices['cn'])
assert {pos for pos,neg in used}==set(clock_devices['cp'])
out['internal_clock_pairs']={'scope':'All positive/negative clock branch combinations within each shared-emitter bank, including parallel devices. No arbitrary one-to-one physical pairing. Bases connected to cp/cn through numeric wire R. Group labels bound through actual MOS drain connectivity. No clock alignment edits, timing waiver, output sampling pass or PLL recovery claim.','collapsed_wire_resistors_for_connectivity_only':wires,'branch_combination_count':len(pairs),'positive_clock_devices':len(clock_devices['cp']),'negative_clock_devices':len(clock_devices['cn']),'pairs':pairs}

out['physical_clock_observation']=clock

# Trace two collector-to-base levels backwards from the physical C output.
# Feedback and clock branches are deliberately retained, never classified as
# forward gain stages merely because connectivity reaches them.
roots={find('w_t255_c'),find('w_t257_c')}
assert len(roots)==2
selected={}; frontier=roots
for depth in range(3):
 next_roots=set()
 for name,dev in bound['groups']['npn13g2'].items():
  if find(dev['nodes'][0]) in frontier:
   selected.setdefault(name,depth)
   next_roots.add(find(dev['nodes'][1]))
 frontier=next_roots
assert selected and any(depth==1 for depth in selected.values())
rows=[]
for code in range(8):
 pattern=[(code>>j)&1 for j in (2,1,0)]
 ids=[i for i in range(2,254) if bits[i-2:i+1]==pattern]
 if not ids:continue
 times=np.array([loaded.START+(i+.5+phase)*loaded.UI for i in ids for phase in [.3,.6,.9]])
 def stats(values):
  v=np.interp(times,t,values)
  return {str(q):float(np.percentile(v,q)) for q in [0,50,100]}
 devices=[]
 for name,depth in sorted(selected.items()):
  dev=bound['groups']['npn13g2'][name];vc,vb,ve,_=map(voltage,dev['nodes'])
  devices.append({'name':name,'collector_backtrace_depth':depth,'nodes':dev['nodes'],'nx':dev['nx'],
   'collector_v':stats(vc),'base_v':stats(vb),'emitter_v':stats(ve),'vce_v':stats(vc-ve),
   'collector_current_a':stats(d['@q.'+name+'.qnpn13g2[ic]'])})
 rows.append({'bits_kminus2_to_k':pattern,'bit_count':len(ids),'sample_count':len(times),
  'c_signed_margin_v':stats((voltage('xpd.cqp')-voltage('xpd.cqn'))),
  'devices':devices})
out['sampler_c_backtrace']={'roots':['w_t255_c','w_t257_c'],'device_count':len(selected),
 'scope':'Connectivity backtrace includes feedback and clock devices; does not assert forward gain. Raw differential voltage, not polarity-adjusted margin. Same frozen rising-edge phases 0.3/0.6/0.9 UI, grouped by bit history; no sample realignment or acceptance edits.',
 'groups':rows}
# The value is raw differential, use an unambiguous field name.
for row in rows:row['c_raw_differential_v']=row.pop('c_signed_margin_v')
P('out').mkdir();P('out/sampler-c-backtrace.json').write_text(json.dumps(out,indent=2));print(out['status'])
