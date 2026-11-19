#!/usr/bin/env python3
"""Selected-net routing experiment; every unaffected DEF net must be preserved."""
import os,json,hashlib,subprocess
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive,put
OUT=ROOT/'hw/soc/out/core-only-sram-clock-selected-route'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,status='PREPARING')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 try:
  run=completed(44432691473,'e5536575eb03f3c6ab4bc61b045d243a265fb55e');assert run['run_attempt']==1
  z,m=archive(run,'core-only-sram-clock-resize-44432691473');assert m['id']==14487078971 and m['digest']=='sha256:174162f2f8c55679aece9a67de73803fb32b45bd57c0e501b7d166eac6960ac0'
  src=json.loads(z.read('result.json'));assert src['source_head']==run['head_sha']and src['sources_unchanged']
  assert src['status']=='ONE_SRAM_CLOCK_DRIVER_RESIZED_OTHER_ROUTES_PRESERVED_REQUIRES_ROUTING_RC_ALL_CORNERS'
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(src['outputs'])
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  assert src['preserved_routes']['checked_net_records']==103083 and src['preserved_routes']['all_other_routes_preserved']
  assert src['audit']['instances']==106647 and src['audit']['resized_cells']==1
  for key in ['exact_terminal_connections','all_other_instances_preserved','net_types_preserved','special_wires_ports_die_preserved','all_antenna_cells_preserved']:assert src['audit'][key]
  assert src['power_contact']['checked_power_terminals']==2 and not src['power_contact']['failures']
  original=OUT/'candidate-partially-routed.odb';put(original,z.read('candidate-partially-routed.odb'),'a9e48d0c9f53e2ec3ac03fa35913b209bc0008717cf7b754b42c5b613734aab4')
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  guard=ROOT/'scripts/audit_core_only_route_identity.py';routeguard=ROOT/'scripts/audit_core_only_clock_route_preservation.py';geometry=ROOT/'scripts/audit_native_signal_geometry_indexed.py'
  protected={str(p):sha(p)for p in [Path(__file__),original,guard,routeguard,geometry,ROOT/'scripts/buffer_core_only_chip_controls.py',ROOT/'scripts/native_geometry_contact_index.py']}
  def execute(tcl,name,metrics=False):
   script=OUT/(name+'.tcl');script.write_text(tcl);protected[str(script)]=sha(script)
   cmd=[str(app),'openroad','-exit']
   if metrics:cmd+=['-metrics',str(OUT/(name+'-metrics.json'))]
   with (OUT/(name+'.log')).open('w')as log:subprocess.run(cmd+[str(script)],stdout=log,stderr=subprocess.STDOUT,check=True)
  def audit(after,name):
   folder=OUT/(name+'-identity');folder.mkdir()
   env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_ROUTE_IDENTITY_BEFORE=str(original),NSSOC_ROUTE_IDENTITY_AFTER=str(after),NSSOC_ROUTE_IDENTITY_OUT=str(folder),NSSOC_PRESERVED_ROUTE_AUDIT=str(OUT/(name+'-preservation')))
   for label,script in [('identity',guard),('preservation',routeguard)]:
    with (OUT/(name+'-'+label+'.log')).open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
   r[name+'_identity']=json.loads((folder/'route-identity.json').read_text());r[name+'_preservation']=json.loads((OUT/(name+'-preservation')/'result.json').read_text());save()
  selected=OUT/'selected-global.odb'
  r.update(status='SELECTED_GLOBAL_ROUTING',source_artifact=m,source_audit=src['audit']);save()
  execute('read_db {'+str(original)+'}\nset_thread_count 4\nset_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nset_global_routing_layer_adjustment Metal2-TopMetal2 0.2\nset_nets_to_route {delaynet_17_clk_i clknet_1_0_0_clk_i}\nglobal_route -verbose\nwrite_db {'+str(selected)+'}\n','global')
  audit(selected,'global')
  after=OUT/'soc_top.odb';r['status']='DETAILED_ROUTING';save()
  execute('read_db {'+str(selected)+'}\nset_thread_count 4\nset_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nsource {'+str(ROOT/'hw/soc/flow/prune_orphan_guides.tcl')+'}\nputs "REMOVED_ORPHAN_GUIDES [prune_orphan_guides [ord::get_db_block]]"\ndetailed_route -droute_end_iter 64 -or_seed 42 -verbose 1 -output_drc {'+str(OUT/'soc_top.drc')+'}\nwrite_db {'+str(after)+'}\ncheck_antennas -report_file {'+str(OUT/'antenna.rpt')+'}\n','route',True)
  r['metrics']=json.loads((OUT/'route-metrics.json').read_text());r['routed_odb_sha256']=sha(after);save()
  audit(after,'detailed')
  geom=OUT/'geometry';geom.mkdir();env=dict(os.environ,NSSOC_PHYSICAL_ROUTE_OUT=str(geom),NSSOC_PHYSICAL_ROUTE_ODB=str(after))
  with (OUT/'geometry.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(geometry)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['visible_geometry']=json.loads((geom/'physical-route-audit.json').read_text())
  assert r['metrics']['route__drc_errors']==0
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='SELECTED_ROUTE_MEASURED_REQUIRES_ANTENNA_CLOSURE_AND_FRESH_RC',sources_unchanged=True,protected_inputs=protected)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
