#!/usr/bin/env python3
"""Authenticate saved routing data and diagnose classes only on a GitHub runner."""
import hashlib,json,os,subprocess,tarfile,time,traceback
from pathlib import Path,PurePosixPath
import mainchip_route_class_diagnosis as diag
import mainchip_targeted_counterpart_routing as scope_core
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-route-class-diagnosis'
REPO='repos/Melihakbulut221/nssoc/'
PRODUCER='7a0776718ec37a106b7dfde0cbd477c6a2a5522f'
PRODUCER_RUN=41292673925
RELEASE=430474717
ASSETS={
 'candidate-native.tar.gz.part000':(536870912,'e4611384c378dea726f1907d4be6fc90a0573358e62b1193bde2875c5981b7c6'),
 'candidate-native.tar.gz.part001':(215124420,'d7c69890e79c3b2199cb834dd40999f9bc4057f52c1bc667cd1113259831051d'),
 'candidate-outputs.json':(163920,'a51300c7e60446e04af87747792f19e58464d587ea46502118e4e920cc027eec'),
 'candidate-parts.json':(487,'d670ee107b22b5242c254cd656225e2d3d1527bc8f33e6e12d152a7434d087e0')}
SELECTED={'work/bulk-postdrt-antenna/fixed.def','work/bulk-postdrt-antenna/routed-fixed.def',
 'bulk-postdrt-antenna/drt-original-classes.json','bulk-postdrt-antenna/insertion-plan.json',
 'bulk-postdrt-antenna/targeted-routing-scope.json'}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path],text=True))
