#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the unchanged two-order native RC check after exact via3 source success."""
import hashlib,json,os,shutil,subprocess,sys,time,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
RUN=40071489977
HEAD='b00c6f400c60190ff4ddcba200bbe0d6f92c8fe7'
REPO='repos/Melihakbulut221/nssoc/'
GROUP='tx-driverpinfeed-followthrough'
OUT=ROOT/'hw/soc/out/cloud-tx-output8088-driverpinfeed-precision'
STAGE=ROOT/'hw/soc/out/cloud-tx-output8088-driverpinfeed-precision-launch'
BASE='scripts/cloud_tx_output8088_power128return64_precision.py'
BASE_SHA='2992451e0de110ea696f1aa2bb1d97621521cc7da7319ea5cbbb4535f3512401'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def metadata(group):
 release=api('releases/tags/cloud-results-'+str(RUN)+'-1-'+group)
 out={}
 for suffix,key in [('.summary.json','summary'),('.parts.json','parts')]:
  assets=[a for a in release['assets']if a['name']==group+'-'+str(RUN)+'-1'+suffix]
  assert len(assets)==1
  a=assets[0]
  b=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'])
  assert a['digest']=='sha256:'+sha(b)
  out[key]=json.loads(b);out[key+'_asset']=a['id'];out[key+'_sha256']=sha(b)
 assert out['summary']['source_head']==HEAD
 return out
