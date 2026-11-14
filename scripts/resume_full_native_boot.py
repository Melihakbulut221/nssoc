# SPDX-License-Identifier: Apache-2.0
"""Cloud-only capability experiment; no chip simulation acceptance."""
import zipfile,io,ctypes
import pathlib,subprocess,json,hashlib,os,time,sys,tarfile,platform,re
P=pathlib.Path;out=P('out');out.mkdir(exist_ok=True);root=P('/tmp/nssoc-full-native-checkpoint');stage='resume'
r={'scope':'Original full native MBIST and firmware boot continuation. Pending checkpoint is not boot acceptance; no routed timing/SDF/serial PHY or manufacturing acceptance','stage':stage,'passed':False,'chip_acceptance':False,'source_sha':os.environ.get('GITHUB_SHA')}
def digest(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(cmd,**kwargs):return subprocess.run(cmd,check=True,text=True,capture_output=True,timeout=600,**kwargs)
def runtime():
 return {'suite_sha256':'8c6010f1cc37f2083a472778ef7e2e756409e377e547f62c11a16f5d96a8f982','kernel':platform.release(),'uid':os.getuid(),'criu':run(['criu','--version']).stdout.strip(),'vvp_version':run(['/tmp/oss-cad-suite/bin/vvp','-V']).stderr}
def mapped_files(pid):
 paths=set()
 for line in P('/proc/'+str(pid)+'/maps').read_text().splitlines():
  parts=line.split(None,5)
  if len(parts)==6 and parts[5].startswith('/'):
   path=parts[5];assert not path.endswith(' (deleted)'),path
   paths.add(path)
 assert paths
 return {p:digest(p) for p in sorted(paths)}

ORIGINAL='3fd0fded2d874efa0109d8558a213380de1f36a7'
repo=P.cwd();build=repo/'hw/soc/out/corrpre-pcie-mbist-native-boot'
def prefix(data,cycle):
 lines=data.splitlines(keepends=True)
 for i,line in enumerate(lines):
  if re.search(rb'^LOGICROM_GL progress cycles='+str(cycle).encode()+rb' ',line):return b''.join(lines[:i+1])
 return None
def wait_prefix(path,cycle,proc=None):
 end=time.monotonic()+1200
 while time.monotonic()<end:
  data=path.read_bytes()
  assert b'FATAL' not in data and b'ERROR' not in data,'Native simulation reported an error'
  found=prefix(data,cycle)
  if found is not None:return found
  if proc is not None:assert proc.poll() is None,'Native simulator exited before observation'
  time.sleep(.2)
 raise TimeoutError('Native workload observation exceeded 1200s')
def prepare():
 # Recovery is downloaded only on the cloud runner, never the user computer.
 payload=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14097721346/zip'],timeout=180)
 assert hashlib.sha256(payload).hexdigest()=='0c938debffdf355789437cd647020d460d3aa7ad6f7a45e0a6fcdf0fc509e676'
 z=zipfile.ZipFile(io.BytesIO(payload));names=[n for n in z.namelist() if n.endswith('gates/inputs.json')];assert len(names)==1
 pre=names[0][:-len('gates/inputs.json')]
 assert not build.exists();build.mkdir(parents=True)
 for info in z.infolist():
  assert info.filename.startswith(pre)
  name=info.filename[len(pre):];p=build/name
  assert p.resolve().is_relative_to(build.resolve())
  if info.is_dir():p.mkdir(parents=True,exist_ok=True)
  else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(info))
 inputs=json.loads((build/'gates/inputs.json').read_text())
 assert inputs['cycle_bound']==3000000
 for path,row in inputs['sources'].items():
  p=P(path);assert p.is_relative_to(repo)
  rel=p.relative_to(repo).as_posix()
  if rel in ['hw/soc/tb/tb_soc_logic_boot_gl.v','hw/soc/tb/flash_w25q128jv.v','hw/soc/tb/mapped_mbist_boot_monitor.v']:
   content=subprocess.check_output(['gh','api','-H','Accept: application/vnd.github.raw+json','repos/Melihakbulut221/nssoc/contents/'+rel+'?ref='+ORIGINAL],timeout=60)
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
  assert p.is_file() and digest(p)==row['sha256'] and p.stat().st_size==row['bytes'],path
 assert '-DNSSOC_GL_MBIST' in inputs['compile_command'] and '-DNSSOC_GL_PCIE_ASYNC' in inputs['compile_command']
 r['original_source']=ORIGINAL;r['original_input_hashes']=inputs['sources']
 r['original_inputs_sha256']=digest(build/'gates/inputs.json')
 return inputs