def save(name,value):
 p=OUT/(name+'.json');p.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def download(a,path):
 with path.open('wb')as f:subprocess.run(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'],stdout=f,check=True)
 assert path.stat().st_size==a['size'] and a['digest']=='sha256:'+sha(path)
def context():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
 return dict(source=os.environ['GITHUB_SHA'],run=int(os.environ['GITHUB_RUN_ID']),attempt=1)
def admission(ctx):
 control=int(os.environ['CONTROL_RUN']);assert control!=ctx['run']
 run=api('actions/runs/'+str(control))
 assert run['head_sha']==ctx['source']and run['status']=='completed'and run['conclusion']=='success'and run['run_attempt']==1
 assert run['event']=='workflow_dispatch'and run['path']=='.github/workflows/cloud-evidence-summary.yml'
 jobs=api('actions/runs/'+str(control)+'/jobs?per_page=100')
 assert jobs['total_count']==len(jobs['jobs'])==2
 statuses={j['name']:j['conclusion']for j in jobs['jobs']}
 assert statuses=={'source-controls':'success','class-diagnosis':'skipped'}
 tag='cloud-results-'+str(ctx['run'])+'-1-mainchip-route-class-diagnosis'
 release=None
 for attempt in range(60):
  p=subprocess.run(['gh','api',REPO+'releases/tags/'+tag],capture_output=True,text=True)
  if p.returncode==0:release=json.loads(p.stdout);break
  assert 'HTTP 404'in p.stderr,p.stderr
  time.sleep(2)
 assert release is not None and release['target_commitish']==ctx['source']and release['assets']==[]
 ref=api('git/ref/tags/'+tag);assert ref['object']['type']=='commit'and ref['object']['sha']==ctx['source']
 save('admission',dict(context=ctx,control_run=run,control_jobs=jobs,independent_empty_reservation=release,tag=ref))
 return release
def main():
 ctx=context();OUT.mkdir(exist_ok=False)
 own_release=admission(ctx)
 work=Path(os.environ['RUNNER_TEMP'])/'mainchip-route-class-diagnosis';work.mkdir(exist_ok=False)
 run=api('actions/runs/'+str(PRODUCER_RUN));assert run['head_sha']==PRODUCER and run['conclusion']=='failure'and run['status']=='completed'and run['run_attempt']==1
 release=api('releases/'+str(RELEASE));assert release['target_commitish']==PRODUCER
 tag=api('git/ref/tags/'+release['tag_name']);assert tag['object']['type']=='commit'and tag['object']['sha']==PRODUCER
 assets={a['name']:a for a in release['assets']};assert set(assets)==set(ASSETS)
 for n,(size,h)in ASSETS.items():
  assert assets[n]['size']==size and assets[n]['digest']=='sha256:'+h
  download(assets[n],work/n)
 index=json.loads((work/'candidate-outputs.json').read_text());parts=json.loads((work/'candidate-parts.json').read_text())
 assert index['source']==PRODUCER and int(index['run'])==PRODUCER_RUN and int(index['attempt'])==1
 assert all(index[k]is False for k in ['full_phy_accepted','physical_acceptance','timing_accepted'])
 assert SELECTED<=index['files'].keys()
 assert [p['name']for p in parts['parts']]==['candidate-native.tar.gz.part000','candidate-native.tar.gz.part001']
 archive=work/'native.tar.gz'
 with archive.open('wb')as out:
  for row in parts['parts']:
   path=work/row['name'];assert path.stat().st_size==row['bytes']and sha(path)==row['sha256']
   with path.open('rb')as f:
    for b in iter(lambda:f.read(1048576),b''):out.write(b)
 assert archive.stat().st_size==parts['archive']['bytes']and sha(archive)==parts['archive']['sha256']
 seen={};members=set()
 with tarfile.open(archive,mode='r|gz')as tar:
  for m in tar:
   p=PurePosixPath(m.name);assert not p.is_absolute()and '..'not in p.parts and m.name not in members
   members.add(m.name)
   if m.isdir():continue
   assert m.isfile()and m.name in index['files'],m.name
   h=hashlib.sha256();length=0;dest=work/'selected'/m.name if m.name in SELECTED else None
   if dest:dest.parent.mkdir(parents=True,exist_ok=True)
   sink=dest.open('wb')if dest else None
   try:
    with tar.extractfile(m)as f:
     for b in iter(lambda:f.read(1048576),b''):
      h.update(b);length+=len(b)
      if sink:sink.write(b)
   finally:
    if sink:sink.close()
   pin=dict(bytes=length,sha256=h.hexdigest());assert pin==index['files'][m.name],m.name;seen[m.name]=pin
 assert set(seen)==set(index['files'])
 save('archive-authentication',dict(context=ctx,producer=PRODUCER,producer_run=PRODUCER_RUN,archive=parts['archive'],authenticated_members=len(seen),selected_inputs={n:seen[n]for n in sorted(SELECTED)},native_payloads_remain_cloud=True))
 selected=work/'selected'
 classes=json.loads((selected/'bulk-postdrt-antenna/drt-original-classes.json').read_text())
 plan=json.loads((selected/'bulk-postdrt-antenna/insertion-plan.json').read_text())
 scope=json.loads((selected/'bulk-postdrt-antenna/targeted-routing-scope.json').read_text())
 antenna,extra,protected,routing=scope_core.validate_scope(scope,plan)
 assert len(antenna)==608 and len(extra)==220 and len(routing)==828 and len(protected)==1691
 save('authenticated-routing-scope',scope)
 result,pins,changes=diag.analyze((selected/'work/bulk-postdrt-antenna/fixed.def').read_bytes(),
  (selected/'work/bulk-postdrt-antenna/routed-fixed.def').read_bytes(),classes,plan['mutable_nets'],sorted(extra))
 result.update(context=ctx,producer=PRODUCER,producer_run=PRODUCER_RUN,producer_release=RELEASE,
  authenticated_members=len(seen),archive=parts['archive'],selected_inputs={n:seen[n]for n in sorted(SELECTED)},
  native_cad_executed=False,native_payloads_remain_cloud=True)
 for n,v in [('result',result),('all-selected-records',pins),('changed-selected-records',changes),
   ('producer-run',run),('producer-release',release),('native-output-index',index),('native-parts',parts)]:save(n,v)
 print(json.dumps(result),flush=True)
 publication={}
 for p in sorted(OUT.glob('*.json')):publication[p.name]=dict(bytes=p.stat().st_size,sha256=sha(p))
 save('complete-output-index',dict(context=ctx,files=publication))
 for p in sorted(OUT.glob('*.json')):
  subprocess.run(['gh','release','upload',own_release['tag_name'],str(p),'--repo','Melihakbulut221/nssoc'],check=True)
if __name__=='__main__':
 try:main()
 except BaseException as exc:
  OUT.mkdir(exist_ok=True)
  save('failure',dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,layout_modified=False))
  raise
