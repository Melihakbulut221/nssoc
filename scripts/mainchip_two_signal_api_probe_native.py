#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only actual OpenROAD API/identity census; never grants routing eligibility."""
import hashlib,json,os,traceback
from pathlib import Path
import mainchip_original_clock_restoration as c
import mainchip_original_clock_restoration_native as qualified
import mainchip_two_signal_repair as source
import mainchip_two_signal_geometry as geometry
from cloud_mainchip_original_clock_restoration import save

RAW_KINDS={0:'PATH',1:'SHORT',3:'RULE',7:'VIA',8:'TECH_VIA',13:'VWIRE'}
METHOD_NAMES=('getId','getOID','getName','getTechLayer','getTopLayer','getBottomLayer',
    'getBoxes','getRect','getGeometries','getWire','getData','getOpcode','length')
CLASS_NAMES=('dbTechLayer','dbNet','dbWire','dbITerm','dbBTerm','dbBPin','dbSWire',
    'dbSBox','dbFill','dbObstruction','dbInst','dbBox','dbVia','dbTechVia','dbTechLayerRule')

def exact_int(value):
    assert type(value)is int,'Native integer is not exact int'
    return value

def rect(value):
    return [exact_int(value.xMin()),exact_int(value.yMin()),exact_int(value.xMax()),exact_int(value.yMax())]

def layer(layer):
    assert layer is not None
    return dict(name=layer.getName(),width=exact_int(layer.getWidth()),
        wrong_way_width=exact_int(layer.getWrongWayWidth()),direction=str(layer.getDirection()),
        layer_number_observed_not_used_as_OID=exact_int(layer.getNumber()),
        routing_level_observed_not_used_as_OID=exact_int(layer.getRoutingLevel()))

def surface(value):
    names=sorted(x for x in dir(value)if not x.startswith('_'))
    result=dict(python_type=type(value).__name__,public_attributes=names,
        methods={k:dict(present=hasattr(value,k),callable=callable(getattr(value,k,None)))for k in METHOD_NAMES})
    # Absence is a diagnostic result. Never invent an ID or an alternative accessor.
    for key in ('getId','getOID'):
        if callable(getattr(value,key,None)):
            try:
                got=getattr(value,key)()
                result[key]=dict(return_type=type(got).__name__,value=got if type(got)is int else None,
                    exact_positive_integer=type(got)is int and got>0)
            except Exception as exc:result[key]=dict(error_type=type(exc).__name__,error=str(exc))
    return result

