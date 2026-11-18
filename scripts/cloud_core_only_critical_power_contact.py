#!/usr/bin/env python3
"""Check the admitted six-resize candidate's native local supply contact."""
import os,json,subprocess,stat
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive,safe_path,put
OUT=ROOT/'hw/soc/out/core-only-critical-power-contact'
MASTERS={n:dict(master='sg13g2_buf_4') for n in ['fanout677','fanout657','fanout644','fanout541','nssoc_sta_i_59322']}
MASTERS['nssoc_sta_i_15034']=dict(master='sg13g2_a21oi_2')
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,manufacturing_approval=False,status='PREPARING')
 try:
  run=completed(44399362987,'dfa8f24652dc77838f127b77980364ee5bf944b6')
  z,meta=archive(run,'core-only-critical-resize-44399362987')
  assert meta['id']==14471483674 and meta['digest']=='sha256:2e58e8e6031aa15fcaa98de675970602b0578d72b62361a175d6fb560f912d9c'
  src=json.loads(z.read('result.json'))
  assert src['source_head']==run['head_sha'] and src['sources_unchanged'] and not src['accepted']
  assert src['status']=='SIX_CRITICAL_DRIVER_RESIZES_LEGALIZED_REQUIRES_NEW_ROUTING_RC_AND_ALL_CORNER_TIMING'
  assert src['audit']['resized_cells']==6 and src['audit']['instances']==106083
  for k in ['exact_terminal_connections','all_other_instances_preserved','net_types_preserved','special_wires_ports_die_preserved','all_antenna_cells_preserved']:assert src['audit'][k]
  base=Path(os.environ['RUNNER_TEMP'])/'critical-power-input';base.mkdir();seen=set()
  for item in z.infolist():
   if item.is_dir() or item.filename=='result.json':continue
   assert not stat.S_ISLNK(item.external_attr>>16) and item.filename not in seen
   put(safe_path(base,item.filename),z.read(item),src['outputs'][item.filename]);seen.add(item.filename)
  assert seen==set(src['outputs'])
  odb=base/'candidate-unrouted.odb'
  assert sha(odb)=='4da67d1ffad55f5cb4aacbcea38b2e7c27124f8a728e79056bd096435b624c60'
  inv=OUT/'inventory.json';inv.write_text(json.dumps(dict(new_cells=MASTERS),indent=2)+'\n')
  check=ROOT/'scripts/audit_critical_power_contact.py'
  protected={str(p):sha(p) for p in [Path(__file__),check,odb,inv]}
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  env=dict(os.environ,ANTENNA_POWER_ODB=str(odb),ANTENNA_POWER_REPORT=str(OUT/'power-contact.json'),ANTENNA_POWER_INVENTORY=str(inv),ANTENNA_POWER_EXPECTED_DIODES='6')
  r.update(source_binding=dict(run=run['id'],head=run['head_sha'],artifact=meta,verified_outputs=len(seen)),protected_inputs=protected)
  with (OUT/'native.log').open('w') as log:
   subprocess.run([str(app),'openroad','-exit','-python',str(check)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  proof=json.loads((OUT/'power-contact.json').read_text())
  assert proof['cells']==6 and proof['checked_power_terminals']==12 and not proof['failures'] and proof['sources_unchanged']
  assert proof['source_odb_sha256']==sha(odb) and proof['native_rail_removal_control']['loss_of_contact_detected']
  assert all(proof['synthetic_controls'].values())
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='SIX_RESIZED_CELLS_LOCAL_SUPPLY_CONTACT_VERIFIED_NOT_FULL_PDN_SIGNOFF',sources_unchanged=True,proof=proof)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
