"""Cloud-only native partial-snapshot roundtrip and original scoped material audit."""
import hashlib,importlib,json,os,shutil,subprocess,sys,tarfile,time,traceback,types
import mainchip_full64_output_preservation as preservation
from mainchip_snapshot_reload_contract import validate_archive_member
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=ROOT/'original'
OUT=ROOT/'full64-native-evidence'
BASE='7a0776718ec37a106b7dfde0cbd477c6a2a5522f'
REPO='repos/Melihakbulut221/nssoc/'
GROUP='mainchip-bulk-postdrt-antenna'
MANIFEST='scripts/mainchip-snapshot-reload-pins.json'
NEW_NATIVE=('scripts/mainchip_snapshot_reload_contract.py','scripts/mainchip_snapshot_reload_inner.py','scripts/mainchip_snapshot_reload_native.py','scripts/mainchip_route47_contract.py','scripts/mainchip_route47_import.py','scripts/mainchip_route47_native.py','scripts/mainchip-route47-selected.json')
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
 assert os.environ['GITHUB_REF']=='refs/heads/codex/mainchip-route47-repair'
 source=os.environ['GITHUB_SHA'];rid=int(os.environ['GITHUB_RUN_ID']);control=int(os.environ['CONTROL_RUN'])
 assert source==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 run=api('actions/runs/'+str(control));jobs=api('actions/runs/'+str(control)+'/jobs?per_page=100')
 assert control!=rid and run['head_sha']==source and run['status']=='completed'and run['conclusion']=='success'and run['run_attempt']==1
 assert run['event']=='workflow_dispatch'and run['path']=='.github/workflows/cloud-evidence-summary.yml'
 assert jobs['total_count']==len(jobs['jobs'])==2 and {j['name']:j['conclusion']for j in jobs['jobs']}=={'source-controls':'success','native-routing':'skipped'}
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
def acquire_snapshot(work,out,pins):
 config=json.loads((ROOT/'scripts/mainchip-snapshot-reload-inputs.json').read_bytes())
 producer=config['producer']
 assert config['schema']=='mainchip-partial-snapshot-reload-inputs-v1'
 assert producer==dict(run=41349316524,source='a47bb1895ad12fdebddeb055dc5e3e9c414c04e0',release=430851918,tag='cloud-results-41349316524-1-mainchip-bulk-postdrt-antenna')
 run=api('actions/runs/'+str(producer['run']));rel=api('releases/'+str(producer['release']))
 assert run['status']=='completed'and run['conclusion']=='failure'and run['head_sha']==producer['source']
 assert run['run_attempt']==1 and rel['target_commitish']==producer['source']and rel['tag_name']==producer['tag']
 assert api('git/ref/tags/'+producer['tag'])['object']['sha']==producer['source']
 live={a['name']:a for a in rel['assets']};assert set(live)==set(config['assets'])
 transport=work/'snapshot-transport';transport.mkdir()
 for name,expected in config['assets'].items():
  actual=live[name]
  assert actual['id']==expected['id']and actual['size']==expected['bytes']and actual['digest']=='sha256:'+expected['sha256']
  target=transport/name
  with target.open('xb')as dest:subprocess.run(['gh','api',REPO+'releases/assets/'+str(expected['id']),'-H','Accept: application/octet-stream'],stdout=dest,check=True,timeout=900)
  assert fp(target)=={k:expected[k]for k in ('bytes','sha256')}
 index=json.loads((transport/'candidate-outputs.json').read_bytes());parts=json.loads((transport/'candidate-parts.json').read_bytes())
 assert index==config['index']and parts==config['parts']
 assert index['source']==producer['source']and index['run']==producer['run']and index['attempt']==1
 archive=transport/'snapshot.tar.gz'
 with archive.open('xb')as dest:
  for part in parts['parts']:
   assert fp(transport/part['name'])=={k:part[k]for k in ('bytes','sha256')}
   with (transport/part['name']).open('rb')as src:shutil.copyfileobj(src,dest,4*1024**2)
 assert fp(archive)==parts['archive']
 expected=index['files'];selected=set(config['selected'])
 assert len(expected)==738 and selected<=set(expected)
 destination=work/'reload-inputs';destination.mkdir()
 observed={};names=set()
 with tarfile.open(archive,'r|gz')as tar:
  for member in tar:
   name=member.name;path=PurePosixPath(name)
   validate_archive_member(name,member.isfile(),member.size,expected,names)
   source=tar.extractfile(member);h=hashlib.sha256();count=0;dest=None
   if name in selected:
    target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);dest=target.open('xb')
   try:
    for data in iter(lambda:source.read(4*1024**2),b''):
     h.update(data);count+=len(data)
     if dest is not None:dest.write(data)
   finally:
    if dest is not None:dest.close()
   observed[name]=dict(bytes=count,sha256=h.hexdigest());assert observed[name]==expected[name]
 assert observed==expected
 selected_pins={name:expected[name]for name in selected}
 for name,pin in selected_pins.items():assert fp(destination/name)==pin
 write(work/'snapshot-selected-pins.json',selected_pins)
 write(out/'bulk-postdrt-snapshot-acquisition.json',dict(producer=producer,assets=config['assets'],all_members=observed,selected=selected_pins,
  complete_archive_authenticated=True,native_bytes_remain_in_cloud=True,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
 shutil.rmtree(transport)
 return selected_pins

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
 identity=None;primary=None;restored=False;projected=False;native_pins={};snapshot_pins={}
 def command(label,argv,timeout=120):return build.execute_command(report,out,label,argv,timeout)
 def inspect(value):return f.decode(subprocess.check_output(['docker','inspect',value],timeout=30))[0]
 try:
  assert shutil.disk_usage(work).free>=24*1024**3
  base.acquire_current(work,OUT)
  tail.restore_prefix(work,out);restored=True
  snapshot_pins=acquire_snapshot(work,out,pins)
  projection=work/'tail-source';projection.mkdir()
  methods=c.method(ORIGINAL)
  source_paths=set(inherited_manifest['files'])|set(methods['protected'])|{qualification.MANIFEST,frozen_boundary.MANIFEST,c.METHOD}
  for n in sorted(source_paths):
   src=c.secure_file(ORIGINAL,n);dest=projection/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
  p.source_guard(projection);c.method(projection)
  extras={n:pins[n]for n in NEW_NATIVE}
  for n in NEW_NATIVE:
   dest=projection/n;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest)
  baseline='scripts/mainchip-bounded-route-baseline.tcl'
  dest=projection/baseline
  if dest.exists():assert fp(dest)==pins[baseline]
  else:shutil.copyfile(ROOT/baseline,dest)
  write(work/'scoped-source-pins.json',extras)
  shutil.copyfile(ROOT/'scripts/mainchip_snapshot_reload_inner.py',work/'inner.py')
  assert fp(work/'inner.py')==pins['scripts/mainchip_snapshot_reload_inner.py'];projected=True
  command('immutable-image-pull',['docker','pull',c.IMAGE],1800)
  c.validate_image(f.decode(command('image-inspect',['docker','image','inspect',c.IMAGE]))[0])
  argv=inherited.hosted_argv(c.create_argv,ctx,work,os.getuid(),os.getgid())
  identity=build.create_owned(ctx,work,report,command,argv);c.validate_container(inspect(identity),ctx,work)
  command('bulk-postdrt-owned-container',['docker','start','--attach',identity],21600)
  inner=f.decode((out/'bulk-postdrt-snapshot-inner-result.json').read_bytes())
  assert inner['status']=='COMPLETE_ACTUAL47_NATIVE_ROUTE_OBSERVATION' and inner['narrow47_observation_complete'] is True
  assert inner['snapshot_reload_qualified']is True and inner['routing_complete']is False
  assert inner['current_audit_calls']==7 and inner['current_route_calls']==1 and inner['current_repair_calls']==0 and inner['current_reconstruction_calls']==6 and inner['current_class_import_phases']==3
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
   c.attempt(report,'inner-source-unchanged',lambda:c.require(fp(work/'inner.py')==pins['scripts/mainchip_snapshot_reload_inner.py'],'inner source changed'))
  for n,pin in native_pins.items():c.attempt(report,'saved-route-input-'+n,lambda n=n,pin=pin:c.require(fp(out/n)==pin,'saved-route input changed'))
  c.attempt(report,'current-input-unchanged',lambda:c.require(fp(work/'current-input.odb')==p.INPUT,'current measured input changed'))
  if identity is not None:
   state=report.get('container_terminal',{}).get('State',{})
   c.attempt(report,'container-terminal',lambda:c.require(not state.get('Running',True)and state.get('ExitCode')==0 and state.get('OOMKilled')is False and not state.get('Error'),'native container failed'))
  if snapshot_pins:
   for name,pin in snapshot_pins.items():c.attempt(report,'selected-snapshot-unchanged-'+name,lambda name=name,pin=pin:c.require(fp(work/'reload-inputs'/name)==pin,'selected partial snapshot input changed'))
  if not snapshot_pins:snapshot_pins={'work/bulk-postdrt-antenna/drt_iter20.odb':json.loads((ROOT/'scripts/mainchip-snapshot-reload-inputs.json').read_bytes())['index']['files']['work/bulk-postdrt-antenna/drt_iter20.odb']}
  c.attempt(report,'permanent-native-publication',lambda:report.update(native_publication=types.FunctionType(base.publish_capsule.__code__,dict(base.publish_capsule.__globals__,CURRENT=snapshot_pins['work/bulk-postdrt-antenna/drt_iter20.odb']),base.publish_capsule.__name__,base.publish_capsule.__defaults__,base.publish_capsule.__closure__)(ctx,proof,work,out,OUT)))
  c.attempt(report,'preserve-derived-outputs',lambda:preservation.preserve_outputs(base,out,OUT,report))
  c.attempt(report,'retained-native-workspace',lambda:base.retained_workspace(ctx,work,out,report))
  report['status']='COMPLETE_ACTUAL47_CLOUD_ROUTE_OBSERVATION'if primary is None and not report['terminal_errors']else'FAIL_ACTUAL47_CLOUD_ROUTE_OBSERVATION'
  write(OUT/'result.json',report)
 return 0 if report['status']=='COMPLETE_ACTUAL47_CLOUD_ROUTE_OBSERVATION'else 1
if __name__=='__main__':
 try:sys.exit(main())
 except BaseException as exc:
  if isinstance(exc,SystemExit):raise
  OUT.mkdir(exist_ok=True);write(OUT/'host-failure.json',dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
  raise
