#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Export actual signal route shapes and placed LEF pin geometry, read-only."""
import gzip,json,os,collections
from pathlib import Path
import odb
OUT=Path(os.environ['NSSOC_ROUTE_AUDIT_OUT'])
def box(shape):return [shape.xMin(),shape.yMin(),shape.xMax(),shape.yMax()]
def main():
    db=odb.dbDatabase.create();odb.read_db(db,str(OUT/'source/routed.odb'));block=db.getChip().getBlock()
    result=dict(status='RUNNING',accepted=False,instances=len(block.getInsts()),nets=len(block.getNets()),exported_nets=0,shapes=0,ndr_nets={},power_geometry_in_scope=False)
    added=int(os.environ.get('NSSOC_GEOMETRY_ADDED_BUFFERS','0'))
    assert added in (0,2,3,50,54),'Unsupported source-verified ECO size'
    assert result['instances']==113791+added and result['nets']==113863+added
    (OUT/'native-capabilities.json').write_text(json.dumps({n:dir(getattr(odb,n)) for n in ('dbWireDecoder','dbITerm','dbWire')},indent=2)+'\n')
    with gzip.open(OUT/'signal-geometry.jsonl.gz','wt') as output:
        for net in block.getNets():
            if str(net.getSigType()) in ('POWER','GROUND'):continue
            terms=list(net.getITerms());ports=list(net.getBTerms());wire=net.getWire()
            if len(terms)+len(ports)<2 and not wire:continue
            row=dict(net=net.getName(),shapes=[],expected_pins=[],virtual_shorts=0,ndr_width_observations=[])
            def add(layer,rect,kind,join=None):
                assert layer and str(layer.getType())=='ROUTING'
                assert rect[0]<rect[2] and rect[1]<rect[3]
                row['shapes'].append(dict(layer=layer.getName(),box=rect,kind=kind,join=join))
            for term in terms:
                name='I:'+term.getInst().getName()+'/'+term.getMTerm().getName();row['expected_pins'].append(name)
                for layer,rect in term.getGeometries():
                    if layer and str(layer.getType())=='ROUTING':add(layer,box(rect),'pin',name)
            for term in ports:
                name='B:'+term.getName();row['expected_pins'].append(name)
                for pin in term.getBPins():
                    for shape in pin.getBoxes():
                        layer=shape.getTechLayer()
                        if layer and str(layer.getType())=='ROUTING':add(layer,box(shape),'pin',name)
            rule=net.getNonDefaultRule();via_index=0
            if wire:
                d=odb.dbWireDecoder();d.begin(wire);previous=None;extension=None;half=0;active_rule=None
                physical_bounds=[];length=0
                def segment(a,b,ae,be,w):
                    assert a[0]==b[0] or a[1]==b[1], 'Nonorthogonal route'
                    start=w if ae is None else ae;end=w if be is None else be
                    if a[1]==b[1]:
                        return [a[0]-start,a[1]-w,b[0]+end,b[1]+w] if a[0]<=b[0] else [b[0]-end,b[1]-w,a[0]+start,a[1]+w]
                    return [a[0]-w,a[1]-start,b[0]+w,b[1]+end] if a[1]<=b[1] else [b[0]-w,b[1]-end,a[0]+w,a[1]+start]
                while True:
                    op=d.next()
                    if op==d.END_DECODE:break
                    layer=d.getLayer()
                    if op in (d.PATH,d.JUNCTION,d.SHORT,d.VWIRE):
                        previous=None;extension=None;half=layer.getWidth()//2;active_rule=None
                        row['virtual_shorts']+=int(op in (d.SHORT,d.VWIRE))
                        assert layer.getWrongWayWidth() in (0,layer.getWidth()),'Unsupported unequal wrong-way geometry width'
                    elif op==d.RULE:
                        lr=d.getRule();half=lr.getWidth()//2;active_rule=lr.getNonDefaultRule()
                    elif op in (d.POINT,d.POINT_EXT):
                        values=d.getPoint_ext() if op==d.POINT_EXT else d.getPoint()
                        point=list(values[:2]);ext=values[2] if op==d.POINT_EXT else None
                        if previous is not None:
                            if point==previous and (ext is not None or extension is not None):
                                extension=ext;continue
                            rect=segment(previous,point,extension,ext,half);add(layer,rect,'wire');physical_bounds.append(rect)
                            length+=abs(point[0]-previous[0])+abs(point[1]-previous[1])
                            if rule:
                                lr=rule.getLayerRule(layer)
                                if lr:row['ndr_width_observations'].append(dict(layer=layer.getName(),box=rect,actual_width_dbu=half*2,required_width_dbu=lr.getWidth(),required_spacing_dbu=lr.getSpacing()))
                        previous=point;extension=ext
                    elif op in (d.VIA,d.TECH_VIA):
                        assert previous is not None
                        via=d.getTechVia() if op==d.TECH_VIA else d.getVia();boxes=list(via.getBoxes())
                        assert any(str(v.getTechLayer().getType())=='CUT' for v in boxes),'Via without physical cut'
                        group='V:'+str(via_index);via_index+=1
                        for v in boxes:
                            vl=v.getTechLayer();rect=[v.xMin()+previous[0],v.yMin()+previous[1],v.xMax()+previous[0],v.yMax()+previous[1]]
                            physical_bounds.append(rect)
                            if str(vl.getType())=='ROUTING':add(vl,rect,'via',group)
                        half=layer.getWidth()//2
                        if active_rule:
                            lr=active_rule.getLayerRule(layer)
                            if lr:half=lr.getWidth()//2
                        extension=None
                    elif op==d.RECT:
                        assert previous is not None
                        index=d.getJunctionId();assert index+3<wire.length()
                        delta=[wire.getData(index+i) for i in range(4)]
                        rect=[delta[0]+previous[0],delta[1]+previous[1],delta[2]+previous[0],delta[3]+previous[1]]
                        add(layer,rect,'patch');physical_bounds.append(rect)
                    else:assert op in (d.ITERM,d.BTERM),('Unhandled native wire opcode',op)
                assert physical_bounds,net.getName()
                measured=[min(v[0] for v in physical_bounds),min(v[1] for v in physical_bounds),max(v[2] for v in physical_bounds),max(v[3] for v in physical_bounds)]
                # Pinned SWIG leaves optional<Rect> opaque; never claim a
                # bounding-box comparison that the runtime cannot perform.
                row['decoded_wire_bbox']=measured
                row['native_wire_bbox_verified']=False
                shape_length=sum(abs((v['box'][2]-v['box'][0])-(v['box'][3]-v['box'][1])) for v in row['shapes'] if v['kind'] in ('wire','patch'))
                assert shape_length==wire.getLength(),('Native shape-length mismatch',net.getName(),shape_length,wire.getLength())
                row['native_shape_length_verified']=True
                row['decoded_centerline_length_dbu']=length
                row['native_wire_length_dbu']=wire.getLength()
            if rule:result['ndr_nets'][net.getName()]=dict(rule=rule.getName(),segments=len(row['ndr_width_observations']),below_rule_width=sum(v['actual_width_dbu'] is not None and v['actual_width_dbu']<v['required_width_dbu'] for v in row['ndr_width_observations']))
            output.write(json.dumps(row,separators=(',',':'))+'\n');result['exported_nets']+=1;result['shapes']+=len(row['shapes'])
    assert len(result['ndr_nets'])==55
    result.update(status='COMPLETE_NATIVE_SIGNAL_GEOMETRY_EXPORT_NOT_SIGNOFF',scope='Actual routed shapes, physical via boxes, placed LEF pins. Pin fragments are electrically equivalent within each library terminal only. Power, inter-net shorts, NDR spacing, macro transistor LVS and final timing remain separate.')
    (OUT/'export.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
