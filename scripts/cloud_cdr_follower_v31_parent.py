#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud native parent replacement; retain all physical failures and old electrical evidence."""
import hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-follower-v31-parent'
TOP='nssoc_cdr_pd476_follower_v23'
# Leaf keeps the serialized top name used by the actual verified v30 run.
LEAF='nssoc_cdr_retime_follower_layout_v23'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
  closed_loop=False,qualified_pex=False,main_chip_integrated=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def report_asset(number,digest):
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(number),'-H','Accept: application/octet-stream'])
  assert hashlib.sha256(raw).hexdigest()==digest
  return json.loads(raw)
 save()
 try:
  parent_pin=json.loads((ROOT/'docs/evidence/cdr-input-impedance-v30-parent-physical-pass-20261022.json').read_text())
  assert parent_pin['run']==39706018326 and parent_pin['summary_sha256']=='c73830e98e87cbee1d1287c658dd29504e6a04275067b90bea7bd6dfbb4e9ae6'
  prior=parent_pin['report']
  assert prior['sources_unchanged']and prior['status']=='PASS_PD476_INPUT_IMPEDANCE_V30_PARENT_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES'
  leaves=[n for n in prior['outputs']if n=='children.json'or n.startswith('inputs/')]
  names=['layout/result.json','layout/schematic.cir','layout/'+TOP+'.gds','layout/'+TOP+'.lef']+leaves
  loaded,proof=reports.restore_report('cdr-input-impedance-v30-parent',parent_pin['run'],
   parent_pin['summary_sha256'],parent_pin['parts_sha256'],OUT/'baseline',names)
  assert loaded==prior
  assert sha(OUT/'baseline/layout'/(TOP+'.gds'))=='49914cacf6d66660c7e0373c8a60ce59e0b389c5c86b538daa54a2062324ea42'
  leaf_pin_path=ROOT/'docs/evidence/cdr-follower-v31-physical-pass-20261022.json'
  leaf_pin=json.loads(leaf_pin_path.read_text())
  assert leaf_pin['run']==39717037237 and leaf_pin['source_head']=='9b8c43b1c910765387d7abc83d482c3347333067'
  fresh=report_asset(leaf_pin['summary_asset'],leaf_pin['summary_sha256'])
  assert fresh['source_head']==leaf_pin['source_head']and fresh['sources_unchanged']
  assert fresh['status']=='PASS_CDR_FOLLOWER_V31_LEAF_PHYSICAL_REQUIRES_PARENT_RC_AND_LOADED_WAVES'
  assert fresh['physical']['status']=='PASS_NATIVE_PDK_CDR_FOLLOWER8_DRC_LVS_AND_SEVEN_FAULT_CONTROLS'
  fn=['layout/result.json','layout/schematic.cir','layout/'+LEAF+'.gds','layout/'+LEAF+'.lef','physical/result.json']
  loaded,fproof=reports.restore_report('cdr-follower-v31-physical',leaf_pin['run'],
   leaf_pin['summary_sha256'],leaf_pin['parts_sha256'],OUT/'data',fn)
  assert loaded==fresh
  r.update(parent_source=proof,data_source=fproof)
  for n in leaves:
   if n.startswith('inputs/rc_retime/'):continue
   dst=OUT/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OUT/'baseline'/n,dst)
  directory=OUT/'inputs/rc_retime/layout';directory.mkdir(parents=True,exist_ok=False)
  for n in ('result.json','schematic.cir',LEAF+'.gds',LEAF+'.lef'):shutil.copyfile(OUT/'data/layout'/n,directory/n)
  manifest=json.loads((OUT/'children.json').read_text())
  manifest['children']['rc_retime']=dict(directory='inputs/rc_retime/layout',
   files={str(p.relative_to(OUT)):sha(p)for p in directory.iterdir()})
  (OUT/'children.json').write_text(json.dumps(manifest,indent=2)+'\n')
  methods=[Path(__file__),leaf_pin_path,ROOT/'scripts/generate_cdr_follower_v31_parent.py',
   ROOT/'scripts/check_cdr_follower_v23_parent_geometry.py',ROOT/'hw/soc/flow/check_pcie_cdr_follower_v23_parent.py']
  protected={str(p):sha(p)for p in [*methods,*[OUT/'baseline'/n for n in names],*[OUT/'data'/n for n in fn]]}
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
  packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
  packed.unlink();runtime=json.loads((ROOT/'manifest.json').read_text())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
  r['runtime_sha256']=sha(app);save()
  script="import sys,json;from pathlib import Path;sys.path.insert(0,'scripts');from check_cdr_follower_v23_parent_geometry import check;p=Path(sys.argv[1]);(p/'child-geometry-proof.json').write_text(json.dumps(check(p),indent=2)+'\\n')"
  for name,cmd in [
   ('generation',[app,'python',ROOT/'scripts/generate_cdr_follower_v31_parent.py','--out',OUT]),
   ('child_geometry',[app,'python','-c',script,OUT]),
   ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_follower_v23_parent.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app])]:
   with(OUT/(name+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
   r[name+'_returncode']=code;save()
   if code:print((OUT/(name+'.log')).read_text()[-16000:],flush=True)
   assert code==0,(name,code)
  r['replacement']=json.loads((OUT/'replacement-proof.json').read_text())
  r['child_geometry']=json.loads((OUT/'child-geometry-proof.json').read_text())
  r['physical']=json.loads((OUT/'physical/result.json').read_text())
  assert len(r['replacement']['changed_reference_devices'])==4 and r['replacement']['parent_geometry_unchanged']
  assert r['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_EIGHT_NATIVE_LEAF_DRAWINGS'
  assert len(r['child_geometry']['controls'])==3
  assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD476_DRC_LVS_AND_FAULT_CONTROLS'
  assert all(sha(Path(n))==v for n,v in protected.items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  r.update(status='PASS_PD476_FOLLOWER_SINK_V31_PARENT_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES',
   sources_unchanged=True,protected_inputs=protected,scope='Four actual follower pull-down resistor lengths4.5um->2.25um in ac/bd only; all fourNx4 follower HBTs, v30samplers and every other device retained. Every original parent polygon, label, transform, collector/retime trunk, historical M4 fill and other child retained. Full native DRC/LVS. Requires fresh whole-parent extraction and original complete early/late and fault waveforms.')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  for key in ('layout','physical'):
   p=OUT/key/'result.json'
   if p.exists():r[key]=json.loads(p.read_text())
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
