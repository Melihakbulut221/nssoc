# SPDX-License-Identifier: Apache-2.0
"""Re-encode the wires of named signal nets from FIXED to ROUTED (OpenROAD -python).

The detailed router never rips up a net whose wire is FIXED. Every op of each
named net is decoded and re-encoded with identical geometry and the ROUTED wire
type. Afterwards the raw op stream is compared with the original: only the
wire-type bits of path ops may differ. Any other difference, a clock, power or
special net, or an op this copier does not handle stops the run before writing.
"""
import json,sys
import odb
from openroad import Design,Tech
src,names_file,dst,report=sys.argv[1:5]
tech=Tech();design=Design(tech);design.readDb(src);block=design.getBlock()
D=odb.dbWireDecoder
PATHS={0,1,2,13}
def raw(w):return[(w.getOpcode(i),w.getData(i))for i in range(w.length())]
def reencode(net):
    w=net.getWire();before=raw(w);d=D();d.begin(w);ops=[]
    # getRect has no Python output binding; a RECT is stored as kRect(14) with
    # deltaX1 followed by three kOperand(11) ops, in decode order.
    rects=[tuple(before[i+k][1]for k in range(4))for i,(o,_)in enumerate(before)
           if o&0x1F==14 and all(before[i+k][0]&0x1F==11 for k in(1,2,3))]
    if len(rects)!=sum(1 for o,_ in before if o&0x1F==14):raise SystemExit(f'unexpected RECT layout on {net.getName()}')
    rects.reverse()
    while True:
        op=d.next()
        if op==D.END_DECODE:break
        if op==D.PATH:ops.append(('path',d.getLayer(),None))
        elif op==D.JUNCTION:ops.append(('junction',d.getJunctionValue(),None))
        elif op==D.SHORT:ops.append(('short',d.getJunctionValue(),d.getLayer()))
        elif op==D.VWIRE:ops.append(('vwire',d.getJunctionValue(),d.getLayer()))
        elif op==D.POINT:x,y=d.getPoint();ops.append(('point',(x,y),d.getProperty(),d.getJunctionId()))
        elif op==D.POINT_EXT:x,y,e=d.getPoint_ext();ops.append(('point_ext',(x,y,e),d.getProperty(),d.getJunctionId()))
        elif op==D.VIA:ops.append(('via',d.getVia(),d.getJunctionId()))
        elif op==D.TECH_VIA:ops.append(('tech_via',d.getTechVia(),d.getJunctionId()))
        elif op==D.RECT:ops.append(('rect',rects.pop()))
        elif op==D.ITERM:ops.append(('iterm',d.getITerm()))
        elif op==D.BTERM:ops.append(('bterm',d.getBTerm()))
        else:raise SystemExit(f'unsupported op {op} on {net.getName()}')
    # The Python binding maps dbWireType to and from its name.
    R='ROUTED';odb.dbWire.destroy(w);w=odb.dbWire.create(net);e=odb.dbWireEncoder();e.begin(w);ids={}
    for o in ops:
        k=o[0]
        if k=='path':e.newPath(o[1],R)
        elif k=='junction':e.newPath(ids[o[1]],R)
        elif k=='short':e.newPathShort(ids[o[1]],o[2],R)
        elif k=='vwire':e.newPathVirtualWire(ids[o[1]],o[2],R)
        elif k=='point':ids[o[3]]=e.addPoint(o[1][0],o[1][1],o[2])
        elif k=='point_ext':ids[o[3]]=e.addPoint(o[1][0],o[1][1],o[1][2],o[2])
        elif k=='via':ids[o[2]]=e.addVia(o[1])
        elif k=='tech_via':ids[o[2]]=e.addTechVia(o[1])
        elif k=='rect':e.addRect(*o[1])
        elif k=='iterm':e.addITerm(o[1])
        elif k=='bterm':e.addBTerm(o[1])
    e.end()
    after=raw(net.getWire())
    if len(after)!=len(before):raise SystemExit(f'op count differs on {net.getName()}: {len(before)} -> {len(after)}')
    changed=0
    for (a,x),(b,y)in zip(before,after):
        if (a&0x1F)in PATHS and (a&0x1F)==(b&0x1F) and x==y:
            if (a&0xE0)!=(b&0xE0):
                if (a&0xE0)!=0x40 or (b&0xE0)!=0x60:raise SystemExit(f'unexpected wire type change on {net.getName()}')
                changed+=1
            continue
        if (a,x)!=(b,y):raise SystemExit(f'op differs on {net.getName()}: {(a,x)} -> {(b,y)}')
    return dict(ops=len(before),path_type_changes=changed)
out={}
for name in [l.strip()for l in open(names_file)if l.strip()]:
    net=block.findNet(name)
    if net is None:out[name]='missing';continue
    if net.isSpecial()or net.getSigType()in('POWER','GROUND','CLOCK')or 'clk' in name:raise SystemExit(f'refusing {name}')
    if net.getWire()is None:out[name]='no wire';continue
    d=D();d.begin(net.getWire());d.next()
    wt=str(d.getWireType())
    if wt!='FIXED':out[name]='already '+wt;continue
    out[name]=reencode(net)
json.dump(out,open(report,'w'),indent=1)
print('NSSOC_UNFIX',sum(1 for v in out.values()if isinstance(v,dict)),'re-encoded of',len(out))
design.writeDb(dst)
