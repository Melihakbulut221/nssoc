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
z=archive(14148043395,'8bf417abc9ce9c1b030c02bd749d4f72c15134d3e86d7bfd59e2307ff1ec259b',43680974890)
matches=[]
for name in z.namelist():
 if name.endswith('.gds'):
  raw=z.read(name)
  if hashlib.sha256(raw).hexdigest()=='0e7b4d8da7e6de4bda98ea0a83d6dbb5ea78c73c89a60d5724ba44401c1a24c0':matches.append((name,raw))
assert matches and all(raw==matches[0][1]for name,raw in matches)
b=matches[0][1]
Path('candidate.gds').write_bytes(b)
z=archive(14148053860,'dd1a823739509bffac9a9296223908e5bbdca2a92377d638b1cf26feba3da2a3',43681114908)
anchors=json.loads(z.read('terminal-anchors.json'))
l=kdb.Layout();l.read('candidate.gds');assert len(l.top_cells())==1 and l.dbu>0
T=l.top_cell();cache={}
def reg(layer):
 if layer not in cache:cache[layer]=kdb.Region(T.begin_shapes_rec(l.layer(layer,0))).merged()
 return cache[layer]
# Actual packed graph component ownership from authenticated extraction.
seed=[r for r in anchors['rows']if r['device']in [211,216]and r['terminal']=='B'and r['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE']
components={r['wire_component']for r in seed};assert len(seed)==2 and len(components)==2;rows=[]
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
result={'source_gds_sha256':hashlib.sha256(b).hexdigest(),'anchors_artifact_id':14148053860,'dbu_um':l.dbu,'top_cell':T.name,'components':sorted(components),'rows':rows,'accepted':False,'scope':'Read-only actual clock CP/CN anchor and same-layer connected polygon geometry. Nearby material has no inferred net ownership. No reroute, DRC/LVS, RC improvement or electrical pass claimed.'}
Path('out').mkdir();Path('out/clock-geometry.json').write_text(json.dumps(result,indent=2));print('actual shared anchor geometry',len(rows),'dbu_um',l.dbu)


# Follow each actual shared conductor through every physical via, not merely
# the M3 landing. Never infer ownership from neighboring geometry.
assert abs(l.dbu-.001)<1e-12
metals=[8,10,30,50,67,126,134]
links=[(8,19,10),(10,29,30),(30,49,50),(50,66,67),(67,125,126),(126,133,134)]
owned={}
for component in sorted(components):
 sels={m:kdb.Region()for m in metals}
 for row in rows:
  r=row['anchor']
  if r['wire_component']!=component:continue
  x,y=r['point_dbu'];m=r['metal'];assert m in metals
  sels[m]=(sels[m]+reg(m).interacting(kdb.Region(kdb.Box(x-1,y-1,x+1,y+1)))).merged()
 for iteration in range(30):
  before=[sels[m].area()for m in metals]
  for lower,via,upper in links:
   sels[upper]=(sels[upper]+reg(upper).interacting(reg(via)&sels[lower])).merged()
   sels[lower]=(sels[lower]+reg(lower).interacting(reg(via)&sels[upper])).merged()
  if [sels[m].area()for m in metals]==before:break
 else:raise AssertionError('Physical conductor traversal did not converge')
 owned[component]=sels
for ca,sa in owned.items():
 for cb,sb in owned.items():
  if ca<cb:
   for m in metals:assert (sa[m]&sb[m]).is_empty(),('Net ownership conflict',ca,cb,m)
original={str(l.get_info(li)):kdb.Region(T.begin_shapes_rec(li)).merged()for li in l.layer_indexes()}
original_bbox=T.bbox()
assert original_bbox.left==0 and original_bbox.bottom==0
macro_extent=kdb.Region(original_bbox)
additions={};proof=[]
# Candidate clearances; native full DRC must confirm all actual foundry rules.
for m,growth,clearance in [(30,300,600),(50,600,600),(67,600,600),(126,2000,2000),(134,3000,3000)]:
 total=kdb.Region();adjacent=[v for lo,v,hi in links if m in (lo,hi)]
 for component,sels in sorted(owned.items()):
  own=sels[m]
  if own.is_empty():continue
  other=reg(m)-own;vias=kdb.Region()
  for v in adjacent:vias+=reg(v)
  foreign=vias-vias.interacting(own)
  patch=(own.sized(growth)-own-other.sized(clearance)-foreign.sized(clearance)-total.sized(clearance)).merged()
  patch=(patch&macro_extent).merged()
  assert (patch-macro_extent).is_empty()
  expanded=(own+patch).merged()
  assert (own-expanded).is_empty()
  assert (patch&other.sized(clearance-1)).is_empty()
  for v in adjacent:assert ((expanded&reg(v))^(own&reg(v))).is_empty(),('Changed via incidence',component,m,v)
  total=(total+patch).merged()
  proof.append(dict(component=component,metal=m,original_area_um2=own.area()*l.dbu*l.dbu,added_area_um2=patch.area()*l.dbu*l.dbu,growth_um=growth*l.dbu,clearance_um=clearance*l.dbu,via_incidence_unchanged=True))
 if not total.is_empty():additions[m]=total
assert additions,'No actual geometry change'
for m,patch in additions.items():T.shapes(l.layer(m,0)).insert(patch)
assert T.bbox()==original_bbox, 'Clock additions changed macro boundary'
Path('native').mkdir();opts=kdb.SaveLayoutOptions();opts.select_cell(T.cell_index());l.write('native/candidate.gds',opts)
check=kdb.Layout();check.read('native/candidate.gds');assert len(check.top_cells())==1
assert check.top_cell().bbox()==original_bbox, 'Serialized macro boundary changed'
actual={str(check.get_info(li)):kdb.Region(check.top_cell().begin_shapes_rec(li)).merged()for li in check.layer_indexes()}
expected=dict(original)
for m,patch in additions.items():expected[str(m)+'/0']=(expected[str(m)+'/0']+patch).merged()
assert set(actual)==set(expected) and all((actual[k]^expected[k]).is_empty()for k in expected)
assert all((original[k]-actual[k]).is_empty()for k in original)
payload=dict(source_gds_sha256=hashlib.sha256(b).hexdigest(),candidate_gds_sha256=hashlib.sha256(Path('native/candidate.gds').read_bytes()).hexdigest(),accepted=False,status='CLOCK_METAL_CANDIDATE_REQUIRES_DRC_LVS_FRESH_RC_ELECTRICAL',added_layers=sorted(additions),components=proof,original_top_hierarchy_and_labels_retained=True,all_original_geometry_retained=True,serialized_region_equality_checked=True,macro_boundary_unchanged=True,source_bbox_dbu=[original_bbox.left,original_bbox.bottom,original_bbox.right,original_bbox.top],scope='Actual via-connected CP/CN clock conductor M3 and upper-metal widening; no numerical RC scaling, device resizing or acceptance claim.')
Path('out/clock-metal-widening-proof.json').write_text(json.dumps(payload,indent=2))
print('CANDIDATE',payload['candidate_gds_sha256'],'LAYERS',payload['added_layers'],flush=True)
