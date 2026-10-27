#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only ownership using acquired raw-OID lookups and separate scoped identities."""
import hashlib,json
import odb
import mainchip_two_signal_geometry as g
import mainchip_original_clock_restoration as c

API_PATH='docs/evidence/mainchip-two-signal-api-probe-native-pass-20261027.api-census.json'
API_SHA='6fd2b5881c98fb1c57a7ba774a03862d5c7ce561da8a9e8592afbce0c732aea8'
IDENTITY_SCOPE='Raw wire operands remain database OIDs. Named parents and anonymous container ordinals below are scoped observation identities, never database OIDs or claims of cross-serialization ordinal stability.'

def api_evidence():
    raw=c.regular(c.ROOT/API_PATH).read_bytes()
    assert len(raw)==72093 and c.digest(raw)==API_SHA,'Exact acquired API census differs'
    value=json.loads(raw)
    assert value['status']=='COMPLETE_READ_ONLY_API_IDENTITY_CENSUS_NOT_OWNERSHIP_QUALIFICATION'
    assert value['input']==dict(member='work/drc-observed.odb',bytes=213740873,
        sha256='444f75328e4065ae1fd1fdf1b872980931fcbae8ec8a62182a833e48230bf9b1')
    assert value['all_net_count']==143820 and value['all_instance_count']==153130
    assert value['complete_raw_opcode_data_pairs']==13905578
    assert value['unique_raw_terminal_OID_joins']==0 and value['raw_terminal_named_joins']==[]
    assert value['every_block_terminal_reconciled_with_connected_net_census']is True
    assert value['terminal_checks']==[dict(label=x,status='PASS')for x in
        ('destroy-read-only-database','unchanged-source-file')]
    for key in ('accepted','full_phy_accepted','ownership_eligible','native_routing_started','source_geometry_mutated'):
        assert value[key]is False
    return value

def box(value):
    return g.rect([value.xMin(),value.yMin(),value.xMax(),value.yMax()])

def layer_record(layer):
    return dict(name=layer.getName(),width=layer.getWidth(),
                wrong_way_width=layer.getWrongWayWidth(),direction=str(layer.getDirection()))

def observed_layer(layer):
    assert layer is not None,'Missing native raw layer lookup'
    return dict(layer_record(layer),layer_number_observed_not_used_as_OID=g.integer(layer.getNumber()),
        routing_level_observed_not_used_as_OID=g.integer(layer.getRoutingLevel()))

def named_layers(tech,proof):
    rows={}
    for layer in tech.getLayers():
        row=layer_record(layer);name=row['name']
        assert type(name)is str and name and name not in rows,'Duplicate or invalid native layer name'
        g.integer(row['width']);g.integer(row['wrong_way_width'])
        assert row['direction']in ('HORIZONTAL','VERTICAL','NONE')
        rows[name]=row
    assert len(rows)==proof['complete_census_counts']['technology-layer'],'Technology layer census changed'
    return rows

def via_record(via,layers):
    assert via is not None and via.getBBox()is not None,'Missing native via geometry'
    top=via.getTopLayer().getName();bottom=via.getBottomLayer().getName()
    assert top in layers and bottom in layers,'Via layer absent from named layer census'
    components=[]
    for ordinal,b in enumerate(via.getBoxes()):
        assert not b.isVia(),'Nested native via component'
        name=b.getTechLayer().getName();assert name in layers
        components.append(dict(layer=name,box=box(b),component_ordinal=ordinal))
    assert components,'Missing native via components'
    return dict(name=via.getName(),top=top,bottom=bottom,box=box(via.getBBox()),components=components)

def expected_via(row):
    return dict(name=row['name'],top=row['top'],bottom=row['bottom'],box=row['bbox'],
        components=[dict(layer=x['layer'],box=x['rect'],component_ordinal=x['component_ordinal'])
                    for x in row['components']])

