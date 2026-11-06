# SPDX-License-Identifier: Apache-2.0
"""List signal nets without a routed wire (OpenROAD -python), read-only.

A net with two or more connected terminals and no wire is an open. Nets with
fewer terminals are reported separately (dangling outputs or tie stubs).
"""
import json,sys
from openroad import Design,Tech
odb_path,out=sys.argv[1:3]
tech=Tech();d=Design(tech);d.readDb(odb_path);b=d.getBlock()
opens=[];stubs=[]
for n in b.getNets():
    if n.isSpecial()or n.getSigType()in('POWER','GROUND'):continue
    if n.getWire()is not None:continue
    terms=[(t.getInst().getName(),t.getMTerm().getName(),t.getIoType())for t in n.getITerms()]+[('PIN',t.getName(),t.getIoType())for t in n.getBTerms()]
    row=dict(net=n.getName(),type=n.getSigType(),terms=terms[:6],count=len(terms))
    (opens if len(terms)>=2 else stubs).append(row)
json.dump(dict(opens=opens,stubs=stubs),open(out,'w'),indent=1)
print('NSSOC_NETS opens',len(opens),'stubs',len(stubs))
for r in opens[:20]:print('NSSOC_OPEN',r['net'],r['count'],r['terms'][:3])
