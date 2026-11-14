import os,json,subprocess,hashlib,zipfile
from pathlib import Path
import klayout.db as kdb
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
def archive(i,h,run):
 m=api('actions/artifacts/'+str(i));assert m['workflow_run']['id']==run and m['digest']=='sha256:'+h and not m['expired']
 p=Path(str(i)+'.zip')
 with p.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(i)+'/zip'],stdout=f,check=True)
 with p.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==h
 return zipfile.ZipFile(p)
z=archive(14131740193,'89585c334b2ae7f06b21e6851babe72ec11b5d1b4e0bee675c79090129193057',43639421390)
n=[n for n in z.namelist()if n.endswith('candidate.gds')];assert len(n)==1
b=z.read(n[0]);assert hashlib.sha256(b).hexdigest()=='ecae8ae8e49beea391b1d2575da6f5ac9ea01180550ae65fc786ddc6fd9ee193'
Path('candidate.gds').write_bytes(b)
z=archive(14131807306,'e5a2c6cbe1134e92f812b6abfe5d77bed5e797a7f4d8a3cbe6af9cf7c6af0cf4',43640767232)
anchors=json.loads(z.read('terminal-anchors.json'))
l=kdb.Layout();l.read('candidate.gds');assert len(l.top_cells())==1 and l.dbu>0
T=l.top_cell();cache={}
def reg(layer):
 if layer not in cache:cache[layer]=kdb.Region(T.begin_shapes_rec(l.layer(layer,0))).merged()
 return cache[layer]
