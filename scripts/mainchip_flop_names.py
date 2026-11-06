# SPDX-License-Identifier: Apache-2.0
"""Map anonymous flip-flop instances to the RTL names of their output nets (OpenROAD -python).

Read-only on a routed database. For each listed instance, prints the master and
the names of the nets on its output pins, which carry the RTL register name.
"""
import json,sys
from openroad import Design,Tech
odb_path,names,out=sys.argv[1:4]
tech=Tech();d=Design(tech);d.readDb(odb_path);b=d.getBlock();rows={}
for n in [l.strip()for l in open(names)if l.strip()]:
    i=b.findInst(n)
    if i is None:rows[n]=None;continue
    rows[n]=dict(master=i.getMaster().getName(),outputs={t.getMTerm().getName():(t.getNet().getName()if t.getNet()else None)for t in i.getITerms()if t.isOutputSignal()})
json.dump(rows,open(out,'w'),indent=1);print('mapped',sum(1 for v in rows.values()if v),'of',len(rows))
