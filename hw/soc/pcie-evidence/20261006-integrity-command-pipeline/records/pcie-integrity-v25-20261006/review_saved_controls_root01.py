"""Independent saved V25 campaign recount; no HDL rerun or product mutation."""
from pathlib import Path
import ast, collections, hashlib, json, lzma, os, re, resource, tarfile, time
import xml.etree.ElementTree as ET
R=Path.cwd(); B=Path(__file__).resolve().parent; D=Path('/dev/shm/nssoc-integrity-v25-full-controls02')
os.sched_setaffinity(0,{2});resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);started=time.monotonic()
def pin(p):
 p=Path(p)
 with p.open('rb') as s:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(s,'sha256').hexdigest()}
def read(p):return json.loads(Path(p).read_text())
def require(p,w):assert pin(p)=={k:w[k] for k in ('bytes','sha256')},str(p)
vpath=B/'pcie-integrity-v25-current-controls02-validation-20261006.json';v=read(vpath)
f=read(B/'source-freeze04.json');require(B/'source-freeze04.json',v['source_freeze'])
peer=read(B/'source-only-peer-rx04.json');assert not peer['findings'];require(B/'source-only-peer-rx04.json',v['source_peer'])
for p,w in f['sources'].items():require(R/p,w)
old=read(B/'failed-controls01/validation.json')
archive_reviews=[]
for label,rec,mp,current in [('current',v['archive'],B/'current-controls02-members.json',True),('retained_failed',old['archive'],B/'failed-controls01/members.json',False)]:
 require(rec['path'],rec); require(mp,v['manifest'] if current else old['member_manifest']);man=read(mp);seen=set();total=0;historical_xml=None
 with lzma.open(rec['path'],'rb') as decoded:
  with tarfile.open(fileobj=decoded,mode='r|',bufsize=1024**2) as tar:
   for member in tar:
    assert member.isfile() and member.name not in seen and not member.name.startswith('/') and '..' not in Path(member.name).parts
    expected=pin(mp) if member.name=='members.json' else man[member.name]
    stream=tar.extractfile(member);h=hashlib.sha256();n=0;selected=[]
    while chunk:=stream.read(1024**2):
     h.update(chunk);n+=len(chunk)
     if member.name.endswith('controls01.xml'):selected.append(chunk)
    assert n==member.size==expected['bytes'] and h.hexdigest()==expected['sha256'],member.name
    if selected:historical_xml=ET.fromstring(b''.join(selected))
    seen.add(member.name);total+=n
  while chunk:=decoded.read(1024**2):assert not any(chunk)
 assert seen==set(man)|{'members.json'} and len(seen)==rec['members']
 origins=0
 if current:
  for row in man.values():require(row['original'],row);origins+=1
 else:
  assert historical_xml is not None
  cs=list(historical_xml.iter('testcase'));assert len(cs)==42 and sum(c.find('failure') is not None for c in cs)==2
 archive_reviews.append(dict(label=label,archive=rec,manifest=pin(mp),members=len(seen),logical_bytes=total,current_origins_rehashed=origins))
cs=list(ET.parse(B/'controls02.xml').iter('testcase'));names=[c.get('name') for c in cs]
assert len(cs)==len(set(names))==43 and all(not any(c.find(n) is not None for n in ['failure','error','skipped']) for c in cs)
assert not any('4118' in n for n in names);assert f['excluded_MAX4118_predicates']==1
assert '43 passed, 1 deselected' in (B/'controls02.log').read_text()
oldcs=list(ET.parse(B/'controls01.xml').iter('testcase'));failed=[c for c in oldcs if c.find('failure') is not None]
assert len(oldcs)==42 and len(failed)==2
assert {c.get('name') for c in failed}=={'test_actual_command_temporal_relation[positive]','test_actual_pending_badblock_fault_edge_and_capacity_quarantine'}
assert any('V25_COMMAND_UNKNOWN_CONTROL_WRITES' in (c.find('failure').text or '') for c in failed)
assert any('V25_FRAMER_UNEXPECTED_FAULT' in (c.find('failure').text or '') for c in failed)
status=read(B/'status02.json');assert status['returncode']==0 and status['stop_reason'] is None
for key in ['controller','pytest']:
 row=status[key];p=Path('/proc')/str(row['pid'])/'stat'
 assert not p.exists() or p.read_text().rsplit(') ',1)[1].split()[19]!=str(row['start_ticks'])
