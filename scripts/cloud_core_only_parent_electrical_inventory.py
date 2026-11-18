#!/usr/bin/env python3
"""Inspect actual parent driver and sink geometry before targeted electrical repair."""
import os,json,hashlib,subprocess
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive
OUT=ROOT/'hw/soc/out/core-only-parent-electrical-inventory'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,full_chip_timing=False,cdc_timing_qualified=False,metastability_qualified=False,qualified_rc_minmax=False)
 try:
  run=completed(44314493056,'4ef92164139e6bcdea2310487f2f02b242064d9b')
  z,m=archive(run,'core-only-chip-gpio-repaired-timing-native-44314493056')
  assert m['id']==14431513763 and m['digest']=='sha256:a97e5bc8f94389c3dfc4a83206f3f09b773029ab3800150cbfa1ef5f11774bf7'
  sz,sm=archive(run,'core-only-chip-gpio-repaired-timing-summary-44314493056')
  assert sm['id']==14431858560 and sm['digest']=='sha256:8b70ee125031bea964988260f342c871f37c24e60a5c7fbebdc5e57b59ce8eb9'
  assert z.read('result.json')==sz.read('result.json');source=json.loads(z.read('result.json'));assert source['sources_unchanged']
  for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
  for p,h in source['protected_inputs'].items():
   rel=p.removeprefix('/home/runner/work/nssoc/nssoc/');assert not rel.startswith('/')
   if not rel.startswith('hw/soc/out/'):assert sha(ROOT/rel)==h,p
  ca=source['coverage'];assert ca['parsed_nets']==ca['expected_wired_multiterminal_nets']==1949
  assert not any(ca[k]for k in ['missing_wired_nets','unexpected_spef_nets','terminal_mismatches','resistance_graph_disconnections'])
  libs={'typ':['std.lib','io.lib'],'slow':['sg13g2_stdcell_slow_1p08V_125C.lib','sg13g2_io_slow_1p08V_3p0V_125C.lib'],'fast':['sg13g2_stdcell_fast_1p32V_m40C.lib','sg13g2_io_fast_1p32V_3p6V_m40C.lib']}
  names=['chip-detailedroute.odb','chip-shell.nom.spef','shell-cts.sdc']+[p for ps in libs.values()for p in ps]
  for p in names:(OUT/p).write_bytes(z.read(p))
  assert sha(OUT/'chip-detailedroute.odb')=='29d6d93b168ef0d33aa06235d8d8578dc30b979ac026d8c4af6a3e811e3821a5'
  assert sha(OUT/'chip-shell.nom.spef')=='90a663aef4bac35f5552d01e6dd6d22f8de21452cabc38539c18edaa73fe32a7'
  assert sha(OUT/'shell-cts.sdc')=='d28e30613e4e2cc9da6f4303c2e49c361fcbc46b60a6389bbf36f6d100200736'
  (OUT/'slow-violations.rpt').write_bytes(z.read('slow/violations.rpt'))
  script=ROOT/'scripts/inspect_core_only_parent_electrical.py'
  protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'slow-violations.rpt',*[OUT/n for n in names]]}
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  with (OUT/'inventory.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_PARENT_CDC_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
  inv=json.loads((OUT/'electrical-inventory.json').read_text())
  assert inv['source_unchanged'] and inv['instance_count']==1975 and inv['violation_count']==53
  assert inv['known_buffer_nets']==['net73','net78','net83','net89']
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='NATIVE_PARENT_ELECTRICAL_GEOMETRY_INVENTORIED_REQUIRES_REPAIR_AND_SIGNOFF',source_artifacts=[m,sm],protected_inputs=protected,inventory=inv,sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+chr(10))
if __name__=='__main__':main()
