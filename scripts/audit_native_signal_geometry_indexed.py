#!/usr/bin/env python3
"""Physical signal continuity on native routing plus LEF pin geometry.

A native cell terminal is one electrically equivalent access group; this does
not prove hidden macro/internal transistor connectivity or replace full LVS.
"""
import json,os,hashlib,sys
from pathlib import Path
from collections import defaultdict,Counter
from native_geometry_contact_index import inter_net_contacts

def touch(a,b):return a[0]<=b[2]and b[0]<=a[2]and a[1]<=b[3]and b[1]<=a[3]
def components(rows):
    # row=(x0,y0,x1,y1,layer,electrical_group,kind,label)
    parent=list(range(len(rows)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(a,b):
        a,b=root(a),root(b)
        if a!=b:parent[b]=a
    groups={};layers=defaultdict(list)
    for i,row in enumerate(rows):
        assert row[0]<row[2]and row[1]<row[3]
        if row[5]in groups:union(i,groups[row[5]])
        else:groups[row[5]]=i
        layers[row[4]].append(i)
    for ids in layers.values():
        active=[]
        for i in sorted(ids,key=lambda i:rows[i][0]):
            active=[j for j in active if rows[j][2]>=rows[i][0]]
            for j in active:
                if touch(rows[i],rows[j]):union(i,j)
            active.append(i)
    result=defaultdict(list)
    for i in range(len(rows)):result[root(i)].append(i)
    return list(result.values())

def self_test():
    pin0=(0,0,2,2,'M1','p0','pin','p0');pin1=(8,0,10,2,'M1','p1','pin','p1')
    wire=(2,0,8,2,'M1','wire','wire','wire')
    assert len(components([pin0,pin1,wire]))==1
    assert len(components([pin0,pin1]))==2
    assert len(components([pin0,pin1,(2,0,8,2,'M2','wrong','wire','wrong')]))==3
    assert len(components([pin0,pin1,wire,(20,0,22,2,'M1','float','wire','float')]))==2
    via=[(1,0,3,2,'M1','v','via','v'),(1,0,3,2,'M2','v','via','v')]
    assert len(components([pin0,*via,(3,0,8,2,'M2','w','wire','w'),(8,0,10,2,'M2','p2','pin','p2')]))==1
    assert len(components([pin0,*via[:1],(3,0,8,2,'M2','w','wire','w'),(8,0,10,2,'M2','p2','pin','p2')]))==2
    assert not touch((0,0,2,2),(3,0,5,2))and touch((0,0,2,2),(2,0,4,2))
    return dict(connected_metal=True,missing_wire_rejected=True,wrong_layer_rejected=True,floating_fragment_rejected=True,native_via_group_model=True,missing_via_landing_rejected=True,integer_edge_contact=True)

def decoded_wire_shapes(odb, wire):
    """Port of pinned OpenDB dbWireShapeItr using the exported decoder.

    Geometry rules follow OpenROAD dcf36133 dbWireShapeItr.cpp/dbShape.h.
    Virtual path relationships never create physical metal. RECT operands
    are read from the encoded stream because getRect lacks Python outputs.
    This adapter still requires native qualification; it is not LVS.
    """
    dec=odb.dbWireDecoder();dec.begin(wire)
    layer=None;previous=None;extension=None;count=0;half=0;nondefault=False
    while True:
        op=dec.next()
        if op==dec.END_DECODE:break
        if op in (dec.PATH,dec.JUNCTION,dec.SHORT,dec.VWIRE):
            layer=dec.getLayer();half=layer.getWidth()//2;count=0
            previous=None;extension=None
        elif op==dec.RULE:
            half=dec.getRule().getWidth()//2;nondefault=True
        elif op in (dec.POINT,dec.POINT_EXT):
            values=dec.getPoint_ext() if op==dec.POINT_EXT else dec.getPoint()
            x,y=values[:2];ext=values[2] if op==dec.POINT_EXT else None
            raw=wire.getOpcode(dec.getJunctionId())
            if isinstance(raw,str):raw=ord(raw)
            elif isinstance(raw,bytes):raw=raw[0]
            raw=int(raw)&0x1f
            assert raw in (4,5,6),('Unexpected point opcode',raw)
            count+=1
            if raw==6:
                previous=(x,y)
                if ext is not None:extension=ext;continue
                if extension is not None:extension=None;continue
                if count<=1:continue
                rect=(x-half,y-half,x+half,y+half)
            elif count==1:
                previous=(x,y);extension=ext;continue
            else:
                assert previous is not None
                px,py=previous;assert px==x or py==y,'Non-orthogonal wire'
                width=half;direction=str(layer.getDirection())
                if not nondefault and ((raw==4 and direction=='VERTICAL')or(raw==5 and direction=='HORIZONTAL')):
                    width=layer.getWrongWayWidth()//2
                start=half if extension is None else extension
                end=half if ext is None else ext
                if px==x:
                    lo,hi=(py-start,y+end) if y>py else (y-end,py+start)
                    if y==py:lo,hi=y-width,y+width
                    rect=(x-width,lo,x+width,hi)
                else:
                    lo,hi=(px-start,x+end) if x>px else (x-end,px+start)
                    rect=(lo,y-width,hi,y+width)
            previous=(x,y);extension=ext
            yield ('rect',layer,odb.Rect(*rect))
        elif op in (dec.VIA,dec.TECH_VIA):
            assert previous is not None,'Via before first point'
            via=dec.getVia() if op==dec.VIA else dec.getTechVia()
            assert via and via.getBBox(),'Via without physical geometry'
            yield ('via',via,previous)
            layer=dec.getLayer()
            if not nondefault:half=layer.getWidth()//2
            extension=None
        elif op==dec.RECT:
            assert previous is not None,'Patch before first point'
            i=dec.getJunctionId();d=[wire.getData(i+j)for j in range(4)];x,y=previous
            yield ('rect',layer,odb.Rect(x+d[0],y+d[1],x+d[2],y+d[3]))
        else:assert op in (dec.ITERM,dec.BTERM),('Unsupported wire opcode',op)


def qualify_native_decoder(odb,block):
    """Encode independent physical fixtures through the real OpenDB API.

    Fixtures exist only in memory and are removed before auditing the design.
    Expected rectangles are specified independently of the decoder algorithm.
    """
    layer=block.getTech().findLayer('Metal2');assert layer
    h=layer.getWidth()//2;wrong=layer.getWrongWayWidth()//2
    direction=str(layer.getDirection());assert direction in ('HORIZONTAL','VERTICAL')
    hx=wrong if direction=='VERTICAL' else h
    vy=wrong if direction=='HORIZONTAL' else h
    results={}
    def fixture(name,encode,expected):
        netname='__nssoc_decoder_fixture_'+name
        assert not block.findNet(netname)
        net=odb.dbNet.create(block,netname)
        try:
            wire=odb.dbWire.create(net);enc=odb.dbWireEncoder();enc.begin(wire)
            enc.newPath(layer,'ROUTED');encode(enc);enc.end()
            actual=[]
            for kind,obj,g in decoded_wire_shapes(odb,wire):
                if kind=='rect':actual.append((kind,obj.getName(),g.xMin(),g.yMin(),g.xMax(),g.yMax()))
                else:actual.append((kind,obj.getName(),*g))
            assert actual==expected,dict(fixture=name,expected=expected,actual=actual)
            results[name]=dict(passed=True,shapes=len(actual))
        finally:odb.dbNet.destroy(net)
    def r(a,b,c,d):return ('rect',layer.getName(),a,b,c,d)
    fixture('horizontal_forward',lambda e:(e.addPoint(10000,10000),e.addPoint(20000,10000)),[r(10000-h,10000-hx,20000+h,10000+hx)])
    fixture('horizontal_reverse',lambda e:(e.addPoint(20000,10000),e.addPoint(10000,10000)),[r(10000-h,10000-hx,20000+h,10000+hx)])
    fixture('vertical_forward',lambda e:(e.addPoint(10000,10000),e.addPoint(10000,20000)),[r(10000-vy,10000-h,10000+vy,20000+h)])
    fixture('vertical_reverse',lambda e:(e.addPoint(10000,20000),e.addPoint(10000,10000)),[r(10000-vy,10000-h,10000+vy,20000+h)])
    fixture('explicit_extensions',lambda e:(e.addPoint(10000,10000,30,0),e.addPoint(20000,10000,70,0)),[r(9970,10000-hx,20070,10000+hx)])
    fixture('patch_rectangle',lambda e:(e.addPoint(10000,10000),e.addRect(-30,-70,80,90)),[r(9970,9930,10080,10090)])
    def junction(e):
        j=e.addPoint(10000,10000);e.addPoint(20000,10000);e.newPath(j,'ROUTED');e.addPoint(10000,20000)
    fixture('junction_branch',junction,[r(10000-h,10000-hx,20000+h,10000+hx),r(10000-vy,10000-h,10000+vy,20000+h)])
    def collinear(e):
        e.addPoint(10000,10000);e.addPoint(20000,10000,70,0);e.addPoint(20000,10000);e.addPoint(20000,20000)
    fixture('collinear_extension_cancel',collinear,[r(10000-h,10000-hx,20070,10000+hx),r(20000-vy,10000-h,20000+vy,20000+h)])
    def virtual(e):
        j=e.addPoint(10000,10000);e.addPoint(20000,10000)
        e.newPathVirtualWire(j,layer,'ROUTED');e.addPoint(30000,10000);e.addPoint(40000,10000)
    fixture('virtual_wire_not_metal',virtual,[r(10000-h,10000-hx,20000+h,10000+hx),r(30000-h,10000-hx,40000+h,10000+hx)])
    candidates=[v for v in block.getTech().getVias()if v.getBottomLayer().getName()==layer.getName() or v.getTopLayer().getName()==layer.getName()]
    assert candidates,'No native technology via fixture available'
    v=candidates[0]
    fixture('native_tech_via_location',lambda e:(e.addPoint(10000,10000),e.addTechVia(v)),[('via',v.getName(),10000,10000)])
    block_vias=list(block.getVias())
    assert block_vias,'No native block via fixture available'
    v=block_vias[0]
    def block_via(e):
        e.newPath(v.getBottomLayer(),'ROUTED');e.addPoint(10000,10000);e.addVia(v)
    fixture('native_block_via_location',block_via,[('via',v.getName(),10000,10000)])
    assert not any(n.getName().startswith('__nssoc_decoder_fixture_')for n in block.getNets())
    return results


def main():
    import odb
    out=Path(os.environ['NSSOC_PHYSICAL_ROUTE_OUT']);path=Path(os.environ['NSSOC_PHYSICAL_ROUTE_ODB']);before=hashlib.sha256(path.read_bytes()).hexdigest()
    db=odb.dbDatabase.create();odb.read_db(db,str(path));block=db.getChip().getBlock();all_shapes=defaultdict(list);reports=[];missing=[];fault=None;unwired=[]
    qualification=qualify_native_decoder(odb,block)
    (out/'native-decoder-qualification.json').write_text(json.dumps(qualification,indent=2)+'\n')
    for net in block.getNets():
        name=net.getName();rows=[];counter=0
        def add(layer,rect,group,kind,label,dx=0,dy=0):
            if not layer or layer.getRoutingLevel()==0:return
            row=(rect.xMin()+dx,rect.yMin()+dy,rect.xMax()+dx,rect.yMax()+dy,layer.getName(),group,kind,label)
            rows.append(row);all_shapes[row[4]].append((*row[:4],name,label))
        def via_shape(via,x,y,group,kind):
            assert via
            metal_layers=set()
            for box in via.getBoxes():
                layer=box.getTechLayer()
                if layer.getRoutingLevel()>0:metal_layers.add(layer.getName())
                add(layer,box,group,kind,via.getName(),x,y)
            assert len(metal_layers)>=2,'Via must expose both routing-metal landings'
        for t in net.getITerms():
            label=t.getInst().getName()+'/'+t.getMTerm().getName();g='pin:'+label
            start=len(rows)
            for layer,rect in t.getGeometries():add(layer,rect,g,'pin',label)
            if len(rows)==start:missing.append(dict(net=name,terminal=label))
        for t in net.getBTerms():
            g='port:'+t.getName();start=len(rows)
            for p in t.getBPins():
                for box in p.getBoxes():
                    assert not box.isVia();add(box.getTechLayer(),box,g,'pin',g)
            if len(rows)==start:missing.append(dict(net=name,terminal=g))
        w=net.getWire()
        if w:
            for kind,obj,geometry in decoded_wire_shapes(odb,w):
                counter+=1;group='wire:'+str(counter)
                if kind=='via':via_shape(obj,*geometry,group,'wire')
                else:add(obj,geometry,group,'wire',group)
        for sw in net.getSWires():
            for box in sw.getWires():
                counter+=1;group='special:'+str(counter)
                if box.isVia():via_shape(box.getTechVia()or box.getBlockVia(),*box.getViaXY(),group,'special')
                else:add(box.getTechLayer(),box,group,'special',group)
        if str(net.getSigType())in['POWER','GROUND']:continue
        parts=components(rows);terminals={row[5]for row in rows if row[6]=='pin'}
        if not w and len(terminals)>1:unwired.append(dict(net=name,components=len(parts),terminals=len(terminals),pin_shapes=len(rows)))
        if len(parts)>1:reports.append(dict(net=name,components=len(parts),terminals=len(terminals),component_summary=[dict(shapes=len(ids),terminals=sorted({rows[i][7]for i in ids if rows[i][6]=='pin'}))for ids in parts]))
        if fault is None and len(parts)==1 and len(terminals)>1:
            removed=[row for row in rows if row[6]=='pin']
            if len(components(removed))>1:fault=dict(net=name,removed_route_shapes=len(rows)-len(removed),detected_components=len(components(removed)))
    assert fault,'No physical disconnection negative control could be exercised'
    counts=Counter();examples=[]
    for layer,rows in all_shapes.items():
        for ia,ib in inter_net_contacts(rows,10*block.getDbUnitsPerMicron()):
            prev,row=rows[ia],rows[ib]
            counts[layer+':'+':'.join(sorted([prev[4],row[4]]))]+=1
            if len(examples)<100:examples.append(dict(layer=layer,a=prev,b=row))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    report=dict(native_decoder_qualification=qualification,source_odb_sha256=before,signal_nets_with_disconnected_geometry=reports,unwired_multi_terminal_nets=unwired,terminals_without_geometry=missing,inter_net_contact_pairs=sum(counts.values()),contact_counts=dict(counts),contact_examples=examples,synthetic_controls=self_test(),actual_route_removal_control=fault,source_unchanged=True,accepted=False,full_gds_lvs=False,scope='Native wire/via and LEF terminal geometry; each library terminal is treated as internally electrically equivalent. Does not prove hidden cell/macro GDS, transistor connectivity, or foundry DRC.')
    (out/'physical-route-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    assert not reports and not missing and not counts,'Physical route continuity/contact checks failed'
if __name__=='__main__':
    if '--self-test'in sys.argv:print(json.dumps(self_test(),indent=2))
    else:main()
