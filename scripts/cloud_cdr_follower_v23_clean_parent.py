#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only replacement of both v22 retime leaves with native active followers."""
import hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-follower-v23-clean-parent'
TOP='nssoc_cdr_pd476_follower_v23'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,main_chip_integrated=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/cdr-follower-v23-parent-physical-pass-20261020.json').read_text())
  assert pin['run']==39473538977 and pin['summary_sha256']=='0b2217d4de1216336207650076be7431b585c3401441057d46f789a35598f945'
  prior=pin['report'];names=[n for n in prior['outputs']if n=='children.json'or n.startswith(('inputs/','layout/','physical/lvs_flat/'))]
  loaded,proof=reports.restore_report('cdr-follower-v23-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'parent',names)
  assert loaded==prior and prior['sources_unchanged']
  assert prior['status']=='PASS_PD476_ACTIVE_FOLLOWER_V23_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES'
  r['original_parent_source']=proof
  for n in names:
   if n=='children.json'or n.startswith('inputs/'):
    dst=OUT/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OUT/'parent'/n,dst)
  (OUT/'wire').mkdir()
  shutil.copyfile(ROOT/'scripts/clean_cdr_v23_floating_parent_metal.py',OUT/'wire/native_cleanup.py')
  methods=[Path(__file__),ROOT/'scripts/clean_cdr_v23_floating_parent_metal.py',
   ROOT/'scripts/check_cdr_follower_v23_parent_geometry.py',ROOT/'hw/soc/flow/check_pcie_cdr_follower_v23_parent.py']
  protected={str(p):sha(p)for p in [*methods,*[OUT/'parent'/n for n in names]]}
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
  packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
  packed.unlink();runtime=json.loads((ROOT/'manifest.json').read_text())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
  r['runtime_sha256']=sha(app);save()
  script="import sys,json;from pathlib import Path;sys.path.insert(0,'scripts');from check_cdr_follower_v23_parent_geometry import check;p=Path(sys.argv[1]);(p/'child-geometry-proof.json').write_text(json.dumps(check(p),indent=2)+'\\n')"
  for name,cmd in [
   ('generation',[app,'python',OUT/'wire/native_cleanup.py']),
   ('child_geometry',[app,'python','-c',script,OUT]),
   ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_follower_v23_parent.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app])]:
   with(OUT/(name+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
   r[name+'_returncode']=code;save()
   if code:print((OUT/(name+'.log')).read_text()[-16000:],flush=True)
   assert code==0,(name,code)
  r['cleanup']=json.loads((OUT/'floating-metal-diagnosis.json').read_text())
  r['child_geometry']=json.loads((OUT/'child-geometry-proof.json').read_text())
  r['physical']=json.loads((OUT/'physical/result.json').read_text())
  assert r['cleanup']['no_device_or_public_terminal_removed'] and r['cleanup']['native_devices']==476
  assert r['cleanup']['floating_components']
  assert r['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_EIGHT_NATIVE_LEAF_DRAWINGS'
  assert len(r['child_geometry']['controls'])==3
  assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD476_DRC_LVS_AND_FAULT_CONTROLS'
  assert all(sha(Path(n))==v for n,v in protected.items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  r.update(status='PASS_PD476_NATIVE_FLOATING_METAL_CLEANUP_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES',
   sources_unchanged=True,protected_inputs=protected,
   scope='Remove only independent wire components with zero native device terminals, zero public pins and entirely parent-owned metal/vias. Original native primitive children and reference circuit unchanged. Fresh full560DRC/deep-flat476deviceLVS and all nine original faults mandatory; not RC/electrical/PHY acceptance.')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  for key in ('layout','physical'):
   p=OUT/key/'result.json'
   if p.exists():r[key]=json.loads(p.read_text())
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
