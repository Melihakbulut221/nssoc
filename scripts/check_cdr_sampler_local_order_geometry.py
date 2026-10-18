#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independently compare every native sampler primitive drawing after reordering."""
import argparse,copy,hashlib,json
from pathlib import Path

def identity(d):
    # Local taps follow their MOS in placement order; TAP numbers are not circuit identities.
    return 'TAP_LOCAL_'+d['local_mos'] if d['kind']=='substrate_tap' and 'local_mos' in d else d['name']

def check_records(a,b):
    def canonical(d):
        r={k:v for k,v in d.items()if k not in ('placement_um','bbox_um')}
        r['name']=identity(d)
        return r
    x={identity(d):canonical(d)for d in a['instances']};y={identity(d):canonical(d)for d in b['instances']}
    assert len(a['instances'])==len(b['instances'])==len(x)==len(y)==54 and x==y, 'Native primitive identity or parameters changed'
    assert a['primitive_counts']==b['primitive_counts']==dict(hbt=16,nmos=9,rppd=12,physical_tap=17)
    assert a['source_circuit_sha256']==b['source_circuit_sha256']
    assert set(a['ports'])==set(b['ports']) and len(a['ports'])==10

def main():
    import pya
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    tops=['nssoc_rx_sampler_parallel_drive_layout_v8','nssoc_rx_sampler_local_order_layout_v9'];all_data=[];all_shapes=[];inputs={}
    for folder,topname in zip((args.baseline,args.candidate),tops,strict=True):
        data=json.loads((folder/'result.json').read_text());L=pya.Layout();L.read(str(folder/(topname+'.gds')));T=L.cell(topname);assert L.dbu==.001 and T is not None
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
                region=pya.Region(cell.begin_shapes_rec(li)).merged()
                if not region.is_empty():regions[(info.layer,info.datatype)]=region
            assert regions;assert identity(d) not in shapes;shapes[identity(d)]=regions
        all_data.append(data);all_shapes.append(shapes)
    check_records(*all_data)
    a,b=all_shapes
    def compare(x,y):
        assert set(x)==set(y)and len(x)==54
        for name in x:
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
    assert old.replace(tops[0],tops[1])==new
    faults=[]
    altered=copy.deepcopy(all_data[1]);next(d for d in altered['instances']if d['kind']=='resistor')['width_um']=999
    try:check_records(all_data[0],altered)
    except AssertionError:faults.append('wrong_resistor_width')
    else:raise AssertionError('Accepted metadata width fault')
    altered=dict(b);del altered[next(n for n in altered if n.startswith('TAP'))]
    try:compare(a,altered)
    except AssertionError:faults.append('missing_native_tap')
    else:raise AssertionError('Accepted missing tap')
    altered={n:dict(v)for n,v in b.items()};name=next(d['name']for d in all_data[1]['instances']if d['kind']=='hbt');layer=next(iter(altered[name]));altered[name][layer]=pya.Region()
    try:compare(a,altered)
    except AssertionError:faults.append('removed_native_hbt_drawing')
    else:raise AssertionError('Accepted primitive drawing corruption')
    plan=all_data[1]['placement_plan'];assert plan['unchanged_primitive_rows']and plan['weighted_span_cost_after']<plan['weighted_span_cost_before']
    r=dict(status='PASS_ALL54_NATIVE_PRIMITIVE_DRAWINGS_REFERENCE_AND_THREE_CONTROLS',inputs=inputs,primitive_count=54,checked_layer_pairs=sum(len(v)for v in a.values()),native_parameters_and_reference_unchanged=True,rejected=faults,placement_plan=plan,qualified_pex=False,full_phy_accepted=False)
    args.output.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
