#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native8088-device physical gates for the actual core/output metal integration."""
import json,os,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
from cloud_tx_exact_external_ports import compare as compare_ports,controls as port_controls
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-output8088-power128return64-physical'
TOP='nssoc_tx_output8088_parent_v1'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,steps={})
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  # Preserve and locate both native width failures before the local metal repair.
  old,oldproof=reports.restore_report('tx-output8088-power128-physical',39608386983,
   '9d5e4b5f7e70287c89cb5d0e531268a0348083df7491bd450162a676a300bd6a',
   '95b5052eb825f2d022cc2b8624af34a41061fae1f7fd48464c28f7c8528baea0',
   OUT/'prior-width-rejection',['drc/drc.lyrdb'])
  assert old['source_head']=='eecb44cb6f2c57286bd408b2b020e3895d1120e8'
  assert old['steps']['drc']['measurement']['categories']=={"'TM2.a'":2}
  assert all(s['expected_verdict_observed']for n,s in old['steps'].items()if n!='drc')
  import xml.etree.ElementTree as ET
  tree=ET.parse(OUT/'prior-width-rejection/drc/drc.lyrdb')
  items=[ET.tostring(v,encoding='unicode')for v in tree.findall('.//items/item')]
  assert len(items)==2
  r['prior_width_rejection']=dict(source=oldproof,items=items,repair='Cover complete four-column TopMetal2 landing with6um bridge width; native cuts preserved')
  save();print('Native prior width markers:',items,flush=True)
  r['electrical_predecessor']=dict(run=39643945084,
   summary_sha256='c067f83ec3a34f0c66da85b267d0da34c69a94a2657fb47cee6574e80cba2b7e',
   status='ORIGINAL_GATES_REFUTED_BY_IMMUTABLE_POWER128_PREFIX',
   repair_hypothesis='32um TopMetal2 from actual public AVDD/AVSS pad to128um parallel trunk; requires fresh RC and full waves')
  r['return_network_diagnosis']=dict(run=39779483353,summary_sha256='c78176a0e96132c2f5c023530c5f493fe7a4e5ab5504a862317a0ac4898ba1b2',
   measured_output_effective_resistance_ohm=12.383116441782459,dominant_raw_edge='R139947',dominant_edge_ohm=11.9326,
   dominant_energy_fraction=.9636184926464064,repair_hypothesis='Add64um middle metal only on actual AVSS spans longer than80um; preserve6/32um selected-route shapes and40um wide-section endpoint access. Requires fresh physical/RC/full-wave checks.')
  r['full_return32_rejection']=dict(run=39882244224,summary_sha256='0ecc3dc388c00cc05dac72ae349db19f935e970180ea149e6bb495ceac14aa66',
   duration_ns=34.,failed_hbt=85,wrong_output_samples=14,full_phy_accepted=False,
   scope='The64um candidate targets output-return resistance only. It does not claim to repair the82 selector and2 final-tail failures or the full serial PHY.')
  r['external_port_controls']={str(n):port_controls(expected_count=n) for n in (163,165)};save()
  inputs=[
   ('tx-raw64-powered-physical',39466552523,'f5fcdbdee650f3c7868e671a9a05b0f3a7db3c78a0be76fe4afb828a1cd73d53','2a3431b7a2cae61f6b9edcbce8edeef23963bc62c170332064a5ab779ac58404','core',['layout/layout.gds','layout/schematic.cir','power-result.json','source/handoff-result.json']),
   ('tx-output14-physical',39564026768,'8f434b1368bcf613ca2f32c4eeebc528d3e131a243299bf6df09f609c293f9fa','82076d156f767b5c9caf35f9fea9f13e7953022abec73f6814bb473c1de452c4','output',['layout/nssoc_tx_cml_layout.gds','layout/schematic.cir','layout/result.json'])]
  source_files={};loaded={}
  for group,run,summary,parts,folder,names in inputs:
   prior,proof=reports.restore_report(group,run,summary,parts,OUT/folder,names)
   assert prior['sources_unchanged']and prior['status'].startswith('PASS_')
   loaded[folder]=prior;r.setdefault('sources',{})[folder]=proof
   source_files.update({OUT/folder/n:prior['outputs'][n]for n in names});save()
  assert loaded['core']['status']=='PASS_NATIVE_RAW64_CORE8074_DRC_DEEP_FLAT_LVS_AND_FAULTS_REQUIRES_FRESH_RC_FULLWAVE'
  assert loaded['output']['status']=='PASS_ACTUAL_TX_OUTPUT14_NATIVE_PHYSICAL_AND_PARENT_ENDPOINT_BINDING_REQUIRES_FRESH_RC_AND_PARENT_ROUTE'
  assert all(step['expected_verdict_observed']for step in loaded['core']['steps'].values())
  assert loaded['core']['geometry']['reference_devices']==8074
  assert sha(OUT/'output/layout/nssoc_tx_cml_layout.gds')=='e3502ee90dae5af99e7ab03ef443197f84c71613189703e8a4b112db77053ef5'
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
  packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
  packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
  assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
  protected={p:sha(p)for p in [Path(__file__),ROOT/'scripts/generate_tx_output8088_power128return64_parent.py',ROOT/'scripts/cloud_tx_exact_external_ports.py']};protected.update(source_files)
  sys.path.insert(0,str(ROOT/'hw/soc/flow'))
  from check_pcie_rx_cell import execute
  from prepare_ihp_drc import validate_lock,verify
  from check_ihp_drc import record_result
  for typ in ('drc','lvs'):
   lock=json.loads((ROOT/f'hw/soc/pnr/ihp-{typ}.lock.json').read_text());validate_lock(lock)
   assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6'
   for row in lock['files']:
    p=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592'/row['path'];verify(p.read_bytes(),row);protected[p]=row['sha256']
  generation=execute([app,'python',ROOT/'scripts/generate_tx_output8088_power128return64_parent.py',OUT],OUT,'generation')
  r['generation']=generation;save()
  if generation['returncode']:print((OUT/'generation.log').read_text(errors='replace')[-12000:],flush=True)
  assert generation['returncode']==0
  r['geometry']=json.loads((OUT/'integration-result.json').read_text());save()
  jobs=[('drc','layout/layout.gds',None,'deep',True),
        ('deep_lvs','layout/layout.gds','layout/schematic.cir','deep',True),
        ('flat_lvs','layout/layout.gds','layout/schematic.cir','flat',True),
        ('handoff_open','faults/handoff_open.gds','layout/schematic.cir','deep',False),
        ('output_return_open','faults/output_return_open.gds','layout/schematic.cir','deep',False),
        ('body_supply_short','faults/body_supply_short.gds','layout/schematic.cir','deep',False),
        ('wrong_width','layout/layout.gds','faults/wrong_width.cir','deep',False),
        ('internal_port_alias','faults/internal_port_alias.gds','layout/schematic.cir','flat',False),
        ('wrong_output_Nx','layout/layout.gds','faults/wrong_output_Nx.cir','deep',False),
        ('swap_output_inputs','layout/layout.gds','faults/swap_output_inputs.cir','deep',False),
        ('offgrid','faults/offgrid.gds',None,'deep',False)]
  results=[]
  for name,geometry,reference,mode,positive in jobs:
   d=OUT/name;d.mkdir();drc=reference is None;typ='drc'if drc else'lvs'
   entry=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592/ihp-sg13g2/libs.tech/klayout/tech'/('drc/ihp-sg13g2.drc'if drc else'lvs/sg13g2.lvs')
   options=['input='+str(OUT/geometry),'topcell='+TOP,'log='+str(d/'deck.log'),'run_mode='+mode]
   options+=['report='+str(d/'drc.lyrdb'),'threads=2','no_recommended=False','precheck_drc=False']if drc else[
    'schematic='+str(OUT/reference),'report='+str(d/'result.lvsdb'),'target_netlist='+str(d/'extracted.cir'),'thr=2','no_simplify=true','top_lvl_pins=true','combine_devices=false']
   cmd=[app,'klayout','-b','-zz','-r',entry]
   for op in options:cmd+=['-rd',op]
   step=dict(execution=execute(cmd,d,'run'),positive=positive,mode=mode,combine_devices=False);r['steps'][name]=step;save()
   assert step['execution']['returncode']==0,('Native deck execution failed',name)
   if drc:
    step['measurement']=record_result(d,TOP,0,protected);v=step['measurement']
    ok=v['category_count']==560 and v['status']==('PASS'if positive else'FAIL')
    if not positive:ok=ok and any('Offgrid'in c for c in v['categories'])
   else:
    step['audit_execution']=execute([app,'python',ROOT/'hw/soc/flow/audit_klayout_lvs.py',d/'result.lvsdb','--top',TOP,'--deck-log',d/'deck.log','--output',d/'audit.json'],d,'audit')
    a=json.loads((d/'audit.json').read_text());step['audit']=a
    step['external_ports']=compare_ports((OUT/'layout/schematic.cir').read_text(),(d/'extracted.cir').read_text(),TOP,expected_count=165)
    ok=a['status']==('PASS within comparison scope'if positive else'FAIL')and step['audit_execution']['returncode']==(0 if positive else 1)
    if positive:
     tops=[c for c in a['circuits']if c['layout']==TOP]
     ok=ok and len(tops)==1 and not a['extraction_diagnostics']and all(tops[0][k]==8088 for k in('layout_devices_recursive','schematic_devices_recursive'))
    else:ok=ok and 'Deck explicitly reported a mismatch'in a['reasons']
    if positive:ok=ok and step['external_ports']['passed']
    if name=='internal_port_alias':
     # Native circuit matching tolerates this extra port. Preserve that result,
     # and require the stronger explicit external-interface contract to reject it.
     step['native_circuit_comparison_passed']=a['status']=='PASS within comparison scope'
     ok=(not step['external_ports']['passed']and step['external_ports'].get('actual_count')==166
      and step['external_ports'].get('extra')==['MP']and not step['external_ports'].get('missing')
      and step['native_circuit_comparison_passed']and not a['extraction_diagnostics'])
     step['fault_rejection_gate']='EXACT_EXTERNAL_INTERFACE_165_NAMES'
   step['expected_verdict_observed']=bool(ok);results.append(bool(ok));save();print(name,'expected verdict',bool(ok),flush=True)
  assert all(sha(p)==v for p,v in protected.items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
  r['sources_unchanged']=True
  r['status']='PASS_ACTUAL_TX_OUTPUT8088_POWER128RETURN64_PARENT_DRC_DEEP_FLAT_LVS_AND_FAULTS_REQUIRES_FRESH_RC_FULLWAVE'if all(results)else'REJECTED_ACTUAL_TX_OUTPUT8088_POWER128RETURN64_PARENT_PHYSICAL_GATES'
  save();assert all(results),'Native physical rejection preserved'
 except BaseException as e:
  if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
  r['error']=repr(e);raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
