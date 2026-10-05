# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive final source/evidence peer; no source tests or native EDA execution."""
from pathlib import Path
import ast,datetime,hashlib,json
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def ast_equal(a,b):return ast.dump(ast.parse(a))==ast.dump(ast.parse(b))
freeze=B/'source-freeze03.json';pins=json.loads(freeze.read_text())
for name,p in pins.items():assert pin(R/name)==p
contract=json.loads((B/'predeclared-contract03.json').read_text());old=json.loads((B/'predeclared-contract.json').read_text())
assert contract['source_pins']==pins
for k in old:
 if k not in ('source_pins','tests'):assert old[k]==contract[k],k
for pair in json.loads((B/'source-bridge03.json').read_text())['pairs']:
 for side in ['before','after']:
  text=''.join(row[side] for row in pair['opcodes']);b=text.encode();p=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());assert p=={k:pair[side][k] for k in ['bytes','sha256']};assert pin(R/pair[side]['path'])==p;ast.parse(text)
initial=B/'source-candidate01-rejected';a=(initial/'hw/soc/flow/check_pcie_clock_div4_v7.py').read_text();b=(R/'hw/soc/flow/check_pcie_clock_div4_v7.py').read_text()
# Entire unchanged checker body: only execute replacement, new guard and one
# additional indirectly imported source pin are permitted after circuit peer.
def normalized(text,new):
 tree=ast.parse(text)
 tree.body=[n for n in tree.body if not(isinstance(n,ast.FunctionDef) and n.name in ('execute','guard_resources'))]
 if new:
  class StripPin(ast.NodeTransformer):
   def visit_List(self,node):
    self.generic_visit(node)
    node.elts=[x for x in node.elts if not(isinstance(x,ast.Constant) and x.value=='check_pcie_rx_cell.py')]
    return node
  tree=StripPin().visit(tree)
 return ast.dump(tree)
assert normalized(a,False)==normalized(b,True)
oldtest=(initial/'sw/tests/test_pcie_clock_div4_v7_layout.py').read_text();newtest=(R/'sw/tests/test_pcie_clock_div4_v7_layout.py').read_text();assert newtest.startswith(oldtest)
assert pin(B/'source-controls04.log')==contract['tests']['pass']
assert '42 passed' in (B/'source-controls04.log').read_text()
previous=B/'source-only-peer01-circuit-and-findings.json';assert pin(previous)==dict(bytes=3956,sha256='17a501b5daf50ab99be46e13ae7ead8f83422ef9005b591b601e26a78c0a7d54')
raw=B/'control-native04-members.json';manifest=json.loads(raw.read_text())
print('saved-control-manifest-schema',list(manifest))
launcher=B/'launch01.py';assert pin(launcher)==dict(bytes=3666,sha256='73ff0e03095722bf5281424d8bae3f6dc0d2d61ada1e6b97d5277fa18e069b87')
# The frozen author's manifest is inspected below according to its actual schema.
assert manifest['source_controls']==pin(B/'source-controls04.log')
for name,p in manifest['members'].items():
 assert pin(B/'control-native04'/name)==p
 source=Path(manifest['source_root'])/name
 if source.exists():assert pin(source)==p
owner_records={}
for name in manifest['members']:
 if not name.endswith('.owned.json'):continue
 d=json.loads((B/'control-native04'/name).read_text());assert d['elapsed_watchdog_seconds'] is None and d['failure_grace_seconds']==5.0
 assert all(x['status'] in ['REAPED_NO_LIVE_MEMBERS','FAILURE_REAPED'] for x in d['processes'])
 owner_records[name]=dict(status=d['status'],reason=d['reason'],child_statuses=[x['status'] for x in d['processes']])
assert len(owner_records)==6
report=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7',reviewer='/root/rx_route_resume',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),findings=[],source_pins=pins,launcher=pin(launcher),source_freeze=pin(freeze),source_bridge=pin(B/'source-bridge03.json'),predeclared_contract=pin(B/'predeclared-contract03.json'),previous_circuit_peer=dict(path=str(previous),**pin(previous)),method=pin(__file__),saved_control_evidence=dict(log=pin(B/'source-controls04.log'),pytest_controls=42,raw_manifest=pin(raw),files=len(manifest['members']),bytes=sum(p['bytes'] for p in manifest['members'].values()),all_copied_members_rehashed=True,owner_records=owner_records),resolved_findings=[dict(id='terminal_signal_loss',resolution='Owner checked immediately after complete and again after restored context; real complete-boundary and teardown-boundary SIGTERM tests now expect raised cancellation. Old failing source/receipt preserved.',raw_limitation='Teardown control injects SIGTERM after final healthy owner save, so the inner JSON correctly remains the preceding HEALTHY snapshot. The actual enclosing pytest exception assertion is the terminal outcome; source and full42-pass log bind it.'),dict(id='terminal_resource_guard',resolution='Same shared and own resource guards run both after native complete and after owner context. Actual child writes2MiB then exits against1MiB harness cap and is rejected; production80MiB ceiling and512MiB floor unchanged.')],checks=['Rehashed all final03 product sources. Reconstructed full v6/v7 before/after bytes from source bridge and checked current file hashes and valid syntax.','Entire prior reviewed graph/placement/ports/reference/census/native sequence/lifecycle contract unchanged. Exact73-device independent schematic expansion and18realptaps evidence remains valid because maker and all4schematic files are unchanged. Native74-device normalized census is a future fail-closed check, not an accepted physical result.','Whole checker AST apart from execute/guard and restored check_pcie_rx_cell.py input pin equals originally reviewed checker. Entire old test prefix preserved; only3 actual boundary controls appended. All29 saved control files freshly hashed.','CPU10,2GiB nativeAS,1GiB entry,512MiB live floor,80MiB scratch+24MiB launch reserve unchanged; no healthy elapsed timeout; lifecycle uses exact4 definitions from frozenProcessOwner. All native stages including generation receive owned groups.','Full launcher read: immutable input manifest rehash, exact peer status/no findings/productpin/selfpin gate, fresh direct /dev/shm roots, CPU10+1GiB, exclusive fsynced SSD PID/start/group checkpoint, samePID exec into checker, token/Python injection environment removed. No separate unmanaged supervisor.','Strict560main-rule DRC, independent deep/flat transistor LVS and8reference+6physical faults plus offgrid and LEF negatives remain required; all graph and geometry preconditions preserved. Restored indirect-import pin protects check_pcie_rx_cell source bytes.'],launcher_manifest_scope='Final launch manifest is intentionally constructed after this receipt to bind its exact bytes; launcher rehashes every declared input before exec. This source review neither constructs nor executes that manifest. Actual identity and runtime/input census must be retained at launch.',native_eda_executed=False,tests_rerun=False,physical_acceptance=False,qualified_pex=False,scope='Independent source and saved control evidence review only. No native generation/DRC/LVS/LEF claim, no extracted division, qualified PEX, PLL/chip integration or manufacturing approval. Earlier rejected candidate and failed evidence remain unchanged.')
p=B/'source-only-peer03-rx.json';assert not p.exists();p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
