#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Strict source-bound wire projection and conservative residual-short admission.

No native imports, archive reads, subprocesses or routing. Coordinates are DBU.
Projection follows pinned dbWireShapeItr::next/getPrevPoint/dbShape::setSegment.
The C++ implementation is the authority; this projection requires hosted controls
and a separate native census. It never infers pin ownership from marker net names.
"""
import hashlib,json
from decimal import Decimal

TARGETS=('net36993','net459')
CLOCK='clknet_5_29__leaf_u_ibex.clk'
MARKERS=(
    ('net36993',('947.4200','1789.9400','947.6200','1790.1400')),
    ('net36993',('943.5350','1789.9400','947.6200','1790.1400')),
    ('net459',('950.7800','1789.9400','950.9800','1790.1400')))
PRIMARY='dcf36133a369abc8f3c5e5738cd4d82e4903c0e0'
MASK=31

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def integer(value):
    assert type(value)is int,'Exact integer required'
    return value

def rect(value):
    assert type(value)in (list,tuple)and len(value)==4,'Four-coordinate rectangle required'
    a=[integer(x)for x in value]
    assert a[0]<a[2]and a[1]<a[3],'Positive-area rectangle required'
    return a

def marker_boxes(dbu):
    assert type(dbu)is int and dbu>0
    result=[]
    for ordinal,(target,coordinates)in enumerate(MARKERS):
        scaled=[Decimal(x)*dbu for x in coordinates]
        assert all(x==x.to_integral_value()for x in scaled),'Marker not exactly on native grid'
        result.append(dict(ordinal=ordinal,layer='Metal5',target=target,
                           source_names=([CLOCK,target]if ordinal<2 else[target,CLOCK]),box=rect([int(x)for x in scaled])))
    return result

def overlap(a,b):
    a=rect(a);b=rect(b)
    return max(a[0],b[0])<min(a[2],b[2])and max(a[1],b[1])<min(a[3],b[3])

def intersection(a,b):
    assert overlap(a,b),'No positive-area intersection'
    return [max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]

def segment(previous,current,previous_extension,current_extension,half_width,default_extension):
    px,py=previous;cx,cy=current
    for v in (*previous,*current,half_width,default_extension):integer(v)
    assert half_width>0 and default_extension>0,'Invalid routing width'
    pe=default_extension if previous_extension is None else integer(previous_extension)
    ce=default_extension if current_extension is None else integer(current_extension)
    if cx==px:
        if cy>py:box=[cx-half_width,py-pe,cx+half_width,cy+ce]
        elif cy<py:box=[cx-half_width,cy-ce,cx+half_width,py+pe]
        else:box=[cx-half_width,cy-half_width,cx+half_width,cy+half_width]
    else:
        assert cy==py,'Nonorthogonal wire is not admitted'
        if cx>px:box=[px-pe,cy-half_width,cx+ce,cy+half_width]
        else:box=[cx-ce,cy-half_width,px+pe,cy+half_width]
    return rect(box)

def validate_catalog(catalog):
    assert set(catalog)=={'layers','path_layers','rules','vias'}
    for key,row in catalog['layers'].items():
        assert type(key)is str and key and key==row['name'],'Named native layer catalogue key differs'
        assert set(row)=={'name','width','wrong_way_width','direction'}
        assert type(row['name'])is str and row['name']
        assert row['direction']in ('HORIZONTAL','VERTICAL','NONE')
        assert integer(row['width'])>=0 and integer(row['wrong_way_width'])>=0
    for oid,name in catalog['path_layers'].items():
        assert type(oid)is int and oid>0 and name in catalog['layers'],'Invalid raw path layer join'
    for key,width in catalog['rules'].items():
        kind,oid=key.split(':')
        assert kind in ('block','tech')and str(int(oid))==oid and int(oid)>0
        assert integer(width)>0
    for key,v in catalog['vias'].items():
        kind,oid=key.split(':')
        assert kind in ('block','tech')and str(int(oid))==oid and int(oid)>0
        assert set(v)=={'name','top','bottom','box','components'}
        assert type(v['name'])is str and v['name']
        assert v['top']in catalog['layers']and v['bottom']in catalog['layers']
        rect(v['box']);assert type(v['components'])is list and v['components']
        for ordinal,component in enumerate(v['components']):
            assert set(component)=={'layer','box','component_ordinal'}
            assert component['layer']in catalog['layers']
            assert type(component['component_ordinal'])is int and component['component_ordinal']==ordinal,'Scoped via component ordinal differs'
            rect(component['box'])
    return catalog

def previous_point(raw,index,catalog):
    """Exact backwards opcode walk; explicit bounds/cycle refusal replaces C++ UB."""
    need_x=need_y=need_layer=True;x=y=0;layer=None;visited=set()
    while True:
        assert type(index)is int and 0<=index<len(raw),'Junction reference out of bounds'
        state=(index,need_x,need_y,need_layer)
        assert state not in visited,'Cyclic junction reference'
        visited.add(state)
        op,data=raw[index];kind=op&MASK
        if kind in (0,1):
            if need_layer:
                assert data in catalog['path_layers'],'Unknown path layer'
                layer=catalog['path_layers'][data];need_layer=False
        elif kind==2:
            index=data
            continue
        elif kind==4 and need_x:x=data;need_x=False
        elif kind==5 and need_y:y=data;need_y=False
        elif kind in (7,8)and need_layer:
            v=catalog['vias'][('block:'if kind==7 else'tech:')+str(data)]
            layer=v['top']if op&128 else v['bottom'];need_layer=False
        if not(need_x or need_y or need_layer):return [x,y],layer
        index-=1

def project_wire(raw,catalog):
    """Full ordered wire shapes: raw OIDs join named layers; component ordinals are not native IDs."""
    assert type(raw)is list and raw,'Nonempty raw wire required'
    for row in raw:
        assert type(row)is list and len(row)==2,'Raw opcode/data pair required'
        op,data=row
        assert type(op)is int and 0<=op<=255 and type(data)is int,'Invalid raw opcode/data'
        assert op&MASK<=17,'Unknown wire opcode'
    validate_catalog(catalog)
    i=0;previous=[0,0];extension=None;layer=None;dw=0;count=0;has_width=False
    shapes=[];checks=[]
    def take():
        nonlocal i
        assert i<len(raw),'Truncated wire operand'
        value=raw[i];i+=1
        return value
    def output(index,kind,box,layer_id,**extra):
        assert layer_id in catalog['layers'],'No current native layer'
        shapes.append(dict(opcode_index=index,kind=kind,layer_key=layer_id,
            layer=catalog['layers'][layer_id]['name'],box=rect(box),**extra))
    while i<len(raw):
        index=i;op,data=take();kind=op&MASK
        if kind in (0,1,13):
            assert data in catalog['path_layers'],'Unknown path layer'
            layer=catalog['path_layers'][data];count=0;dw=catalog['layers'][layer]['width']>>1
            # Match C++: has_width is not reset here.
        elif kind==2:
            previous,layer=previous_point(raw,data,catalog)
            checks.append(dict(index=data,xy=list(previous),reason='junction'))
            extension=None;count=0;dw=catalog['layers'][layer]['width']>>1
        elif kind==3:
            dw=catalog['rules'][('block:'if op&128 else'tech:')+str(data)]>>1
            has_width=True
        elif kind in (4,5):
            assert layer is not None,'Coordinate before native path'
            if kind==4:
                current=[data,previous[1]]
                if count==0:
                    op,y=take();assert op&MASK==5,'Initial X must be followed by Y'
                    current[1]=y
                check_index=i-1
            else:
                assert count!=0,'Initial Y without X'
                current=[previous[0],data];check_index=index
            current_extension=None
            if op&128:
                operand_op,current_extension=take()
                assert operand_op&MASK==11,'Extension operand opcode differs'
            checks.append(dict(index=check_index,xy=list(current),reason='coordinate'))
            old_count=count;count+=1
            if old_count:
                half=dw
                direction=catalog['layers'][layer]['direction']
                if not has_width and ((kind==4 and direction=='VERTICAL')or
                                      (kind==5 and direction=='HORIZONTAL')):
                    half=catalog['layers'][layer]['wrong_way_width']//2
                output(index,'wire',segment(previous,current,extension,current_extension,half,dw),
                    layer,from_xy=list(previous),to_xy=list(current),
                    previous_extension=extension,current_extension=current_extension,
                    half_width=half,default_extension=dw)
            previous=current;extension=current_extension
        elif kind==6:
            count+=1
            if op&128:extension=data
            elif extension is not None:extension=None
            elif count>1:
                output(index,'wire',segment(previous,previous,None,None,dw,dw),layer,
                       from_xy=list(previous),to_xy=list(previous),
                       previous_extension=None,current_extension=None,half_width=dw,default_extension=dw)
                extension=None
        elif kind in (7,8):
            key=('block:'if kind==7 else'tech:')+str(data)
            v=catalog['vias'][key]
            layer=v['top']if op&128 else v['bottom']
            if not has_width:dw=catalog['layers'][layer]['width']>>1
            extension=None
            for ordinal,component in enumerate(v['components']):
                box=component['box'];px,py=previous
                output(index,'via',[box[0]+px,box[1]+py,box[2]+px,box[3]+py],
                    component['layer'],via_key=key,via_name=v['name'],component_ordinal=ordinal,
                    component_identity=[key,component['component_ordinal']],origin_xy=list(previous),definition_box=list(box),
                    definition_bbox=list(v['box']))
        elif kind==14:
            deltas=[data]
            for unused in range(3):
                operand_op,value=take()
                assert operand_op&MASK==11,'RECT operand opcode differs'
                deltas.append(value)
            output(index,'wire-rect',[previous[0]+deltas[0],previous[1]+deltas[1],
                previous[0]+deltas[2],previous[1]+deltas[3]],layer,origin_xy=list(previous),deltas=deltas)
        else:
            assert kind in (9,10,11,12,15,16,17),'Unsupported native opcode'
    return dict(raw_sha256=digest(raw),raw_count=len(raw),shapes=shapes,
                native_coordinate_checks=checks,shape_count=len(shapes),
                source_algorithm=PRIMARY)

def ownership_decision(markers,records):
    """Conservative sufficient condition; absence/ambiguity never grants repair."""
    assert len(markers)==3 and [x['ordinal']for x in markers]==[0,1,2]
    assert [x['target']for x in markers]==['net36993','net36993','net459']
    for marker in markers:
        expected=[CLOCK,marker['target']]if marker['ordinal']<2 else[marker['target'],CLOCK]
        assert marker['source_names']==expected,'Original ordered typed source names differ'
    ids=[row['record_id']for row in records]
    assert all(type(value)is str and value for value in ids),'Native record IDs must be nonempty strings'
    assert len(ids)==len(set(ids)),'Duplicate native ownership record'
    allowed={'wire','wire-rect','via','iterm-pin','bterm-pin','master-obstruction',
             'block-obstruction','special-wire','special-via','metal-fill'}
    for row in records:
        assert row['kind']in allowed,'Unclassified native material'
        assert type(row['layer'])is str and row['layer']
        rect(row['box'])
        assert type(row['source_indices'])is list,'Original source indices required'
        assert row['source_indices']==[[m['ordinal'],i]for m in markers
            for i,name in enumerate(m['source_names'])if name==row['owner']],'Original source index mapping differs'
        assert row['owner']is None or type(row['owner'])is str
    witnesses=[];blockers=[]
    for marker in markers:
        local=[r for r in records if r['layer']==marker['layer']and overlap(r['box'],marker['box'])]
        target=marker['target'];pair={target,CLOCK}
        unknown=[r['record_id']for r in local if r['owner']not in pair or
                 r['kind']in ('master-obstruction','block-obstruction','special-wire','special-via','metal-fill')]
        if unknown:blockers.append(dict(marker=marker['ordinal'],reason='Foreign, obstruction or special material',records=unknown))
        a=[r for r in local if r['owner']==target];b=[r for r in local if r['owner']==CLOCK]
        actual=[]
        for left in a:
            for right in b:
                if overlap(left['box'],right['box']):
                    common=intersection(left['box'],right['box'])
                    if overlap(common,marker['box']):
                        actual.append((left,right,intersection(common,marker['box'])))
        if not actual:blockers.append(dict(marker=marker['ordinal'],reason='No exact source-pair material overlap'))
        for left,right,common in actual:
            movable=left['kind']in ('wire','wire-rect','via')and left.get('route_class')=='ROUTED'
            if not movable:
                blockers.append(dict(marker=marker['ordinal'],reason='Immutable target pin or unsupported target material',
                                     records=[left['record_id'],right['record_id']]))
            witnesses.append(dict(marker=marker['ordinal'],target_record=left['record_id'],
                clock_record=right['record_id'],intersection=common,target_movable=movable,
                clock_material_kind=right['kind'],clock_movement_permitted=False))
    return dict(marker_count=3,markers=markers,records=records,witnesses=witnesses,blockers=blockers,
                eligible_for_one_two_net_attempt=bool(witnesses)and not blockers,
                inferred_root_cause=False,feasibility_proven=False,accepted=False)
