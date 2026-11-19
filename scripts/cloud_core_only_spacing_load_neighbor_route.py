#!/usr/bin/env python3
"""Selected-net routing experiment; every unaffected DEF net must be preserved."""
import os,json,hashlib,subprocess,re
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive,put
OUT=ROOT/'hw/soc/out/core-only-spacing-load-neighbor-route'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,status='PREPARING')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 try:
  from verify_spacing_load_rejection import verify_rejection
  r['rejected_predecessor']=verify_rejection(OUT);save()
  run=completed(44484842788,'424916da5073bb877d9562283d0776f9e84b4312');assert run['run_attempt']==1
  z,m=archive(run,'core-only-spacing-load-isolation-prep-44484842788');assert m['id']==14509698252 and m['digest']=='sha256:e561c72c73d4ff2e3423d1aa7418346e899dbc55e6dd325b92fda65336e9828d'
  src=json.loads(z.read('result.json'));assert src['source_head']==run['head_sha']and src['sources_unchanged']
  assert src['status']=='THREE_SLEW_LOAD_ISOLATION_BUFFERS_PREPARED_REQUIRES_ROUTING_ANTENNA_AND_FRESH_RC'
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(src['outputs'])
  for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  assert src['preserved_routes']['unchanged_def_net_records']==103082 and src['preserved_routes']['clock_routes_preserved']
  assert src['preserved_routes']['checked_clock_nets']==2113 and src['preserved_routes']['ndr_assignments_preserved']
  assert src['audit']['instances']==106654 and src['audit']['new_buffers']==3
  assert src['source_admission']['run']==44478446308 and src['source_admission']['odb_sha256']=='a185d1494ffb265a9d07a08a4175704602ade02cf974ee8f9efbb923d22d098e'
  for key in ['route__drc_errors','antenna__violating__nets','antenna__violating__pins']:assert src['source_admission']['metrics'][key]==0
  for key in ['all_original_geometry_preserved','original_functional_connections_recovered_after_identity_buffer_collapse','wrong_connection_control_rejected','power_geometry_ports_preserved','diode_connections_preserved']:assert src['audit'][key]
  assert src['power_contact']['checked_power_terminals']==6 and not src['power_contact']['failures']
  original=OUT/'candidate-partially-routed.odb';put(original,z.read('candidate-partially-routed.odb'),'817da3424bab97949446a8735eb1ee14b49b7d9bbdf39e1b2680e6c6bd0761a2')
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  guard=ROOT/'scripts/audit_core_only_route_identity.py';routeguard=ROOT/'scripts/audit_core_only_spacing_load_neighbor_routes.py';geometry=ROOT/'scripts/audit_native_signal_geometry_indexed.py'
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
  execute('read_db {'+str(original)+'}\nset_thread_count 4\nset_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nset_global_routing_layer_adjustment Metal2-TopMetal2 0.2\nset_nets_to_route {nssoc_sta_n_100406 nssoc_sta_n_53586 nssoc_sta_n_63283 nssoc_slewiso_0_net nssoc_slewiso_1_net nssoc_slewiso_2_net net5592}\nglobal_route -verbose\nwrite_db {'+str(selected)+'}\n','global')
  audit(selected,'global')
  # Fix native encoded paths, not merely dbNet metadata: DRT reads decoder wire type.
  selected_def=OUT/'selected.def'
  execute('read_db {'+str(selected)+'}\nwrite_def {'+str(selected_def)+'}\n','export-selected')
  def records(text):
   m=re.search(r'^NETS (\d+) ;\n(.*?)^END NETS',text,re.M|re.S);assert m
   entries=re.findall(r'^[ \t]*- (\S+) (.*?);',m.group(2),re.M|re.S);assert len(entries)==int(m.group(1))
   result=dict(entries);assert len(result)==len(entries);return result
  def canonical_record(value):
   # DEF terminal order is non-semantic. Preserve multiplicity and every suffix token.
   prefix,sep,suffix=value.partition('+');assert sep
   terminals=re.findall(r'\(\s*([^()]*)\)',prefix)
   assert not re.sub(r'\([^()]*\)','',prefix).strip(),prefix
   return (tuple(sorted(' '.join(t.split())for t in terminals)), ' '.join((sep+suffix).split()))
  fixture='( a A ) ( b B ) + USE SIGNAL + ROUTED Metal2 ( 10 20 ) ( 30 * )'
  assert canonical_record(fixture)==canonical_record(fixture.replace('( a A ) ( b B )','( b B ) ( a A )'))
  for wrong in [fixture.replace('b B','b C'),fixture.replace('( 30 * )','( 31 * )'),fixture.replace('( a A )','( a A ) ( a A )')]:
   assert canonical_record(fixture)!=canonical_record(wrong)
  source_text=selected_def.read_text();source_records=records(source_text)
  design=re.search(r'^DESIGN (\S+) ;',source_text,re.M).group(1);units=re.search(r'^UNITS DISTANCE MICRONS (\d+) ;',source_text,re.M).group(1)
  changed={'net5592', 'nssoc_slewiso_1_net', 'nssoc_slewiso_2_net', 'nssoc_sta_n_63283', 'nssoc_sta_n_100406', 'nssoc_slewiso_0_net', 'nssoc_sta_n_53586'}
  fixed_names=sorted(n for n,v in source_records.items()if n not in changed and re.search(r'\+ ROUTED\b',v))
  assert len(fixed_names)>90000 and 'clk_i'in fixed_names
  assert all(not re.search(r'\+ (FIXED|COVER|SHIELD)\b',source_records[n])for n in fixed_names)
  def patch(path,entries):
   path.write_text('VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN '+design+' ;\nUNITS DISTANCE MICRONS '+units+' ;\nNETS '+str(len(entries))+' ;\n'+''.join('- '+n+' '+v+';\n'for n,v in entries)+'END NETS\nEND DESIGN\n')
   protected[str(path)]=sha(path)
  fixed_def=OUT/'fixed-patch.def';patch(fixed_def,[(n,re.sub(r'\+ ROUTED\b','+ FIXED',source_records[n]))for n in fixed_names])
  fixed=OUT/'fixed-global.odb';fixed_export=OUT/'fixed-export.def'
  execute('read_db {'+str(selected)+'}\nread_def -floorplan_initialize {'+str(fixed_def)+'}\nwrite_db {'+str(fixed)+'}\nwrite_def {'+str(fixed_export)+'}\n','fix-unselected')
  fixed_records=records(fixed_export.read_text());assert set(fixed_records)==set(source_records)
  assert all(re.search(r'\+ FIXED\b',fixed_records[n])and not re.search(r'\+ ROUTED\b',fixed_records[n])for n in fixed_names),'Native DEF did not apply FIXED status'
  names_path=OUT/'fixed-net-names.json';names_path.write_text(json.dumps(fixed_names)+'\n');protected[str(names_path)]=sha(names_path)
  type_guard=ROOT/'scripts/audit_encoded_fixed_wire_type.py';protected[str(type_guard)]=sha(type_guard)
  def verify_types(odb_path,expected,label):
   env=dict(os.environ,NSSOC_FIXED_VERIFY_ODB=str(odb_path),NSSOC_FIXED_VERIFY_NAMES=str(names_path),NSSOC_FIXED_VERIFY_TYPE=expected,NSSOC_FIXED_VERIFY_REPORT=str(OUT/(label+'.json')))
   with (OUT/(label+'.log')).open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(type_guard)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
   r[label]=json.loads((OUT/(label+'.json')).read_text());save()
  verify_types(fixed,'FIXED','fixed-type-admission')
  for n,v in fixed_records.items():
   normalized=re.sub(r'\+ FIXED\b','+ ROUTED',v)if n in fixed_names else v
   assert canonical_record(normalized)==canonical_record(source_records[n]),('fix_roundtrip_changed_net',n)
  r['fixed_route_preparation']=dict(fixed_nets=len(fixed_names),all_records_verified=True);save()
  selected=fixed
  after=OUT/'soc_top.odb';r['status']='DETAILED_ROUTING_FIXED_UNSELECTED';save()
  execute('read_db {'+str(selected)+'}\nset_thread_count 4\nset_routing_layers -signal Metal2-TopMetal2 -clock Metal2-TopMetal2\nsource {'+str(ROOT/'hw/soc/flow/prune_orphan_guides.tcl')+'}\nputs "REMOVED_ORPHAN_GUIDES [prune_orphan_guides [ord::get_db_block]]"\ndetailed_route -droute_end_iter 64 -or_seed 42 -verbose 1 -output_drc {'+str(OUT/'soc_top.drc')+'}\nwrite_db {'+str(after)+'}\ncheck_antennas -report_file {'+str(OUT/'antenna.rpt')+'}\n','route',True)
  r['metrics']=json.loads((OUT/'route-metrics.json').read_text());save()
  # Restore only the routing status from FIXED to ROUTED after routing completes.
  routed_fixed_def=OUT/'routed-fixed.def'
  execute('read_db {'+str(after)+'}\nwrite_def {'+str(routed_fixed_def)+'}\n','export-fixed-result')
  routed_records=records(routed_fixed_def.read_text());assert set(routed_records)==set(source_records)
  for n in fixed_names:
   assert canonical_record(re.sub(r'\+ FIXED\b','+ ROUTED',routed_records[n]))==canonical_record(source_records[n]),('fixed_route_changed',n)
  thaw=OUT/'restore-route-status.def';patch(thaw,[(n,re.sub(r'\+ FIXED\b','+ ROUTED',routed_records[n]))for n in fixed_names])
  final=OUT/'restored-status.odb'
  execute('read_db {'+str(after)+'}\nread_def -floorplan_initialize {'+str(thaw)+'}\nwrite_db {'+str(final)+'}\n','restore-status')
  after=final;verify_types(after,'ROUTED','restored-type-admission');r['routed_odb_sha256']=sha(after);r['output_odb']='restored-status.odb';save()
  audit(after,'detailed')
  geom=OUT/'geometry';geom.mkdir();env=dict(os.environ,NSSOC_PHYSICAL_ROUTE_OUT=str(geom),NSSOC_PHYSICAL_ROUTE_ODB=str(after))
  with (OUT/'geometry.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(geometry)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['visible_geometry']=json.loads((geom/'physical-route-audit.json').read_text())
  assert r['metrics']['route__drc_errors']==0
  assert r['metrics']['antenna__violating__nets']==0 and r['metrics']['antenna__violating__pins']==0
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='SLEW_LOAD_NEIGHBOR_ROUTE_GEOMETRY_AND_ANTENNA_CLEAN_REQUIRES_FRESH_RC_AND_SIGNOFF',sources_unchanged=True,protected_inputs=protected)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
