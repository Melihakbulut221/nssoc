#!/usr/bin/env python3
"""Cloud-only native legalizer experiment on measured critical data-path drivers."""
import os,json,hashlib,subprocess,urllib.request
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive
OUT=ROOT/'hw/soc/out/core-only-critical-resize'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING',final_timing_complete=False)
 try:
  rr=completed(44392013502,'bea6ce2b77b37f1d7260008aa35007cef91c7f73');z,m=archive(rr,'core-only-antenna-repair3-44392013502')
  assert m['id']==14470750161 and m['digest']=='sha256:649654de02cb1931abd888d8ffbb038f5cb743e89aa8dfe4a7ee484805fb8415'
  src=json.loads(z.read('result.json'));assert src['sources_unchanged'] and src['returncode']==0
  for k in ['route__drc_errors','antenna__violating__nets','antenna__violating__pins']:assert src['metrics'][k]==0
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h
  odb=z.read('soc_top.odb');assert hashlib.sha256(odb).hexdigest()=='4a618b8c1bad70988890ae099ca8d94c37495bc8fd56a9b6d38c64303b81bbf4';(OUT/'source.odb').write_bytes(odb)
  completed(44396480600,'35697a797feab75754dd73e52505671fd1ddcddb')
  url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
  with urllib.request.urlopen(url,timeout=60)as response:data=response.read()
  assert hashlib.sha256(data).hexdigest()=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4';(OUT/'std.lib').write_bytes(data)
  script=ROOT/'scripts/prepare_core_only_critical_resize.py';app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
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
  r['audit']=json.loads((OUT/'audit.json').read_text());r['plan']=json.loads((OUT/'plan.json').read_text())['resizes'];assert r['audit']['resized_cells']==6
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='SIX_CRITICAL_DRIVER_RESIZES_LEGALIZED_REQUIRES_NEW_ROUTING_RC_AND_ALL_CORNER_TIMING',sources_unchanged=True,protected_inputs=protected,source_artifact=m)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
