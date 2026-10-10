"""Finite V19 measured candidate; preserved witness failure is not relabelled."""
from pathlib import Path
import datetime,hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
releases=[]
for name,count in [('controls-release01.json',3),('native-release01.json',2)]:
 p=B/name;r=json.loads(p.read_text());assert r['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(r['assets'])==count
 for row,asset in zip(r['files'],r['assets'],strict=True):
  assert asset['authenticated_roundtrip']and asset['anonymous_roundtrip']
  assert pin(Path(row['path']))=={k:row[k]for k in ['bytes','sha256']}
  assert all(row[k]==asset[k]for k in ['name','bytes','sha256'])
 releases.append(r)
freeze=json.loads((B/'source-freeze04.json').read_text());controls=json.loads((B/'pcie-integrity-v19-core-controls-validation-20261005.json').read_text());decision=json.loads((B/'candidate-decision.json').read_text());native=json.loads((B/'pcie-integrity-v19-native-validation-20261005.json').read_text())
for path,value in freeze['files'].items():assert pin(R/path)==value
assert controls['status']=='PASS_SEVEN_SLOT_QUARANTINE_AND_ACTUAL_PUBLIC_FAULT_CONTROLS'and controls['historical_failed_executions']==1
assert json.loads((B/'continuation-status02.json').read_text())['status']=='COMPLETE_NATIVE_SCREEN_FINITE_REVIEW_AND_PUBLICATION_REQUIRED'
files={str(p.relative_to(R)):pin(p)for p in B.rglob('*')if p.is_file()and not p.is_symlink()and '__pycache__'not in p.parts and p.name not in ['active-checkpoint.json','ready-finite.json','build-ready.log']}
r=dict(status='READY_V19_MEASURED_REGRESSION_NOT_ADOPTED',utc=datetime.datetime.now(datetime.UTC).isoformat(),source_allowlist=[dict(repository_path=p,**v)for p,v in freeze['files'].items()],controls={k:controls[k]for k in ['pytest_executions','pytest_passed_executions','historical_failed_executions','original_selected_tests_covered','distinct_original_predicates','positive_public_case_executions','actual_RTL_mutants','literal_cases','literal_unknown_step_holds','literal_wrap_writes','excluded_MAX4118_ids','pytest_skipped','targeted_cocotb_intentionally_unselected']},functional_source_peer=pin(B/'source-only-peer-rx04.json'),merged_and_lifecycle_peer=pin(B/'native-source-only-peer02.json'),native_source_bridge=pin(B/'native-source-bridge02.json'),native=dict(mapped_cells=native['native_cell_count'],flops=native['flops'],limit_bytes=2*1024**3,CPU6=True,profile_ns=4,setup_ns=decision['setup_ns'],hold_ns=decision['hold_ns'],delta_vs_V17_ns=decision['delta_vs_V17'],delta_vs_V11_ns=decision['delta_vs_V11'],import_cell_pin_bits=native['native_import_full_pin_proof']['checked_cell_pin_bits'],actual_import_graph_mutants=6),candidate_decision=pin(B/'candidate-decision.json'),releases={n:pin(B/n)for n in ['controls-release01.json','native-release01.json']},assets=[a for r in releases for a in r['assets']],evidence=files,stable_baseline='V11',adopted=False,physical_acceptance=False,scope='Seven ringcontentwrites separated underexactstep fromfrozenV17. Public/occupied/committedvisibility equivalence, not arbitraryinvalidstorage equivalence. Initial26PASS/1FAIL strictactualinvaliddifference coverage retained; onlyelevenlinepublicprefill added, allstrictassertions unchanged. Correctedfull14miter+targeteddirectepochPASS with16faultsteps,16observablydifferentinvalidwrites,16heldfaults. 29pytestexecutions=28PASS+1historicalFAIL coveroriginal27selectedtests/26distinctpredicates,22actualRTLfaults,4096literalcases. Native103720cells/9410FF,+2903cells vsV17; same4ns setup regresses84.146/93.771/62.561ps. Holdspositive. No adoption; newcritical read_ptr[3] to current_valid. Rawinitial206memberfailure,252membercombinedcontrols and174membernative archives arepublic. TwoMAX4118profilesexcluded; changedcase direct intentionallyunselected13oldcases, coveredbyunchangedfirst13priorfullrun. No fullformal/mappedfunctionalreplay/place/CTS/route/RC/wholechipLVS/PHY/productionapproval.')
with (B/'ready-finite.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(dict(ready=pin(B/'ready-finite.json'),sources=len(r['source_allowlist']),evidence=len(files),assets=len(r['assets']))))