def native_wire(db,block,wire,layers,proof):
    raw=[[wire.getOpcode(i),wire.getData(i)]for i in range(wire.length())]
    catalog=dict(layers=dict(layers),path_layers={},rules={},vias={})
    lookups=proof['raw_operand_native_lookups']
    for op,data in raw:
        assert type(op)is int and 0<=op<=255 and type(data)is int,'Invalid native raw operand'
        kind=op&g.MASK
        assert kind not in (9,10),'Raw terminal static getter was not exercised in acquired native census'
        if kind in (0,1,13):
            assert data>0 and str(data)in lookups['layers'],'Unobserved raw layer OID'
            actual=odb.dbTechLayer.getTechLayer(db.getTech(),data)
            row=observed_layer(actual)
            assert row==lookups['layers'][str(data)],'Raw layer OID/name/geometry join differs'
            assert layer_record(actual)==layers[row['name']],'Raw layer differs from independent named census'
            catalog['path_layers'][data]=row['name']
        elif kind==3:
            scope='block'if op&128 else'tech';key=scope+':'+str(data)
            assert data>0 and key in lookups['rules'],'Unobserved raw layer-rule scope/OID'
            r=odb.dbTechLayerRule.getTechLayerRule(block if scope=='block'else db.getTech(),data)
            assert r is not None,'Missing native layer rule'
            width=g.integer(r.getWidth())
            assert dict(width=width)==lookups['rules'][key],'Raw layer-rule width differs'
            catalog['rules'][key]=width
        elif kind in (7,8):
            scope='block'if kind==7 else'tech';key=scope+':'+str(data)
            assert data>0 and scope=='tech'and key in lookups['vias'],'Unobserved raw via static getter scope/OID'
            via=odb.dbTechVia.getTechVia(db.getTech(),data)
            value=via_record(via,layers)
            assert value==expected_via(lookups['vias'][key]),'Raw via OID/name/component join differs'
            catalog['vias'][key]=value
    result=g.project_wire(raw,catalog)
    for row in result['native_coordinate_checks']:
        actual=wire.getCoord(row['index'])
        assert type(actual)in (list,tuple)and list(actual)==row['xy'],('Native coordinate mismatch',row,actual)
    result.update(raw=raw,catalog=catalog,native_coordinate_checks_passed=True,
        identity_scope=IDENTITY_SCOPE)
    return result

def placed_box(transform,value):
    # Point& is an ordinary SWIG input; unlike Rect&, it is not an output-only typemap.
    points=[odb.Point(value.xMin(),value.yMin()),odb.Point(value.xMax(),value.yMax())]
    for point in points:transform.apply(point)
    x=[p.x()for p in points];y=[p.y()for p in points]
    return g.rect([min(x),min(y),max(x),max(y)])

def iterm_key(iterm):
    key=(iterm.getInst().getName(),iterm.getMTerm().getName())
    assert all(type(x)is str and x for x in key),'Invalid named ITerm identity'
    return key

def no_unobserved_material(block):
    fills=list(block.getFills());obstructions=list(block.getObstructions())
    assert not fills,'Nonempty fill census: native fill instance API was not exercised'
    assert not obstructions,'Nonempty block-obstruction census: native instance API was not exercised'
    return dict(metal_fill=0,block_obstruction=0)

