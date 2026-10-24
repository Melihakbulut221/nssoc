#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Wait for one exact native precision pass, then compose and measure real rail access."""
import hashlib,json,os,shutil,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'hw/soc/out/cloud-tx-driverpinfeed-composition-followthrough'
OUT=ROOT/'hw/soc/out/cloud-tx-output8088-driverpinfeed-composition'
REPO='repos/Melihakbulut221/nssoc/'
RUN=40072842481
HEAD='12a42514bee086c800ba8f296a09b2b78556275f'
GROUP='tx-output8088-driverpinfeed-precision'
CONTROLLER='scripts/cloud_tx_output8088_driverpinfeed_composition_launch.py'
CONTROLLER_SHA='4ee36cad53b34e017a7ca5a16aad72da9d7b69917907083965f6c1d1f97568b3'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'
 assert digest(ROOT/CONTROLLER)==CONTROLLER_SHA
 locked=json.loads((ROOT/'scripts/tx-driverpinfeed-composition-launch-methods.json').read_text())
 assert all(digest(ROOT/p)==h for p,h in locked.items())
 STAGE.mkdir(parents=True,exist_ok=False)
 r=dict(status='WAITING_FOR_EXACT_NATIVE_PRECISION',source_head=os.environ['GITHUB_SHA'],
  source_run=RUN,precision_source_head=HEAD,accepted=False,electrical_accepted=False,full_phy_accepted=False,no_new_simulation=True)
 def save():(STAGE/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  start=time.monotonic();previous=None
  while True:
   q=api('actions/runs/'+str(RUN))
   assert q['head_sha']==HEAD and q['run_attempt']==1
   assert q['head_branch']=='codex/tx-via3-rail-diagnosis'
   assert q['path']=='.github/workflows/tx-output8088-driverpinfeed-precision-cloud.yml'
   state=(q['status'],q['conclusion'])
   if state!=previous:
    print('Exact native precision source',state,flush=True);r['source_live']=dict(status=state[0],conclusion=state[1]);save();previous=state
   if q['status']=='completed':
    assert q['conclusion']=='success','Failed precision cannot advance; never restart its native process'
    break
   assert time.monotonic()-start<210*60,'Observation limit reached; prerequisite is not cancelled'
   time.sleep(60)
  jobs=api('actions/runs/'+str(RUN)+'/jobs')['jobs']
  assert len(jobs)==1 and jobs[0]['name']=='actual-full-parent-wire-rc'and jobs[0]['conclusion']=='success'
  release=api('releases/tags/cloud-results-'+str(RUN)+'-1-'+GROUP)
  pin=dict(run=RUN,source_head=HEAD)
  for suffix,key in [('.summary.json','summary'),('.parts.json','parts')]:
   assets=[a for a in release['assets']if a['name']==GROUP+'-'+str(RUN)+'-1'+suffix];assert len(assets)==1
   a=assets[0];b=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'])
   assert a['digest']=='sha256:'+sha(b);pin[key+'_sha256']=sha(b)
   (STAGE/('precision'+suffix)).write_bytes(b)
   if key=='summary':
    source=json.loads(b)
    assert source['source_head']==HEAD and source['sources_unchanged']
    assert source['status']=='PASS_ACTUAL8088_DRIVERPINFEED_NATIVE_RC_DOUBLE_TOTALS_TWO_ORDERS_AND13_CONTROLS_EACH_NOT_FULL_PHY'
    assert source['both_native_input_orders_verified']and source['no_rc_records_changed']and source['no_geometry_technology_or_threshold_change']
    assert source['launcher']['generated_sources_unchanged']
  r.update(status='RUNNING_EXACT_NATIVE_COMPOSITION_AND_RAIL_COMPARISON',precision_pin=pin);save()
  env=os.environ.copy();env['NSSOC_TX_PRECISION_SOURCE']=json.dumps(pin)
  with(STAGE/'native.log').open('w')as log:
   p=subprocess.run([sys.executable,ROOT/CONTROLLER],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
  r['returncode']=p.returncode;save()
  assert p.returncode==0,'Composition or unchanged native rail identity controls rejected'
  d=json.loads((OUT/'result.json').read_text())
  assert d['status']=='PASS_ACTUAL_FULL8088_DRIVERPINFEED_PARENT_WIRE_COMPOSITION_AND25_CONTROLS_REQUIRES_LOADED_NATIVE_WAVES'
  assert d['sources_unchanged']and len(d['controls'])==25
  assert d['launcher']['status']=='PASS_FRESH_FULL_PARENT_COMPOSITION_AND_EXACT_RAIL_COMPARISON_REQUIRES_LOADED_NATIVE_WAVES'
  assert d['launcher']['generated_sources_unchanged']
  assert all(digest(ROOT/p)==h for p,h in locked.items())and digest(ROOT/CONTROLLER)==CONTROLLER_SHA
  r.update(status='PASS_EXACT_PRECISION_COMPOSITION_AND_RAIL_ACCESS_REQUIRES_PARENT_REVIEW',sources_unchanged=True,
   rail_comparison=d['launcher']['rail_comparison'])
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  save();OUT.mkdir(parents=True,exist_ok=True);shutil.move(str(STAGE),str(OUT/'followthrough-evidence'))
  rp=OUT/'result.json';d=json.loads(rp.read_text())if rp.exists()else dict(status='FAIL_BEFORE_COMPOSITION',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False)
  d['followthrough']=r
  if r['status']=='FAIL_OR_ERROR':d['status']='FAIL_OR_ERROR'
  d['outputs']={str(p.relative_to(OUT)):digest(p)for p in OUT.rglob('*')if p.is_file()and p!=rp}
  rp.write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':main()
