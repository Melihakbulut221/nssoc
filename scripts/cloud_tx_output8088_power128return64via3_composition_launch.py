#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compose the exact fresh via3 device model and independently checked wire RC."""
import difflib,hashlib,json,os,shutil,subprocess,sys,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output8088-power128return64via3-composition'
STAGE=ROOT/'hw/soc/out/cloud-tx-output8088-power128return64via3-composition-launch'
REPO='repos/Melihakbulut221/nssoc/'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def asset(a,h):
 b=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a),'-H','Accept: application/octet-stream'])
 assert sha(b)==h
 return b
def derivation(path,base,new):
 aa=base.splitlines(True);bb=new.splitlines(True);offset=[0]
 for line in aa:offset.append(offset[-1]+len(line))
 changes=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(a=aa,b=bb,autojunk=False).get_opcodes():
  if tag!='equal':changes.append(dict(start=offset[i],end=offset[j],replacement=''.join(bb[k:l])))
 return dict(baseline_path=path,baseline_sha256=sha(base.encode()),candidate_sha256=sha(new.encode()),changes=changes)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 STAGE.mkdir(parents=True,exist_ok=False)
 r=dict(status='RESTORING_EXACT_NATIVE_SOURCES',source_head=os.environ['GITHUB_SHA'],
  full_phy_accepted=False,electrical_accepted=False,qualified_pex=False)
 generated={}
 def save():(STAGE/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def write(path,data):
  p=ROOT/path;assert not p.exists(),('Do not replace checked-in sources',path)
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);generated[path]=sha(data)
 save()
 try:
  for run,head in [(39992856037,'26c97387b0c7a26d8eef5fa5701f2282b3e3bc93'),(39991332843,'b321d505ab8dcb63224a282ae7ce2ce3d0cce3b0')]:
   q=api('actions/runs/'+str(run))
   assert q['status']=='completed'and q['conclusion']=='success'and q['head_sha']==head and q['run_attempt']==1
  ps=asset(669885636,'42a9cc9ae8aa4f93cd430856b48636b428c5119e3ee42e6fc104172e106c1cb8')
  pp=asset(669885709,'1e626f5db80292f83ae08657610f247e0aca6b4d92732127771d274310e42256')
  precision=json.loads(ps)
  assert precision['source_head']=='26c97387b0c7a26d8eef5fa5701f2282b3e3bc93'
  assert precision['status']=='PASS_ACTUAL8088_POWER128RETURN64VIA3_NATIVE_RC_DOUBLE_TOTALS_TWO_ORDERS_AND13_CONTROLS_EACH_NOT_FULL_PHY'
  assert precision['sources_unchanged']and precision['both_native_input_orders_verified']
  assert precision['launcher']['generated_sources_unchanged']
  hashes=precision['launcher']['generated_sha256']
  names=['launcher-evidence/generated/'+p for p in hashes]
  assert all(precision['outputs'][n]==hashes[n[len('launcher-evidence/generated/'):]]for n in names)
  reports.OUT=STAGE
  prior,proof=reports.restore_report('tx-output8088-power128return64via3-precision',39992856037,sha(ps),sha(pp),STAGE/'source',names)
  assert prior==precision;r['source_restore']=proof
  for n in names:
   p=n[len('launcher-evidence/generated/'):]
   assert p.startswith(('scripts/','docs/evidence/'))and '..'not in Path(p).parts
   b=(STAGE/'source'/n).read_bytes();assert sha(b)==hashes[p];write(p,b)
  si=asset(669847530,'e0d82e0b7fac26a96d7ee1d1f742805dad56881b729b94aeb8f5303d384f88a5')
  pi=asset(669847638,'62867b6aea8f0e5004f1763372325382cacb7983df61c9af66ba4161a6a72a07')
  intrinsic=json.loads(si)
  assert intrinsic['source_head']=='b321d505ab8dcb63224a282ae7ce2ce3d0cce3b0'
  assert intrinsic['status']=='PASS_FULL8088_NATIVE_INTRINSIC_BINDING_65_BODY_NETS_AND19_CONTROLS_REQUIRES_WHOLE_WIRE_RC_AND_LOADED_WAVES'
  assert intrinsic['sources_unchanged']and len(intrinsic['controls'])==19
  docs={
   'precision-pass':dict(run=39992856037,source_head=precision['source_head'],
    summary_asset_id=669885636,summary_sha256=sha(ps),summary_bytes=len(ps),
    parts_asset_id=669885709,parts_sha256=sha(pp),parts_bytes=len(pp)),
   'composition-input':dict(run=39992856037,source_head=precision['source_head'],
    workflow_path='.github/workflows/tx-output8088-power128return64via3-precision-cloud.yml'),
   'intrinsic-pass':dict(run=39991332843,source_head=intrinsic['source_head'],
    summary_asset=669847530,summary_sha256=sha(si),parts_asset=669847638,parts_sha256=sha(pi),report=intrinsic)}
  for name,data in docs.items():
   write('docs/evidence/tx-output8088-power128return64via3-'+name+'-20261023.json',(json.dumps(data,indent=2)+'\n').encode())
  methods={}
  for path,expected in [
   ('scripts/cloud_tx_output8088_power128return64_composition.py','34aa13531ab74ebf0fe0bcb3c6d2bb499a38be955e67533e911eccd2a0e49f3a'),
   ('scripts/compose_tx_output8088_power128return64_native.py','cc631961176293f5e60cdcfd6a859e881c2438e700353826f6f160d175cf4563')]:
   b=(ROOT/path).read_bytes();assert sha(b)==expected
   base=b.decode();new=base.replace('power128return64','power128return64via3').replace('POWER128RETURN64','POWER128RETURN64VIA3')
   if 'cloud_'in path:
    assert new.count("bp['run']==39901168356")==1
    assert new.count('eab4cea794ef2b27d693b0deb92ca7f6dc2b1361')==1
    new=new.replace("bp['run']==39901168356","bp['run']==39991332843").replace('eab4cea794ef2b27d693b0deb92ca7f6dc2b1361','b321d505ab8dcb63224a282ae7ce2ce3d0cce3b0')
   candidate=path.replace('power128return64','power128return64via3')
   methods[candidate]=derivation(path,base,new);write(candidate,new.encode())
  write('scripts/tx-output8088-power128return64via3-composition-method.json',(json.dumps(methods,indent=2)+'\n').encode())
  r.update(status='COMPOSING_EVERY_ACTUAL_DEVICE_AND_WIRE',generated_sha256=generated);save()
  with (STAGE/'native.log').open('w')as log:
   p=subprocess.run([sys.executable,ROOT/'scripts/cloud_tx_output8088_power128return64via3_composition.py'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  r['native_returncode']=p.returncode
  assert all(digest(ROOT/n)==h for n,h in generated.items())
  assert p.returncode==0,'Composition or one of25 original corruption controls rejected'
  report=json.loads((OUT/'result.json').read_text())
  assert report['status']=='PASS_ACTUAL_FULL8088_POWER128RETURN64VIA3_PARENT_WIRE_COMPOSITION_AND25_CONTROLS_REQUIRES_LOADED_NATIVE_WAVES'
  assert report['sources_unchanged']and len(report['controls'])==25
  r.update(status='PASS_FRESH_FULL_PARENT_COMPOSITION_REQUIRES_LOADED_NATIVE_WAVES',generated_sources_unchanged=True)
 except BaseException as e:
  r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
 finally:
  for p in generated:
   if (ROOT/p).exists():
    dst=STAGE/'generated'/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,dst)
  save();OUT.mkdir(parents=True,exist_ok=True);shutil.move(str(STAGE),str(OUT/'launcher-evidence'))
  rp=OUT/'result.json'
  report=json.loads(rp.read_text())if rp.exists()else dict(status='FAIL_BEFORE_COMPOSITION',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False)
  report['launcher']=r
  if r['status']=='FAIL_OR_ERROR':report['status']='FAIL_OR_ERROR'
  report['outputs']={str(p.relative_to(OUT)):digest(p)for p in OUT.rglob('*')if p.is_file()and p!=rp}
  rp.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