def census(odb,db,block):
    assert not list(block.getChildren()),'Unqualified child block'
    assert block.getDbUnitsPerMicron()==db.getTech().getDbUnitsPerMicron()
    tech=db.getTech();layers=list(tech.getLayers());layer_rows=[layer(x)for x in layers]
    by_name={x['name']:x for x in layer_rows};assert len(by_name)==len(layer_rows)
    counts={};streams={};representatives={};raw_ids=dict(layers={},rules={},vias={})
    class_surfaces={name:dict(present=hasattr(odb,name),
        public_attributes=sorted(x for x in dir(getattr(odb,name))if not x.startswith('_'))if hasattr(odb,name)else[])
        for name in CLASS_NAMES}
    def record(kind,key,value,obj):
        counts[kind]=counts.get(kind,0)+1
        raw=c.canonical([key,value]);streams.setdefault(kind,hashlib.sha256())
        streams[kind].update(len(raw).to_bytes(8,'big'));streams[kind].update(raw)
        if kind not in representatives:
            representatives[kind]=dict(scoped_identity=key,api=surface(obj))
    for row,obj in zip(layer_rows,layers):record('technology-layer',['technology-layer',row['name']],row,obj)
    def via_row(via,scope,oid=None):
        assert via is not None
        boxes=[]
        for index,b in enumerate(via.getBoxes()):
            assert not b.isVia(),'Nested native via component'
            row=dict(layer=b.getTechLayer().getName(),rect=rect(b),component_ordinal=index)
            assert row['layer']in by_name
            boxes.append(row);record('via-component-box',[scope,via.getName(),index],row,b)
        row=dict(name=via.getName(),top=via.getTopLayer().getName(),
            bottom=via.getBottomLayer().getName(),bbox=rect(via.getBBox()),components=boxes)
        assert row['top']in by_name and row['bottom']in by_name
        record('via-definition',[scope,via.getName()],row,via)
        if oid is not None:
            key=scope+':'+str(oid)
            if key in raw_ids['vias']:assert raw_ids['vias'][key]==row
            else:raw_ids['vias'][key]=row
        return row
    nets=sorted(block.getNets(),key=lambda x:x.getName())
    assert len(nets)==143820 and len({x.getName()for x in nets})==len(nets)
    net_iterms={};net_bterms={};raw_wire_count=0
    for net in nets:
        name=net.getName();record('net',['net',name],dict(sigtype=str(net.getSigType()),special=net.isSpecial()),net)
        wire=net.getWire()
        if wire is not None:
            raw=[[exact_int(wire.getOpcode(i)),exact_int(wire.getData(i))]for i in range(wire.length())]
            record('ordinary-wire',['net',name,'wire'],raw,wire);raw_wire_count+=len(raw)
            for index,(op,data)in enumerate(raw):
                kind=op&31
                if kind in (0,1,13):
                    assert data>0
                    actual=odb.dbTechLayer.getTechLayer(tech,data);row=layer(actual)
                    assert row==by_name[row['name']],'Static raw layer lookup differs from enumerated native layer'
                    key=str(data)
                    if key in raw_ids['layers']:assert raw_ids['layers'][key]==row
                    else:raw_ids['layers'][key]=row
                elif kind==3:
                    assert data>0
                    scope='block'if op&128 else'tech'
                    actual=odb.dbTechLayerRule.getTechLayerRule(block if scope=='block'else tech,data)
                    assert actual is not None
                    row=dict(width=exact_int(actual.getWidth()))
                    key=scope+':'+str(data)
                    if key in raw_ids['rules']:assert raw_ids['rules'][key]==row
                    else:raw_ids['rules'][key]=row;record('raw-layer-rule',[scope,data],row,actual)
                elif kind in (7,8):
                    assert data>0
                    scope='block'if kind==7 else'tech';key=scope+':'+str(data)
                    if key not in raw_ids['vias']:
                        obj=odb.dbVia.getVia(block,data)if kind==7 else odb.dbTechVia.getTechVia(tech,data)
                        via_row(obj,scope,data)
                elif kind in (9,10):
                    assert data>0
                    if kind==9:
                        obj=odb.dbITerm.getITerm(block,data);assert obj is not None
                        identity=[obj.getInst().getName(),obj.getMTerm().getName()];kind_name='iterm'
                    else:
                        obj=odb.dbBTerm.getBTerm(block,data);assert obj is not None
                        identity=[obj.getName()];kind_name='bterm'
                    assert obj.getNet()is not None and obj.getNet().getName()==name
                    record('raw-'+kind_name+'-lookup',['net',name,'opcode',index,'raw-OID',data],
                        dict(named_identity=identity,owner=name),obj)
        for it in net.getITerms():
            key=(it.getInst().getName(),it.getMTerm().getName());assert key not in net_iterms
            assert it.getNet()is not None and it.getNet().getName()==name
            net_iterms[key]=name
        for bt in net.getBTerms():
            key=bt.getName();assert key not in net_bterms
            assert bt.getNet()is not None and bt.getNet().getName()==name
            net_bterms[key]=name
        for si,swire in enumerate(net.getSWires()):
            record('special-wire',['net',name,'swire',si],dict(type=str(swire.getWireType())),swire)
            for bi,b in enumerate(swire.getWires()):
                key=['net',name,'swire',si,'box',bi]
                if b.isVia():
                    v=b.getTechVia();scope='tech'
                    if v is None:v=b.getBlockVia();scope='block'
                    row=dict(via=via_row(v,scope),origin=list(b.getViaXY()),bbox=rect(b))
                else:row=dict(layer=b.getTechLayer().getName(),rect=rect(b))
                record('special-box',key,row,b)
    seen_iterms={};seen_bterms={}
    for it in block.getITerms():
        key=(it.getInst().getName(),it.getMTerm().getName());assert key not in seen_iterms
        owner=None if it.getNet()is None else it.getNet().getName();seen_iterms[key]=owner
        shapes=[[lay.getName(),rect(box)]for lay,box in it.getGeometries()]
        record('instance-terminal',['iterm',*key],dict(owner=owner,geometries=shapes),it)
    assert {k:v for k,v in seen_iterms.items()if v is not None}==net_iterms
    for bt in block.getBTerms():
        key=bt.getName();assert key not in seen_bterms
        owner=None if bt.getNet()is None else bt.getNet().getName();seen_bterms[key]=owner
        record('block-terminal',['bterm',key],dict(owner=owner),bt)
        for pi,pin in enumerate(bt.getBPins()):
            record('block-pin',['bterm',key,'bpin',pi],dict(placement=str(pin.getPlacementStatus())),pin)
            for bi,b in enumerate(pin.getBoxes()):
                assert not b.isVia(),'Unqualified BPin via'
                record('block-pin-box',['bterm',key,'bpin',pi,'box',bi],dict(layer=b.getTechLayer().getName(),rect=rect(b)),b)
    assert {k:v for k,v in seen_bterms.items()if v is not None}==net_bterms
    for index,fill in enumerate(block.getFills()):
        record('metal-fill',['fill',index],dict(layer=fill.getTechLayer().getName(),
            rect=rect(fill.getRect()),mask=fill.maskNumber(),needs_OPC=fill.needsOPC()),fill)
    for index,ob in enumerate(block.getObstructions()):
        b=ob.getBBox();assert not b.isVia()
        record('block-obstruction',['block-obstruction',index],dict(layer=b.getTechLayer().getName(),rect=rect(b)),ob)
        record('block-obstruction-box',['block-obstruction',index,'box'],dict(layer=b.getTechLayer().getName(),rect=rect(b)),b)
    masters={}
    instances=sorted(block.getInsts(),key=lambda x:x.getName());assert len(instances)==153130
    assert len({i.getName()for i in instances})==len(instances)
    for inst in instances:
        master=inst.getMaster();key=(master.getLib().getName(),master.getName());masters[key]=master
        record('instance',['instance',inst.getName()],dict(master=list(key),
            origin=list(inst.getOrigin()),orientation=str(inst.getOrient())),inst)
    for key,master in sorted(masters.items()):
        for index,b in enumerate(master.getObstructions(True)):
            assert not b.isVia()
            record('master-obstruction-box',['master',*key,'obstruction',index],
                dict(layer=b.getTechLayer().getName(),rect=rect(b)),b)
    assert len({row['name']for row in raw_ids['layers'].values()})==len(raw_ids['layers'])
    assert {geometry.CLOCK,*source.TARGETS}<={net.getName()for net in nets}
    return dict(status='COMPLETE_READ_ONLY_API_IDENTITY_CENSUS_NOT_OWNERSHIP_QUALIFICATION',
        dbu_per_micron=block.getDbUnitsPerMicron(),all_net_count=len(nets),all_instance_count=len(instances),
        native_class_surfaces=class_surfaces,representative_api_surfaces=representatives,
        complete_census_counts=counts,complete_census_sha256={k:v.hexdigest()for k,v in streams.items()},
        complete_raw_opcode_data_pairs=raw_wire_count,raw_operand_native_lookups=raw_ids,
        layer_numbers_or_routing_levels_used_as_OIDs=False,table_OIDs_invented=False,
        scoped_identity_contract='Names are unique within their named native parent; anonymous entries retain exact native-container ordinal and geometry multiplicity. These keys are not database OIDs and are not yet a repair qualification.',
        every_block_terminal_reconciled_with_connected_net_census=True,
        disconnected_iterms=sum(v is None for v in seen_iterms.values()),
        disconnected_bterms=sum(v is None for v in seen_bterms.values()),
        source_geometry_mutated=False,native_routing_started=False,ownership_eligible=False,
        original_getId_failure_preserved=True,accepted=False,full_phy_accepted=False)

