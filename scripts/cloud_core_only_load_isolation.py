#!/usr/bin/env python3
"""Cloud-only native legalizer experiment on measured critical data-path drivers."""
import os,json,hashlib,subprocess,urllib.request
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive
OUT=ROOT/'hw/soc/out/core-only-load-isolation'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING',final_timing_complete=False)
 try:
  from cloud_core_only_postgrt import api
  rr=api('actions/runs/44420129432');assert rr['status']=='completed'and rr['conclusion']=='failure'and rr['run_attempt']==1 and rr['head_sha']=='3e56fb282941bad19a74019ff73a65d41f058141'
  z,m=archive(rr,'core-only-critical-antenna-repair-44420129432');assert m['id']==14482852777 and m['digest']=='sha256:6ceddd39ed4711d1735da8e5be09b1ac79b56de71d6c3d7631561aa100a13e80'
  src=json.loads(z.read('result.json'));assert src['source_head']==rr['head_sha']and src['returncode']==0 and src['route_identity']['instances']==106617
  assert src['metrics']['route__drc_errors']==0 and src['metrics']['antenna__violating__nets']==15
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h
  odb=z.read('soc_top.odb');assert hashlib.sha256(odb).hexdigest()=='0bccd439a9efe8b7463ae5d32f1ae42616c49872548bf6aabaaa35e3eb721eb5';(OUT/'source.odb').write_bytes(odb)
  completed(44424914697,'d3530f50f723406ffa59eef5833a50f76289b3b0')
  url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
  with urllib.request.urlopen(url,timeout=60)as response:data=response.read()
  assert hashlib.sha256(data).hexdigest()=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4';(OUT/'std.lib').write_bytes(data)
  script=ROOT/'scripts/prepare_core_only_load_isolation.py';app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  protected={str(p):sha(p)for p in [Path(__file__),script,ROOT/'scripts/buffer_core_only_chip_controls.py',OUT/'source.odb',OUT/'std.lib']}
  env=dict(os.environ,NSSOC_CRITICAL_ECO_OUT=str(OUT),NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_CRITICAL_ECO_MODE='prepare')
  with (OUT/'prepare.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  def q(n):return '{'+str(OUT/n)+'}'
  tcl='set_thread_count 4\nread_liberty '+q('std.lib')+'\nread_db '+q('before-legalize.odb')+'\ndetailed_placement\ncheck_placement -verbose\nwrite_db '+q('legalized.odb')+'\nputs NSSOC_CRITICAL_LEGALIZED\n'
  (OUT/'legalize.tcl').write_text(tcl)
  with (OUT/'legalize.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(OUT/'legalize.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
  assert 'NSSOC_CRITICAL_LEGALIZED'in (OUT/'legalize.log').read_text()
  env['NSSOC_CRITICAL_ECO_MODE']='audit'
  with (OUT/'audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['audit']=json.loads((OUT/'audit.json').read_text());r['plan']=json.loads((OUT/'plan.json').read_text())['new_cells'];assert r['audit']['new_buffers']==2
  power=ROOT/'scripts/audit_load_isolation_power.py';protected[str(power)]=sha(power)
  env=dict(os.environ,ANTENNA_POWER_ODB=str(OUT/'candidate-unrouted.odb'),ANTENNA_POWER_REPORT=str(OUT/'power-contact.json'),ANTENNA_POWER_INVENTORY=str(OUT/'plan.json'),ANTENNA_POWER_EXPECTED_DIODES='2')
  with (OUT/'power-contact.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(power)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['power_contact']=json.loads((OUT/'power-contact.json').read_text());assert r['power_contact']['checked_power_terminals']==4 and not r['power_contact']['failures']
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='TWO_LOAD_ISOLATION_BUFFERS_LEGALIZED_REQUIRES_ROUTING_RC_TIMING',sources_unchanged=True,protected_inputs=protected,source_artifact=m)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
