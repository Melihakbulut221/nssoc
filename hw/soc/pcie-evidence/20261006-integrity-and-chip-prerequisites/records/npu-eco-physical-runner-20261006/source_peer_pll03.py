# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent final source/diff and saved control recount; no EDA/tests."""
from pathlib import Path
import ast, hashlib, json, xml.etree.ElementTree as ET
R=Path.cwd(); B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def funcs(text):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
f=json.loads((B/'source-freeze03.json').read_text())
assert pin(B/'source-freeze03.json')=={'bytes':6677,'sha256':'81cd1ac90fd7806fcc61ab706d6dd51d2c138da1e19d4d04a7f6b440db622e5e'}
for section in ('sources','dependencies'):
 for p,h in f[section].items():assert pin(p)==h,p
for p,h in f['controls'].items():assert pin(B/p)==h,p
old=json.loads((B/'source-freeze01.json').read_text())
for name,p in [('run_npu_eco_physical.py','runner-source01.py'),('npu_physical_process.py','process-source01.py'),('test_npu_eco_physical.py','tests-source01.py')]:
 original=next(h for path,h in old['sources'].items() if path.endswith('/'+name));assert pin(B/p)==original
current=(R/'scripts/run_npu_eco_physical.py').read_text(); prior=(B/'runner-source01.py').read_text()
a,b=funcs(prior),funcs(current)
changed=[k for k in a if a[k]!=b[k]]
assert changed==['execute','preserve','run','compare'],changed
assert set(b)-set(a)=={'capture_template','verify_saved_geometry'}
tests0=funcs((B/'tests-source01.py').read_text());tests1=funcs((R/'sw/tests/test_npu_eco_physical.py').read_text())
assert all(tests1[k]==v for k,v in tests0.items())
assert set(tests1)-set(tests0)=={'test_interruption_between_spawn_and_assignment_cleans_exact_child','test_saved_template_is_independent_of_final_geometry'}
assert (B/'process-source01.py').read_bytes()==(R/'scripts/npu_physical_process.py').read_bytes()
ancestor=R/'hw/soc/pcie-evidence/20261006-compact-rc-and-repair/records/pcie-gen3-transmit-v4-repair-20261005/owned_lifecycle05.py'
assert ancestor.read_bytes()==(R/'scripts/npu_physical_process.py').read_bytes()
cases=list(ET.parse(B/'controls03.xml').getroot().iter('testcase'))
assert len(cases)==57 and all(not any(c.find(k)is not None for k in ('error','failure','skipped')) for c in cases)
counts={}
for c in cases:counts[c.attrib.get('classname','')]=counts.get(c.attrib.get('classname',''),0)+1
assert sorted(counts.values())==[24,33],counts
names=[c.attrib['name'] for c in cases]
assert 'test_interruption_between_spawn_and_assignment_cleans_exact_child' in names
assert len([n for n in names if n.startswith('test_saved_template_is_independent_of_final_geometry[')])==4
assert (B/'ruff03.log').read_text().strip()=='All checks passed!'
finding=json.loads((B/'source-only-peer-pll01.json').read_text());assert len(finding['findings'])==1
r={'status':'PASS_SOURCE_ONLY_MATCHED_NPU_PHYSICAL_RUNNER','freeze':pin(B/'source-freeze03.json'),'method':pin(__file__),'sources':f['sources'],'prior_finding':pin(B/'source-only-peer-pll01.json'),'findings':[], 'saved_controls':{'actual_cases':57,'counts_by_class':counts,'all_passed':True,'rerun':False,'xml':pin(B/'controls03.xml'),'log':pin(B/'controls03.log'),'ruff':pin(B/'ruff03.log')},'exact_diff_checks':{'changed_functions':changed,'new_functions':sorted(set(b)-set(a)),'all_prior_test_functions_AST_unchanged':True,'process_helper_whole_byte_identity':{'path':str(ancestor),**pin(ancestor)}}, 'reviewed_corrections':['Template GEOMETRY is independently captured and hashed at the actual template stage, including available partial files during failure preservation. Missing inventory fails verification; template and final are parsed separately and byte pins compared. Saved comparison calls audit_check(final,template), not final twice. Three actual template-only corruption cases and positive control are present and saved PASS.','SIGINT/TERM remain blocked through caller child assignment. Inner helper restores its blocked entry mask and then supplied child_setup restores the actual original mask before native limits. Pending signal reaches caller only after owned handle assignment; outer exception cleans the exact unreaped owned group. Actual injected SIGTERM between spawn and assignment is saved PASS with child absent and handlers restored.','Complete runner and test diffs reread; only four declared functions changed, two geometry helpers added, and all prior test function ASTs are unchanged. Original source01 and initial52-case evidence/finding remain retained.'], 'continuing_scope':['Strict readiness reruns full boot/source/mapping evidence before physical work; exact original/factored input,28firmwarechecks34321binaryequations and full source bundle/runtime pins remain required. This review does not assert boot or native physical completion.','Same20ns,32fixedSRAM,301physical signal boxes, matched original config and all existing raw timing/geometry audit methods remain unchanged. Compare reparses raw audit and strict readiness; returned results remain global-route estimates without adoption, final timing or manufacturing acceptance.','Owned helper is byte-identical to reviewed TX05. WNOWAIT retains leader through group cleanup; no healthy elapsed timeout. Memory9GiB/disk3GiB are launch entry checks, native8GiBAS, not a claimed continuous9GiB reserve.'], 'native_or_tests_executed_by_peer':False}
p=B/'source-only-peer-pll03.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(p))
