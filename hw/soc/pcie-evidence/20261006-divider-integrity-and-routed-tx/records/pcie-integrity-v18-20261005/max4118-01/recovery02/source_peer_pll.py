"""Source-only exact-birth orphan recovery and saved race-control peer."""
from pathlib import Path
import ast,datetime,hashlib,json
B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert pin(B/'run.py')==dict(bytes=10705,sha256='574287f1b8aba32dd907c0176daf381254d59a8cdc3daa51da044aa6ffb91142')
assert pin(B/'policy.json')==dict(bytes=42087,sha256='c937d704a7a64f098cafd363c22858419e466a704dafa6b39decb081f157d519')
p=json.loads((B/'policy.json').read_text())
for name,value in p['pins'].items():assert pin(name)==value,name
s=(B/'run.py').read_text();prior=(B/'source-candidate01/run.py').read_text()
a="""                try:
                    fd = os.pidfd_open(row['pid'])
                except ProcessLookupError:
                    # Normal child exit after the process-table snapshot.
                    continue
"""
assert s.count(a)==1 and s.replace(a,"                fd = os.pidfd_open(row['pid'])\n")==prior
race=json.loads((B/'completion-race-control.json').read_text());assert race['source']==pin(B/'run.py') and race['method']==pin(B/'test_completion_race.py')
assert race['status']=='PASS_ACTUAL_EXIT_BEFORE_PIDFD_OPEN_AND_REMAINING_LIVE_PEER'
assert race['exact_observe_AST'] and race['actual_ESRCH_caught'] and race['remaining_live_peer_pidfd_opened_and_signalled'] and race['no_remaining_births']
for name in ['dead_identity','live_identity']:
 row=race[name];q=Path('/proc')/str(row['pid'])/'stat'
 if q.exists():assert q.read_text().rsplit(') ',1)[1].split()[19]!=row['start_ticks']
observed=[]
for row in p['adopted_births']:
 q=Path('/proc')/str(row['pid'])/'stat'
 if q.exists():
  f=q.read_text().rsplit(') ',1)[1].split();observed.append(dict(pid=row['pid'],state=f[0],same_birth=f[19]==row['start_ticks']))
assert 'returncode_provenance' in s and "closed_functional('direct', None)" in s
assert 'signal.pidfd_send_signal' in s and "stage = original_policy['stages'][1]" in s
r=dict(status='PASS_SOURCE_ONLY_MAX4118_EXACT_BIRTH_RECOVERY',utc=datetime.datetime.now(datetime.UTC).isoformat(),policy=pin(B/'policy.json'),method=pin(Path(__file__)),source=pin(B/'run.py'),saved_race_control=pin(B/'completion-race-control.json'),saved_race_method=pin(B/'test_completion_race.py'),source_pins_rehashed=len(p['pins']),readonly_external_observation=observed,findings=[],reviewed=['Sameboot and lostoriginalcontroller guards; seeded exactPID/start/command/CPU2 checked, no duplicate directtest.','Passive existing-birth observation and descendants; pidfd opened thenbirth rechecked. Signals onlyonerror/stop throughboundpidfds, not reusablePID or unownedgroup.','Priorcandidate unhandledESRCH race preserved; onlyProcessLookupError aroundpidfdopen nowtreated asnormalcompletion. Savedactualexact-observeAST racecontrol rehashed and inspected; deadchildESRCH andremaininglivepeerpidfd bothcovered. WrongambientPython attempt retained; useverified3.12cocotbvenv interpreter.','Original externalpytest wait status remainsNone explicitlyunavailable, neverfabricated. Directfunctional classification requires13actualunskippedcocotbPASS, helper4118/R2048/2GiB/inputs/outputs andpytestXML agreement afterallknownbirths close.','Only not-yet-run miter launchesfromoriginalfrozenpolicy afterdirectterminalreview; freshoutput/log guards, sameCPU2/2GiB/subreaper/floors. Ownedmiter wait status remainsactualreturncode.','Cancellation checkedwhilewaiting, afterownedcomplete, before/afterownercontext; externalpidfd cleanup andowneddescendant cleanup separate. Nohealthyelapsedwatchdog. Finalresults requireseparate recovery-awareseal; originalowner/status bytes untouched.'],scope='Source andsavedactualcontrol review only; no direct/miter simulation launched/repeated/signaled. Existingexternalprocess observations readonly. Fiveexistingseededbirths and ordinaryfixedhelper tree bound; not a generic OS processadoption primitive.')
with (B/'source-peer.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(pin(B/'source-peer.json')))
