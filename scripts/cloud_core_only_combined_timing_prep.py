#!/usr/bin/env python3
"""Cloud-only native legalizer experiment on measured critical data-path drivers."""
import os,json,hashlib,subprocess,urllib.request
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive
OUT=ROOT/'hw/soc/out/core-only-combined-timing-prep'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING',final_timing_complete=False)
 try:
  rr=completed(44442857432,'25a15d4dc0908a74c0be310f123d660b1d459682');assert rr['run_attempt']==1
  z,m=archive(rr,'core-only-sram-clock-antenna-route-44442857432');assert m['id']==14492198043 and m['digest']=='sha256:0a0e746a9a6ce9647871b45e03c7582fa1602cf92f8f348e7094b3c3c3bceeef'
  src=json.loads(z.read('result.json'));assert src['source_head']==rr['head_sha']and src['sources_unchanged']and not src['accepted']
  assert src['status']=='CLOCK_ANTENNA_ROUTE_GEOMETRY_CLEAN_REQUIRES_FRESH_RC_AND_SIGNOFF'
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(src['outputs'])
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  for key in ['route__drc_errors','antenna__violating__nets','antenna__violating__pins']:assert src['metrics'][key]==0
  ident=src['detailed_identity'];assert ident['instances']==106648 and ident['sources_unchanged']
  for key in ['exact_instance_geometry_status_and_masters','exact_terminal_connections','exact_net_names_and_signal_types','exact_special_wires_ports_and_die']:assert ident[key]
  for key in ['insertion_preservation','detailed_preservation']:
   p=src[key];assert p['checked_unchanged_nets']==103082 and p['checked_clock_nets']==2112 and not p['changed_unselected_nets']and not p['changed_clock_nets']
  g=src['visible_geometry'];assert g['source_unchanged']and not g['signal_nets_with_disconnected_geometry']and not g['unwired_multi_terminal_nets']and not g['terminals_without_geometry']and g['inter_net_contact_pairs']==0
  odb=z.read('restored-status.odb');digest=hashlib.sha256(odb).hexdigest();assert digest==src['routed_odb_sha256']==g['source_odb_sha256']=='42710e6fade6cbcf116bf9f0d606312fa6224293034c0b3a96b629404396c0d8';(OUT/'source.odb').write_bytes(odb)
  r['source_admission']=dict(run=rr['id'],head=rr['head_sha'],artifact=m,odb_sha256=digest,metrics=src['metrics'],identity=ident,geometry=g)
  url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
  with urllib.request.urlopen(url,timeout=60)as response:data=response.read()
  assert hashlib.sha256(data).hexdigest()=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4';(OUT/'std.lib').write_bytes(data)
  script=ROOT/'scripts/prepare_core_only_combined_timing.py';app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
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
  r['preserved_routes']=json.loads((OUT/'preserved-route-audit.json').read_text())
  r['audit']=json.loads((OUT/'audit.json').read_text());r['plan']=json.loads((OUT/'plan.json').read_text())['new_cells'];assert r['audit']['new_buffers']==2 and r['audit']['instances']==106650
  power=ROOT/'scripts/audit_load_isolation_power.py';protected[str(power)]=sha(power)
  env=dict(os.environ,ANTENNA_POWER_ODB=str(OUT/'candidate-partially-routed.odb'),ANTENNA_POWER_REPORT=str(OUT/'power-contact.json'),ANTENNA_POWER_INVENTORY=str(OUT/'plan.json'),ANTENNA_POWER_EXPECTED_DIODES='2')
  with (OUT/'power-contact.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(power)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['power_contact']=json.loads((OUT/'power-contact.json').read_text());assert r['power_contact']['checked_power_terminals']==4 and not r['power_contact']['failures']
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='COMBINED_CLOCK_AND_DATA_ECO_PREPARED_REQUIRES_ROUTING_ANTENNA_AND_FRESH_RC',sources_unchanged=True,protected_inputs=protected,source_artifact=m)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
