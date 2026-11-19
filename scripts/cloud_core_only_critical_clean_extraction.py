#!/usr/bin/env python3
"""Fresh nominal RC on authenticated antenna-clean six-resize route; not signoff."""
import os,json,subprocess,hashlib,io,zipfile
from pathlib import Path
import cloud_core_only_critical_clean_extraction_base as flow
from cloud_core_only_postgrt import api,sha,put
ROOT=flow.ROOT
OUT=ROOT/'hw/soc/out/core-only-critical-clean-extraction'
original_restore=flow.restore_route
STAGES=[
 (44420129432,'3e56fb282941bad19a74019ff73a65d41f058141',14482852777,'6ceddd39ed4711d1735da8e5be09b1ac79b56de71d6c3d7631561aa100a13e80',534,106617,'failure'),
 (44424120322,'9cde7620bcfd8e3c085db0f1e2d52077b45e6a77',14483568401,'2865358b36af3aa027ecf46350838c1cd7d5bebcc52c4c69cbd16292e37916a8',21,106638,'failure'),
 (44427090834,'8a27e631912305e5a184c0268279374283705dc9',14486835187,'d32941fd839e1f0a505d1f0a57de09ea83f12ca5f3958bb7510b83a452bf5993',9,106647,'success')]
def restore_candidate():
 current_run,current_head=flow.RUN,flow.HEAD
 flow.RUN=44392013502;flow.HEAD='bea6ce2b77b37f1d7260008aa35007cef91c7f73'
 try:report,artifacts,initial=original_restore()
 finally:flow.RUN,flow.HEAD=current_run,current_head
 cumulative=dict(report['cumulative_antenna_inventory']);assert len(cumulative)==832
 prior='8f32184f94bd944c39e6a90417462535091164272a145110b7a716523d6a6ee1'
 stages=[]
 for rid,head,aid,digest,count,total,conclusion in STAGES:
  run=api('actions/runs/'+str(rid));assert run['head_sha']==head and run['run_attempt']==1 and run['status']=='completed'and run['conclusion']==conclusion
  meta=api('actions/artifacts/'+str(aid));assert meta['workflow_run']['id']==rid and meta['digest']=='sha256:'+digest
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(raw).hexdigest()==digest
  z=zipfile.ZipFile(io.BytesIO(raw));r=json.loads(z.read('result.json'));assert r['source_head']==head and r['returncode']==0 and not r['accepted']
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
  for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  inv=r['insertion_audit'];ident=r['route_identity'];power=r['added_power_contact']
  assert prior in inv['source_hashes'].values()and inv['new_diodes']==count and inv['total_instances']==total and inv['sources_unchanged']
  assert inv['original_geometry_status_and_connections_preserved']and inv['power_geometry_ports_and_die_preserved']and inv['all_new_terminals_connected']
  assert ident['instances']==total and ident['sources_unchanged']
  for key in ['exact_instance_geometry_status_and_masters','exact_terminal_connections','exact_net_names_and_signal_types','exact_special_wires_ports_and_die']:assert ident[key]
  assert power['checked_power_terminals']==2*count and not power['failures']and power['sources_unchanged']
  assert power['source_odb_sha256']in inv['source_hashes'].values()and power['source_odb_sha256']in ident['source_hashes'].values()
  assert not set(cumulative)&set(inv['new_cells']);cumulative.update(inv['new_cells']);prior=r['routed_odb_sha256']
  artifacts.append(meta);stages.append(dict(run=rid,head=head,artifact=aid,digest=digest,added_diodes=count,odb_sha256=prior))
 assert len(cumulative)==1396 and r['sources_unchanged']
 assert r['status']=='ROUTING_ANTENNA_AND_VISIBLE_GEOMETRY_CHECKED_REQUIRES_FRESH_RC_TIMING_AND_SIGNOFF'
 for k in ['route__drc_errors','antenna__violating__nets','antenna__violating__pins']:assert r['metrics'][k]==0
 g=r['visible_geometry'];assert g['source_unchanged']and not g['signal_nets_with_disconnected_geometry']and not g['unwired_multi_terminal_nets']and not g['terminals_without_geometry']and g['inter_net_contact_pairs']==0
 odb=OUT/'clean-route.odb';put(odb,z.read('soc_top.odb'),'234841fdb17170a7973e3315d2e493e9220c13808a881fa43e262e63a3b02d76')
 assert sha(odb)==prior==g['source_odb_sha256']
 state=json.loads(initial.read_text());sdc=Path(state['sdc']);sdchash=sha(sdc)
 export=OUT/'routed-export.tcl';export.write_text('read_db {'+str(odb)+'}\nwrite_def {'+str(OUT/'routed.def')+'}\nwrite_verilog {'+str(OUT/'routed.v')+'}\nputs NSSOC_CLEAN_EXPORT_COMPLETE\n')
 with (OUT/'routed-export.log').open('w')as log:subprocess.run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(export)],stdout=log,stderr=subprocess.STDOUT,check=True)
 assert 'NSSOC_CLEAN_EXPORT_COMPLETE'in(OUT/'routed-export.log').read_text()
 check=flow.check_added_antennas((OUT/'routed.v').read_text(),cumulative)
 assert check['new_diodes_exported']==1396 and not check['missing_diodes']and not check['duplicate_diodes']and not check['signal_connection_mismatches']
 assert sha(sdc)==sdchash
 state.update(odb=str(odb),nl=str(OUT/'routed.v'));state['def']=str(OUT/'routed.def');state['metrics']={}
 initial.write_text(json.dumps(state,indent=2)+'\n')
 report['fresh_view_binding']=dict(odb_sha256=sha(odb),netlist_sha256=sha(OUT/'routed.v'),def_sha256=sha(OUT/'routed.def'),sdc_sha256=sdchash,export_script_sha256=sha(export))
 report['cumulative_antenna_inventory']=cumulative;report['antenna_netlist_export']=check
 report['added_diode_power_contact'].update(checked_terminals=2792,additional_repair_round_terminals=[1068,42,18],scope='Historical and current additive diode local supply contacts only; not full PDN or resized-cell signoff.')
 (OUT/'clean-route-source.json').write_text(json.dumps(dict(stages=stages,metrics=r['metrics'],route_identity=ident,visible_geometry=g,wrapper_sha256=sha(__file__),production_admissible=False),indent=2)+'\n')
 return report,artifacts,initial
if __name__=='__main__':
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 flow.OUT=OUT;flow.restore_route=restore_candidate;flow.RUN=44427090834;flow.HEAD='8a27e631912305e5a184c0268279374283705dc9'
 flow.main()
