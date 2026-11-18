#!/usr/bin/env python3
"""Route authenticated additive diode ECO. No timing or foundry signoff implied."""
import os,json,subprocess,hashlib,zipfile,io,stat
from pathlib import Path
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/core-only-antenna-reroute'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,status='PREPARING')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 try:
  run=api('actions/runs/44381946807');assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']=='14f4ff51de6541638ed75d13152bb5f6b5113611'and run['run_attempt']==1
  aid=int(os.environ['INSERTION_ARTIFACT']);digest=os.environ['INSERTION_DIGEST'];assert len(digest)==64
  meta=api('actions/artifacts/'+str(aid));assert meta['workflow_run']['id']==run['id']and meta['digest']=='sha256:'+digest
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(raw).hexdigest()==digest
  z=zipfile.ZipFile(io.BytesIO(raw));src=json.loads(z.read('result.json'));assert src['source_head']==run['head_sha']and src['sources_unchanged']and not src['accepted']
  assert src['status']=='DIODES_INSERTED_AND_IDENTITY_AUDITED_REQUIRES_DETAILED_ROUTING_AND_SIGNOFF'
  assert src['insertion_audit']['original_geometry_status_and_connections_preserved']and src['insertion_audit']['all_new_terminals_connected']
  assert src['insertion_audit']['original_instances']==105251 and src['insertion_audit']['new_diodes']>0
  base=Path(os.environ['RUNNER_TEMP'])/'antenna-insertion-input';base.mkdir();seen=set()
  for item in z.infolist():
   if item.is_dir()or item.filename=='result.json':continue
   n=item.filename;assert not Path(n).is_absolute()and '..'not in Path(n).parts and not stat.S_ISLNK(item.external_attr>>16)and n not in seen
   data=z.read(item);assert hashlib.sha256(data).hexdigest()==src['outputs'][n];p=base/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);seen.add(n)
  assert seen==set(src['outputs'])
  before=base/'core-antennas-inserted-unrouted.odb';assert sha(before)==src['output_odb_sha256']
  controls=api('actions/runs/44382097435');assert controls['conclusion']=='success'and controls['head_sha']=='21ddfc693f50fcd5ead6e0e288d083651b900823'and controls['run_attempt']==1
  audit=ROOT/'scripts/audit_core_only_antenna_insertion.py';assert sha(audit)==src['protected_inputs'][str(ROOT/'scripts/audit_core_only_antenna_insertion.py')]
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  tcl=OUT/'route.tcl';tcl.write_text('read_db $::env(NSSOC_ROUTE_INPUT)\nset_thread_count 4\nset_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nsource $::env(NSSOC_PRUNE_GUIDES)\nputs "REMOVED_ORPHAN_GUIDES [prune_orphan_guides [ord::get_db_block]]"\ndetailed_route -droute_end_iter 64 -or_seed 42 -verbose 1 -output_drc $::env(NSSOC_ROUTE_DRC)\nwrite_db $::env(NSSOC_ROUTE_OUTPUT)\nset antenna_nets [check_antennas -report_file $::env(NSSOC_ANTENNA_REPORT)]\nputs "NSSOC_FINAL_ANTENNA_NETS $antenna_nets"\nputs "NSSOC_ROUTE_COMPLETE"\n')
  guard=ROOT/'scripts/audit_core_only_route_identity.py';geometry=ROOT/'scripts/audit_native_signal_geometry_indexed.py';prune=ROOT/'hw/soc/flow/prune_orphan_guides.tcl'
  protected={str(p):sha(p)for p in [Path(__file__),before,tcl,guard,geometry,prune,audit,ROOT/'scripts/native_geometry_contact_index.py',ROOT/'scripts/buffer_core_only_chip_controls.py']}
  r.update(status='DETAILED_ROUTING',protected_inputs=protected,source_admission=dict(run=run['id'],head=run['head_sha'],artifact=aid,digest=digest,verified_outputs=len(seen),insertion_audit=src['insertion_audit']))
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
