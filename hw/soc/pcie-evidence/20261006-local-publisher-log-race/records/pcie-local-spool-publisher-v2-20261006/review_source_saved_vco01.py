# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-byte/source reading; never imports reviewed workers/tests."""
from pathlib import Path
import ast,hashlib,json,os,resource,xml.etree.ElementTree as E
os.sched_setaffinity(0,{2});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
R=Path.cwd();B=Path(__file__).resolve().parent;F=B/'source-freeze01.json';P=B/'launch01/policy.json'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert pin(F)==dict(bytes=426687,sha256='d648b47da536f585bdf60e89b0c9e5c048edad70ee973b1448af641dbb9405c8')
assert pin(P)==dict(bytes=1958,sha256='a6cd2cc532972dba983e4098650165fa0cb24582a4e3b8be9f008f740e269bef')
f=json.loads(F.read_text());p=json.loads(P.read_text());assert len(f['pins'])==1448
for name,value in f['pins'].items():assert pin(name)==value,name
for name,value in p['pins'].items():assert pin(name)==value,name
for name,value in f['sources'].items():assert pin(R/name)==value,name
old=(R/'scripts/publish_pcie_local_spool_v1.py').read_text();new=(R/'scripts/publish_pcie_local_spool_v2.py').read_text()
def functions(text):return {n.name:n for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
a=functions(old);b=functions(new);assert set(b)==set(a)|{'evidence_bytes'}
for name in a:
 if name!='guard':assert ast.dump(a[name])==ast.dump(b[name]),name
old_guard=ast.get_source_segment(old,a['guard']);new_guard=ast.get_source_segment(new,b['guard']);walker=ast.get_source_segment(new,b['evidence_bytes'])
x=old.replace('import shutil\n','import shutil\nimport stat\n',1).replace('Independent bounded publisher of immutable locally committed PLL parts.','Independent publisher V2 with bounded full-tree retries for moving logs.',1).replace(old_guard,walker+'\n\n\n'+new_guard,1);assert x==new
inverse=new.replace(walker+'\n\n\n'+new_guard,old_guard,1).replace('import shutil\nimport stat\n','import shutil\n',1).replace('Independent publisher V2 with bounded full-tree retries for moving logs.','Independent bounded publisher of immutable locally committed PLL parts.',1);assert inverse==old
oldtests=(R/'sw/tests/test_pcie_local_spool_publisher_v1.py').read_text();newtests=(R/'sw/tests/test_pcie_local_spool_publisher_v2.py').read_text();ta=functions(oldtests);tb=functions(newtests)
for name,node in ta.items():
 actual=ast.get_source_segment(newtests,tb[name]).replace('publish_pcie_local_spool_v2.py','publish_pcie_local_spool_v1.py');assert ast.dump(ast.parse(actual))==ast.dump(ast.parse(ast.get_source_segment(oldtests,node))),name
campaigns=[]
for i in range(1,4):
 root=E.parse(B/f'controls0{i}.xml').getroot();cases=list(root.iter('testcase'));failed=[c.attrib['name']for c in cases if c.find('failure')is not None or c.find('error')is not None];assert len(cases)==31 and not any(c.find('skipped')is not None for c in cases)
 for c in cases:assert c.attrib['name'].split('[')[0]in tb,c.attrib['name']
 campaigns.append(dict(xml=pin(B/f'controls0{i}.xml'),executions=len(cases),passed=len(cases)-len(failed),failed=failed))
assert [len(c['failed'])for c in campaigns]==[4,1,0]
fixture=B/'fixtures03';public=[];owners=[]
for path in sorted(fixture.rglob('publication.json')):
 d=json.loads(path.read_text());assert d['native_result_unmodified']is True and d['physical_acceptance']is False
 public.append(dict(path=str(path),status=d['status'],attempts=len(d['attempts']),assets=len(d['assets']),explicit_stop=d.get('explicit_stop')))
for path in sorted(fixture.rglob('*owner*.json')):
 d=json.loads(path.read_text())
 if 'processes'not in d:continue
 for child in d['processes']:
  if child['status']!='REAPED_NO_LIVE_MEMBERS':
   assert child['status']=='FAILURE_REAPED' and d['status']=='CANCELLED' and d['reason']=='Parent received SIGTERM'
   cleanup=d['cleanup'];assert not cleanup['recording_errors']and not cleanup['observation_errors']
   group=next(g for g in cleanup['groups']if g['process_group']==child['process_group']);assert not group['identity_reused']and group['term_sent']and group['immediate_after_kill']==[]
  pid=child['identity']['pid'];statpath=Path(f'/proc/{pid}/stat')
  if statpath.exists():
   fields=statpath.read_text().rsplit(') ',1)[1].split();assert fields[19]!=str(child['identity']['start_ticks'])or fields[0]=='Z'
 owners.append(dict(path=str(path),pin=pin(path),processes=len(d['processes']),status=d['status']))
recovery=fixture/'test_recovery_reconciles_exist0';state=json.loads((recovery/'upload-state.json').read_text());assert state['uploads']==0
r=json.loads((recovery/'recovery/publication.json').read_text());assert r['status']=='PASS_ALL_COMPLETE_LOCAL_PARTS_PUBLIC'and len(r['assets'])==1
for i in [0,1]:
 d=fixture/f'test_actual_offline_worker_sto{i}';x=json.loads((d/'publication/publication.json').read_text());assert x['explicit_stop']is True
 y=json.loads((d/'recovered-publication/publication.json').read_text());assert y['status']=='PASS_ALL_COMPLETE_LOCAL_PARTS_PUBLIC'and len(y['assets'])==1
 for a in y['assets']:assert a['asset']['authenticated_roundtrip']is True and a['asset']['anonymous_roundtrip']is True
# Launch checks are source read only, not executed; failed native-independent
# worker receipt and immutable configuration are already pinned above.
failed=json.loads(Path(p['failed_publication']).read_text());assert failed['status']=='ERROR_INDEPENDENT_PUBLICATION_LOCAL_SOURCE_RETAINED'and failed['explicit_stop']is False
assert p['native_signals_or_adoption']is False and p['full_reverify_existing_assets']is True
launch=(B/'launch01/launch_publisher01.py').read_text()
for expected in ['start_new_session=True','close_fds=True',"'PYTHONEXECUTABLE'","'PYTHONOPTIMIZE'",'len(assets) + 515 <= 1000',".open('x')",'not out.exists()']:assert expected in launch
assert all(pin(name)==value for name,value in p['pins'].items())
receipt=dict(status='PASS_SOURCE_SAVED_PUBLISHER_V2_AND_LAUNCH',reviewer='/root/vco_loaded_feedback',freeze=pin(F),policy=pin(P),method=pin(__file__),findings=[],rehashed_freeze_pins=1448,complete_worker_forward_inverse=True,unchanged_worker_functions=sorted(set(a)-{'guard'}),all_prior_test_function_ASTs_unchanged_except_literal_worker_basename=True,actual_current_predicates=31,current_prior_predicates=21,current_new_predicates=10,historical_campaigns=campaigns,historical_executions=93,historical_passed=88,historical_failed=5,saved_publication_terminals=public,saved_owned_receipts=owners,reviewer_attempts_retained=['attempt01: AST source excludes final newline, so full-byte reconstruction initially missed one blank line; exact formatting corrected.','attempt02: expected all saved owners to be successful; actual intentional SIGTERM owner is CANCELLED/FAILURE_REAPED with exact clean cleanup. Corrected to enforce this precise expected terminal schema and retained both attempts.'],source_review=['Complete V1 bytes restored after sole docstring/import/guard replacement. All worker state-machine, source/receipt bindings, cancellation handoffs, V4 ownership and metadata reserve behavior unchanged.','ENOENT invalidates entire tree sample and restarts from root at most four times. Non-ENOENT propagates; observed non-regular entries fail; hardlinks count conservatively per name. This remains a sampled guard over its owned publication directory, not an atomic quota or adversarial rename-proof directory capability.','Read real rename/compress-unlink/subtree-removal control paths, actual sparse overcap, permission/EIO failures, four failed rescans, static symlink refusal and recovery with zero uploads/full dual readback.','Fresh launcher rehashes all frozen sources/controls/runtime/configuration, refuses duplicate spool worker, checks boot/free SSD/release headroom, starts exact CPU14 V2 detached. No old asset seeding, source mutation, native adoption or signaling.'],scope='Independent source and saved data only. No reviewed worker/tests/imports, network, native, or control reruns. Allows fresh existing-policy V2 publication launch; does not validate native physical result or future capacity indefinitely.')
(B/'source-saved-peer-vco01.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(receipt=pin(B/'source-saved-peer-vco01.json'),owners=len(owners),terminals=len(public),status=receipt['status'])))
