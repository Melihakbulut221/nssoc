"""Retain real failed dispatch; bind and reuse completed map/boundary/import."""
from pathlib import Path
import json,hashlib
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
status=json.loads((B/'continuation-status02.json').read_text());assert status['status']=='FAILED_RETAINED'and[(r['name'],r['returncode'])for r in status['stages']]==[('map',0),('registered_boundary',0),('import',0),('import_graph_proof',2)]
log=B/'import_graph_proof.controller.log';assert 'prove_balanced_import02.py' in log.read_text()and '[Errno 2]'in log.read_text()
allpins={str(B/'continuation-status02.json'):pin(B/'continuation-status02.json'),str(log):pin(log)}
for kind,expected in [('map','COMPLETE_NATIVE_MAP_FUNCTIONAL_REPLAY_REQUIRED'),('import','PASS_GRAPH_METADATA_AND_LITERAL_TIE_IMPORT')]:
 d=Path('/dev/shm')/f'nssoc-integrity-v22-balanced-{kind}-01';r=json.loads((d/'result.json').read_text());assert r['status']==expected and r['returncode']==0
 allpins[str(d/'result.json')]=pin(d/'result.json')
 for p,v in r['inputs'].items():assert pin(p)==v;allpins[p]=v
 for p,v in r['outputs'].items():assert pin(d/p)==v;allpins[str(d/p)]=v
for name in ['native-registered-boundary.json','signed-wire-census.json','continuation-owner02.json','detached-native02-receipt.json','native-source-only-peer02.json']:
 allpins[str(B/name)]=pin(B/name)
births=[status['controller']]+[r['identity']for r in status['stages']]
for birth in births:
 p=Path(f"/proc/{birth['pid']}/stat")
 if p.exists():assert p.read_text().rsplit(') ',1)[1].split()[19]!=birth['start_ticks']
q=dict(status='SAVED_COMPLETE_V22_MAP_BOUNDARY_IMPORT_DISPATCH_TYPO_RETAINED',files=allpins,closed_births=births,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),old_failure=pin(B/'continuation-status02.json'),scope='All three completed stages retained exactly. Nonexistent proof-helper path failed before graph execution; fix dispatch only and continue remaining proof/STA. No completed tool rerun.')
(B/'native-recovery-basis03.json').write_text(json.dumps(q,indent=2)+'\n')
guard='''"""Require completed unchanged native outputs; no mapping/import executed."""
from pathlib import Path
import hashlib,json
B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
p=B/'native-recovery-basis03.json'
assert pin(p)==BASIS_PIN
q=json.loads(p.read_text());assert q['status']=='SAVED_COMPLETE_V22_MAP_BOUNDARY_IMPORT_DISPATCH_TYPO_RETAINED'
for name,value in q['files'].items():assert pin(name)==value,name
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==q['boot_id']
for birth in q['closed_births']:
 s=Path(f"/proc/{birth['pid']}/stat")
 if s.exists():assert s.read_text().rsplit(') ',1)[1].split()[19]!=birth['start_ticks']
b=json.loads((B/'native-registered-boundary.json').read_text());assert b['status']=='PASS_EMITTED_REGISTERED_RETIRE_PAYLOAD_BOUNDARY_ONLY'and b['no_original_ring_content_q_in_output_d']and len(b['availability_consumer_flop_d'])==8
assert not Path('/dev/shm/nssoc-integrity-v22-balanced-sta-01').exists()
print('PASS_SAVED_V22_MAP_BOUNDARY_IMPORT_EXACT_REUSE')
'''.replace('BASIS_PIN',repr(pin(B/'native-recovery-basis03.json')))
(B/'verify_saved_native03.py').write_text(guard)
s=(B/'continue_native02.py').read_text();start=s.index("  stage('map',");end=s.index("  stage('import_graph_proof'",start);oldblock=s[start:end]
s=s[:start]+"  stage('saved_map_boundary_import',[sys.executable,str(B/'verify_saved_native03.py')])\n"+s[end:]
edits=[('continuation-status02.json','continuation-status03.json'),('continuation-policy02.json','continuation-policy03.json'),('continuation-owner02.json','continuation-owner03.json'),('native-source-only-peer02.json','native-source-only-peer03.json'),('prove_balanced_import02.py','prove_balanced_import.py')]
for a,b in edits:assert a in s;s=s.replace(a,b)
(B/'continue_native03.py').write_text(s)
ledger=dict(parent=dict(path=str(B/'continue_native02.py'),**pin(B/'continue_native02.py')),removed_completed_stages=oldblock,replacement="  stage('saved_map_boundary_import',[sys.executable,str(B/'verify_saved_native03.py')])\n",replacements=edits,after=pin(B/'continue_native03.py'),scope='Same owning stage lifecycle; only actual completed stages replaced by source/output gate, correct missing proof filename, fresh receipts.')
(B/'native-source-recovery-bridge03.json').write_text(json.dumps(ledger,indent=2)+'\n')
policy=json.loads((B/'continuation-policy02.json').read_text());policy['method_pins'].pop(str(B/'continue_native02.py'))
for name in ['continue_native03.py','verify_saved_native03.py','native-recovery-basis03.json','native-source-recovery-bridge03.json']:policy['method_pins'][str(B/name)]=pin(B/name)
policy['status']='FROZEN_V22_SAVED_MAP_IMPORT_RECOVERY03_PEER_REQUIRED';policy['completed_stages_reused']=dict(path=str(B/'native-recovery-basis03.json'),**pin(B/'native-recovery-basis03.json'))
(B/'continuation-policy03.json').write_text(json.dumps(policy,indent=2)+'\n')
s=(B/'detach_native02.py').read_text()
for a,b in [('continuation-policy02.json','continuation-policy03.json'),('native-source-only-peer02.json','native-source-only-peer03.json'),('continuation-status02.json','continuation-status03.json'),('detached-native02','detached-native03'),('continue_native02.py','continue_native03.py')]:s=s.replace(a,b)
s=s.replace(repr(pin(B/'continuation-policy02.json')),repr(pin(B/'continuation-policy03.json')))
s=s.replace("assert not Path('/dev/shm/nssoc-integrity-v22-balanced-map-01').exists()","assert Path('/dev/shm/nssoc-integrity-v22-balanced-map-01').exists()")
s=s.replace("assert not Path('/dev/shm/nssoc-integrity-v22-balanced-import-01').exists()","assert Path('/dev/shm/nssoc-integrity-v22-balanced-import-01').exists()")
(B/'detach_native03.py').write_text(s)
print(pin(B/'continuation-policy03.json'),pin(B/'detach_native03.py'))
