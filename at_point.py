# SPDX-License-Identifier: Apache-2.0
"""Report the terminals whose pin geometry contains a layout point, and the
TopMetal2 wire length of their nets (OpenROAD -python), read-only."""
import sys
import odb
from openroad import Design,Tech
odb_path,x,y=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
t=Tech();d=Design(t);d.readDb(odb_path);b=d.getBlock();u=b.getDbUnitsPerMicron();X,Y=int(x*u),int(y*u)
def tm2_length(net):
    w=net.getWire()
    if w is None:return 0
    dec=odb.dbWireDecoder();dec.begin(w);L=0;last=None;layer=None
    while True:
        op=dec.next()
        if op==odb.dbWireDecoder.END_DECODE:return L/u
        if op in(odb.dbWireDecoder.PATH,odb.dbWireDecoder.JUNCTION,odb.dbWireDecoder.SHORT,odb.dbWireDecoder.VWIRE):
            layer=dec.getLayer().getName()if dec.getLayer()else layer;last=None
        elif op==odb.dbWireDecoder.POINT:
            p=tuple(dec.getPoint())
            if last and layer=='TopMetal2':L+=abs(p[0]-last[0])+abs(p[1]-last[1])
            last=p
        elif op in(odb.dbWireDecoder.VIA,odb.dbWireDecoder.TECH_VIA):layer=dec.getLayer().getName()if dec.getLayer()else layer
for i in b.getInsts():
    bb=i.getBBox()
    if not(bb.xMin()-u<=X<=bb.xMax()+u and bb.yMin()-u<=Y<=bb.yMax()+u):continue
    tx=i.getTransform()
    for it in i.getITerms():
        n=it.getNet()
        if n is None or n.getSigType()in('POWER','GROUND'):continue
        hit=False
        for mp in it.getMTerm().getMPins():
            for g in mp.getGeometry():
                r=odb.Rect(g.xMin(),g.yMin(),g.xMax(),g.yMax());tx.apply(r)
                if r.xMin()-u//2<=X<=r.xMax()+u//2 and r.yMin()-u//2<=Y<=r.yMax()+u//2:hit=True
        print('NSSOC_TERM',i.getName(),i.getMaster().getName(),it.getMTerm().getName(),n.getName(),'near' if hit else 'cell','tm2_um=%.1f'%tm2_length(n))