def collect(db,block):
    proof=api_evidence()
    assert not list(block.getChildren()),'Child blocks require separate ownership qualification'
    empty=no_unobserved_material(block)
    markers=g.marker_boxes(block.getDbUnitsPerMicron())
    assert db.getTech().getDbUnitsPerMicron()==block.getDbUnitsPerMicron()
    layers=named_layers(db.getTech(),proof)
    source_names={g.CLOCK,*g.TARGETS}
    nets=list(block.getNets());assert len(nets)==143820
    assert len({n.getName()for n in nets})==len(nets),'Duplicate native net name'
    assert source_names<={n.getName()for n in nets}
    rows=[];full_sources={};counts={};stream=hashlib.sha256();raw_stream=hashlib.sha256();raw_pairs=0
    connected_iterms={};connected_bterms={}
    def feed(row):
        kind=row['kind'];counts[kind]=counts.get(kind,0)+1
        raw=g.canonical(row);stream.update(len(raw).to_bytes(8,'big'));stream.update(raw)
        if any(row['layer']==m['layer']and g.overlap(row['box'],m['box'])for m in markers):
            row=dict(row)
            row['source_indices']=[[m['ordinal'],i]for m in markers
                for i,name in enumerate(m['source_names'])if name==row['owner']]
            rows.append(row)
    def pin_geometry(iterm,owner):
        key=iterm_key(iterm);master=iterm.getInst().getMaster()
        master_key=[master.getLib().getName(),master.getName()]
        geometries=iterm.getGeometries()
        if owner in source_names:
            full_sources[owner]['pins'].append(dict(kind='iterm',scoped_identity=['iterm',*key],
                instance=key[0],master=master_key,terminal=key[1],
                geometries=[[layer.getName(),box(r)]for layer,r in geometries]))
        for ordinal,(layer,r)in enumerate(geometries):
            feed(dict(record_id=['iterm',*key,'geometry',ordinal],owner=owner,kind='iterm-pin',
                layer=layer.getName(),box=box(r),instance=key[0],master=master_key,terminal=key[1]))
    def bpin_geometry(bterm,owner):
        name=bterm.getName()
        for pi,pin in enumerate(bterm.getBPins()):
            for ordinal,b in enumerate(pin.getBoxes()):
                assert not b.isVia(),'Unprojected BPin via'
                row=dict(record_id=['bterm',name,'bpin',pi,'box',ordinal],
                    owner=owner,kind='bterm-pin',layer=b.getTechLayer().getName(),box=box(b),
                    terminal=name)
                if owner in source_names:full_sources[owner]['pins'].append(row)
                feed(row)
    for net in sorted(nets,key=lambda n:n.getName()):
        name=net.getName();assert type(name)is str and name
        wire=net.getWire()
        if name in source_names:
            assert not net.isSpecial()and not list(net.getSWires()),'Source net has special material'
            if name in g.TARGETS:
                assert str(net.getSigType())=='SIGNAL'and str(net.getWireType())=='ROUTED'
                assert wire is not None
                kinds=[wire.getOpcode(i)&224 for i in range(wire.length())if wire.getOpcode(i)&31 in (0,1,2,13)]
                assert kinds and set(kinds)=={96},'Target path is not actually encoded ROUTED'
        if wire is not None:
            projected=native_wire(db,block,wire,layers,proof);raw_pairs+=len(projected['raw'])
            raw_proof=g.canonical([['net',name,'wire'],projected['raw']])
            raw_stream.update(len(raw_proof).to_bytes(8,'big'));raw_stream.update(raw_proof)
            route_class=str(net.getWireType())
            if name in source_names:
                full_sources[name]=dict(scoped_identity=['net',name],metadata_class=route_class,
                    sigtype=str(net.getSigType()),wire_identity=['net',name,'wire'],projection=projected,pins=[])
            raw=g.canonical([name,['net',name,'wire'],projected['raw'],projected['catalog']])
            stream.update(len(raw).to_bytes(8,'big'));stream.update(raw)
            counts['raw-wire']=counts.get('raw-wire',0)+1
            for ordinal,shape in enumerate(projected['shapes']):
                feed(dict(shape,record_id=['net',name,'wire','shape',ordinal],
                    owner=name,route_class=route_class))
        else:assert name not in source_names,'Source net is unwired'
        for iterm in net.getITerms():
            key=iterm_key(iterm);assert key not in connected_iterms,'Duplicate connected ITerm'
            assert iterm.getNet()is not None and iterm.getNet().getName()==name
            connected_iterms[key]=name;pin_geometry(iterm,name)
        for bterm in net.getBTerms():
            key=bterm.getName();assert type(key)is str and key and key not in connected_bterms,'Duplicate connected BTerm'
            assert bterm.getNet()is not None and bterm.getNet().getName()==name
            connected_bterms[key]=name;bpin_geometry(bterm,name)
        for si,swire in enumerate(net.getSWires()):
            for ordinal,b in enumerate(swire.getWires()):
                identity=['net',name,'swire',si,'box',ordinal]
                if b.isVia():
                    tech=b.getTechVia();via=tech if tech is not None else b.getBlockVia()
                    v=via_record(via,layers);xy=list(b.getViaXY());assert len(xy)==2
                    for value in xy:g.integer(value)
                    for component_index,component in enumerate(v['components']):
                        r=component['box']
                        feed(dict(record_id=[*identity,'component',component_index],owner=name,kind='special-via',
                            layer=component['layer'],box=[r[0]+xy[0],r[1]+xy[1],r[2]+xy[0],r[3]+xy[1]],
                            via_definition=v,via_namespace='tech'if tech is not None else'block',origin_xy=xy))
                else:
                    feed(dict(record_id=identity,owner=name,kind='special-wire',
                        layer=b.getTechLayer().getName(),box=box(b)))
    all_iterms=list(block.getITerms());all_bterms=list(block.getBTerms())
    assert len({iterm_key(t)for t in all_iterms})==len(all_iterms),'Duplicate block ITerm identity'
    assert len({t.getName()for t in all_bterms})==len(all_bterms),'Duplicate block BTerm identity'
    assert {iterm_key(t):t.getNet().getName()for t in all_iterms if t.getNet()is not None}==connected_iterms,'Connected ITerm census mismatch'
    assert {t.getName():t.getNet().getName()for t in all_bterms if t.getNet()is not None}==connected_bterms,'Connected BTerm census mismatch'
    for iterm in all_iterms:
        if iterm.getNet()is None:pin_geometry(iterm,None)
    for bterm in all_bterms:
        if bterm.getNet()is None:bpin_geometry(bterm,None)
    counts['all-block-iterm']=len(all_iterms);counts['all-block-bterm']=len(all_bterms)
    counts['disconnected-iterm']=len(all_iterms)-len(connected_iterms)
    counts['disconnected-bterm']=len(all_bterms)-len(connected_bterms)
    counts['metal-fill']=empty['metal_fill'];counts['block-obstruction']=empty['block_obstruction']
    assert counts['raw-wire']==proof['complete_census_counts']['ordinary-wire'],'Ordinary-wire census changed'
    assert raw_pairs==proof['complete_raw_opcode_data_pairs'],'Raw opcode/data pair census changed'
    assert raw_stream.hexdigest()==proof['complete_census_sha256']['ordinary-wire'],'Full raw wire stream differs from acquired native census'
    assert len(all_iterms)==proof['complete_census_counts']['instance-terminal'],'Full ITerm census changed'
    assert len(all_bterms)==proof['complete_census_counts']['block-terminal'],'Full BTerm census changed'
    assert counts['disconnected-iterm']==proof['disconnected_iterms']and counts['disconnected-bterm']==proof['disconnected_bterms'],'Disconnected terminal census changed'
    master_cache={}
    instances=sorted(block.getInsts(),key=lambda i:i.getName());assert len(instances)==153130
    assert len({i.getName()for i in instances})==len(instances),'Duplicate native instance name'
    for instance in instances:
        master=instance.getMaster();key=(master.getLib().getName(),master.getName())
        if key not in master_cache:
            material=list(master.getObstructions(True))
            for b in material:assert not b.isVia(),'Unprojected master obstruction via'
            master_cache[key]=material
        transform=instance.getTransform()
        for ordinal,b in enumerate(master_cache[key]):
            feed(dict(record_id=['instance',instance.getName(),'master',*key,'obstruction',ordinal],owner=None,
                kind='master-obstruction',layer=b.getTechLayer().getName(),box=placed_box(transform,b),
                master=list(key),instance=instance.getName(),original_box=box(b),
                origin=list(instance.getOrigin()),orientation=str(instance.getOrient())))
    for row in rows:row['record_id']=json.dumps(row['record_id'],separators=(',',':'))
    decision=g.ownership_decision(markers,rows)
    decision.update(native_geometry_census=counts,native_geometry_sha256=stream.hexdigest(),
        full_source_material=full_sources,source_net_count=3,all_net_count=len(nets),
        instance_count=len(instances),dbu_per_micron=block.getDbUnitsPerMicron(),
        complete_raw_opcode_data_pairs=raw_pairs,complete_raw_wire_sha256=raw_stream.hexdigest(),
        acquired_api_report_sha256=API_SHA,
        read_only=True,identity_scope=IDENTITY_SCOPE,
        scope='All ordinary raw opcode-derived boxes, every via component, every connected/disconnected native placed terminal pin, special-wire boxes/vias and transformed decomposed master obstructions. Empty native fill/block-obstruction censuses are mandatory because their instance getters were not exercised. Polygon segmentation identity is not claimed.')
    assert set(full_sources)==source_names
    return decision

