#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only C/D active-input integration and full native500-device verification."""
import hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-sampler-active-input-v57-parent'
OLD_TOP='nssoc_cdr_pd476_follower_v23'
TOP='nssoc_cdr_pd500_active_input_v57'
LEAF='nssoc_rx_sampler_active_input_layout_v57'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,closed_loop=False,qualified_pex=False,main_chip_integrated=False)
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  from check_cdr_sampler_active_input_v57 import check
  r['circuit_contract']=check()
  parent_path=ROOT/'docs/evidence/cdr-sampler-settling-v32-parent-physical-pass-20261022.json'
  parent_pin=json.loads(parent_path.read_text())
  assert parent_pin['run']==39738683936 and parent_pin['summary_sha256']=='946587a69d7843b31025493531a10f1bfad2454029fe91df703cb0967ea71ae1'
  prior=parent_pin['report']
  assert prior['sources_unchanged']and prior['status']=='PASS_PD476_SAMPLER_SETTLING_V32_PARENT_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES'
  leaves=[n for n in prior['outputs']if n=='children.json'or n.startswith('inputs/')]
  names=['layout/result.json','layout/schematic.cir','layout/'+OLD_TOP+'.gds','layout/'+OLD_TOP+'.lef']+leaves
  loaded,proof=reports.restore_report('cdr-sampler-settling-v32-parent',parent_pin['run'],parent_pin['summary_sha256'],parent_pin['parts_sha256'],OUT/'baseline',names)
  assert loaded==prior
  leaf_path=ROOT/'docs/evidence/cdr-sampler-active-input-v57-physical-pass-20261024.json'
  leaf_pin=json.loads(leaf_path.read_text())
  assert leaf_pin['run']==40060383240 and leaf_pin['summary_sha256']=='7d2f8549a3dcc26788fb77ded7e805a2a06d11d56d1c52625ed368fe2358481d'
  fn=['layout/result.json','layout/schematic.cir','layout/'+LEAF+'.gds','layout/'+LEAF+'.lef','physical/result.json']
  fresh,fproof=reports.restore_report(leaf_pin['group'],leaf_pin['run'],leaf_pin['summary_sha256'],leaf_pin['parts_sha256'],OUT/'data',fn)
  assert fresh['source_head']==leaf_pin['source_head']and fresh['sources_unchanged']and fresh['status']==leaf_pin['status']
  assert fresh['physical']['status']=='PASS_ACTIVE_INPUT_V57_SAMPLER66_UNSIMPLIFIED_DEEP_FLAT_DRC_LEF_AND_TWENTY_SEVEN_FAULTS'
  assert fresh['layout']['bbox_um']==[0,0,1323,243.63]
  r.update(parent_source=proof,data_source=fproof)
  for n in leaves:
   dst=OUT/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(OUT/'baseline'/n,dst)
  directory=OUT/'inputs/sampler_cd/layout';directory.mkdir(parents=True,exist_ok=False)
  for n in ('result.json','schematic.cir',LEAF+'.gds',LEAF+'.lef'):shutil.copyfile(OUT/'data/layout'/n,directory/n)
  manifest=json.loads((OUT/'children.json').read_text())
  assert len(manifest['children'])==8 and 'sampler_cd'not in manifest['children']
  manifest['children']['sampler_cd']=dict(directory='inputs/sampler_cd/layout',files={str(p.relative_to(OUT)):sha(p)for p in directory.iterdir()})
  manifest['status']='ALL_NINE_CHILD_SOURCE_PROOFS_BOUND_C_D_ONLY_ACTIVE_INPUT'
  (OUT/'children.json').write_text(json.dumps(manifest,indent=2)+'\n')
  methods=[Path(__file__),parent_path,leaf_path,ROOT/'scripts/generate_cdr_sampler_active_input_v57_parent.py',ROOT/'scripts/check_cdr_sampler_active_input_v57_parent_geometry.py',ROOT/'scripts/check_cdr_sampler_active_input_v57.py',ROOT/'hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py',ROOT/'scripts/generate_cdr_retimed_parallel_v3_base.py',ROOT/'hw/soc/flow/make_pcie_clock_vco_v6_local_v1.py',ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-drc-marker-frames-20261024.json',ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-supply-collision-20261024.json',ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-m4-attachments-20261024.json',ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-m4-overlay-wire-path-20261024.json']
  protected={str(p):sha(p)for p in [*methods,*[OUT/'baseline'/n for n in names],*[OUT/'data'/n for n in fn],OUT/'children.json']}
  spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
  packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
  with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
  packed.unlink();runtime=json.loads((ROOT/'manifest.json').read_text())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
  r['runtime_sha256']=sha(app);save()
  failure=json.loads((ROOT/'docs/evidence/cdr-sampler-active-input-v57-parent-lef-grid-error-20261024.json').read_text())
  old_failure,old_proof=reports.restore_report(failure['group'],failure['run'],failure['summary_sha256'],failure['parts_sha256'],OUT/'prior-lef',['layout/'+TOP+'.gds','layout/'+TOP+'.lef'])
  assert old_failure==failure['report']
  diagnostic=ROOT/'scripts/read_cdr_sampler_parent_lef_grid.py'
  with(OUT/'lef-grid-readback.log').open('w')as log:rc=subprocess.call([str(app),'python',str(diagnostic),str(OUT/'prior-lef')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  if rc:print((OUT/'lef-grid-readback.log').read_text()[-10000:],flush=True)
  assert rc==0,'Exact native grid diagnosis failed'
  r['previous_lef_failure']=dict(source=old_proof,readback=json.loads((OUT/'prior-lef/readback.json').read_text()));save()

  script="import sys,json;from pathlib import Path;sys.path.insert(0,'scripts');from check_cdr_sampler_active_input_v57_parent_geometry import check;p=Path(sys.argv[1]);(p/'child-geometry-proof.json').write_text(json.dumps(check(p),indent=2)+'\\n')"
  for name,cmd in [
   ('generation',[app,'python',ROOT/'scripts/generate_cdr_sampler_active_input_v57_parent.py','--out',OUT]),
   ('child_geometry',[app,'python','-c',script,OUT]),
   ('physical',[sys.executable,ROOT/'hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py','--layout',OUT/'layout','--out',OUT/'physical','--app',app])]:
   with(OUT/(name+'.log')).open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
   r[name+'_returncode']=code;save()
   if code:print((OUT/(name+'.log')).read_text()[-18000:],flush=True)
   assert code==0,(name,code)
  r['replacement']=json.loads((OUT/'replacement-proof.json').read_text())
  r['child_geometry']=json.loads((OUT/'child-geometry-proof.json').read_text())
  r['physical']=json.loads((OUT/'physical/result.json').read_text())
  assert r['replacement']['changed_sampler_tags']==['sc','sd']and len(r['replacement']['controls'])==10
  assert r['child_geometry']['status']=='PASS_ALL16_ACTUAL_PLACEMENTS_AND_NINE_NATIVE_LEAF_DRAWINGS'
  assert len(r['child_geometry']['controls'])==5
  assert r['physical']['status']=='PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS'
  assert all(sha(Path(n))==v for n,v in protected.items())
  assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
  r.update(status='PASS_PD500_C_D_ACTIVE_INPUT_V57_PARENT_PHYSICAL_REQUIRES_FRESH_RC_AND_ORIGINAL_LOADED_GATES',sources_unchanged=True,protected_inputs=protected,scope='Only C/D sampler leaves changed from54 to66 devices. A/B and368 other reference devices unchanged; 32 old C/D Metal1 enclosure strips moved with their identical native components; two old AVSS Metal3 bridges rerouted around new SUB contacts with all original via contacts preserved; 32 intentional v14 M4 source-bypass pieces and their96 root Via3 cuts preserved; 16 obsolete v16 M4 route widening overlays removed only after proving no root-owned via or external parent endpoint depends on them; old child-local M3/M5 widening rings removed only with one original child attachment and zero root-owned via contacts; any obsolete added notch area retired without subtracting child geometry. Drawing-only AVSS/SUB separation checked before and after GDS serialization. All other parent geometry, labels and transforms preserved. Actual width grows320um; LEF regenerated and checked. Full560-rule DRC, unsimplified deep/flat500-device LVS and12 faults. Standalone1pF electrical safety failures remain; fresh actual whole-parent RC and original full loaded early/late/fault waves required. No complete PHY, recovered clock, mainchip or production approval.')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  for key in ('layout','physical'):
   p=OUT/key/'result.json'
   if p.exists():r[key]=json.loads(p.read_text())
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
