#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Complete read-only geometry window over the exact one-diode inserted database."""
import hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_antenna_escape_window as p
import mainchip_two_signal_geometry as g
import mainchip_two_signal_ownership_native as own
import mainchip_original_clock_restoration_native as n
import mainchip_single_antenna_trial as trial
from mainchip_two_signal_ownership_native import (
 api_evidence,no_unobserved_material,named_layers,native_wire,via_record,box,placed_box,iterm_key,API_SHA,IDENTITY_SCOPE)
D=Path("/work/out/antenna-escape-window")
W=Path("/work/out/work/antenna-escape-window")
SOURCE=Path("/work/current-input.odb")
def fp(path):
    with path.open("rb")as f: digest=hashlib.file_digest(f,"sha256").hexdigest()
    return dict(bytes=path.stat().st_size,sha256=digest)
def save(name,value):
    path=D/name;assert not path.exists()
    path.write_text(json.dumps(value,sort_keys=True,allow_nan=False,indent=2)+"\n")

def collect(db,block):
    proof=api_evidence()
    assert not list(block.getChildren()),'Child blocks require separate ownership qualification'
    empty=no_unobserved_material(block)
    window=list(p.WINDOW)
    assert db.getTech().getDbUnitsPerMicron()==block.getDbUnitsPerMicron()
    layers=named_layers(db.getTech(),proof)
    source_names={p.NET,p.FOREIGN}
    nets=list(block.getNets());assert len(nets)==143820
    assert len({n.getName()for n in nets})==len(nets),'Duplicate native net name'
    assert source_names<={n.getName()for n in nets}
    rows=[];full_sources={};counts={};stream=hashlib.sha256();raw_stream=hashlib.sha256();raw_pairs=0
    connected_iterms={};connected_bterms={}
    def feed(row):
        kind=row['kind'];counts[kind]=counts.get(kind,0)+1
        raw=g.canonical(row);stream.update(len(raw).to_bytes(8,'big'));stream.update(raw)
        assert row['layer']in layers,'Geometry layer absent from complete layer census'
        if p.intersects(row['box'],window):rows.append(dict(row))
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
            if name == p.NET:
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
    master_cache={}
    instances=sorted(block.getInsts(),key=lambda i:i.getName());assert len(instances)==153129
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
    via_definitions={}
    for namespace,container in (('tech',db.getTech()),('block',block)):
        records={}
        for via in container.getVias():
            name=via.getName();assert name not in records,'Duplicate via definition'
            records[name]=via_record(via,layers)
        via_definitions[namespace]=records
    assert set(full_sources)==source_names
    return dict(status='COMPLETE_NATIVE_ALL_LAYER_WINDOW_DIAGNOSTIC_ONLY',
        window_DBU=window,unclipped_intersecting_geometry=rows,geometry_selection='closed_boundary_all_layers',
        full_source_material=full_sources,source_net_count=len(source_names),
        native_geometry_census=counts,native_geometry_sha256=stream.hexdigest(),
        all_net_count=len(nets),instance_count=len(instances),dbu_per_micron=block.getDbUnitsPerMicron(),
        complete_raw_opcode_data_pairs=raw_pairs,complete_raw_wire_sha256=raw_stream.hexdigest(),
        via_definitions=via_definitions,layers=layers,acquired_api_report_sha256=API_SHA,
        every_block_terminal_reconciled_with_connected_net_census=True,
        read_only=True,identity_scope=IDENTITY_SCOPE,
        scope='All ordinary raw opcode-derived boxes and via components, connected/disconnected placed pins, special wires/vias and transformed decomposed master obstructions. Fill and block obstruction censuses must be empty. No routing clearance or segmentation proof is inferred.',
        physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)

def main():
    assert not any(k in os.environ for k in ("GH_TOKEN","GITHUB_TOKEN"))
    D.mkdir();W.mkdir(parents=True);holder={}
    def action():
        assert fp(SOURCE)==p.INPUT
        db,b=n.load(SOURCE);holder["db"]=db
        assert b.getDbUnitsPerMicron()==db.getTech().getDbUnitsPerMicron()==1000
        clocks=sorted(n.selected(b));assert len(clocks)==1691
        diode=b.findInst(p.NEW);assert diode is not None and diode.getMaster().getName()=="sg13g2_antennanp"
        assert diode.findITerm("A").getNet().getName()==p.NET
        assert own.box(diode.getBBox())==[98880,502740,100320,506520]
        odb.write_def(b,str(W/"before.def"));before=fp(W/"before.def")
        result=collect(db,b)
        assert len(result["full_source_material"][p.NET]["projection"]["shapes"])==40
        assert result["unclipped_intersecting_geometry"],"empty actual window"
        save("ownership-window.json",result)
        odb.write_tech_lef(db.getTech(),str(D/"technology.lef"))
        assert (D/"technology.lef").is_file()and (D/"technology.lef").stat().st_size>0
        odb.write_def(b,str(W/"after.def"));after=fp(W/"after.def")
        assert before==after and sorted(n.selected(b))==clocks,"read-only geometry/clock mutation"
        save("result.json",dict(status="COMPLETE_ANTENNA_ESCAPE_WINDOW_DIAGNOSTIC",
          input=p.INPUT,all_1691_original_clocks_preserved=True,clock_names=clocks,
          native_geometry_census=result["native_geometry_census"],
          window_rows=len(result["unclipped_intersecting_geometry"]),before_def=before,after_def=after,
          complete_window_report=fp(D/"ownership-window.json"),technology_lef=fp(D/"technology.lef"),
          source_geometry_mutated=False,route_generated=False,clearance_proven=False,
          physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
    def finish():
        errors=[]
        for label,fn in (("destroy-database",lambda:odb.dbDatabase.destroy(holder["db"])if "db"in holder else None),
                         ("unchanged-source",lambda:p.require(fp(SOURCE)==p.INPUT,"input drift"))):
            try:fn()
            except BaseException as e:errors.append(dict(label=label,error=repr(e)))
        if errors:raise RuntimeError(repr(errors))
    return trial.run_phase("window",action,finish,save)
if __name__=="__main__":main()
