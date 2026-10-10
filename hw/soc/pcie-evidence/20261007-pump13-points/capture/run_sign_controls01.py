# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Two tiny ideal-source OP sign controls; source gate required before native."""
from pathlib import Path
import hashlib,json,os,re,resource,shutil,subprocess,sys
B=Path(__file__).resolve().parent;R=Path.cwd();sys.path.insert(0,str(B))
import characterize_pump13_02 as m
N=m.NATIVE_ROOT/'sign-control01';CAP=32*1024**2

def pin(p):return m.pin(p)
def guard():
 m.guard(N)
 assert m.sampled_bytes(N)<=CAP,'Sign-control32MiBcap'
def limit():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
 resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024**2,)*2)
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{10})
def verify_sign(data,expected):
 assert set(data)=={'v(vctrl)','i(vctrl)'},'Exact sign-control observations'
 assert all(len(v)==1 for v in data.values()),'One actual operating point'
 assert abs(float(data['v(vctrl)'][0])-.6)<=1e-12,'Actual clamp polarity/level'
 assert abs(float(data['i(vctrl)'][0])-expected)<=1e-15,'Actual independent source current sign'

def main():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 assert os.sched_getaffinity(0)=={10}
 freeze=B/'source-freeze01.json';f=json.loads(freeze.read_text());peer=json.loads((B/'source-only-peer-root01.json').read_text())
 assert peer['status']=='PASS_SOURCE_ONLY_PUMP13_EXECUTABLE_AND_CONTROLS' and peer['freeze']==pin(freeze) and not peer['findings']
 for p,v in f['pins'].items():assert pin(p)==v,p
 assert not N.exists() and shutil.disk_usage('/dev/shm').free>=1024**3
 assert shutil.disk_usage(B).free>=m.AGGREGATE_LIMIT+m.SSD_FLOOR
 assert m.n.common.sha(m.n.NG)==m.n.common.NG47_SHA
 m.NATIVE_ROOT.mkdir(exist_ok=True);N.mkdir();guard()
 result=dict(status='RUNNING_TWO_IDEAL_CLAMP_CURRENT_SIGN_CONTROLS',inputs=f['pins'],source_freeze=pin(freeze),source_peer=pin(B/'source-only-peer-root01.json'),outcomes=[],physical13_executed=False)
 m.n.common.atomic(N/'result.json',result)
 try:
  for label,positive in [('inject',True),('withdraw',False)]:
   out=N/label;out.mkdir();from_to='0 vctrl' if positive else 'vctrl 0'
   deck=f'Independent current-source sign control\nVCTRL vctrl 0 0.6\nITEST {from_to} 1u\n.control\nset filetype=binary\nsave v(vctrl) i(vctrl)\nop\nwrite sign.raw all\nquit\n.endc\n.end\n'
   (out/'bench.cir').write_text(deck);(out/'spinit').write_text('set num_threads=1\n')
   inputs={str(p):pin(p)for p in out.iterdir()};inputs[str(m.n.NG)]=pin(m.n.NG)
   env={k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE','PYTHONOPTIMIZE','LD_PRELOAD','GH_TOKEN','GITHUB_TOKEN')}
   env.update(SPICE_SCRIPTS=str(out),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',RAYON_NUM_THREADS='1')
   with m.life.ProcessOwner(out/'owner.json')as owner:
    with(out/'run.log').open('x')as log:
     child=owner.launch('native',[str(m.n.NG),'-n','-b','bench.cir'],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=limit)
     assert os.sched_getaffinity(child.pid)=={10}
     while child.poll()is None:owner.check();guard();owner.cancelled.wait(.05)
     assert owner.complete(child)==0;owner.check();guard()
   owner.check();guard()
   log=(out/'run.log').read_text()
   assert 'ngspice-47 done' in log and not re.search(r'warning|error|failed|singular|gmin stepping|source stepping',log,re.I)
   data=m.n.read_raw(out/'sign.raw',['v(vctrl)','i(vctrl)'],False);expected=1e-6 if positive else -1e-6
   verify_sign(data,expected)
   for mode in ['reversed_sign','missing_observation']:
    bad={k:v.copy()for k,v in data.items()}
    if mode=='reversed_sign':bad['i(vctrl)']*=-1
    else:bad.pop('i(vctrl)')
    try:verify_sign(bad,expected)
    except AssertionError as error:diagnostic=str(error)
    else:raise AssertionError('Sign mutation accepted')
    result['outcomes'].append(dict(case=label+'_'+mode,passed=True,diagnostic=diagnostic,mutation_of_actual_saved_native=True))
   assert all(pin(p)==v for p,v in inputs.items())
   result['outcomes'].append(dict(case=label+'_actual_native_OP_sign',passed=True,expected_a=expected,observed_a=float(data['i(vctrl)'][0]),inputs=inputs,outputs={str(p.relative_to(out)):pin(p)for p in out.iterdir()if p.is_file()}))
  for p,v in f['pins'].items():assert pin(p)==v,p
  assert len(result['outcomes'])==6 and all(x['passed']for x in result['outcomes'])
  result.update(status='PASS_ACTUAL_IDEAL_CURRENT_SOURCE_CLAMP_SIGN_CONTROLS',cases=6,physical13_executed=False,loaded570_force_computed=False)
 except BaseException as error:result.update(status='FAILED_CURRENT_SIGN_CONTROLS_RETAINED',error=repr(error));raise
 finally:
  result['outputs']={str(p.relative_to(N)):pin(p)for p in N.rglob('*')if p.is_file()and p.name!='result.json'}
  m.n.common.atomic(N/'result.json',result)
 guard();print(json.dumps(dict(status=result['status'],result=pin(N/'result.json'))))

if __name__=='__main__':main()
