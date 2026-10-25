# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""V17 explicit leaf-event source-only review; no simulation or native mapping."""
from pathlib import Path
import ast,datetime,hashlib,json,re,runpy
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
freeze=B/'source-freeze.json';assert pin(freeze)==dict(bytes=2299,sha256='48a78275df28c51417f5e318750ccc77d933ccf34fd7188cdc3158445e101dcd')
f=json.loads(freeze.read_text())
for p,v in f['files'].items():assert pin(R/p)==v
prev=R/'hw/soc/out/pcie-integrity-v16-20261005';assert pin(prev/'source-freeze.json')==f['predecessor']
pf=json.loads((prev/'source-freeze.json').read_text())
for p,v in pf['files'].items():assert pin(R/p)==v
G=runpy.run_path(str(R/'scripts/generate_pcie_integrity_read_v17.py'));P=runpy.run_path(str(R/'scripts/generate_pcie_integrity_read_v16.py'))
assert G['FIELDS']==P['FIELDS']==dict(data=32,keep=4,sop=4,eop=4,dllp=4,sequence=12)
rtl=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v17.v';text=rtl.read_text();body=G['balanced_read']();assert G['candidate']()==text and text.count(body)==1
assert text.replace(body,G['original_read']()).replace('integrity_v17','integrity_v11')==G['SOURCE'].read_text()
assert pin(G['SOURCE'])==f['baseline']
expected=['read_address','slot_data[read_slot]','slot_keep[read_slot]','slot_sop[read_slot]','slot_eop[read_slot]','slot_dllp[read_slot]','slot_sequence[read_slot]','slot_verdict[read_slot]']
header=re.search(r'always @\((.*?)\) begin',body).group(1);assert header.split(' or ')==expected
leaf=body.split('always @('+header+') begin',1)[1].split('assign read_eligible_tree[RING_DWORDS+read_slot]',1)[0]
read_fields=set(re.findall(r'slot_\w+\[read_slot\]',leaf));assert read_fields==set(expected)-{'read_address'}
assert 'if(read_address==read_slot' in leaf
restored=body.replace('V17','V16').replace('     // Every leaf reads only this constant word. Explicit event terms avoid\n     // implicit whole-array sensitivity expansion; all read fields are listed.\n','').replace('always @('+header+')','always @*')
assert restored==P['balanced_read']()
# Every inherited source is an exact version bridge except new generator/RTL
# and appended isolated-event tests. No writer/parser/commit or test changes hide.
for n,v in f['files'].items():
 prior=n.replace('_v17','_v16');current=(R/n).read_text();baseline=(R/prior).read_text()
 if n.endswith('test_pcie_gen3_integrity_v17_read.py'):
  inherited=current[:current.index('\nEVENTS = ')].replace('_v17','_v16');assert inherited.rstrip()==baseline.rstrip()
 elif n not in ['scripts/generate_pcie_integrity_read_v17.py','hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v17.v']:
  assert current.replace('_v17','_v16')==baseline
oldpeer=prev/'source-only-peer-rx.json';assert pin(oldpeer)==dict(bytes=4364,sha256='cdeb51278874bb0a6414f71386cd138d4cfc78ed02d9ac307211c0ff583d2e36')
result=dict(status='PASS_V17_EXPLICIT_CONSTANT_WORD_SENSITIVITY_SOURCE_ONLY_PEER',utc=datetime.datetime.now(datetime.UTC).isoformat(),reviewer='/root/rx_route_resume',findings=[],source_freeze=pin(freeze),source_pins=f['files'],method=pin(__file__),inherited_v16_source_peer=dict(path=str(oldpeer),**pin(oldpeer)),events=expected,checks=['Rehashed all9 V17 and all9 inheritedV16 source pins. GeneratedV17 equals checked-in RTL; exact fullV11 inverse restores all writers/control/parser/fault/pointers/commit logic.','After only comments/version and explicit leaf event-list normalization, complete read block is byte-identical to independently reviewed staticV16 tree. All wrappers/checkers/miter/directcontrols remain exact version bridges; readtest retains entire V16 prefix and adds only isolated-event controls.','Independently enumerated actual leaf RHS dependencies: read_address plus exactly six60bit payload fields and verdict. Keep is both qualifier and returned field and is listed once. Constant genvarread_slot itself never changes and requires no event; read_address captures read_ptr+constantlane changes. No leaf input is omitted.','Outer visible-output count gate remains separate always@*: committed/count changes can reveal previously cached leaf outputs; leaf still listens to payload/verdict/keep while hidden. Unknown address/keep/verdict continues procedural not-true masking and selected X/Z payload still propagates through muxes, not OR.','New realHDL sensitivity harness compares original V11 literal dynamic read with candidate at31 sequential checks: sixfields independently changed through known/X/Z values, isolated verdict/keep disable/re-enable with hidden writes, address/unknownaddress, committed0 hiddenwrite/committed4. Full243bit vector compared with four-state case inequality.','Nine actual source mutants remove each of8event terms or watch wrong dataword; each runs changed Verilog and requires native simulation mismatch, not textual rejection. Independent scalar input changes make missing dependency observable; pure source peer did not execute them.','V16 actual long compilation/incompletion remains separate and unchanged. Existing default150/fullmiter and literal16/64/128 requirements remain; MAX4118 cases are still separate, and mapped depth/2GiBnative/original4ns timing must be measured.'],simulations_rerun=False,native_executed=False,physical_acceptance=False,scope='Complete source and event-dependency review only. No timing, synthesis-memory improvement, native tree depth or full suite completion claimed here. Existing diagnostic compile/simulation and currently running inherited suite remain their own evidence.')
p=B/'source-only-peer-rx.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p))))
