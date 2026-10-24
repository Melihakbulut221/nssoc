#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud native parent replacement; retain all physical failures and old electrical evidence."""
import hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-selector-v19-parent'
TOP='nssoc_cdr_pd484_localbus_v12'
LEAF='nssoc_rx_sampler_selector_layout_v19'
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
  prior=report_asset(658459671,'9d7300c3965d2a9487882e1a569cf17c5328acc130bbf2dc0ee9c993e0c210d3')
  assert prior['source_head']=='6fae6cae4e8242e3436fe8873b5e42bed7e112be'and prior['sources_unchanged']
  assert prior['status']=='PASS_PD484_V16_BAND_REORDER_PHYSICAL_REQUIRES_FRESH_FULL_RC_AND_ORIGINAL_LOADED_GATES'
  leaves=[n for n in prior['outputs']if n=='children.json'or n.startswith('inputs/')]
  names=['layout/result.json','layout/schematic.cir','layout/'+TOP+'.gds','layout/'+TOP+'.lef']+leaves
  loaded,proof=reports.restore_report('cdr-retime-band-reorder',39379285294,
   '9d7300c3965d2a9487882e1a569cf17c5328acc130bbf2dc0ee9c993e0c210d3',
   'b58458f2193418c85cfb1ea89a1716749f5028b2b5ce58558524b1b097f1bdb3',OUT/'baseline',names)
  assert loaded==prior
  assert sha(OUT/'baseline/layout'/(TOP+'.gds'))=='27321a65507bccd81228e05933676158794b3c099186535fd4f9b892afacb37e'
  fresh=report_asset(658706341,'aeb0b6a953f21c68caa1cf46503a60d9ac4e0583305a9d021bff6df765c750a3')
  assert fresh['source_head']=='2ffc2ae6dc2f9f1cf1fa9d4b6a57b3717760ac2f'and fresh['sources_unchanged']
  assert fresh['status']=='PASS_SELECTOR4_SAMPLER54_PHYSICAL_REQUIRES_FRESH_PARENT_RC_AND_LOADED_WAVES'
  assert fresh['physical']['status']=='PASS_SELECTOR4_SAMPLER54_UNSIMPLIFIED_DEEP_FLAT_DRC_LEF_AND_SEVENTEEN_FAULTS'
  fn=['layout/result.json','layout/schematic.cir','layout/'+LEAF+'.gds','layout/'+LEAF+'.lef','physical/result.json','primitive-identity.json']
  loaded,fproof=reports.restore_report('cdr-sampler-selector-v19-physical',39391984326,
   'aeb0b6a953f21c68caa1cf46503a60d9ac4e0583305a9d021bff6df765c750a3',
   '4d6b6e895846c33d807639086729e908c3d2ea7fe846149d95aaf0941261a565',OUT/'selector',fn)
  assert loaded==fresh
  ident=json.loads((OUT/'selector/primitive-identity.json').read_text())
  assert ident['unchanged_primitive_drawings']==46 and len(ident['changed_selectors'])==8 and len(ident['rejected'])==4
  r.update(parent_source=proof,selector_source=fproof)
  for n in leaves:
   if n.startswith('inputs/sampler/'):continue
   dst=OUT/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OUT/'baseline'/n,dst)
  directory=OUT/'inputs/sampler/layout';directory.mkdir(parents=True,exist_ok=False)
  for n in ('result.json','schematic.cir',LEAF+'.gds',LEAF+'.lef'):shutil.copyfile(OUT/'selector/layout'/n,directory/n)
  manifest=json.loads((OUT/'children.json').read_text())
  manifest['children']['sampler']=dict(directory='inputs/sampler/layout',
   files={str(p.relative_to(OUT)):sha(p)for p in directory.iterdir()})
  (OUT/'children.json').write_text(json.dumps(manifest,indent=2)+'\n')
  methods=[Path(__file__),ROOT/'scripts/generate_cdr_selector_v19_parent.py',
   ROOT/'scripts/check_cdr_localbus_v12_parent_geometry.py',ROOT/'hw/soc/flow/check_pcie_cdr_retimed_localbus_v12_parent.py']
  protected={str(p):sha(p)for p in [*methods,*[OUT/'baseline'/n for n in names],*[OUT/'selector'/n for n in fn]]}
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
  packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
  packed.unlink();runtime=json.loads((ROOT/'manifest.json').read_text())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
  r['runtime_sha256']=sha(app);save()
  script="import sys,json;from pathlib import Path;sys.path.insert(0,'scripts');from check_cdr_localbus_v12_parent_geometry import check;p=Path(sys.argv[1]);(p/'child-geometry-proof.json').write_text(json.dumps(check(p),indent=2)+'\\n')"
  for name,cmd in [
   ('generation',[app,'python',ROOT/'scripts/generate_cdr_selector_v19_parent.py','--out',OUT]),
   ('child_geometry',[app,'python','-c',script,OUT]),
   ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_retimed_localbus_v12_parent.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app])]:
   with(OUT/(name+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
   r[name+'_returncode']=code;save()
   if code:print((OUT/(name+'.log')).read_text()[-16000:],flush=True)
   assert code==0,(name,code)
  r['replacement']=json.loads((OUT/'replacement-proof.json').read_text())
  r['child_geometry']=json.loads((OUT/'child-geometry-proof.json').read_text())
  r['physical']=json.loads((OUT/'physical/result.json').read_text())
  assert len(r['replacement']['changed_reference_devices'])==32
  assert r['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_EIGHT_NATIVE_LEAF_DRAWINGS'
  assert len(r['child_geometry']['controls'])==3
  assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD484_DRC_LVS_AND_FAULT_CONTROLS'
  assert all(sha(Path(n))==v for n,v in protected.items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  r.update(status='PASS_PD484_SELECTOR4_PARENT_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES',
   sources_unchanged=True,protected_inputs=protected,scope='32 actual native selector changes in four samplers; original parent metal/transforms and all other children retained. Full native DRC/LVS. Requires fresh whole-parent extraction and original complete early/late and fault waveforms.')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  for key in ('layout','physical'):
   p=OUT/key/'result.json'
   if p.exists():r[key]=json.loads(p.read_text())
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