helpers=[]
for p in sorted(D.glob('*/capture/result.json')):
 j=read(p)
 for n,w in j['inputs'].items():require(n,w)
 for n,w in j.get('outputs',{}).items():require(p.parent/n,w)
 xml=p.parent/'results.xml';tests=list(ET.parse(xml).iter('testcase'));counts=dict(passed=0,failed=0,skipped=0)
 for c in tests:counts['failed' if any(c.find(x) is not None for x in ['failure','error']) else 'skipped' if c.find('skipped') is not None else 'passed']+=1
 if 'tests' in j:assert counts==j['tests'] and counts['failed']==0
 else:assert j['status']=='FAIL' and counts['failed']>0
 helpers.append(dict(path=str(p),receipt=pin(p),xml=pin(xml),counts=counts))
assert len(helpers)==24 and sum(x['counts']['failed']>0 for x in helpers)==20
positives=[x['counts'] for x in helpers if x['counts']['failed']==0]
assert collections.Counter(tuple(x.values()) for x in positives)==collections.Counter({(19,0,0):2,(1,0,18):2})
counts=read(D/'test_actual_all_public_transac0/capture/v25-command-witnesses.json');assert counts['cache_quarantine_counts']==[8,8,8] and min(counts['counts'])>0 and min(counts['epoch_counts'])>0
for d in D.glob('test_actual_nominal_ready_one_*/capture'):assert 'V25_NOMINAL_PLUS_ONE_PASS' in (d/'simulation.log').read_text()
tree=ast.parse((R/'sw/tests/test_pcie_gen3_integrity_v25_command.py').read_text())
faults=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FAULTS' for t in n.targets)))
assert len(faults)==12
text=(D/'test_actual_command_temporal_r0/simulation.log').read_text();line=next(x for x in text.splitlines() if x.startswith('V25_COMMAND_RELATION_PASS '));a=dict((k,int(n)) for k,n in re.findall(r'(\w+)=(\d+)',line))
assert a==dict(comparisons=4102,bubbles=587,replace=2927,ending=1,epochs=5,previous_verdict=4,duplicate=1,wraps=512,unknown_holds=10,unknown_fault_applies=2)
mutants=[]
for i,row in enumerate(faults,1):
 p=D/f'test_actual_command_temporal_r{i}';log=(p/'simulation.log').read_text();assert 'FATAL:' in log and row[3] in log and 'V25_COMMAND_RELATION_PASS' not in log
 mutant=(p/'command.v').read_text();assert row[2] in mutant
 mutants.append(dict(name=row[0],diagnostic=row[3],log=pin(p/'simulation.log'),compiled_image=pin(p/'command.vvp')))
reset=next(x for x in mutants if x['name']=='reset_apply_guard_removed');assert reset['diagnostic']=='V25_COMMAND_UNKNOWN_CONTROL_WRITES'
pending=(D/'test_actual_pending_badblock_f0/fault_epochs/simulation.log').read_text();assert 'V25_PENDING_FAULTS_PASS badblocks=2 overflow=1 recoveries=3' in pending and 'ending=4' in pending and 'V25_REAL_LINE_RATE' in pending
bursts=list(D.glob('test_actual_accepted_block_tr*/burst/result.json'));assert len(bursts)==2
for p in bursts:
 j=read(p);assert j['returncode']==0 and j['fault'] is None
 log=(p.parent/'simulation.log').read_text();assert 'PASS_V25_FRAMER_BURST' in log and 'V25_REAL_LINE_RATE' in log
assert {read(p)['ring'] for p in bursts}=={16,64}
result=dict(status='PASS_INDEPENDENT_SAVED_V25_CURRENT_43_FUNCTIONAL_PREDICATES',reviewer='root independent full archive and saved native predicate recount',validation=pin(vpath),findings=[],source_freeze=pin(B/'source-freeze04.json'),source_peer=pin(B/'source-only-peer-rx04.json'),source_pins=len(f['sources']),archives=archive_reviews,current_cases=names,current43_passed=True,historical40_passed_2_failed_retained=True,MAX4118_deselected_open=1,helper_xml_recounts=helpers,component_counts=a,component_actual_mutants=mutants,command_epoch_witnesses=counts,physical_acceptance=False,general_cycle_equivalence=False,limits='Component X/Z/reset validity plus declared transaction profiles; not arbitrary full-framer X/Z reset, full MAX4118, native timing, PHY or chip acceptance. Ring16 explicit stress, not automatic default. Stale frozen42/11/no-execution metadata qualified by current43/12 saved facts.',method=pin(__file__),elapsed_seconds=time.monotonic()-started)
out=B/'saved-controls-peer-vco04.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],peer=pin(out),elapsed=result['elapsed_seconds'],archives=[x['members']for x in archive_reviews])))
