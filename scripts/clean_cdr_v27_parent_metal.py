#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Remove only native-LVS-proven terminal-free parent metal, never child geometry."""
import argparse,copy,hashlib,json
from collections import defaultdict
from pathlib import Path
TOP='nssoc_cdr_pd476_follower_v23'
METALS=[8,10,30,50,67,126,134]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    import pya
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args();out=args.out
    old=out/'baseline';dest=out/'layout';before=json.loads((old/'layout/result.json').read_text())
    diag=json.loads((out/'diagnosis/source/unowned-metal.json').read_text())
    assert diag['status']=='LOCATED_NATIVE_TERMINAL_FREE_METAL_NOT_ACCEPTANCE'and not diag['geometry_edited']
    assert len(diag['orphan_rows'])==8 and diag['wire_components']==119
    L=pya.Layout();L.read(str(old/'layout'/(TOP+'.gds')));T=L.cell(TOP);assert T is not None and L.dbu==.001
    db=pya.LayoutVsSchematic();db.read(str(old/'physical/lvs_flat/result.lvsdb'))
    circuit=db.netlist().top_circuit();assert len(list(circuit.each_device()))==476
    terminals=defaultdict(list);ports=defaultdict(list)
    for d in circuit.each_device():
        for td in d.device_class().terminal_definitions():terminals[d.net_for_terminal(td.id()).cluster_id].append((d.id(),td.name))
    for pin in circuit.each_pin():ports[circuit.net_for_pin(pin.id()).cluster_id].append(pin.name())
    assert sum(map(len,terminals.values()))==1382 and sum(map(len,ports.values()))==25
    full={m:pya.Region(T.begin_shapes_rec(L.layer(m,0))).merged()for m in METALS}
    mapping={}
    for m,r in full.items():
        if r.is_empty():continue
        candidates=[i for i in db.layer_indexes()if db.layer_by_index(i).bbox()==r.bbox()and db.layer_by_index(i).area()==r.area()and(db.layer_by_index(i)^r).is_empty()]
        assert len(candidates)==1;mapping[m]=candidates[0]
    rows=[];remove={}
    for n in circuit.each_net():
        if terminals[n.cluster_id]:continue
        parts={m:db.shapes_of_net(n,db.layer_by_index(i),True)for m,i in mapping.items()}
        parts={m:r for m,r in parts.items()if not r.is_empty()}
        if not parts:continue
        assert not ports[n.cluster_id]
        layers={}
        for m,r in parts.items():
            layers[str(m)]=dict(area_dbu2=r.area(),bbox_dbu=[r.bbox().left,r.bbox().bottom,r.bbox().right,r.bbox().top])
            remove[m]=remove.get(m,pya.Region())+r
        rows.append(dict(native_cluster=n.cluster_id,layers=layers))
    def compare_diagnosis(rows,diag):
        expected={r['native_cluster']:{m:{k:x[k]for k in ('area_dbu2','bbox_dbu')}for m,x in r['layers'].items()}for r in diag['orphan_rows']}
        actual={r['native_cluster']:r['layers']for r in rows}
        assert len(actual)==len(expected)==8 and actual==expected,'Native orphan identity changed'
    compare_diagnosis(rows,diag)
    rejected=[]
    for fault in ('missing_cluster','changed_cluster','changed_area','changed_box'):
        bad=copy.deepcopy(diag)
        if fault=='missing_cluster':bad['orphan_rows'].pop()
        elif fault=='changed_cluster':bad['orphan_rows'][0]['native_cluster']=-1
        else:
            layer=next(iter(bad['orphan_rows'][0]['layers'].values()))
            if fault=='changed_area':layer['area_dbu2']+=1
            else:layer['bbox_dbu'][0]+=5
        try:compare_diagnosis(rows,bad)
        except AssertionError:rejected.append(fault)
        else:raise AssertionError('Accepted cleanup identity fault '+fault)
    remove={m:r.merged()for m,r in remove.items()}
    assert set(remove)=={30,67}and {m:r.area()for m,r in remove.items()}=={30:23180000,67:9540000}
    instance_signature=sorted((i.cell.name,str(i.cplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in T.each_inst())
    child_shapes={}
    for li in L.layer_indexes():
        r=pya.Region()
        for inst in T.each_inst():
            assert inst.na in (0,1)and inst.nb in (0,1)
            r+=pya.Region(inst.cell.begin_shapes_rec(li)).transformed(inst.cplx_trans)
        child_shapes[li]=r.merged()
    before_regions={li:pya.Region(T.begin_shapes_rec(li)).merged()for li in L.layer_indexes()}
    texts={li:[s.text.dup()for s in T.shapes(li).each()if s.is_text()]for li in L.layer_indexes()}
    for m,r in remove.items():
        li=L.layer(m,0);direct=pya.Region(T.shapes(li)).merged()
        assert(r-direct).is_empty(),'Removal is not entirely in parent metal'
        assert(r&child_shapes[li]).is_empty(),'Removal touches child geometry'
        T.shapes(li).clear();T.shapes(li).insert(direct-r)
        for text in texts[li]:T.shapes(li).insert(text)
    L.write(str(dest/(TOP+'.gds')))
    R=pya.Layout();R.read(str(dest/(TOP+'.gds')));U=R.cell(TOP)
    assert sorted((i.cell.name,str(i.cplx_trans),i.na,i.nb,str(i.a),str(i.b))for i in U.each_inst())==instance_signature
    for li,region in before_regions.items():
        info=L.get_info(li);newli=R.layer(info.layer,info.datatype)
        expected=region-remove.get(info.layer,pya.Region())if info.datatype==0 else region
        actual=pya.Region(U.begin_shapes_rec(newli)).merged()
        assert(expected^actual).is_empty(),('Unplanned serialized geometry change',str(info))
        assert sorted(str(s.text)for s in U.shapes(newli).each()if s.is_text())==sorted(map(str,texts[li]))
    assert (dest/'schematic.cir').read_bytes()==(old/'layout/schematic.cir').read_bytes()
    assert sha(dest/(TOP+'.lef'))==sha(old/'layout'/(TOP+'.lef'))
    proof=dict(status='PASS_EXACT_EIGHT_NATIVE_TERMINAL_FREE_PARENT_COMPONENTS_REMOVED',before_gds_sha256=sha(old/'layout'/(TOP+'.gds')),after_gds_sha256=sha(dest/(TOP+'.gds')),
        clusters=rows,removed_area_dbu2={str(m):r.area()for m,r in remove.items()},removed_components=8,only_parent_metal_changed=True,
        all_child_geometry_unchanged=True,all_16_parent_instances_unchanged=len(instance_signature)==16,
        schematic_and_lef_unchanged=True,original_terminal_and_port_count=[1382,25],controls=rejected,
        physical_validation_passed=False,qualified_pex=False,full_phy_accepted=False)
    assert proof['all_16_parent_instances_unchanged']
    (out/'cleanup-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    meta=copy.deepcopy(before);meta['status']='GENERATED_V27_CLEAN_PARENT_REQUIRES_NATIVE_DRC_LVS_AND_GRAPH'
    meta['terminal_free_parent_cleanup']=proof
    meta['outputs']={n:sha(dest/n)for n in (TOP+'.gds',TOP+'.lef','schematic.cir')}
    meta['historical_parent_inputs']=copy.deepcopy(before['inputs'])
    consumed=[Path(__file__).resolve(),old/'layout/result.json',old/'layout'/(TOP+'.gds'),old/'layout/schematic.cir',old/'layout'/(TOP+'.lef'),old/'physical/lvs_flat/result.lvsdb',out/'diagnosis/source/unowned-metal.json',out/'children.json']
    consumed.extend(p for p in (out/'inputs').rglob('*')if p.is_file())
    meta['inputs']={str(p.resolve()):sha(p)for p in consumed}
    (dest/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
if __name__=='__main__':main()
