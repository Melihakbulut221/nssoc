#!/usr/bin/env python3
import os,re,json
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load
out=Path(os.environ['NSSOC_PRESERVED_ROUTE_AUDIT']);out.mkdir()
d,b=load(Path(os.environ['NSSOC_ROUTE_IDENTITY_BEFORE']));dd,bb=load(Path(os.environ['NSSOC_ROUTE_IDENTITY_AFTER']))
changed={'net2151', 'nssoc_sta_n_62749', 'net2135', 'nssoc_sta_n_63198', 'net2774', 'nssoc_sta_n_18115', 'net5510', 'net5513', 'nssoc_sta_n_60087', 'net2194', 'nssoc_sta_n_28565', 'nssoc_sta_n_60783'}
def records(block,path):
 odb.write_def(block,str(path));text=path.read_text();m=re.search(r'^NETS (\d+) ;\n(.*?)^END NETS',text,re.M|re.S);assert m
 entries=re.findall(r'^[ \t]*- (\S+) (.*?);',m.group(2),re.M|re.S);r={n:' '.join(v.split())for n,v in entries};assert len(r)==len(entries)==int(m.group(1));return r
left=records(b,out/'before.def');right=records(bb,out/'after.def');assert set(left)==set(right)
def ndr_assignments(block):
 return {n.getName():n.getNonDefaultRule().getName()if n.getNonDefaultRule()else None for n in block.getNets()}
assert ndr_assignments(b)==ndr_assignments(bb),'ndr_assignment_changed'
def ndr_layers(db,block):
 result={}
 for rule in block.getNonDefaultRules():
  rows={}
  for layer in db.getTech().getLayers():
   if str(layer.getType())!='ROUTING':continue
   lr=rule.getLayerRule(layer)
   rows[layer.getName()]=(lr.getWidth(),lr.getSpacing())if lr else None
  result[rule.getName()]=rows
 return result
assert ndr_layers(d,b)==ndr_layers(dd,bb),'ndr_layer_rules_changed'
assert {n for n,r in ndr_assignments(bb).items()if r=='NSSOC_SLEW_LOWER_SPACE2'}=={'net4410','nssoc_sta_n_55164','nssoc_sta_n_55165','nssoc_sta_n_56323'}

bad=[];clocks=[];checked=0
for n,v in left.items():
 if n in changed or str(b.findNet(n).getSigType())in ['POWER','GROUND']:continue
 checked+=1
 if str(b.findNet(n).getSigType())=='CLOCK':clocks.append(n)
 if right[n]!=v:bad.append(n)
r=dict(accepted=False,checked_unchanged_nets=checked,checked_clock_nets=len(clocks),changed_unselected_nets=bad,changed_clock_nets=sorted(set(bad)&set(clocks)))
(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
assert checked==103076 and len(clocks)==2113
assert not bad,('unselected_route_changed',len(bad),bad[:20])
