"""Guarded author supersession after complete V17 controls and source peer."""
from pathlib import Path
import datetime,hashlib,json,os,signal,sys,time
R=Path.cwd();B=Path(__file__).resolve().parent;A=B.parent/'pcie-integrity-v16-20261005'
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life

def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert '39 passed, 2 deselected' in (B/'controls01.log').read_text()
assert pin(B/'source-only-peer-rx.json')==json.loads((B/'peer-pin.json').read_text())
gate=json.loads((B/'lifecycle-peer-pin03.json').read_text());peerpath=Path(gate['path'])
assert pin(peerpath)=={k:gate[k] for k in ['bytes','sha256']}
assert json.loads(peerpath.read_text())['status'].startswith('PASS_V17_')
guards=json.loads((B/'supersession-identity-guards02.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==guards['boot_id']
prior=json.loads((B/'V16-supersession-receipt02.json').read_text())
failed=json.loads((B/'continuation-status02.json').read_text())
assert failed['status']=='FAILED_RETAINED' and len(failed['stages'])==1 and failed['stages'][0]['name']=='supersede_v16'
assert [row['kind'] for row in prior['stops']]==['idle_continuation','incomplete_V16_controls']
assert json.loads((A/'continuation-status02.json').read_text())['stages']==[]
record=dict(status='RECOVERING_OBSERVER_TEARDOWN_RACE_RETAINING_V2_FAILURE',utc=datetime.datetime.now(datetime.UTC).isoformat(),method=pin(Path(__file__)),lifecycle_peer=gate,identity_guards=pin(B/'supersession-identity-guards02.json'),prior_supersession=pin(B/'V16-supersession-receipt02.json'),prior_controller_failure=pin(B/'continuation-status02.json'),stops=[],reason='Finish authorized supersession after exact oldcontrol/watcherdeath. V2 polling raced exiting commandline; strict signal guards unchanged, observational liveness separated. V16 remains incomplete, not passed.',PLL_untouched=True)
out=B/'V16-supersession-receipt03.json';assert not out.exists()
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
def alive(expected):
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==guards['boot_id']
 actual=life.process_identity(expected['pid'])
 return actual is not None and actual['start_ticks']==expected['start_ticks'] and actual['state']!='Z'

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
 while time.monotonic()<deadline and any(alive(x) for x in row['members_before']):time.sleep(.05)
 remaining=[x for x in row['members_before'] if alive(x)]
 if remaining:
  for x in remaining:
   if same(x):os.kill(x['pid'],signal.SIGKILL)
  deadline=time.monotonic()+5
  while time.monotonic()<deadline and any(alive(x) for x in remaining):time.sleep(.05)
 row['remaining_exact_identities']=[x for x in row['members_before'] if alive(x)];assert not row['remaining_exact_identities']
 row['after']=[life.process_identity(x['pid']) for x in row['members_before']];save()
# Already stopped identities are observed only and must stay absent/zombie;
# no signal is sent to an absent old PID or a replacement PID.
closed=[]
for row in prior['stops']:
 for expected in row['members_before']:
  assert not alive(expected),'An old supposedly stopped identity is still live; inspect, do not infer'
  closed.append(dict(expected=expected,after=life.process_identity(expected['pid'])))
record['prior_stopped_identities_rechecked']=closed;save()
stop(guards['jobs']['incomplete_Icarus14_probe'],45372,'incomplete_Icarus14_probe')
record.update(status='AUTHOR_SUPERSEDED_V16_INCOMPLETE_CAPTURE_RETAINED',finished_utc=datetime.datetime.now(datetime.UTC).isoformat(),controls_log=pin(A/'controls01.log'),controls_status='Incomplete; no full-suite PASS, no native V16 map launched',probe_status='Incomplete compiler comparison; no simulation PASS',V16_source_freeze=pin(A/'source-freeze.json'))
save();print(record['status'])
