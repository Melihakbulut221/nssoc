"""Source preparation only; every native stage remains gated by current controls."""
from pathlib import Path
import hashlib,json,difflib
R=Path.cwd();B=Path(__file__).resolve().parent;OLD=B.parent/'pcie-integrity-v24-20261006'
def pin(p):return dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
bridges=[]
names=('native_lifecycle02.py','measure_registered_boundary.py','balanced_import02.py','prove_balanced_import.py','balanced_preplacement02.py','review_timing.py','analyze_critical_path.py','run_balanced_map03.py','continue_native03.py')
for name in names:
 parent=OLD/name;candidate=B/name;assert not candidate.exists()
 s=parent.read_text();s=s.replace('integrity-v24','integrity-v25').replace('integrity_v24','integrity_v25').replace('V24','V25')
 if name in ('run_balanced_map03.py','continue_native03.py'):
  s=s.replace('source-freeze03.json','source-freeze04.json').replace('0d5e960250b246c1d49e56e4e1e098fff10a2a48ce6f37b563edbd6d6ce2f604',pin(B/'source-freeze04.json')['sha256'])
 if name=='run_balanced_map03.py':
  a=s.index("CORE=FREEZE.parent/");z=s.index("assert shutil.disk_usage('/dev/shm').free>=1024**3",a)
  s=s[:a]+'''CORE=FREEZE.parent/'pcie-integrity-v25-current-controls02-validation-20261006.json'
validation=json.loads(CORE.read_text())
assert validation['status']=='PASS_V25_COMPLETE_43_CURRENT_FUNCTIONAL_PREDICATES' and validation['source_freeze']==pin(FREEZE)
assert validation['current_pytest']==dict(passed=43,failed=0,skipped=0,deselected_MAX4118=1)
assert validation['historical_pytest']==dict(passed=40,failed=2,skipped=0)
assert validation['public_profiles']==dict(direct=19,instrumented_transactions=19,nominal_plus_one_cases=2,general_cycle_equivalence=False)
assert min(validation['cache_quarantine_counts'])>=8 and validation['component']['comparisons']==4102
assert validation['component']['unknown_holds']==10 and validation['component']['unknown_fault_applies']==2 and validation['component']['actual_faults']==12
assert validation['whole_dut_mutants']==dict(public=12,architecture=8,block=2)
assert validation['pending_faults']==dict(badblocks=2,overflow=1,recoveries=3)
PEER=FREEZE.parent/'source-only-peer-rx04.json';assert pin(PEER)==validation['source_peer'] and not json.loads(PEER.read_text())['findings']
SAVED_PEER=FREEZE.parent/'saved-controls-peer-vco04.json';saved_peer=json.loads(SAVED_PEER.read_text())
assert saved_peer['status']=='PASS_INDEPENDENT_SAVED_V25_CURRENT_43_FUNCTIONAL_PREDICATES' and not saved_peer['findings'] and saved_peer['validation']==pin(CORE)
CONTROL_ROWS=validation['control_receipts']
CONTROL_RECEIPTS=[Path(row['path'])for row in CONTROL_ROWS]
for p,row in zip(CONTROL_RECEIPTS,CONTROL_ROWS):assert pin(p)=={k:row[k]for k in ('bytes','sha256')}
''' +s[z:]
  old_scope='Separate V25 accepted-bank token-only prefix context from frozen V23. Same public latency and original18 direct/cycle profiles;3796416 finite literal relation comparisons,672 full packing cases and actual bank/fault ownership witnesses.'
  assert old_scope in s;s=s.replace(old_scope,'Separate V25 registered parser-to-ring command from frozen V23. Explicit restricted nominal+1 payload latency and19-case independent transaction profiles,4102 finite command comparisons with10 unknown-control holds and12 actual mutants, real accepted-block/capacity/fault/restart tests. No general cycle equivalence.')
 if name=='continue_native03.py':
  a=s.index("  core=Path(policy['controls']");z=s.index("  stage('map'",a)
  s=s[:a]+'''  core=Path(policy['controls']['validation']['path']);assert pin(core)=={k:policy['controls']['validation'][k]for k in ['bytes','sha256']}
  result=json.loads(core.read_text());assert result['status']=='PASS_V25_COMPLETE_43_CURRENT_FUNCTIONAL_PREDICATES'
  assert result['current_pytest']==dict(passed=43,failed=0,skipped=0,deselected_MAX4118=1)
  assert result['source_freeze']==pin(B/'source-freeze04.json') and result['source_peer']==pin(B/'source-only-peer-rx04.json')
  controls_peer=Path(policy['controls']['independent_peer']['path']);assert pin(controls_peer)=={k:policy['controls']['independent_peer'][k]for k in ['bytes','sha256']}
  controls_review=json.loads(controls_peer.read_text());assert controls_review['status']=='PASS_INDEPENDENT_SAVED_V25_CURRENT_43_FUNCTIONAL_PREDICATES'and not controls_review['findings']and controls_review['validation']==pin(core)
  peer_path=B/'native-source-only-peer01.json';peer=json.loads(peer_path.read_text());assert peer['status']=='PASS_SOURCE_ONLY_V25_NATIVE_CONTINUATION' and peer['policy']==pin(B/'continuation-policy01.json') and not peer['findings']
''' +s[z:]
  s=s.replace('Composite44executions with1retainedhistoricalhostfailure; original18case direct/miter and actual context-bank/prefix/packing controls required.','Fresh43 current predicates plus original40PASS2FAIL retained separately;19case direct/instrumented transactions, restricted nominal+1 and actual command/epoch/fault boundaries required.')
 candidate.write_text(s)
 bridges.append(dict(parent=str(parent),parent_pin=pin(parent),candidate=str(candidate),candidate_pin=pin(candidate),parent_body=parent.read_text(),candidate_body=s,full_diff=''.join(difflib.unified_diff(parent.read_text().splitlines(True),s.splitlines(True)))))
(B/'native-source-bridges-draft01.json').write_text(json.dumps(dict(status='DRAFT_NATIVE_METHODS_PENDING_FUNCTIONAL_RESULT_AND_SOURCE_PEER',bridges=bridges),indent=2)+'\n')
print('Prepared nine source bodies; no native dispatch.')
