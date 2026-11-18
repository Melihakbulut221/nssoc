#!/usr/bin/env python3
"""Route authenticated additive diode ECO. No timing or foundry signoff implied."""
import os,json,subprocess,hashlib,zipfile,io,stat
from pathlib import Path
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/core-only-critical-detailedroute'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,status='PREPARING')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 try:
  from cloud_core_only_postgrt import completed,archive,safe_path,put
  run=completed(44400094526,'6df2ae68122fa3ae95a7fa43ced91cf51c35667e')
  z,meta=archive(run,'core-only-critical-globalroute-44400094526')
  aid=14473695972;digest='e79245dfbdd45320ed97b0974638189d4dfcac84adc18de26f16bcfe1657744d'
  assert meta['id']==aid and meta['digest']=='sha256:'+digest
  src=json.loads(z.read('result.json'));assert src['source_head']==run['head_sha'] and src['sources_unchanged'] and src['returncode']==0 and not src['accepted']
  assert src['source_binding']['eco_run']==44399362987 and src['source_binding']['eco_head']=='dfa8f24652dc77838f127b77980364ee5bf944b6'
  assert src['eco_audit']['resized_cells']==6 and src['eco_audit']['instances']==106083
  for c in src['corners'].values():
   assert c['metrics']['timing__setup_vio__count']==0 and c['metrics']['timing__hold_vio__count']==0
  base=Path(os.environ['RUNNER_TEMP'])/'critical-globalroute-input';base.mkdir();seen=set()
  for item in z.infolist():
   if item.is_dir()or item.filename=='result.json':continue
   n=item.filename;assert not stat.S_ISLNK(item.external_attr>>16) and n not in seen
   put(safe_path(base,n),z.read(item),src['outputs'][n]);seen.add(n)
  assert seen==set(src['outputs'])
  state=json.loads(z.read(src['output_state']));prefix=str(ROOT/'hw/soc/out/core-only-critical-globalroute')+'/'
  assert state['odb'].startswith(prefix);odbname=state['odb'][len(prefix):]
  before=safe_path(base,odbname);assert sha(before)==src['outputs'][odbname]
  # Recheck global-route instance/connectivity against the admitted ECO source.
  eco_run=completed(44399362987,'dfa8f24652dc77838f127b77980364ee5bf944b6')
  ez,em=archive(eco_run,'core-only-critical-resize-44399362987')
  assert em['id']==14471483674 and em['digest']=='sha256:2e58e8e6031aa15fcaa98de675970602b0578d72b62361a175d6fb560f912d9c'
  original=base/'candidate-unrouted.odb';put(original,ez.read('candidate-unrouted.odb'),'4da67d1ffad55f5cb4aacbcea38b2e7c27124f8a728e79056bd096435b624c60')
  audit=ROOT/'scripts/audit_core_only_route_identity.py'
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  admission=OUT/'globalroute-identity';admission.mkdir()
  env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_ROUTE_IDENTITY_BEFORE=str(original),NSSOC_ROUTE_IDENTITY_AFTER=str(before),NSSOC_ROUTE_IDENTITY_OUT=str(admission))
  with (OUT/'globalroute-identity.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(audit)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['globalroute_identity']=json.loads((admission/'route-identity.json').read_text());assert r['globalroute_identity']['instances']==106083
  tcl=OUT/'route.tcl';tcl.write_text('read_db $::env(NSSOC_ROUTE_INPUT)\nset_thread_count 4\nset_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nsource $::env(NSSOC_PRUNE_GUIDES)\nputs "REMOVED_ORPHAN_GUIDES [prune_orphan_guides [ord::get_db_block]]"\ndetailed_route -droute_end_iter 64 -or_seed 42 -verbose 1 -output_drc $::env(NSSOC_ROUTE_DRC)\nwrite_db $::env(NSSOC_ROUTE_OUTPUT)\nset antenna_nets [check_antennas -report_file $::env(NSSOC_ANTENNA_REPORT)]\nputs "NSSOC_FINAL_ANTENNA_NETS $antenna_nets"\nputs "NSSOC_ROUTE_COMPLETE"\n')
  guard=ROOT/'scripts/audit_core_only_route_identity.py';geometry=ROOT/'scripts/audit_native_signal_geometry_indexed.py';prune=ROOT/'hw/soc/flow/prune_orphan_guides.tcl'
  protected={str(p):sha(p)for p in [Path(__file__),before,tcl,guard,geometry,prune,audit,ROOT/'scripts/native_geometry_contact_index.py',ROOT/'scripts/buffer_core_only_chip_controls.py']}
  r.update(status='DETAILED_ROUTING',protected_inputs=protected,source_admission=dict(run=run['id'],head=run['head_sha'],artifact=aid,digest=digest,verified_outputs=len(seen),eco_audit=src['eco_audit'],estimated_corners=src['corners']))
  after=OUT/'soc_top.odb';metrics=OUT/'metrics.json';save()
  env=dict(os.environ,NSSOC_ROUTE_INPUT=str(before),NSSOC_ROUTE_OUTPUT=str(after),NSSOC_PRUNE_GUIDES=str(prune),NSSOC_ROUTE_DRC=str(OUT/'soc_top.drc'),NSSOC_ANTENNA_REPORT=str(OUT/'antenna.rpt'))
  with (OUT/'route.log').open('w')as log:proc=subprocess.run([str(app),'openroad','-exit','-metrics',str(metrics),str(tcl)],env=env,stdout=log,stderr=subprocess.STDOUT)
  r['returncode']=proc.returncode;assert proc.returncode==0 and after.is_file()and 'NSSOC_ROUTE_COMPLETE'in (OUT/'route.log').read_text()
  r['metrics']=json.loads(metrics.read_text());r['routed_odb_sha256']=sha(after);save()
  identity=OUT/'identity';identity.mkdir()
  env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_ROUTE_IDENTITY_BEFORE=str(before),NSSOC_ROUTE_IDENTITY_AFTER=str(after),NSSOC_ROUTE_IDENTITY_OUT=str(identity))
  with (OUT/'identity.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(guard)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['route_identity']=json.loads((identity/'route-identity.json').read_text());save()
  geom=OUT/'geometry';geom.mkdir();env=dict(os.environ,NSSOC_PHYSICAL_ROUTE_OUT=str(geom),NSSOC_PHYSICAL_ROUTE_ODB=str(after))
  with (OUT/'geometry.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(geometry)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['visible_geometry']=json.loads((geom/'physical-route-audit.json').read_text())
  assert r['metrics']['route__drc_errors']==0
  assert r['metrics']['antenna__violating__nets']==0 and r['metrics']['antenna__violating__pins']==0
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='ROUTING_ANTENNA_AND_VISIBLE_GEOMETRY_CHECKED_REQUIRES_FRESH_RC_TIMING_AND_SIGNOFF',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
