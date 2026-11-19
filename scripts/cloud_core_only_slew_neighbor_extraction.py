#!/usr/bin/env python3
"""Fresh actual nominal RC for the physically admitted combined clock/data ECO."""
import os,json,hashlib,subprocess
from pathlib import Path
import cloud_core_only_critical_clean_extraction as clean
from cloud_core_only_postgrt import completed,archive,put,sha
flow=clean.flow
OUT=flow.ROOT/'hw/soc/out/core-only-slew-neighbor-extraction'
RUN=44465781176
HEAD='144b7a14e8978ab90639276687c0091c038c96fa'
ODB_SHA='773f9b92c29ead0f8755f0a6803503c855d27279eca288eb778269190449be5f'
def restore_candidate():
 report,artifacts,initial=clean.restore_candidate()
 run=completed(RUN,HEAD);assert run['run_attempt']==1
 z,m=archive(run,'core-only-slew-neighbor-route-'+str(RUN))
 assert m['id']==14501894937 and m['digest']=='sha256:b1a6bb7cec948c35b52d9deb69ba1d2019334f341816212eca108a259610c2f5'
 r=json.loads(z.read('result.json'));assert r['source_head']==HEAD and r['sources_unchanged']and not r['accepted']
 assert r['status']=='SLEW_RESIZE_ROUTE_GEOMETRY_AND_ANTENNA_CLEAN_REQUIRES_FRESH_RC_AND_SIGNOFF'
 assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 assert r['source_artifact']['id']==14500910211
 assert r['source_artifact']['digest']=='sha256:0af2aeed67452942363b30b898bc07cd8feeeb74e70232380f917469194b88a1'
 assert r['source_audit']['instances']==106650 and r['source_audit']['resized_cells']==3
 ident=r['detailed_identity'];assert ident['instances']==106650 and ident['sources_unchanged']
 for key in ['exact_instance_geometry_status_and_masters','exact_terminal_connections','exact_net_names_and_signal_types','exact_special_wires_ports_and_die']:assert ident[key]
 preserve=r['detailed_preservation'];assert preserve['checked_unchanged_nets']==103067 and preserve['checked_clock_nets']==2113
 assert not preserve['changed_unselected_nets']and not preserve['changed_clock_nets']
 for key,expected in [('fixed-type-admission','FIXED'),('restored-type-admission','ROUTED')]:
  t=r[key];assert t['checked_nets']==102951 and t['expected_encoded_type']==expected and not t['wrong_types']and t['source_unchanged']
  assert t['controls']['metadata_only_fix_rejected']and t['controls']['encoded_fixed_accepted']
 assert r['metrics']['route__drc_errors']==0
 # Current route must have zero native antenna violations.
 assert r['metrics']['antenna__violating__nets']==0 and r['metrics']['antenna__violating__pins']==0
 g=r['visible_geometry'];assert g['source_unchanged']and g['actual_route_removal_control']
 assert not g['signal_nets_with_disconnected_geometry']and not g['unwired_multi_terminal_nets']and not g['terminals_without_geometry']and g['inter_net_contact_pairs']==0
 assert r['routed_odb_sha256']==g['source_odb_sha256']==ODB_SHA and r['output_odb']=='restored-status.odb'
 odb=OUT/'combined-route.odb';put(odb,z.read(r['output_odb']),ODB_SHA)
 def verified(rid,head,name,aid,digest):
  rr=completed(rid,head);assert rr['run_attempt']==1
  zz,mm=archive(rr,name);assert mm['id']==aid and mm['digest']=='sha256:'+digest
  result=json.loads(zz.read('result.json'));assert result['source_head']==head and result['sources_unchanged']and not result['accepted']
  assert set(n for n in zz.namelist()if not n.endswith('/')and n!='result.json')==set(result['outputs'])
  for n,h in result['outputs'].items():assert hashlib.sha256(zz.read(n)).hexdigest()==h,n
  return result,mm
 slew,sm=verified(44461789690,'a5b0a083be4dbb4cd656a7f92c5d5eb8d31531e3','core-only-clean-slew-resize-44461789690',14500910211,'0af2aeed67452942363b30b898bc07cd8feeeb74e70232380f917469194b88a1')
 assert slew['audit']['instances']==106650 and slew['audit']['resized_cells']==3
 assert slew['power_contact']['checked_power_terminals']==6 and not slew['power_contact']['failures']
 assert slew['outputs']['candidate-partially-routed.odb']=='4fc368e1d6ca1d5661f048b8cad148d38554176849b003245bf2f74454edf14b'
 assert slew['outputs']['source.odb']=='f381bd8d9e79ca38918d4bbda5c4014959a0e6966ac9a130d4ea9274d6a5192e'
 assert set(slew['plan'])=={'nssoc_sta_i_55577','nssoc_sta_i_54413','nssoc_sta_i_57921'}
 for name in ['nssoc_sta_i_55577','nssoc_sta_i_54413']:
  assert slew['plan'][name]['old']=='sg13g2_nor4_1' and slew['plan'][name]['new']=='sg13g2_nor4_2'
 assert slew['plan']['nssoc_sta_i_57921']['old']=='sg13g2_nor3_1' and slew['plan']['nssoc_sta_i_57921']['new']=='sg13g2_nor3_2'
 (OUT/'slew-preparation-admission.json').write_text(json.dumps(dict(audit=slew['audit'],power=slew['power_contact'],artifact=sm,production_admissible=False),indent=2)+'\n')
 artifacts.append(sm)
 resized,rm=verified(44451541789,'54f69c44d1155216d7309873f97aec09a4c48462','core-only-combined-setup-resize-44451541789',14495583524,'c15fe2a7fbeac097c782c716191d9e946547e900c6ca922e21afff743ed61fd2')
 assert resized['audit']['instances']==106650 and resized['audit']['resized_cells']==2
 assert resized['power_contact']['checked_power_terminals']==4 and not resized['power_contact']['failures']
 assert resized['outputs']['candidate-partially-routed.odb']=='3fdabf4513843cba12aeb42f01583f9bedc63551408e357a7724f26cdd51bd21'
 assert resized['outputs']['source.odb']=='81766779033ee0642d322a417e4e8f389807b7cb2d1d5ceb6cf1842915fb68ee'
 assert set(resized['plan'])=={'nssoc_sta_i_2496','fanout2484'}
 assert resized['plan']['nssoc_sta_i_2496']['old']=='sg13g2_nor2_1' and resized['plan']['nssoc_sta_i_2496']['new']=='sg13g2_nor2_2'
 assert resized['plan']['fanout2484']['old']=='sg13g2_buf_1' and resized['plan']['fanout2484']['new']=='sg13g2_buf_4'
 prep,pm=verified(44445416976,'b1583bfb21a37be84e123d3b179aaa5c26db5985','core-only-combined-timing-prep-44445416976',14493640185,'d878b0137b2bfe8e79a6be7b630238e69051c3d6ea4f340755248df3fb7722b1')
 assert prep['audit']['instances']==106650 and prep['audit']['new_buffers']==2
 assert prep['power_contact']['checked_power_terminals']==4 and not prep['power_contact']['failures']
 assert prep['source_admission']['run']==44442857432 and prep['source_admission']['odb_sha256']=='42710e6fade6cbcf116bf9f0d606312fa6224293034c0b3a96b629404396c0d8'
 ant,am=verified(44442143764,'e77d6ccd6fb5ca195e0d006fb8a46a7eb8520c16','core-only-sram-clock-antenna-prep-44442143764',14492630052,'473f0f6f2dabdc8e14e1fa3b97f95449a64c1ca3bbd0fdd73e4ee63cd0d8c8b3')
 inv=ant['insertion_audit'];assert inv['new_diodes']==1 and inv['total_instances']==106648 and inv['sources_unchanged']
 assert inv['original_geometry_status_and_connections_preserved']and inv['power_geometry_ports_and_die_preserved']and inv['all_new_terminals_connected']
 assert list(inv['new_cells'])==['ANTENNA_2565']and inv['new_cells']['ANTENNA_2565']['signal_terms'][0]['net']=='clknet_1_0_0_clk_i'
 assert ant['added_power_contact']['checked_power_terminals']==2 and not ant['added_power_contact']['failures']and ant['added_power_contact']['sources_unchanged']
 cumulative=report['cumulative_antenna_inventory'];assert len(cumulative)==1396 and not set(cumulative)&set(inv['new_cells'])
 cumulative.update(inv['new_cells']);assert len(cumulative)==1397
 report['added_diode_power_contact'].update(checked_terminals=2794,clock_repair_terminals=2,clock_repair_artifact=am)
 (OUT/'combined-preparation-admission.json').write_text(json.dumps(dict(setup_resize=resized['audit'],setup_resize_power=resized['power_contact'],buffers=prep['audit'],buffer_power=prep['power_contact'],clock_diode=inv,clock_diode_power=ant['added_power_contact'],production_admissible=False),indent=2)+'\n')
 artifacts.extend([pm,am,rm])

 state=json.loads(initial.read_text());sdc=Path(state['sdc']);sdc_hash=sha(sdc)
 export=OUT/'routed-export.tcl';export.write_text('read_db {'+str(odb)+'}\nwrite_def {'+str(OUT/'routed.def')+'}\nwrite_verilog {'+str(OUT/'routed.v')+'}\nputs NSSOC_CLOCK_EXPORT_COMPLETE\n')
 with (OUT/'routed-export.log').open('w')as log:subprocess.run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(export)],stdout=log,stderr=subprocess.STDOUT,check=True)
 assert 'NSSOC_CLOCK_EXPORT_COMPLETE'in(OUT/'routed-export.log').read_text()
 check=flow.check_added_antennas((OUT/'routed.v').read_text(),report['cumulative_antenna_inventory'])
 assert check['new_diodes_exported']==1397 and not check['missing_diodes']and not check['duplicate_diodes']and not check['signal_connection_mismatches']
 assert sha(sdc)==sdc_hash
 state.update(odb=str(odb),nl=str(OUT/'routed.v'));state['def']=str(OUT/'routed.def');state['metrics']={}
 initial.write_text(json.dumps(state,indent=2)+'\n')
 report['fresh_view_binding']=dict(odb_sha256=sha(odb),netlist_sha256=sha(OUT/'routed.v'),def_sha256=sha(OUT/'routed.def'),sdc_sha256=sdc_hash,export_script_sha256=sha(export))
 report['antenna_netlist_export']=check
 (OUT/'combined-route-source.json').write_text(json.dumps(dict(run=RUN,head=HEAD,artifact=m,metrics=r['metrics'],preservation=preserve,identity=ident,visible_geometry=g,production_admissible=False,antenna_open=False,wrapper_sha256=sha(__file__)),indent=2)+'\n')
 (OUT/'source-antenna.rpt').write_bytes(z.read('antenna.rpt'))
 artifacts.append(m)
 return report,artifacts,initial
if __name__=='__main__':
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 clean.OUT=OUT;flow.OUT=OUT;flow.restore_route=restore_candidate;flow.RUN=RUN;flow.HEAD=HEAD
 flow.main()
