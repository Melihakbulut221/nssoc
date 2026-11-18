#!/usr/bin/env python3
"""Re-route verified canonical targeted ECO; estimated timing is not signoff."""
import json,os,stat,subprocess
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive,safe_path,put,current_path,restore_mapping,restore_cts,qualify_sources,fresh_corner_metrics
from cloud_core_only_clock_probe import restore_cts8
from cloud_core_only_clock_refine import restore_clock_split,restore_previous
from cloud_core_only_detailed_route import restore_refinement
OUT=ROOT/'hw/soc/out/core-only-second-setup-globalroute'
RUN=44313432783
HEAD='0090423d1f3dc1df2c9aba5bd319cb0dd3529c6d'
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
  run=completed(RUN,HEAD);z,meta=archive(run,f'core-only-second-setup-eco-{RUN}')
  assert meta['id']==14431422748 and meta['digest']=='sha256:94f4547d41cbad0d23d46598efab1a14175fca869bf86a48c5d215edecfb9ec4'
  raw=z.read('result.json');eco=json.loads(raw)
  assert eco['source_head']==HEAD and eco['sources_unchanged'] and not eco['accepted'] and not eco['timing_accepted']
  assert eco['status']=='TARGETED_BUFFER_ECO_LEGALIZED_AND_FUNCTIONALLY_CONTRACTED_REQUIRES_FRESH_ROUTING_TIMING'
  audit=eco['audit'];assert audit['upsized_buffers']==6
  for key in ['all_original_terminals_preserved','all_other_instances_geometry_preserved','pins_and_power_geometry_preserved','no_instances_added_or_removed','previous_hold_chain_unchanged','stale_routes_removed']:
   assert audit[key] is True,key
  root=ROOT/'hw/soc/out/core-only-second-setup-eco';seen=set()
  for item in z.infolist():
   if item.is_dir()or item.filename=='result.json':continue
   assert not stat.S_ISLNK(item.external_attr>>16)
   n=item.filename;assert n in eco['outputs'] and n not in seen
   put(safe_path(root,n),z.read(item),eco['outputs'][n]);seen.add(n)
  assert seen==set(eco['outputs']);root.joinpath('result.json').write_bytes(raw)
  for p,h in eco['protected_inputs'].items():assert sha(current_path(p))==h,p
  odb=root/'core-eco-placed-unrouted.odb'
  assert sha(odb)=='ec52b0c9b5bb667bde1d66175577780ea493f4ee5698f2c6ca2c61ea99490105'
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  export=OUT/'export.tcl'
  export.write_text('read_db {'+str(odb)+'}\nwrite_def {'+str(OUT/'eco.def')+'}\nwrite_verilog {'+str(OUT/'eco.v')+'}\nputs NSSOC_ECO_VIEWS_WRITTEN\n')
  with (OUT/'export.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(export)],stdout=log,stderr=subprocess.STDOUT,check=True)
  assert 'NSSOC_ECO_VIEWS_WRITTEN'in(OUT/'export.log').read_text()
  state=json.loads(initial.read_text());state.update(odb=str(odb),nl=str(OUT/'eco.v'));state['def']=str(OUT/'eco.def')
  for key in ['spef','sdf','lib','pnl']:
   if key in state:state[key]=None
  state['metrics']={};initial=OUT/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
  cfg=json.loads(config.read_text());assert cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5.0 and cfg['CLOCK_PORT']==['clk_i']
  flow=ROOT/'hw/soc/pnr/core_only_globalroute_flow.py'
  protected={str(p):sha(p)for p in [Path(__file__),flow,ROOT/'hw/soc/pnr/core_only_postcts_flow.py',ROOT/'hw/soc/pnr/interface_flow.py',ROOT/'hw/soc/flow/check_timing_derate.tcl',config,initial,odb,current_path(state['sdc']),OUT/'eco.v',OUT/'eco.def']}
  r.update(source_binding=dict(eco_run=RUN,eco_head=HEAD,artifacts=ma+ca+[cm,sm,pm]+rm+[meta]),protected_inputs=protected,eco_audit=audit,status='GLOBAL_ROUTING')
  directory=OUT/'routing';directory.mkdir()
  cmd=[str(app),'python',str(flow),'--flow','CoreOnlyGlobalRoute','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(directory),'--with-initial-state',str(initial),str(config)]
  r['command']=cmd;save()
  with (OUT/'routing.log').open('w')as log:code=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
  r['returncode']=code
  if code:raise RuntimeError('Native global route/STA failed; inspect routing.log')
  r['corners']={}
  for name,corner in [('slow','nom_slow_1p08V_125C'),('typical','nom_typ_1p20V_25C'),('fast','nom_fast_1p32V_m40C')]:
   states=list(directory.glob('*-nssoc-coreonlyrouted'+name+'/state_out.json'));assert len(states)==1,(name,states)
   metrics,path=fresh_corner_metrics(states[0],corner)
   r['corners'][name]=dict(state=str(states[0].relative_to(OUT)),corner_name=corner,metrics=metrics,metrics_source=str(path.relative_to(OUT)),metrics_sha256=sha(path))
   initial=states[0]
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='TARGETED_ECO_GLOBAL_ROUTE_MEASURED_REQUIRES_DETAILED_ROUTE_AND_EXTRACTION',sources_unchanged=True,output_state=str(initial.relative_to(OUT)))
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
