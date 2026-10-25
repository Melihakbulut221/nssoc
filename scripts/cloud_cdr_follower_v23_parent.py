#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only replacement of both v22 retime leaves with native active followers."""
import hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-follower-v23-parent'
TOP='nssoc_cdr_pd476_follower_v23'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,main_chip_integrated=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/cdr-follower-v23-leaf-physical-pass-20261020.json').read_text())
  assert pin['run']==39470863624 and pin['summary_sha256']=='2bc7414412c4d8580bb0c72878416a4190ca60a4e76209641329861e012574f1'
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/659813164','-H','Accept: application/octet-stream'])
  assert hashlib.sha256(raw).hexdigest()=='0425f0b6cbfdae35240d2e99a0faea3f75b114f2e4974639d804556a36ccb266';prior=json.loads(raw)
  assert prior['status']=='PASS_PD484_RETIME_TRUNKS_V22_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES'
  names=[n for n in prior['outputs']if n=='children.json'or n.startswith('inputs/')or n.startswith('layout/')]
  loaded,proof=reports.restore_report('cdr-retime-trunks-v22-parent',39454675485,'0425f0b6cbfdae35240d2e99a0faea3f75b114f2e4974639d804556a36ccb266','bdf63f2c67dc97827411310b1a9d50ccd81855b1aa4d686ce94c81e98747aca3',OUT/'baseline',names)
  assert loaded==prior;r['baseline_source']=proof
  for n in names:
   if n=='children.json'or n.startswith('inputs/'):
    dst=OUT/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OUT/'baseline'/n,dst)
  leaf,proof=reports.restore_report('cdr-follower-v23-physical',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'follower',['layout/result.json','layout/schematic.cir','layout/nssoc_cdr_retime_follower_layout_v23.gds','layout/nssoc_cdr_retime_follower_layout_v23.lef'])
  assert leaf['status']=='PASS_CDR_FOLLOWER_V23_LEAF_PHYSICAL_REQUIRES_PARENT_RC_AND_LOADED_WAVES'
  r['follower_source']=proof
  target=OUT/'inputs/rc_retime/layout'
  shutil.rmtree(target);shutil.copytree(OUT/'follower/layout',target)
  manifest=json.loads((OUT/'children.json').read_text())
  manifest['children']['rc_retime']['files']={str(p.relative_to(OUT)):sha(p)for p in target.iterdir()if p.is_file()}
  (OUT/'children.json').write_text(json.dumps(manifest,indent=2)+'\n')
  methods=[Path(__file__),ROOT/'scripts/generate_cdr_follower_v23_parent.py',
   ROOT/'scripts/check_cdr_follower_v23_parent_geometry.py',ROOT/'hw/soc/flow/check_pcie_cdr_follower_v23_parent.py']
  protected={str(p):sha(p)for p in [*methods,*[OUT/'baseline'/n for n in names]]}
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
  packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
  packed.unlink();runtime=json.loads((ROOT/'manifest.json').read_text())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
  r['runtime_sha256']=sha(app);save()
  script="import sys,json;from pathlib import Path;sys.path.insert(0,'scripts');from check_cdr_follower_v23_parent_geometry import check;p=Path(sys.argv[1]);(p/'child-geometry-proof.json').write_text(json.dumps(check(p),indent=2)+'\\n')"
  for name,cmd in [
   ('generation',[app,'python',ROOT/'scripts/generate_cdr_follower_v23_parent.py','--out',OUT]),
   ('child_geometry',[app,'python','-c',script,OUT]),
   ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_follower_v23_parent.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app])]:
   with(OUT/(name+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
   r[name+'_returncode']=code;save()
   if code:print((OUT/(name+'.log')).read_text()[-16000:],flush=True)
   assert code==0,(name,code)
  r['replacement']=json.loads((OUT/'replacement-proof.json').read_text())
  r['child_geometry']=json.loads((OUT/'child-geometry-proof.json').read_text())
  r['physical']=json.loads((OUT/'physical/result.json').read_text())
  assert r['replacement']['replaced_instances']==['ac','bd'] and len(r['replacement']['actual_added_avdd_routes'])==2 and len(r['replacement']['controls'])==2
  assert r['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_EIGHT_NATIVE_LEAF_DRAWINGS'
  assert len(r['child_geometry']['controls'])==3
  assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD476_DRC_LVS_AND_FAULT_CONTROLS'
  assert all(sha(Path(n))==v for n,v in protected.items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  r.update(status='PASS_PD476_ACTIVE_FOLLOWER_V23_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES',
   sources_unchanged=True,protected_inputs=protected,
   scope='Two retime leaves replaced by actual native HBT followers. Fourteen other instances and all old parent routing retained. Two new AVDD branches and native vias required. Full560DRC, deep-flat476deviceLVS, original applicable faults and active polarity fault. Fresh whole-parent RC and unchanged original loaded electrical gates still required.')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  for key in ('layout','physical'):
   p=OUT/key/'result.json'
   if p.exists():r[key]=json.loads(p.read_text())
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
