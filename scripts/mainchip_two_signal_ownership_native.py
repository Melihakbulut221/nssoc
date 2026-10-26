#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only native ownership census. No DB/DEF writing and no routing commands."""
import hashlib,json
import odb
import mainchip_two_signal_geometry as g

def box(value):
    return g.rect([value.xMin(),value.yMin(),value.xMax(),value.yMax()])

def layer_record(layer):
    return dict(name=layer.getName(),width=layer.getWidth(),
                wrong_way_width=layer.getWrongWayWidth(),direction=str(layer.getDirection()))

def via_record(via):
    assert via is not None and via.getBBox()is not None,'Missing native via geometry'
    return dict(name=via.getName(),top=via.getTopLayer().getId(),bottom=via.getBottomLayer().getId(),
        box=box(via.getBBox()),components=[
            dict(layer=b.getTechLayer().getId(),box=box(b),box_id=b.getId())for b in via.getBoxes()])

def native_wire(db,block,wire,layers):
    raw=[[wire.getOpcode(i),wire.getData(i)]for i in range(wire.length())]
    catalog=dict(layers={},rules={},vias={})
    for op,data in raw:
        kind=op&g.MASK
        if kind in (0,1,13):
            assert data in layers,'Missing native layer ID'
            catalog['layers'][data]=layers[data]
        elif kind==3:
            scope='block'if op&128 else'tech'
            r=odb.dbTechLayerRule.getTechLayerRule(block if scope=='block'else db.getTech(),data)
            assert r is not None,'Missing native layer rule'
            catalog['rules'][scope+':'+str(data)]=r.getWidth()
        elif kind in (7,8):
            scope='block'if kind==7 else'tech'
            via=odb.dbVia.getVia(block,data)if kind==7 else odb.dbTechVia.getTechVia(db.getTech(),data)
            v=via_record(via);catalog['vias'][scope+':'+str(data)]=v
            for lid in [v['top'],v['bottom'],*[x['layer']for x in v['components']]]:
                assert lid in layers;catalog['layers'][lid]=layers[lid]
    result=g.project_wire(raw,catalog)
    for row in result['native_coordinate_checks']:
        actual=wire.getCoord(row['index'])
        assert type(actual)in (list,tuple)and list(actual)==row['xy'],('Native coordinate mismatch',row,actual)
    result.update(raw=raw,catalog=catalog,native_coordinate_checks_passed=True)
    return result

def placed_box(transform,value):
    # Point& is an ordinary SWIG input; unlike Rect&, it is not an output-only typemap.
    points=[odb.Point(value.xMin(),value.yMin()),odb.Point(value.xMax(),value.yMax())]
    for point in points:transform.apply(point)
    x=[p.x()for p in points];y=[p.y()for p in points]
    return g.rect([min(x),min(y),max(x),max(y)])

