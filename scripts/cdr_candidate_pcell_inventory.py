#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate actual candidate PCells; inspect dimensions, never claim macro LVS."""
import argparse,hashlib,json,math,sys
from pathlib import Path
from decimal import Decimal
import build_pcie_local_vco_hybrid_v6 as parser

def specs():
    rows=[]
    for w in (36,54):
        rows.append(dict(tag='nmos_w'+str(w),cell='nmos',parameters=dict(w=str(w)+'u',l='.3u',ng=1)))
    for nx in (2,3,4,5,6):
        rows.append(dict(tag='hbt_nx'+str(nx),cell='npn13G2',parameters=dict(Nx=nx)))
    for w in (4,6,8):
        for length in ('.9','1.2'):
            rows.append(dict(tag='rppd_w'+str(w)+'_l'+length.replace('.','p'),cell='rppd',parameters=dict(w=str(w)+'u',l=length+'u')))
    for length in ('1.0','1.2','1.6','2.6'):
        rows.append(dict(tag='collector_l'+length.replace('.','p'),cell='rppd',parameters=dict(w='32u',l=length+'u')))
    assert len(rows)==17 and len({r['tag']for r in rows})==17
    return rows

def verify_parameters(requested,observed):
    for key,value in requested.items():
        assert key in observed, ('Native PCell omitted parameter',key)
        if key in ('w','l'):
            assert parser.number(str(observed[key]))==parser.number(str(value)), ('Native dimension clamp or mismatch',key,value,observed[key])
        else:assert Decimal(str(observed[key]))==Decimal(str(value)), ('Native parameter mismatch',key)

def controls():
    request=dict(w='54u',l='.3u',ng=1)
    verify_parameters(request,dict(w='54e-6',l='0.3e-6',ng=1))
    rejected=[]
    for name,value in [('w','36u'),('l','.31u'),('ng',2),('missing',None)]:
        bad=dict(request)
        if name=='missing':bad.pop('w')
        else:bad[name]=value
        try:verify_parameters(request,bad)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Native PCell mismatch accepted')
    return dict(cells=len(specs()),rejected=rejected,equivalent_si_spelling_passed=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--pdk',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    out=args.out;out.mkdir(parents=True,exist_ok=False)
    source=args.pdk.resolve()/'libs.tech/klayout/python'
    inputs=[*source.rglob('*.py'),*source.rglob('*.json'),Path(__file__)]
    digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    protected={str(x):digest(x)for x in inputs}
    assert len(protected)>10
    sys.dont_write_bytecode=True
    sys.path[:0]=[str(source),str(source/'pycell4klayout-api/source/python')]
    import pya
    import sg13g2_pycell_lib
    layout=pya.Layout();top=layout.create_cell('nssoc_cdr_candidate_pcell_inventory')
    records=[];x=0.
    for spec in specs():
        cell=layout.create_cell(spec['cell'],'SG13_dev',spec['parameters'])
        assert cell is not None and not cell.is_empty()
        observed=cell.pcell_parameters_by_name()
        verify_parameters(spec['parameters'],observed)
        box=cell.dbbox()
        assert all(math.isfinite(z)for z in (box.left,box.bottom,box.right,box.top)) and box.width()>0 and box.height()>0
        trans=pya.DTrans(x-box.left,-box.bottom)
        top.insert(pya.DCellInstArray(cell.cell_index(),trans))
        records.append(dict(**spec,native_parameters={k:observed[k]for k in spec['parameters']},
            native_bbox_um=[box.left,box.bottom,box.right,box.top],width_um=box.width(),height_um=box.height(),
            original_sampler_top_limit_um=50.,satisfies_original_local_top_limit=box.top<50.,
            inventory_translation_um=[x-box.left,-box.bottom],
            scope='Actual isolated PCell only; local top limit is necessary but not sufficient for sampler placement or DRC.'))
        x+=box.width()+40.
    gds=out/'candidate-pcells.gds';layout.write(str(gds))
    assert gds.stat().st_size>0
    assert all(digest(Path(k))==v for k,v in protected.items())
    result=dict(status='PASS_ACTUAL17_PCELL_PARAMETER_READBACK_AND_GEOMETRY_INVENTORY_NOT_LAYOUT_SIGNOFF',
        controls=controls(),native_cells=records,source_files=protected,sources_unchanged=True,
        gds_sha256=digest(gds),gds_bytes=gds.stat().st_size,
        candidate_macro_generated=False,macro_drc_passed=False,macro_lvs_passed=False,
        extracted_diffusion_parameters_proven=False,qualified_pex=False,full_phy_accepted=False,
        scope='Real PDK PCell parameter readback, bounding boxes and drawings for candidate layout planning. This does not qualify MOS AS/AD/PS/PD, connectivity, taps, complete macro/parent routing, DRC/LVS or electrical timing.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],cells=len(records))),flush=True)
if __name__=='__main__':
    if '--controls'in sys.argv:print(json.dumps(controls()))
    else:main()