# Actual packed graph component ownership from authenticated extraction.
seed=[r for r in anchors['rows']if r['device']in [277,280,281,286,301,304,305,310]and r['terminal']in ['E','C']and r['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE']
components={r['wire_component']for r in seed};rows=[]
for r in anchors['rows']:
 if r.get('wire_component')not in components or r['disposition']!='ACTUAL_TERMINAL_METAL_POINT_REFERENCE':continue
 x,y=r['point_dbu'];hit=reg(r['metal']).interacting(kdb.Region(kdb.Box(x-1,y-1,x+1,y+1)))
 polys=list(hit.each());assert len(polys)==1,(r,len(polys))
 poly=polys[0];box=poly.bbox()
 rows.append({'anchor':r,'same_metal_connected_polygon':{'bbox_dbu':[box.left,box.bottom,box.right,box.top],'bbox_um':[v*l.dbu for v in [box.left,box.bottom,box.right,box.top]],'area_um2':poly.area()*l.dbu*l.dbu,'hull_vertices_dbu':[[p.x,p.y]for p in poly.each_point_hull()],'holes':poly.holes()},'nearby_material':{}})
 window=kdb.Region(kdb.Box(x-int(3/l.dbu),y-int(3/l.dbu),x+int(3/l.dbu),y+int(3/l.dbu)))
 for layer in [8,10,19,29,30,49,50,66,67,125,126,133,134]:
  near=reg(layer)&window
  if not near.is_empty():rows[-1]['nearby_material'][str(layer)]=[{'bbox_dbu':[p.bbox().left,p.bbox().bottom,p.bbox().right,p.bbox().top],'hull_vertices_dbu':[[v.x,v.y]for v in p.each_point_hull()]}for p in near.each()]
result={'source_gds_sha256':hashlib.sha256(b).hexdigest(),'anchors_artifact_id':14131807306,'dbu_um':l.dbu,'top_cell':T.name,'components':sorted(components),'rows':rows,'accepted':False,'scope':'Read-only actual shared comparator anchor and same-layer connected polygon geometry. Nearby material has no inferred net ownership. No reroute, DRC/LVS, RC improvement or electrical pass claimed.'}
Path('out').mkdir();Path('out/shared-geometry.json').write_text(json.dumps(result,indent=2));print('actual shared anchor geometry',len(rows),'dbu_um',l.dbu)

# Grow only physically connected M3 polygons reached through real via stacks.
# This is a candidate requiring native DRC/LVS/freshRC, not a qualified fix.
assert abs(l.dbu-.001)<1e-12
metal3=reg(30);selected={}
for item in rows:
 r=item['anchor'];x,y=r['point_dbu'];point=kdb.Region(kdb.Box(x-1,y-1,x+1,y+1))
 if r['metal']==10:m2=reg(10).interacting(point)
 elif r['metal']==8:
  m1=reg(8).interacting(point);m2=reg(10).interacting(reg(19)&m1)
 else:continue
 assert not m2.is_empty()
 via2=reg(29)&m2;m3=metal3.interacting(via2)
 assert not m3.is_empty(),r
 component=r['wire_component'];selected[component]=(selected.get(component,kdb.Region())+m3).merged()
assert set(selected)==components
for a,ra in selected.items():
 for b,rb in selected.items():
  if a<b:assert (ra&rb).is_empty(),('M3 ownership conflict',a,b)
addition=kdb.Region();proof=[];clearance=600;growth=600
# Clip against other conductors and every unrelated adjacent-layer via.
for component,owned in sorted(selected.items()):
 other=metal3-owned
 foreign_vias=(reg(29)+reg(49))-(reg(29)+reg(49)).interacting(owned)
 expanded=(owned.sized(growth)-other.sized(clearance)-foreign_vias.sized(clearance)).merged()
 assert (owned-expanded).is_empty(),('Existing metal clipped',component)
 patch=(expanded-owned).merged()
 assert not patch.is_empty(),('No legal widening',component)
 assert (patch&other.sized(clearance-1)).is_empty()
 assert ((expanded&reg(29))^(owned&reg(29))).is_empty(),'Changed via2 incidence'
 assert ((expanded&reg(49))^(owned&reg(49))).is_empty(),'Changed via3 incidence'
 assert (expanded&addition.sized(clearance-1)).is_empty(),'Candidate net spacing conflict'
 addition=(addition+patch).merged()
 proof.append({'wire_component':component,'original_m3_area_um2':owned.area()*l.dbu*l.dbu,'added_m3_area_um2':patch.area()*l.dbu*l.dbu,'original_bbox_dbu':str(owned.bbox()),'via_incidence_unchanged':True})
assert not addition.is_empty()
# Overlay in a new wrapper; retain every original primitive and original metal.
original_name=T.name;T.name=original_name+'_unmodified'
C=l.create_cell(original_name);C.insert(kdb.CellInstArray(T.cell_index(),kdb.Trans()));C.shapes(l.layer(30,0)).insert(addition)
Path('native').mkdir();opts=kdb.SaveLayoutOptions();opts.select_cell(C.cell_index());l.write('native/candidate.gds',opts)
check=kdb.Layout();check.read('native/candidate.gds');assert len(check.top_cells())==1
actual={str(check.get_info(li)):kdb.Region(check.top_cell().begin_shapes_rec(li)).merged()for li in check.layer_indexes()}
expected={str(l.get_info(li)):kdb.Region(T.begin_shapes_rec(li)).merged()for li in l.layer_indexes()}
expected['30/0']=(expected['30/0']+addition).merged()
assert set(actual)==set(expected)
assert all((actual[k]^expected[k]).is_empty()for k in expected)
assert not (actual['30/0']^(expected['30/0']-addition)).is_empty(),'Deleted-patch control ineffective'
payload={'source_gds_sha256':result['source_gds_sha256'],'candidate_gds_sha256':hashlib.sha256(Path('native/candidate.gds').read_bytes()).hexdigest(),'accepted':False,'status':'GEOMETRY_CANDIDATE_REQUIRES_DRC_LVS_FRESH_RC_AND_ORIGINAL_LOADED_TEST','dbu_um':l.dbu,'growth_um':growth*l.dbu,'other_net_clearance_um':clearance*l.dbu,'components':proof,'only_metal3_added':True,'all_original_geometry_retained':True,'serialized_region_equality_checked':True,'deleted_patch_control_rejected':True,'scope':'Conservative local M3 widening reached through actual M1-Via1-M2-Via2 incidence. No new vias, device changes, net swaps, electrical pass or signoff claimed.'}
Path('out/shared-widening-proof.json').write_text(json.dumps(payload,indent=2))
