#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independently verify every placed leaf drawing and actual transform in PD484."""
import hashlib,json,re
from collections import Counter
from pathlib import Path

def check(parent):
    import pya
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    owners=[];sources={};snapshots=[]
    def read(path,top):
        L=pya.Layout();L.read(str(path));owners.append(L)
        T=L.cell(top);assert T is not None and L.dbu==.001
        sources[str(path)]=sha(path)
        return L,T
    def regions(L,T):
        result={}
        for li in L.layer_indexes():
            info=L.get_info(li)
            if info.layer in (8,10,30,50,67,126,134) and info.datatype in (2,25):continue
            r=pya.Region(T.begin_shapes_rec(li)).flatten().merged()
            if not r.is_empty():result[(info.layer,info.datatype)]=r
        assert result
        snapshots.append((result,{k:r.area()for k,r in result.items()}))
        return result
    def same(a,b):
        assert set(a)==set(b)
        for k in a:assert (a[k]^b[k]).is_empty(),('Changed native child geometry',k)
    A=parent/'layout';meta=json.loads((A/'result.json').read_text());plan=meta['source_plan']
    sources[str(A/'result.json')]=sha(A/'result.json')
    L,T=read(A/'nssoc_cdr_pd484_localbus_v12.gds','nssoc_cdr_pd484_localbus_v12')
    assert len(meta['placements'])==16 and sum(meta['primitive_census'].values())==484
    sources[str(parent/'children.json')]=sha(parent/'children.json')
    manifest=json.loads((parent/'children.json').read_text())
    expected={};copied={};counts={}
    for kind,item in manifest['children'].items():
        directory=parent/item['directory'];name=plan['types'][kind]['top']
        child_l,child_t=read(directory/(name+'.gds'),name)
        assert child_t.dbbox().left==child_t.dbbox().bottom==0
        target=L.cell('pd_child_'+kind);assert target is not None
        expected[kind]=regions(child_l,child_t);copied[kind]=regions(L,target)
        same(expected[kind],copied[kind]);counts[kind]=len(expected[kind])
    rows=[]
    for inst in T.each_inst():
        if not inst.cell.name.startswith('pd_child_'):continue
        tr=inst.dcplx_trans;assert tr.angle==0 and not tr.is_mirror() and tr.mag==1
        b=inst.dbbox();rows.append(dict(kind=inst.cell.name.removeprefix('pd_child_'),bbox=[b.left,b.bottom,b.right,b.top],translation=[tr.disp.x,tr.disp.y]))
    def placements(actual):
        assert len(actual)==16
        assert Counter(v['kind']for v in actual)==Counter(n['kind']for n in plan['nodes'])
        used=set()
        for tag,p in meta['placements'].items():
            box=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',p['bbox_um'])));assert len(box)==4
            found=[i for i,r in enumerate(actual)if r['kind']==p['kind']and all(abs(a-b)<1e-7 for a,b in zip(r['bbox'],box,strict=True))and r['translation']==r['bbox'][:2]]
            assert len(found)==1 and found[0]not in used,('Wrong actual macro placement',tag)
            used.add(found[0])
        assert len(used)==16
    placements(rows)
    for shapes,snapshot in snapshots:assert {k:r.area()for k,r in shapes.items()}==snapshot,'Native regions lost their Layout owner'
    controls=[]
    kind='sampler';key=next(k for k in expected[kind]if k[1]==0)
    bad=dict(copied[kind]);cut=pya.Region(next(bad[key].each()));bad[key]=bad[key]-cut
    try:same(expected[kind],bad)
    except AssertionError:controls.append('removed_native_sampler_polygon')
    else:raise AssertionError('Accepted removed primitive geometry')
    bad=[dict(r)for r in rows];bad[0]={**bad[0],'translation':[bad[0]['translation'][0]+.005,bad[0]['translation'][1]]}
    try:placements(bad)
    except AssertionError:controls.append('shifted_actual_macro_transform')
    else:raise AssertionError('Accepted shifted macro')
    try:placements(rows[:-1])
    except AssertionError:controls.append('missing_actual_macro')
    else:raise AssertionError('Accepted missing macro')
    sources[str(Path(__file__))]=sha(Path(__file__))
    return dict(status='PASS_ALL16_ACTUAL_PLACEMENTS_AND_EIGHT_NATIVE_LEAF_DRAWINGS',checked_layers_by_kind=counts,actual_placements=rows,controls=controls,inputs=sources,scope='Exact non-port-annotation child drawings and actual native transforms. Parent connectivity is independently checked against unsimplified LVS and158 native planes. Does not certify RC or electrical behavior.',full_phy_accepted=False)
