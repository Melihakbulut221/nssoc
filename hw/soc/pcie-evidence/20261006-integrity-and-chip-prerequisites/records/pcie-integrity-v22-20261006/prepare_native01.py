"""Generate whole-body bridges to the already checked native resource lifecycle."""
from pathlib import Path
import json,hashlib
R=Path.cwd();B=Path(__file__).resolve().parent;O=B.parent/'pcie-integrity-v21-20261005';ledger=[]
def pin(p):
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def write(old,new,edits):
 p=O/old;s=p.read_text();steps=[]
 for a,b in edits:
  n=s.count(a);assert n,(old,a);s=s.replace(a,b);steps.append(dict(before=a,after=b,count=n))
 q=B/new;assert not q.exists();q.write_text(s);ledger.append(dict(parent=str(p),parent_pin=pin(p),path=str(q),pin=pin(q),replacements=steps))
common=[('v21','v22'),('V21','V22'),('pcie-integrity-v22-20261005','pcie-integrity-v22-20261006')]
for name in ['balanced_import.py','balanced_preplacement.py','prove_balanced_import.py','review_timing.py','analyze_critical_path.py']:
 edits=[(a,b)for a,b in common if a in (O/name).read_text() or a=='pcie-integrity-v22-20261005'and'pcie-integrity-v21-20261005'in(O/name).read_text()]
 write(name,name,edits)
write('measure_registered_boundary03.py','measure_registered_boundary.py',[('v21','v22')])
old=(O/'run_balanced_map.py').read_text();a=old[old.index('FREEZE='):old.index('assert shutil.disk_usage')]
b="""FREEZE=R/'hw/soc/out/pcie-integrity-v22-20261006/source-freeze03.json'
assert pin(FREEZE)['sha256']=='46d599c89a5a19fee6e87dd9fbfa006a7d29f81922530256ab348685ea50e21c'
for name,value in json.loads(FREEZE.read_text())['sources'].items():assert pin(R/name)==value
CORE=FREEZE.parent/'pcie-integrity-v22-controls-validation-20261006.json'
validation=json.loads(CORE.read_text())
assert validation['status']=='PASS_V22_CACHE_QUARANTINE_COMPOSITE_CONTROLS'
assert validation['pytest_executions']==38 and validation['pytest_passed_executions']==35 and validation['historical_failed_executions']==3
assert validation['source_freeze']==pin(FREEZE) and validation['public_positive_composite']==dict(original_unchanged_cases=16,targeted_corrected_case=1,complete_direct_profile_rerun=False,complete_cycle_miter_cases=17)
assert validation['actual_cache_witness']==dict(epochs=8,fault_steps=8,invalid_cache_changes=8)and len(validation['meaningful_miter_mutants'])==6
PEER=FREEZE.parent/'source-only-peer-vco03.json';assert pin(PEER)==validation['source_peer']
assert not json.loads(PEER.read_text())['findings']
CONTROL_RECEIPTS=[Path(row['path'])for row in validation['xml_recount']]
for p,row in zip(CONTROL_RECEIPTS,validation['xml_recount']):assert pin(p)=={k:row[k]for k in ['bytes','sha256']}
"""
write('run_balanced_map.py','run_balanced_map.py',[(a,b),('v21','v22'),('V21 registered retirement from frozen V17; explicit one-cycle added output latency. Exact source inverse, descriptor literal, transaction oracle and restricted nominal latency gates required.','V22 cache fault-write qualification from frozen V21; same registered retirement and public latency. Exact inverse, literal4096, cycle-exact17case miter and eight actual cache fault/reuse epochs required.')])
# Normal map continuation, not any saved-map recovery.
s=(O/'continue_native02.py').read_text()
oldnext=s[s.index("next='")+6:s.index("')\n life.atomic",s.index("next='"))]
newnext='Owned same2GiB CPU6 freshmap, actual registeredboundary, literal-tieimport/fullpin graph and original4ns three-corner preplacement. Actual38testexecutions35PASS3historicalFAIL; corrected17case miter, eight invalidcachewriteepochs and sixmeaningfulmutants. No PLLduplicate or acceptance relaxation.'
edits=common[:2]+[
 ('source-freeze04.json','source-freeze03.json'),('48be11f969876f9738a70f993e31eea6ff63a425a3b26227dfcdc2e55a33d6df','46d599c89a5a19fee6e87dd9fbfa006a7d29f81922530256ab348685ea50e21c'),
 ('continuation-status02.json','continuation-status01.json'),('continuation-policy02.json','continuation-policy01.json'),('continuation-owner02.json','continuation-owner01.json'),
 ('native-source-only-peer02.json','native-source-only-peer01.json'),('source-only-peer-rx04.json','source-only-peer-vco03.json'),('measure_registered_boundary02.py','measure_registered_boundary.py'),
 ('PASS_REGISTERED_RETIRE_COMPOSITE_PUBLIC_AND_LITERAL_CONTROLS','PASS_V22_CACHE_QUARANTINE_COMPOSITE_CONTROLS'),("result['historical_failed_executions']==1 and result['pytest_passed_executions']==32","result['historical_failed_executions']==3 and result['pytest_passed_executions']==35"),
 (oldnext,newnext)]
write('continue_native02.py','continue_native01.py',edits)
# All lifecycle function ASTs remain exact, except status-filename field in save.
ledgerpath=B/'native-source-bridges01.json';ledgerpath.write_text(json.dumps(ledger,indent=2)+'\n')
f=json.loads((B/'source-freeze03.json').read_text());v=B/'pcie-integrity-v22-controls-validation-20261006.json';validation=json.loads(v.read_text())
methods=[B/x['path'].split('/')[-1]for x in ledger]+[ledgerpath,B/'seal_controls03.py',B/'source-freeze03.json',B/'source-only-peer-vco03.json',B/'source-only-peer-vco02.json',v,R/'scripts/characterize_pcie_clock_trim_stream_v2.py']
p=dict(status='FROZEN_V22_NATIVE_POLICY_PEER_REQUIRED',method_pins={str(x):pin(x)for x in methods},source_pins=f['sources'],controls=dict(validation=dict(path=str(v),**pin(v)),archive=validation['archive']),PLL=dict(status='COMPLETED159PART_REPLAY_FAILED_RAW_PHASE_PAIR_RETAINED_NEW_TMAX_PREPARING',path=str(B.parent/'pcie-pll-acquisition-v3-20261005/numerical-convergence-plan01/launch01')),profile=dict(cpu=6,RLIMIT_AS=2*1024**3,clock_period_ns=4,max_packet_bytes=150,ring=64,healthy_timeout=None),scope='V22 only invalidcachewriterfaultqualification. Same V21 registeredboundary actualQ/D guards and fullpin graph. Exact originalbalancedABC/4nsPDKprofile; preplacement evidence only, not route/foundry/fullPHYsignoff.')
policy=B/'continuation-policy01.json';policy.write_text(json.dumps(p,indent=2)+'\n')
s=(O/'detach_native02.py').read_text()
for a,b in common+[('continuation-policy02.json','continuation-policy01.json'),('native-source-only-peer02.json','native-source-only-peer01.json'),('continuation-status02.json','continuation-status01.json'),('detached-native02','detached-native01'),('continue_native02.py','continue_native01.py')]:s=s.replace(a,b)
s=s.replace("{'bytes': 7537, 'sha256': '688adf4334d92975f11255ea8a0219456ba970e8304e89bb660b8a3ff2234faa'}",repr(pin(policy)))
(B/'detach_native01.py').write_text(s)
print(pin(policy),pin(B/'detach_native01.py'))
