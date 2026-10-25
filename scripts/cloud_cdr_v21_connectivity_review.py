#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inspect actual failed native LVS connectivity; never waive or rewrite it."""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-v21-connectivity-review'
TOP='nssoc_cdr_pd484_localbus_v12'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def native():
 import pya
 def rect(raw):
  return pya.DBox(*map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)))
 def load(directory,dbpath):
  meta=json.loads((directory/'layout/result.json').read_text())
  L=pya.Layout();L.read(str(directory/'layout'/(TOP+'.gds')));T=L.cell(TOP)
  D=pya.LayoutVsSchematic();D.read(str(directory/dbpath))
  assert L.dbu==.001 and T is not None
  layers={}
  for m in (67,126,134):
   full=pya.Region(T.begin_shapes_rec(L.layer(m,0))).merged()
   found=[i for i in D.layer_indexes()if (D.layer_by_index(i)^full).is_empty()]
   assert len(found)==1,(m,found)
   layers[m]=D.layer_by_index(found[0])
  anchors=[]
  for node in meta['source_plan']['nodes']:
   place=meta['placements'][node['tag']]
   for pin,net in node['pins'].items():
    box=rect(place['ports'][pin]);m=meta['source_plan']['types'][node['kind']]['layer']
    n=D.probe_net(layers[m],box.to_itype(L.dbu).center());assert n is not None
    anchors.append(dict(label=node['tag']+'.'+pin,logical_net=net,cluster=n.cluster_id,native_name=n.name))
  for net,raw in meta['ports'].items():
   n=D.probe_net(layers[134],rect(raw).to_itype(L.dbu).center());assert n is not None
   anchors.append(dict(label='public.'+net,logical_net=net,cluster=n.cluster_id,native_name=n.name))
  assert len(anchors)==158
  groups={};inverse={}
  for a in anchors:
   groups.setdefault(a['logical_net'],set()).add(a['cluster'])
   inverse.setdefault(a['cluster'],set()).add(a['logical_net'])
  return L,T,D,layers,meta,anchors,groups,inverse
 old=load(OUT/'original','physical/lvs_flat/result.lvsdb')
 new=load(OUT/'candidate','physical/lvs/result.lvsdb')
 assert len(old[6])==len(old[7])==51 and all(len(v)==1 for v in old[6].values())
 problems=[a for a in new[5]if len(new[6][a['logical_net']])!=1 or len(new[7][a['cluster']])!=1]
 # Include actual netlist comparison state; an empty anchor problem list can
 # still conceal an internal unmatched terminal and must never imply a pass.
 mismatch=dict(open_logical_nets={n:sorted(v)for n,v in new[6].items()if len(v)>1},
  shorted_logical_nets={str(n):sorted(v)for n,v in new[7].items()if len(v)>1},
  affected_anchors=problems,all_candidate_anchors=new[5])
 old_l,old_t,old_db,layers,meta,_,_,_=old
 r=new[4]['collector_trunk_relocation'];assert len(r['changed_rectangles'])==14
 changed=[q for q in r['changed_rectangles']if q['layer']==126];assert len(changed)==4
 existing=pya.Region(old_t.begin_shapes_rec(old_l.layer(126,0))).merged()
 for c in changed:existing-=pya.Region(pya.Box.from_s(c['before_box_dbu']))
 overlaps=[]
 for c in changed:
  target=pya.Region(pya.Box.from_s(c['after_box_dbu']))
  for poly in (existing&target).merged().each():
   box=poly.bbox();n=old_db.probe_net(layers[126],box.center())
   overlaps.append(dict(target=c['after_box_dbu'],intersection_dbu=str(poly),area_dbu2=poly.area(),
     original_cluster=None if n is None else n.cluster_id,original_native_name=None if n is None else n.name))
 result=dict(status='READ_ONLY_NATIVE_LVS_MISMATCH_DIAGNOSIS_NOT_ACCEPTANCE',mismatch=mismatch,
  new_trunk_intersections_with_retained_original_tm1=overlaps,
  original_all158anchors_51distinct_nets=True,original_and_candidate_dbu=.001,
  candidate_geometry_unchanged=True,full_phy_accepted=False,accepted=False)
 (OUT/'native-connectivity.json').write_text(json.dumps(result,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');a=p.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 if a.native:native();return
 OUT.mkdir(exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
 try:
  sources=[
   ('candidate','cdr-collector-trunks-v21-parent',39438730794,'82b0b6e799da7cfd45d9385cb51b59a1b5ee9edb8c03e3b6772fd531909e42dd','6334caad8f48bafd422298018aba4e99a5a9d18790cf7c0fd34ed39d43f8985a','physical/lvs/result.lvsdb'),
   ('original','cdr-data-v20-parent',39420628714,'e00f439f650c884950ccc232bca90a26958cce39e93606316834a991e945e463','7bf653c3d1a370acb7c34704423e60277261e29c68919579976ff37518d1cd78','physical/lvs_flat/result.lvsdb')]
  protected={}
  for directory,group,run,summary,parts,db in sources:
   names=['layout/result.json','layout/'+TOP+'.gds',db]
   report,proof=reports.restore_report(group,run,summary,parts,OUT/directory,names);r[directory+'_source']=proof
   if directory=='candidate':
    assert report['generation_returncode']==report['child_geometry_returncode']==0 and report['physical_returncode']==1
    assert report['physical']['steps']['drc']['measurement']['markers']==0
    assert report['physical']['steps']['lvs']['audit']['circuit_status_counts']=={'NoMatch':1}
   else:assert report['sources_unchanged']and report['physical']['status']=='PASS_NATIVE_PDK_CDR_PD484_DRC_LVS_AND_FAULT_CONTROLS'
   protected.update({str(OUT/directory/n):report['outputs'][n]for n in names})
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  with(OUT/'native.log').open('w')as f:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native'],stdout=f,stderr=subprocess.STDOUT,cwd=ROOT)
  r['native_returncode']=rc
  if rc:print((OUT/'native.log').read_text()[-12000:],flush=True)
  assert rc==0
  r['diagnosis']=json.loads((OUT/'native-connectivity.json').read_text())
  assert all(sha(Path(n))==h for n,h in protected.items())
  r.update(status='COMPLETE_NATIVE_CONNECTIVITY_DIAGNOSIS_ORIGINAL_LVS_REMAINS_FAILED',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
