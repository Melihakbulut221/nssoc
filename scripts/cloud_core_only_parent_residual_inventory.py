#!/usr/bin/env python3
"""Inspect actual parent driver and sink geometry before targeted electrical repair."""
import os,json,hashlib,subprocess
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive
OUT=ROOT/'hw/soc/out/core-only-parent-residual-inventory'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,full_chip_timing=False,cdc_timing_qualified=False,metastability_qualified=False,qualified_rc_minmax=False)
 try:
  run=completed(44350414168,'eb62422fc2451c9ab1488faf7f69692b14cfb913')
  z,m=archive(run,'core-only-parent-perimeter-timing-44350414168')
  assert m['id']==14449570443 and m['digest']=='sha256:c4fff039998704cd8c94a35f5775ee9a6eca9129f82b11a6e15e7b66603f38de'
  source=json.loads(z.read('result.json'));assert source['sources_unchanged']
  for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
  for p,h in source['protected_inputs'].items():
   rel=p.removeprefix('/home/runner/work/nssoc/nssoc/');assert not rel.startswith('/')
   if not rel.startswith('hw/soc/out/'):assert sha(ROOT/rel)==h,p
  ca=source['coverage'];assert ca['parsed_nets']==ca['expected_wired_multiterminal_nets']==2005
  assert not any(ca[k]for k in ['missing_wired_nets','unexpected_spef_nets','terminal_mismatches','resistance_graph_disconnections'])
  libs={'typ':['std.lib','io.lib'],'slow':['sg13g2_stdcell_slow_1p08V_125C.lib','sg13g2_io_slow_1p08V_3p0V_125C.lib'],'fast':['sg13g2_stdcell_fast_1p32V_m40C.lib','sg13g2_io_fast_1p32V_3p6V_m40C.lib']}
  names=['chip-detailedroute.odb','chip-shell.nom.spef','shell-cts.sdc']+[p for ps in libs.values()for p in ps]
  for p in names:(OUT/p).write_bytes(z.read(p))
  assert sha(OUT/'chip-detailedroute.odb')=='889adb811029777356c711b1316f2abab9a59be3eed68c6d44702eee7d0c9e35'
  assert sha(OUT/'chip-shell.nom.spef')=='8169476ef5a641d3f84ca64f2db1b20a898a6e348270d7a46803813036dc78d6'
  assert sha(OUT/'shell-cts.sdc')=='d28e30613e4e2cc9da6f4303c2e49c361fcbc46b60a6389bbf36f6d100200736'
  (OUT/'slow-violations.rpt').write_bytes(z.read('slow/violations.rpt'))
  script=ROOT/'scripts/inspect_core_only_parent_residual.py'
  protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'slow-violations.rpt',*[OUT/n for n in names]]}
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  with (OUT/'inventory.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_PARENT_CDC_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
  inv=json.loads((OUT/'electrical-inventory.json').read_text())
  assert inv['source_unchanged'] and inv['instance_count']==2031 and inv['violation_count']==50
  assert inv['known_buffer_nets']==['net128']
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='NATIVE_PARENT_ELECTRICAL_GEOMETRY_INVENTORIED_REQUIRES_REPAIR_AND_SIGNOFF',source_artifacts=[m],protected_inputs=protected,inventory=inv,sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+chr(10))
if __name__=='__main__':main()
