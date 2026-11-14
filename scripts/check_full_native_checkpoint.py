# SPDX-License-Identifier: Apache-2.0
"""Cloud-only capability experiment; no chip simulation acceptance."""
import zipfile,io
import pathlib,subprocess,json,hashlib,os,time,sys,tarfile,platform,re
P=pathlib.Path;out=P('out');out.mkdir(exist_ok=True);root=P('/tmp/nssoc-full-native-checkpoint');stage=sys.argv[1]
r={'scope':'First 20000 cycles of original full native chip MBIST compared across separate runners; not completed MBIST/boot or physical acceptance','stage':stage,'passed':False,'chip_acceptance':False,'source_sha':os.environ.get('GITHUB_SHA')}
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

try:
 inputs=prepare()
 r['runtime']=runtime()
 check=run(['sudo','criu','check']);r['kernel_preflight']=check.stdout[-4000:]+check.stderr[-4000:]
 if stage=='dump':
  assert not root.exists();root.mkdir();(root/'images').mkdir()
  cmd=list(inputs['compile_command']);cmd[0]='/tmp/oss-cad-suite/bin/iverilog';cmd[cmd.index('-o')+1]=str(root/'sim.vvp')
  compiled=run(cmd);r['compile_stderr']=compiled.stderr[-4000:]
  sys.path.insert(0,str(repo/'hw/soc/flow'))
  from sim_logic_boot_gl import check_native_cell
  gate=check_native_cell('iverilog',cmd[0],repo/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v',root/'cell-gate')
  assert gate['passed'];r['native_cell_gate']=gate
  command=['/tmp/oss-cad-suite/bin/vvp','-i',str(root/'sim.vvp'),'+flash0='+str(build/'rtl/flash0.hex')]
  with (root/'baseline.log').open('w') as f,open('/dev/null') as stdin:
   baseline=subprocess.Popen(command,stdin=stdin,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  try:reference=wait_prefix(root/'baseline.log',20000,baseline)
  finally:
   baseline.terminate();baseline.wait(timeout=20)
  (root/'baseline-prefix.log').write_bytes(reference)
  with (root/'resumed.log').open('w') as f,open('/dev/null') as stdin:
   proc=subprocess.Popen(command,stdin=stdin,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  wait_prefix(root/'resumed.log',10000,proc)
  assert prefix((root/'resumed.log').read_bytes(),20000) is None,'Checkpoint was too late'
  r['mapped_file_hashes']=mapped_files(proc.pid)
  run(['sudo','criu','dump','-t',str(proc.pid),'-D',str(root/'images'),'--shell-job','--cpu-cap=all','-o','dump.log','-v4'])
  proc.wait(timeout=20)
  captured=(root/'resumed.log').read_bytes();assert captured and b'LOGICROM_GL PASS' not in captured
  r['checkpoint_prefix_bytes']=len(captured);r['checkpoint_prefix_sha256']=hashlib.sha256(captured).hexdigest()
  r['baseline_sha256']=digest(root/'baseline-prefix.log');r['runtime_manifest']=r['runtime']
  (root/'manifest.json').write_text(json.dumps(r,indent=2))
  run(['sudo','tar','-czf','checkpoint.tgz','-C','/tmp','nssoc-full-native-checkpoint'])
  run(['sudo','chown',str(os.getuid())+':'+str(os.getgid()),'checkpoint.tgz'])
  r['checkpoint_tgz_sha256']=digest('checkpoint.tgz');r['passed']=True
 elif stage=='restore':
  assert not root.exists()
  dump=json.loads(P('dump-result.json').read_text());assert dump['passed']
  assert r['original_input_hashes']==dump['original_input_hashes']
  assert r['original_inputs_sha256']==dump['original_inputs_sha256']
  assert digest('checkpoint.tgz')==dump['checkpoint_tgz_sha256']
  assert r['runtime']==dump['runtime_manifest'], 'Runtime/kernel/library identity changed; no compatibility bypass'
  run(['sudo','tar','-xzf','checkpoint.tgz','-C','/tmp'])
  assert all(P(p).is_file() and digest(p)==sha for p,sha in dump['mapped_file_hashes'].items()),'Mapped runtime files differ'
  assert digest(root/'resumed.log')==dump['checkpoint_prefix_sha256']
  run(['sudo','criu','restore','-D',str(root/'images'),'--shell-job','--cpu-cap=all','--restore-detached','--pidfile',str(root/'restored.pid'),'-o','restore.log','-v4'])
  pid=int(run(['sudo','cat',str(root/'restored.pid')]).stdout)
  try:observed=wait_prefix(root/'resumed.log',20000)
  finally:run(['sudo','kill','-TERM',str(pid)])
  assert observed==(root/'baseline-prefix.log').read_bytes(),'Native full-chip interrupted/uninterrupted prefixes differ'
  r['trace_sha256']=hashlib.sha256(observed).hexdigest();r['trace_lines']=len(observed.splitlines());r['compared_through_cycle']=20000;r['passed']=True
 else:raise ValueError(stage)
except Exception as e:
 r['error']=repr(e)
 if isinstance(e,subprocess.CalledProcessError):r['native_error']={'stdout':e.stdout[-6000:],'stderr':e.stderr[-6000:]}
 raise
finally:
 # Persist the native verdict before attempting privileged diagnostic reads.
 (out/(stage+'-result.json')).write_text(json.dumps(r,indent=2))
 r['criu_logs']={}
 for log in (root/'images').glob('*.log'):
  capture=subprocess.run(['sudo','tail','-c','10000',str(log)],capture_output=True,text=True,timeout=15)
  r['criu_logs'][log.name]={'returncode':capture.returncode,'text':capture.stdout,'stderr':capture.stderr}

 (out/(stage+'-result.json')).write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k in ['stage','passed','error','native_error']}))
