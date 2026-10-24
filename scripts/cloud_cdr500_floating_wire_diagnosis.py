#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only diagnosis of every terminal-free native PD500 metal net.

The unchanged strict probe must reproduce its exact rejection. This separate
reader enumerates rejected geometry; it never creates usable RC inputs, edits
layout, relaxes the strict probe, or grants physical/electrical acceptance.
"""
import argparse,json,os,re,subprocess
from pathlib import Path
from collections import Counter,defaultdict
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr500-floating-wire-diagnosis'
TOP='nssoc_cdr_pd500_active_input_v57'
METALS=(8,10,30,50,67,126,134);VIAS=(19,29,49,66,125,133)
CENSUS=dict(npn13G2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
SUMMARY='b982ff54a0d20feda8f5758f13f4e32928b8256e7bb6696e3382110fd3a3d62f'
PARTS='556b2981edfe4216b74ddec5b5303d65282b83703e832e2b500c55d39e650a55'
SOURCE='751b438f516913e657da4a8ebb31f59c40cb5de2'
REJECTION='if not ts:assert not area and not ps and n.cluster_id not in owners'

def native():
    import pya
    source=OUT/'source';parent=source/'parent';gds=parent/'layout'/(TOP+'.gds')
    L=pya.Layout();L.read(str(gds));T=L.cell(TOP);assert T is not None and L.dbu==.001
    db=pya.LayoutVsSchematic();db.read(str(parent/'physical/lvs_flat/result.lvsdb'))
    c=db.netlist().top_circuit();assert c.name==TOP and c.pin_count()==25
    assert dict(Counter(d.device_class().name for d in c.each_device()))==CENSUS
    assert json.loads((parent/'physical/lvs_flat/audit.json').read_text())['status']=='PASS within comparison scope'
    regions={m:pya.Region(T.begin_shapes_rec(L.layer(m,0))).flatten().merged()for m in (*METALS,*VIAS)}
    mapping={}
    for metal in METALS:
        r=regions[metal];assert not r.is_empty()
        hits=[i for i in db.layer_indexes()if db.layer_by_index(i).bbox()==r.bbox() and db.layer_by_index(i).area()==r.area() and (db.layer_by_index(i)^r).is_empty()]
        assert len(hits)==1,(metal,hits);mapping[metal]=hits[0]
    e=pya.LayoutToNetlist('PD500_DRAWING_ONLY_DIAGNOSIS',L.dbu)
    for m,r in regions.items():
        if not r.is_empty():e.register(r,'gds_'+str(m));e.connect(r)
    for lo,v,hi in zip(METALS,VIAS,METALS[1:]):
        if not regions[v].is_empty():e.connect(regions[lo],regions[v]);e.connect(regions[v],regions[hi])
    e.extract_netlist();ec=e.netlist().top_circuit();assert not list(ec.each_device())
    terminals=defaultdict(list);ports=defaultdict(list)
    for d in c.each_device():
        dc=d.device_class()
        for td in dc.terminal_definitions():
            terminals[d.net_for_terminal(td.id()).cluster_id].append(dict(device=d.id(),model=dc.name,terminal=td.name))
    assert sum(map(len,terminals.values()))==1446
    for p in c.each_pin():ports[c.net_for_pin(p.id()).cluster_id].append(p.name())
    owner_regions={}
    instances=list(T.each_inst());assert len(instances)==16
    for m in (*METALS,*VIAS):
        owner_regions[m]={'root_direct':pya.Region(T.shapes(L.layer(m,0))).flatten().merged()}
        for inst in instances:
            owner=inst.cell.name+'@'+str(inst.dcplx_trans)
            assert owner not in owner_regions[m]
            owner_regions[m][owner]=pya.Region(inst.cell.begin_shapes_rec(L.layer(m,0))).transformed(inst.cplx_trans).flatten().merged()
        union=pya.Region()
        for r in owner_regions[m].values():union+=r
        assert(union.merged()^regions[m]).is_empty(),('Ownership coverage',m)
    old=pya.Layout();old.read(str(parent/'baseline/layout/nssoc_cdr_pd476_follower_v23.gds'))
    oldtop=old.cell('nssoc_cdr_pd476_follower_v23');assert oldtop is not None and old.dbu==L.dbu
    oldroot={m:pya.Region(oldtop.shapes(old.layer(m,0))).flatten().merged()for m in (*METALS,*VIAS)}
    proof=json.loads((parent/'replacement-proof.json').read_text())['parent_geometry_changes']
    bypass=proof['m4_enclosures'];assert len(bypass)==48
    preserved=[r for r in bypass if r['action']=='PRESERVE_V14_SOURCE_BYPASS_METAL_AND_ALL_ROOT_VIAS'];assert len(preserved)==32
    def polygons(r):return [str(p)for p in r.merged().each()]
    def contributions(m,r):
        result=[];covered=pya.Region()
        for name,owned in owner_regions[m].items():
            overlap=(r&owned).merged()
            if overlap.is_empty():continue
            covered+=overlap
            row=dict(owner=name,area_dbu2=overlap.area(),polygons_dbu=polygons(overlap))
            if name=='root_direct':
                row['original_parent_root_overlap_area_dbu2']=(overlap&oldroot[m]).area()
                row['entire_overlap_present_in_original_parent_root']=(overlap-oldroot[m]).is_empty()
            result.append(row)
        assert(r-covered).is_empty(),('Incomplete ownership',m)
        return result
    wires={};owners=defaultdict(list);bound=[]
    for n in ec.each_net():
        pieces={m:e.shapes_of_net(n,regions[m],True).flatten().merged()for m in METALS}
        metal,region=next((m,r)for m,r in pieces.items()if not r.is_empty())
        boxes=[p.bbox()for p in region.decompose_trapezoids_to_region().each()if p.area()==p.bbox().area() and p.bbox().width()>2 and p.bbox().height()>2]
        assert boxes;point=boxes[0].center();native=db.probe_net(db.layer_by_index(mapping[metal]),point);assert native is not None
        for m,r in pieces.items():assert(r-db.shapes_of_net(native,db.layer_by_index(mapping[m]),True)).is_empty(),('Crossed native cluster',n.cluster_id,m)
        owners[native.cluster_id].append(n.cluster_id);wires[n.cluster_id]=(n,pieces)
        bound.append(dict(wire_cluster=n.cluster_id,native_cluster=native.cluster_id,native_name=native.name,probe_metal=metal,probe_dbu=[point.x,point.y]))
    assert all(len(v)==1 for v in owners.values()),'Native metal net split'
    coverage=[];rejected=[]
    for n in c.each_net():
        native_pieces={m:db.shapes_of_net(n,db.layer_by_index(mapping[m]),True).flatten().merged()for m in METALS}
        area=sum(r.area()for r in native_pieces.values());ts=terminals.get(n.cluster_id,[]);ps=ports.get(n.cluster_id,[])
        if area:assert n.cluster_id in owners
        row=dict(native_cluster=n.cluster_id,native_name=n.name,metal_area_dbu2=area,wire_clusters=owners.get(n.cluster_id,[]),intrinsic_terminal_count=len(ts),public_ports=ps)
        coverage.append(row)
        if ts:continue
        record=dict(row,violates_unchanged_strict_probe=bool(area or ps or n.cluster_id in owners),intrinsic_terminals=[],layers=[],nodes=[],edges=[],unbound_vias=[],preserved_v14_m4_overlaps=[])
        if not area:
            assert n.cluster_id not in owners;rejected.append(record);continue
        assert len(owners[n.cluster_id])==1
        wire,pieces=wires[owners[n.cluster_id][0]]
        for m in METALS:assert(pieces[m]^native_pieces[m]).is_empty(),('Incomplete native metal coverage',n.cluster_id,m)
        allpieces={**pieces,**{v:e.shapes_of_net(wire,regions[v],True).flatten().merged()for v in VIAS}}
        nodes=[]
        for m,r in allpieces.items():
            record['layers'].append(dict(layer=m,area_dbu2=r.area(),polygon_count=r.count(),polygons_dbu=polygons(r),contributors=contributions(m,r)))
            if m in METALS:
                for p in r.each():nodes.append((m,pya.Region(p),p))
        record['nodes']=[dict(id=i,metal=m,polygon_dbu=str(p),contributors=contributions(m,r))for i,(m,r,p)in enumerate(nodes)]
        adjacency=defaultdict(set)
        for lo,v,hi in zip(METALS,VIAS,METALS[1:]):
            for p in allpieces[v].each():
                cut=pya.Region(p)
                lower=[i for i,(m,r,_)in enumerate(nodes)if m==lo and not r.interacting(cut).is_empty()]
                upper=[i for i,(m,r,_)in enumerate(nodes)if m==hi and not r.interacting(cut).is_empty()]
                row=dict(via=v,polygon_dbu=str(p),lower_nodes=lower,upper_nodes=upper,contributors=contributions(v,cut))
                assert len(lower)<=1 and len(upper)<=1,('Multiple same-layer attachments',v,lower,upper)
                if lower and upper:
                    record['edges'].append(row);adjacency[lower[0]].add(upper[0]);adjacency[upper[0]].add(lower[0])
                else:record['unbound_vias'].append(row)
        visited=set();pending=[0]
        while pending:
            current=pending.pop()
            if current in visited:continue
            visited.add(current);pending.extend(adjacency[current]-visited)
        assert len(visited)==len(nodes),'Geometry graph does not reproduce extracted component'
        for witness in preserved:
            exact=[p for p in owner_regions[50]['root_direct'].each()if str(p)==witness['before_polygon_dbu']]
            assert len(exact)==1
            ring=pya.Region(exact[0]);overlap=ring&pieces[50]
            if not overlap.is_empty():record['preserved_v14_m4_overlaps'].append(dict(tag=witness['tag'],polygon_dbu=witness['before_polygon_dbu'],intersection_area_dbu2=overlap.area(),entire_preserved_piece_on_this_net=(ring-pieces[50]).is_empty(),source_root_via_contacts=witness['root_owned_via_contacts']))
        record['wire_graph_connected']=True;rejected.append(record)
    violations=[r for r in rejected if r['violates_unchanged_strict_probe']];assert violations,'Original rejection was not reproduced in native diagnosis'
    result=dict(status='COMPLETE_ALL_NATIVE_PD500_TERMINAL_FREE_NETS_NOT_ACCEPTANCE',
        native_devices=CENSUS,native_terminal_count=1446,native_public_port_count=25,native_layer_mapping=mapping,
        native_net_count=len(coverage),wire_component_count=len(bound),native_terminal_free_count=len(rejected),
        strict_probe_violating_terminal_free_count=len(violations),native_net_coverage=coverage,wire_native_binding=bound,
        terminal_free_nets=rejected,all_native_nets_enumerated=True,all_drawing_wire_components_bound=True,
        entire_native_metal_geometry_covered=True,geometry_edited=False,strict_probe_edited=False,
        no_label_union=True,accepted=False,qualified_pex=False,wire_rc_extracted=False,full_phy_accepted=False)
    (OUT/'native.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('status','native_terminal_free_count','strict_probe_violating_terminal_free_count','wire_component_count')},indent=2),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');args=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,geometry_edited=False,strict_probe_edited=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        selected=['probe01.py.log','wire/probe01.py','wire/source-pins.json','planes/native-planes.json','parent/result.json','parent/child-geometry-proof.json','parent/replacement-proof.json','parent/layout/result.json','parent/layout/'+TOP+'.gds','parent/layout/schematic.cir','parent/baseline/layout/nssoc_cdr_pd476_follower_v23.gds','parent/baseline/layout/result.json',*['parent/physical/lvs_flat/'+n for n in ('result.lvsdb','audit.json','deck.log','extracted.cir')]]
        prior,proof=reports.restore_report('cdr-sampler-active-input-v57-wire-inputs',40073945226,SUMMARY,PARTS,OUT/'source',selected)
        assert prior['source_head']==SOURCE and prior['status']=='FAIL_OR_ERROR' and prior['error']=="AssertionError(('probe01.py', 1))"
        assert prior['physical_source']['run']==40073349301 and prior['physical_source']['summary_sha256']=='ebd36ac051b0e3ea95c682e86688f4441456b6fc785dd7667dead89101e0f083'
        assert prior['plane_source']['summary_sha256']=='f217113af059e6b18c0e43cb94c4d79a74d609f1274ec7bc62529e280820b1d5'
        r['original_failed_wire_source']=proof
        parent=OUT/'source/parent';physical=json.loads((parent/'result.json').read_text())
        assert physical['status']=='PASS_PD500_C_D_ACTIVE_INPUT_V57_PARENT_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES'
        assert sha(parent/'result.json')==prior['physical_source']['summary_sha256']
        assert physical['sources_unchanged'] and physical['physical']['steps']['drc']['measurement']['markers']==0
        for name in ('lvs','lvs_flat'):assert physical['physical']['steps'][name]['audit']['circuits'][0]['layout_devices_recursive']==500
        strict=OUT/'source/wire/probe01.py';assert sha(strict)==prior['method_adaptations']['probe01.py']['adapted_sha256']=='d0ff17e291afae70873724369a89304dfd845ace8a5b9ed438e478c05b9a3790'
        assert strict.read_text().count(REJECTION)==1
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        with (OUT/'strict-probe-reproduction.log').open('w')as log:rc=subprocess.call([str(app),'python',str(strict)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        text=(OUT/'strict-probe-reproduction.log').read_text();assert rc==1 and REJECTION in text and text.rstrip().endswith('AssertionError'),text[-2000:]
        r['strict_rejection_reproduced']=dict(returncode=rc,log_sha256=sha(OUT/'strict-probe-reproduction.log'),original_probe_sha256=sha(strict),assertion=REJECTION);save()
        with (OUT/'native.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r['native_returncode']=rc
        if rc:print((OUT/'native.log').read_text()[-16000:],flush=True)
        assert rc==0;r['native']=json.loads((OUT/'native.json').read_text())
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
        r['sources_unchanged']=True;r['status']='COMPLETE_ACTUAL_PD500_TERMINAL_FREE_METAL_DIAGNOSIS_NOT_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_DIAGNOSIS',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
