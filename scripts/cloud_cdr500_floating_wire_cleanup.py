#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Remove only ten proved floating root components; recheck physical and strict wires."""
import argparse,copy,json,os,shutil,subprocess,sys,tarfile
from collections import Counter,defaultdict
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr500-floating-wire-cleanup'
TOP='nssoc_cdr_pd500_active_input_v57';METALS=(8,10,30,50,67,126,134);VIAS=(19,29,49,66,125,133)
EXPECTED_NETS={41,42,43,44,45,142,143,144,145,146}
EXPECTED_CENSUS={10:(10,21721000),30:(10,256849500),50:(20,7105000),19:(160,5776000),29:(160,5776000),49:(80,2888000)}

def cleanup():
    import pya
    import cloud_cdr500_floating_wire_diagnosis as diagnosis
    # Recompute the full diagnostic from immutable sources in this fresh job.
    # This code never turns the rejected probe into an accepting probe.
    diagnosis.OUT=OUT;diagnosis.native()
    measured=json.loads((OUT/'native.json').read_text())
    pinned=json.loads((OUT/'diagnosis/native.json').read_text());assert measured==pinned
    rows=[r for r in measured['terminal_free_nets']if r['violates_unchanged_strict_probe']]
    assert len(rows)==10 and {r['native_cluster']for r in rows}==EXPECTED_NETS
    source=OUT/'source/parent';dest=OUT/'parent/layout';dest.mkdir(parents=True,exist_ok=False)
    G=source/'layout'/(TOP+'.gds');L=pya.Layout();L.read(str(G));T=L.cell(TOP);assert T is not None and L.dbu==.001
    db=pya.LayoutVsSchematic();db.read(str(source/'physical/lvs_flat/result.lvsdb'));c=db.netlist().top_circuit()
    terminals=defaultdict(list);ports=defaultdict(list)
    for d in c.each_device():
        for td in d.device_class().terminal_definitions():terminals[d.net_for_terminal(td.id()).cluster_id].append((d.id(),td.name))
    for p in c.each_pin():ports[c.net_for_pin(p.id()).cluster_id].append(p.name())
    assert sum(map(len,terminals.values()))==1446 and len(list(c.each_device()))==500
    root={m:pya.Region(T.shapes(L.layer(m,0))).flatten().merged()for m in (*METALS,*VIAS)}
    child={m:pya.Region()for m in (*METALS,*VIAS)}
    for i in T.each_inst():
        for m in child:child[m]+=pya.Region(i.cell.begin_shapes_rec(L.layer(m,0))).transformed(i.cplx_trans)
    child={m:r.flatten().merged()for m,r in child.items()}
    def guard(pieces,actual_terminals,public_pins,root_geometry,child_geometry):
        assert not actual_terminals,'Native device terminal depends on candidate'
        assert not public_pins,'Public pin depends on candidate'
        assert any(not p.is_empty()for p in pieces.values())
        for m,r in pieces.items():
            assert(r-root_geometry[m]).is_empty(),('Not exclusively root-owned',m)
            assert(r&child_geometry[m]).is_empty(),('Child or intrinsic geometry intersects removal',m)
    removed={m:pya.Region()for m in root};records=[]
    native_nets={n.cluster_id:n for n in c.each_net()}
    for row in rows:
        nid=row['native_cluster'];assert not row['intrinsic_terminals']and not row['public_ports']and row['wire_graph_connected']
        pieces={m:pya.Region()for m in root}
        for layer in row['layers']:
            m=layer['layer'];wanted=layer['polygons_dbu'];actual=[p for p in root[m].each()if str(p)in wanted]
            assert len(actual)==len(wanted)==layer['polygon_count']
            assert set(map(str,actual))==set(wanted)
            for p in actual:pieces[m]+=pya.Region(p)
            pieces[m]=pieces[m].merged();assert pieces[m].area()==layer['area_dbu2']
            assert all(v['owner']=='root_direct'for v in layer['contributors'])
        guard(pieces,terminals[nid],ports[nid],root,child)
        n=native_nets[nid]
        for m in METALS:
            actual=db.shapes_of_net(n,db.layer_by_index(measured['native_layer_mapping'][str(m)]),True)
            assert(actual^pieces[m]).is_empty(),('Incomplete native metal component',nid,m)
        for m,r in pieces.items():assert(removed[m]&r).is_empty();removed[m]+=r
        records.append(dict(native_cluster=nid,native_name=row['native_name'],wire_clusters=row['wire_clusters'],no_intrinsic_terminal=True,no_public_pin=True,root_exclusive=True,no_child_intersection=True,layers=row['layers'],unbound_vias=row['unbound_vias']))
    def census(parts):return {m:(r.merged().count(),r.area())for m,r in parts.items()if not r.is_empty()}
    def exact(parts):assert census(parts)==EXPECTED_CENSUS,('Unexpected removal census',census(parts))
    exact(removed)
    assert sum(r['metal_area_dbu2']for r in rows)==285675500
    assert sum(len(r['preserved_v14_m4_overlaps'])for r in rows)==20
    assert all(r['intrinsic_terminal_count']==0 and not r['public_ports']for r in rows)
    faults=[]
    def reject(name,fn):
        try:fn()
        except AssertionError:faults.append(dict(name=name,rejected=True))
        else:raise AssertionError('Accepted '+name)
    reject('native_intrinsic_terminal_attached',lambda:guard(removed,[next(v for v in terminals.values()if v)[0]],[],root,child))
    reject('public_pin_attached',lambda:guard(removed,[],['avss'],root,child))
    corrupt=dict(child);corrupt[10]=corrupt[10]+removed[10]
    reject('actual_child_geometry_intersection',lambda:guard(removed,[],[],root,corrupt))
    corrupt_root=dict(root);corrupt_root[10]=root[10]-removed[10]
    reject('not_exclusively_root_owned',lambda:guard(removed,[],[],corrupt_root,child))
    missing=dict(removed);missing[49]=missing[49]-pya.Region(next(missing[49].each()))
    reject('missing_via_cut_from_component',lambda:exact(missing))
    added=dict(removed);added[10]=added[10]+pya.Region(pya.Box(-10000,-10000,-9000,-9000))
    reject('extra_unproved_metal',lambda:exact(added))
    def snapshot(layout,top):
        found={}
        def visit(cell):
            if cell.name in found:return
            polygons={};texts={}
            for li in layout.layer_indexes():
                info=layout.get_info(li);key=(info.layer,info.datatype)
                r=pya.Region(cell.shapes(li)).flatten().merged()
                if not r.is_empty():polygons[key]=r
                labels=sorted(str(s.text)for s in cell.shapes(li).each()if s.is_text())
                if labels:texts[key]=labels
            instances=sorted((i.cell.name,str(i.dcplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in cell.each_inst())
            found[cell.name]=(polygons,texts,instances)
            for inst in cell.each_inst():visit(inst.cell)
        visit(top);return found
    def compare(a,b):
        assert set(a)==set(b),'Hierarchy changed'
        for name,(polys,texts,instances)in a.items():
            assert texts==b[name][1]and instances==b[name][2],('Labels/transforms changed',name)
            assert set(polys)==set(b[name][0]),('Layer inventory changed',name)
            for k,r in polys.items():assert(r^b[name][0][k]).is_empty(),('Untracked drawing change',name,k)
    before=snapshot(L,T);expected=dict(before);root_expected=dict(before[TOP][0])
    for m,r in removed.items():
        if r.is_empty():continue
        changed=(root[m]-r).merged()
        assert(changed&r).is_empty()and((changed+r).merged()^root[m]).is_empty()
        T.shapes(L.layer(m,0)).clear();T.shapes(L.layer(m,0)).insert(changed)
        root_expected[(m,0)]=changed
    expected[TOP]=(root_expected,before[TOP][1],before[TOP][2]);compare(expected,snapshot(L,T))
    reject('unremoved_original_component',lambda:compare(expected,before))
    oldbbox=T.dbbox();options=pya.SaveLayoutOptions();options.select_cell(T.cell_index());L.write(str(dest/(TOP+'.gds')),options)
    R=pya.Layout();R.read(str(dest/(TOP+'.gds')));U=R.cell(TOP);assert U is not None and U.dbbox()==oldbbox
    compare(expected,snapshot(R,U))
    for n in (TOP+'.lef','schematic.cir'):shutil.copyfile(source/'layout'/n,dest/n)
    proof=dict(status='PROVEN_TEN_ROOT_ONLY_COMPONENT_SUBTRACTION_REQUIRES_NEW_PHYSICAL_AND_STRICT_WIRES',records=records,
        removed_component_count=10,removed_metal_area_dbu2=285675500,removed_layer_census={str(k):dict(polygons=v[0],area_dbu2=v[1])for k,v in EXPECTED_CENSUS.items()},
        removed_preserved_v14_m4_pieces=20,remaining_v14_m4_pieces=12,all_other_root_geometry_unchanged=True,
        all_child_and_intrinsic_drawings_unchanged=True,all_labels_and_instance_transforms_unchanged=True,
        serialized_geometry_exact=True,schematic_and_lef_bytes_unchanged=True,controls=faults,accepted=False)
    assert len(faults)==7
    (OUT/'cleanup-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    meta=json.loads((source/'layout/result.json').read_text());meta['status']='GENERATED_PD500_WITH_TEN_PROVEN_FLOATING_ROOT_COMPONENTS_REMOVED'
    meta['floating_metal_cleanup']=proof
    meta['inputs']={str(p):sha(p)for p in [G,source/'layout/result.json',source/'physical/lvs_flat/result.lvsdb',OUT/'diagnosis/native.json',ROOT/'scripts/cloud_cdr500_floating_wire_diagnosis.py',Path(__file__)]}
    meta['outputs']={p.name:sha(p)for p in dest.iterdir()if p.is_file()}
    (dest/'result.json').write_text(json.dumps(meta,indent=2)+'\n')

def planes():
    import cloud_cdr_sampler_active_input_v57_planes as module
    module.OUT=OUT;module.native()

def recover():
    import cloud_cdr_sampler_active_input_v57_wire_inputs as module
    module.OUT=OUT;module.recover()

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',choices=('cleanup','planes','recover'));args=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:globals()[args.native]();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,wire_rc_extracted=False,closed_loop=False,main_chip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(command,name):
        with (OUT/(name+'.log')).open('w')as log:rc=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(name=name,returncode=rc,log_sha256=sha(OUT/(name+'.log'))));save()
        if rc:print((OUT/(name+'.log')).read_text()[-18000:],flush=True)
        assert rc==0,(name,rc)
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr500-wire-inputs-strict-rejection-20261024.json').read_text())
        selected=[n for n in pin['report']['outputs']if n.startswith(('parent/','wire/'))or n=='planes/native-planes.json']
        prior,source=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior==pin['report'];r['original_rejected_wire_source']=source
        witness=json.loads((ROOT/'docs/evidence/cdr500-floating-wire-diagnosis-20261024.json').read_text())
        observed,proof=reports.restore_report(witness['group'],witness['run'],witness['summary_sha256'],witness['parts_sha256'],OUT/'diagnosis',['native.json'])
        assert observed==witness['report']and observed['sources_unchanged']and not observed['geometry_edited']and not observed['strict_probe_edited']
        assert observed['original_failed_wire_source']['summary_sha256']==pin['summary_sha256'];r['diagnostic_source']=proof
        assert observed['strict_rejection_reproduced']['original_probe_sha256']==prior['method_adaptations']['probe01.py']['adapted_sha256']
        assert sha(ROOT/'scripts/cloud_cdr500_floating_wire_diagnosis.py')=='83016e11e2a08f8b4bf0bd28457f2368d51e59b31610ccd786c8508c0d2ba6d3'
        parent=OUT/'parent';parent.mkdir();shutil.copytree(OUT/'source/parent/inputs',parent/'inputs');shutil.copyfile(OUT/'source/parent/children.json',parent/'children.json')
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        methods=[Path(__file__),ROOT/'scripts/cloud_cdr500_floating_wire_diagnosis.py',ROOT/'scripts/cloud_cdr_sampler_active_input_v57_planes.py',ROOT/'scripts/cloud_cdr_sampler_active_input_v57_wire_inputs.py',ROOT/'scripts/check_cdr_sampler_active_input_v57_parent_geometry.py',ROOT/'hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py']
        protected={str(p):sha(p)for p in methods}
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();runtime=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        assert all(sha(Path(n))==v for n,v in protected.items())
        run([app,'python',Path(__file__),'--native','cleanup'],'cleanup');r['cleanup']=json.loads((OUT/'cleanup-proof.json').read_text());save()
        run([sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py','--layout',parent/'layout','--out',parent/'physical','--app',app],'physical')
        r['physical']=json.loads((parent/'physical/result.json').read_text());assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS';save()
        run([app,'python',Path(__file__),'--native','planes'],'fresh-planes');r['native_planes']=json.loads((OUT/'native-planes.json').read_text());assert r['native_planes']['status']=='PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS';save()
        wire=OUT/'wire';wire.mkdir();method_pins={}
        for name in ('probe01.py','locate01.py','anchors01.py','dedup01.py'):
            shutil.copyfile(OUT/'source/wire'/name,wire/name)
            assert sha(wire/name)==prior['method_adaptations'][name]['adapted_sha256'];method_pins[name]=sha(wire/name)
        run([app,'python',Path(__file__),'--native','recover'],'source-annotations')
        for name in method_pins:run([app,'python',wire/name],name)
        r['strict_wire_graph']=json.loads((wire/'native05/result.json').read_text())
        r['device_locations']=json.loads((wire/'device-locations01.json').read_text());r['anchors']=json.loads((wire/'anchors08.json').read_text())
        assert r['strict_wire_graph']['native_device_count']==500 and r['strict_wire_graph']['native_terminal_count']==1446
        assert r['strict_wire_graph']['wire_component_count']==113
        assert r['anchors']['logical_anchor_count']==978 and r['anchors']['public_ports']==25
        assert r['anchors']['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493)
        assert all(sha(wire/n)==h for n,h in method_pins.items());r['unchanged_wire_method_sha256']=method_pins
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
        assert all(sha(Path(n))==v for n,v in protected.items())and all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        r['sources_unchanged']=True;r['status']='PASS_PD500_FLOATING_ROOT_CLEANUP_FULL_PHYSICAL_AND_UNCHANGED_STRICT_WIRES_REQUIRES_FRESH_RC'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        for name,path in [('layout',OUT/'parent/layout/result.json'),('physical',OUT/'parent/physical/result.json'),('cleanup',OUT/'cleanup-proof.json')]:
            if path.exists():r[name]=json.loads(path.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
