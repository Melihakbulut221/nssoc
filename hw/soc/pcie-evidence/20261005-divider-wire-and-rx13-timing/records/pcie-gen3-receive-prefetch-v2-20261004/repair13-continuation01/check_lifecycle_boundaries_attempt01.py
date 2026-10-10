# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Three real-process controls on exact extracted production stage/tail ASTs."""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,signal,subprocess,sys,threading,time
C=Path(__file__).resolve().parent;R=C.parents[4]
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
script=C/'run.py';assert pin(script)['sha256']=='86943cdab7f5be4e3731150b87c865d13ca16b532474ad1db6bbf0f74b1a2cc0'
spec=importlib.util.spec_from_file_location('candidate_controller_only',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
main=next(n for n in ast.parse(script.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='main');stage=next(n for n in ast.walk(main) if isinstance(n,ast.FunctionDef) and n.name=='run_stage');tail=main.body[-2];assert isinstance(tail,ast.Try)
life=R/'scripts/characterize_pcie_clock_trim_stream_v2.py';assert pin(life)['sha256']=='39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886'
ns=dict(os=os,Path=Path,threading=threading,signal=signal,subprocess=subprocess,time=time,atomic=module.atomic,require=module.require,FAILURE_GRACE_SECONDS=15.)
selected=[n for n in ast.parse(life.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in {'Cancelled','process_identity','group_members','ProcessOwner'}];assert len(selected)==4;exec(compile(ast.Module(selected,[]),str(life),'exec'),ns)
results=[]
for mode in ['complete_signal','teardown_signal','stage_failure']:
 out=C/'lifecycle-controls'/mode;out.mkdir(parents=True)
 Base=ns['ProcessOwner']
 class BoundaryOwner(Base):
  saves=0
  def save(self):
   super().save()
   if any(e['record']['status']=='REAPED_NO_LIVE_MEMBERS' for e in self.entries):
    self.saves+=1
    if mode=='teardown_signal' and self.saves==2:os.kill(os.getpid(),signal.SIGTERM)
  def complete(self,process):
   code=super().complete(process)
   if mode=='complete_signal':os.kill(os.getpid(),signal.SIGTERM)
   return code
 owner=BoundaryOwner(out/'owner.json');record=dict(stages=[],status='CONTROL_RUNNING');saves=[]
 context=dict(module.__dict__,owner=owner,record=record,manifest=dict(inputs={}),sources_unchanged=lambda:None,save=lambda:saves.append(json.loads(json.dumps(record))),limits=module.limits)
 exec(compile(ast.Module([stage],[]),str(script),'exec'),context)
 try:
  with owner:
   context['run_stage']('actual_control',[sys.executable,'-c','raise SystemExit('+('1' if mode=='stage_failure' else '0')+')'],out/'child.log')
  exec(compile(ast.Module([tail],[]),str(script),'exec'),context)
 except BaseException as error:
  expected='nonzero exit' if mode=='stage_failure' else 'SIGTERM';assert expected in str(error)
 else:raise AssertionError('Actual failure/stop incorrectly accepted')
 members=[]
 for e in owner.entries:members+=ns['group_members'](e['process'].pid)
 assert not any(x['state']!='Z' for x in members)
 if mode=='teardown_signal':assert record['status']=='FAILED_RETAINED_NO_DEPENDENT_BYPASS'
 row=dict(mode=mode,expected_error=expected,record=record,owner_reason=owner.reason,remaining_members=members,terminal_guard_or_error_seen=True);(out/'result.json').write_text(json.dumps(row,indent=2)+'\n');results.append(row)
r=dict(status='PASS_THREE_ACTUAL_RX13_CONTINUATION_BOUNDARY_CONTROLS',source=pin(script),method=pin(__file__),exact_production_stage_ast=True,exact_production_post_context_try_ast=True,results=results,scope='Real small Python child, completion/teardown real SIGTERM and actual nonzero exit. Original route observed nowhere, no EDA/proof/publication rerun. CPU8/productionlimits and outer15s owner retained.')
p=C/'lifecycle-controls.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
