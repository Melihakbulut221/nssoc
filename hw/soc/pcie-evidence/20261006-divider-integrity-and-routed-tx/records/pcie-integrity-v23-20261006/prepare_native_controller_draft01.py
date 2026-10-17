"""Prepare unlaunched V23 chain; finite actual controls must satisfy strict gates."""
from pathlib import Path
import hashlib,json
B=Path(__file__).resolve().parent;O=B.parent/'pcie-integrity-v22-20261006';R=Path.cwd();ledger=[]
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def derive(old,new,edits):
 s=(O/old).read_text();rows=[]
 for a,b in edits:
  count=s.count(a);assert count,(old,a);s=s.replace(a,b);rows.append(dict(before=a,after=b,count=count))
 p=B/new;assert not p.exists();p.write_text(s);ledger.append(dict(parent=str(O/old),parent_pin=pin(O/old),path=str(p),pin=pin(p),replacements=rows))
old=(O/'run_balanced_map02.py').read_text();a=old[old.index('FREEZE='):old.index('assert shutil.disk_usage')]
b="""FREEZE=R/'hw/soc/out/pcie-integrity-v23-20261006/source-freeze01.json'
assert pin(FREEZE)['sha256']=='446efb90f07eb3b2fe960498c55079afb385c3a89f8e2dad6dc02f028372b630'
for name,value in json.loads(FREEZE.read_text())['sources'].items():assert pin(R/name)==value
CORE=FREEZE.parent/'pcie-integrity-v23-controls01-validation-20261006.json'
validation=json.loads(CORE.read_text())
assert validation['status']=='PASS_V23_ADJACENT_HEADER_CONTROLS'
assert {k:validation['pytest'][k]for k in ('passed','failed','skipped')}==dict(passed=35,failed=0,skipped=0)
assert validation['source_freeze']==pin(FREEZE) and validation['observations']['public_cases']==validation['observations']['cycle_exact_cases']==18
obs=validation['observations'];assert obs['cache_fault_write_epochs']==obs['cache_actual_changed_epochs']==8
assert len(obs['adjacent_positions'])==16 and min(obs['adjacent_positions'])>0 and obs['cross_block_headers']>0 and obs['minimum_first_header_end_same_beat']>0 and obs['missing_old_predecessor_accepts']>=16
assert len(obs['miter_actual_mutants'])==12 and len(obs['literal_controls'])==6 and obs['observer_negative']
PEER=FREEZE.parent/'source-only-peer-rx01.json';assert pin(PEER)==validation['source_peer']
assert not json.loads(PEER.read_text())['findings']
CONTROL_RECEIPTS=[Path(validation['pytest']['path'])]+[Path(row['path'])for row in validation['helper_receipts']]
for p,row in zip(CONTROL_RECEIPTS,[validation['pytest']]+validation['helper_receipts']):assert pin(p)=={k:row[k]for k in ('bytes','sha256')}
"""
scope="Separate V23 registered accepted adjacent header relation from frozen V22. Same public latency, strict 18-case public and cycle miter, declared literal557056/XZ1440 and actual predecessor/cache fault witnesses."
a_scope=old[old.index("'scope':'")+len("'scope':'"):old.index(" Exact balancedABC")]
derive('run_balanced_map02.py','run_balanced_map02.py',[(a,b),(a_scope,scope),('v22','v23')])
s=(O/'continue_native02.py').read_text();oldgate=s[s.index("  result=json.loads(core.read_text())"):s.index("  peer_path=")]
newgate="""  result=json.loads(core.read_text());assert result['status']=='PASS_V23_ADJACENT_HEADER_CONTROLS' and {k:result['pytest'][k]for k in ('passed','failed','skipped')}==dict(passed=35,failed=0,skipped=0)
  assert result['source_freeze']==pin(B/'source-freeze01.json') and result['source_peer']==pin(B/'source-only-peer-rx01.json')
"""
oldnext=s[s.index("next='")+6:s.index("')\n life.atomic",s.index("next='"))]
newnext='Owned same2GiB CPU6 freshmap, actual registeredboundary, literal-tieimport/fullpin graph and original4ns three-corner preplacement. Complete35actualcontrols/18case public and cyclemiter plus old accepted predecessor and cache fault/restart witness required. No PLLduplicate or acceptance relaxation.'
derive('continue_native02.py','continue_native01.py',[(oldgate,newgate),(oldnext,newnext),('v22','v23'),('V22','V23'),('source-freeze03.json','source-freeze01.json'),('46d599c89a5a19fee6e87dd9fbfa006a7d29f81922530256ab348685ea50e21c','446efb90f07eb3b2fe960498c55079afb385c3a89f8e2dad6dc02f028372b630'),('continuation-status02.json','continuation-status01.json'),('continuation-policy02.json','continuation-policy01.json'),('continuation-owner02.json','continuation-owner01.json'),('native-source-only-peer02.json','native-source-only-peer01.json'),('VALIDATED_MERGED_V23_CONTROLS_READY_NATIVE','VALIDATED_V23_CONTROLS_READY_NATIVE'),('PASS_SOURCE_ONLY_V23_MERGED_NATIVE_CONTINUATION','PASS_SOURCE_ONLY_V23_NATIVE_CONTINUATION'),('prove_balanced_import02.py','prove_balanced_import.py')])
# Explicitly enumerate the exact invoked paths; prevent the inherited suffix
# substitution dispatch failure from recurring. No invocation here.
controller=(B/'continue_native01.py').read_text()
import re
stagefiles=re.findall(r"stage\('[^']+',\[sys.executable,str\(B/'([^']+)'\)\]\)",controller)
assert stagefiles==['run_balanced_map02.py','measure_registered_boundary.py','balanced_import02.py','prove_balanced_import.py','balanced_preplacement02.py','review_timing.py','analyze_critical_path.py']
for p in stagefiles:assert (B/p).is_file()
(B/'native-controller-bridges-draft01.json').write_text(json.dumps(dict(bridges=ledger,exact_stage_paths={p:pin(B/p)for p in stagefiles},status='SOURCE_ONLY_NOT_LAUNCHED'),indent=2)+'\n')
print('Prepared exact seven-stage chain only; no native and no policy acceptance')
