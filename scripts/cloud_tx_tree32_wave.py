#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Full native32:1 waveform from actual1674-device GDS and parent RC."""
import argparse,json,os,re,resource,subprocess,tarfile,time
from pathlib import Path
import run_cloud_tx_mux4 as tree
import cloud_tx_companion_replay as engines
from cloud_tx_driver_localpins_loaded import fixtures
from cloud_tx_stream import streaming_deck
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
PROFILE='breakpoint_tight_trap'
def main():
 p=argparse.ArgumentParser();p.add_argument('--return-rail',choices=('original','wide64'),default='original');p.add_argument('--placement-pitch',choices=('original','tight'),default='original');p.add_argument('--physical-clock',action='store_true');p.add_argument('--first-clock-l5p7',action='store_true');p.add_argument('--mode',choices=('compact','wire'),required=True);p.add_argument('--fault',choices=('none','swap_leaf_select'),default='none');p.add_argument('--variant',choices=('budget_high3','budget_high3_trim'),default='budget_high3');p.add_argument('--condition',choices=('nominal','hot_low','cold_high'),default='nominal');args=p.parse_args()
 assert args.condition=='nominal' or (args.variant=='budget_high3_trim' and args.fault=='none')
 trim=args.variant=='budget_high3_trim'
 tight=args.placement_pitch=='tight'
 wide64=args.return_rail=='wide64'
 assert not wide64 or tight
 assert not tight or (trim and args.physical_clock and args.first_clock_l5p7)
 counts=dict(devices=1674,R=114909,C=76614)if tight else dict(devices=1674,R=114819,C=76351)
 assert not args.physical_clock or trim
 assert not args.first_clock_l5p7 or (args.physical_clock and trim)
 clock_key='stiff625' if trim else 'stiff65'
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 out=ROOT/((('cloud-tx-tree32-return64-wave-'if wide64 else'cloud-tx-tree32-tight-wave-'if tight else'cloud-tx-tree32-firstclock-wave-'if args.first_clock_l5p7 else'cloud-tx-tree32-clock-wire-wave-'if args.physical_clock else'cloud-tx-tree32-headroom-wave-')+args.mode+'-'+args.condition+'-'+args.fault)if trim else('cloud-tx-tree32-physical-wave-'+args.mode+'-'+args.fault));out.mkdir(exist_ok=False)
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],mode=args.mode,fault=args.fault,variant=args.variant,placement_pitch=args.placement_pitch,condition=args.condition,return_rail=args.return_rail,core_counts=counts,accepted=False,full_phy_accepted=False,qualified_pex=False,electrical_screen_passed=False,scope='Actual full32 physical core1674devices, all604HBT/512MOS native bounds, original34ns/256bits/three sampling phases. Wire mode includes all114819R76351C; compact mode excludes metal RC for diagnosis. External schematic CMOS/clock modulation/output frontends remain. No fullPHY/PVT/RF/substrate/mainchip acceptance.')
 def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  receipt=json.loads((ROOT/'docs/evidence'/('tx-tree32-return64-composition-pass-20261017.json'if wide64 else'tx-tree32-tight-composition-pass-20261017.json'if tight else'tx-tree32-headroom-composition-pass-20261017.json'if trim else'tx-tree32-high3-composition-pass-20261017.json')).read_text());result['source']=receipt
  archive=out/'source.tar.gz';fetch(receipt['url'],receipt['sha256'],archive);assert archive.stat().st_size==receipt['bytes']
  dest=out/'source';dest.mkdir()
  with tarfile.open(archive)as tar:tar.extractall(dest,filter='data')
  archive.unlink();source=dest/('cloud-tx-tree32-return64-assembly'if wide64 else'cloud-tx-tree32-tight-assembly'if tight else'cloud-tx-tree32-headroom-assembly'if trim else'cloud-tx-tree32-high3-assembly')
  assert sha(source/'composition-result.json')==receipt['summary_sha256']
  report=json.loads((source/'composition-result.json').read_text())
  assert report['status']=='PASS_ACTUAL_TREE1674_SOURCE_BOUND_RC_COMPOSITION_AND_FAULTS_REQUIRES_TRANSIENT'
  assert report['variant']==args.variant and report['source_head']==receipt['source_head'] and report['composition']['counts']==counts
  if tight:
   assert report['placement_pitch']==receipt['placement_pitch']==dict(name='tight',column_um=700.,row_um=422.,inverse_topology_matches_original=True)
   result['scope']=result['scope'].replace('114819R76351C','114909R76614C')
  if wide64:
   assert report['source_head']=='086401ca1c58c652a7114d4ebb1b9cd990c075bd'
   assert report['return_rail']==receipt['return_rail'] and report['return_rail']['profile']=='wide64'
   assert report['return_rail']['trunk_and_bus_width_um']==64.
   assert report['geometry_delta']['status']==receipt['geometry_delta_status']=='PASS_EXACT_SIX_AVSS_EXPANSIONS_ALL_OTHER_DRAWING_GEOMETRY_UNCHANGED'
   assert report['extraction_source_sha256']=='b3aaa9993a1136dfc0716f19832f407420a54ba3d89f0c92f931b14463b17b53'
  assert len(report['controls']['controls'])==6
  assert {c['case']for c in report['controls']['controls']}=={'missing_contact','wrong_hbt_size','bypassed_terminal_rc','wrong_cap_reference','missing_wire_resistor','changed_wire_cap'}
  assert report['controls']['counts']==counts
  assert report['topology']['no_intermacro_ideal_alias'] and report['topology']['no_duplicate_child_rc']
  assert all(sha(source/n)==h for n,h in report['outputs'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  probe=out/'all-interfaces.json'
  with (out/'bind-interface.log').open('w')as log:
   subprocess.run(['sudo','env','-u','LD_LIBRARY_PATH',str(app),'python',str(ROOT/'scripts/bind_tx_tree32_interfaces.py'),str(source),str(probe)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  interfaces=json.loads(probe.read_text());assert interfaces['status']=='PASS_ALL124_PHYSICAL_INPUT_LEGS_AND372_DATA_BASES'
  core=source/('binding96/tree1674-compact01.spice' if args.mode=='compact' else 'wire96/tree1674-wire01.spice')
  result['model_sha256']=sha(core);result['interfaces_sha256']=sha(probe)
  if tight:assert result['model_sha256']==receipt['model_sha256'][args.mode]
  inputs=out/'fixtures';fixtures(inputs);engines.OUT=out;paths,provenance=engines.restore_engines();result['runtime_provenance']=provenance
  tree.FRONT=ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc'
  if trim:
   clock_path=ROOT/'hw/soc/analog/pcie/tx_clock_common_bias_trim625_v1.spice'
   assert sha(clock_path)=='597ecb6d90aed4f6fe0ed0f425a5925cd836969cbd9502a9ebffa54ef90719ca'
   tree.CLOCK_REFERENCES[clock_key]=clock_path
   tree.CLOCK_FEEDS[clock_key]=tree.CLOCK_FEEDS['stiff65']
   result['clock_model_scope']='Fixed-trim625 schematic reference/feed. Physical clock6 RC is not composed in this bench.'
  deck,contract=tree.build(inputs,args.condition,fault=args.fault,clock_bias='native_res',final_drive='double_taps_margin',pre_bias='native_res_tc',output_bias='native_res',streams=32,clock_reference=clock_key,assembled_core=core,interface_probes=interfaces['modes'][args.mode],solver_profile=PROFILE)
  if args.physical_clock:
   from cloud_tx_tree32_clock_adapter import adapt_clock32
   clock_receipt=json.loads((ROOT/'docs/evidence/tx-clock-headroom-composition-pass-20261017.json').read_text())
   clock_archive=out/'clock-source.tar.gz';fetch(clock_receipt['url'],clock_receipt['sha256'],clock_archive)
   assert clock_archive.stat().st_size==clock_receipt['bytes']
   clock_dest=out/'clock-source';clock_dest.mkdir()
   with tarfile.open(clock_archive)as tar:tar.extractall(clock_dest,filter='data')
   clock_archive.unlink();clock_source=clock_dest/'cloud-tx-clock-reference-compose-l6p25'
   assert sha(clock_source/'result.json')==clock_receipt['summary_sha256']
   cp=json.loads((clock_source/'result.json').read_text())
   assert cp['source_head']==clock_receipt['source_head'] and cp['variant']=='l6p25'and cp['source_unchanged']
   assert cp['status']=='PASS_RAW6_AND_ALL13R28C_EXACT_CLOCK_COMPOSITION_WITH11_FAULTS_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
   assert len(cp['controls'])==11 and all(c['rejected']for c in cp['controls'])
   assert all(sha(clock_source/n)==h for n,h in cp['outputs'].items())
   clock_model=clock_source/'clock6-wire.spice';assert sha(clock_model)==cp['model_sha256']==clock_receipt['model_sha256']
   for name in ('resistors_mod.lib','sg13g2_hbt_mod.lib'):
    assert sha(inputs/'models'/name)==sha(clock_source/'inputs/tx-clock-reference-intrinsic-l6p25/pdk/libs.tech/ngspice/models'/name)
   (out/'schematic-clock-bench.cir').write_text(deck)
   first_clock_model=None
   if args.first_clock_l5p7:
    from cloud_tx_tree32_firstclock import restore
    first_clock_model,first_clock_source,result['first_clock_source']=restore(out,inputs)
   deck,contract,result['physical_clock_binding']=adapt_clock32(deck,contract,clock_model,first_clock_model)
   if args.first_clock_l5p7:
    assert result['physical_clock_binding']['clock_variants']==['l5p7']+['l6p25']*10
    result['physical_clock_binding']['first_group_scope']='Actual l5p7 macro replaces shared sa/sb/s reference only; all other ten groups retain l6p25. No per-corner tuning.'

   result['clock_source']=clock_receipt
   result['clock_model_scope']='All eleven actual six-device clock macros, each13R28C and finite body contacts. Modulation, supply, wire C reference and intermacro connections remain ideal boundaries; fullPHY/mainchip still open.'
   result['scope']=result['scope'].replace('External schematic CMOS/clock modulation/output frontends remain.','Actual eleven clock reference/feed macros included. External schematic CMOS, ideal modulation and output frontends remain.')
  assert len(contract['hbt'])==604 and len(contract['mos'])==512 and len(contract['interface_probes'])==124
  result['native_binding']=dict(actual_input_legs=124,actual_data_bases=372,hbt_count=604,mos_count=512,public_data_pins=64,all_interface_probes_are_bound_terminals=True);save()
  assert contract['source_bits_sha256']=='5dd4496031f00ffea20c2af8cd828d95a868960129829389125dc5055bdb6825'
  assert len(contract['tree_plan']['nodes'])==30 and tree.BITS==256 and tree.UI==125e-12 and abs(tree.STOP-34e-9)<1e-22
  native=out/'native';native.mkdir();(native/'bench.cir').write_text(streaming_deck(deck,contract));(native/'contract.json').write_text(json.dumps(contract,indent=2)+'\n');(native/'spinit').write_text('set num_threads=1\n')
  protected=[Path(__file__),ROOT/'scripts/bind_tx_tree32_interfaces.py',ROOT/'scripts/run_cloud_tx_mux4.py',ROOT/'scripts/cloud_tx_stream.py',tree.FRONT,tree.TX,tree.PRE_FEED,tree.OUTPUT_FEEDS,tree.CLOCK_REFERENCES[clock_key],tree.CLOCK_FEEDS[clock_key],paths['patched'],probe,*[q for q in inputs.rglob('*')if q.is_file()],*[q for q in source.rglob('*')if q.is_file()],*native.iterdir()]
  if args.physical_clock:protected += [ROOT/'scripts/cloud_tx_tree32_clock_adapter.py',*[q for q in clock_source.rglob('*')if q.is_file()]]
  if args.first_clock_l5p7:protected += [ROOT/'scripts/cloud_tx_tree32_firstclock.py',*[q for q in first_clock_source.rglob('*')if q.is_file()]]
  result['protected_inputs']={str(q):sha(q)for q in protected};save()
  def limits():
   resource.setrlimit(resource.RLIMIT_AS,(12*1024**3,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
  env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(native),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
  start=time.monotonic()
  with (native/'run.log').open('w')as log:rc=subprocess.call([str(paths['patched']),'-n','-b','bench.cir'],cwd=native,env=env,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT)
  result.update(returncode=rc,elapsed_s=time.monotonic()-start);save();assert rc==0,'Native simulation failed'
  text=(native/'run.log').read_text(errors='replace');result['solver_options']=tree.verify_solver_options(text,PROFILE);result['diagnostics']=tree.native_diagnostics(text,PROFILE)
  flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
  assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in contract['hbt']]
  assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',body)==['1']for _,body in flags)
  result['native_off_flags_count']=len(flags);result['review']=tree.review(native,contract)
  assert set(result['review']['interfaces'])=={'cmos','final','level_4','level_8','level_16'}
  assert all(v['samples']==6912 for v in result['review']['interfaces'].values()) if args.mode=='wire' else all(v['samples']==768 for v in result['review']['interfaces'].values())
  assert all(sha(Path(n))==h for n,h in result['protected_inputs'].items());result['source_unchanged']=True
  result['electrical_screen_passed']=args.fault=='none' and result['review']['all_engineering_gates_passed'] and not result['diagnostics']
  if args.fault!='none':
   result['actual_leaf_fault_rejected_by_original_bits']=not result['review']['signals']['passed']
   assert result['actual_leaf_fault_rejected_by_original_bits']
  result['status']='COMPLETE_ACTUAL_FULL32_PHYSICAL_NATIVE_WAVEFORM_NOT_PHY_ACCEPTANCE'
 except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  result['outputs']={str(q.relative_to(out)):sha(q)for q in out.rglob('*')if q.is_file()and q!=out/'result.json'};save();print(json.dumps({k:result[k]for k in ('status','mode','fault','electrical_screen_passed')}),flush=True)
if __name__=='__main__':main()
