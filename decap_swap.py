# SPDX-License-Identifier: Apache-2.0
"""Swap filler cells for same-width decoupling cells in a routed database (OpenROAD -python).

The fill-cell gaps of the placement rows carry no Activ, GatPoly or Metal1
beyond the rails, which leaves the standard-cell core below the foundry's
Activ and Metal1 minimum density after metal fill. sg13g2_fill_4/8 become
sg13g2_decap_4 (same width, same VDD/VSS terminals); a fill_8 becomes two
abutting decap_4 in its footprint (decap_8 is one site narrower than fill_8).
Signal routing starts at Metal2, so no routed wire changes. Every other
instance and every wire is left as it is.
"""
import collections,json,sys
import odb
from openroad import Design,Tech
src,dst,report=sys.argv[1:4]
t=Tech();d=Design(t);d.readDb(src);b=d.getBlock();db=t.getDB()
master=lambda n:next((m for lib in db.getLibs() for m in lib.getMasters() if m.getName()==n),None)
f4,f8,c4=master('sg13g2_fill_4'),master('sg13g2_fill_8'),master('sg13g2_decap_4')
assert None not in(f4,f8,c4)
assert (f4.getWidth(),f4.getHeight())==(c4.getWidth(),c4.getHeight()) and f8.getWidth()==2*c4.getWidth() and f8.getHeight()==c4.getHeight()
assert sorted(m.getName() for m in f4.getMTerms())==sorted(m.getName() for m in c4.getMTerms())
before=collections.Counter(i.getMaster().getName() for i in b.getInsts() if 'fill' in i.getMaster().getName() or 'decap' in i.getMaster().getName())
swapped=collections.Counter();failed=[];k=0
for i in list(b.getInsts()):
    n=i.getMaster().getName()
    if n=='sg13g2_fill_4':
        loc=tuple(i.getLocation());orient=i.getOrient()
        if not i.swapMaster(c4):failed.append(i.getName());continue
        assert tuple(i.getLocation())==loc and i.getOrient()==orient
        swapped[n]+=1
    elif n=='sg13g2_fill_8':
        x,y=i.getLocation();orient=i.getOrient();status=i.getPlacementStatus();name=i.getName()
        odb.dbInst.destroy(i)
        for j,dx in enumerate((0,c4.getWidth())):
            new=odb.dbInst.create(b,c4,f'{name}_DCAP{j}')
            if new is None:failed.append(name);break
            new.setOrient(orient);new.setLocation(x+dx,y);new.setPlacementStatus(status)
        swapped[n]+=1
after=collections.Counter(i.getMaster().getName() for i in b.getInsts() if 'fill' in i.getMaster().getName() or 'decap' in i.getMaster().getName())
dbu=b.getDbUnitsPerMicron()
area=(swapped['sg13g2_fill_4']+2*swapped['sg13g2_fill_8'])*c4.getWidth()*c4.getHeight()/dbu/dbu
r=dict(before=before,after=after,swapped=swapped,failed=failed[:20],failed_count=len(failed),swapped_cell_area_um2=area)
json.dump(r,open(report,'w'),indent=1);print('NSSOC_DECAP',json.dumps(r))
assert not failed
d.writeDb(dst)
