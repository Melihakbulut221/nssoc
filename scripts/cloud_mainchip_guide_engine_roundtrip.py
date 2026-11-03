"""Cloud-only explicit guide-batch engine full-chip qualification; no routing."""
import hashlib,importlib,json,os,shutil,subprocess,sys,tarfile,time,traceback,types
import mainchip_full64_output_preservation as preservation
from mainchip_guide_engine_acquisition import acquire
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=ROOT/'original'
OUT=ROOT/'full64-native-evidence'
BASE='7a0776718ec37a106b7dfde0cbd477c6a2a5522f'
REPO='repos/Melihakbulut221/nssoc/'
GROUP='mainchip-bulk-postdrt-antenna'
MANIFEST='scripts/mainchip-snapshot-reload-pins.json'
NEW_NATIVE=('scripts/mainchip_guide_engine_inner.py','scripts/mainchip_guide_engine_native.py','scripts/mainchip_guide_engine_acquisition.py','scripts/mainchip_route47_memory.py','scripts/mainchip-guide-engine-built-inputs.json','scripts/mainchip-guide-engine-reference.json')
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
 assert os.environ['GITHUB_REF']=='refs/heads/codex/mainchip-guide-tiled-roundtrip'
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
 identity=None;primary=None;restored=False;projected=False;native_pins={};reference_pins={};engine_pins={}
 def command(label,argv,timeout=120):return build.execute_command(report,out,label,argv,timeout)
 def inspect(value):return f.decode(subprocess.check_output(['docker','inspect',value],timeout=30))[0]
 try:
  assert shutil.disk_usage(work).free>=24*1024**3
  base.acquire_current(work,OUT)
  tail.restore_prefix(work,out);restored=True
  engine_config=json.loads((ROOT/'scripts/mainchip-guide-engine-built-inputs.json').read_bytes())
  reference_config=json.loads((ROOT/'scripts/mainchip-guide-engine-reference.json').read_bytes())
  engine_pins=acquire(engine_config,'outputs.json','parts.json',('openroad','runtime-dependencies.json'),work,out,'guide-engine',engine=True)
  os.chmod(work/'guide-engine/openroad',0o755)
  assert fp(work/'guide-engine/openroad')==engine_config['binary']
  assert json.loads((work/'runtime-dependencies.json').read_bytes())==engine_config['runtime_dependencies']
  reference_pins=acquire(reference_config,'candidate-outputs.json','candidate-parts.json',reference_config['selected'],work,out,'guide-reference')
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
  shutil.copyfile(ROOT/'scripts/mainchip_guide_engine_inner.py',work/'inner.py')
  assert fp(work/'inner.py')==pins['scripts/mainchip_guide_engine_inner.py'];projected=True
  command('immutable-image-pull',['docker','pull',c.IMAGE],1800)
  c.validate_image(f.decode(command('image-inspect',['docker','image','inspect',c.IMAGE]))[0])
  argv=inherited.hosted_argv(c.create_argv,ctx,work,os.getuid(),os.getgid())
  identity=build.create_owned(ctx,work,report,command,argv);c.validate_container(inspect(identity),ctx,work)
  command('bulk-postdrt-owned-container',['docker','start','--attach',identity],21600)
  inner=f.decode((out/'bulk-postdrt-snapshot-inner-result.json').read_bytes())
  assert inner['status']=='PASS_GUIDE_ENGINE_ACTUAL_CHIP_QUALIFICATION' and inner['guide_engine_observation_complete'] is True
  assert inner['snapshot_reload_qualified']is True and inner['routing_complete']is False
  assert inner['current_audit_calls']==3 and inner['current_route_calls']==0 and inner['current_repair_calls']==0 and inner['current_reconstruction_calls']==0 and inner['current_class_import_phases']==0
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
   c.attempt(report,'inner-source-unchanged',lambda:c.require(fp(work/'inner.py')==pins['scripts/mainchip_guide_engine_inner.py'],'inner source changed'))
  for n,pin in native_pins.items():c.attempt(report,'saved-route-input-'+n,lambda n=n,pin=pin:c.require(fp(out/n)==pin,'saved-route input changed'))
  c.attempt(report,'current-input-unchanged',lambda:c.require(fp(work/'current-input.odb')==p.INPUT,'current measured input changed'))
  if identity is not None:
   state=report.get('container_terminal',{}).get('State',{})
   c.attempt(report,'container-terminal',lambda:c.require(not state.get('Running',True)and state.get('ExitCode')==0 and state.get('OOMKilled')is False and not state.get('Error'),'native container failed'))
  for label,selected in (('guide-reference',reference_pins),('guide-engine',engine_pins)):
   for name,pin in selected.items():c.attempt(report,label+'-'+name,lambda name=name,pin=pin,label=label:c.require(fp(work/label/name)==pin,'authenticated input changed'))
  candidate_pin=json.loads((ROOT/'scripts/mainchip-guide-engine-reference.json').read_bytes())['index']['files']['work/bulk-postdrt-antenna/narrow47-restored.odb']
  c.attempt(report,'permanent-native-publication',lambda:report.update(native_publication=types.FunctionType(base.publish_capsule.__code__,dict(base.publish_capsule.__globals__,CURRENT=candidate_pin),base.publish_capsule.__name__,base.publish_capsule.__defaults__,base.publish_capsule.__closure__)(ctx,proof,work,out,OUT)))
  c.attempt(report,'preserve-derived-outputs',lambda:preservation.preserve_outputs(base,out,OUT,report))
  c.attempt(report,'retained-native-workspace',lambda:base.retained_workspace(ctx,work,out,report))
  report['status']='PASS_CLOUD_GUIDE_ENGINE_ACTUAL_CHIP_QUALIFICATION'if primary is None and not report['terminal_errors']else'FAIL_CLOUD_GUIDE_ENGINE_ACTUAL_CHIP_QUALIFICATION'
  write(OUT/'result.json',report)
 return 0 if report['status']=='PASS_CLOUD_GUIDE_ENGINE_ACTUAL_CHIP_QUALIFICATION'else 1
if __name__=='__main__':
 try:sys.exit(main())
 except BaseException as exc:
  if isinstance(exc,SystemExit):raise
  OUT.mkdir(exist_ok=True);write(OUT/'host-failure.json',dict(error=repr(exc),traceback=traceback.format_exc(),physical_acceptance=False,timing_accepted=False,full_phy_accepted=False))
  raise
