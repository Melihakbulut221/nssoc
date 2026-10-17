from pathlib import Path
import hashlib,json,ast
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 p=Path(p);b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def bridges(path):
 rows=json.loads(path.read_text())
 for row in rows:
  assert pin(row['parent'])==row['parent_pin'] and pin(row['path'])==row['pin']
  original=Path(row['parent']).read_text();s=original;states=[]
  for step in row['replacements']:
   count=s.count(step['before']);assert count>0
   if 'count'in step:assert count==step['count']
   states.append(s);s=s.replace(step['before'],step['after'])
  assert s==Path(row['path']).read_text()
  for step,prior in reversed(list(zip(row['replacements'],states))):
   pieces=prior.split(step['before']);assert step['after'].join(pieces)==s;s=step['before'].join(pieces)
  assert s==original
 return len(rows)
p=B/'continuation-policy02.json';d=json.loads(p.read_text())
for name,v in d['method_pins'].items():assert pin(name)==v
for name,v in d['source_pins'].items():assert pin(R/name)==v
n=bridges(B/'native-source-bridges01.json')+bridges(B/'native-source-supplement02.json')
for name in ['run_balanced_map02.py','balanced_import02.py','balanced_preplacement02.py']:
 s=(B/name).read_text();assert 'killpg('not in s and s.count('OwnedNative(')==1 and s.count('free_floor(')==1
 assert s.index('OwnedNative(')<s.index('finally:signal.pthread_sigmask(signal.SIG_SETMASK')
 assert s.index('free_floor(')>s.index('.wait()')
 assert 'terminal_shared_free' in s and "with_name('native_lifecycle02.py')"in s
for name in ['balanced_import02.py','balanced_preplacement02.py','run_balanced_map02.py','continue_native02.py','native_lifecycle02.py','detach_native02.py','lifecycle_controls02.py']:
 ast.parse((B/name).read_text())
g=(B/'native_lifecycle02.py').read_text();assert g.index('if p.returncode is not None:')<g.index('current=identity(')<g.index('os.killpg(')<g.index('code=p.wait()')
controls=json.loads((B/'lifecycle-controls02.json').read_text());assert controls['status']=='PASS_SIX_ACTUAL_NATIVE_LIFECYCLE_CONTROLS'and len(controls['controls'])==6
assert controls['method']==pin(B/'native_lifecycle02.py')and controls['harness']==pin(B/'lifecycle_controls02.py')
cases={r['case']:r['receipt']for r in controls['controls']};assert len(cases)==6
for name in ['clean_completion_already_reaped_no_signal','actual_completed_child_terminal_floor_rejected_no_signal']:assert cases[name]['status']=='ALREADY_REAPED_NO_SIGNAL'and cases[name]['returncode']==0
for name in ['actual_live_wrong_birth_refused_child_alive','actual_live_wrong_group_refused_child_alive']:assert cases[name]['status']=='REFUSED_BIRTH_OR_GROUP_MISMATCH_NO_SIGNAL'and cases[name]['current']!=cases[name]['expected']
for name in ['actual_live_exact_birth_failure_cleanup','actual_sigterm_wrapper_native_group_cleanup']:assert cases[name]['status']=='EXACT_OWNED_GROUP_KILLED_AND_REAPED'and cases[name]['returncode']==-9 and cases[name]['signal_sent']
for name in ['continuation-policy01.json','continuation-policy02.json','detach_native02.py','native-source-only-peer01-findings-vco.json','saved-controls-peer-vco.json','lifecycle-controls02.log','lifecycle-signal-worker02.py','lifecycle-signal-birth02.json','lifecycle-signal-receipt02.json']:assert(B/name).is_file()
# The detached supervisor remains the reviewed launch-once/filestdio/session design.
a=(B/'detach_native01.py').read_text();b=(B/'detach_native02.py').read_text();a=a.replace('01','02').replace(str({'bytes':6271,'sha256':'0481d2e69e3ff0cdd1b0fddcb4ba1771512cdde3e87fb1ec425d7e50d68fb1c6'}),str(pin(p)))
assert a==b
r=dict(status='PASS_SOURCE_ONLY_V22_MERGED_NATIVE_CONTINUATION',policy=pin(p),findings=[],method=pin(__file__),detacher=pin(B/'detach_native02.py'),independent_saved_controls=pin(B/'saved-controls-peer-vco.json'),historical_findings=pin(B/'native-source-only-peer01-findings-vco.json'),full_byte_bridges=n,method_pins=len(d['method_pins']),product_pins=len(d['source_pins']),lifecycle_controls=pin(B/'lifecycle-controls02.json'),review=['Exact original eight V21→V22 complete bodies and four additive lifecycle inverses reconstructed both ways.','Three launchers capture native birth/group with SIGINT/SIGTERM blocked; terminal shared floor checks follow wait; cleanup refuses already-reaped or mismatched birth/group and reaps an exact unreaped owned child.','All six saved actual process controls independently read; no new control run. Synchronous owned group contract retained, no arbitrary orphan adoption.','Actual Q/D descriptor and availability boundary uses corrected V21 method03, complete native pin proof and six graph controls unchanged. Original 4ns PDK/corners/preplacement constraints untouched.','Merged 38 executions/35 passed/3 historical failed controls, full corrected17 miter and8 fault/cache/reuse witnesses required. Publicdirect first16 reuse plus targeted17 is explicit.','Detached launcher matches previous whole body except revision and policy pin, with exclusive once marker/freshroots/file stdio/newsession.'],scope='Source and saved-control review only. No map, STA, tested producer, compilation, download or native execution; actual mapped timing/route/fullPHY acceptance remains separate.')
out=B/'native-source-only-peer02.json';assert not out.exists();out.write_text(json.dumps(r,indent=2)+'\n');print(pin(out))
