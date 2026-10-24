#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independently compare every native sampler primitive drawing after reordering."""
import argparse,copy,hashlib,json
from pathlib import Path

def identity(d):
    # Local taps follow their MOS in placement order; TAP numbers are not circuit identities.
    return 'TAP_LOCAL_'+d['local_mos'] if d['kind']=='substrate_tap' and 'local_mos' in d else d['name']

DATA_PAIRS={f"{stage}_{side}"for stage in ("M","S")for side in ("DP","DN","LP","LN")}
def check_records(a,b):
    def canonical(d):
        r={k:v for k,v in d.items()if k not in ('placement_um','bbox_um')}
        r['name']=identity(d)
        return r
    x={identity(d):canonical(d)for d in a['instances']}
    y={identity(d):canonical(d)for d in b['instances']}
    assert set(x)==set(y)and len(x)==54 and DATA_PAIRS<=set(x)
    for name in x:
        if name in DATA_PAIRS:
            assert x[name]['kind']==y[name]['kind']=='hbt'
            assert x[name]['nx']==8 and y[name]['nx']==4
            assert {k:v for k,v in x[name].items()if k!='nx'}=={k:v for k,v in y[name].items()if k!='nx'}
        else:assert x[name]==y[name],('Unrelated primitive changed',name)
    assert a['primitive_counts']==b['primitive_counts']==dict(hbt=16,nmos=9,rppd=12,physical_tap=17)
    assert a['source_circuit_sha256']=='61e140fee5f40e93e11d159673cdbda65d180e25dd7538e24df9a86ae9385c79'
    assert b['source_circuit_sha256']=='b8f060f20cf9834535b11fb03742b306041e163e37a6c6cff5158dfadd97dcc2'
    assert set(a['ports'])==set(b['ports'])and len(a['ports'])==10
    assert a['ports']==b['ports']and a['bbox_um']==b['bbox_um'],'Original leaf interface changed'
    assert {identity(d):d['placement_um']for d in a['instances']}=={identity(d):d['placement_um']for d in b['instances']},'Native primitive moved'

