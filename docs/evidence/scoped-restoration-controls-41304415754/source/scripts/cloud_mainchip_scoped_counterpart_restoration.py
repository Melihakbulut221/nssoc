"""Cloud-only restoration of the authenticated saved route with original native audits."""
import hashlib,importlib,json,os,shutil,subprocess,sys,tarfile,time,traceback
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=ROOT/'original'
OUT=ROOT/'scoped-restoration-evidence'
BASE='7a0776718ec37a106b7dfde0cbd477c6a2a5522f'
REPO='repos/Melihakbulut221/nssoc/'
GROUP='mainchip-bulk-postdrt-antenna'
MANIFEST='scripts/mainchip-scoped-restoration-native-pins.json'
NEW_NATIVE=('scripts/mainchip_scoped_counterpart_restoration.py','scripts/mainchip_scoped_counterpart_restoration_native.py','scripts/mainchip_scoped_counterpart_restoration_inner.py')
SELECTED={
 'work/bulk-postdrt-antenna/routed-fixed.odb','work/bulk-postdrt-antenna/routed-fixed.def',
 'work/bulk-postdrt-antenna/fixed.def','work/bulk-postdrt-antenna/insertion.def',
 'bulk-postdrt-antenna/baseline-snapshot.json','bulk-postdrt-antenna/insertion-snapshot.json',
 'bulk-postdrt-antenna/drt-original-classes.json','bulk-postdrt-antenna/insertion-plan.json',
 'bulk-postdrt-antenna/targeted-routing-scope.json','bulk-postdrt-antenna/baseline-antenna-violations.json',
 'bulk-postdrt-antenna/saved-construction-plan.json'}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def fp(path):return dict(bytes=path.stat().st_size,sha256=sha(path))
def api(path):return json.loads(subprocess.check_output(['gh','api',REPO+path],text=True))
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
def own_sources():
 pins=json.loads((ROOT/MANIFEST).read_text())
 subprocess.run(['git','diff','--exit-code','HEAD','--',MANIFEST,*pins],cwd=ROOT,check=True)
 for n,p in pins.items():
  path=ROOT/n;assert path.is_file()and not path.is_symlink()and fp(path)==p,('own source',n)
 return pins
def admission():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
 assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'and os.environ['GITHUB_EVENT_NAME']=='workflow_dispatch'
 assert os.environ['GITHUB_REF']=='refs/heads/codex/mainchip-scoped-restoration'
 source=os.environ['GITHUB_SHA'];rid=int(os.environ['GITHUB_RUN_ID']);control=int(os.environ['CONTROL_RUN'])
 assert source==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 run=api('actions/runs/'+str(control));jobs=api('actions/runs/'+str(control)+'/jobs?per_page=100')
 assert control!=rid and run['head_sha']==source and run['status']=='completed'and run['conclusion']=='success'and run['run_attempt']==1
 assert run['event']=='workflow_dispatch'and run['path']=='.github/workflows/cloud-evidence-summary.yml'
 assert jobs['total_count']==len(jobs['jobs'])==2 and {j['name']:j['conclusion']for j in jobs['jobs']}=={'source-controls':'success','native-restoration':'skipped'}
 ctx=dict(source=source,run_id=rid,attempt=1,token=str(rid)+'-1',name='nssoc-witness-build-'+str(rid)+'-1',group=GROUP)
 tag='cloud-results-'+ctx['token']+'-'+GROUP;release=None
 for i in range(60):
  p=subprocess.run(['gh','api',REPO+'releases/tags/'+tag],capture_output=True,text=True)
  if p.returncode==0:release=json.loads(p.stdout);break
  assert 'HTTP 404'in p.stderr,p.stderr
  time.sleep(2)
 assert release is not None and release['assets']==[]and release['target_commitish']==source
 ref=api('git/ref/tags/'+tag);assert ref['object']['type']=='commit'and ref['object']['sha']==source
 proof=dict(tag=tag,tested_source=source,release_id=release['id'],target_verified=True,assets_overwritten=False,externally_reserved=True,creation_attempted=False,existing_assets=[])
 write(OUT/'independent-admission.json',dict(context=ctx,controls_run=run,controls_jobs=jobs,release=release,tag=ref,proof=proof))
 return ctx,proof