def repo_api(path):
 return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path],timeout=60))
def verify_prerequisites():
 for runid,sha in [(43557919707,'104cfcfbe16b589bf3ee5df1b51d0374c1d19eb2'),(43558336660,'292a3313f7c0fca20c3fa65cc5de910003083162'),(43558722004,'7d118a79f0bdfab6aa60b5bccb1cdb9dd836e2b8')]:
  state=repo_api('actions/runs/'+str(runid));assert state['status']=='completed' and state['conclusion']=='success' and state['head_sha']==sha
 r['prerequisite_runs']=[43557919707,43558336660,43558722004]
def last_cycle(data):
 values=re.findall(rb'^LOGICROM_GL progress cycles=(\d+) ',data,re.M)
 return int(values[-1]) if values else 0
try:
 verify_prerequisites();inputs=prepare();r['runtime']=runtime()
 r['kernel_preflight']=run(['sudo','criu','check']).stdout
 assert not root.exists()
 dump=json.loads(P('resume-result.json').read_text())
 assert dump['source_sha']=='7d118a79f0bdfab6aa60b5bccb1cdb9dd836e2b8'
 assert dump['checkpoint_saved'] is True and dump['completed_boot'] is False and dump['passed'] is False
 assert dump['stage_status']=='checkpointed_pending_boot' and 'error' not in dump
 assert dump['image_directory']=='images-43558722004' and dump['last_progress_cycle']==1260000
 assert dump['checkpoint_tgz_sha256']=='8f480f6170a83b41ed1be10ef15ac5beae08b3f77e635575274e6f1ad6632181'
 assert dump['checkpoint_prefix_sha256']=='a2b5e52f0f115f5c17249a7eea6528f2b50814d1be91992f5b7b66714f5223e5'
 assert dump['parent_checkpoint']=={'run':43557919707,'native_artifact':14099590587,'result_artifact':14099221726,'tgz_sha256':'704cc23ee221ab0d09f5f21b0bee1c2b5f4a7cf250c80c8b4ee90ca0cafced2e'}
 assert r['original_input_hashes']==dump['original_input_hashes'] and r['original_inputs_sha256']==dump['original_inputs_sha256']
 assert digest('next-checkpoint.tgz')==dump['checkpoint_tgz_sha256']
 assert r['runtime']==dump['runtime_manifest'],'Runtime identity changed'
 run(['sudo','tar','-xzf','next-checkpoint.tgz','-C','/tmp'])
 assert all(P(p).is_file() and digest(p)==sha for p,sha in dump['mapped_file_hashes'].items()),'Mapped runtime differs'
 assert digest(root/'resumed.log')==dump['checkpoint_prefix_sha256']
 P('next-checkpoint.tgz').rename('parent-checkpoint.tgz')
 libc=ctypes.CDLL(None,use_errno=True);assert libc.prctl(36,1,0,0,0)==0,os.strerror(ctypes.get_errno())
 enabled=ctypes.c_int();assert libc.prctl(37,ctypes.byref(enabled),0,0,0)==0 and enabled.value==1
 r['child_subreaper']=True;r['completed_boot']=False;r['checkpoint_saved']=False
 r['parent_checkpoint']={'run':43558722004,'native_artifact':14104748996,'result_artifact':14105022987,'tgz_sha256':dump['checkpoint_tgz_sha256']}
 initial_cycle=last_cycle((root/'resumed.log').read_bytes());assert initial_cycle==1260000
 run(['sudo','criu','restore','-D',str(root/dump['image_directory']),'--shell-job','--cpu-cap=all','--restore-detached','--pidfile',str(root/'restored.pid'),'-o','restore-long.log','-v4'])
 pid=int(run(['sudo','cat',str(root/'restored.pid')]).stdout)
 parent=int(next(line.split()[1] for line in P('/proc/'+str(pid)+'/status').read_text().splitlines() if line.startswith('PPid:')))
 assert parent==os.getpid(),'Restored process not adopted'
 start=time.monotonic();next_report=start;code=None
 while time.monotonic()-start<10800:
  child,status=os.waitpid(pid,os.WNOHANG)
  if child==pid:code=os.waitstatus_to_exitcode(status);break
  data=(root/'resumed.log').read_bytes()
  assert not re.search(rb'(?im)(?:FATAL:|ERROR:|%Fatal|%Error)',data),'Native run reported failure'
  if time.monotonic()>=next_report:
   print(json.dumps({'elapsed_s':round(time.monotonic()-start),'last_progress_cycle':last_cycle(data)}),flush=True);next_report=time.monotonic()+60
  time.sleep(2)
 r['segment_seconds']=time.monotonic()-start
 if code is None:
  image_dir=root/('images-'+os.environ['GITHUB_RUN_ID']);image_dir.mkdir()
  r['mapped_file_hashes']=mapped_files(pid)
  run(['sudo','criu','dump','-t',str(pid),'-D',str(image_dir),'--shell-job','--cpu-cap=all','-o','dump.log','-v4'])
  child,status=os.waitpid(pid,0);assert child==pid
  r['checkpoint_stop_returncode']=os.waitstatus_to_exitcode(status)
  data=(root/'resumed.log').read_bytes()
  assert last_cycle(data)>initial_cycle,'No measurable simulation progress'
  assert not re.search(rb'(?im)(?:FATAL:|ERROR:|%Fatal|%Error)',data)
  r.update(checkpoint_saved=True,stage_status='checkpointed_pending_boot',image_directory=image_dir.name,
    checkpoint_prefix_bytes=len(data),checkpoint_prefix_sha256=hashlib.sha256(data).hexdigest(),
    runtime_manifest=r['runtime'],last_progress_cycle=last_cycle(data))
  (root/'manifest.json').write_text(json.dumps(r,indent=2))
  run(['sudo','tar','-czf','next-checkpoint.tgz','-C','/tmp','nssoc-full-native-checkpoint'])
  run(['sudo','chown',str(os.getuid())+':'+str(os.getgid()),'next-checkpoint.tgz'])
  r['checkpoint_tgz_sha256']=digest('next-checkpoint.tgz')
 else:
  sys.path.insert(0,str(repo/'hw/soc/flow'))
  from sim_logic_boot_gl import boot_checks
  r['native_returncode']=code
  text=(root/'resumed.log').read_text()
  r['boot_checks']=boot_checks(text,code,'packet-async','system-ethernet')
  r['sources_unchanged']=all(digest(p)==row['sha256'] for p,row in inputs['sources'].items())
  assert r['boot_checks']['passed'] and r['sources_unchanged'],'Full native MBIST/firmware acceptance failed'
  r.update(completed_boot=True,passed=True,stage_status='completed_native_boot')
