#!/usr/bin/env python3
"""Buffer overloaded signal nets without deleting any antenna cell; candidate only."""
import os,json,hashlib,subprocess
from pathlib import Path
from cloud_core_only_postgrt import ROOT,completed,archive,sha
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-signal-electrical-eco'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,antenna_protection_requalified=False,final_timing_complete=False)
 try:
  run=completed(44316794375,'96c3430c61fd579f7b19ce3619683d095a1907a3');z,meta=archive(run,'core-only-third-setup-eco-44316794375')
  assert meta['id']==14432817763 and meta['digest']=='sha256:b741e44790b18ef8943e9fc80afbb424131587613956e578120176ea4fbb486d'
  source=json.loads(z.read('result.json'));assert source['sources_unchanged']and source['audit']['upsized_buffers']==4
  for n,h in source['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h
  for path,h in source['protected_inputs'].items():
   prefix='/home/runner/work/nssoc/nssoc/';assert path.startswith(prefix);rel=path[len(prefix):]
   if not rel.startswith('hw/soc/out/'):assert sha(ROOT/rel)==h,rel
  (OUT/'chip-detailedroute.odb').write_bytes(z.read('core-eco-placed-unrouted.odb'));(OUT/'std.lib').write_bytes(z.read('std.lib'))
  assert sha(OUT/'chip-detailedroute.odb')=='31ce8138c79ae6a20ba2f24dcf5a91433a29b2c539ae864571dc221f968fc29f'
  run=completed(44316553449,'42b08594e0a6b8b41477ca96eb51c0407480a407');iz,im=archive(run,'core-only-electrical-load-inventory-44316553449')
  assert im['id']==14433760218 and im['digest']=='sha256:67fb7f0ccf8e6ff015b5e9d54a16217f123c59bff202fcb5175531991b483393'
  ir=json.loads(iz.read('result.json'));assert ir['sources_unchanged']and ir['drivers']==171
  for n,h in ir['outputs'].items():assert hashlib.sha256(iz.read(n)).hexdigest()==h
  for path,h in ir['protected_inputs'].items():
   prefix='/home/runner/work/nssoc/nssoc/';assert path.startswith(prefix);rel=path[len(prefix):]
   if not rel.startswith('hw/soc/out/'):assert sha(ROOT/rel)==h,rel
  (OUT/'load-inventory.json').write_bytes(iz.read('load-inventory.json'))
  prep=ROOT/'scripts/prepare_core_only_signal_electrical_eco.py';audit=ROOT/'scripts/audit_core_only_signal_electrical_eco.py'
  protected={str(p):sha(p)for p in [Path(__file__),prep,audit,ROOT/'scripts/buffer_core_only_chip_controls.py',OUT/'chip-detailedroute.odb',OUT/'std.lib',OUT/'load-inventory.json']}
  r.update(source_artifact=meta,inventory_artifact=im,protected_inputs=protected)
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_PAD_REPAIR_OUT=str(OUT))
  with (OUT/'prepare.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(prep)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  def q(n):return '{'+str(OUT/n)+'}'
  tcl='set_thread_count 4\nread_liberty '+q('std.lib')+'\nread_db '+q('repair-input.odb')+'\ndetailed_placement\ncheck_placement -verbose\nwrite_db '+q('repair-placed.odb')+'\nputs NSSOC_SIGNAL_ELECTRICAL_LEGALIZED\n'
  (OUT/'legalize.tcl').write_text(tcl)
  with (OUT/'legalize.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(OUT/'legalize.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
  assert 'NSSOC_SIGNAL_ELECTRICAL_LEGALIZED'in(OUT/'legalize.log').read_text()
  with (OUT/'audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(audit)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['audit']=json.loads((OUT/'repair-audit.json').read_text());r['selection']=json.loads((OUT/'repair-selection.json').read_text())['excluded_clock_drivers']
  assert all(sha(p)==h for p,h in protected.items());r.update(status='SIGNAL_ELECTRICAL_BUFFER_CANDIDATE_REQUIRES_ROUTING_ANTENNA_RCX_AND_TIMING',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
