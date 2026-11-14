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
