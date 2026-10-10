"""Prepare one reviewed V24 native screen; this script launches no EDA."""
from pathlib import Path
import ast,hashlib,json,difflib
R=Path.cwd();B=Path(__file__).resolve().parent;P=B.parent/'pcie-integrity-v23-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
F=B/'source-freeze03.json';fr=json.loads(F.read_text());C=B/'pcie-integrity-v24-composite-controls-validation-20261006.json';control=json.loads(C.read_text())
assert control['status']=='PASS_V24_PREFIX_CONTEXT_COMPOSITE_CONTROLS' and control['source_freeze']==pin(F)
CP=B/'saved-controls-peer-vco03.json';cp=json.loads(CP.read_text());assert cp['status']=='PASS_INDEPENDENT_SAVED_V24_COMPOSITE_FUNCTIONAL_CONTROLS' and cp['validation']==pin(C) and not cp['findings']
def version(s):return s.replace('v23','v24').replace('V23','V24')
s=version((P/'run_balanced_map03.py').read_text())
first=s.index('assert pin(FREEZE)');last=s.index("assert shutil.disk_usage('/dev/shm').free>=1024**3")
gate="""assert pin(FREEZE)['sha256']==FREEZEHASH
for name,value in json.loads(FREEZE.read_text())['sources'].items():assert pin(R/name)==value
CORE=FREEZE.parent/'pcie-integrity-v24-composite-controls-validation-20261006.json'
validation=json.loads(CORE.read_text())
assert validation['status']=='PASS_V24_PREFIX_CONTEXT_COMPOSITE_CONTROLS' and validation['source_freeze']==pin(FREEZE)
assert [(x['passed'],x['failed'],x['skipped'])for x in validation['campaigns']]==[(41,1,0),(2,0,0)]
assert validation['pytest_executions']==44 and validation['passed_executions']==43 and validation['historical_failed_executions']==1
assert validation['current_42_predicates_covered'] and validation['public_profiles']==dict(direct=18,cycle_miter=18,unchanged_latency=True)
assert validation['cache_fault_write_epochs']==8 and len(validation['meaningful_miter_mutants'])==12 and len(validation['context_bank_mutants'])==4
assert validation['component']['comparisons']==3796416 and validation['component']['actual_faults']==4
assert validation['packing']==dict(vectors=672,binary=512,literal_XZ=160,positions=16,actual_faults=2)
PEER=FREEZE.parent/'source-only-peer-vco03.json';assert pin(PEER)==validation['source_peer'] and not json.loads(PEER.read_text())['findings']
SAVED_PEER=FREEZE.parent/'saved-controls-peer-vco03.json';saved_peer=json.loads(SAVED_PEER.read_text())
assert saved_peer['status']=='PASS_INDEPENDENT_SAVED_V24_COMPOSITE_FUNCTIONAL_CONTROLS' and not saved_peer['findings'] and saved_peer['validation']==pin(CORE)
CONTROL_ROWS=validation['campaigns']+validation['helper_receipts']
CONTROL_RECEIPTS=[Path(row['path'])for row in CONTROL_ROWS]
for p,row in zip(CONTROL_RECEIPTS,CONTROL_ROWS):assert pin(p)=={k:row[k]for k in ('bytes','sha256')}
""".replace('FREEZEHASH',repr(pin(F)['sha256']))
s=s[:first]+gate+s[last:]
old_scope="Separate V24 registered accepted adjacent header relation from frozen V22. Same public latency, strict 18-case public and cycle miter, declared literal557056/XZ1440 and actual predecessor/cache fault witnesses. Exact balancedABC script and150-byte v2 mapping profile. Full native proof/replay and timing acceptance remain separate; frozen v1/v2/v3/v4/v5/v6/v7/v8/v9 unchanged."
new_scope="Separate V24 accepted-bank token-only prefix context from frozen V23. Same public latency and original18 direct/cycle profiles;3796416 finite literal relation comparisons,672 full packing cases and actual bank/fault ownership witnesses. Exact balancedABC script and150-byte v2 mapping profile. Native graph/timing only; full mapped functional replay and physical acceptance remain separate."
assert s.count(old_scope)==1;s=s.replace(old_scope,new_scope)
(B/'run_balanced_map03.py').write_text(s);ast.parse(s)
s=version((P/'continue_native03.py').read_text()).replace('81b39160001de5717fa414371ec18b62772e367e7625e7aaab3af3b0f3af0540',pin(F)['sha256'])
s=s.replace('PASS_V24_ADJACENT_HEADER_COMPOSITE_CONTROLS','PASS_V24_PREFIX_CONTEXT_COMPOSITE_CONTROLS').replace('[(28,7,0),(6,3,0),(3,0,0)]','[(41,1,0),(2,0,0)]')
s=s.replace('Composite47executions with10retainedhistorical failures; original18case pluscorrected18th direct/miter and meaningful realblock promotioncontrol required.','Composite44executions with1retainedhistoricalhostfailure; original18case direct/miter and actual context-bank/prefix/packing controls required.')
(B/'continue_native03.py').write_text(s);ast.parse(s)
# Add exact V23 comparator without changing parser, constraints or path selection.
t=B/'review_timing.py';before=t.read_text();extra="""previous23_path=B.parent / 'pcie-integrity-v23-20261006/timing-comparison.json'
assert hashlib.sha256(previous23_path.read_bytes()).hexdigest()==BASELINEHASH
previous23=json.loads(previous23_path.read_text())
old23={(r['corner'],r['direction']):r['worst_slack_ns'] for r in previous23['groups'] if r['stage']=='PREPLACEMENT_REPAIRED'}
delta23={r['corner']+'_'+r['direction']:r['worst_slack_ns']-old23[r['corner'],r['direction']] for r in rows if r['stage']=='PREPLACEMENT_REPAIRED'}
""".replace('BASELINEHASH',repr(pin(P/'timing-comparison.json')['sha256']))
assert 'previous23_path' not in before
after=before.replace('markers = list(parser.MARKER.finditer(text))',extra+'markers = list(parser.MARKER.finditer(text))').replace('delta_vs_v19=delta19,','delta_vs_v19=delta19, delta_vs_v23=delta23,')
t.write_text(after);ast.parse(after)
methods=['run_balanced_map03.py','native_lifecycle02.py','continue_native03.py','measure_registered_boundary.py','balanced_import02.py','prove_balanced_import.py','balanced_preplacement02.py','review_timing.py','analyze_critical_path.py']
for n in methods:assert (B/n).is_file()
policy=dict(status='FROZEN_V24_MERGED_NATIVE_CONTINUATION_REQUIRES_SOURCE_PEER',method_pins={str(B/n):pin(B/n)for n in methods},source_pins=fr['sources'],controls=dict(validation=dict(path=str(C),**pin(C)),independent_peer=dict(path=str(CP),**pin(CP))),PLL=json.loads((P/'continuation-policy01.json').read_text())['PLL'],CPU=6,AS_bytes=2*1024**3,clock_period_ns=4.0,actual_stage_paths={n:pin(B/n)for n in methods if n not in('native_lifecycle02.py','continue_native03.py')},fresh_outputs=[f'/dev/shm/nssoc-integrity-v24-balanced-{n}-01'for n in('map','import','sta')],native_lifecycle_ancestry=json.loads((P/'continuation-policy01.json').read_text())['native_lifecycle_ancestry'],no_new_native_started=True)
policy_path=B/'continuation-policy01.json';policy_path.write_text(json.dumps(policy,indent=2)+'\n')
s=version((P/'detach_native01.py').read_text()).replace(repr(pin(P/'continuation-policy01.json')),repr(pin(policy_path)))
(B/'detach_native01.py').write_text(s);ast.parse(s)
rows=[]
for n in methods+['detach_native01.py']:
 old=P/n;new=B/n
 rows.append(dict(parent=dict(path=str(old),**pin(old)),candidate=dict(path=str(new),**pin(new)),whole_diff=''.join(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True)))))
rec=dict(status='V24_NATIVE_WHOLE_SOURCE_BRIDGES_NO_EXECUTION',policy=pin(policy_path),launcher=pin(B/'detach_native01.py'),rows=rows,baseline23=dict(path=str(P/'timing-comparison.json'),**pin(P/'timing-comparison.json')),native_profile='Exact original4ns/CPU6/2GiB/150-byte native tail, same ABC/import/literal-ties/pin graph/registered-boundary/24STA groups.',all_actual_stage_files_exist=True)
(B/'native-source-bridges01.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(dict(policy=pin(policy_path),launcher=pin(B/'detach_native01.py'))))