def collect(db,block):
    markers=g.marker_boxes(block.getDbUnitsPerMicron())
    assert db.getTech().getDbUnitsPerMicron()==block.getDbUnitsPerMicron()
    layers={x.getId():layer_record(x)for x in db.getTech().getLayers()}
    assert len(layers)==len(list(db.getTech().getLayers()))
    source_names={g.CLOCK,*g.TARGETS}
    nets=list(block.getNets());assert len(nets)==143820
    assert source_names<={n.getName()for n in nets}
    rows=[];full_sources={};counts={};stream=hashlib.sha256()
    def feed(row):
        kind=row['kind'];counts[kind]=counts.get(kind,0)+1
        raw=g.canonical(row);stream.update(len(raw).to_bytes(8,'big'));stream.update(raw)
        if any(row['layer']==m['layer']and g.overlap(row['box'],m['box'])for m in markers):
            row=dict(row)
            row['source_indices']=[[m['ordinal'],i]for m in markers
                for i,name in enumerate(m['source_names'])if name==row['owner']]
            rows.append(row)
    for net in sorted(nets,key=lambda n:n.getName()):
        name=net.getName();wire=net.getWire()
        if name in source_names:
            assert not net.isSpecial()and not list(net.getSWires()),'Source net has special material'
            if name in g.TARGETS:
                assert str(net.getSigType())=='SIGNAL'and str(net.getWireType())=='ROUTED'
                assert wire is not None
                kinds=[wire.getOpcode(i)&224 for i in range(wire.length())if wire.getOpcode(i)&31 in (0,1,2,13)]
                assert kinds and set(kinds)=={96},'Target path is not actually encoded ROUTED'
        if wire is not None:
            projected=native_wire(db,block,wire,layers)
            route_class=str(net.getWireType())
            if name in source_names:
                full_sources[name]=dict(net_id=net.getId(),metadata_class=route_class,
                    sigtype=str(net.getSigType()),wire_id=wire.getId(),projection=projected,pins=[])
            # Retain each raw wire in the complete streaming census, even if far from markers.
            raw=g.canonical([name,wire.getId(),projected['raw'],projected['catalog']])
            stream.update(len(raw).to_bytes(8,'big'));stream.update(raw)
            counts['raw-wire']=counts.get('raw-wire',0)+1
            for ordinal,shape in enumerate(projected['shapes']):
                feed(dict(shape,record_id=['net',net.getId(),'wire',wire.getId(),ordinal],
                    owner=name,route_class=route_class))
        else:assert name not in source_names,'Source net is unwired'
        for iterm in net.getITerms():
            geometries=iterm.getGeometries()
            if name in source_names:
                full_sources[name]['pins'].append(dict(kind='iterm',id=iterm.getId(),
                    instance=iterm.getInst().getName(),master=iterm.getInst().getMaster().getName(),
                    terminal=iterm.getMTerm().getName(),
                    geometries=[[layer.getName(),box(r)]for layer,r in geometries]))
            for ordinal,(layer,r)in enumerate(geometries):
                feed(dict(record_id=['iterm',iterm.getId(),ordinal],owner=name,kind='iterm-pin',
                    layer=layer.getName(),box=box(r),instance=iterm.getInst().getName(),
                    master=iterm.getInst().getMaster().getName(),terminal=iterm.getMTerm().getName()))
        for bterm in net.getBTerms():
            for pin in bterm.getBPins():
                for ordinal,b in enumerate(pin.getBoxes()):
                    assert not b.isVia(),'Unprojected BPin via'
                    row=dict(record_id=['bterm',bterm.getId(),'bpin',pin.getId(),ordinal],
                        owner=name,kind='bterm-pin',layer=b.getTechLayer().getName(),box=box(b),
                        terminal=bterm.getName(),native_box_id=b.getId())
                    if name in source_names:full_sources[name]['pins'].append(row)
                    feed(row)
        for swire in net.getSWires():
            for ordinal,b in enumerate(swire.getWires()):
                identity=['net',net.getId(),'swire',swire.getId(),ordinal]
                if b.isVia():
                    tech=b.getTechVia();via=tech if tech is not None else b.getBlockVia()
                    v=via_record(via);xy=list(b.getViaXY());assert len(xy)==2
                    for component_index,component in enumerate(v['components']):
                        r=component['box']
                        feed(dict(record_id=[*identity,component_index],owner=name,kind='special-via',
                            layer=layers[component['layer']]['name'],
                            box=[r[0]+xy[0],r[1]+xy[1],r[2]+xy[0],r[3]+xy[1]],
                            via_definition=v,origin_xy=xy,native_box_id=b.getId()))
                else:
                    feed(dict(record_id=identity,owner=name,kind='special-wire',
                        layer=b.getTechLayer().getName(),box=box(b),native_box_id=b.getId()))
    for ob in block.getObstructions():
        b=ob.getBBox();assert not b.isVia(),'Unprojected block obstruction via'
        feed(dict(record_id=['block-obstruction',ob.getId()],owner=None,kind='block-obstruction',
                  layer=b.getTechLayer().getName(),box=box(b),native_box_id=b.getId()))
    master_cache={}
    instances=sorted(block.getInsts(),key=lambda i:i.getName());assert len(instances)==153130
    for instance in instances:
        master=instance.getMaster();key=(master.getLib().getName(),master.getName())
        if key not in master_cache:
            material=list(master.getObstructions(True))
            for b in material:assert not b.isVia(),'Unprojected master obstruction via'
            master_cache[key]=material
        transform=instance.getTransform()
        for ordinal,b in enumerate(master_cache[key]):
            feed(dict(record_id=['instance',instance.getId(),'obstruction',ordinal],owner=None,
                kind='master-obstruction',layer=b.getTechLayer().getName(),box=placed_box(transform,b),
                master=list(key),instance=instance.getName(),native_box_id=b.getId(),
                original_box=box(b),origin=list(instance.getOrigin()),orientation=str(instance.getOrient())))
    # IDs are structured native namespace tuples, serialized without erasing multiplicity.
    for row in rows:row['record_id']=json.dumps(row['record_id'],separators=(',',':'))
    decision=g.ownership_decision(markers,rows)
    decision.update(native_geometry_census=counts,native_geometry_sha256=stream.hexdigest(),
        full_source_material=full_sources,source_net_count=3,all_net_count=len(nets),
        instance_count=len(instances),dbu_per_micron=block.getDbUnitsPerMicron(),
        read_only=True,scope='All ordinary wire opcode-derived boxes, every via component, native placed ITerm/BTerm pins, special-wire boxes/vias, block and transformed decomposed master obstruction boxes. Polygon segmentation identity is not claimed.')
    assert set(full_sources)==source_names
    return decision
