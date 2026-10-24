#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read actual failed parent markers and identify geometry contributors; do not edit."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-active-input-v57-parent-diagnosis'
TOP='nssoc_cdr_pd500_active_input_v57'
def native():
 import pya
 source=OUT/'source';L=pya.Layout();L.read(str(source/'layout'/(TOP+'.gds')));T=L.cell(TOP)
 assert L.dbu==.001 and T is not None
 tree=ET.parse(source/'physical/drc/drc.lyrdb');items=tree.findall('.//items/item')
 assert len(items)==54
 metas=json.loads((source/'layout/result.json').read_text())
 categories=[dict(name=x.findtext('name'),description=x.findtext('description'))for x in tree.findall('.//categories/category')]
 regions={}
 for metal in (8,67):
  li=L.layer(metal,0);regions[(metal,'parent_direct')]=pya.Region(T.shapes(li)).flatten().merged()
  for inst in T.each_inst():
   tr=inst.dcplx_trans;key=inst.cell.name+'@'+str(tr)
   regions[(metal,key)]=pya.Region(inst.cell.begin_shapes_rec(li)).transformed(inst.cplx_trans).flatten().merged()
 markers=[]
 for item in items:
  category=item.findtext('category').strip("'");metal=8 if category.startswith('M1.')else 67
  assert category in ('M1.a','M1.b','M5.b')
  values=[v.text for v in item.findall('values/value')]
  coords=[float(v)for text in values for v in re.findall(r'-?\d+(?:\.\d+)?',text)]
  assert len(coords)>=4 and len(coords)%2==0,(category,values)
  box=pya.DBox(min(coords[::2]),min(coords[1::2]),max(coords[::2]),max(coords[1::2])).to_itype(L.dbu)
  clip=pya.Region(box.enlarged(1200));contributors=[]
  for (m,key),r in regions.items():
   if m!=metal:continue
   cut=r&clip
   if not cut.is_empty():contributors.append(dict(owner=key,area_dbu2=cut.area(),shapes=[str(x)for x in cut.each()]))
  markers.append(dict(category=category,values=values,bbox_um=str(box.to_dtype(L.dbu)),contributors=contributors))
 r=dict(status='PASS_ACTUAL54_MARKER_AND_GEOMETRY_READBACK',categories=categories,markers=markers,
        direct_parent_shapes={str(m):[str(x)for x in regions[(m,'parent_direct')].each()]for m in (8,67)},
        input_sha256={str(p):sha(p)for p in source.rglob('*')if p.is_file()},geometry_edited=False,physical_pass=False)
 (OUT/'diagnosis.json').write_text(json.dumps(r,indent=2))
def main():
 p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');a=p.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 if a.native:native();return
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False,physical_pass=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2))
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-drc-error-20261024.json').read_text())
  prior,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',['layout/'+TOP+'.gds','layout/result.json','physical/drc/drc.lyrdb'])
  assert prior==pin['report']
  measurement=prior['physical']['steps']['drc']['measurement']
  assert measurement['markers']==54 and measurement['report_sha256']==sha(OUT/'source/physical/drc/drc.lyrdb')
  r['source']=proof;save()
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  with(OUT/'native.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  r['native_returncode']=rc
  if rc:print((OUT/'native.log').read_text()[-16000:],flush=True)
  assert rc==0
  r['diagnosis']=json.loads((OUT/'diagnosis.json').read_text())
  assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in ('layout/'+TOP+'.gds','layout/result.json','physical/drc/drc.lyrdb'))
  r.update(status='PASS_FAILED_PARENT_DRC_GEOMETRY_DIAGNOSIS_NOT_PHYSICAL_CLOSURE',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
