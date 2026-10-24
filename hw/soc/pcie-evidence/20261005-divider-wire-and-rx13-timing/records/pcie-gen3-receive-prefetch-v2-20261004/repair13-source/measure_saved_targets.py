# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure saved-output RX12 path/DEF/Liberty/Verilog target census; no EDA."""
from pathlib import Path
import re,json,hashlib,collections
R=Path.cwd();B=Path(__file__).resolve().parent
D=Path('/dev/shm/nssoc-rx-prefetch-v2-repair12-drt-01');P=B.parent/'repair12-peer'
L=Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_slow_1p08V_125C.lib')
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def blocks(text,kind):
 for m in re.finditer(r'\b'+kind+r'\s*\(\s*([^\)]+?)\s*\)\s*\{',text):
  level=1;pos=m.end()
  while level:
   if text[pos]=='{':level+=1
   elif text[pos]=='}':level-=1
   pos+=1
  yield m.group(1).strip('"'),text[m.end():pos-1]
cells={n:{pn:re.search(r'\bdirection\s*:\s*"?(\w+)',p).group(1) for pn,p in blocks(body,'pin')} for n,body in blocks(L.read_text(),'cell')}
v=(D/'routed.v').read_text();inst={}
for m in re.finditer(r'\b(sg13g2_\w+)\s+(\S+)\s*\((.*?)\);',v,re.S):
 master,name,body=m.groups();assert name not in inst
 pins={p:n.strip() for p,n in re.findall(r'\.(\w+)\s*\((.*?)\)',body,re.S)};assert set(pins)<=set(cells[master]);inst[name]=dict(master=master,pins=pins)
d=(D/'routed.def').read_text();scale=int(re.search(r'UNITS DISTANCE MICRONS (\d+)',d).group(1));loc={}
for m in re.finditer(r'^\s*- (\S+) (sg13g2_\w+)[^;]*?\+ (?:PLACED|FIXED) \( (\d+) (\d+) \)',d,re.M|re.S):loc[m.group(1)]=[int(m.group(3))/scale,int(m.group(4))/scale]
review=json.loads((P/'review.json').read_text());assert review['nominal_rc_cell_corner_slack_ns']['slow']['setup']==-.521801
paths=review['SS_three_worst_setup_paths'];measurement={}
for path in paths:
 for raw in path['raw_path'].splitlines():
  m=re.fullmatch(r'\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+[\^v] (\S+)/(\S+) \((sg13g2_\w+)\)',raw)
  if m:
   fan,cap,slew,delay,t,name,pinname,master=m.groups();measurement.setdefault(name,dict(fanout=int(fan),cap_pf=float(cap),slew_ns=float(slew),incremental_cell_net_delay_ns=float(delay),output_pin=pinname,master=master,raw_line=raw))
selection=[('_19674_','isolate','sg13g2_buf_8'),('_19783_','isolate','sg13g2_buf_8'),('_19786_','isolate','sg13g2_buf_8'),('_20546_','isolate','sg13g2_buf_4'),('_19774_','isolate','sg13g2_buf_4'),('_20604_','isolate','sg13g2_buf_4'),('place9604','upsize','sg13g2_buf_4'),('rebuffer11537','upsize','sg13g2_buf_4'),('_24539_','upsize','sg13g2_nand2_2'),('_19892_','upsize','sg13g2_nor2_2')]
rows=[]
for name,change,target in selection:
 e=inst[name];m=measurement[name];assert e['master']==m['master'] and target in cells;assert set(cells[target])==set(cells[e['master']]) if change=='upsize' else True
 op=m['output_pin'];assert cells[e['master']][op]=='output';net=e['pins'][op]
 assert not any(net in x.split() for x in re.findall(r'assign(.*?);',v,re.S))
 loads=[];drivers=[]
 for n,c in inst.items():
  for p,q in c['pins'].items():
   if q==net:
    if cells[c['master']][p]=='output':drivers.append((n,p))
    else:
     assert cells[c['master']][p]=='input';loads.append(dict(instance=n,pin=p,master=c['master'],location_um=loc[n],manhattan_um=sum(abs(a-b) for a,b in zip(loc[n],loc[name]))))
 assert drivers==[(name,op)] and len(loads)==m['fanout']
 rows.append(dict(driver=name,master=e['master'],output_pin=op,net=net,location_um=loc[name],loads=loads,measured_slow_path=m,change=change,target_master=target))
report=dict(status='PASS_SAVED_RX12_TARGET_TOPOLOGY_AND_ACTUAL_NOMINAL_PATH_CENSUS',inputs={str(p):pin(p) for p in [Path(__file__),D/'routed.v',D/'routed.def',P/'review.json',L]},instance_census=len(inst),targets=rows,selected_isolations=6,selected_upsizes=4,liberty_available_drive_alternatives={stem:[n for n in cells if n.startswith('sg13g2_'+stem+'_')] for stem in ['nand3','nand4','nand2','nor2','or2','buf']},reason='The actual three slow paths now expose high fanout/long-wire weak drivers. NAND3/NAND4 have only drive1; isolate all exact loads near source with real buffers. Other4 measured weak cells upsize with unchanged logic. Existing timing limitations unchanged; no estimate of timing gain is asserted.',scope='Saved byte parser only, no native EDA, no new timing acceptance. Candidate must retain4ns/IO/clock constraints then fresh proof, port replay, detailed routing and nominal RC.')
p=B/'selected-targets.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p),targets=[{k:x[k] for k in ['driver','change','target_master']} for x in rows])))
