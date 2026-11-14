# SPDX-License-Identifier: Apache-2.0
"""Cloud-only capability experiment; no chip simulation acceptance."""
import pathlib,subprocess,json,hashlib,os,time,sys,tarfile,platform,re
P=pathlib.Path;out=P('out');out.mkdir(exist_ok=True);root=P('/tmp/nssoc-vvp-checkpoint-proof');stage=sys.argv[1]
r={'scope':'Pinned OSS suite native IHP flip-flop plus four-state delayed-event checkpoint, not SRAM/full MBIST acceptance','stage':stage,'passed':False,'chip_acceptance':False,'source_sha':os.environ.get('GITHUB_SHA')}
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

try:
 r['runtime']=runtime()
 check=run(['sudo','criu','check']);r['kernel_preflight']=check.stdout[-4000:]+check.stderr[-4000:]
 if stage=='dump':
  assert not root.exists();root.mkdir();(root/'images').mkdir()
  bench="""`timescale 1ns/1ps
module proof;
reg clk=0; always #5 clk=~clk;
integer count=0;
reg [7:0] q=8'bx10z1010;
reg [31:0] checksum=32'h12345678;
reg delayed=0;
wire native_q;
wire native_rst=(count%1000000)>10;
sg13g2_dfrbpq_1 ff(.CLK(clk),.RESET_B(native_rst),.D(q[0]),.Q(native_q));
always @(posedge clk) begin
 count=count+1;
 q <= {q[6:0],q[7]};
 delayed <= #7 ~delayed;
 checksum <= {checksum[30:0],checksum[31]^checksum[21]^checksum[1]^checksum[0]};
 if(count%100000==0) begin
  $display("TRACE %0d %b %b %08x %0t %b",count,q,delayed,checksum,$time,native_q); $fflush();
 end
 if(count==50000000) begin $display("CHECKPOINT_CONTROL_FINISHED"); $fflush(); $finish; end
end
endmodule
"""
  (root/'proof.v').write_text(bench)
  run(['/tmp/oss-cad-suite/bin/iverilog','-g2012','-s','proof','-o',str(root/'sim.vvp'),str(root/'proof.v'),str(P('hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v').resolve())])
  with (root/'baseline.log').open('w') as f:
   p=subprocess.run(['/tmp/oss-cad-suite/bin/vvp',str(root/'sim.vvp')],stdout=f,stderr=subprocess.STDOUT,timeout=600);assert p.returncode==0
  assert 'CHECKPOINT_CONTROL_FINISHED' in (root/'baseline.log').read_text()
  with (root/'resumed.log').open('w') as f,open('/dev/null') as stdin:
   proc=subprocess.Popen(['/tmp/oss-cad-suite/bin/vvp',str(root/'sim.vvp')],stdin=stdin,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  end=time.monotonic()+60
  while 'TRACE ' not in (root/'resumed.log').read_text():
   assert proc.poll() is None and time.monotonic()<end;time.sleep(.05)
  assert 'CHECKPOINT_CONTROL_FINISHED' not in (root/'resumed.log').read_text()
  r['mapped_file_hashes']=mapped_files(proc.pid)
  run(['sudo','criu','dump','-t',str(proc.pid),'-D',str(root/'images'),'--shell-job','--cpu-cap=all','-o','dump.log','-v4'])
  proc.wait(timeout=20)
  prefix=(root/'resumed.log').read_bytes();assert prefix and b'CHECKPOINT_CONTROL_FINISHED' not in prefix
  r['checkpoint_prefix_bytes']=len(prefix);r['checkpoint_prefix_sha256']=hashlib.sha256(prefix).hexdigest()
  r['baseline_sha256']=digest(root/'baseline.log');r['runtime_manifest']=r['runtime']
  (root/'manifest.json').write_text(json.dumps(r,indent=2))
  run(['sudo','tar','-czf','checkpoint.tgz','-C','/tmp','nssoc-vvp-checkpoint-proof'])
  run(['sudo','chown',str(os.getuid())+':'+str(os.getgid()),'checkpoint.tgz'])
  r['checkpoint_tgz_sha256']=digest('checkpoint.tgz');r['passed']=True
 elif stage=='restore':
  assert not root.exists()
  dump=json.loads(P('dump-result.json').read_text());assert dump['passed']
  assert digest('checkpoint.tgz')==dump['checkpoint_tgz_sha256']
  assert r['runtime']==dump['runtime_manifest'], 'Runtime/kernel/library identity changed; no compatibility bypass'
  assert all(P(p).is_file() and digest(p)==sha for p,sha in dump['mapped_file_hashes'].items()),'Mapped runtime files differ'
  run(['sudo','tar','-xzf','checkpoint.tgz','-C','/tmp'])
  assert digest(root/'resumed.log')==dump['checkpoint_prefix_sha256']
  run(['sudo','criu','restore','-D',str(root/'images'),'--shell-job','--cpu-cap=all','--restore-detached','--pidfile',str(root/'restored.pid'),'-o','restore.log','-v4'])
  end=time.monotonic()+600
  while 'CHECKPOINT_CONTROL_FINISHED' not in (root/'resumed.log').read_text():
   assert time.monotonic()<end,'Restored simulator did not finish';time.sleep(.2)
  pid=int(run(['sudo','cat',str(root/'restored.pid')]).stdout);limit=time.monotonic()+15
  while P('/proc/'+str(pid)+'/stat').exists():
   stat=P('/proc/'+str(pid)+'/stat').read_text()
   if stat.split(') ',1)[1].startswith('Z'):break
   assert time.monotonic()<limit,'Restored process still active after sentinel';time.sleep(.1)
  assert (root/'resumed.log').read_bytes()==(root/'baseline.log').read_bytes(),'Interrupted and uninterrupted four-state/delayed-event traces differ'
  r['trace_sha256']=digest(root/'resumed.log');r['trace_lines']=len((root/'resumed.log').read_text().splitlines());r['passed']=True
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
