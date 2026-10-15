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
    assert result['instances']==113791 and result['nets']==113863
    (OUT/'native-capabilities.json').write_text(json.dumps({n:dir(getattr(odb,n)) for n in ('dbWirePathItr','dbWirePath','dbWirePathShape','dbITermShapeItr','dbShape')},indent=2)+'\n')
    with gzip.open(OUT/'signal-geometry.jsonl.gz','wt') as output:
        for net in block.getNets():
            if str(net.getSigType()) in ('POWER','GROUND'):continue
            terms=list(net.getITerms());ports=list(net.getBTerms());wire=net.getWire()
            if len(terms)+len(ports)<2 and not wire:continue
            row=dict(net=net.getName(),shapes=[],expected_pins=[],virtual_shorts=0,ndr_width_observations=[])
            def add(layer,rect,kind,join=None):
                assert layer and layer.getType()=='ROUTING'
                assert rect[0]<rect[2] and rect[1]<rect[3]
                row['shapes'].append(dict(layer=layer.getName(),box=rect,kind=kind,join=join))
            for term in terms:
                name='I:'+term.getInst().getName()+'/'+term.getMTerm().getName();row['expected_pins'].append(name)
                iterator=odb.dbITermShapeItr(True);iterator.begin(term);shape=odb.dbShape()
                while iterator.next(shape):
                    layer=shape.getTechLayer()
                    if layer and str(layer.getType())=='ROUTING':add(layer,box(shape),'pin',name)
            for term in ports:
                name='B:'+term.getName();row['expected_pins'].append(name)
                for pin in term.getBPins():
                    for shape in pin.getBoxes():
                        layer=shape.getTechLayer()
                        if layer and str(layer.getType())=='ROUTING':add(layer,box(shape),'pin',name)
            rule=net.getNonDefaultRule();via_index=0
            if wire:
                iterator=odb.dbWirePathItr();iterator.begin(wire);path=odb.dbWirePath();part=odb.dbWirePathShape()
                while iterator.getNextPath(path):
                    row['virtual_shorts']+=int(path.is_short);previous=[path.point.x(),path.point.y()]
                    while iterator.getNextShape(part):
                        shape=part.shape;point=[part.point.x(),part.point.y()]
                        if shape.isVia():
                            via=shape.getTechVia() or shape.getVia();assert via
                            boxes=list(via.getBoxes());assert any(str(b.getTechLayer().getType())=='CUT' for b in boxes),'Via without physical cut'
                            group='V:'+str(via_index);via_index+=1
                            for b in boxes:
                                layer=b.getTechLayer()
                                if str(layer.getType())=='ROUTING':add(layer,[b.xMin()+point[0],b.yMin()+point[1],b.xMax()+point[0],b.yMax()+point[1]],'via',group)
                        else:
                            layer=shape.getTechLayer();add(layer,box(shape),'wire')
                            if rule:
                                lr=rule.getLayerRule(layer)
                                if lr:
                                    dx=point[0]-previous[0];dy=point[1]-previous[1]
                                    width=shape.getDY() if dx and not dy else shape.getDX() if dy and not dx else None
                                    row['ndr_width_observations'].append(dict(layer=layer.getName(),box=box(shape),actual_width_dbu=width,required_width_dbu=lr.getWidth(),required_spacing_dbu=lr.getSpacing()))
                        previous=point
            if rule:result['ndr_nets'][net.getName()]=dict(rule=rule.getName(),segments=len(row['ndr_width_observations']),below_rule_width=sum(v['actual_width_dbu'] is not None and v['actual_width_dbu']<v['required_width_dbu'] for v in row['ndr_width_observations']))
            output.write(json.dumps(row,separators=(',',':'))+'\n');result['exported_nets']+=1;result['shapes']+=len(row['shapes'])
    assert len(result['ndr_nets'])==55
    result.update(status='COMPLETE_NATIVE_SIGNAL_GEOMETRY_EXPORT_NOT_SIGNOFF',scope='Actual routed shapes, physical via boxes, placed LEF pins. Pin fragments are electrically equivalent within each library terminal only. Power, inter-net shorts, NDR spacing, macro transistor LVS and final timing remain separate.')
    (OUT/'export.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
