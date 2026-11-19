#!/usr/bin/env python3
"""Prepare additive diode repair on the preserved SRAM clock route."""
import os,json,hashlib,subprocess
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive,put
OUT=ROOT/'hw/soc/out/core-only-sram-clock-antenna-prep'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,status='PREPARING')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 try:
  run=completed(44438114279,'2f0e5e8b1fa7352b93ae19796fd741a4ef1f52f6');assert run['run_attempt']==1
  z,m=archive(run,'core-only-sram-clock-fixed-route-44438114279')
  assert m['id']==14490194336 and m['digest']=='sha256:eaa8647f9269c317488cc1fb488ae12402d9ea637dcb5a040dea27779298903a'
  src=json.loads(z.read('result.json'));assert src['sources_unchanged']and src['source_head']==run['head_sha']and not src['accepted']
  assert src['status']=='SELECTED_ROUTE_MEASURED_REQUIRES_ANTENNA_CLOSURE_AND_FRESH_RC'
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(src['outputs'])
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  assert src['metrics']['route__drc_errors']==0 and src['metrics']['antenna__violating__nets']==1 and src['metrics']['antenna__violating__pins']==1
  ident=src['detailed_identity'];assert ident['instances']==106647 and ident['sources_unchanged']
  for key in ['exact_instance_geometry_status_and_masters','exact_terminal_connections','exact_net_names_and_signal_types','exact_special_wires_ports_and_die']:assert ident[key]
  p=src['detailed_preservation'];assert p['checked_unchanged_nets']==103081 and p['checked_clock_nets']==2111 and not p['changed_unselected_nets']and not p['changed_clock_nets']
  g=src['visible_geometry'];assert g['source_unchanged']and not g['signal_nets_with_disconnected_geometry']and not g['unwired_multi_terminal_nets']and not g['terminals_without_geometry']and g['inter_net_contact_pairs']==0
  original=OUT/'source.odb';put(original,z.read('restored-status.odb'),'a2d85760fec57ea28ea10a192c27528326b9fb48aa5c4a682367c08fdacca9ba')
  assert sha(original)==src['routed_odb_sha256']==g['source_odb_sha256']
  r['source_admission']=dict(run=run['id'],head=run['head_sha'],artifact=m,metrics=src['metrics'],source_odb_sha256=sha(original))
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  before=OUT/'diodes-inserted.odb';insert=OUT/'insert.tcl';audit=ROOT/'scripts/audit_core_only_antenna_insertion.py';power=ROOT/'scripts/audit_critical_antenna_power_contact.py'
  insert.write_text('read_db $::env(NSSOC_REPAIR_INPUT)\nset_thread_count 4\nset_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nset_global_routing_layer_adjustment Metal2-TopMetal2 0.2\nputs "NSSOC_INSERTED_DIODES [repair_antennas sg13g2_antennanp -iterations 1 -ratio_margin 10 -diode_only]"\nglobal_connect\ncheck_placement -verbose\nwrite_db $::env(NSSOC_REPAIR_OUTPUT)\nputs NSSOC_INSERTION_COMPLETE\n')
  protected={str(p):sha(p)for p in [Path(__file__),original,insert,audit,power,ROOT/'scripts/audit_core_only_route_identity.py',ROOT/'scripts/buffer_core_only_chip_controls.py']}
  r.update(status='INSERTING_ADDITIONAL_DIODES',protected_inputs=protected,antenna_repair_ratio_margin_percent=10);save()
  env=dict(os.environ,NSSOC_REPAIR_INPUT=str(original),NSSOC_REPAIR_OUTPUT=str(before))
  with (OUT/'insertion.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(insert)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  assert before.is_file()and 'NSSOC_INSERTION_COMPLETE'in(OUT/'insertion.log').read_text()
  inv=OUT/'insertion-audit.json';env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_ROUTE_IDENTITY_BEFORE=str(original),NSSOC_ROUTE_IDENTITY_AFTER=str(before),NSSOC_ANTENNA_AUDIT_OUT=str(inv))
  with (OUT/'insertion-audit.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(audit)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  added=json.loads(inv.read_text());assert added['original_instances']==106647 and added['new_diodes']>0 and added['sources_unchanged'];r['insertion_audit']=added;save()
  env=dict(os.environ,ANTENNA_POWER_ODB=str(before),ANTENNA_POWER_REPORT=str(OUT/'power-contact.json'),ANTENNA_POWER_INVENTORY=str(inv),ANTENNA_POWER_EXPECTED_DIODES=str(added['new_diodes']))
  with (OUT/'power-contact.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(power)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['added_power_contact']=json.loads((OUT/'power-contact.json').read_text());protected[str(inv)]=sha(inv)
  assert all(c['signal_terms'][0]['net']=='clknet_1_0_0_clk_i'for c in added['new_cells'].values()),'Unexpected diode net'
  routeguard=ROOT/'scripts/audit_core_only_clock_route_preservation.py';protected[str(routeguard)]=sha(routeguard)
  env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_ROUTE_IDENTITY_BEFORE=str(original),NSSOC_ROUTE_IDENTITY_AFTER=str(before),NSSOC_PRESERVED_ROUTE_AUDIT=str(OUT/'preservation'))
  with (OUT/'preservation.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(routeguard)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['preserved_routes']=json.loads((OUT/'preservation/result.json').read_text())
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='CLOCK_ANTENNA_DIODES_ADDED_OTHER_ROUTES_PRESERVED_REQUIRES_ROUTING_AND_FRESH_RC',sources_unchanged=True,protected_inputs=protected,output_odb='diodes-inserted.odb',candidate_odb_sha256=sha(before))
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
