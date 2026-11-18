#!/usr/bin/env python3
"""Cloud candidate only: measured setup buffer sizing and isolated SRAM hold delay."""
import os,json,hashlib,subprocess,urllib.request
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,archive,api,current_path,restore_mapping,restore_cts,qualify_sources
from cloud_core_only_clock_probe import restore_cts8
from cloud_core_only_clock_refine import restore_clock_split,restore_previous
from cloud_core_only_detailed_route import restore_refinement
from cloud_core_only_routed_extraction import restore_route
OUT=ROOT/'hw/soc/out/core-only-residual-electrical-eco'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,timing_accepted=False)
 try:
  qualify_sources()
  run=api('actions/runs/44321041305');assert run['head_sha']=='60b3f906b2128a1658e73b57a2acb20c051f5789'and run['status']=='completed'and run['conclusion']=='success'
  z,m=archive(run,'core-only-fourth-setup-eco-44321041305');assert m['id']==14435511020 and m['digest']=='sha256:84e412b4255aa6051dfb2ff4991d0d07e41d4933692dcca9bd77c6d67e859f4b'
  result=json.loads(z.read('result.json'));assert result['sources_unchanged']and result['audit']['upsized_buffers']==8 and result['audit']['all_original_terminals_preserved']
  assert result['source_globalroute_head']=='64c31ae9192137edf449245cf59ba3bbb0c8469b'
  for p,h in result['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
  for p,h in result['protected_inputs'].items():
   prefix='/home/runner/work/nssoc/nssoc/';assert p.startswith(prefix);relative=p[len(prefix):]
   if not relative.startswith('hw/soc/out/'):assert sha(ROOT/relative)==h,relative
  (OUT/'core-routed.odb').write_bytes(z.read('core-eco-placed-unrouted.odb'))
  assert sha(OUT/'core-routed.odb')=='4154f31a6b96a6e746bf9e373848c010e24dcb22a4581784379a92193e2641d6'
  r.update(source_setup_head=run['head_sha'],baseline_estimated_corners=result['baseline_estimated_corners'])
  url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
  with urllib.request.urlopen(url,timeout=60)as response:data=response.read()
  assert hashlib.sha256(data).hexdigest()=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4';(OUT/'std.lib').write_bytes(data)
  prep=ROOT/'scripts/prepare_core_only_residual_electrical_eco.py';audit=ROOT/'scripts/audit_core_only_residual_electrical_eco.py'
  protected={str(p):sha(p)for p in [Path(__file__),prep,audit,ROOT/'scripts/buffer_core_only_chip_controls.py',*[p for p in OUT.iterdir()if p.is_file()]]}
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');env=dict(os.environ,NSSOC_CORE_TARGETED_ECO_OUT=str(OUT),NSSOC_CONTROL_BUFFER_OUT=str(OUT))
  with (OUT/'prepare.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(prep)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  p=json.loads((OUT/'eco-plan.json').read_text());r['selection']={k:v for k,v in p.items()if k!='original_statuses'}
  def q(n):return '{'+str(OUT/n)+'}'
  tcl='set_thread_count 4\nread_liberty '+q('std.lib')+'\nread_db '+q('eco-before-legalize.odb')+'\ndetailed_placement\ncheck_placement -verbose\nwrite_db '+q('eco-legalized.odb')+'\nputs NSSOC_CORE_TARGETED_LEGALIZED\n'
  (OUT/'legalize.tcl').write_text(tcl)
  with (OUT/'legalize.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(OUT/'legalize.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
  assert 'NSSOC_CORE_TARGETED_LEGALIZED'in(OUT/'legalize.log').read_text()
  with (OUT/'audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(audit)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['audit']=json.loads((OUT/'eco-audit.json').read_text());assert all(sha(p)==h for p,h in protected.items())
  r.update(status='TARGETED_BUFFER_ECO_LEGALIZED_AND_FUNCTIONALLY_CONTRACTED_REQUIRES_FRESH_ROUTING_TIMING',sources_unchanged=True,protected_inputs=protected,source_artifact=m)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