def immutable_material(db,block):
    """Full special/obstacle material with explicit named and parent-scoped identities."""
    proof=api_evidence()
    assert not list(block.getChildren()),'Child blocks require separate material qualification'
    empty=no_unobserved_material(block);layers=named_layers(db.getTech(),proof)
    stream=hashlib.sha256();counts={}
    def feed(kind,row):
        encoded=g.canonical([kind,row]);stream.update(len(encoded).to_bytes(8,'big'));stream.update(encoded)
        counts[kind]=counts.get(kind,0)+1
    feed('required-empty-native-material',empty)
    for name,row in sorted(layers.items()):feed('technology-layer',[name,row])
    masters={(i.getMaster().getLib().getName(),i.getMaster().getName()):i.getMaster()for i in block.getInsts()}
    for key,master in sorted(masters.items()):
        for ordinal,b in enumerate(master.getObstructions(True)):
            assert not b.isVia()
            feed('master-obstruction',[list(key),ordinal,b.getTechLayer().getName(),box(b)])
    for net in sorted(block.getNets(),key=lambda x:x.getName()):
        for si,swire in enumerate(net.getSWires()):
            for ordinal,b in enumerate(swire.getWires()):
                if b.isVia():
                    tech=b.getTechVia();v=tech if tech is not None else b.getBlockVia()
                    material=dict(kind='via',namespace='tech'if tech is not None else'block',
                        via=via_record(v,layers),origin=list(b.getViaXY()),bbox=box(b))
                else:material=dict(kind='box',layer=b.getTechLayer().getName(),box=box(b))
                feed('special-wire',[net.getName(),si,ordinal,material])
    return dict(counts=counts,sha256=stream.hexdigest(),identity_scope=IDENTITY_SCOPE,
        scope='Exact layer name/width/direction, decomposed master obstruction boxes and every special-wire/via component with parent-scoped order/multiplicity. Native fills/block obstructions must remain empty. Instance transforms are independently protected by the qualified placement digest.')
