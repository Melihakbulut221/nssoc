"""Guarded author supersession after complete V17 controls and source peer."""
from pathlib import Path
import datetime,hashlib,json,os,signal,sys,time
R=Path.cwd();B=Path(__file__).resolve().parent;A=B.parent/'pcie-integrity-v16-20261005'
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life

def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert '39 passed, 2 deselected' in (B/'controls01.log').read_text()
peer=json.loads((B/'source-only-peer-rx.json').read_text());assert peer['status'].startswith('PASS_V17_')
assert pin(B/'source-only-peer-rx.json')==json.loads((B/'peer-pin.json').read_text())
for name,value in json.loads((B/'source-freeze.json').read_text())['files'].items():assert pin(R/name)==value
gate=json.loads((B/'lifecycle-peer-pin02.json').read_text());peerpath=Path(gate['path'])
assert pin(peerpath)=={k:gate[k] for k in ['bytes','sha256']}
assert json.loads(peerpath.read_text())['status'].startswith('PASS_V17_')
guards=json.loads((B/'supersession-identity-guards02.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==guards['boot_id']
pre=json.loads((A/'continuation-status02.json').read_text());assert pre['status']=='WAITING_EXISTING_FROZEN_CONTROLS' and pre['stages']==[]
record=dict(status='SUPERSEDING_V16_AFTER_VALIDATED_EQUIVALENT_COMPILE_FIX',utc=datetime.datetime.now(datetime.UTC).isoformat(),method=pin(Path(__file__)),V17_controls=pin(B/'controls01.log'),V17_peer=pin(B/'source-only-peer-rx.json'),prior_continuation=pre,lifecycle_peer=gate,identity_guards=pin(B/'supersession-identity-guards02.json'),boot_id=guards['boot_id'],stops=[],reason='Superseded by validated equivalent compile fix. Not a healthy elapsed-time limit, not a passed V16 suite, and not user shutdown.',PLL_untouched=True)
out=B/'V16-supersession-receipt02.json';assert not out.exists()
def save():life.atomic(out,record)
def same(expected):
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==guards['boot_id'],'Boot changed: refuse every signal'
 actual=life.process_identity(expected['pid'])
 if actual is None or actual['start_ticks']!=expected['start_ticks'] or actual['state']=='Z':return False
 assert actual['process_group']==expected['process_group'],'Process group changed: refuse signal'
 command=Path('/proc')/str(expected['pid'])/'cmdline'
 raw=command.read_bytes()
 assert len(raw)==expected['commandline_bytes'] and hashlib.sha256(raw).hexdigest()==expected['commandline_sha256'],'Command changed: refuse signal'
 return True
def members(group):
 result=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  item=life.process_identity(int(p.name))
  if item is not None and item['process_group']==group and item['state']!='Z':
   raw=(p/'cmdline').read_bytes();item['commandline_bytes']=len(raw);item['commandline_sha256']=hashlib.sha256(raw).hexdigest();item['stat_text']=(p/'stat').read_text();result.append(item)
 return result
def stop(expected,group,kind):
 assert group==expected['process_group'] and same(expected),(kind,'Exact identity no longer matches; inspect instead of signaling')
 row=dict(kind=kind,expected=expected,group=group,members_before=members(group));record['stops'].append(row);save()
 # Exact leader/start guards precede signaling; recorded whole group belongs to
 # this job, and all descendants keep this group during the current compile.
 assert same(expected),'Recheck exact boot/PID/start/group/command immediately before signaling'
 if kind=='idle_continuation':os.kill(expected['pid'],signal.SIGTERM)
 else:os.killpg(expected['process_group'],signal.SIGTERM)
 deadline=time.monotonic()+5
 while time.monotonic()<deadline and any(same(x) for x in row['members_before']):time.sleep(.05)
 remaining=[x for x in row['members_before'] if same(x)]
 if remaining:
  for x in remaining:
   if same(x):os.kill(x['pid'],signal.SIGKILL)
  deadline=time.monotonic()+5
  while time.monotonic()<deadline and any(same(x) for x in remaining):time.sleep(.05)
 row['remaining_exact_identities']=[x for x in row['members_before'] if same(x)];assert not row['remaining_exact_identities']
 row['after']=[life.process_identity(x['pid']) for x in row['members_before']];save()
save()
stop(guards['jobs']['idle_continuation'],48770,'idle_continuation')
post=json.loads((A/'continuation-status02.json').read_text());assert post['stages']==[];record['stopped_continuation']=post;save()
stop(guards['jobs']['incomplete_V16_controls'],42780,'incomplete_V16_controls')
stop(guards['jobs']['incomplete_Icarus14_probe'],45372,'incomplete_Icarus14_probe')
record.update(status='AUTHOR_SUPERSEDED_V16_INCOMPLETE_CAPTURE_RETAINED',finished_utc=datetime.datetime.now(datetime.UTC).isoformat(),controls_log=pin(A/'controls01.log'),controls_status='Incomplete; no full-suite PASS, no native V16 map launched',probe_status='Incomplete compiler comparison; no simulation PASS',V16_source_freeze=pin(A/'source-freeze.json'))
save();print(record['status'])
