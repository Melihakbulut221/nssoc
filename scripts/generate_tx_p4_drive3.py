#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replace four physical p4 cells with the existing native nx3 master.
Every public pin and every parent route is preserved. Fresh native gates decide.
"""
import copy,json,re,sys
from collections import Counter
from pathlib import Path
import pya
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
TAGS=tuple('p4_'+str(i)for i in range(4))
def box(raw):
    v=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)))
    assert len(v)==4
    return pya.DBox(*v)
def generate(out):
    source=out/'source/layout';old=json.loads((source/'result.json').read_text())
    name=next(n for n in old['outputs']if n.endswith('.gds'));path=source/name
    assert sha(path)==old['outputs'][name]=='b8ee72861b772cea2ea42746710dec3075c85fb2999c7204e55b9f1536585ab4'
    A=pya.Layout();A.read(str(path));B=pya.Layout();B.read(str(path))
    assert A.dbu==B.dbu==.001 and len(A.top_cells())==len(B.top_cells())==1
    top=A.top_cell();target=B.top_cell()
    assert old['total_devices']==1674 and len(old['placements'])==31 and len(old['signal_routes'])==60
    dx,dy=old['origin_translation_um'];origin=pya.DTrans(dx,dy)
    meta=copy.deepcopy(old);changes=[]
    def wanted_transform(tag):return origin*pya.DTrans.from_s(old['placements'][tag]['transform'])
    def find(L,tag):
        tr=wanted_transform(tag);matches=[i for i in L.top_cell().each_inst()if str(i.dtrans)==str(tr)and L.cell(i.cell_index).name in ('core_pre','core_pre_low','core_final')]
        assert len(matches)==1,(tag,str(tr),len(matches))
        return matches[0]
    exemplar=find(A,'a');assert A.cell(exemplar.cell_index).name=='core_pre'
    base_ports=old['placements']['a']['ports'];assert len(base_ports)==12
    expected={}
    for tag in TAGS:
        before=old['placements'][tag];assert before['kind']=='pre_low'
        deltas=[]
        for port in base_ports:
            a=box(base_ports[port]);b=box(before['ports'][port]);shift=pya.DTrans(b.left-a.left,b.bottom-a.bottom)
            assert str(a.transformed(shift))==str(b),(tag,port,'Pin shape differs')
            deltas.append((round(b.left-a.left,6),round(b.bottom-a.bottom,6)))
        assert len(set(deltas))==1,(tag,'Not a single exact all-pin translation',deltas)
        sx,sy=deltas[0];newtr=pya.DTrans(sx,sy)*exemplar.dtrans
        i=find(B,tag);assert B.cell(i.cell_index).name=='core_pre_low'
        oldcell=i.cell_index;oldtr=str(i.dtrans);before_native_bbox=i.bbox()
        i.cell_index=B.cell('core_pre').cell_index();i.dtrans=newtr
        expected[tag]=(oldcell,oldtr,i.cell_index,str(newtr))
        local=pya.DTrans(-dx,-dy)*newtr
        native_footprint=i.bbox()
        expected_old=box(before['bbox_um']).to_itype(A.dbu).transformed(pya.Trans(round(dx/A.dbu),round(dy/A.dbu)))
        assert before_native_bbox==expected_old,('Original native/metadata bounds differ',tag,str(before_native_bbox),str(expected_old))
        footprint=native_footprint.transformed(pya.Trans(-round(dx/A.dbu),-round(dy/A.dbu))).to_dtype(A.dbu)
        oldbox=box(before['bbox_um'])
        probe=dict(tag=tag,before_native_bbox_dbu=str(before_native_bbox),candidate_native_bbox_dbu=str(native_footprint),candidate_transform=str(newtr),old_float_bbox=str(oldbox),new_float_bbox=str(footprint))
        (out/'placement-candidate.json').write_text(json.dumps(probe,indent=2)+'\n')
        assert before_native_bbox.left<=native_footprint.left and before_native_bbox.right>=native_footprint.right,probe
        assert before_native_bbox.bottom<=native_footprint.bottom and before_native_bbox.top>=native_footprint.top,probe
        assert native_footprint.height()<before_native_bbox.height(),probe
        meta['placements'][tag].update(kind='pre',transform=str(local),bbox_um=str(footprint))
        changes.append(dict(tag=tag,original_kind='pre_low',candidate_kind='pre',
            before_transform=before['transform'],after_transform=str(local),
            before_bbox=before['bbox_um'],after_bbox=str(footprint),
            public_pin_rectangles_identical=True,original_emitters=19,candidate_emitters=55))
    def instances(L,c):
        return sorted((L.cell(i.cell_index).name,str(i.dtrans),i.na,i.nb,str(i.a),str(i.b))for i in c.each_inst())
    expected_instances=instances(B,target)
    cells={c.name:c for c in A.each_cell()}
    def verify(L):
        assert L.dbu==A.dbu and L.top_cell().name==top.name
        actual={c.name:c for c in L.each_cell()};assert set(actual)==set(cells)
        infos={(A.get_info(i).layer,A.get_info(i).datatype)for i in A.layer_indexes()}|{(L.get_info(i).layer,L.get_info(i).datatype)for i in L.layer_indexes()}
        for name,ca in cells.items():
            cb=actual[name]
            assert instances(L,cb)==(expected_instances if name==top.name else instances(A,ca)),('Unplanned instance change',name)
            for layer,dt in infos:
                ia=A.layer(layer,dt);ib=L.layer(layer,dt)
                if dt==0:
                    assert (pya.Region(ca.shapes(ia)).merged()^pya.Region(cb.shapes(ib)).merged()).is_empty(),('Changed local drawing',name,layer)
                else:
                    assert sorted(str(s)for s in ca.shapes(ia).each())==sorted(str(s)for s in cb.shapes(ib).each()),('Changed annotation',name,layer,dt)
        assert L.top_cell().bbox()==top.bbox()
    verify(B)
    # Rebind the complete existing high-drive a circuit, never merely edit Nx.
    pp=ROOT/'docs/evidence/tx-v5-timing-priority-physical-pass-20261019.json'
    baseline=json.loads(pp.read_text());maps=baseline['report']['plan']['maps']
    assert baseline['run']==39304550527 and baseline['summary_sha256']=='03caa3a4f54f8e14402894a81321e33796f6ec6c502ec39fcc59e4db20e1dd5d'
    assert baseline['report']['layout']['total_devices']==1674
    cir=source/'schematic.cir';lines=cir.read_text().splitlines()
    def cards(tag,rows):return [l.split()for l in rows if re.match(r'^[QR]'+re.escape(tag)+r'_',l)]
    high=cards('a',lines);assert len(high)==54 and sum(r[0].startswith('Q')for r in high)==19
    assert sum(int(re.search(r'\bNx=(\d+)\b',' '.join(r))[1])for r in high if r[0].startswith('Q'))==55
    replacements={};circuit_changes=[]
    for tag in TAGS:
        original=cards(tag,lines);assert len(original)==54
        assert sum(int(re.search(r'\bNx=(\d+)\b',' '.join(r))[1])for r in original if r[0].startswith('Q'))==19
        mapping={net:maps[tag][port]for port,net in maps['a'].items()};assert len(mapping)==12
        def rename_net(n):
            if n in mapping:return mapping[n]
            if n.startswith('a_'):return tag+n[1:]
            assert n=='BULK',('Unbound original native net',n)
            return n
        candidate=[]
        for row in high:
            r=row.copy();r[0]=r[0][0]+tag+'_'+r[0][3:]
            count=4 if row[0].startswith('Q')else 2 if row[3]=='ptap1'else 3
            assert r[count+1]in ('npn13G2','rppd','ptap1')
            r[1:count+1]=[rename_net(n)for n in row[1:count+1]]
            candidate.append(r)
        assert {r[0]for r in candidate}=={r[0]for r in original}
        replacements.update({r[0]:' '.join(r)for r in candidate})
        circuit_changes.append(dict(tag=tag,original_cards=original,candidate_cards=candidate,source_master='a',public_mapping=mapping))
    newlines=[replacements.get(l.split()[0],l)if l.split()else l for l in lines]
    assert len(replacements)==216 and len(newlines)==len(lines)
    untouched=[l for l in lines if not l.split()or l.split()[0]not in replacements]
    assert untouched==[l for l in newlines if not l.split()or l.split()[0]not in replacements]
    hbts=[l for l in newlines if l.startswith('Q')]
    emitters=sum(int(re.search(r'\bNx=(\d+)\b',l)[1])for l in hbts)
    assert len(hbts)==589 and emitters==863
    dest=out/'layout';dest.mkdir();B.write(str(dest/name))
    C=pya.Layout();C.read(str(dest/name));verify(C)
    for filename in old['outputs']:
        if filename.endswith('.lef'):(dest/filename).write_bytes((source/filename).read_bytes())
    (dest/'schematic.cir').write_text('\n'.join(newlines)+'\n')
    assert meta['ports']==old['ports']and meta['signal_routes']==old['signal_routes']
    meta.update(status='GENERATED_UNVERIFIED_FOUR_P4_NATIVE_NX3_MACROS_FIXED_PINS_AND_PARENT_ROUTES',
        inputs={str(p):sha(p)for p in (Path(__file__),path,cir,source/'result.json',pp)},
        outputs={p.name:sha(p)for p in dest.iterdir()},
        frozen_child_drawing_regions_equal=True,
        scope='Four p4 low-drive instances replaced by existing native high-drive master at an exact twelve-pin translation. Parent drawings/routes/pins/LEF and all master drawings unchanged. Full native circuit cards rebound by topology. 863 core emitters; whole-chip emitter budget and fresh RC/electrical behavior remain unproven.')
    (dest/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
    faults=[];faultdir=out/'geometry-faults';faultdir.mkdir()
    def reject(label):
        f=faultdir/(label+'.gds');B.write(str(f))
        try:verify(B)
        except AssertionError:faults.append(dict(name=label,rejected=True,gds_sha256=sha(f)))
        else:raise AssertionError('Accepted '+label)
    victim=next(i for i in target.each_inst()if str(i.dtrans)==expected[TAGS[0]][3]and B.cell(i.cell_index).name=='core_pre')
    cell=victim.cell_index;tr=victim.dtrans
    victim.cell_index=B.cell('core_pre_low').cell_index();reject('wrong_native_macro');victim.cell_index=cell
    victim.dtrans=pya.DTrans(.005,0)*tr;reject('shift_native_pins_5nm');victim.dtrans=tr
    li=B.layer(126,0);saved=pya.Region(target.shapes(li));assert not saved.is_empty()
    target.shapes(li).clear();reject('missing_parent_metal');target.shapes(li).insert(saved);verify(B)
    result=dict(status='PASS_FOUR_P4_NATIVE_MASTER_REPLACEMENTS_ALL_PINS_PARENT_ROUTES_AND_THREE_FAULTS',
        source_gds_sha256=sha(path),candidate_gds_sha256=sha(dest/name),
        changes=changes,circuit_changes=circuit_changes,original_master_drawings_unchanged=True,
        parent_drawings_routes_and_pins_unchanged=True,lef_byte_identical=True,
        reference_hbts=589,reference_emitters=emitters,four_lane_core_emitter_projection=4*emitters,
        whole_chip_emitter_budget_qualified=False,serialized_gds_verified=True,controls=faults,
        electrical_accepted=False,qualified_pex=False,full_phy_accepted=False)
    (out/'geometry-delta.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':generate(Path(sys.argv[1]).resolve())
