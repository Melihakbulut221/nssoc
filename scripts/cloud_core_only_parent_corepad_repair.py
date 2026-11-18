#!/usr/bin/env python3
"""Place audited buffer chains around the core for four measured long parent wires."""
import os,json,hashlib,subprocess,time
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive as fetch_archive
OUT=ROOT/'hw/soc/out/core-only-parent-corepad-repair'
def archive(run,name):
 for attempt in range(3):
  try:return fetch_archive(run,name)
  except subprocess.CalledProcessError:
   if attempt==2:raise
   time.sleep(5*(attempt+1))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,full_chip_timing=False,cdc_timing_qualified=False,metastability_qualified=False,qualified_rc_minmax=False)
 try:
  run=completed(44355961230,'07fb3635e7e2fc98691d5a8056707a2cf153a81d')
  z,m=archive(run,'core-only-parent-crossing-timing-44355961230')
  assert m['id']==14452736425 and m['digest']=='sha256:85672c97a9d40da712b4fa0bc750f3e80d2d41f470d8099c239c1df2f58058d0'
  source=json.loads(z.read('result.json'));assert source['sources_unchanged']
  for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
  for p,h in source['protected_inputs'].items():
   rel=p.removeprefix('/home/runner/work/nssoc/nssoc/');assert not rel.startswith('/')
   if not rel.startswith('hw/soc/out/'):assert sha(ROOT/rel)==h,p
  ca=source['coverage'];assert ca['parsed_nets']==ca['expected_wired_multiterminal_nets']==2019
  assert not any(ca[k]for k in ['missing_wired_nets','unexpected_spef_nets','terminal_mismatches','resistance_graph_disconnections'])
  libs={'typ':['std.lib','io.lib'],'slow':['sg13g2_stdcell_slow_1p08V_125C.lib','sg13g2_io_slow_1p08V_3p0V_125C.lib'],'fast':['sg13g2_stdcell_fast_1p32V_m40C.lib','sg13g2_io_fast_1p32V_3p6V_m40C.lib']}
  names=['chip-detailedroute.odb','chip-shell.nom.spef','shell-cts.sdc']+[p for ps in libs.values()for p in ps]
  for p in names:(OUT/p).write_bytes(z.read(p))
  assert sha(OUT/'chip-detailedroute.odb')=='190b40da1d8f3b94c091cd493d6ce0a607e96f0fdb1b01b0179aba6a42fc0ac1'
  assert sha(OUT/'chip-shell.nom.spef')=='b6bee91a31c4444b16fb9846139632e94ad86f0c815aee5c6afe7d2334cb4734'
  assert sha(OUT/'shell-cts.sdc')=='d28e30613e4e2cc9da6f4303c2e49c361fcbc46b60a6389bbf36f6d100200736'
  (OUT/'slow-violations.rpt').write_bytes(z.read('slow/violations.rpt'))
  ir=completed(44357611874,'4b2996acaeee744fc8b31544a10448ad42a05c4c')
  iz,im=archive(ir,'core-only-parent-output-inventory-44357611874')
  assert im['id']==14453627328 and im['digest']=='sha256:9ffea7f1cb2fae40bc9f85d141a19ab1f78c81ee6c00bb01d2f6829f8344635f'
  iv=json.loads(iz.read('result.json'));assert iv['sources_unchanged']
  for p,h in iv['outputs'].items():assert hashlib.sha256(iz.read(p)).hexdigest()==h
  (OUT/'electrical-inventory.json').write_bytes(iz.read('electrical-inventory.json'))
  assert iv['inventory']['source_odb_sha256']==sha(OUT/'chip-detailedroute.odb')
  scripts=[ROOT/'scripts/prepare_core_only_parent_corepad.py',ROOT/'scripts/audit_core_only_pad_repair.py',ROOT/'scripts/audit_core_only_parent_corepad.py']
  protected={str(p):sha(p)for p in [Path(__file__),*scripts,ROOT/'scripts/buffer_core_only_chip_controls.py',*[p for p in OUT.iterdir()if p.is_file()]]}
  r.update(protected_inputs=protected,source_artifacts=[m,im])
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  env=dict(os.environ,NSSOC_PAD_REPAIR_OUT=str(OUT),NSSOC_CONTROL_BUFFER_OUT=str(OUT))
  def native(script,log):
   with (OUT/log).open('w')as f:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
  native(scripts[0],'prepare.log')
  def q(n):return '{'+str(OUT/n)+'}'
  tcl='set_thread_count 4'+chr(10)+'read_liberty '+q('std.lib')+chr(10)+'read_liberty '+q('io.lib')+chr(10)+'read_db '+q('repair-input.odb')+chr(10)
  tcl+='detailed_placement'+chr(10)+'check_placement -verbose'+chr(10)+'write_db '+q('repair-placed.odb')+chr(10)+'write_verilog '+q('repair-placed.v')+chr(10)
  (OUT/'legalize.tcl').write_text(tcl);protected[str(OUT/'legalize.tcl')]=sha(OUT/'legalize.tcl')
  with (OUT/'legalize.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(OUT/'legalize.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
  native(scripts[1],'connectivity-audit.log')
  native(scripts[2],'perimeter-audit.log')
  r['audit']=json.loads((OUT/'repair-audit.json').read_text())
  r['placement_audit']=json.loads((OUT/'perimeter-placement-audit.json').read_text())
  r['selection']=json.loads((OUT/'repair-selection.json').read_text())
  assert r['audit']['new_buffers']==r['placement_audit']['new_buffers']==len(r['selection']['planned_buffers'])
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='PERIMETER_BUFFER_CANDIDATE_LEGALIZED_AND_CONNECTIVITY_VERIFIED_REQUIRES_ROUTING_AND_TIMING',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+chr(10))
if __name__=='__main__':main()
