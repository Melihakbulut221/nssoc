#!/usr/bin/env python3
"""Re-route verified canonical targeted ECO; estimated timing is not signoff."""
import json,os,stat,subprocess,time
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive,safe_path,put,current_path,restore_mapping,restore_cts,qualify_sources,fresh_corner_metrics
from cloud_core_only_clock_probe import restore_cts8
from cloud_core_only_clock_refine import restore_clock_split,restore_previous
from cloud_core_only_detailed_route import restore_refinement
OUT=ROOT/'hw/soc/out/core-only-posteco-detailed-route'
RUN=44327965276
HEAD='0fbac4d6617c72f3d00a0b759cfc4677bae1b732'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,status='PREPARING',parasitics='global route estimates, not extracted signoff')
 def save(): (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 try:
  qualify_sources()
  mapping,ma=restore_mapping();cts,ca,config,initial=restore_cts()
  assert cts['source_binding']['netlist_sha256']==mapping['outputs']['synthesis/soc_top.netlist.v']
  _,cm,config,initial=restore_cts8(config)
  _,sm,initial=restore_clock_split();_,pm,initial=restore_previous();_,rm,initial=restore_refinement()
  run=completed(RUN,HEAD);z,meta=archive(run,f'core-only-pin-aware-electrical-eco-{RUN}')
  assert meta['id']==14438605718 and meta['digest']=='sha256:36fcd030bd23666169d392b84668f5bf0cd727d1b4b5f351d75c8a20fd876bb1'
  raw=z.read('result.json');eco=json.loads(raw)
  assert eco['source_head']==HEAD and eco['sources_unchanged'] and not eco['accepted']
  assert eco['status']=='TARGETED_BUFFER_ECO_LEGALIZED_AND_FUNCTIONALLY_CONTRACTED_REQUIRES_FRESH_ROUTING_TIMING'
  assert eco['source_globalroute_head']=='3d8c75c1f63dfa753f58617e391e28850aa603ef'
  audit=eco['audit'];assert audit['new_buffers']==6 and audit['resized_cells']==4
  assert audit['sram_pin_distance_after_um']<=75 and audit['sram_pin_distance_after_um']<audit['sram_pin_distance_before_um']/4
  for key in ['all_other_instance_geometry_preserved','original_terminal_classes_preserved','original_net_signal_types_preserved','pins_and_power_geometry_preserved','all_original_antenna_cells_preserved','clock_geometry_and_connectivity_preserved']:
   assert audit[key] is True,key
  root=ROOT/'hw/soc/out/core-only-pin-aware-electrical-eco';seen=set()
  for item in z.infolist():
   if item.is_dir()or item.filename=='result.json':continue
   assert not stat.S_ISLNK(item.external_attr>>16)
   n=item.filename;assert n in eco['outputs'] and n not in seen
   put(safe_path(root,n),z.read(item),eco['outputs'][n]);seen.add(n)
  assert seen==set(eco['outputs']);root.joinpath('result.json').write_bytes(raw)
  for p,h in eco['protected_inputs'].items():assert sha(current_path(p))==h,p
  odb=root/'core-eco-placed-unrouted.odb'
  assert sha(odb)=='5d800a165a0fa1a0600c6f5e076b1af0ff8b37edff802f2f62c72f0fb0f4483d'
  grun=completed(44328874040,'733cb000518b8bd6d95470fde5e6e3c3e32bafa6')
  gz,gm=archive(grun,'core-only-pin-aware-electrical-globalroute-44328874040')
  assert gm['id']==14438862280 and gm['digest']=='sha256:e47da3fe91a279ad2102ee2d84420b226afddd73646b26dceb5ab42c37e05fa8'
  graw=gz.read('result.json');g=json.loads(graw)
  assert g['sources_unchanged'] and g['returncode']==0 and not g['accepted']
  assert g['source_binding']['eco_run']==RUN and g['source_binding']['eco_head']==HEAD
  groot=ROOT/'hw/soc/out/core-only-pin-aware-electrical-globalroute';seen=set()
  for item in gz.infolist():
   if item.is_dir()or item.filename=='result.json':continue
   assert not stat.S_ISLNK(item.external_attr>>16)
   n=item.filename;assert n in g['outputs']and n not in seen
   put(safe_path(groot,n),gz.read(item),g['outputs'][n]);seen.add(n)
  assert seen==set(g['outputs']);(groot/'result.json').write_bytes(graw)
  for p,h in g['protected_inputs'].items():assert sha(current_path(p))==h,p
  for entry in g['corners'].values():
   metrics,path=fresh_corner_metrics(safe_path(groot,entry['state']),entry['corner_name'])
   assert metrics==entry['metrics']and sha(path)==entry['metrics_sha256']
   assert metrics['timing__setup_vio__count']==metrics['timing__hold_vio__count']==metrics['design__max_fanout_violation__count']==0
  # Electrical violations are retained as open; routing is a measurement trial.
  assert g['corners']['slow']['metrics']['design__max_slew_violation__count']==11
  assert all(e['metrics']['design__max_cap_violation__count']==1 for e in g['corners'].values())
  initial=safe_path(groot,g['output_state']);state=json.loads(initial.read_text());before=current_path(state['odb'])
  assert sha(before)=='4dc086112f1b650df6bd4789aadb8c5de94bebba913055d5fd9a0de827ffc7f8'
  cfg=json.loads(config.read_text());assert cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5.0
  cfg2=dict(cfg);cfg2.update(DRT_ANTENNA_REPAIR_JUMPER_ONLY=True,DRT_ANTENNA_REPAIR_DIODE_ONLY=False)
  allowed={'DRT_ANTENNA_REPAIR_JUMPER_ONLY','DRT_ANTENNA_REPAIR_DIODE_ONLY'}
  assert {k for k in set(cfg)|set(cfg2)if cfg.get(k)!=cfg2.get(k)}<=allowed
  config=OUT/'route-config.json';config.write_text(json.dumps(cfg2,indent=2)+'\n')
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  flow=ROOT/'hw/soc/pnr/core_only_detailed_route_flow.py'
  guard=ROOT/'scripts/audit_core_only_route_identity.py';geometry=ROOT/'scripts/audit_native_signal_geometry_indexed.py'
  assert sha(guard)=='e3de6a24b6a993082970527da2154933c32b4b39ab50342a435028439bf3ef02'
  assert sha(geometry)=='3baed05b7cbad6c03991d783fc7ad772e3b68e1534031ad07735750d7e79dabd'
  assert sha(ROOT/'scripts/native_geometry_contact_index.py')=='0423bd8ec0941d761f7594100f2e3be84f6cc6b2c67a2d55c951d69b86b7a26f'
  completed(44336120355,'fd3d320e8090dce8b16963e5add98162d168faf9')
  protected={str(p):sha(p)for p in [Path(__file__),flow,guard,geometry,ROOT/'scripts/native_geometry_contact_index.py',ROOT/'scripts/buffer_core_only_chip_controls.py',config,initial,before,current_path(state['sdc'])]}
  r.update(status='DETAILED_ROUTING',protected_inputs=protected,source_binding=dict(globalroute_run=44328874040,globalroute_head=grun['head_sha'],artifacts=ma+ca+[cm,sm,pm]+rm+[meta,gm]),baseline_estimated_corners=g['corners'],accepted=False,parasitics='No new extracted timing yet',full_chip_lvs_passed=False,manufacturing_approval=False,config_delta={k:cfg2[k]for k in allowed})
  directory=OUT/'routing';directory.mkdir()
  cmd=[str(app),'python',str(flow),'--flow','CoreOnlyDetailedRoute','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(directory),'--with-initial-state',str(initial),str(config)]
  r['command']=cmd;save()
  with (OUT/'routing.log').open('w')as log:
   process=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);started=time.monotonic()
   while process.poll()is None:
    print('Detailed routing active',process.pid,'elapsed_seconds',round(time.monotonic()-started),flush=True);time.sleep(30)
  r['returncode']=process.returncode
  if process.returncode:raise RuntimeError('Detailed route failed; preserve logs')
  states=list(directory.glob('*-nssoc-coreonlydetailedrouting/state_out.json'));assert len(states)==1
  routed=states[0];after=current_path(json.loads(routed.read_text())['odb'])
  metrics=routed.parent/'or_metrics_out.json';r['routing_metrics']=dict(path=str(metrics.relative_to(OUT)),sha256=sha(metrics),values=json.loads(metrics.read_text()))
  ant=list(directory.glob('*-openroad-checkantennas/or_metrics_out.json'));assert len(ant)==1
  r['antenna_metrics']=dict(path=str(ant[0].relative_to(OUT)),sha256=sha(ant[0]),values=json.loads(ant[0].read_text()))
  identity_out=OUT/'identity';identity_out.mkdir()
  env=dict(os.environ,NSSOC_CONTROL_BUFFER_OUT=str(OUT),NSSOC_ROUTE_IDENTITY_BEFORE=str(before),NSSOC_ROUTE_IDENTITY_AFTER=str(after),NSSOC_ROUTE_IDENTITY_OUT=str(identity_out))
  with (OUT/'identity.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(guard)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['route_identity']=json.loads((identity_out/'route-identity.json').read_text());r['routed_state']=str(routed.relative_to(OUT));save()
  geomout=OUT/'geometry';geomout.mkdir();env=dict(os.environ,NSSOC_PHYSICAL_ROUTE_OUT=str(geomout),NSSOC_PHYSICAL_ROUTE_ODB=str(after))
  with (OUT/'geometry.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(geometry)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  r['visible_geometry']=json.loads((geomout/'physical-route-audit.json').read_text())
  assert r['routing_metrics']['values']['route__drc_errors']==0
  assert r['antenna_metrics']['values']['antenna__violating__nets']==0 and r['antenna_metrics']['values']['antenna__violating__pins']==0
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='DETAILED_ROUTE_AND_NATIVE_GEOMETRY_CHECKED_REQUIRES_EXTRACTION_TIMING_AND_SIGNOFF',sources_unchanged=True,extraction_executed=False)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
