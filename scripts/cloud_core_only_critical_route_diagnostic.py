#!/usr/bin/env python3
"""Diagnostic fresh RC/STA on an antenna-rejected resized candidate. Never signoff."""
import os,json,subprocess,hashlib,io,zipfile
from pathlib import Path
import cloud_core_only_antenna_extraction as flow
from cloud_core_only_postgrt import api,sha,put
ROOT=flow.ROOT
OUT=ROOT/'hw/soc/out/core-only-critical-route-diagnostic'
original_restore=flow.restore_route

def restore_candidate():
 current_run,current_head=flow.RUN,flow.HEAD
 flow.RUN=44392013502;flow.HEAD='bea6ce2b77b37f1d7260008aa35007cef91c7f73'
 try:report,artifacts,initial=original_restore()
 finally:flow.RUN,flow.HEAD=current_run,current_head
 run=api('actions/runs/44402072903')
 assert run['head_sha']=='75131e1401c85e6cdc12d05819f401856162a93c'and run['run_attempt']==1 and run['status']=='completed'and run['conclusion']=='failure'
 aid=14481780456;digest='3abb2224c073efa979a43238b0d3aa8782549a174d4ef6c7606ced1d086460ce'
 meta=api('actions/artifacts/'+str(aid));assert meta['workflow_run']['id']==run['id']and meta['digest']=='sha256:'+digest
 raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(raw).hexdigest()==digest
 z=zipfile.ZipFile(io.BytesIO(raw));r=json.loads(z.read('result.json'))
 assert r['source_head']==run['head_sha']and r['returncode']==0 and not r['accepted']and r['status']=='FAIL_OR_INCOMPLETE'
 assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h
 assert r['metrics']['route__drc_errors']==0 and r['metrics']['antenna__violating__nets']==234 and r['metrics']['antenna__violating__pins']==265
 ident=r['route_identity'];assert ident['instances']==106083 and ident['sources_unchanged']
 for k in ['exact_instance_geometry_status_and_masters','exact_terminal_connections','exact_net_names_and_signal_types','exact_special_wires_ports_and_die']:assert ident[k]
 g=r['visible_geometry'];assert g['source_unchanged']and not g['signal_nets_with_disconnected_geometry']and not g['unwired_multi_terminal_nets']and not g['terminals_without_geometry']and g['inter_net_contact_pairs']==0
 assert r['source_admission']['run']==44400094526 and r['source_admission']['head']=='6df2ae68122fa3ae95a7fa43ced91cf51c35667e'
 assert r['source_admission']['eco_audit']['resized_cells']==6
 odb=OUT/'diagnostic.odb';put(odb,z.read('soc_top.odb'),'8f32184f94bd944c39e6a90417462535091164272a145110b7a716523d6a6ee1')
 state=json.loads(initial.read_text());sdc=Path(state['sdc']);sdchash=sha(sdc)
 export=OUT/'diagnostic-export.tcl';export.write_text('read_db {'+str(odb)+'}\nwrite_def {'+str(OUT/'routed.def')+'}\nwrite_verilog {'+str(OUT/'routed.v')+'}\nputs NSSOC_DIAGNOSTIC_EXPORT_COMPLETE\n')
 with (OUT/'diagnostic-export.log').open('w')as log:subprocess.run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(export)],stdout=log,stderr=subprocess.STDOUT,check=True)
 assert 'NSSOC_DIAGNOSTIC_EXPORT_COMPLETE'in(OUT/'diagnostic-export.log').read_text()
 check=flow.check_added_antennas((OUT/'routed.v').read_text(),report['cumulative_antenna_inventory'])
 assert check['new_diodes_exported']==832 and not check['missing_diodes']and not check['duplicate_diodes']and not check['signal_connection_mismatches']
 assert sha(sdc)==sdchash
 state.update(odb=str(odb),nl=str(OUT/'routed.v'));state['def']=str(OUT/'routed.def');state['metrics']={}
 initial.write_text(json.dumps(state,indent=2)+'\n')
 report['fresh_view_binding']=dict(odb_sha256=sha(odb),netlist_sha256=sha(OUT/'routed.v'),def_sha256=sha(OUT/'routed.def'),sdc_sha256=sdchash,export_script_sha256=sha(export))
 report['baseline_estimated_corners']=r['source_admission']['estimated_corners'];report['antenna_netlist_export']=check
 report['added_diode_power_contact']['scope']+=' Historical diode contact evidence only; resized-cell power proof is a separate gate.'
 (OUT/'diagnostic-source.json').write_text(json.dumps(dict(run=run['id'],head=run['head_sha'],artifact=aid,digest=digest,metrics=r['metrics'],production_admissible=False,wrapper_sha256=sha(__file__)),indent=2)+'\n')
 return report,artifacts+[meta],initial

if __name__=='__main__':
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 flow.OUT=OUT;flow.restore_route=restore_candidate;flow.RUN=44402072903;flow.HEAD='75131e1401c85e6cdc12d05819f401856162a93c'
 try:flow.main()
 finally:
  p=OUT/'result.json'
  if p.is_file():
   r=json.loads(p.read_text());r.update(diagnostic_only=True,antenna_closed=False,production_admissible=False,requires_repaired_route_reextraction=True)
   if r['status'].startswith('NOMINAL_RC_'):r['status']='DIAGNOSTIC_NOMINAL_RC_STA_ONLY_ANTENNA_REJECTED_CANDIDATE'
   p.write_text(json.dumps(r,indent=2)+'\n')