def main():
 locked=json.loads((ROOT/'scripts/tx-driverpinfeed-precision-launch-methods.json').read_text())
 assert all(digest(ROOT/p)==h for p,h in locked.items())
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'
 STAGE.mkdir(parents=True,exist_ok=False)
 record=dict(status='WAITING_FOR_EXACT_FRESH_INTRINSIC_RC',source_run=RUN,source_head=HEAD,
  full_phy_accepted=False,electrical_accepted=False,qualified_pex=False)
 def save():(STAGE/'result.json').write_text(json.dumps(record,indent=2)+'\n')
 save()
 try:
  start=time.monotonic();previous=None
  while True:
   r=api('actions/runs/'+str(RUN))
   assert r['head_sha']==HEAD and r['run_attempt']==1
   assert r['head_branch']=='codex/tx-via3-rail-diagnosis'
   assert r['path']=='.github/workflows/tx-driverpinfeed-followthrough-cloud.yml'
   key=(r['status'],r['conclusion'])
   if key!=previous:print('Exact native source',key,flush=True);previous=key
   if r['status']=='completed':
    assert r['conclusion']=='success','Failed source may not advance'
    break
   assert time.monotonic()-start<180*60,'Observation limit; source is not cancelled or restarted'
   time.sleep(60)
  jobs=api('actions/runs/'+str(RUN)+'/jobs')['jobs']
  assert len(jobs)==1 and jobs[0]['name']=='native-physical'and jobs[0]['conclusion']=='success'
  combined=metadata(GROUP);source=combined['summary']
  assert source['status']=='PASS_FRESH_DRIVERPINFEED_INTRINSIC_AND_RC_REQUIRES_TWO_ORDER_PRECISION_COMPOSITION_AND_FULLWAVE'
  assert source['generated_sources_unchanged']and source['source_native_process_not_restarted']
  assert source['anchor_receipt']['run']==40071267004
  assert len(source['results'])==2 and all(x['returncode']==0 and x['sources_unchanged']for x in source['results'])
  selected=['generated/'+p for p in source['generated_sha256'] if not p.startswith('.github/')]
  assert selected and all(source['outputs'][n]==source['generated_sha256'][n[len('generated/'):]]for n in selected)
  reports.OUT=STAGE
  loaded,proof=reports.restore_report(GROUP,RUN,combined['summary_sha256'],combined['parts_sha256'],STAGE/'source',selected)
  assert loaded==source
  record['source_restore']=proof
  generated={}
  for name in selected:
   p=name[len('generated/'):]
   assert p.startswith(('scripts/','docs/evidence/'))and '..'not in Path(p).parts
   data=(STAGE/'source'/name).read_bytes()
   assert sha(data)==source['generated_sha256'][p]
   target=ROOT/p
   if target.exists():assert target.read_bytes()==data,('Checked-in source differs from qualified source',p)
   else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
   generated[p]=sha(data)
  rc=metadata('tx-output8088-driverpinfeed-native-rc');d=rc['summary']
  assert d['status']=='PASS_FRESH_TX_OUTPUT8088_DRIVERPINFEED_PRECISE_WIRE_RC_AND13_RAW_CORRUPTIONS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
  assert d['sources_unchanged']and len(d['controls']['cases'])==13
  assert d['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
  assert d['audit']['actual_exported_resistors']>0 and d['audit']['actual_exported_capacitors']>0
  intrinsic=metadata('tx-output8088-driverpinfeed-intrinsic')
  assert intrinsic['summary']['status']=='PASS_FULL8088_NATIVE_INTRINSIC_BINDING_65_BODY_NETS_AND19_CONTROLS_REQUIRES_WHOLE_WIRE_RC_AND_LOADED_WAVES'
  assert intrinsic['summary']['sources_unchanged']and len(intrinsic['summary']['controls'])==19
  for name,item in [('native-rc',rc),('intrinsic',intrinsic)]:
   expected=next(x for x in source['results']if x['name']==name)
   assert expected['report_sha256']==item['summary_sha256']
  pin={k:d[k]for k in ('source_head','status','outputs','audit','controls')}
  pin.update(run=RUN,summary_sha256=rc['summary_sha256'],parts_sha256=rc['parts_sha256'])
  pinpath='docs/evidence/tx-output8088-driverpinfeed-native-rc-pass-20261024.json'
  data=json.dumps(pin,indent=2)+'\n';(ROOT/pinpath).write_text(data);generated[pinpath]=sha(data.encode())
  base=(ROOT/BASE).read_bytes();assert sha(base)==BASE_SHA
  candidate='scripts/cloud_tx_output8088_driverpinfeed_precision.py'
  edits=[dict(before='power128return64',after='driverpinfeed',count=10),
   dict(before='POWER128RETURN64',after='DRIVERPINFEED',count=1),
   dict(before='full_tx_output8088_driverpinfeed_wires',after='full_tx_output8088_driver_pinfeed_wires',count=3),
   dict(before='20261023',after='20261024',count=1),
   dict(before='39901168356',after=str(RUN),count=1),
   dict(before='2b19f65083554c59fc5a171eb89e25ce51bcc5f8f3f31de42024a554e049d729',after=rc['summary_sha256'],count=1)]
  code=base.decode()
  for e in edits:
   assert code.count(e['before'])==e['count'];code=code.replace(e['before'],e['after'])
  (ROOT/candidate).write_text(code);generated[candidate]=sha(code.encode())
  method=dict(baseline_path=BASE,baseline_sha256=BASE_SHA,candidate_path=candidate,
   candidate_sha256=sha(code.encode()),edits=edits,
   scope='Only via3 names and exact fresh RC source. Original producer, two input orders, exact R/C multisets and13 corruption controls per order unchanged.')
  methodpath='scripts/tx-output8088-driverpinfeed-precision-method.json'
  data=json.dumps(method,indent=2)+'\n';(ROOT/methodpath).write_text(data);generated[methodpath]=sha(data.encode())
  record.update(status='RUNNING_FRESH_TWO_ORDER_NATIVE_RC',generated_sha256=generated,
   rc_summary_sha256=rc['summary_sha256'],rc_parts_sha256=rc['parts_sha256']);save()
  with (STAGE/'native.log').open('w')as log:
   completed=subprocess.run([sys.executable,ROOT/candidate],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  record['native_returncode']=completed.returncode
  assert all(digest(ROOT/p)==s for p,s in generated.items())
  assert all(digest(ROOT/p)==h for p,h in locked.items())
  assert completed.returncode==0,'Native two-order precision rejected; full log preserved'
  result=json.loads((OUT/'result.json').read_text())
  assert result['status']=='PASS_ACTUAL8088_DRIVERPINFEED_NATIVE_RC_DOUBLE_TOTALS_TWO_ORDERS_AND13_CONTROLS_EACH_NOT_FULL_PHY'
  assert result['sources_unchanged']and result['both_native_input_orders_verified']
  record.update(status='PASS_FRESH_TWO_ORDER_NATIVE_RC_REQUIRES_COMPOSITION_AND_FULL_WAVES',
   generated_sources_unchanged=True)
 except BaseException as e:
  record.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  for p,s in record.get('generated_sha256',{}).items():
   if (ROOT/p).exists():
    target=STAGE/'generated'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,target)
  save();OUT.mkdir(parents=True,exist_ok=True)
  shutil.move(str(STAGE),str(OUT/'launcher-evidence'))
  rp=OUT/'result.json'
  r=json.loads(rp.read_text())if rp.exists()else dict(status='FAIL_BEFORE_NATIVE_PRECISION',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False)
  r['launcher']=record
  if record['status']=='FAIL_OR_ERROR':r['status']='FAIL_OR_ERROR'
  r['outputs']={str(p.relative_to(OUT)):digest(p)for p in OUT.rglob('*')if p.is_file()and p!=rp}
  rp.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
