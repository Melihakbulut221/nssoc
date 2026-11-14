# SPDX-License-Identifier: Apache-2.0
"""Cloud-only capability experiment; no chip simulation acceptance."""
import pathlib,subprocess,json,hashlib,os,time,sys,tarfile,platform,re
P=pathlib.Path;out=P('out');out.mkdir(exist_ok=True);root=P('/tmp/nssoc-vvp-checkpoint-proof');stage=sys.argv[1]
r={'stage':stage,'passed':False,'chip_acceptance':False,'source_sha':os.environ.get('GITHUB_SHA')}
def digest(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(cmd,**kwargs):return subprocess.run(cmd,check=True,text=True,capture_output=True,timeout=300,**kwargs)
def runtime():
 paths={'/usr/bin/vvp','/usr/bin/iverilog'}
 for line in run(['ldd','/usr/bin/vvp']).stdout.splitlines():
  for token in line.split():
   if token.startswith('/') and P(token).is_file():paths.add(token)
 return {'files':{p:digest(p) for p in sorted(paths)},'kernel':platform.release(),'uid':os.getuid(),'criu':run(['criu','--version']).stdout.strip()}
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
always @(posedge clk) begin
 count=count+1;
 q <= {q[6:0],q[7]};
 delayed <= #7 ~delayed;
 checksum <= {checksum[30:0],checksum[31]^checksum[21]^checksum[1]^checksum[0]};
 if(count%100000==0) begin
  $display("TRACE %0d %b %b %08x %0t",count,q,delayed,checksum,$time); $fflush();
 end
 if(count==50000000) begin $display("CHECKPOINT_CONTROL_FINISHED"); $fflush(); $finish; end
end
endmodule
"""
  (root/'proof.v').write_text(bench)
  run(['iverilog','-g2012','-s','proof','-o',str(root/'sim.vvp'),str(root/'proof.v')])
  with (root/'baseline.log').open('w') as f:
   p=subprocess.run(['vvp',str(root/'sim.vvp')],stdout=f,stderr=subprocess.STDOUT,timeout=300);assert p.returncode==0
  assert 'CHECKPOINT_CONTROL_FINISHED' in (root/'baseline.log').read_text()
  with (root/'resumed.log').open('w') as f,open('/dev/null') as stdin:
   proc=subprocess.Popen(['vvp',str(root/'sim.vvp')],stdin=stdin,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  end=time.monotonic()+60
  while 'TRACE ' not in (root/'resumed.log').read_text():
   assert proc.poll() is None and time.monotonic()<end;time.sleep(.05)
  assert 'CHECKPOINT_CONTROL_FINISHED' not in (root/'resumed.log').read_text()
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
  run(['sudo','tar','-xzf','checkpoint.tgz','-C','/tmp'])
  assert digest(root/'resumed.log')==dump['checkpoint_prefix_sha256']
  run(['sudo','criu','restore','-D',str(root/'images'),'--shell-job','--cpu-cap=all','--restore-detached','--pidfile',str(root/'restored.pid'),'-o','restore.log','-v4'])
  end=time.monotonic()+300
  while 'CHECKPOINT_CONTROL_FINISHED' not in (root/'resumed.log').read_text():
   assert time.monotonic()<end,'Restored simulator did not finish';time.sleep(.2)
  pid=int((root/'restored.pid').read_text());limit=time.monotonic()+15
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
 r['criu_logs']={p.name:p.read_text(errors='replace')[-10000:] for p in (root/'images').glob('*.log')} if (root/'images').exists() else {}
 (out/(stage+'-result.json')).write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k in ['stage','passed','error','native_error']}))
