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
OUT=ROOT/'hw/soc/out/core-only-canonical-targeted-eco'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,timing_accepted=False)
 try:
  qualify_sources()
  run=api('actions/runs/44308129454');assert run['head_sha']=='78432b99eb354dcb2a7a2d3266ecbb445a31c9cc'and run['status']=='completed'and run['conclusion']=='success'
  z,m=archive(run,'core-only-canonical-extracted-timing-native-44308129454');assert m['id']==14429028836 and m['digest']=='sha256:de85c0ced40577188dcb7af6786736f4f6159025fc41ae9bcdbbd6ec8e57168a'
  zz,sm=archive(run,'core-only-canonical-extracted-timing-summary-44308129454');assert sm['id']==14428669560 and sm['digest']=='sha256:036458784784f5f8e044fef2499f4556c346ff75316df930fc1737e07fff25cf'
  assert z.read('result.json')==zz.read('result.json');result=json.loads(z.read('result.json'));assert result['returncode']==0 and result['sources_unchanged']
  assert result['canonicalization']['all_original_geometry_and_connectivity_preserved']and result['canonicalization']['binary_readback_verified']
  for p,h in result['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
  for corner,entry in result['annotation_classification'].items():
   assert entry['partially_unannotated_drivers']==0 and entry['loaded_unannotated_drivers']==0 and entry['native_missing_loads']==0
  (OUT/'core-routed.odb').write_bytes(z.read('canonical.odb'))
  (OUT/'canonical-name-map.json').write_bytes(z.read('canonical-name-map.json'))
  for corner,name,target in [('nom_slow_1p08V_125C','max.rpt','slow-max.rpt'),('nom_fast_1p32V_m40C','min.rpt','fast-min.rpt')]:
   (OUT/target).write_bytes(z.read('extraction/2-nssoc-coreonlyextractedsta/'+corner+'/'+name))
  r.update(canonical_source_head=run['head_sha'],canonical_artifact=m,canonical_summary=sm,original_names_preserved_in_map=True)
  url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
  with urllib.request.urlopen(url,timeout=60)as response:data=response.read()
  assert hashlib.sha256(data).hexdigest()=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4';(OUT/'std.lib').write_bytes(data)
  prep=ROOT/'scripts/prepare_core_only_targeted_eco.py';audit=ROOT/'scripts/audit_core_only_targeted_eco.py'
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
