import os,subprocess,json,hashlib,io,zipfile,re
from pathlib import Path
import klayout.db as db
assert os.environ.get('GITHUB_ACTIONS')=='true'
out=Path('current650-placement-audit');out.mkdir()
repo='repos/Melihakbulut221/nssoc/'
def api(path):return json.loads(subprocess.check_output(['gh','api',repo+path]))
def archive(run,head,aid,digest):
    r=api('actions/runs/'+str(run));assert r['conclusion']=='success' and r['head_sha']==head and r['run_attempt']==1
    m=api('actions/artifacts/'+str(aid));assert not m['expired'] and m['workflow_run']['id']==run and m['digest']=='sha256:'+digest
    data=subprocess.check_output(['gh','api',repo+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(data).hexdigest()==digest
    return zipfile.ZipFile(io.BytesIO(data))
z=archive(43748270188,'4a37a0285be11fc7d424daa830887ec7bde5654b',14175765192,'a1381011a37b531184deedcca9e57e6bdba3ce18ac9d7a280ff0f00c1747504a')
data=z.read('candidate650-select-width2.gds');assert hashlib.sha256(data).hexdigest()=='5f66ce0cb46acfb580b517ba02b10f66560ba4200d9cfbba0b633a839cc59c5a'
proof=json.loads(z.read('result.json'));assert proof['steps']['drc']['measurement']['markers']==0
gds=out/'source.gds';gds.write_bytes(data)
old=archive(43695046876,'7c253a13438932af701b33f6c9d6c76f2ddfa6b5',14154400256,'c79134cba9fcd33d749903b93d9a71b940771c3da7266ad4b1ed4ff051600248')
metadata=json.loads(old.read('hw/soc/out/cloud-cdr-wire-shortcuts-physical/layout/result.json'))
(out/'source-metadata.json').write_text(json.dumps(metadata,indent=2))
layout=db.Layout();layout.read(str(gds));top=layout.cell('nssoc_cdr_pd500_resistor_v59');assert top and layout.dbu==.001
children=[i for i in top.each_inst() if i.cell.name.startswith('pd_child_')]
assert children
def bounds(b):return [b.left,b.bottom,b.right,b.top]
inventory=[dict(name=i.cell.name,transform=str(i.dcplx_trans),bbox_dbu=bounds(i.bbox()),array=i.is_regular_array())for i in children]
ordered=sorted(children,key=lambda i:i.bbox().bottom)
gaps=[]
for left,right in zip(ordered,ordered[1:]):
    lo=left.bbox().top;hi=right.bbox().bottom
    gaps.append(dict(lower=left.cell.name,upper=right.cell.name,low_dbu=lo,high_dbu=hi,
                     gap_um=(hi-lo)*layout.dbu,cut_dbu=5*round((lo+hi)/10)))
parent={}
for li in layout.layer_indexes():
    info=layout.get_info(li)
    full=db.Region(top.begin_shapes_rec(li)).merged();child=db.Region()
    for inst in children:
        child+=db.Region(inst.cell.begin_shapes_rec(li)).transformed(inst.cplx_trans)
    remainder=(full-child.merged()).merged()
    if not remainder.is_empty():parent[(info.layer,info.datatype)]=remainder
crossings=[]
for gap in gaps:
    cut=gap['cut_dbu'];rows=[]
    for layer,region in parent.items():
        crossing=[p for p in region.each()if p.bbox().bottom<cut<p.bbox().top]
        if crossing:
            rows.append(dict(layer=list(layer),count=len(crossing),boxes_dbu=[bounds(p.bbox())for p in crossing]))
    crossings.append(dict(**gap,parent_crossings=rows))
r=dict(source_head=os.environ['GITHUB_SHA'],source_gds_sha256=hashlib.sha256(data).hexdigest(),
       child_count=len(children),children=inventory,metadata_keys=list(metadata),
       metadata_placements=metadata.get('placements'),bands=crossings,
       source_unchanged=hashlib.sha256(gds.read_bytes()).hexdigest()==hashlib.sha256(data).hexdigest(),
       geometry_modified=False,full_phy_accepted=False,
       scope='Read-only exact650 hierarchy and candidate band-boundary audit. Crossings require explicit rerouting, never cutting or dropping material. Parent remainder is full geometry minus union of child geometry; overlapping material ownership is not resolved by this audit.')

# Locate cuts with a full 1um clear margin from all non-trunk material.
# This is a feasibility test, not permission to discard crossing TM1.
cut_plans=[]
for gap in gaps:
    candidates=range(gap['low_dbu']+1000,gap['high_dbu']-999,5)
    forbidden=[]
    for (layer,datatype),region in parent.items():
        if (layer,datatype)==(126,0):continue
        for poly in region.each():
            box=poly.bbox()
            if box.top>=gap['low_dbu'] and box.bottom<=gap['high_dbu']:
                forbidden.append((box.bottom-1000,box.top+1000))
    allowed=[y for y in candidates if not any(lo<=y<=hi for lo,hi in forbidden)]
    cut=min(allowed,key=lambda y:abs(y-gap['cut_dbu']))if allowed else None
    trunks=[]
    if cut is not None:
        for poly in parent.get((126,0),db.Region()).each():
            box=poly.bbox()
            if box.bottom<cut<box.top:
                trunks.append(dict(bbox_dbu=bounds(box),rectangle=poly.area()==box.area(),
                                   area_dbu2=poly.area()))
    cut_plans.append(dict(lower=gap['lower'],upper=gap['upper'],low_dbu=gap['low_dbu'],
                          high_dbu=gap['high_dbu'],selected_cut_dbu=cut,
                          nontrunk_clearance_dbu=1000,allowed_grid_sites=len(allowed),
                          crossing_tm1_polygons=trunks))
r['cut_feasibility']=cut_plans
r['all_boundaries_have_nontrunk_clear_cut']=all(x['selected_cut_dbu']is not None for x in cut_plans)
r['no_geometry_change_or_electrical_acceptance']=True

(out/'result.json').write_text(json.dumps(r,indent=2))
