"""Finite V18 measured candidate delivery; later MAX4118 campaign stays separate."""
from pathlib import Path
import datetime,hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())

releases=[]
for name,count in [('controls-release01.json',4),('native-release01.json',2)]:
 p=B/name;r=json.loads(p.read_text());assert r['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(r['assets'])==count
 for asset in r['assets']:assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
 for row in r['files']:assert pin(Path(row['path']))=={k:row[k] for k in ['bytes','sha256']}
 releases.append(r)
freeze=json.loads((B/'source-freeze.json').read_text());controls=json.loads((B/'pcie-integrity-v18-core-controls-validation-20261005.json').read_text());decision=json.loads((B/'candidate-decision.json').read_text());native=json.loads((B/'pcie-integrity-v18-native-validation-20261005.json').read_text())
for path,value in freeze['files'].items():assert pin(R/path)==value
assert controls['status']=='PASS_BALANCED_COMMIT_AND_ACTUAL_PUBLIC_FAULT_CONTROLS'
assert json.loads((B/'continuation-status01.json').read_text())['status']=='COMPLETE_NATIVE_SCREEN_FINITE_REVIEW_AND_PUBLICATION_REQUIRED'
files={str(p.relative_to(R)):pin(p) for p in B.rglob('*') if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and 'max4118-01' not in p.parts and p.name not in ['active-checkpoint.json','ready-finite.json','build-ready.log']}
r=dict(status='READY_V18_MEASURED_REGRESSION_NOT_ADOPTED',utc=datetime.datetime.now(datetime.UTC).isoformat(),source_allowlist=[dict(repository_path=p,**v) for p,v in freeze['files'].items()],controls={k:controls[k] for k in ['pytest_executions','distinct_predicates','duplicate_predicate','positive_public_cases','actual_RTL_mutants','corrected_full_parser_cases','parser_outputs','excluded_MAX4118_ids','skipped']},source_peer=pin(B/'source-only-peer-pll02.json'),root_focused_peer=pin(B/'commit-controls02-validation.json'),native_source_bridge=pin(B/'native-source-bridge01.json'),native=dict(mapped_cells=native['native_cell_count'],flops=native['flops'],limit_bytes=2*1024**3,CPU6=True,profile_ns=4,setup_ns=decision['setup_ns'],hold_ns=decision['hold_ns'],delta_vs_V17_ns=decision['delta_vs_V17'],delta_vs_V11_ns=decision['delta_vs_V11'],import_cell_pin_bits=native['native_import_full_pin_proof']['checked_cell_pin_bits'],actual_import_graph_mutants=6),candidate_decision=pin(B/'candidate-decision.json'),releases={n:pin(B/n) for n in ['controls-release01.json','native-release01.json']},assets=[a for r in releases for a in r['assets']],evidence=files,stable_baseline='V11',adopted=False,physical_acceptance=False,scope='Balanced last-commit reducer fromfrozenV17 preserves complete parser public behavior. Completed21pytest executions/20distinct and26public cases,32768fullparser arbitrary-state cases,16actualRTLmutants. Original correlated focused stimulus and equivalent upper-valueZ mutant explicitly superseded, not PASS; corrected LOOKoffset/fallbackZ detected. Native100625cells/9410FF,192cells belowV17 but same4ns setup worsens79.384/71.241/42.954ps versusV17. Holds positive; no adoption. Entire public135member and combined94member capsules plus native162member capture authenticated+anonymous verified. Two MAX4118 positives excluded fromthiscut; newly assigned separate max4118-01 campaign remains pending/outofscope. No fullformal/mappedfunctionalreplay/place/CTS/route/RC/wholechipLVS/PHY/productionapproval. Frozen sourcefreeze historical pending wording preserved; final completed gates bind root8PASS and public13PASS.')
with (B/'ready-finite.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(dict(ready=pin(B/'ready-finite.json'),sources=len(r['source_allowlist']),evidence=len(files),assets=len(r['assets']))))
