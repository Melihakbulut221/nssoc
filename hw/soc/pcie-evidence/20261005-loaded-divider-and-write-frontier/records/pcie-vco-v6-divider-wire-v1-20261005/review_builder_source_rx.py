# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure source and existing-input review; never execute model builder or native tool."""
from pathlib import Path
import ast,collections,hashlib,json,re
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
plan=read(B/'source-plan.json');bridge=read(B/'divider-builder-source-bridge.json')
for path,value in plan['inputs'].items():assert pin(path)==value,path
for path,value in bridge['native_inputs'].items():assert pin(path)==value,path
before=Path(bridge['parent']['path']);after=Path(bridge['new']['path']);assert pin(before)=={k:bridge['parent'][k] for k in ['bytes','sha256']};assert pin(after)=={k:bridge['new'][k] for k in ['bytes','sha256']}
s=before.read_text()
for change in bridge['operations']:
 assert s.count(change['old'])==change['count'];s=s.replace(change['old'],change['new'])
assert s==after.read_text()
for change in reversed(bridge['operations']):
 assert s.count(change['new'])==change['count'];s=s.replace(change['new'],change['old'])
assert s==before.read_text()
def literal(text,name):
 n=next(x for x in ast.parse(text).body if isinstance(x,ast.Assign) and any(isinstance(y,ast.Name) and y.id==name for y in x.targets));return ast.literal_eval(n.value)
assert literal(after.read_text(),'MODEL_PINS')==literal(before.read_text(),'MODEL_PINS')
assert literal(after.read_text(),'NATIVE_ORDER')==literal(before.read_text(),'NATIVE_ORDER')
census=literal(after.read_text(),'CENSUS');assert census=={'npn13G2':34,'rppd':33,'cap_cmim':6,'ptap1':18}
paths={Path(path).name:Path(path) for path in plan['inputs']}
anchors=read(paths['anchors.json']);devices=read(paths['device-location-geometry.json'])['devices'];geometry=read(paths['wire-component-geometry.json'])
assert collections.Counter(d['model'] for d in devices)==census
assert [d['native_id'] for d in devices]==list(range(1,92))
assert sum(len(d['terminals']) for d in devices)==283
assert len(anchors['anchors'])==205 and len(anchors['unmodeled_body_well_terminals'])==85
assert collections.Counter(x['native_cluster'] for x in anchors['unmodeled_body_well_terminals'])=={1:85}
assert len(geometry['wire_components'])==37
assert collections.Counter(x['kind'] for x in anchors['anchors'])=={'INTRINSIC_DEVICE_TERMINAL_REFERENCE':198,'PUBLIC_PORT_REFERENCE':7}
records=[]
for line in paths['wires.spice'].read_text().splitlines():
 line=line.strip()
 if line and line[0] in 'RC':records.append(line.split())
assert collections.Counter(r[0][0] for r in records)=={'R':312,'C':618}
assert len({r[0].lower() for r in records})==930 and all(len(r)==4 and r[1]!=r[2] for r in records)
# Input geometry uses the two explicitly allowed floating serializations; the
# conversion map is exact keyed matching, not tolerance or rounding.
values=[str(v) for d in devices for v in d['parameters'].values()]
assert '38.400000000000006' in values and '12.700000000000001' in values
body=after.read_text();assert '"38.400000000000006": "38.4"' in body and '"12.700000000000001": "12.7"' in body
assert 'ports = sorted(public.values()) + ["BODY_SUBSTRATE", "WIRE_CREF"]' in body
assert 'witness["native_cluster"] == 1' in body and 'net = "BODY_SUBSTRATE"' in body
assert 'finite_contacts=18' in body and 'full_pex_qualified=False' in body
r=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_HYBRID_BUILDER',findings=[],source=bridge['new'],parent=bridge['parent'],source_plan=pin(B/'source-plan.json'),bridge=pin(B/'divider-builder-source-bridge.json'),method=pin(__file__),all13_plan_inputs_rehashed=True,whole_source_forward_inverse_verified=True,existing_input_census=dict(intrinsics=91,HBT=34,rppd=33,MIM=6,finite_taps=18,terminals=283,metal_anchors=198,body_terminals=85,anchors=205,wire_components=37,wire_R=312,wire_C=618,public_ports=7),review=['Full18,858-byte builder read and exact allowlisted whole-source inverse verified. Model-file pins, named terminal order, finite contact equation, strict native parameters, all-wire copying and generated statement verifier are inherited unchanged.', 'New finite dimensions match independently counted saved native geometry and wire text:91intrinsics/205anchors/283namedterminals; all18actual PTAPs remain finite devices. Only actual bodycluster1 is permitted and all85body terminal identities retained.', 'All37resistor components and930native R/C records are preserved. Wire capacitive reference and intrinsic body remain distinct explicit ports; no inferred body-metal merge, ideal clock, device replacement or PEX/signoff claim.', 'Exactly two pinned JSON float-spelling corrections are accepted. No numerical tolerance or generic rounding is introduced; raw native geometry/model/parameter census remains strict.', 'This source peer covers the standalone builder only. It does not execute generation, new composition, model mutation tests,455-device screening, loaded transient, qualifiedRC or main-chip integration. Those remain separate required measured gates.'],new_model_generation_executed=False,new_native_or_simulation_executed=False,qualified_PEX=False,main_chip_integrated=False)
p=B/'builder-source-only-peer-rx.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(p))
