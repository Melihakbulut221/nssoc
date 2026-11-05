# SPDX-License-Identifier: Apache-2.0
"""Re-encode the wires of named signal nets from FIXED to ROUTED (OpenROAD -python).

The detailed router never rips up a net whose wire is FIXED. Every op of each
named net is decoded and re-encoded with identical geometry and the ROUTED wire
type. The encoder may pack points differently, so the check is geometric:
the decoded geometry (segments, vias, extensions and patch rectangles), the
connected terminals in order and the length must equal the original, and every
path must read ROUTED. Any difference, a clock, power or special net, or an op
this copier does not handle stops the run before writing.
"""
import json,sys
import odb
from openroad import Design,Tech
src,names_file,dst,report=sys.argv[1:5]
tech=Tech();design=Design(tech);design.readDb(src);block=design.getBlock()
D=odb.dbWireDecoder
PATHS={0,1,2,13}
def raw(w):return[(w.getOpcode(i),w.getData(i))for i in range(w.length())]
def shapes(w,rects):
    """Encoding-independent geometry: segments, vias and patch rectangles."""
    d=D();d.begin(w);out=[];at={};layer=None;last=None;rects=list(reversed(rects))
    while True:
        op=d.next()
        if op==D.END_DECODE:return sorted(out,key=repr)
        if op==D.PATH:layer=d.getLayer().getName();last=None
        elif op in(D.JUNCTION,D.SHORT,D.VWIRE):
            layer=d.getLayer().getName()if d.getLayer()else layer;last=at[d.getJunctionValue()]
            if op!=D.JUNCTION:out.append(('jump',op,layer,last))
        elif op in(D.POINT,D.POINT_EXT):
            pt=tuple(d.getPoint())if op==D.POINT else tuple(d.getPoint_ext())
            xy=pt[:2]
            if last is not None and last!=xy:out.append(('seg',layer,tuple(sorted([last,xy]))))
            if op==D.POINT_EXT:out.append(('ext',layer,pt))
            last=xy;at[d.getJunctionId()]=xy
        elif op in(D.VIA,D.TECH_VIA):
            v=d.getVia()if op==D.VIA else d.getTechVia();out.append(('via',v.getName(),last))
            layer=d.getLayer().getName();at[d.getJunctionId()]=last
        elif op==D.RECT:out.append(('rect',layer,last,rects.pop()))
def rawrects(r):
    return[tuple(r[i+k][1]for k in range(4))for i,(o,_)in enumerate(r)if o&0x1F==14]
def terms(w):
    d=D();d.begin(w);t=[];types=set()
    while True:
        op=d.next()
        if op==D.END_DECODE:return t,types
        if op in(D.PATH,D.SHORT,D.VWIRE):types.add(str(d.getWireType()))
        if op==D.ITERM:t.append(('i',d.getITerm().getId()))
        if op==D.BTERM:t.append(('b',d.getBTerm().getId()))
def reencode(net):
    w=net.getWire();before=raw(w);geo=(shapes(w,rawrects(before)),terms(w)[0],w.getLength());d=D();d.begin(w);ops=[]
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
        elif op==D.POINT:
            x,y=d.getPoint();prop=d.getProperty()
            if prop:raise SystemExit(f'nonzero point property {prop} on {net.getName()}')
            ops.append(('point',(x,y),prop,d.getJunctionId()))
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
        # In Python a third integer selects the extension overload, so plain
        # points take two arguments. Point properties (kProperty, 0 here) carry
        # no geometry and are not rewritten.
        elif k=='point':ids[o[3]]=e.addPoint(o[1][0],o[1][1])
        elif k=='point_ext':ids[o[3]]=e.addPoint(o[1][0],o[1][1],o[1][2])
        elif k=='via':ids[o[2]]=e.addVia(o[1])
        elif k=='tech_via':ids[o[2]]=e.addTechVia(o[1])
        elif k=='rect':e.addRect(*o[1])
        elif k=='iterm':e.addITerm(o[1])
        elif k=='bterm':e.addBTerm(o[1])
    e.end()
    w=net.getWire();t,types=terms(w)
    now=(shapes(w,rawrects(raw(w))),t,w.getLength())
    if now!=geo:
        import collections
        a=collections.Counter(map(repr,geo[0]));b=collections.Counter(map(repr,now[0]))
        print('ORIGINAL_ONLY',list((a-b).elements())[:30]);print('NEW_ONLY',list((b-a).elements())[:30])
        print('TERMS',geo[1]==now[1],len(geo[1]),len(now[1]),'LENGTH',geo[2],now[2])
        print('RAW_BEFORE',before[:60])
        raise SystemExit(f'geometry or terminals differ on {net.getName()}')
    if types!={'ROUTED'}:raise SystemExit(f'wire types {types} on {net.getName()}')
    return dict(ops_before=len(before),ops_after=w.length(),shapes=len(geo[0]),terms=len(t))
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
