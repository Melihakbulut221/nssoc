# SPDX-License-Identifier: Apache-2.0
"""Cloud-only all-layer polygon comparison; no filename-based equivalence."""
import hashlib,json,pathlib,tarfile,zipfile
import klayout.db as db
out=pathlib.Path('out');out.mkdir(exist_ok=True)
r={'status':'ERROR','full_chip_lvs':False,'manufacturing_approval':False,'scope':'Compare flattened polygons at original coordinates, every layer/datatype. Texts are inventoried but not equated. Not electrical LVS or current-chip acceptance.'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(raw,name):
 p=pathlib.Path(name);p.write_bytes(raw);l=db.Layout();l.read(str(p));return l
try:
 assert file_sha('pkg.tgz')=='822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4'
 assert file_sha('cc.zip')=='d266fe1a64e0c09716552f44a8ebb27c13e39a461c208d7153386b59429f7d90'
 with zipfile.ZipFile('cc.zip') as z:
  names=[n for n in z.namelist() if n.endswith('DP8TSRAMDP256x16.gds')];assert len(names)==1
  archived=z.read(names[0]);assert sha(archived)=='c6a1be71d0439e88e2c08729345eb8d8001f773266cb7a8b939446e54999ff45'
 with tarfile.open('pkg.tgz','r:gz') as t:
  candidates=[m for m in t if m.isfile() and m.name.endswith('/sg13g2_sram/gds/RM_IHPSG13_2P_256x16_c2_bm_bist.gds')];assert len(candidates)==1
  current=t.extractfile(candidates[0]).read();assert sha(current)=='420b5223d14e2f873a2464849e3decbbec2b5b16b3c6a0f8cd2bb21b0d52365b'
 layouts=[load(archived,'archived.gds'),load(current,'current.gds')];tops=[];inventories=[]
 for label,l in zip(['verified_archive','routed_input'],layouts):
  ts=list(l.top_cells());assert len(ts)==1,(label,'ambiguous top');top=ts[0];tops.append(top)
  inventories.append({'label':label,'dbu_um':l.dbu,'top':top.name,'bbox_dbu':[top.bbox().left,top.bbox().bottom,top.bbox().right,top.bbox().top],'cells':sorted(c.name for c in l.each_cell()),'layers':sorted([l.get_info(i).layer,l.get_info(i).datatype] for i in l.layer_indexes())})
 r['inventories']=inventories
 assert layouts[0].dbu==layouts[1].dbu,'different grids need explicit normalization'
 maps=[{(l.get_info(i).layer,l.get_info(i).datatype):i for i in l.layer_indexes()} for l in layouts]
 assert all(len(m)==len(list(l.layer_indexes())) for m,l in zip(maps,layouts)),'duplicate layer mapping'
 rows=[]
 for key in sorted(set(maps[0])|set(maps[1])):
  regions=[]
  for l,top,m in zip(layouts,tops,maps):
   reg=db.Region(top.begin_shapes_rec(m[key])) if key in m else db.Region();reg.merge();regions.append(reg)
  difference=regions[0]^regions[1]
  rows.append({'layer':key[0],'datatype':key[1],'archive_area_dbu2':regions[0].area(),'routed_area_dbu2':regions[1].area(),'xor_area_dbu2':difference.area(),'xor_polygons':difference.count(),'equal':difference.is_empty()})
 r.update(status='POLYGON_COMPARISON_COMPLETED',layers=rows,all_polygon_layers_identical=all(x['equal'] for x in rows),archive_sha256=sha(archived),routed_sha256=sha(current))
except Exception as e:r['error']=type(e).__name__+': '+str(e)
(out/'sram-geometry-comparison.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='inventories'}));raise SystemExit(0 if r['status']=='POLYGON_COMPARISON_COMPLETED' else 1)
