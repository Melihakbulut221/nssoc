#!/usr/bin/env python3
"""Fresh actual nominal RC for the physically admitted combined clock/data ECO."""
import os,json,hashlib,subprocess
from pathlib import Path
import cloud_core_only_critical_clean_extraction as clean
from cloud_core_only_postgrt import completed,archive,put,sha
flow=clean.flow
OUT=flow.ROOT/'hw/soc/out/core-only-load-resize-antenna-extraction'
RUN=44524545738
HEAD='c0ae24df469b3a3422b35c7ff9bcb99b38870b94'
ODB_SHA='171fa1a8f80a9eff594c169519b2fc216ff12ffd7c2e4ef150964ee0af26a1bb'
def restore_candidate():
 report,artifacts,initial=clean.restore_candidate()
 run=completed(RUN,HEAD);assert run['run_attempt']==1
 z,m=archive(run,'core-only-load-resize-antenna-neighbor-route-'+str(RUN))
 assert m['id']==14531207616 and m['digest']=='sha256:3be91dc83fb3d6312ada57dbcb86dba41cf073099485b49591541ff693fd163b'
 r=json.loads(z.read('result.json'));assert r['source_head']==HEAD and r['sources_unchanged']and not r['accepted']
 assert r['status']=='RESIZED_DRIVER_ANTENNA_NEIGHBOR_ROUTE_GEOMETRY_CLEAN_REQUIRES_FRESH_RC_AND_SIGNOFF'
 assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 assert r['source_artifact']['id']==14527411628
 assert r['source_artifact']['digest']=='sha256:308f48a0aef5a5f9dc5d779b4e12df86264f90ee82a244850de27cc08d6a3c7c'
 assert r['source_audit']['original_instances']==106656 and r['source_audit']['new_diodes']==8 and r['source_audit']['total_instances']==106664
 ident=r['detailed_identity'];assert ident['instances']==106664 and ident['sources_unchanged']
 for key in ['exact_instance_geometry_status_and_masters','exact_terminal_connections','exact_net_names_and_signal_types','exact_special_wires_ports_and_die']:assert ident[key]
 preserve=r['detailed_preservation'];assert preserve['checked_unchanged_nets']==103085 and preserve['checked_clock_nets']==2113
 assert not preserve['changed_unselected_nets']and not preserve['changed_clock_nets']
 for key,expected in [('fixed-type-admission','FIXED'),('restored-type-admission','ROUTED')]:
  t=r[key];assert t['checked_nets']==102969 and t['expected_encoded_type']==expected and not t['wrong_types']and t['source_unchanged']
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
 signal,signal_meta=verified(44477663047,'ea2bf956f4fc240ca27b77e803e215068687ec1e','core-only-slew-spacing-antenna-prep-44477663047',14506853261,'057c9964796507d082a385c92076a2617f67cb05fe6b37556af4ede89dc3c5b1')
 assert signal['status']=='SLEW_SIGNAL_ANTENNA_DIODE_ADDED_ALL_CLOCK_ROUTES_PRESERVED_REQUIRES_ROUTING_AND_FRESH_RC'
 si=signal['insertion_audit'];assert si['original_instances']==106650 and si['new_diodes']==1 and si['total_instances']==106651 and si['sources_unchanged']
 assert list(si['new_cells'])==['ANTENNA_2566'] and si['new_cells']['ANTENNA_2566']['signal_terms']==[dict(pin='A',type='SIGNAL',net='nssoc_sta_n_56323')]
 for key in ['original_geometry_status_and_connections_preserved','power_geometry_ports_and_die_preserved','all_new_terminals_connected']:assert si[key]
 sp=signal['added_power_contact'];assert sp['checked_power_terminals']==2 and not sp['failures'] and sp['sources_unchanged'] and sp['native_rail_removal_control']['loss_of_contact_detected']
 assert signal['candidate_odb_sha256']==signal['outputs']['diodes-inserted.odb']=='fd3890d4cdcee434e279277375a484922cc4e3a5b7ae6f00235d2eb45ed22845'
 assert signal['outputs']['source.odb']=='c872aa32fa3af58292e86a6caecf6e2fb2f8e875d3c8f1be077461304133d99d'
 pp=signal['preserved_routes'];assert pp['checked_unchanged_nets']==103084 and pp['checked_clock_nets']==2113 and not pp['changed_unselected_nets'] and not pp['changed_clock_nets']
 (OUT/'signal-diode-preparation-admission.json').write_text(json.dumps(dict(audit=si,power=sp,artifact=signal_meta,production_admissible=False),indent=2)+'\n')
 artifacts.append(signal_meta)
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
 assert not set(cumulative)&set(si['new_cells'])
 cumulative.update(si['new_cells']);assert len(cumulative)==1398
 load,load_meta=verified(44494801363,'56a2b9d33ad08ae632486f6248e8ffc75e5b60c6','core-only-spacing-load-antenna-prep-44494801363',14515255856,'48c52b4678a6115d8e161e91468cfe78d9f2f6aee0c41d11467cda0e204247ff')
 assert load['status']=='SLEW_LOAD_ANTENNA_DIODE_ADDED_ALL_CLOCK_ROUTES_PRESERVED_REQUIRES_ROUTING_AND_FRESH_RC'
 li=load['insertion_audit'];assert li['original_instances']==106654 and li['new_diodes']==2 and li['total_instances']==106656 and li['sources_unchanged']
 assert set(li['new_cells'])=={'ANTENNA_2567','ANTENNA_2568'}
 assert all(c['master']=='sg13g2_antennanp' and c['signal_terms']==[dict(pin='A',type='SIGNAL',net='nssoc_slewiso_1_net')] for c in li['new_cells'].values())
 for key in ['original_geometry_status_and_connections_preserved','power_geometry_ports_and_die_preserved','all_new_terminals_connected']:assert li[key]
 lp=load['added_power_contact'];assert lp['checked_power_terminals']==4 and not lp['failures'] and lp['sources_unchanged'] and lp['native_rail_removal_control']['loss_of_contact_detected']
 assert load['candidate_odb_sha256']==load['outputs']['diodes-inserted.odb']=='44e5b8fe6d989394000395ca7449744007dc812710149bc856efaa6172aad9d4'
 assert load['outputs']['source.odb']=='0cb063d1069d079d08912d11c1cf23429e1d53417e5185b822df4b4d27da6fc7'
 pp=load['preserved_routes'];assert pp['checked_unchanged_nets']==103087 and pp['checked_clock_nets']==2113 and not pp['changed_unselected_nets'] and not pp['changed_clock_nets']
 buffers,buffers_meta=verified(44484842788,'424916da5073bb877d9562283d0776f9e84b4312','core-only-spacing-load-isolation-prep-44484842788',14509698252,'e561c72c73d4ff2e3423d1aa7418346e899dbc55e6dd325b92fda65336e9828d')
 assert buffers['status']=='THREE_SLEW_LOAD_ISOLATION_BUFFERS_PREPARED_REQUIRES_ROUTING_ANTENNA_AND_FRESH_RC'
 bi=buffers['audit'];assert bi['instances']==106654 and bi['new_buffers']==3
 for key in ['all_original_geometry_preserved','original_functional_connections_recovered_after_identity_buffer_collapse','wrong_connection_control_rejected','power_geometry_ports_preserved','diode_connections_preserved']:assert bi[key]
 bp=buffers['power_contact'];assert bp['checked_power_terminals']==6 and not bp['failures']
 assert buffers['outputs']['candidate-partially-routed.odb']=='817da3424bab97949446a8735eb1ee14b49b7d9bbdf39e1b2680e6c6bd0761a2'
 assert buffers['source_admission']['odb_sha256']=='a185d1494ffb265a9d07a08a4175704602ade02cf974ee8f9efbb923d22d098e'
 (OUT/'load-preparation-admission.json').write_text(json.dumps(dict(antenna=li,power=lp,artifact=load_meta,buffers=bi,buffer_power=bp,buffer_artifact=buffers_meta,production_admissible=False),indent=2)+'\n')
 artifacts.extend([load_meta,buffers_meta])
 assert not set(cumulative)&set(li['new_cells'])
 cumulative.update(li['new_cells']);assert len(cumulative)==1400


 next_resize,next_meta=verified(44505868283,'2f8f9bbde7acaea4208e4f2f23c8b5ee073a48cf','core-only-load-next-resize-44505868283',14518854658,'243b14e961d165d81124ec57e503af59e6e6bbf2e6a5398180c013ae6dc0623d')
 assert next_resize['status']=='TWO_REMAINING_SLEW_DRIVERS_RESIZED_ALL_CLOCK_ROUTES_PRESERVED_REQUIRES_ROUTING_RC_ALL_CORNERS'
 assert next_resize['audit']['instances']==106656 and next_resize['audit']['resized_cells']==2
 assert next_resize['power_contact']['checked_power_terminals']==4 and not next_resize['power_contact']['failures']
 assert next_resize['outputs']['candidate-partially-routed.odb']=='756fdc34ff3710eaf3341548c9c06815866d76ce5215c60e87c511eefddd6286'
 assert next_resize['outputs']['source.odb']=='8bd5334ca987ad52d5987b776587773d801188c9f83119d102cfd63a348d00c8'
 assert set(next_resize['plan'])=={'nssoc_sta_i_61007','nssoc_sta_i_63722'}
 for name,old,new in [('nssoc_sta_i_61007','sg13g2_nor3_1','sg13g2_nor3_2'),('nssoc_sta_i_63722','sg13g2_a21oi_1','sg13g2_a21oi_2')]:
  assert next_resize['plan'][name]['old']==old and next_resize['plan'][name]['new']==new
 extra,extra_meta=verified(44518671953,'d14bbe71c8b0f6c51415c86b5f4f43384272f08d','core-only-load-resize-antenna-prep-44518671953',14527411628,'308f48a0aef5a5f9dc5d779b4e12df86264f90ee82a244850de27cc08d6a3c7c')
 assert extra['status']=='RESIZED_DRIVER_ANTENNA_DIODES_ADDED_ALL_CLOCK_ROUTES_PRESERVED_REQUIRES_ROUTING_AND_FRESH_RC'
 ei=extra['insertion_audit'];assert ei==r['source_audit']
 assert ei['original_instances']==106656 and ei['new_diodes']==8 and ei['total_instances']==106664 and ei['sources_unchanged']
 assert set(ei['new_cells'])=={'ANTENNA_'+str(i) for i in range(2569,2577)}
 for key in ['original_geometry_status_and_connections_preserved','power_geometry_ports_and_die_preserved','all_new_terminals_connected']:assert ei[key]
 assert all(c['master']=='sg13g2_antennanp' and c['signal_terms']==[dict(pin='A',type='SIGNAL',net='nssoc_sta_n_60783')] for c in ei['new_cells'].values())
 ep=extra['added_power_contact'];assert ep['checked_power_terminals']==16 and not ep['failures'] and ep['sources_unchanged'] and ep['native_rail_removal_control']['loss_of_contact_detected']
 assert extra['candidate_odb_sha256']==extra['outputs']['diodes-inserted.odb']=='8d1a34b991abf59c1e26a7e2ef119b3ee74f7bf82ddd96167b4e95814524e5ed'
 assert extra['outputs']['source.odb']=='8569baaabaf2e1c027eb5c59a8872a9d1936dc2d40d6781f17c0e36fbf0eafe5'
 assert not set(cumulative)&set(ei['new_cells'])
 cumulative.update(ei['new_cells']);assert len(cumulative)==1408
 (OUT/'next-resize-preparation-admission.json').write_text(json.dumps(dict(resize=next_resize['audit'],resize_power=next_resize['power_contact'],resize_artifact=next_meta,antenna=ei,antenna_power=ep,antenna_artifact=extra_meta,production_admissible=False),indent=2)+'\n')
 artifacts.extend([next_meta,extra_meta])

 report['added_diode_power_contact'].update(checked_terminals=2816,next_resize_terminals=16,next_resize_artifact=extra_meta,load_repair_terminals=4,load_repair_artifact=load_meta,clock_repair_terminals=2,clock_repair_artifact=am,signal_repair_terminals=2,signal_repair_artifact=signal_meta)
 (OUT/'combined-preparation-admission.json').write_text(json.dumps(dict(setup_resize=resized['audit'],setup_resize_power=resized['power_contact'],buffers=prep['audit'],buffer_power=prep['power_contact'],clock_diode=inv,clock_diode_power=ant['added_power_contact'],production_admissible=False),indent=2)+'\n')
 artifacts.extend([pm,am,rm])

 state=json.loads(initial.read_text());sdc=Path(state['sdc']);sdc_hash=sha(sdc)
 export=OUT/'routed-export.tcl';export.write_text('read_db {'+str(odb)+'}\nwrite_def {'+str(OUT/'routed.def')+'}\nwrite_verilog {'+str(OUT/'routed.v')+'}\nputs NSSOC_CLOCK_EXPORT_COMPLETE\n')
 with (OUT/'routed-export.log').open('w')as log:subprocess.run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(export)],stdout=log,stderr=subprocess.STDOUT,check=True)
 assert 'NSSOC_CLOCK_EXPORT_COMPLETE'in(OUT/'routed-export.log').read_text()
 check=flow.check_added_antennas((OUT/'routed.v').read_text(),report['cumulative_antenna_inventory'])
 assert check['new_diodes_exported']==1408 and not check['missing_diodes']and not check['duplicate_diodes']and not check['signal_connection_mismatches']
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
