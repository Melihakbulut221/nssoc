# SPDX-License-Identifier: Apache-2.0
"""Routed wire length against pin half-perimeter for every signal net (OpenROAD -python).

Read-only on the routed database. For each signal net with a wire, the routed
length is the sum of path segment lengths from dbWireDecoder; the reference is
the half-perimeter of the bounding box of its instance and block pins. The
ratio shows routing detour; the named nets are those on the measured critical
paths. Output: a JSON summary.
"""
import json,os,statistics,sys
import odb
from openroad import Design,Tech
odb_path,out=sys.argv[1],sys.argv[2];named=sys.argv[3].split(',')if len(sys.argv)>3 else[]
tech=Tech();design=Design(tech);design.readDb(odb_path)
block=design.getBlock();dbu=block.getDbUnitsPerMicron()
def pins(net):
    pts=[]
    for it in net.getITerms():
        ok,x,y=it.getAvgXY()
        if ok:pts.append((x,y))
        else:
            b=it.getInst().getBBox();pts.append(((b.xMin()+b.xMax())//2,(b.yMin()+b.yMax())//2))
    for bt in net.getBTerms():
        ok,x,y=bt.getFirstPinLocation()
        if ok:pts.append((x,y))
    return pts
def routed(net):
    w=net.getWire()
    if w is None:return 0,{}
    d=odb.dbWireDecoder();d.begin(w);length=0;last=None;layer=None;per={}
    while True:
        op=d.next()
        if op==odb.dbWireDecoder.END_DECODE:break
        if op in(odb.dbWireDecoder.PATH,odb.dbWireDecoder.JUNCTION,odb.dbWireDecoder.SHORT,odb.dbWireDecoder.VWIRE):
            layer=d.getLayer().getName()if d.getLayer()else layer;last=None
            if op==odb.dbWireDecoder.JUNCTION:last=None
        elif op==odb.dbWireDecoder.POINT or op==odb.dbWireDecoder.POINT_EXT:
            p=d.getPoint()[:2]
            if last is not None:
                seg=abs(p[0]-last[0])+abs(p[1]-last[1]);length+=seg;per[layer]=per.get(layer,0)+seg
            last=p
        elif op==odb.dbWireDecoder.TECH_VIA or op==odb.dbWireDecoder.VIA:
            l=d.getVia().getTopLayer()if op==odb.dbWireDecoder.VIA else d.getTechVia().getTopLayer()
            layer=l.getName()if l else layer
    return length,per
rows=[];per_layer={};total=0;total_hp=0
for net in block.getNets():
    if net.getSigType()not in('SIGNAL','CLOCK'):continue
    p=pins(net)
    if len(p)<2:continue
    xs=[a for a,_ in p];ys=[b for _,b in p];hp=(max(xs)-min(xs))+(max(ys)-min(ys))
    L,per=routed(net)
    if L==0:continue
    total+=L;total_hp+=hp
    for k,v in per.items():per_layer[k]=per_layer.get(k,0)+v
    rows.append((net.getName(),L/dbu,hp/dbu,len(p),net.getSigType()))
ratios=[L/max(h,1e-3)for _,L,h,_,_ in rows if h>=20]
res=dict(nets=len(rows),routed_um=total/dbu,hpwl_um=total_hp/dbu,ratio_total=total/max(total_hp,1),
  ratio_quantiles={q:sorted(ratios)[int(q*(len(ratios)-1))]for q in(0.5,0.9,0.99,0.999)}if ratios else{},
  per_layer_um={k:v/dbu for k,v in sorted(per_layer.items())},
  longest=[dict(net=n,routed_um=L,hpwl_um=h,pins=k)for n,L,h,k,_ in sorted(rows,key=lambda r:-r[1])[:40]],
  worst_detour=[dict(net=n,routed_um=L,hpwl_um=h,pins=k)for n,L,h,k,_ in sorted([r for r in rows if r[2]>=50],key=lambda r:-r[1]/r[2])[:40]],
  named={})
idx={r[0]:r for r in rows}
for n in named:
    r=idx.get(n);res['named'][n]=dict(routed_um=r[1],hpwl_um=r[2],pins=r[3])if r else None
die=block.getDieArea();res['die_um']=[die.dx()/dbu,die.dy()/dbu]
open(out,'w').write(json.dumps(res,indent=1));print(json.dumps({k:res[k]for k in('nets','routed_um','hpwl_um','ratio_total','ratio_quantiles','die_um','named')},indent=1))
