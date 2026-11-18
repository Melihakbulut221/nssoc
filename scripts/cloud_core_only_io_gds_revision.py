#!/usr/bin/env python3
"""Native recursive polygon and text comparison of two official I/O GDS views."""
import os,json,hashlib,urllib.request
from pathlib import Path
import klayout.db as db
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/core-only-io-gds-revision'
SOURCES=[('old','c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c','6b9cf6fd110e9c78040a433ecce704171e275bfe',71399424),('new','cc9afba57e0ec1b5ba77e6bbb638ba9dbe5866b8','f12b92abbb474add36ca5447ab4a54c9dce56f89',71426048)]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def texts(cell,layer):
 rows=[];it=cell.begin_shapes_rec(layer)
 while not it.at_end():
  shape=it.shape()
  if shape.is_text():rows.append(str(shape.text.transformed(it.trans())))
  it.next()
 return sorted(rows)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING',klayout_version=db.__version__,sources=[],cells={},connectivity_equivalence_proven=False,manufacturing_approval=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 try:
  assert db.__version__=='0.30.9'
  layouts=[];paths=[]
  for label,ref,blob,size in SOURCES:
   url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+ref+'/ihp-sg13g2/libs.ref/sg13g2_io/gds/sg13g2_io.gds'
   path=Path(os.environ['RUNNER_TEMP'])/('nssoc-io-'+label+'.gds')
   with urllib.request.urlopen(url,timeout=180)as f:raw=f.read(size+1)
   assert len(raw)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+raw).hexdigest()==blob
   path.write_bytes(raw);digest=sha(path);del raw
   ly=db.Layout();ly.read(str(path));layouts.append(ly);paths.append((path,digest))
   r['sources'].append(dict(label=label,commit=ref,git_blob=blob,bytes=size,sha256=digest,url=url,dbu=ly.dbu))
  old,new=layouts;assert old.dbu==new.dbu
  names=[{c.name for c in ly.each_cell()}for ly in layouts]
  wanted=sorted(n for n in names[0]|names[1] if n.startswith('sg13g2_IOPad')or n in ['sg13g2_GateDecode','sg13g2_LevelDown','sg13g2_DCNDiode','sg13g2_DCPDiode'])
  assert 'sg13g2_IOPadInOut4mA'in wanted
  layers=[{(ly.get_info(i).layer,ly.get_info(i).datatype):i for i in ly.layer_indexes()}for ly in layouts]
  for name in wanted:
   if name not in names[0]or name not in names[1]:
    r['cells'][name]=dict(present_old=name in names[0],present_new=name in names[1]);save();continue
   cells=[ly.cell(name)for ly in layouts];changes=[];checked=0
   for layer in sorted(set(layers[0])|set(layers[1])):
    regions=[];labels=[]
    for j in range(2):
     idx=layers[j].get(layer)
     regions.append(db.Region()if idx is None else db.Region(cells[j].begin_shapes_rec(idx)).merged())
     labels.append([]if idx is None else texts(cells[j],idx))
    delta=regions[0]^regions[1];checked+=1
    if not delta.is_empty()or labels[0]!=labels[1]:
     changes.append(dict(layer=list(layer),xor_area_dbu2=delta.area(),xor_polygons=delta.count(),old_area_dbu2=regions[0].area(),new_area_dbu2=regions[1].area(),text_equal=labels[0]==labels[1],old_text=labels[0],new_text=labels[1]))
   r['cells'][name]=dict(present_old=True,present_new=True,old_bbox=str(cells[0].bbox()),new_bbox=str(cells[1].bbox()),checked_layers=checked,changed_layers=changes,recursive_polygon_and_text_equal=not changes);save()
  assert all(sha(p)==h for p,h in paths)
  r.update(status='OFFICIAL_IO_GDS_GEOMETRY_DIFF_MEASURED_REQUIRES_CONNECTIVITY_AND_TIMING_REVIEW',sources_unchanged=True,script_sha256=sha(__file__),compared_cells=len(wanted),changed_cells=[n for n,v in r['cells'].items()if not v.get('recursive_polygon_and_text_equal',False)])
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:save()
if __name__=='__main__':main()
