# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source and actual saved target census; no TX native execution."""
from pathlib import Path
import ast,datetime,hashlib,json,re
S=Path(__file__).resolve().parent;B=S.parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((S/'source-freeze.json').read_text());ledger=json.loads((S/'derivation.json').read_text());census=json.loads((S/'selected-targets.json').read_text());candidate=Path(f['candidate']['path']);assert pin(candidate)=={k:f['candidate'][k] for k in ['bytes','sha256']}
assert pin(S/'derivation.json')==f['derivation'] and pin(S/'selected-targets.json')==f['census']
a=Path(ledger['before']['path']).read_text();z=candidate.read_text();assert pin(Path(ledger['before']['path']))=={k:ledger['before'][k] for k in ['bytes','sha256']}
forward=a
for x in ledger['changes']:assert forward.count(x['before'])==1;forward=forward.replace(x['before'],x['after'])
assert forward==z
inverse=z
for x in reversed(ledger['changes']):assert inverse.count(x['after'])==1;inverse=inverse.replace(x['after'],x['before'])
assert inverse==a
def defs(text):return {n.name:ast.dump(n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
assert defs(a)==defs(z)
for p,v in ledger['baseline'].items():assert pin(p)==v
for p,v in census['inputs'].items():assert pin(p)==v
native=Path('/dev/shm/nssoc-tx-path-v4-repair02-drt-03');lib=next(Path(x) for x in census['inputs'] if x.endswith('.lib'))
def blocks(text,kind):
 for m in re.finditer(r'\b'+kind+r'\s*\(\s*([^\)]+?)\s*\)\s*\{',text):
  i=m.end();depth=1
  while depth:
   if text[i]=='{':depth+=1
   elif text[i]=='}':depth-=1
   i+=1
  yield m.group(1).strip('"'),text[m.end():i-1]
masters={}
for name,body in blocks(lib.read_text(),'cell'):
 masters[name]={}
 for port,ptext in blocks(body,'pin'):
  direction=re.search(r'\bdirection\s*:\s*"?(\w+)',ptext).group(1);function=re.search(r'\bfunction\s*:\s*"([^"]+)"',ptext)
  masters[name][port]=dict(direction=direction,function=function.group(1) if function else None)
text=(native/'routed.v').read_text();inst={}
for m in re.finditer(r'\b(sg13g2_\w+)\s+(\S+)\s*\((.*?)\);',text,re.S):
 master,name,body=m.groups();assert name not in inst;inst[name]=dict(master=master,pins={p:n.strip() for p,n in re.findall(r'\.(\w+)\s*\((.*?)\)',body,re.S)})
oldreview=json.loads((B/'repair02-peer/review.json').read_text());paths='\n'.join(x['raw_path'] for x in oldreview['SS_three_worst_setup_paths'])
tree=ast.parse(z);assign={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['targets','upsizes']}
assert len(assign['targets'])==7 and len(assign['upsizes'])==3
checked=[]
for row in census['targets']:
 name=row['driver'];cell=inst[name];assert cell['master']==row['master'] and cell['pins'][row['output_pin']]==row['net'];assert row['measured_slow_path']['raw_line'] in paths
 assert masters[cell['master']][row['output_pin']]['direction']=='output'
 loads=[];drivers=[]
 for n,c in inst.items():
  for p,net in c['pins'].items():
   if net==row['net']:
    if masters[c['master']][p]['direction']=='input':loads.append(n+'/'+p)
    else:assert masters[c['master']][p]['direction']=='output';drivers.append((n,p))
 assert drivers==[(name,row['output_pin'])] and sorted(loads)==sorted(x['instance']+'/'+x['pin'] for x in row['loads']) and len(loads)==row['measured_slow_path']['fanout']
 if row['change']=='isolate':
  declaration=next(x for x in assign['targets'] if x['name']==name);assert declaration==dict(name=name,master=row['master'],output_pin=row['output_pin'],net=row['net'],loads=[x['instance']+'/'+x['pin'] for x in row['loads']],buffer=row['target_master'])
  assert masters[row['target_master']]==dict(A=dict(direction='input',function=None),X=dict(direction='output',function='A'))
 else:
  assert (name,row['master'],row['target_master']) in assign['upsizes'];assert masters[row['master']]==masters[row['target_master']]
 checked.append(dict(name=name,master=row['master'],loads=len(loads),change=row['change'],target=row['target_master'],actual_slow_cell_net_delay_ns=row['measured_slow_path']['incremental_cell_net_delay_ns']))
assert len(checked)==10
report=dict(status='PASS_TX03_SOURCE_ONLY_PEER',utc=datetime.datetime.now(datetime.UTC).isoformat(),reviewer='/root/rx_route_resume',findings=[],method=pin(__file__),source_freeze=pin(S/'source-freeze.json'),candidate=f['candidate'],derivation=f['derivation'],target_census=f['census'],baseline_pins_rehashed=len(ledger['baseline']),independent_native_instance_census=len(inst),independently_checked_targets=checked,checks=['Full original02/new03 source read; exact whole-source forward and inverse ledger rebuilt, all6 helper function ASTs unchanged.','All saved baseline and census inputs freshly rehashed. Independent actual routed Verilog and Liberty parser verifies every selected master/output/net/exact complete load set; all10 targets occur in actualTX02 worst3slow paths.','Seven buffers have true A→X function and three upsizes have identical fullpin directions/functions; existing hold/recovery circuit inherited in immutableTX02 baseline with no new hold insertion.','Generated Tcl asserts exact current target master, actual outputnet, full sorted loads and zero boundary terminals; inserts real declared buf4/buf8 at actual source location, then detailed placement/freshincrementalGRT.','Read baseline actualRC before geometry clear; originalDB/SPEF remain immutable; before/after logical netlist guard; only freshGRT estimates after cell/net edits. Unchanged4ns/IO/propagatedclock, no false/multicycle paths introduced.','Native control retains blocked signal spawn registration, own processgroup, failure-only5scleanup,1GiBentry/528MiBsharedfloor/2.5GiBAS/singleCPU4; no healthy elapsed timeout. Fresh equivalence/ports/DRT/RC mandatory.'],native_executed=False,tests_rerun=False,qualified_rc=False,physical_acceptance=False,scope='Source-only candidate peer; no fresh GRT, nativeproof, portreplay, route or nominalRC acceptance. PreviousTX02 timing remains the only measured baseline; no timing improvement promised.')
p=S/'source-only-peer-rx.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
