"""Add terminal resource and exact owned birth checks; preserve candidate01."""
from pathlib import Path
import hashlib,json
B=Path(__file__).resolve().parent;R=Path.cwd();ledger=[]
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def derive(old,new,edits):
 p=B/old;s=p.read_text();rows=[]
 for a,b in edits:
  assert s.count(a)==1,(old,a,s.count(a));s=s.replace(a,b);rows.append(dict(before=a,after=b))
 q=B/new;assert not q.exists();q.write_text(s);ledger.append(dict(parent=str(p),parent_pin=pin(p),path=str(q),pin=pin(q),replacements=rows))
for name in ['run_balanced_map','balanced_import']:
 s=(B/(name+'.py')).read_text();pop=next(x for x in s.splitlines()if x.startswith('   try:p=subprocess.Popen'))
 edits=[('from pathlib import Path','from pathlib import Path\nfrom native_lifecycle02 import OwnedNative,free_floor'),
 ('  p=None','  p=None;native_owner=None'),
 (pop,'   try:\n    '+pop.strip()[4:]+'\n    native_owner=OwnedNative(p);r[\'native_birth\']=native_owner.birth'),
 ("   r['returncode']=p.wait()","   r['returncode']=p.wait()\n   r['terminal_shared_free']=shutil.disk_usage('/dev/shm').free;free_floor(r['terminal_shared_free'])"),
 ("   if p is not None:\n    try:os.killpg(p.pid,signal.SIGKILL)\n    except ProcessLookupError:pass\n    p.wait()","   if native_owner is not None:\n    try:native_owner.kill_and_reap()\n    finally:r['cleanup']=native_owner.cleanup"),
 ('Path(__file__),','Path(__file__),Path(__file__).with_name(\'native_lifecycle02.py\'),')]
 derive(name+'.py',name+'02.py',edits)
s=(B/'balanced_preplacement.py').read_text();pop=next(x for x in s.splitlines()if x.startswith('                try:process=subprocess.Popen'))
derive('balanced_preplacement.py','balanced_preplacement02.py',[
 ('from pathlib import Path','from pathlib import Path\nfrom native_lifecycle02 import OwnedNative,free_floor'),
 ('            process=None','            process=None;native_owner=None'),
 (pop,'                try:\n                    '+pop.strip()[4:]+'\n                    native_owner=OwnedNative(process);row[\'native_birth\']=native_owner.birth'),
 ("                row['returncode']=process.wait()","                row['returncode']=process.wait()\n                free=shutil.disk_usage('/dev/shm').free;row['minimum_shared_free']=min(free,row['minimum_shared_free']);row['terminal_shared_free']=free;free_floor(free)"),
 ('                if process is not None:\n                    try:os.killpg(process.pid,signal.SIGKILL)\n                    except ProcessLookupError:pass\n                    process.wait()',"                if native_owner is not None:\n                    try:native_owner.kill_and_reap()\n                    finally:row['cleanup']=native_owner.cleanup"),
 ('files=[Path(__file__),','files=[Path(__file__),Path(__file__).with_name(\'native_lifecycle02.py\'),')])
# Explicit named continuation changes only; functional/physical stage predicates unchanged.
s=(B/'continue_native01.py').read_text();pairs=[('continuation-status01.json','continuation-status02.json'),('continuation-policy01.json','continuation-policy02.json'),('continuation-owner01.json','continuation-owner02.json'),('native-source-only-peer01.json','native-source-only-peer02.json'),('run_balanced_map.py','run_balanced_map02.py'),('balanced_import.py','balanced_import02.py'),('balanced_preplacement.py','balanced_preplacement02.py')]
rows=[]
for a,b in pairs:
 assert s.count(a)>0;s=s.replace(a,b);rows.append(dict(before=a,after=b))
p=B/'continue_native02.py';p.write_text(s);ledger.append(dict(parent=str(B/'continue_native01.py'),parent_pin=pin(B/'continue_native01.py'),path=str(p),pin=pin(p),replacements=rows))
(B/'native-source-supplement02.json').write_text(json.dumps(ledger,indent=2)+'\n')
policy=json.loads((B/'continuation-policy01.json').read_text());updated={str(B/(Path(p).stem+'02.py'))if Path(p).name in['run_balanced_map.py','balanced_import.py','balanced_preplacement.py','continue_native01.py']else p:v for p,v in policy['method_pins'].items()}
# continue_native01's version suffix is not a stem append.
updated.pop(str(B/'continue_native0102.py'),None);updated[str(B/'continue_native02.py')]={}
extras=['native_lifecycle02.py','lifecycle_controls02.py','lifecycle-controls02.json','lifecycle-controls02.log','lifecycle-signal-worker02.py','lifecycle-signal-birth02.json','lifecycle-signal-receipt02.json','native-source-supplement02.json','saved-controls-peer-vco.json','native-source-only-peer01-findings-vco.json']
for n in extras:updated[str(B/n)]={}
policy['method_pins']={p:pin(Path(p))for p in updated};policy['status']='FROZEN_V22_NATIVE_POLICY02_EXACT_BIRTH_TERMINAL_FLOOR_PEER_REQUIRED';policy['lifecycle_supplement']='Candidate01 retained; native synchronous group cleanup only before leader reap under exact boot/start/group, terminal free floor checked afterwait; six actual short controls, no native tool rerun.'
p=B/'continuation-policy02.json';p.write_text(json.dumps(policy,indent=2)+'\n')
s=(B/'detach_native01.py').read_text()
for a,b in [('continuation-policy01.json','continuation-policy02.json'),('native-source-only-peer01.json','native-source-only-peer02.json'),('continuation-status01.json','continuation-status02.json'),('detached-native01','detached-native02'),('continue_native01.py','continue_native02.py')]:s=s.replace(a,b)
s=s.replace(repr(pin(B/'continuation-policy01.json')),repr(pin(p)));(B/'detach_native02.py').write_text(s)
print(pin(p),pin(B/'detach_native02.py'))
