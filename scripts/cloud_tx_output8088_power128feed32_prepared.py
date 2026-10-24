#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare the actual8088 core plus output with unchanged full34ns gates."""
import argparse,json,os,re,resource,subprocess,sys,tarfile,time,math,shutil
from pathlib import Path
import cloud_tx_p4_drive3_builder as tree
import cloud_tx_companion_replay as engines
from cloud_tx_driver_localpins_loaded import fixtures
from cloud_tx_chunked_op import chunked_stream,assemble_op,native_pilot
from cloud_tx_stream import streaming_deck
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
PROFILE='breakpoint_tight_trap'
def main():
 p=argparse.ArgumentParser();p.add_argument('--prepare-only',action='store_true');p.add_argument('--return-rail',choices=('wide64',),default='wide64');p.add_argument('--placement-pitch',choices=('compact_columns',),default='compact_columns');p.add_argument('--physical-clock',action='store_true');p.add_argument('--first-clock-l5p7',action='store_true');p.add_argument('--mode',choices=('compact','wire'),required=True);p.add_argument('--fault',choices=('none','swap_leaf_select'),default='none');p.add_argument('--variant',choices=('budget_balanced_v5',),default='budget_balanced_v5');p.add_argument('--condition',choices=('nominal','hot_low','cold_high'),default='nominal');args=p.parse_args()
 assert args.condition=='nominal' or (args.variant=='budget_balanced_v5' and args.fault=='none')
 trim=args.variant=='budget_balanced_v5'
 tight=args.placement_pitch=='tight'
 wide64=args.return_rail=='wide64'
 assert wide64 and not tight
 assert not tight or (trim and args.physical_clock and args.first_clock_l5p7)
 counts=dict(devices=1674,R=117251,C=77892)
 assert args.physical_clock and args.first_clock_l5p7
 assert not args.physical_clock or trim
 assert not args.first_clock_l5p7 or (args.physical_clock and trim)
 clock_key='stiff625' if trim else 'stiff65'
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 assert args.prepare_only,'Actual8088 native fullwave requires a checkpointed runtime; this controller only prepares its complete deck'
 assert args.mode=='wire','Actual8088 acceptance uses its complete wire model'
 from check_tx_output8088_power128feed32_prepared_sources import check
 check()
 out=ROOT/('cloud-tx-output8088-power128feed32-prepared-'+args.mode+'-'+args.condition+'-'+args.fault);out.mkdir(exist_ok=False)
 result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],mode=args.mode,fault=args.fault,variant=args.variant,placement_pitch=args.placement_pitch,condition=args.condition,return_rail=args.return_rail,core_counts=counts,accepted=False,full_phy_accepted=False,qualified_pex=False,electrical_screen_passed=False,scope='Actual full32 physical core1674devices, all604HBT/512MOS native bounds, original34ns/256bits/three sampling phases. Wire mode includes all117251R77892C; compact mode excludes metal RC for diagnosis. External schematic CMOS/clock modulation/output frontends remain. No fullPHY/PVT/RF/substrate/mainchip acceptance.')
 def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 save()
 try:
  from check_tx_wire24_g234_evidence import validate
  result['selection_evidence']=validate(out);save()
  receipt=json.loads((ROOT/'docs/evidence'/('tx-p4-drive3-composition-pass-20261020.json'if wide64 else'tx-tree32-tight-composition-pass-20261017.json'if tight else'tx-tree32-balanced-v5-composition-pass-20261017.json'if trim else'tx-tree32-high3-composition-pass-20261017.json')).read_text());result['source']=receipt
  archive=out/'source.tar.gz';fetch(receipt['url'],receipt['sha256'],archive);assert archive.stat().st_size==receipt['bytes']
  dest=out/'source';dest.mkdir()
  with tarfile.open(archive)as tar:tar.extractall(dest,filter='data')
  archive.unlink();source=dest/('cloud-tx-p4-drive3-physical'if wide64 else'cloud-tx-tree32-tight-assembly'if tight else'cloud-tx-tree32-balanced-v5-assembly'if trim else'cloud-tx-tree32-high3-assembly')
  assert receipt['source_run']==39450330853 and receipt['source_head']=='b47b573b1f5d609409215e53a8c9c41b75b61f70'
  assert receipt['summary_sha256']=='8650e9cafe751223d45c274ffa736b5900e2120400a45ece57bd23270a809406'
  assert receipt['sha256']=='c2c710046e77004e1c622ac8c2ed21f4a4b987de6873411aca92e9fe98cd0444'
  assert sha(source/'composition-result.json')==receipt['summary_sha256']
  report=json.loads((source/'composition-result.json').read_text())
  assert report['extraction_source_sha256']==receipt['extraction_summary_sha256']=='9db11328c2adaf1c9eed1d11c1cd29a8105d1c288b1385cbb88ce851640983f1'
  assert report['outputs']==receipt['outputs'] and report['controls']['controls']==receipt['controls']
  assert report['placement_pitch']==receipt['placement_pitch']==dict(name='compact_columns',column_um=700.,row_um=600.,inverse_topology_matches_original=True)
  assert report['status']=='PASS_ACTUAL_TREE1674_SOURCE_BOUND_RC_COMPOSITION_AND_FAULTS_REQUIRES_TRANSIENT'
  assert report['variant']==args.variant and report['source_head']==receipt['source_head'] and report['composition']['counts']==counts
  if tight:
   assert report['placement_pitch']==receipt['placement_pitch']==dict(name='tight',column_um=700.,row_um=422.,inverse_topology_matches_original=True)
   result['scope']=result['scope'].replace('114819R76351C','114909R76614C')
  if wide64:
   assert report['source_head']=='b47b573b1f5d609409215e53a8c9c41b75b61f70'
   assert report['return_rail']==receipt['return_rail'] and report['return_rail']['profile']=='wide64'
   assert report['return_rail']['trunk_and_bus_width_um']==64.
   assert report['return_rail']['final_column_trunk_width_um']==128.
   assert report['return_rail']['final_column_trunk_offset_from_right_um']==340.
   assert report['geometry_delta']['status']==receipt['geometry_delta_status']=='PASS_FOUR_P4_NATIVE_MASTER_REPLACEMENTS_ALL_PINS_PARENT_ROUTES_AND_THREE_FAULTS'
   assert report['extraction_source_sha256']=='9db11328c2adaf1c9eed1d11c1cd29a8105d1c288b1385cbb88ce851640983f1'
  assert report['return_rail']['local_final_strap_width_um']==6.
  delta=report['independent_data_route_geometry']
  assert delta==receipt['independent_data_route_geometry']==report['geometry_delta']
  assert delta['candidate_gds_sha256']=='d202185d3691cd7778b8040492bab73492f44a1cfb0896c5f0b8f31350e6bdff'
  assert delta['original_master_drawings_unchanged']and delta['parent_drawings_routes_and_pins_unchanged']and delta['serialized_gds_verified']
  assert delta['reference_emitters']==863 and delta['reference_hbts']==589
  assert {q['tag']for q in delta['changes']}=={'p4_0','p4_1','p4_2','p4_3'}
  assert all(q['public_pin_rectangles_identical']and q['original_emitters']==19 and q['candidate_emitters']==55 for q in delta['changes'])
  assert len(delta['controls'])==3 and all(c['rejected']for c in delta['controls'])
  assert {c['name']for c in delta['controls']}=={'wrong_native_macro','shift_native_pins_5nm','missing_parent_metal'}
  gp=report['baseline_data_route_geometry']
  assert gp==receipt['baseline_data_route_geometry']
  assert gp['status']=='PASS_TIMING_PRIORITY_ACTUAL31_PLACEMENTS_FROZEN_CHILDREN_60_ROUTES_AND_THREE_FAULTS'
  assert gp['reference_devices_unchanged']and gp['actual_native_children_unchanged']
  assert gp['fixed_leaf_and_final_rows']==17 and gp['signal_legs']==60
  assert gp['plan']['row_lattice']['quantum_um']==600.
  assert all(abs((v-gp['plan']['original_rows_um'][k])/600.-round((v-gp['plan']['original_rows_um'][k])/600.))<1e-9 for k,v in gp['plan']['row_targets_um'].items())
  assert gp['plan']['solver']['first_mip_gap']==gp['plan']['solver']['second_mip_gap']==0.
  priority=gp['plan']['timing_priority']
  assert priority['maximum_weighted_after']<priority['maximum_weighted_before']
  assert priority['stage_maxima']['1']['after']<priority['stage_maxima']['1']['before']
  assert gp['maximum_after_um']<priority['original_maximum_ceiling_um']
  assert len(priority['regressed_legs'])==24
  assert len(report['controls']['controls'])==6
  assert {c['case']for c in report['controls']['controls']}=={'missing_contact','wrong_hbt_size','bypassed_terminal_rc','wrong_cap_reference','missing_wire_resistor','changed_wire_cap'}
  assert report['controls']['counts']==counts
  assert report['topology']['no_intermacro_ideal_alias'] and report['topology']['no_duplicate_child_rc']
  assert all(sha(source/n)==h for n,h in report['outputs'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  probe=out/'all-interfaces.json'
  with (out/'bind-interface.log').open('w')as log:
   subprocess.run(['sudo','env','-u','LD_LIBRARY_PATH',str(app),'python',str(ROOT/'scripts/bind_tx_p4_drive3_interfaces.py'),str(source),str(probe)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  interfaces=json.loads(probe.read_text());assert interfaces['status']=='PASS_ALL124_PHYSICAL_INPUT_LEGS_AND372_DATA_BASES'
  assert interfaces['references']==report['all_interface_probes']['references'] and interfaces['modes']==report['all_interface_probes']['modes']
  core=source/('binding96/tree1674-compact01.spice' if args.mode=='compact' else 'wire96/tree1674-wire01.spice')
  result['model_sha256']=sha(core);result['interfaces_sha256']=sha(probe)
  assert result['model_sha256']==receipt['model_sha256'][args.mode]
  if tight:assert result['model_sha256']==receipt['model_sha256'][args.mode]
  inputs=out/'fixtures';fixtures(inputs);engines.OUT=out;paths,provenance=engines.restore_engines();result['runtime_provenance']=provenance
  tree.FRONT=ROOT/'hw/soc/analog/pcie/tx_cmos_hv_resistive_input_v7.inc'
  if trim:
   clock_path=ROOT/'hw/soc/analog/pcie/tx_clock_common_bias_trim625_v1.spice'
   assert sha(clock_path)=='597ecb6d90aed4f6fe0ed0f425a5925cd836969cbd9502a9ebffa54ef90719ca'
   tree.CLOCK_REFERENCES[clock_key]=clock_path
   tree.CLOCK_FEEDS[clock_key]=tree.CLOCK_FEEDS['stiff65']
   result['clock_model_scope']='Fixed-trim625 schematic reference/feed. Physical clock6 RC is not composed in this bench.'
  subprocess.run([sys.executable,str(ROOT/'scripts/cloud_tx_p4_drive3_model_compare.py')],cwd=ROOT,check=True)
  from check_tx_p4_drive3_builder import check
  result['builder_binding']=check()
  deck,contract=tree.build(inputs,args.condition,fault=args.fault,clock_bias='native_res',final_drive='double_taps_margin',pre_bias='native_res_tc',output_bias='native_res',streams=32,clock_reference=clock_key,assembled_core=core,interface_probes=interfaces['modes'][args.mode],solver_profile=PROFILE)
  if args.physical_clock:
   from cloud_tx_p4_drive3_clock_adapter import adapt_clock32
   import cloud_tx_p4_drive3_clock_adapter as clock_adapter
   assert clock_adapter.tree is tree
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
    assert result['physical_clock_binding']['clock_variants']==['l5p7'if i in (0,2,3,4)else'l6p25'for i in range(11)]
    result['physical_clock_binding']['first_group_scope']='Actual l5p7 macros at fixed groups0,2,3,4; other seven groups retain l6p25. Groups2/3/4 are the only new changes; no per-corner tuning.'

   assert result['physical_clock_binding']['changed_from_original_first_only_groups']==[2,3,4]
   assert len(result['physical_clock_binding']['controls'])==55
   result['clock_source']=clock_receipt
   result['clock_model_scope']='All eleven actual six-device clock macros, each13R28C and finite body contacts. Modulation, supply, wire C reference and intermacro connections remain ideal boundaries; fullPHY/mainchip still open.'
   result['scope']=result['scope'].replace('External schematic CMOS/clock modulation/output frontends remain.','Actual eleven clock reference/feed macros included. External schematic CMOS, ideal modulation and output frontends remain.')
  assert len(contract['hbt'])==604 and len(contract['mos'])==512 and len(contract['interface_probes'])==124
  from cloud_tx_full32_rawdriver_adapter import restore_and_adapt
  driver_root=out/'raw-drivers'
  deck,contract,result['physical_driver_binding']=restore_and_adapt(driver_root,inputs,deck,contract)
  from cloud_tx_raw8074_fullwave_adapter import restore_and_adapt as whole_adapt
  whole_root=out/'whole8074'
  deck,contract,result['whole_parent_binding']=whole_adapt(whole_root,deck,contract)
  from cloud_tx_output8088_power128feed32_fullwave_adapter import restore_and_adapt as output_adapt
  output_root=out/'whole8088'
  deck,contract,result['output_parent_binding']=output_adapt(output_root,deck,contract)
  assert len(contract['hbt'])==604 and len(contract['mos'])==5376 and len(contract['interface_probes'])==124
  result['scope']=result['scope'].replace('External schematic CMOS, ideal modulation and output frontends remain.','Input CMOS layouts and local RC included; ideal differential clock modulation and output frontends remain.')+' All64 CMOS input drivers now use actual native100-device models with each260R295C; driver/core interconnect and supply boundaries still ideal. No composite fullPHY layout acceptance.'
  result['core_counts']=dict(devices=8088,R=140222,C=99906)
  result['model_sha256']=result['output_parent_binding']['model_sha256']
  result['scope']='Actual whole8088 parent including64 native input drivers, native output14 and physical driver/core/output routes with140222R99906C. Original256-bit34ns stimuli,604HBT5376MOS observations, device bounds and three sampling phases retained. External11clock macros/intermacro modulation, bias/supply feeds, RF/device-access/substrate PEX and mainchip integration remain open.'
  result['native_binding']=dict(actual_input_legs=124,actual_data_bases=372,hbt_count=604,mos_count=5376,public_data_pins=64,all_interface_probes_are_bound_terminals=True);save()
  assert contract['source_bits_sha256']=='5dd4496031f00ffea20c2af8cd828d95a868960129829389125dc5055bdb6825'
  assert len(contract['tree_plan']['nodes'])==30 and tree.BITS==256 and tree.UI==125e-12 and abs(tree.STOP-34e-9)<1e-22
  result['op_transport_control']=native_pilot(paths['patched'],out/'op-transport-control');save()
  native=out/'native';native.mkdir();streamed,op_spec=chunked_stream(deck,contract);result['op_chunk_spec']=op_spec;(native/'bench.cir').write_text(streamed);(native/'contract.json').write_text(json.dumps(contract,indent=2)+'\n');(native/'spinit').write_text('set num_threads=1\n')
  protected=[Path(__file__),ROOT/'scripts/bind_tx_p4_drive3_interfaces.py',ROOT/'scripts/run_cloud_tx_mux4.py',ROOT/'scripts/cloud_tx_p4_drive3_builder.py',ROOT/'scripts/check_tx_p4_drive3_builder.py',ROOT/'scripts/cloud_tx_stream.py',tree.FRONT,tree.TX,tree.PRE_FEED,tree.OUTPUT_FEEDS,tree.CLOCK_REFERENCES[clock_key],tree.CLOCK_FEEDS[clock_key],paths['patched'],probe,*[q for q in inputs.rglob('*')if q.is_file()],*[q for q in source.rglob('*')if q.is_file()],*native.iterdir()]
  if args.physical_clock:protected += [ROOT/'scripts/cloud_tx_tree32_clock_adapter.py',ROOT/'scripts/cloud_tx_p4_drive3_clock_adapter.py',*[q for q in clock_source.rglob('*')if q.is_file()]]
  if args.first_clock_l5p7:protected += [ROOT/'scripts/cloud_tx_tree32_firstclock.py',*[q for q in first_clock_source.rglob('*')if q.is_file()]]
  protected += [ROOT/'scripts/check_tx_wire24_g234_evidence.py',out/'selection-proof.json',out/'selection-source-summary.json',out/'selection-source.tar.gz']
  protected += [ROOT/'scripts/cloud_tx_p4_drive3_model_compare.py',ROOT/'hw/soc/out/cloud-tx-p4-drive3-model-compare/result.json',ROOT/'scripts/cloud_tx_full32_rawdriver_adapter.py',*[q for q in driver_root.rglob('*')if q.is_file()],ROOT/'scripts/cloud_tx_chunked_op.py',*[q for q in (out/'op-transport-control').rglob('*')if q.is_file()]]
  protected += [ROOT/'scripts/cloud_tx_raw8074_fullwave_adapter.py',ROOT/'scripts/check_tx_raw8074_prepared_sources.py',ROOT/'scripts/tx-raw8074-prepared-source-delta.json',*[q for q in whole_root.rglob('*')if q.is_file()]]
  protected += [ROOT/'scripts/cloud_tx_output8088_power128feed32_fullwave_adapter.py',ROOT/'scripts/check_tx_output8088_power128feed32_prepared_sources.py',ROOT/'scripts/tx-output8088-power128feed32-prepared-source-delta.json',ROOT/'docs/evidence/tx-output8088-power128feed32-interfaces-pass-20261021.json',*[q for q in output_root.rglob('*')if q.is_file()]]
  result['protected_inputs']={str(q):sha(q)for q in protected};save()
  columns=len(contract['vectors'])+1
  minimum_rows=math.ceil(tree.STOP/(contract['condition']['step_ps']*1e-12))+1
  result['capture_preflight']=dict(columns=columns,minimum_rows=minimum_rows,
   minimum_raw_payload_bytes=columns*minimum_rows*8,free_disk_bytes=shutil.disk_usage(out).free,
   retained_every_raw_mos_terminal=True,retained_every_hbt_and_original_interface=True,
   estimate_scope='Strict lower bound from maximum integration step; adaptive rows and archive space add to this. No sampling reduction.')
  if args.prepare_only:
   assert all(sha(Path(n))==v for n,v in result['protected_inputs'].items())
   result.update(status='READY_ACTUAL8088_POWER128FEED32_PHYSICAL_WIRE_DECK_NOT_SIMULATED',source_unchanged=True,simulator_checked=False)
   save();return

  raise AssertionError('Preparation-only path must return before native activation')

 except BaseException as e:
  if result['status']!='REJECTED_ACTUAL_FULL32_PHYSICAL_NATIVE_WAVEFORM':result['status']='FAIL_OR_ERROR'
  result['error']=repr(e);raise
 finally:
  result['outputs']={str(q.relative_to(out)):sha(q)for q in out.rglob('*')if q.is_file()and q!=out/'result.json'};save();print(json.dumps({k:result[k]for k in ('status','mode','fault','electrical_screen_passed')}),flush=True)
if __name__=='__main__':main()
