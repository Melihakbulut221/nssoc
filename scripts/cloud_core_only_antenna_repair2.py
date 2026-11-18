#!/usr/bin/env python3
"""Route authenticated additive diode ECO. No timing or foundry signoff implied."""
import os,json,subprocess,hashlib,zipfile,io,stat
from pathlib import Path
from bootstrap_flow import verify
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/core-only-antenna-repair2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,status='PREPARING')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 try:
  run=api('actions/runs/44383558280');assert run['status']=='completed'and run['conclusion']=='failure'and run['head_sha']=='b42104b780290a762ecf705e0741af846db8d43b'and run['run_attempt']==1
  aid=14467291770;digest='8ff4da47a0db4ca80da0b04fba83a6a6829969e3c3be39916bbe6d0cdb6bd7f3'
  meta=api('actions/artifacts/'+str(aid));assert meta['workflow_run']['id']==run['id']and meta['digest']=='sha256:'+digest
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(raw).hexdigest()==digest
  z=zipfile.ZipFile(io.BytesIO(raw));src=json.loads(z.read('result.json'));assert src['source_head']==run['head_sha']and src['returncode']==0 and src['status']=='FAIL_OR_INCOMPLETE'
  assert src['metrics']['route__drc_errors']==0 and src['metrics']['antenna__violating__nets']==17 and src['metrics']['antenna__violating__pins']==19
  assert src['route_identity']['instances']==106051 and src['route_identity']['sources_unchanged']
  g=src['visible_geometry'];assert g['source_unchanged']and not g['signal_nets_with_disconnected_geometry']and not g['unwired_multi_terminal_nets']and not g['terminals_without_geometry']and g['inter_net_contact_pairs']==0
  base=Path(os.environ['RUNNER_TEMP'])/'antenna-repair2-input';base.mkdir();seen=set()
  for item in z.infolist():
   if item.is_dir()or item.filename=='result.json':continue
   n=item.filename;assert not Path(n).is_absolute()and '..'not in Path(n).parts and not stat.S_ISLNK(item.external_attr>>16)and n not in seen
   data=z.read(item);assert hashlib.sha256(data).hexdigest()==src['outputs'][n];p=base/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);seen.add(n)
  assert seen==set(src['outputs'])
  original=base/'soc_top.odb';assert sha(original)==src['routed_odb_sha256']=='77fcf3c7134a4b7d36f33117e39a7c8cf0818000fb1b95cdf5167b831f5b687f'
  r['source_admission']=dict(run=run['id'],head=run['head_sha'],artifact=aid,digest=digest,verified_outputs=len(seen),metrics=src['metrics'],identity=src['route_identity'],geometry=g)
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  before=OUT/'diodes-inserted.odb';insert=OUT/'insert.tcl';audit=ROOT/'scripts/audit_core_only_antenna_insertion.py';power=ROOT/'scripts/audit_antenna_power_contact.py'
  insert.write_text('read_db $::env(NSSOC_REPAIR_INPUT)\nset_thread_count 4\nset_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nset_global_routing_layer_adjustment Metal2-TopMetal2 0.2\nputs "NSSOC_INSERTED_DIODES [repair_antennas sg13g2_antennanp -iterations 1 -ratio_margin 10 -diode_only]"\nglobal_connect\ncheck_placement -verbose\nwrite_db $::env(NSSOC_REPAIR_OUTPUT)\nputs NSSOC_INSERTION_COMPLETE\n')
  protected={str(p):sha(p)for p in [Path(__file__),original,insert,audit,power,ROOT/'scripts/audit_core_only_route_identity.py',ROOT/'scripts/buffer_core_only_chip_controls.py']}
  r.update(status='INSERTING_ADDITIONAL_DIODES',protected_inputs=protected,antenna_repair_ratio_margin_percent=10);save()
  env=dict(os.environ,NSSOC_REPAIR_INPUT=str(original),NSSOC_REPAIR_OUTPUT=str(before))
  with (OUT/'insertion.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(insert)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  assert before.is_file()and 'NSSOC_INSERTION_COMPLETE'in(OUT/'insertion.log').read_text()
  inv=OUT/'insertion-audit.json';env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_ROUTE_IDENTITY_BEFORE=str(original),NSSOC_ROUTE_IDENTITY_AFTER=str(before),NSSOC_ANTENNA_AUDIT_OUT=str(inv))
  with (OUT/'insertion-audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(audit)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  added=json.loads(inv.read_text());assert added['original_instances']==106051 and added['new_diodes']>0 and added['sources_unchanged'];r['insertion_audit']=added;save()
  env=dict(os.environ,ANTENNA_POWER_ODB=str(before),ANTENNA_POWER_REPORT=str(OUT/'power-contact.json'),ANTENNA_POWER_INVENTORY=str(inv),ANTENNA_POWER_EXPECTED_DIODES=str(added['new_diodes']))
  with (OUT/'power-contact.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(power)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['added_power_contact']=json.loads((OUT/'power-contact.json').read_text());protected[str(inv)]=sha(inv)
  tcl=OUT/'route.tcl';tcl.write_text('read_db $::env(NSSOC_ROUTE_INPUT)\nset_thread_count 4\nset_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nsource $::env(NSSOC_PRUNE_GUIDES)\nputs "REMOVED_ORPHAN_GUIDES [prune_orphan_guides [ord::get_db_block]]"\ndetailed_route -droute_end_iter 64 -or_seed 42 -verbose 1 -output_drc $::env(NSSOC_ROUTE_DRC)\nwrite_db $::env(NSSOC_ROUTE_OUTPUT)\nset antenna_nets [check_antennas -report_file $::env(NSSOC_ANTENNA_REPORT)]\nputs "NSSOC_FINAL_ANTENNA_NETS $antenna_nets"\nputs "NSSOC_ROUTE_COMPLETE"\n')
  guard=ROOT/'scripts/audit_core_only_route_identity.py';geometry=ROOT/'scripts/audit_native_signal_geometry_indexed.py';prune=ROOT/'hw/soc/flow/prune_orphan_guides.tcl'
  protected.update({str(p):sha(p)for p in [Path(__file__),before,tcl,guard,geometry,prune,audit,ROOT/'scripts/native_geometry_contact_index.py',ROOT/'scripts/buffer_core_only_chip_controls.py']})
  r.update(status='DETAILED_ROUTING',protected_inputs=protected,source_admission=r['source_admission'])
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
  assert r['route_identity']['instances']==added['total_instances']
  assert r['metrics']['route__drc_errors']==0
  assert r['metrics']['antenna__violating__nets']==0 and r['metrics']['antenna__violating__pins']==0
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='ROUTING_ANTENNA_AND_VISIBLE_GEOMETRY_CHECKED_REQUIRES_FRESH_RC_TIMING_AND_SIGNOFF',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
