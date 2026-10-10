# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source-only geometry peer; never imports reviewed producers."""
import ast
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path

B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
freeze_path=B/'geometry-source-freeze.json'
assert pin(freeze_path)==dict(bytes=7682,sha256='50f2a8f62902994c007660175b883010f18baff51eb2354814876cc1610d233d')
freeze=json.loads(freeze_path.read_text())
for path,expected in freeze['inputs'].items():assert pin(path)==expected,path
bridge=json.loads((B/'geometry-source-bridge.json').read_text())
assert len(bridge)==6
bridges=[]
for row in bridge:
 old,new=Path(row['before']['path']),Path(row['after']['path'])
 assert pin(old)=={k:row['before'][k] for k in ('bytes','sha256')}
 assert pin(new)=={k:row['after'][k] for k in ('bytes','sha256')}
 assert ''.join(op['before'] for op in row['opcodes'])==old.read_text()
 assert ''.join(op['after'] for op in row['opcodes'])==new.read_text()
 assert all(op['before']==op['after'] for op in row['opcodes'] if op['tag']=='equal')
 ast.parse(new.read_text())
 bridges.append(dict(before=row['before'],after=row['after'],full_forward_inverse=True))
runner=ast.parse((B/'run_geometry.py').read_text())
checker=Path('hw/soc/flow/check_pcie_clock_div4_v7_v2.py')
expected={'require','atomic','lifecycle','limits','scratch_bytes','guard_resources','execute'}
functions={n.name:n for n in ast.parse(checker.read_text()).body if isinstance(n,ast.FunctionDef)}
assert expected<=functions.keys()
# All child work is executed through private exact checker AST definitions.
runner_text=(B/'run_geometry.py').read_text()
selected_names=[ast.literal_eval(n.value) for n in ast.walk(runner) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='names' for t in n.targets)]
assert selected_names==[expected]
assert "execution = ns['execute']([A, 'python', B / (name + '.py')], B, name)" in runner_text
assert "assert execution['returncode'] == 0, name" in runner_text
assert "assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}" in runner_text
assert "ns['guard_resources']()" in runner_text
# Independent finite source graph/terminal declaration, no geometry execution.
g=json.loads(Path('/dev/shm/nssoc-div4-v7-layout-01/result.json').read_text())
counts=Counter(x['kind'] for x in g['instances'])
assert counts==dict(hbt=34,resistor=33,capacitor=6,substrate_tap=18)
assert len(g['instances'])==91 and len({x['name'] for x in g['instances']})==91
nets=set()
for d in g['instances']:
 n=list(d['nets'])
 if d['kind'] in ('hbt','resistor'):n[-1]='BULK'
 nets.update(n)
assert len(nets)==38 and 'SUB' in nets and 'BULK' in nets
assert len(g['ports'])==7
assert 34*4+33*3+6*2+18*2==283
assert 34+33+18==85 and 283-85==198 and 198+7==205
result=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_GEOMETRY',findings=[],utc=datetime.datetime.now(datetime.UTC).isoformat(),method=pin(__file__),freeze=pin(freeze_path),source_pins=freeze['producer_sources'],all_input_pins_rehashed=len(freeze['inputs']),full_byte_bridges=bridges,review=[
 'Read all seven producer bodies and source derivation; full six VCO-to-divider bodies reconstructed in both directions against exact old/new pins.',
 'Native census expectations 91 physical devices,283 terminals,198 metal terminals,85 body terminals,205 anchors and38 named nets independently checked from the frozen source graph; 37 actual metal components is a native assertion yet to execute.',
 'Every nonempty M1-through-TopMetal2/via region is copied and XOR checked. Empty TopMetal2/TopVia2 are explicitly inventoried/asserted, never silently dropped. Per-wire ownership uses native interior geometry, region containment, unique component per native metal net and complete coverage.',
 'Unsimplified native graph keeps all18 individual finite ptaps. Each native device is uniquely enclosed by an actual matching PCell; source placement transform, model, all native parameter keys/values and complete named-net bijection must pass. BULK is distinct from SUB; no substrate spreading resistor or intrinsic body terminal is deleted or claimed modeled.',
 'Terminal reference planes use actual PCell pin/access geometry plus native-net containment and one wire-component owner. All198 metal accesses must resolve. Seven public pin rectangles/labels/net names are checked. Intrinsic point references remain explicitly undistributed and unqualified.',
 'run_geometry privately compiles the exact seven pinned corrected checker functions. Each real child group is CPU10/2GiB, core0,1GiB entry,512MiB shared floor,80MiB own ceiling+24MiB launch reserve; post-complete and post-context signal/resource checks retained. No healthy elapsed deadline. Every stage exit/source pin is gated; failure is retained.',
 'Runtime restoration source reviewed as separate source-only utility: full403-member pin map,398 owned-prefix allowlist, path/symlink checks, exact existing bytes and exclusive writes; it is not called by geometry production.'
 ],native_or_reviewed_method_executed=False,controls_rerun=False,geometry_results_claimed=False,qualified_pex=False,main_chip_integrated=False,scope='Source-only review permits finite saved-layout geometry reading. No measured geometry, RC, device-extracted division, standalone clockbank or full PHY acceptance is inferred.')
with (B/'geometry-source-only-peer.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(path=str(B/'geometry-source-only-peer.json'),**pin(B/'geometry-source-only-peer.json'))))