except Exception as e:
 r['error']=repr(e)
 if isinstance(e,subprocess.CalledProcessError):r['native_error']={'stdout':str(e.stdout)[-6000:],'stderr':str(e.stderr)[-6000:]}
 raise
finally:
 # CRIU writes detailed errors into its work directory, not stderr. Preserve
 # classified diagnostics even when the restore itself fails.
 if 'dump' in globals() and 'image_directory' in dump:
  logpath=root/dump['image_directory']/'restore-long.log'
  if logpath.is_file():
   capture=subprocess.run(['sudo','cat',str(logpath)],capture_output=True,timeout=30)
   if capture.returncode==0:
    raw=capture.stdout;logtext=raw.decode(errors='replace')
    for key in ('GH_TOKEN','GITHUB_TOKEN'):
     if os.environ.get(key):logtext=logtext.replace(os.environ[key],'[REDACTED]')
    nativeout=P('out-native');nativeout.mkdir(exist_ok=True)
    (nativeout/'criu-restore.log').write_text(logtext)
    errors=[line for line in logtext.splitlines() if re.search(r'\b(?:Error|Warn|Warning)\b',line)]
    r['criu_restore_log']={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'diagnostics':errors,'full_log_cloud_only':True}
 (out/'resume-result.json').write_text(json.dumps(r,indent=2))
 if (root/'resumed.log').exists():(out/'native-boot.log').write_bytes((root/'resumed.log').read_bytes())
 print(json.dumps({k:v for k,v in r.items() if k in ['passed','completed_boot','checkpoint_saved','stage_status','error']}),flush=True)
