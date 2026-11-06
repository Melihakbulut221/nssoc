# SPDX-License-Identifier: Apache-2.0
"""Report the instances and nets at a layout point (OpenROAD -python), read-only."""
import sys
from openroad import Design,Tech
odb_path,x,y=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
t=Tech();d=Design(t);d.readDb(odb_path);b=d.getBlock();u=b.getDbUnitsPerMicron();X,Y=int(x*u),int(y*u)
for i in b.getInsts():
    bb=i.getBBox()
    if bb.xMin()-2*u<=X<=bb.xMax()+2*u and bb.yMin()-2*u<=Y<=bb.yMax()+2*u:
        print('NSSOC_AT',i.getName(),i.getMaster().getName(),[(t_.getMTerm().getName(),t_.getNet().getName()if t_.getNet()else None)for t_ in i.getITerms()if t_.getNet()and t_.getNet().getSigType()not in('POWER','GROUND')])
for bt in b.getBTerms():
    for p in bt.getBPins():
        for bx in p.getBoxes():
            if bx.getTechLayer().getName().startswith('TopMetal'):
                print('NSSOC_PIN',bt.getName(),bt.getNet().getName(),bx.getTechLayer().getName(),bx.xMin()/u,bx.yMin()/u,bx.xMax()/u,bx.yMax()/u)
