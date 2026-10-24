# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source and saved-control review, without EDA or test execution."""
from pathlib import Path
import ast,hashlib,json,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 with Path(p).open('rb') as f:return {'bytes':Path(p).stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
f=json.loads((B/'source-freeze01.json').read_text());assert pin(B/'source-freeze01.json')=={'bytes':6062,'sha256':'d665716f334fe276d85120ed8d1195af58eef7efca78e325dec1b7feb0fbd900'}
for section in ['sources','dependencies']:
 for p,h in f[section].items():assert pin(p)==h,p
for p,h in f['controls'].items():assert pin(B/p)==h,p
cases=list(ET.parse(B/'controls01.xml').getroot().iter('testcase'));assert len(cases)==52 and all(not any(c.find(x) is not None for x in ['failure','error','skipped']) for c in cases)
counts={}
for c in cases:counts[c.attrib.get('classname','')]=counts.get(c.attrib.get('classname',''),0)+1
assert sorted(counts.values())==[19,33]
old=R/'hw/soc/pcie-evidence/20261006-compact-rc-and-repair/records/pcie-gen3-transmit-v4-repair-20261005/owned_lifecycle05.py';assert old.read_bytes()==(R/'scripts/npu_physical_process.py').read_bytes()
run=(R/'scripts/run_npu_eco_physical.py').read_text();tree=ast.parse(run)
assert all(any(isinstance(n,ast.FunctionDef) and n.name==name for n in tree.body) for name in ['run','compare','execute','capture_methods','verify_bundle','preserve'])
assert 'physical.audit_check(root / \'capture\', root / \'capture\'' in run
r={'status':'FINDINGS_SOURCE_ONLY_MATCHED_NPU_PHYSICAL_RUNNER','freeze':pin(B/'source-freeze01.json'),'method':pin(__file__),'findings':[{'priority':2,'file':'scripts/run_npu_eco_physical.py','functions':['preserve','compare'],'title':'Preserve actual template geometry for independent saved comparison','body':'The initial run checks actual template versus final geometry, but only final GEOMETRY is captured. preserve excludes the template TSV/TXT files. compare calls audit_check(capture,capture), so saved evidence cannot independently re-establish that original pin/template relation. Preserve the actual template GEOMETRY inventory separately with exact pins, pass it as template_step in compare, and reject an actual copied-template pin geometry mutation.'}],'saved_controls':{'actual_cases':52,'counts_by_class':counts,'all_passed':True,'rerun':False},'process_helper_whole_byte_identity':{'path':str(old),**pin(old)},'reviewed_scope':['All three new source bodies plus exact old fresh_config/geometry_check/audit_check/capture_audit, readiness check/gate and resource/preexec functions read.','Native gate re-runs strict complete boot and mapped binary readiness before creating physicalwork; original failed boot/proof guards remain unchanged. Before/after runtime/bundle and source/method pins retained; returned record remains estimate-only.','Actual owned helper is byte-identical to reviewed TX05. SIGINT/TERM blocked across launch, unreaped leader anchors group identity, WNOWAIT detects exited leader with descendants, failure-only TERM/KILL cleanup avoids reaped-leader reuse. No healthy elapsed-time stop.','Resource function checks9GiBmemory/3GiBdisk at entry and before native; native per-process8GiBAS inherited. These are entry checks, not a claimed continuous9GiB memory reserve.','Comparison replays full strict boot evidence, actual endpoint/hold/constraints audits and matched config/method/runtime inputs; template capture/replay gap above remains blocking for independent geometry evidence.'],'native_or_tests_executed':False,'scope':'Source-only review and saved52-case XML/pin recount. No EDA, live boot assumption, timing acceptance or full-chip claim.'}
p=B/'source-only-peer-pll01.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(p))
