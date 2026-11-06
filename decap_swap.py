# SPDX-License-Identifier: Apache-2.0
"""Swap filler cells for same-width decoupling cells in a routed database (OpenROAD -python).

The fill-cell gaps of the placement rows carry no Activ, GatPoly or Metal1
beyond the rails, which leaves the standard-cell core below the foundry's
Activ and Metal1 minimum density after metal fill. sg13g2_fill_4/8 become
sg13g2_decap_4/8, which have the same width and the same VDD/VSS terminals.
Signal routing starts at Metal2, so no routed wire changes. Every other
instance and every wire is left as it is.
"""
import collections,json,sys
from openroad import Design,Tech
src,dst,report=sys.argv[1:4]
t=Tech();d=Design(t);d.readDb(src);b=d.getBlock();db=b.getDb()
master=lambda n:next((m for lib in db.getLibs() for m in lib.getMasters() if m.getName()==n),None)
pairs={}
for w in('4','8'):
    f,c=master('sg13g2_fill_'+w),master('sg13g2_decap_'+w)
    assert f is not None and c is not None,w
    assert (f.getWidth(),f.getHeight())==(c.getWidth(),c.getHeight()),(w,f.getWidth(),c.getWidth())
    assert sorted(m.getName() for m in f.getMTerms())==sorted(m.getName() for m in c.getMTerms()),w
    pairs[f.getName()]=c
before=collections.Counter(i.getMaster().getName() for i in b.getInsts() if 'fill' in i.getMaster().getName() or 'decap' in i.getMaster().getName())
swapped=collections.Counter();failed=[]
for i in b.getInsts():
    n=i.getMaster().getName()
    if n in pairs:
        loc=i.getLocation();orient=i.getOrient();status=i.getPlacementStatus()
        if not i.swapMaster(pairs[n]):failed.append(i.getName());continue
        assert tuple(i.getLocation())==tuple(loc) and i.getOrient()==orient
        swapped[n]+=1
after=collections.Counter(i.getMaster().getName() for i in b.getInsts() if 'fill' in i.getMaster().getName() or 'decap' in i.getMaster().getName())
dbu=b.getDbUnitsPerMicron()
area=sum(m.getWidth()*m.getHeight() for m in [pairs[k] for k in swapped for _ in range(swapped[k])])/dbu/dbu
r=dict(before=before,after=after,swapped=swapped,failed=failed[:20],failed_count=len(failed),swapped_cell_area_um2=area)
json.dump(r,open(report,'w'),indent=1);print('NSSOC_DECAP',json.dumps(r))
assert not failed
d.writeDb(dst)
