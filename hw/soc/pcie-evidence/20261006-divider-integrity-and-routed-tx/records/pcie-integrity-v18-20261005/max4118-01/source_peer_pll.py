"""Read-only independent source/saved-evidence review; no processes launched."""
from pathlib import Path
import ast,datetime,hashlib,json
B=Path(__file__).resolve().parent;R=B.parents[4]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
assert pin(B/'run.py')==dict(bytes=8582,sha256='2524980c5a3110d40592066dafc5aa4d0fdaaae68bebc7e49d789b723c66245b')
assert pin(B/'policy.json')==dict(bytes=27068,sha256='96677ce5b807f9b816dc099ae4da2782723fccff538cab6f5f8e9f8786b07094')
p=json.loads((B/'policy.json').read_text());l=json.loads((B/'lifecycle-controls.json').read_text())
for name,value in p['pins'].items():assert pin(name)==value,name
for name,value in l['raw_files'].items():assert pin(name)==value,name
assert l['source']==pin(B/'run.py') and l['method']==pin(B/'lifecycle_controls.py')
assert len(l['rows'])==4 and [x['case'] for x in l['rows']]==['healthy','resource','cancel_tree','complete_signal']
for row in l['rows']:
 assert row['status']=='PASS_ACTUAL_LIFECYCLE_CONTROL' and not any(x['state']!='Z' for x in row['remaining'])
 if row['case'] in ['resource','cancel_tree']:
  assert len({x['process_group'] for x in row['tree_cleanup']['before']})==2
  assert {x['signal'] for x in row['tree_cleanup']['signals']}=={9,15}
  for x in row['tree_cleanup']['before']:
   q=Path('/proc')/str(x['pid'])/'stat'
   if q.exists():assert q.read_text().rsplit(') ',1)[1].split()[19]!=x['start_ticks']
assert len(p['stages'])==2
for stage,test in zip(p['stages'],['sw/tests/test_pcie_gen3_continuous_rx_integrity_v18.py::test_actual_wide_rx_full_positive_profiles[4118]','sw/tests/test_pcie_gen3_integrity_v18_miter.py::test_v11_v18_cycle_exact_all_public_outputs[4118]']):
 assert stage['command'].count(test)==1
assert p['CPU']==2 and p['native_AS']==2147483648 and p['healthy_elapsed_timeout'] is None
s=(B/'run.py').read_text();a=ast.parse(s)
assert 'PR_SET_CHILD_SUBREAPER' in s and 'if row[\'state\'] != \'Z\' and same_birth(row)' in s
for literal in ['assert not any(c[\'state\'] != \'Z\' for c in descendants())','owner.check()','record[\'tree_cleanup\'] = cleanup_tree()']:
 assert literal in s
r=dict(status='PASS_SOURCE_ONLY_V18_MAX4118_CONTROLLER',utc=datetime.datetime.now(datetime.UTC).isoformat(),policy=pin(B/'policy.json'),source=pin(B/'run.py'),review_method=pin(Path(__file__)),saved_lifecycle=pin(B/'lifecycle-controls.json'),rehashes=dict(policy_pins=len(p['pins']),raw_lifecycle_files=len(l['raw_files'])),findings=[],reviewed=['Only two exact unchanged4118 pytest node IDs, CPU2 and inherited2GiB child AS.','Fresh output/status guards,110immutable pins checked before launch and between stages; peer policy gate.','Subreaper owns separately sessioned nested children; ancestry census plus immediate PID/start checks before own per-PID signals. No external process group signaling.','Cleanup TERM grace5seconds thenKILL only after explicitstop/resource/error, no healthy elapsedwatchdog; owner cleans/reaps directchild.','Cancellation observed whilepolling, aftercomplete, before/afterownerexit; resource floors and owncaptureceiling remain unchanged.','Actual saved4controls reviewed: health,2GiB sparsecap failure, realSIGTERM killing2distinct TERM-ignoring sessions, post-complete SIGTERM. Closed child identities checked read-only.','Nonzero individual functional/frontend case is retained and second independent case may run; finalstatus cannot classifyfailedcases asPASS. XML/casecount/source relation/finitearchive remain subsequent independent gates.'],scope='Independent source and saved actual-control review only; no controller/native/test rerun or production signals. Controls invoke frozen ownership/guard functions in isolated harness, not completeproductionmain. No functional MAX4118/timing PASS claim.')
with (B/'source-peer.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(pin(B/'source-peer.json')))
