# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve both source byte directions and pre-native contracts; not physical proof."""
from pathlib import Path
import hashlib,json,difflib,sys,ast
R=Path.cwd();B=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'hw/soc/flow'))
import make_pcie_clock_div4_v7 as m
import check_pcie_clock_div4_v7 as c

def pin(p):
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
pairs=[]
for stem in ('make','check'):
 old=R/f'hw/soc/flow/{stem}_pcie_clock_div4_v6.py';new=R/f'hw/soc/flow/{stem}_pcie_clock_div4_v7.py'
 a=old.read_text().splitlines(keepends=True);b=new.read_text().splitlines(keepends=True)
 ops=[]; forward=[]; inverse=[]
 for tag,a0,a1,b0,b1 in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
  x=''.join(a[a0:a1]);y=''.join(b[b0:b1]); ops.append(dict(tag=tag,before_lines=[a0,a1],after_lines=[b0,b1],before=x,after=y));forward.append(y);inverse.append(x)
 assert ''.join(forward).encode()==new.read_bytes() and ''.join(inverse).encode()==old.read_bytes()
 pairs.append(dict(before=dict(path=str(old.relative_to(R)),**pin(old)),after=dict(path=str(new.relative_to(R)),**pin(new)),opcodes=ops))
inputs=[R/'hw/soc/flow/make_pcie_clock_div4_v7.py',R/'hw/soc/flow/check_pcie_clock_div4_v7.py',R/'sw/tests/test_pcie_clock_div4_v7_layout.py']
freeze={str(p.relative_to(R)):pin(p) for p in inputs}
assert '42 passed' in (B/'source-controls04.log').read_text()
(B/'source-freeze03.json').write_text(json.dumps(freeze,indent=2)+'\n')
(B/'source-bridge03.json').write_text(json.dumps(dict(status='SOURCE_BIDIRECTIONAL_BYTE_BRIDGES_NOT_NATIVE_PROOF',pairs=pairs),indent=2)+'\n')
rows=m.devices(R); plan,starts,nets=m.placement_plan(rows)
physical=m.physical_reference(R)
assert len(rows)==73 and physical.count('ptap1 A=4p P=8u')==18
assert sum(r['kind']=='hbt' for r in rows)==34
assert all(n not in physical for n in ('VCO_AVDD','VCTRL','OSC__','NWELL','ntap1','sg13_hv_pmos'))
for fault in c.REFERENCE_FAULTS: assert c.fault_reference(physical,fault)!=physical
life=R/c.LIFECYCLE_SOURCE; assert pin(life)['sha256']==c.LIFECYCLE_SHA
ns=c.lifecycle()
selected=['Cancelled','process_identity','group_members','ProcessOwner'];tree=ast.parse(life.read_text())
(B/'predeclared-contract03.json').write_text(json.dumps(dict(status='SOURCE_ONLY_READY_FOR_INDEPENDENT_PEER_BEFORE_ANY_NATIVE',source_pins=freeze,
 predecessors=[q['before'] for q in pairs],actual_schematic_inputs={n:pin(R/n) for n in m.SOURCES},
 graph=rows,placement=plan,row_starts=starts,row_nets=nets,physical_reference_sha256=hashlib.sha256(physical.encode()).hexdigest(),
 census=dict(hbt=34,rppd=33,cmim=6,physical_ptap=18,physical_devices=91,expected_normalized_devices=74,contact_normalization='18 native parallel ptap1 square contacts combine to A72p P144u; actual native extraction must verify this and independent LVS; no blackbox'),
 ports=m.PORTS,port_directions={p:m.use_direction(p) for p in m.PORTS},
 tests={'controls':42,'pass':pin(B/'source-controls04.log'),'earlier39pass_rejected_for_terminal_gaps':pin(B/'source-controls02.log'),'peer_boundary_findings':pin(B/'source-peer-boundary-findings01.json'),'earlier_rejected':pin(B/'source-controls01.log'),'earlier_failure':'Passive multiplier negative initially passed this auxiliary census parser; now strict rppd/cap m=1 required. Full native LVS not run or changed.'},
 lifecycle=dict(path=str(life.relative_to(R)),**pin(life),selected_definitions=selected,selected_ast_sha256=hashlib.sha256(ast.dump(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in selected],type_ignores=[])).encode()).hexdigest(),cpu=10,address_space=2*1024**3,entry_free=c.ENTRY_FREE,shared_floor=c.SHARED_FLOOR,own_scratch=c.SCRATCH_LIMIT,launch_reservation=c.LAUNCH_RESERVATION,failure_grace=5,healthy_timeout=None),
 native_sequence=['owned native PCell generation','unchanged main560category DRC','actual offgrid DRC rejection','strict deep LVS','strict flat LVS',*c.REFERENCE_FAULTS,*c.PHYSICAL_FAULTS,'native LEF','missing real CLKP pin rejection','actual clock pin blockage rejection'],
 no_native_started=True,physical_acceptance=False,scope='Standalone current divider only; no oscillator/CMOSfeedback/composite clockbank, no wireRC or postlayout functional acceptance yet'),indent=2)+'\n')
print(json.dumps({'sources':freeze,'bridge':pin(B/'source-bridge03.json'),'contract':pin(B/'predeclared-contract03.json')}))
