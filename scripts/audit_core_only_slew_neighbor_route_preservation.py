#!/usr/bin/env python3
import os,re,json
from pathlib import Path
import odb
from buffer_core_only_chip_controls import load
out=Path(os.environ['NSSOC_PRESERVED_ROUTE_AUDIT']);out.mkdir()
d,b=load(Path(os.environ['NSSOC_ROUTE_IDENTITY_BEFORE']));dd,bb=load(Path(os.environ['NSSOC_ROUTE_IDENTITY_AFTER']))
changed={'nssoc_sta_n_56297', 'nssoc_sta_n_55165', 'nssoc_sta_n_56322', 'nssoc_sta_n_56385', 'nssoc_sta_n_55109', 'nssoc_sta_n_58638', 'nssoc_sta_n_56312', 'nssoc_sta_n_56323', 'nssoc_sta_n_55098', 'net4410', 'nssoc_sta_n_58640', 'net5477', 'nssoc_sta_n_58641', 'nssoc_sta_n_58639', 'nssoc_sta_n_56302', 'nssoc_sta_n_55164', 'nssoc_sta_n_55140', 'nssoc_sta_n_55117'}
assert all(b.findNet(n) and str(b.findNet(n).getSigType())=='SIGNAL' for n in changed)
def records(block,path):
 odb.write_def(block,str(path));text=path.read_text();m=re.search(r'^NETS (\d+) ;\n(.*?)^END NETS',text,re.M|re.S);assert m
 entries=re.findall(r'^[ \t]*- (\S+) (.*?);',m.group(2),re.M|re.S);r={n:' '.join(v.split())for n,v in entries};assert len(r)==len(entries)==int(m.group(1));return r
left=records(b,out/'before.def');right=records(bb,out/'after.def');assert set(left)==set(right)
bad=[];clocks=[];checked=0
for n,v in left.items():
 if n in changed or str(b.findNet(n).getSigType())in ['POWER','GROUND']:continue
 checked+=1
 if str(b.findNet(n).getSigType())=='CLOCK':clocks.append(n)
 if right[n]!=v:bad.append(n)
r=dict(accepted=False,checked_unchanged_nets=checked,checked_clock_nets=len(clocks),changed_unselected_nets=bad,changed_clock_nets=sorted(set(bad)&set(clocks)))
(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
assert checked==103067 and len(clocks)==2113
assert not bad,('unselected_route_changed',len(bad),bad[:20])