def acquire_route(work,out):
 # Byte-identical producer assets used by successful readout41302468053.
 assets_pin={
 'candidate-native.tar.gz.part000':(536870912,'e4611384c378dea726f1907d4be6fc90a0573358e62b1193bde2875c5981b7c6'),
 'candidate-native.tar.gz.part001':(215124420,'d7c69890e79c3b2199cb834dd40999f9bc4057f52c1bc667cd1113259831051d'),
 'candidate-outputs.json':(163920,'a51300c7e60446e04af87747792f19e58464d587ea46502118e4e920cc027eec'),
 'candidate-parts.json':(487,'d670ee107b22b5242c254cd656225e2d3d1527bc8f33e6e12d152a7434d087e0')}
 run=api('actions/runs/41292673925');release=api('releases/430474717')
 assert run['head_sha']==BASE and run['status']=='completed'and run['conclusion']=='failure'and run['run_attempt']==1
 assert release['target_commitish']==BASE
 tag=api('git/ref/tags/'+release['tag_name']);assert tag['object']['sha']==BASE and tag['object']['type']=='commit'
 assets={a['name']:a for a in release['assets']};assert set(assets)==set(assets_pin)
 transport=work/'saved-route-transport';transport.mkdir()
 for n,(size,h)in assets_pin.items():
  a=assets[n];assert a['size']==size and a['digest']=='sha256:'+h
  with (transport/n).open('wb')as f:subprocess.run(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'],stdout=f,check=True)
  assert fp(transport/n)==dict(bytes=size,sha256=h)
 index=json.loads((transport/'candidate-outputs.json').read_text());parts=json.loads((transport/'candidate-parts.json').read_text())
 assert index['source']==BASE and int(index['run'])==41292673925 and int(index['attempt'])==1
 assert SELECTED<=set(index['files'])
 assert [p['name']for p in parts['parts']]==['candidate-native.tar.gz.part000','candidate-native.tar.gz.part001']
 archive=transport/'native.tar.gz'
 with archive.open('wb')as f:
  for p in parts['parts']:
   assert fp(transport/p['name'])=={k:p[k]for k in ('bytes','sha256')}
   with (transport/p['name']).open('rb')as source:shutil.copyfileobj(source,f,1048576)
 assert fp(archive)==parts['archive']==dict(bytes=751995332,sha256='136e2aaa710f7e51c2ed31ef42054309a7c2c13be7a85e2d849db8cfbeaf436f')
 seen={};members=set()
 with tarfile.open(archive,mode='r|gz')as tar:
  for m in tar:
   p=PurePosixPath(m.name);assert not p.is_absolute()and '..'not in p.parts and m.name not in members
   members.add(m.name)
   if m.isdir():continue
   assert m.isfile()and m.name in index['files']
   target=out/m.name if m.name in SELECTED else None
   if target:target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
   sink=target.open('xb')if target else None
   h=hashlib.sha256();size=0
   try:
    with tar.extractfile(m)as f:
     for b in iter(lambda:f.read(1048576),b''):
      size+=len(b);h.update(b)
      if sink:sink.write(b)
   finally:
    if sink:sink.close()
   pin=dict(bytes=size,sha256=h.hexdigest());assert pin==index['files'][m.name];seen[m.name]=pin
 assert set(seen)==set(index['files'])and len(seen)==728
 write(OUT/'saved-route-restoration.json',dict(producer=run,release=release,tag=tag,archive=parts['archive'],full_members_authenticated=len(seen),selected={n:seen[n]for n in sorted(SELECTED)},source_unchanged=True,native_bytes_cloud_only=True))
 shutil.rmtree(transport)
 return {n:seen[n]for n in sorted(SELECTED)}
def main():
 OUT.mkdir(exist_ok=False);pins=own_sources();ctx,proof=admission()
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ORIGINAL,text=True).strip()==BASE
 sys.path.insert(0,str(ORIGINAL/'scripts'))
 import cloud_mainchip_bulk_postdrt_antenna as base
 import cloud_mainchip_saved_diode_routing as qualification
 import cloud_mainchip_bounded_route_stage as frozen_boundary
 import mainchip_stale_wire_routing as inherited
 f,c,p,tail,build=base.f,base.c,base.p,base.tail,base.build
 inherited_manifest=frozen_boundary.source_gate()
 base.reservation(ctx,proof,f.api('releases/'+str(proof['release_id'])),f.api('git/ref/tags/'+proof['tag']))
 work=Path(os.environ['RUNNER_TEMP'])/(GROUP+'-'+ctx['token']);assert not work.exists();work.mkdir(mode=0o700)
 write(work/'owner.json',ctx);out=work/'out';out.mkdir()
 report=dict(status='IN_PROGRESS',source=ctx['source'],run_id=ctx['run_id'],commands=[],terminal_errors=[],creation_attempted=False,**p.FLAGS)
 identity=None;primary=None;restored=False;projected=False;native_pins={}
 def command(label,argv,timeout=120):return build.execute_command(report,out,label,argv,timeout)
 def inspect(value):return f.decode(subprocess.check_output(['docker','inspect',value],timeout=30))[0]
 try:
  assert shutil.disk_usage(work).free>=24*1024**3
  base.acquire_current(work,OUT)
  tail.restore_prefix(work,out);restored=True
  native_pins=acquire_route(work,out)
  projection=work/'tail-source';projection.mkdir()
  methods=c.method(ORIGINAL)
  source_paths=set(inherited_manifest['files'])|set(methods['protected'])|{qualification.MANIFEST,frozen_boundary.MANIFEST,c.METHOD}
  for n in sorted(source_paths):
   src=c.secure_file(ORIGINAL,n);dest=projection/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
  p.source_guard(projection);c.method(projection)
  extras={n:pins[n]for n in NEW_NATIVE}
  for n in NEW_NATIVE:
   dest=projection/n;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest)
  write(work/'scoped-source-pins.json',extras)
  shutil.copyfile(ROOT/'scripts/mainchip_scoped_counterpart_restoration_inner.py',work/'inner.py')
  assert fp(work/'inner.py')==pins['scripts/mainchip_scoped_counterpart_restoration_inner.py'];projected=True
  command('immutable-image-pull',['docker','pull',c.IMAGE],1800)
  c.validate_image(f.decode(command('image-inspect',['docker','image','inspect',c.IMAGE]))[0])
  argv=inherited.hosted_argv(c.create_argv,ctx,work,os.getuid(),os.getgid())
  identity=build.create_owned(ctx,work,report,command,argv);c.validate_container(inspect(identity),ctx,work)
  command('bulk-postdrt-owned-container',['docker','start','--attach',identity],18000)
  inner=f.decode((out/'bulk-postdrt-scoped-inner-result.json').read_bytes())
  assert inner['status']=='COMPLETE_SCOPED_CLASS_RESTORATION_AND_ORIGINAL_AUDITS'
  assert inner['restoration_and_original_audits_completed']is True
  assert all(inner[k]==0 for k in ('current_route_calls','current_repair_calls','current_reconstruction_calls'))
  assert all(inner[k]is False for k in p.FLAGS)
  report['native_result']=inner
 except BaseException as exc:primary=exc;report['error']=c.error_record('scoped-restoration-host',exc)
 finally:
  c.attempt(report,'owned-container-cleanup',lambda:build.cleanup_owned(ctx,work,report,identity,report['creation_attempted'],inspect,command))
  c.attempt(report,'own-source-unchanged',own_sources)
  c.attempt(report,'original-source-unchanged',frozen_boundary.source_gate)
  if restored:c.attempt(report,'frozen-prefix-unchanged',lambda:c.frozen_unchanged(work,f.decode((work/'frozen-manifest.json').read_bytes())))
  if projected:
   c.attempt(report,'original-projection-unchanged',lambda:c.method(work/'tail-source'))
   for n in NEW_NATIVE:c.attempt(report,'new-projection-'+n,lambda n=n:c.require(fp(work/'tail-source'/n)==pins[n],'new native source changed'))
   c.attempt(report,'inner-source-unchanged',lambda:c.require(fp(work/'inner.py')==pins['scripts/mainchip_scoped_counterpart_restoration_inner.py'],'inner source changed'))
  for n,pin in native_pins.items():c.attempt(report,'saved-route-input-'+n,lambda n=n,pin=pin:c.require(fp(out/n)==pin,'saved-route input changed'))
  c.attempt(report,'current-input-unchanged',lambda:c.require(fp(work/'current-input.odb')==p.INPUT,'current measured input changed'))
  if identity is not None:
   state=report.get('container_terminal',{}).get('State',{})
   c.attempt(report,'container-terminal',lambda:c.require(not state.get('Running',True)and state.get('ExitCode')==0 and state.get('OOMKilled')is False and not state.get('Error'),'native container failed'))
  c.attempt(report,'permanent-native-publication',lambda:report.update(native_publication=base.publish_capsule(ctx,proof,work,out,OUT)))
  c.attempt(report,'preserve-derived-outputs',lambda:base.preserve_outputs(out,OUT,report))
  c.attempt(report,'retained-native-workspace',lambda:base.retained_workspace(ctx,work,out,report))
  report['status']='COMPLETE_SCOPED_RESTORATION_EXPERIMENT'if primary is None and not report['terminal_errors']else'FAIL_SCOPED_RESTORATION_EXPERIMENT'
  write(OUT/'result.json',report)
 return 0 if report['status']=='COMPLETE_SCOPED_RESTORATION_EXPERIMENT'else 1
if __name__=='__main__':
 try:sys.exit(main())
 except BaseException as exc:
  if isinstance(exc,SystemExit):raise
  OUT.mkdir(exist_ok=True);write(OUT/'host-failure.json',dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
  raise
