#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only physical retime-input routing candidate from the exact v21 parent."""
import hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-retime-trunks-v22-parent'
TOP='nssoc_cdr_pd484_localbus_v12'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,main_chip_integrated=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/cdr-collector-trunks-v21-parent-physical-pass-20261020.json').read_text())
  assert pin['run']==39440691879 and pin['summary_sha256']=='ae578b3ecf11a68193c310a0a496d47c959d30a411f7c6803aeb04f1e5dfff0d'
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/659575914','-H','Accept: application/octet-stream'])
  assert hashlib.sha256(raw).hexdigest()==pin['summary_sha256'];prior=json.loads(raw)
  assert prior['source_head']=='4446725afb079d53c9f707c92fc4cfb2a94e31a7'and prior['sources_unchanged']
  assert prior['status']=='PASS_PD484_COLLECTOR_TRUNKS_V21_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES'
  names=[n for n in prior['outputs']if n=='children.json'or n.startswith('inputs/')or n.startswith('layout/')]
  loaded,proof=reports.restore_report('cdr-collector-trunks-v21-parent',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'baseline',names)
  assert loaded==prior;r['baseline_source']=proof
  for n in names:
   if n=='children.json'or n.startswith('inputs/'):
    dst=OUT/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OUT/'baseline'/n,dst)
  methods=[Path(__file__),ROOT/'scripts/generate_cdr_retime_trunks_v22_parent.py',
   ROOT/'scripts/check_cdr_localbus_v12_parent_geometry.py',ROOT/'hw/soc/flow/check_pcie_cdr_retimed_localbus_v12_parent.py']
  protected={str(p):sha(p)for p in [*methods,*[OUT/'baseline'/n for n in names]]}
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
  packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
  packed.unlink();runtime=json.loads((ROOT/'manifest.json').read_text())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
  r['runtime_sha256']=sha(app);save()
  script="import sys,json;from pathlib import Path;sys.path.insert(0,'scripts');from check_cdr_localbus_v12_parent_geometry import check;p=Path(sys.argv[1]);(p/'child-geometry-proof.json').write_text(json.dumps(check(p),indent=2)+'\\n')"
  for name,cmd in [
   ('generation',[app,'python',ROOT/'scripts/generate_cdr_retime_trunks_v22_parent.py','--out',OUT]),
   ('child_geometry',[app,'python','-c',script,OUT]),
   ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_retimed_localbus_v12_parent.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app])]:
   with(OUT/(name+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
   r[name+'_returncode']=code;save()
   if code:print((OUT/(name+'.log')).read_text()[-16000:],flush=True)
   assert code==0,(name,code)
  r['routing']=json.loads((OUT/'routing-proof.json').read_text())
  r['child_geometry']=json.loads((OUT/'child-geometry-proof.json').read_text())
  r['physical']=json.loads((OUT/'physical/result.json').read_text())
  assert len(r['routing']['changed_rectangles'])==12 and len(r['routing']['moved_native_tm1_tm2_vias'])==8 and len(r['routing']['controls'])==3
  assert r['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_EIGHT_NATIVE_LEAF_DRAWINGS'
  assert len(r['child_geometry']['controls'])==3
  assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD484_DRC_LVS_AND_FAULT_CONTROLS'
  assert all(sha(Path(n))==v for n,v in protected.items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  r.update(status='PASS_PD484_RETIME_TRUNKS_V22_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES',
   sources_unchanged=True,protected_inputs=protected,
   scope='Four internal retime-input trunks moved into the existing channel; eight horizontal arms shortened and eight native junctions translated. Existing v21 collector routing is retained. Native children, placements, schematic, public pins and LEF unchanged. Full native DRC/LVS required. No extraction or electrical pass inferred from wire length.')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  for key in ('layout','physical'):
   p=OUT/key/'result.json'
   if p.exists():r[key]=json.loads(p.read_text())
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
