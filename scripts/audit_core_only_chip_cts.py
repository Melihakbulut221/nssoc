#!/usr/bin/env python3
"""Require unchanged logic and trace inserted clock buffers to original pad sources."""
import os,json
from pathlib import Path
from collections import Counter
import odb
out=Path(os.environ['NSSOC_CTS_OUT'])
def load(n):
    d=odb.dbDatabase.create();odb.read_db(d,str(out/n));return d,d.getChip().getBlock()
def pins(b):
    return sorted((t.getName(),t.getNet().getName(),str(t.getIoType()),str(t.getSigType()),sorted((str(p.getPlacementStatus()),sorted((x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax())for x in p.getBoxes()))for p in t.getBPins()))for t in b.getBTerms())
def geometry(i):
    b=i.getBBox();return [str(i.getOrient()),str(i.getPlacementStatus()),b.xMin(),b.yMin(),b.xMax(),b.yMax()]
d0,b0=load('chip-placed.odb');d1,b1=load('chip-cts.odb');a={i.getName():i for i in b0.getInsts()};z={i.getName():i for i in b1.getInsts()}
assert set(a)<set(z) and pins(b0)==pins(b1)
new={n:z[n]for n in set(z)-set(a)}
allowed={'sg13g2_buf_2','sg13g2_buf_4','sg13g2_buf_8','sg13g2_buf_16'}
for n,i in new.items():
    assert i.getMaster().getName()in allowed and str(i.getPlacementStatus())=='PLACED'
    for p,v in [('VDD','VDD'),('VSS','VSS')]:assert i.findITerm(p).getNet().getName()==v
    assert all(t.getNet()for t in i.getITerms())
drivers={}
for n,i in new.items():
    net=i.findITerm('X').getNet().getName();assert net not in drivers;drivers[net]=i.findITerm('A').getNet().getName()
def origin(net):
    seen=set()
    while net in drivers:
        assert net not in seen;seen.add(net);net=drivers[net]
    return net,len(seen)
clock_counts=Counter();buffered_counts=Counter();fixed=0;core_clock=None
for n,i in a.items():
    j=z[n];assert i.getMaster().getName()==j.getMaster().getName()
    if str(i.getPlacementStatus())=='LOCKED':assert geometry(i)==geometry(j);fixed+=1
    else:assert str(j.getPlacementStatus())=='PLACED'
    for t in i.getITerms():
        pin=t.getMTerm().getName();old=t.getNet().getName();newnet=j.findITerm(pin).getNet();assert newnet
        clk=(i.getMaster().getName()=='sg13g2_dfrbpq_1' and pin=='CLK')or(n=='u_core'and pin=='clk_i')
        if clk:
            root,depth=origin(newnet.getName());assert root==old
            if n=='u_core':core_clock=dict(root=root,buffer_depth=depth)
            else:clock_counts[root]+=1;buffered_counts[root]+=int(depth>0)
        else:assert newnet.getName()==old,(n,pin,old,newnet.getName())
assert fixed==297 and clock_counts=={'n_1486':161,'n_1484':197} and buffered_counts==clock_counts
assert all(origin(v)[0]in clock_counts for v in drivers)
# Topology invariance is stronger than simply observing a successful CTS log.
report=dict(inserted_buffers=len(new),clock_sink_counts=dict(clock_counts),buffered_sink_counts=dict(buffered_counts),fixed_instances=fixed,core_clock=core_clock,nonclock_connections_unchanged=True,top_pin_shapes_unchanged=True,accepted=False,core_clock_load_qualified=False,cts_timing_qualified=False)
(out/'cts-audit.json').write_text(json.dumps(report,indent=2)+'\n')
