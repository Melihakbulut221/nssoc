#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native full8074-device physical gates for actual64-driver/core assembly."""
import json,os,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-raw64-powered-physical'
TOP='nssoc_tx_full32_raw64_handoff_candidate_v1'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,steps={})
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/tx-raw64-physical-handoffs-20261020.json').read_text())
  prior,proof=reports.restore_report('tx-raw64-physical-handoffs',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',pin['selected_outputs'])
  assert prior['handoffs']['routed_count']==64 and prior['handoffs']['blocked_count']==0 and prior['sources_unchanged']
  r['source']=proof
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
  packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
  packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
  assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
  protected={p:sha(p)for p in [Path(__file__),ROOT/'scripts/generate_tx_raw64_powered_physical.py',*[OUT/'source'/n for n in pin['selected_outputs']]]}
  sys.path.insert(0,str(ROOT/'hw/soc/flow'))
  from check_pcie_rx_cell import execute
  from prepare_ihp_drc import validate_lock,verify
  from check_ihp_drc import record_result
  for typ in ('drc','lvs'):
   lock=json.loads((ROOT/f'hw/soc/pnr/ihp-{typ}.lock.json').read_text());validate_lock(lock)
   assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6'
   for row in lock['files']:
    p=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592'/row['path'];verify(p.read_bytes(),row);protected[p]=row['sha256']
  generation=execute([app,'python',ROOT/'scripts/generate_tx_raw64_powered_physical.py',OUT],OUT,'generation')
  r['generation']=generation;save()
  if generation['returncode']:print((OUT/'generation.log').read_text(errors='replace')[-12000:],flush=True)
  assert generation['returncode']==0
  r['geometry']=json.loads((OUT/'power-result.json').read_text());save()
  jobs=[('drc','layout/layout.gds',None,'deep',True),
        ('deep_lvs','layout/layout.gds','layout/schematic.cir','deep',True),
        ('flat_lvs','layout/layout.gds','layout/schematic.cir','flat',True),
        ('handoff_open','faults/handoff_open.gds','layout/schematic.cir','deep',False),
        ('body_supply_short','faults/body_supply_short.gds','layout/schematic.cir','deep',False),
        ('wrong_width','layout/layout.gds','faults/wrong_width.cir','deep',False),
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
    ok=a['status']==('PASS within comparison scope'if positive else'FAIL')and step['audit_execution']['returncode']==(0 if positive else 1)
    if positive:
     tops=[c for c in a['circuits']if c['layout']==TOP]
     ok=ok and len(tops)==1 and not a['extraction_diagnostics']and all(tops[0][k]==8074 for k in('layout_devices_recursive','schematic_devices_recursive'))
    else:ok=ok and 'Deck explicitly reported a mismatch'in a['reasons']
   step['expected_verdict_observed']=bool(ok);results.append(bool(ok));save();print(name,'expected verdict',bool(ok),flush=True)
  assert all(sha(p)==v for p,v in protected.items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
  r['sources_unchanged']=True
  r['status']='PASS_NATIVE_RAW64_CORE8074_DRC_DEEP_FLAT_LVS_AND_FAULTS_REQUIRES_FRESH_RC_FULLWAVE'if all(results)else'REJECTED_NATIVE_RAW64_CORE8074_PHYSICAL_GATES'
  save();assert all(results),'Native physical rejection preserved'
 except BaseException as e:
  if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
  r['error']=repr(e);raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
