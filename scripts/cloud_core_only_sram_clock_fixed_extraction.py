#!/usr/bin/env python3
"""Diagnostic actual RC for the preserved SRAM clock ECO; antenna remains open."""
import os,json,hashlib,subprocess
from pathlib import Path
import cloud_core_only_critical_clean_extraction as clean
from cloud_core_only_postgrt import completed,archive,put,sha
flow=clean.flow
OUT=flow.ROOT/'hw/soc/out/core-only-sram-clock-fixed-extraction'
RUN=44438114279
HEAD='2f0e5e8b1fa7352b93ae19796fd741a4ef1f52f6'
ODB_SHA='a2d85760fec57ea28ea10a192c27528326b9fb48aa5c4a682367c08fdacca9ba'
def restore_candidate():
 report,artifacts,initial=clean.restore_candidate()
 run=completed(RUN,HEAD);assert run['run_attempt']==1
 z,m=archive(run,'core-only-sram-clock-fixed-route-'+str(RUN))
 assert m['id']==14490194336 and m['digest']=='sha256:eaa8647f9269c317488cc1fb488ae12402d9ea637dcb5a040dea27779298903a'
 r=json.loads(z.read('result.json'));assert r['source_head']==HEAD and r['sources_unchanged']and not r['accepted']
 assert r['status']=='SELECTED_ROUTE_MEASURED_REQUIRES_ANTENNA_CLOSURE_AND_FRESH_RC'
 assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 assert r['source_artifact']['id']==14487078971
 assert r['source_artifact']['digest']=='sha256:174162f2f8c55679aece9a67de73803fb32b45bd57c0e501b7d166eac6960ac0'
 assert r['source_audit']['instances']==106647 and r['source_audit']['resized_cells']==1
 ident=r['detailed_identity'];assert ident['instances']==106647 and ident['sources_unchanged']
 for key in ['exact_instance_geometry_status_and_masters','exact_terminal_connections','exact_net_names_and_signal_types','exact_special_wires_ports_and_die']:assert ident[key]
 preserve=r['detailed_preservation'];assert preserve['checked_unchanged_nets']==103081 and preserve['checked_clock_nets']==2111
 assert not preserve['changed_unselected_nets']and not preserve['changed_clock_nets']
 for key,expected in [('fixed-type-admission','FIXED'),('restored-type-admission','ROUTED')]:
  t=r[key];assert t['checked_nets']==102965 and t['expected_encoded_type']==expected and not t['wrong_types']and t['source_unchanged']
  assert t['controls']['metadata_only_fix_rejected']and t['controls']['encoded_fixed_accepted']
 assert r['metrics']['route__drc_errors']==0
 # Known open antenna result is explicit, never waived for production.
 assert r['metrics']['antenna__violating__nets']==1 and r['metrics']['antenna__violating__pins']==1
 g=r['visible_geometry'];assert g['source_unchanged']and g['actual_route_removal_control']
 assert not g['signal_nets_with_disconnected_geometry']and not g['unwired_multi_terminal_nets']and not g['terminals_without_geometry']and g['inter_net_contact_pairs']==0
 assert r['routed_odb_sha256']==g['source_odb_sha256']==ODB_SHA and r['output_odb']=='restored-status.odb'
 odb=OUT/'clock-route.odb';put(odb,z.read(r['output_odb']),ODB_SHA)
 state=json.loads(initial.read_text());sdc=Path(state['sdc']);sdc_hash=sha(sdc)
 export=OUT/'routed-export.tcl';export.write_text('read_db {'+str(odb)+'}\nwrite_def {'+str(OUT/'routed.def')+'}\nwrite_verilog {'+str(OUT/'routed.v')+'}\nputs NSSOC_CLOCK_EXPORT_COMPLETE\n')
 with (OUT/'routed-export.log').open('w')as log:subprocess.run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(export)],stdout=log,stderr=subprocess.STDOUT,check=True)
 assert 'NSSOC_CLOCK_EXPORT_COMPLETE'in(OUT/'routed-export.log').read_text()
 check=flow.check_added_antennas((OUT/'routed.v').read_text(),report['cumulative_antenna_inventory'])
 assert check['new_diodes_exported']==1396 and not check['missing_diodes']and not check['duplicate_diodes']and not check['signal_connection_mismatches']
 assert sha(sdc)==sdc_hash
 state.update(odb=str(odb),nl=str(OUT/'routed.v'));state['def']=str(OUT/'routed.def');state['metrics']={}
 initial.write_text(json.dumps(state,indent=2)+'\n')
 report['fresh_view_binding']=dict(odb_sha256=sha(odb),netlist_sha256=sha(OUT/'routed.v'),def_sha256=sha(OUT/'routed.def'),sdc_sha256=sdc_hash,export_script_sha256=sha(export))
 report['antenna_netlist_export']=check
 (OUT/'clock-route-source.json').write_text(json.dumps(dict(run=RUN,head=HEAD,artifact=m,metrics=r['metrics'],preservation=preserve,identity=ident,visible_geometry=g,production_admissible=False,antenna_open=True,wrapper_sha256=sha(__file__)),indent=2)+'\n')
 (OUT/'source-antenna.rpt').write_bytes(z.read('antenna.rpt'))
 artifacts.append(m)
 return report,artifacts,initial
if __name__=='__main__':
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 clean.OUT=OUT;flow.OUT=OUT;flow.restore_route=restore_candidate;flow.RUN=RUN;flow.HEAD=HEAD
 flow.main()
