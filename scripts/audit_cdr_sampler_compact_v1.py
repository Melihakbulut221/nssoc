#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare native PCell drawings and exact source reference before DRC/LVS."""
import argparse,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out
    sys.path.insert(0,str(ROOT/'hw/soc/flow'))
    import make_pcie_sampler_cell as baseline
    import make_pcie_sampler_compact_v1 as candidate
    import pya
    old=out/'baseline';new=out/'layout'
    br=json.loads((old/'result.json').read_text());nr=json.loads((new/'result.json').read_text())
    assert br['primitive_counts']==nr['primitive_counts']==dict(hbt=15,rppd=12,physical_tap=8)
    before=(old/'schematic.cir').read_text();after=(new/'schematic.cir').read_text()
    assert before.count(baseline.TOP)==2 and before.replace(baseline.TOP,candidate.TOP)==after
    assert br['source_circuit_sha256']==nr['source_circuit_sha256']==baseline.CIRCUIT_SHA256
    # Parameterized native PCells, including every via, must be identical on
    # every flattened layer. Only top-level placement and routing may change.
    bl=pya.Layout();bl.read(str(old/(baseline.TOP+'.gds')))
    nl=pya.Layout();nl.read(str(new/(candidate.TOP+'.gds')))
    assert bl.dbu==nl.dbu
    bc={c.name:c for c in bl.each_cell()if c.name!=baseline.TOP}
    nc={c.name:c for c in nl.each_cell()if c.name!=candidate.TOP}
    assert bc.keys()==nc.keys()
    compared=[]
    for name,c in bc.items():
        d=nc[name];assert c.dbbox()==d.dbbox(),name
        layers={(bl.get_info(i).layer,bl.get_info(i).datatype)for i in bl.layer_indexes()}|{(nl.get_info(i).layer,nl.get_info(i).datatype)for i in nl.layer_indexes()}
        for layer in layers:
            x=pya.Region(c.begin_shapes_rec(bl.layer(*layer)))
            y=pya.Region(d.begin_shapes_rec(nl.layer(*layer)))
            assert (x^y).is_empty(),(name,layer)
        compared.append(name)
    assert len(br['instances'])==len(nr['instances'])==35
    for b,n in zip(br['instances'],nr['instances'],strict=True):
        ignore={'placement_um','bbox_um'}
        assert {k:v for k,v in b.items()if k not in ignore}=={k:v for k,v in n.items()if k not in ignore}
    bw,bh=br['bbox_um'][2:];nw,nh=nr['bbox_um'][2:]
    assert nw<bw and nh<bh and nw*nh<bw*bh
    assert len(br['routes'])==len(nr['routes']) and len(br['vias'])==len(nr['vias'])
    result=dict(status='PASS_NATIVE_PCELL_GEOMETRY_AND_CIRCUIT_PRESERVED_REQUIRES_DRC_LVS_AND_FRESH_RC',
        original_bbox_um=br['bbox_um'],candidate_bbox_um=nr['bbox_um'],area_ratio=nw*nh/(bw*bh),
        compared_native_cells=compared,primitive_counts=nr['primitive_counts'],
        only_top_name_changed_in_reference=True,all_original_physical_gates_required=True,
        full_phy_accepted=False,qualified_pex=False,loaded_wave_accepted=False,
        inputs={str(f.relative_to(ROOT)):sha(f)for d in(old,new)for f in d.iterdir()if f.is_file()})
    (out/'compaction-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
