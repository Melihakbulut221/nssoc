#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Place actual C8 pump in the verified divider-v2 physical845 PLL."""
import argparse,json,os,shutil,subprocess,tarfile
from pathlib import Path
import integrate_pll_rhi120_c8_parent as base
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-pll-rhi120-c8-parent'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/'
OLDTOP='nssoc_pll845_divider3p2_c8_v2_development'
TOP='nssoc_pll845_divider3p2_rhi120_c8_development'
CHILD='nssoc_pump_filter13_rhi120_c8_v1'
def configure():
 base.OUT=OUT;base.OLDTOP=OLDTOP;base.TOP=TOP;base.CHILD=CHILD

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--generate',action='store_true');args=parser.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true';configure()
 if args.generate:base.generate();return
 OUT.mkdir(parents=True,exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],size_um=8,rhi_length_um=120,accepted=False,full_phy_accepted=False,qualified_pex=False,main_chip_integrated=False,scope='Actual native RHI120/C8 pump replacement in existing divider-v2 PLL845 GDS. Freeze all other cells and every parent polygon/7pump port planes; native845deep+flatLVS/560DRC and actual RHI-length/open faults. Fresh parentRC, physically matched complete1us acquisition and fulldevice/PVT verification remain required.')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def restore(url,digest,bytes_,prefix,dest):
  packed=OUT/'restore.tar.gz';fetch(url,digest,packed);assert packed.stat().st_size==bytes_
  with tarfile.open(packed)as tar:
   names=tar.getnames();assert len(names)==len(set(names))
   for member in tar.getmembers():
    p=Path(member.name);assert not p.is_absolute() and '..' not in p.parts and p.parts[0]==prefix and(member.isdir()or member.isfile())
   tar.extractall(OUT,filter='data')
  packed.unlink();(OUT/prefix).rename(dest)
 save()
 try:
  parentpin=json.loads((ROOT/'docs/evidence/pll-c8-v2-parent-pass-20261017.json').read_text())
  restore(parentpin['archive_url'],parentpin['archive_sha256'],parentpin['archive_bytes'],'cloud-pll-c8-v2-parent',OUT/'source-parent')
  source=OUT/'source-parent';assert sha(source/'result.json')==parentpin['summary_sha256']
  prior=json.loads((source/'result.json').read_text())
  assert prior['source_head']==parentpin['source_head']
  assert prior['status']=='PASS_REAL_C8_DIVIDER_V2_PARENT845_DRC_LVS_REQUIRES_FRESH_RC_AND_ACQUISITION'
  assert all(sha(source/n)==v for n,v in prior['outputs'].items())
  old=json.loads((source/'integrated/result.json').read_text())
  assert old['top']==OLDTOP and old['integration_proof']['all7ports_unchanged'] and old['integration_proof']['other_cell_shapes_and_instances_unchanged']
  assert sha(source/'integrated'/(OLDTOP+'.gds'))=='79b2f5869f620cb5d6ce57756bab18f6ef10743aee953fb9c140202a6b225cdc'
  shutil.copytree(source/'integrated',OUT/'parent')
  r['c8_v2_parent_source']=dict(run=39005910789,summary_sha256=sha(source/'result.json'),gds_sha256=sha(source/'integrated'/(OLDTOP+'.gds')),prior_integration_proof=old['integration_proof'])
  pin=json.loads((ROOT/'docs/evidence/pll-rhi120-c8-physical-pass-20261023.json').read_text());r['pump_source']=pin
  restore(pin['base']+pin['stem']+'.tar.gz.part0000',pin['sha256'],pin['bytes'],'cloud-pll-rhi120-c8-layout',OUT/'child')
  assert sha(OUT/'child/result.json')==pin['summary_sha256']
  child=json.loads((OUT/'child/result.json').read_text());assert child['status']=='PASS_CANDIDATE_PUMP_NATIVE_DRC_LVS_LEF_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE'
  assert child['size_um']==8 and child['rhi_length_um']==120 and child['lef']['status']=='PASS_NATIVE_LEF_AND_TWO_PHYSICAL_FAULTS'
  assert all(sha(OUT/'child'/n)==v for n,v in child['outputs'].items())
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());packed=OUT/'runtime.tar.gz'
  fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
  packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256'];r['runtime_sha256']=sha(app)
  r['method_hashes']={str(q):sha(q)for q in [Path(__file__),ROOT/'scripts/integrate_pll_rhi120_c8_parent.py']};save()
  with (OUT/'generate.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--generate'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  if rc:print((OUT/'generate.log').read_text()[-12000:],flush=True)
  assert rc==0,'Native parent generation failed'
  r['integrated']=json.loads((OUT/'integrated/result.json').read_text());save()
  r['physical']=base.verify(app)
  assert all(sha(source/n)==v for n,v in prior['outputs'].items()) and all(sha(OUT/'child'/n)==v for n,v in child['outputs'].items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
  assert all(sha(Path(n))==h for n,h in r['method_hashes'].items())
  r['status']='PASS_REAL_RHI120_C8_PARENT845_DRC_LVS_REQUIRES_FRESH_RC_AND_ACQUISITION'
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  for label in ('integrated','physical'):
   q=OUT/label/'result.json'
   if q.exists():r[label]=json.loads(q.read_text())
  r['outputs']={str(q.relative_to(OUT)):sha(q)for q in OUT.rglob('*')if q.is_file()and q!=OUT/'result.json'};save()
if __name__=='__main__':main()