def main():
    import pya
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    tops=['nssoc_rx_sampler_selector_layout_v19','nssoc_rx_sampler_data_layout_v20'];all_data=[];all_shapes=[];inputs={};native_layouts=[];area_snapshots=[]
    for folder,topname in zip((args.baseline,args.candidate),tops,strict=True):
        data=json.loads((folder/'result.json').read_text());L=pya.Layout();L.read(str(folder/(topname+'.gds')));T=L.cell(topname);assert L.dbu==.001 and T is not None
        native_layouts.append(L)  # Region iterators retain native geometry owned by this Layout.
        for n in ('result.json','schematic.cir',topname+'.gds'):inputs[str(folder/n)]=hashlib.sha256((folder/n).read_bytes()).hexdigest()
        dx,dy=data['origin_translation_um'];insts=list(T.each_inst());shapes={}
        for d in data['instances']:
            kind={'hbt':'npn13G2','nmos':'nmos','resistor':'rppd','substrate_tap':'ptap1'}[d['kind']]
            x,y=d['placement_um'];found=[]
            for i in insts:
                tr=i.dcplx_trans
                if i.cell.name.lower().startswith(kind.lower())and abs(tr.disp.x-x-dx)<1e-7 and abs(tr.disp.y-y-dy)<1e-7:
                    assert tr.angle==0 and not tr.is_mirror() and tr.mag==1;found.append(i.cell)
            assert len(found)==1,(d['name'],kind,len(found),[x+dx,y+dy])
            cell=found[0];regions={}
            for li in L.layer_indexes():
                info=L.get_info(li)
                if info.datatype!=0:continue
                region=pya.Region(cell.begin_shapes_rec(li)).flatten().merged()
                if not region.is_empty():regions[(info.layer,info.datatype)]=region
            assert regions;assert identity(d) not in shapes;shapes[identity(d)]=regions
        all_data.append(data);all_shapes.append(shapes)
        area_snapshots.append({n:{li:r.area() for li,r in layers.items()}for n,layers in shapes.items()})
    assert len(native_layouts)==2
    for shapes,snapshot in zip(all_shapes,area_snapshots,strict=True):
        assert {n:{li:r.area() for li,r in layers.items()}for n,layers in shapes.items()}==snapshot, 'Native region changed after reading second layout'
    check_records(*all_data)
    # Every actual primitive drawing must remain identical after placement.
    # No golden replacement or parameter exception is allowed.
    a,b=all_shapes
    def compare(x,y):
        assert set(x)==set(y)and len(x)==54
        for name in x:
            if name in DATA_PAIRS:
                assert any(not (x[name].get(li,pya.Region())^y[name].get(li,pya.Region())).is_empty()for li in set(x[name])|set(y[name])),('Data/hold drawing did not change',name)
                continue
            assert set(x[name])==set(y[name])
            for layer in x[name]:
                delta=x[name][layer]^y[name][layer]
                if not delta.is_empty():
                    report=dict(name=name,layer=layer,baseline_bbox=str(x[name][layer].bbox()),candidate_bbox=str(y[name][layer].bbox()),baseline_area=x[name][layer].area(),candidate_area=y[name][layer].area(),xor_area=delta.area(),baseline_polygons=[str(p) for p in x[name][layer].each()],candidate_polygons=[str(p) for p in y[name][layer].each()])
                    print(json.dumps(report),flush=True)
                    args.output.with_name('primitive-drawing-mismatch.json').write_text(json.dumps(report,indent=2)+'\n')
                assert delta.is_empty(),(name,layer)
    compare(a,b)
    old=(args.baseline/'schematic.cir').read_text();new=(args.candidate/'schematic.cir').read_text()
    expected=old.replace(tops[0],tops[1])
    for name in DATA_PAIRS:
        anchor='Q'+name+' '
        lines=expected.splitlines(keepends=True)
        assert sum(line.startswith(anchor)for line in lines)==1
        expected=''.join(line.replace('Nx=8','Nx=4')if line.startswith(anchor)else line for line in lines)
    assert expected==new
    faults=[]
    altered=copy.deepcopy(all_data[1]);next(d for d in altered['instances']if d['kind']=='resistor')['width_um']=999
    try:check_records(all_data[0],altered)
    except AssertionError:faults.append('wrong_resistor_width')
    else:raise AssertionError('Accepted metadata width fault')
    altered=dict(b);del altered[next(n for n in altered if n.startswith('TAP'))]
    try:compare(a,altered)
    except AssertionError:faults.append('missing_native_tap')
    else:raise AssertionError('Accepted missing tap')
    altered={n:dict(v)for n,v in b.items()};name=next(d['name']for d in all_data[1]['instances']if d['kind']=='hbt' and d['name']not in DATA_PAIRS);layer=next(iter(altered[name]));altered[name][layer]=pya.Region()
    try:compare(a,altered)
    except AssertionError:faults.append('removed_native_hbt_drawing')
    else:raise AssertionError('Accepted primitive drawing corruption')
    altered=copy.deepcopy(all_data[1]);next(d for d in altered['instances']if d['name']=='M_DP')['nx']=8
    try:check_records(all_data[0],altered)
    except AssertionError:faults.append('wrong_data_nx')
    else:raise AssertionError('Unchanged data/hold size accepted')
    altered=copy.deepcopy(all_data[1]);altered['instances'][0]['placement_um'][0]+=.005
    try:check_records(all_data[0],altered)
    except AssertionError:faults.append('moved_native_primitive')
    else:raise AssertionError('Changed native primitive position accepted')
    assert len(faults)==5
    r=dict(status='PASS_EXACT_EIGHT_DATA_HOLD_NX_CHANGES_AND46_UNCHANGED_NATIVE_DRAWINGS',
        inputs=inputs,primitive_count=54,changed_data_pairs=sorted(DATA_PAIRS),
        before_nx=8,after_nx=4,unchanged_primitive_drawings=46,rejected=faults,
        all_native_reference_changes_explicit=True,qualified_pex=False,full_phy_accepted=False,
        scope='Fresh native PCell geometry and unsimplified LVS required; old parent RC cannot qualify this new geometry.')
    args.output.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
