#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud native parent replacement; retain all physical failures and old electrical evidence."""
import hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-bias-access-v27-parent'
TOP='nssoc_cdr_pd476_follower_v23'
LEAF='nssoc_rx_sampler_bias_access_layout_v27'
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
  parent_pin=json.loads((ROOT/'docs/evidence/cdr-input-access-v26-clean-parent-pass-20261021.json').read_text())
  assert parent_pin['run']==39531419538 and parent_pin['summary_sha256']=='9182d81d1edd700aa7a5884b2f29f4611e254c298ad278fa8fc6898ee77c6856'
  prior=parent_pin['report']
  assert prior['sources_unchanged']and prior['status']=='PASS_PD476_V26_CLEAN_PARENT_PHYSICAL_AND_STRICT111_COMPONENT_GRAPH_REQUIRES_FRESH_RC'
  leaves=[n for n in prior['outputs']if n=='children.json'or n.startswith('inputs/')]
  names=['layout/result.json','layout/schematic.cir','layout/'+TOP+'.gds','layout/'+TOP+'.lef']+leaves
  loaded,proof=reports.restore_report('cdr-input-access-v26-clean-parent',parent_pin['run'],
   parent_pin['summary_sha256'],parent_pin['parts_sha256'],OUT/'baseline',names)
  assert loaded==prior
  assert sha(OUT/'baseline/layout'/(TOP+'.gds'))=='c6be489346bba16ce781ff09a919618dbaf9fee17a85714149400b70b3445458'
  leaf_pin_path=ROOT/'docs/evidence/cdr-sampler-bias-access-v27-physical-pass-20261021.json'
  leaf_pin=json.loads(leaf_pin_path.read_text())
  assert leaf_pin['run']==39541838229 and leaf_pin['source_head']=='0b708c413b266e1755986c3a72aea52a4b3c8732'
  fresh=report_asset(leaf_pin['summary_asset'],leaf_pin['summary_sha256'])
  assert fresh['source_head']==leaf_pin['source_head']and fresh['sources_unchanged']
  assert fresh['status']=='PASS_BIAS_ACCESS_V27_SAMPLER54_PHYSICAL_REQUIRES_FRESH_PARENT_RC_AND_LOADED_WAVES'
  assert fresh['physical']['status']=='PASS_BIAS_ACCESS_V27_SAMPLER54_UNSIMPLIFIED_DEEP_FLAT_DRC_LEF_AND_TWENTY_FAULTS'
  fn=['layout/result.json','layout/schematic.cir','layout/'+LEAF+'.gds','layout/'+LEAF+'.lef','physical/result.json','primitive-identity.json']
  loaded,fproof=reports.restore_report('cdr-sampler-bias-access-v27-physical',leaf_pin['run'],
   leaf_pin['summary_sha256'],leaf_pin['parts_sha256'],OUT/'data',fn)
  assert loaded==fresh
  ident=json.loads((OUT/'data/primitive-identity.json').read_text())
  assert ident['unchanged_primitive_drawings']==52 and set(ident['changed_bias_resistors'])=={'BP','BN'} and len(ident['rejected'])==6
  r.update(parent_source=proof,data_source=fproof)
  for n in leaves:
   if n.startswith('inputs/sampler/'):continue
   dst=OUT/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OUT/'baseline'/n,dst)
  directory=OUT/'inputs/sampler/layout';directory.mkdir(parents=True,exist_ok=False)
  for n in ('result.json','schematic.cir',LEAF+'.gds',LEAF+'.lef'):shutil.copyfile(OUT/'data/layout'/n,directory/n)
  manifest=json.loads((OUT/'children.json').read_text())
  manifest['children']['sampler']=dict(directory='inputs/sampler/layout',
   files={str(p.relative_to(OUT)):sha(p)for p in directory.iterdir()})
  (OUT/'children.json').write_text(json.dumps(manifest,indent=2)+'\n')
  methods=[Path(__file__),leaf_pin_path,ROOT/'scripts/generate_cdr_bias_access_v27_parent.py',
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
   ('generation',[app,'python',ROOT/'scripts/generate_cdr_bias_access_v27_parent.py','--out',OUT]),
   ('child_geometry',[app,'python','-c',script,OUT]),
   ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_follower_v23_parent.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app])]:
   with(OUT/(name+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
   r[name+'_returncode']=code;save()
   if code:print((OUT/(name+'.log')).read_text()[-16000:],flush=True)
   assert code==0,(name,code)
  r['replacement']=json.loads((OUT/'replacement-proof.json').read_text())
  r['child_geometry']=json.loads((OUT/'child-geometry-proof.json').read_text())
  r['physical']=json.loads((OUT/'physical/result.json').read_text())
  assert len(r['replacement']['changed_reference_devices'])==8
  assert r['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_EIGHT_NATIVE_LEAF_DRAWINGS'
  assert len(r['child_geometry']['controls'])==3
  assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD476_DRC_LVS_AND_FAULT_CONTROLS'
  assert all(sha(Path(n))==v for n,v in protected.items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  r.update(status='PASS_PD476_BIAS_ACCESS_V27_PARENT_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES',
   sources_unchanged=True,protected_inputs=protected,scope='Eight actual BP/BN bias resistor length2.4um->0.9um changes in four samplers; all Nx4 data/hold and Nx2 selectors retained; every original parent polygon, collector/retime trunk, transform and all other children retained with exact serialized region proof. Full native DRC/LVS. Requires fresh whole-parent extraction and original complete early/late and fault waveforms.')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  for key in ('layout','physical'):
   p=OUT/key/'result.json'
   if p.exists():r[key]=json.loads(p.read_text())
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
