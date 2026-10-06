# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-only peer of fresh Cap24 wire-RC derivative; no producer imported."""
from pathlib import Path
import ast,hashlib,json,difflib
B=Path(__file__).resolve().parent;R=B.parents[3];OLD=B.parent/'pcie-divider-v7-compact-v2-wire-rc-v1-20261006';G=B.parent/'pcie-divider-v8-cap-v1-wire-v1-20261006'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
def load(p):return json.loads(Path(p).read_text())
f=load(B/'source-freeze.json');assert pin(B/'source-freeze.json')=={'bytes':566038,'sha256':'6bdeb7f399b489ca1b468e9048ec91a2f42e2c9e690c78fec3dca12453be1885'}
assert len(f['inputs'])==2541
for p,w in f['inputs'].items():assert pin(p)==w,p
for p,w in f['producer_sources'].items():assert pin(p)==w,p
bridges=load(B/'draft-source-bridge.json');assert len(bridges)==3
for x in bridges:
 p=Path(x['parent']);q=Path(x['new']);assert p.parent==OLD and q.parent==B and p.name==q.name
 assert pin(p)==x['parent_pin'] and pin(q)==x['new_pin']
 expected=p.read_text().replace('pcie-divider-v7-compact-v2-wire-v1-20261006','pcie-divider-v8-cap-v1-wire-v1-20261006').replace('nssoc-div4-v7-compact-v2-','nssoc-div4-v8-cap-v1-').replace('DIVIDER_V7_','DIVIDER_V8_CAP24_')
 assert expected==q.read_text(),q
 assert x['full_unified_diff']==''.join(difflib.unified_diff(p.read_text().splitlines(True),q.read_text().splitlines(True)))
 ast.parse(q.read_text())
oldpeer=load(OLD/'source-only-peer.json');assert oldpeer['findings']==[]
peer=load(G/'saved-geometry-peer.json');assert peer['status']=='PASS_DIVIDER_V8_CAP24_SAVED_GEOMETRY_AND_BINDING_CONTROLS' and peer['findings']==[]
assert peer['geometry_execution']==pin(G/'geometry-execution.json') and peer['binding_controls']==pin(G/'binding-controls01/result.json')
assert len(peer['actual_two_cap24_devices'])==2
run=(B/'run_native_rc.py').read_text();audit=(B/'audit_wire_rc.py').read_text();mut=(B/'check_native_mutations_v2.py').read_text()
for source in [B/'run_native_rc.py',B/'audit_wire_rc.py',B/'check_native_mutations_v2.py']:assert str(source) in f['inputs']
for p in [G/'saved-geometry-peer.json',G/'anchors.json',G/'terminal-reference-planes.json',R/'scripts/characterize_pcie_clock_trim_stream_v2.py',R/'hw/soc/flow/check_pcie_clock_div4_v7_v2.py']:
 assert str(p) in f['inputs']
assert not Path('/dev/shm/nssoc-div4-v8-cap-v1-wire-rc-01').exists() and not (B/'native-execution.json').exists()
out={'status':'PASS_SOURCE_ONLY_DIVIDER_V8_CAP24_WIRE_RC','freeze':pin(B/'source-freeze.json'),'findings':[],'method':pin(__file__),'full_three_body_inverse_checked':True,'full_source_and_runtime_pins_rehashed':len(f['inputs']),'parent_peer':pin(OLD/'source-only-peer.json'),'saved_geometry_peer':pin(G/'saved-geometry-peer.json'),'source_bridge':pin(B/'draft-source-bridge.json'),'review':['Read all three full methods and exact predecessor bodies. Changes only fresh geometry/native roots and declared Cap24 status labels. Same205 actual anchors/37wire components/85body dispositions and actual two24um caps gate bound.','Native Tcl AST selection and unchanged Magic/runtime are frozen; same CPU10,2GiB childAS,80MiBowned scratch,512MiBshared floor,terminal guard and existing tested ProcessOwner lifecycle. Fresh output/receipt/peer gates preserve duplicate prevention.','Strict auditor retains actual raw R topology/value multiset, every actualpointC and mutual attachment plus complete38x38 collapsed matrix. Original intrinsic aliases are ownership witnesses, never resistance graph edges.','All13 actual raw-corruption mechanisms and exact rejection diagnostics are byte-identical apart from native root: real bridge separates probes37to38components, actual mutual C deletion/change, cross-conductor short, missingport/completion, pointredistribution and body/anchor faults. No relaxed acceptance or original geometry mutation.'],'producer_imported':False,'native_or_controls_executed':False,'scope':'Bounded independent source/byte review only. No fresh RC extraction, PEXqualification, loadeddivide result, mainchip or fullPHY claim.'}
p=B/'source-only-peer.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(out['status'],pin(p))
