"""Independent frozen source bridge and saved owned-child evidence review."""
from pathlib import Path
import ast,gzip,hashlib,json,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-publisher-v4-controls02')
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def load(p):return json.loads(Path(p).read_text())
f=B/'source-freeze01.json';assert pin(f)==dict(bytes=64049,sha256='7bc519c0fa66900a7b366fe71bb1a3d5c28b6ba93bdb303ed16dd30b20177c64')
j=load(f);assert j['tests']==15 and len(j['inputs'])==276 and len(j['sources'])==2
for k in('inputs','sources'):
 for n,h in j[k].items():assert pin(n)==h,n
old=R/'scripts/publish_pcie_native_capture_v3.py';new=R/'scripts/publish_pcie_native_capture_v4.py'
assert pin(old)['sha256']=='b2ea742c31c20c19bf02b30b3b1954342d5aa73772732dc69c8f170f46e1fa0f'
a=ast.parse(new.read_text());assigns={x.targets[0].id:x.value for x in a.body if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name)}
def literal(n):
 if isinstance(n,ast.Name):return literal(assigns[n.id])
 if isinstance(n,(ast.List,ast.Tuple)):return [literal(x)for x in n.elts]
 return ast.literal_eval(n)
replacements=literal(assigns['replacements']);assert len(replacements)==3
old_lines=old.read_text().splitlines(True);main=next(x for x in ast.parse(old.read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='main')
whole=''.join(old_lines[main.lineno-1:main.end_lineno]);reconstructed=whole
for before,after in replacements:assert reconstructed.count(before)==1;reconstructed=reconstructed.replace(before,after)
reverse=reconstructed
for before,after in reversed(replacements):assert reverse.count(after)==1;reverse=reverse.replace(after,before)
assert reverse==whole
client=next(x for x in a.body if isinstance(x,ast.ClassDef) and x.name=='Client')
assert ast.unparse(client.bases[0])=='previous.Client'
assert [x.name for x in client.body if isinstance(x,ast.FunctionDef)]==['__init__','resolve_asset']
# Every original command/deadline/stderr cap/prefix/authenticated+anonymous
# transport and signal cleanup method is inherited unmodified.
cs=list(ET.parse(B/'controls02.xml').getroot().iter('testcase'));assert len(cs)==15 and all(not len(c)for c in cs)
states={p.parent.name:load(p)for p in D.glob('*/upload-state.json')if not p.parent.is_symlink()}
expected={'test_current_capture_change_re0':0,'test_real_cli_retries_upload_a0':2,'test_real_integrity_or_permane0':1,'test_real_integrity_or_permane1':1,'test_real_integrity_or_permane2':1,'test_real_signal_stops_owned_u0':1,'test_real_signal_stops_owned_u1':1,'test_real_uncertain_absent_upl0':2,'test_real_uncertain_absent_upl1':2,'test_real_upload_present_or_vi0':1,'test_real_upload_present_or_vi1':1,'test_real_upload_present_or_vi2':1,'test_real_upload_retry_budget_0':3,'test_successful_but_missing_as0':1}
assert {n:s['uploads']for n,s in states.items()}==expected
for s in states.values():assert all('--clobber'not in c for c in s['calls'])
assert states['test_real_upload_present_or_vi2']['metadata']==4
assert states['test_successful_but_missing_as0']['metadata']==6
assert states['test_real_upload_retry_budget_0']['metadata']==6
journals=[];child_count=0
for p in D.glob('*/*/attempts.json'):
 if p.parent.parent.is_symlink():continue
 rows=load(p);assert rows
 for row in rows:
  assert row['status'] in('PASS','TRANSPORT_FAILURE','FATAL_NO_RETRY')
  assert row['deadline_seconds']<=120
  assert '--clobber'not in row['command']
  for key in('stdout','stderr'):
   item=row[key];assert pin(item['path'])=={k:item[k]for k in('bytes','sha256')}
   raw=gzip.decompress(Path(item['path']).read_bytes())
   assert dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())==item['uncompressed']
  owner=load(row['owned_processes'])
  for c in owner['processes']:
   assert c['status']=='REAPED_NO_LIVE_MEMBERS' and not c.get('members_at_leader_exit'),c
   child_count+=1
 journals.append(dict(path=str(p),**pin(p),attempts=len(rows)))
timeout=load(D/'test_real_uncertain_absent_upl0/evidence/attempts.json')
up=[x for x in timeout if x['kind']=='upload'];assert len(up)==2 and up[0]['deadline_triggered'] and up[0]['returncode']==-15 and up[1]['returncode']==0
assert up[0]['status']=='TRANSPORT_FAILURE' and up[1]['status']=='PASS'
for n in('test_real_signal_stops_owned_u0','test_real_signal_stops_owned_u1'):
 r=load(D/n/'receipt.json');assert r['status']=='FAIL' and r['explicit_stop'] and states[n]['uploads']==1
r=load(D/'test_real_cli_retries_upload_a0/receipt.json')
assert r['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and r['publisher_revision']==4 and not r['physical_acceptance']
assert len(r['upload_reconciliations'])==2 and len(r['assets'])==1
assert r['assets'][0]['authenticated_roundtrip'] and r['assets'][0]['anonymous_roundtrip']
assert r['publisher_v3']==pin(old) and r['source']==pin(new)
out=dict(status='PASS_PUBLISHER_V4_SOURCE_AND_15_ACTUAL_CONTROLS',freeze=pin(f),findings=[],reviewer='PLL/integrity independent source and saved-control reader',method=pin(__file__),sources=j['sources'],input_count=276,actual_pytest_cases=[c.attrib for c in cs],actual_owned_transport_children=child_count,transport_journals=journals,source_bridge=dict(replacements=3,old_main_sha256=hashlib.sha256(whole.encode()).hexdigest(),new_main_sha256=hashlib.sha256(reconstructed.encode()).hexdigest(),whole_inverse=True),review_checks=['Read complete new Client and unchanged inherited V3 retry/command/API/upload/authenticated/anonymous and actual signal propagation.', 'Only uncertain-absent upload permits new attempt; successful-but-absent uses bounded metadata-only retries; permanent absent, ambiguous, different/incomplete assets remain fatal and never clobbered.', 'Actual timeout child closed with SIGTERM; retry recovered on second real child. Saved collision/visibility, integrity/permanent/no-local-source-change and budget controls rechecked.', 'All transport compressed stdout/stderr fully decoded and uncompressed hash checked; exact stop in upload/backoff made one upload and terminal FAIL.', 'Complete CLI authenticated and anonymous byte readbacks retained; no tested producer/native/GitHub operation was rerun by reviewer.'],scope='Bounded publisher transport reconciliation review only; no new numerical solver, no PHY or timing acceptance. Direct Client use assumes declared validattempts; CLI preserves1..4 and120s upper bounds.')
q=B/'source-saved-peer-pll01.json';assert not q.exists();q.write_text(json.dumps(out,indent=2)+'\n');print(out['status'],pin(q),child_count)
