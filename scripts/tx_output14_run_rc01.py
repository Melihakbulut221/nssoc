# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json,hashlib,os,resource,subprocess,time,signal
R=Path.cwd();B=Path(__file__).resolve().parent;O=B/'rc01';O.mkdir();A=B/'anchors03.json';a=json.loads(A.read_text());W=B/'native01/wires.gds';RT=B/'magic-cloud/runtime/lib';T=B/'magic-cloud/tech'
def pin(p):
 with Path(p).open('rb')as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert pin(RT/'magic/tcl/tclmagic.so')['sha256']=='e8f2d96121e704acee41e7a58c23feead887527e3bfc4f51da4d97aa8183970e'
assert all(pin(p)['sha256']==h for p,h in a['inputs'].items())
lines=['puts "NSSOC_LOADED_NATIVE_LIBRARIES [info loaded]"',f'cd {{{O}}}','drc off',f'gds read {{{W}}}','load tx_output_wires','select top cell'];metals={8:'metal1',10:'metal2',30:'metal3',50:'metal4',67:'metal5',126:'metal6',134:'metal7'}
for i,r in enumerate(a['anchors']):
 x,y=[f'{v/1000:.3f}um'for v in r['point_dbu']];n=r['label'];lines += [f'box values {x} {y} {x} {y}',f'label {n} center {metals[r["metal"]]}',f'port {n} make {i+1}',f'port {n} class inout',f'port {n} use signal']
lines+=['save tx_output_wires','extract unique all','extract style ngspice()','extract all','ext2spice lvs','ext2spice merge none','ext2spice global off','ext2spice cthresh 0','ext2spice rthresh 0','ext2spice extresist off','ext2spice -o baseline.spice','puts NSSOC_WIRE_CAP_BASELINE_COMPLETE','ext2sim labels on','ext2sim','extresist threshold 0','extresist tolerance 0.000001','extresist simplify off','extresist all','ext2spice extresist on','ext2spice -o wires.spice','puts NSSOC_WIRE_RC_COMPLETE','quit -noprompt']
script=O/'native.tcl';script.write_text('\n'.join(lines)+'\n');inputs={str(p):pin(p)for p in [A,W,script,Path(__file__).resolve(),RT/'magic/tcl/tclmagic.so',RT/'magic/tcl/magic.tcl',*T.iterdir()]if p.is_file()}
env={k:v for k,v in os.environ.items()if k not in ['PYTHONHOME','PYTHONPATH','PYTHONEXECUTABLE','LD_PRELOAD']};env['CAD_ROOT']=str(RT)
def limits():resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
cmd=['/usr/bin/tclsh8.6',str(RT/'magic/tcl/magic.tcl'),'-dnull','-noconsole','-rcfile',str(T/'ihp-sg13g2.magicrc'),str(script)];start=time.monotonic();reason=None
with(O/'native.log').open('x')as log:
 p=subprocess.Popen(cmd,cwd=O,env=env,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 while p.poll()is None:
  size=sum(q.stat().st_size for q in O.rglob('*')if q.is_file())
  if size>80*1024**2:
   reason='OWNED_SCRATCH_80MIB_LIMIT';os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   break
  time.sleep(.5)
assert all(pin(n)==h for n,h in inputs.items());record=dict(status=reason or'NATIVE_COMPLETE_AWAITING_RC_AUDIT',returncode=p.returncode,seconds=time.monotonic()-start,inputs=inputs,outputs={q.name:pin(q)for q in O.iterdir()if q.is_file()},qualified_pex=False,elapsed_timeout=False)
(O/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(record['status'],record['returncode'])
