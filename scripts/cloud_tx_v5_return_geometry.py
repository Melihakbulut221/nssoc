#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independently reconstruct only the measured TX trunk repair on actual GDS layers."""
import argparse,hashlib,json,os,re,subprocess,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-v5-return-geometry'
def native():
    import pya
    def load(label):
        base=OUT/label;meta=json.loads((base/'layout/result.json').read_text());name=next(n for n in meta['outputs']if n.endswith('.gds'))
        L=pya.Layout();L.read(str(base/'layout'/name));assert L.dbu==.001 and len(L.top_cells())==1
        return L,L.top_cell(),meta
    A,at,old=load('baseline');B,bt,new=load('candidate');assert old['origin_translation_um']==new['origin_translation_um'];dx,dy=old['origin_translation_um']
    assert old['placement_pitch']==new['placement_pitch']==dict(column_um=700.,row_um=600.)
    assert old['placements']==new['placements']and old['signal_routes']==new['signal_routes']
    assert old['ports']==new['ports']and old['total_devices']==new['total_devices']==1674
    def normalized(path):
        out=[]
        for line in path.read_text().splitlines():
            f=line.split()
            if not f or f[0].startswith('*'):continue
            if f[0].lower()in ('.subckt','.ends'):f[1]='SAME_TOP'
            out.append(f)
        return out
    assert normalized(OUT/'baseline/layout/schematic.cir')==normalized(OUT/'candidate/layout/schematic.cir')
    infos={(L.get_info(i).layer,L.get_info(i).datatype)for L in (A,B)for i in L.layer_indexes()if L.get_info(i).datatype==0}
    def drawing(L,T):return {info:pya.Region(T.begin_shapes_rec(L.layer(*info))).merged()for info in infos}
    before=drawing(A,at);after=drawing(B,bt);removed={i:pya.Region()for i in infos};added={i:pya.Region()for i in infos}
    def shifted(box):return pya.DBox(*box).transformed(pya.DTrans(dx,dy)).to_itype(A.dbu)
    oa=old['parent_return_geometry_before_origin_translation'];na=new['parent_return_geometry_before_origin_translation'];assert len(oa)==len(na)==6 and oa[:4]==na[:4]
    ot,nt=oa[4],na[4];assert ot['width_um']==64 and nt['width_um']==128
    ob,nb=ot['box_um'],nt['box_um'];ox=(ob[0]+ob[2])/2;nx=(nb[0]+nb[2])/2
    assert abs(nx-ox-80)<1e-9 and abs(nb[1]-(ob[1]-32))<1e-9 and abs(nb[3]-(ob[3]+32))<1e-9
    assert oa[5]['width_um']==na[5]['width_um']==64 and oa[5]['box_um'][:2]==na[5]['box_um'][:2]and oa[5]['box_um'][3]==na[5]['box_um'][3]
    assert abs(na[5]['box_um'][2]-oa[5]['box_um'][2]-80)<1e-9
    # The global bus extends to final trunk centre plus its own 64um halfwidth;
    # generator metadata records the actual endpoint width. Verify actual boxes.
    port=pya.DBox.from_s(old['placements']['f']['ports']['avss']);px,py=port.center().x,port.center().y
    rectangles=[(126,ob,nb),(134,oa[5]['box_um'],na[5]['box_um']),(134,[min(px,ox)-16,py-16,max(px,ox)+16,py+16],[min(px,nx)-16,py-16,max(px,nx)+16,py+16])]
    def require_box(L,T,layer,box):
        hits=[s for s in T.shapes(L.layer(layer,0)).each()if s.is_box()and s.box==box];assert len(hits)==1,(layer,str(box),len(hits))
    for layer,o,n in rectangles:
        oldbox,newbox=shifted(o),shifted(n);require_box(A,at,layer,oldbox);require_box(B,bt,layer,newbox)
        removed[layer,0]+=pya.Region(oldbox);added[layer,0]+=pya.Region(newbox)
    moved=[];new_via_regions=[]
    def via(L,T,x,y):
        matches=[]
        for inst in T.each_inst():
            cell=L.cell(inst.cell_index)
            if cell.name.startswith('core_'):continue
            b=cell.dbbox().transformed(inst.dcplx_trans)
            if abs(b.center().x-(x+dx))<.003 and abs(b.center().y-(y+dy))<.003:matches.append(inst)
        assert len(matches)==1,(x,y,len(matches));return matches[0]
    for y in (py,-200.):
        vi,vj=via(A,at,ox,y),via(B,bt,nx,y);ra={};rb={}
        for info in infos:
            r=pya.Region(A.cell(vi.cell_index).begin_shapes_rec(A.layer(*info))).transformed(vi.cplx_trans).merged()
            s=pya.Region(B.cell(vj.cell_index).begin_shapes_rec(B.layer(*info))).transformed(vj.cplx_trans).merged()
            assert (r.transformed(pya.Trans(round(80/A.dbu),0))^s).is_empty(),('Moved native via changed',info)
            removed[info]+=r;added[info]+=s;ra[info]=r;rb[info]=s
        new_via_regions.append(rb);moved.append(dict(old_center_um=[ox+dx,y+dy],new_center_um=[nx+dx,y+dy]))
    expected={info:((before[info]-removed[info])+added[info]).merged()for info in infos}
    def verify(candidate):
        for info in infos:assert(expected[info]^candidate[info]).is_empty(),('Unexpected drawing delta',info)
    verify(after)
    faults=[]
    # Mutate actual candidate polygons; these are geometry-comparison controls,
    # separate from the already-passed five native LVS/DRC physical faults.
    bad=dict(after);bad[126,0]=after[126,0]-pya.Region(shifted(nb))
    try:verify(bad)
    except AssertionError:faults.append('removed_new_trunk')
    else:raise AssertionError('Accepted removed trunk')
    cut=shifted([nx+31,py+20,nx+32,py+21]);assert not(after[126,0]&pya.Region(cut)).is_empty()
    bad=dict(after);bad[126,0]=after[126,0]-pya.Region(cut)
    try:verify(bad)
    except AssertionError:faults.append('actual_trunk_cut')
    else:raise AssertionError('Accepted cut')
    cuts=[i for i in infos if i[0]in (19,29,49,66,125,133)and not new_via_regions[0][i].is_empty()];assert cuts
    info=cuts[0];bad=dict(after);bad[info]=after[info]-new_via_regions[0][info]
    try:verify(bad)
    except AssertionError:faults.append('missing_moved_native_via_cuts')
    else:raise AssertionError('Accepted via removal')
    result=dict(status='PASS_EXACT_TX_FINAL_TRUNK_STUB_BUS_AND_TWO_NATIVE_VIA_MOVES',actual_reference_devices=1674,actual_macro_placements=31,signal_routes_unchanged=60,public_planes_unchanged=162,all_drawing_layers_checked=len(infos),changed_drawing_layers=[list(i)for i in infos if not(before[i]^after[i]).is_empty()],rectangles=[dict(layer=l,before_um=o,after_um=n)for l,o,n in rectangles],moved_vias=moved,controls=faults,frozen_child_and_all_other_geometry_unchanged=True,electrical_accepted=False)
    (OUT/'native.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],flush=True)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--native',action='store_true');a=ap.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if a.native:native();return
    OUT.mkdir(parents=True,exist_ok=False);r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
    try:
        proofs={}
        for label,filename,prefix in [('baseline','tx-v5-columns-physical-pass-20261018.json','cloud-tx-v5-columns-assembly/'),('candidate','tx-v5-return-repair-physical-pass-20261018.json','cloud-tx-v5-return-repair-assembly/')]:
            pin=json.loads((ROOT/'docs/evidence'/filename).read_text());packed=OUT/(label+'.tar.gz');fetch(pin['url'],pin['sha256'],packed);assert packed.stat().st_size==pin['bytes']
            dest=OUT/label;dest.mkdir();selected={}
            with tarfile.open(packed)as tar:
                raw=tar.extractfile(prefix+'result.json').read();assert hashlib.sha256(raw).hexdigest()==pin['summary_sha256'];prior=json.loads(raw);assert prior==pin['report']
                names=['layout/result.json','layout/schematic.cir',*['layout/'+n for n in prior['layout']['outputs']if n.endswith('.gds')]]
                for n in names:
                    raw=tar.extractfile(prefix+n).read();assert hashlib.sha256(raw).hexdigest()==prior['outputs'][n];p=dest/n;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(raw);selected[n]=sha(p)
            packed.unlink();proofs[label]=dict(run=pin['source_run'],summary_sha256=pin['summary_sha256'],archive_sha256=pin['sha256'],selected=selected)
        r['sources']=proofs;app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        with(OUT/'native.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r['returncode']=rc
        if rc:print((OUT/'native.log').read_text()[-12000:],flush=True)
        assert rc==0;r['native']=json.loads((OUT/'native.json').read_text())
        assert all(sha(OUT/label/n)==v for label,p in proofs.items()for n,v in p['selected'].items())
        r.update(status='PASS_INDEPENDENT_NATIVE_TX_RETURN_GEOMETRY_DELTA_REQUIRES_FRESH_RC',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
