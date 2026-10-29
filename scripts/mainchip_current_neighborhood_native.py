#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read current serialized chip without changes; no clearance/signoff claim."""
import hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_two_signal_geometry as g
import mainchip_original_clock_restoration as c
from mainchip_two_signal_ownership_native import (
 api_evidence,no_unobserved_material,named_layers,native_wire,iterm_key,box,
 via_record,placed_box,API_SHA,IDENTITY_SCOPE)
from mainchip_original_clock_restoration_native import identity
WINDOW=[937420,1779520,957620,1800560]
INPUT=dict(bytes=213429713,sha256="47d657f41565f5c379a9152672eac824a5d296043c3726527031452ad2097677")
OUT=Path("/work/out/current-neighborhood")
def layers_for_window(db):
    return [layer.getName() for layer in db.getTech().getLayers()]
def fingerprint(path):
    h=hashlib.sha256()
    with path.open("rb")as stream:
        for data in iter(lambda:stream.read(1024*1024),b""):h.update(data)
    return dict(bytes=path.stat().st_size,sha256=h.hexdigest())
def save(name,value):
    with (OUT/name).open("x")as stream:json.dump(value,stream,indent=2,sort_keys=True);stream.write("\n")

def collect_current(db,block):
    proof=api_evidence()
    assert not list(block.getChildren()),'Child blocks require separate ownership qualification'
    empty=no_unobserved_material(block)
    markers=[dict(layer=name,box=WINDOW) for name in layers_for_window(db)]
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
            row['source_indices']=[]
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
    decision=dict(records=rows,observation_window_dbu=WINDOW,all_layers_observed=True,
        clearance_qualified=False,rule_expanded_window_qualified=False)
    decision.update(native_geometry_census=counts,native_geometry_sha256=stream.hexdigest(),
        full_source_material=full_sources,source_net_count=3,all_net_count=len(nets),
        instance_count=len(instances),dbu_per_micron=block.getDbUnitsPerMicron(),
        complete_raw_opcode_data_pairs=raw_pairs,complete_raw_wire_sha256=raw_stream.hexdigest(),
        historical_api_lookup_report_sha256=API_SHA,
        historical_database_identity_not_reused=True,
        read_only=True,identity_scope=IDENTITY_SCOPE,
        scope='All ordinary raw opcode-derived boxes, every via component, every connected/disconnected native placed terminal pin, special-wire boxes/vias and transformed decomposed master obstructions. Empty native fill/block-obstruction censuses are mandatory because their instance getters were not exercised. Polygon segmentation identity is not claimed.')
    assert set(full_sources)==source_names
    return decision

def main():
    assert not any(k in os.environ for k in ("GH_TOKEN","GITHUB_TOKEN"))
    source=Path("/work/current-input.odb")
    assert fingerprint(source)==INPUT
    OUT.mkdir()
    db=odb.dbDatabase.create()
    try:
        odb.read_db(db,str(source));block=db.getChip().getBlock()
        assert block.getDbUnitsPerMicron()==1000
        tech=db.getTech()
        api=dict(odb_tech_export_available=hasattr(odb,"write_tech_lef"),
                 technology_methods=[n for n in dir(tech)if not n.startswith("_")],
                 layer_methods=[n for n in dir(next(iter(tech.getLayers())))if not n.startswith("_")])
        save("native-api.json",api)
        assert api["odb_tech_export_available"]
        # The exact upstream SWIG API exports the technology embedded in this ODB.
        rc=odb.write_tech_lef(tech,str(OUT/"current-tech.lef"))
        assert rc==1 and (OUT/"current-tech.lef").stat().st_size>0,("tech export",rc)
        result=collect_current(db,block)
        result["source_database"]=INPUT
        result["current_source_identities"]={name:identity(db,block.findNet(name))
            for name in (g.CLOCK,*g.TARGETS)}
        result["manufacturing_grid_dbu"]=tech.getManufacturingGrid()
        result["embedded_technology_lef"]=fingerprint(OUT/"current-tech.lef")
        result["scope"]="Actual current full-database census with selected all-layer geometry in a fixed 10um padded observation window and full three-net material. Rule radius and repair feasibility remain unqualified until exported rules are reviewed."
        result.update(status="PASS_CURRENT_SERIALIZED_NEIGHBORHOOD_OBSERVATION_ONLY",
            physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
            geometry_changed=False,routing_started=False)
        save("neighborhood.json",result)
    finally:
        odb.dbDatabase.destroy(db)
        assert fingerprint(source)==INPUT,"source database changed"
    save("result.json",dict(status="PASS_CURRENT_SERIALIZED_NEIGHBORHOOD_OBSERVATION_ONLY",
      input=INPUT,unchanged_source=True,database_destroyed=True,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
      geometry_changed=False,routing_started=False,clearance_qualified=False,
      files={p.name:fingerprint(p)for p in OUT.iterdir()if p.is_file()}))
if __name__=="__main__":main()