def main():
    from mainchip_two_signal_api_probe import methods
    import odb
    m=methods()
    assert m['native_api_probe_authorized']is True and m['cloud_restore_authorized']is True
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    path=c.regular(Path(os.environ['NSSOC_TWO_SIGNAL_FAILED_SOURCE'])/source.INPUT)
    assert c.file_sha(path)==source.INPUT_SHA and path.stat().st_size==source.INPUT_BYTES
    out=Path(os.environ['NSSOC_TWO_SIGNAL_OUT']);assert out.is_dir()and out.is_absolute()
    for p in [out,*out.parents]:assert not p.is_symlink()
    result=dict(status='RUNNING_READ_ONLY_API_CENSUS',accepted=False,native_routing_started=False)
    database=None;failure=None
    try:
        database,block=qualified.load(path)
        result=census(odb,database,block)
        result['input']=dict(member=source.INPUT,sha256=source.INPUT_SHA,bytes=source.INPUT_BYTES)
    except BaseException as exc:
        failure=exc
        result.update(status='FAIL_READ_ONLY_API_CENSUS',error=repr(exc),traceback=traceback.format_exc())
    finally:
        result['terminal_checks']=[]
        for label,fn in [('destroy-read-only-database',lambda:odb.dbDatabase.destroy(database)if database is not None else None),
                         ('unchanged-source-file',lambda:check_input(path))]:
            try:fn()
            except BaseException as exc:
                result['terminal_checks'].append(dict(label=label,status='FAIL',error=repr(exc)))
                result['status']='FAIL_READ_ONLY_API_CENSUS'
                if failure is None:
                    failure=exc;result.update(error=repr(exc),traceback=traceback.format_exc())
            else:result['terminal_checks'].append(dict(label=label,status='PASS'))
        save(out/'api-identity-census.json',result)
    if failure is not None:raise failure

def check_input(path):
    assert c.file_sha(path)==source.INPUT_SHA and path.stat().st_size==source.INPUT_BYTES,'Read-only input bytes changed'
if __name__=='__main__':main()
