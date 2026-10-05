# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent additive source peer of exact actual hierarchy correction."""
from pathlib import Path
from collections import Counter
import hashlib,json,datetime,ast
B=Path(__file__).resolve().parent;OLD=B.parent/'pcie-divider-v7-wire-v1-20261005'
def pin(p):
 with Path(p).open('rb') as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=B/'geometry-source-freeze.json';assert pin(f)==dict(bytes=8955,sha256='167ebd4d7e6eaf817cedd3b0cef89be5517cb3b681c35c48c32526c87121479e')
freeze=json.loads(f.read_text())
for p,h in freeze['inputs'].items():assert pin(p)==h,p
bridge=json.loads((B/'geometry-source-bridge.json').read_text());assert len(bridge)==7
for row in bridge:
 old,new=Path(row['before']['path']),Path(row['after']['path'])
 for k,p in [('before',old),('after',new)]:assert pin(p)=={key:row[k][key] for key in ('bytes','sha256')}
 assert ''.join(x['before'] for x in row['opcodes'])==old.read_text()
 assert ''.join(x['after'] for x in row['opcodes'])==new.read_text()
 s=new.read_text().replace('nssoc-div4-v7-wire-geometry-02','nssoc-div4-v7-wire-geometry-01')
 if new.name=='probe_native_cells.py':s=s.replace('assert len(rows)==678','assert len(rows)==91').replace('dict(npn13G2=34,rppd=33,cmim=6,ptap1=18,via_stack=587)','dict(npn13G2=34,rppd=33,cmim=6,ptap1=18)')
 if new.name=='probe_device_locations.py':s=s.replace("assert len(leaves)==91 and len(source)==678\nassert Counter(r['cell'].split('$')[0] for r in source)==dict(npn13G2=34,rppd=33,cmim=6,ptap1=18,via_stack=587)",'assert len(leaves)==len(source)==91')
 assert s==old.read_text(),new
 ast.parse(new.read_text())
rows=json.loads((OLD/'native-pcell-inventory-diagnostic.json').read_text())
assert len(rows)==678 and Counter(r['cell'].split('$')[0] for r in rows)==dict(npn13G2=34,rppd=33,cmim=6,ptap1=18,via_stack=587)
assert json.loads((OLD/'geometry-execution.json').read_text())['status']=='FAIL_GEOMETRY_RETAINED'
prior=OLD/'geometry-source-only-peer.json';assert json.loads(prior.read_text())['findings']==[]
result=dict(status='PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_GEOMETRY',findings=[],utc=datetime.datetime.now(datetime.UTC).isoformat(),method=pin(__file__),freeze=pin(f),source_pins=freeze['producer_sources'],all_input_pins_rehashed=len(freeze['inputs']),prior_source_peer=pin(prior),source_bridge=pin(B/'geometry-source-bridge.json'),full_seven_source_byte_inverse=True,actual_prior_hierarchy=pin(OLD/'native-pcell-inventory-diagnostic.json'),review=['All seven V2 bodies inverse exactly to reviewed V1 after only fresh wire geometry output02 and explicit678total/587via hierarchy correction. Same seven controlled native-reader steps, corrected checker lifecycle and original resource guards.','Actual saved diagnostic contains678 leaves, exactly34HBT+33rppd+6MIM+18ptap+587via_stack. Only electrical PCells are selected for91device enclosure; every residual leaf must be via_stack. No unknown-class suppression.','Metal/via geometry union is unchanged and recursively retains all587via stack shapes; no device, electrical terminal, resistance, graph quantity or check was removed.','Original actual native hierarchy assertion failure, diagnostic/source pins and prior source-only peer remain immutable. No prior failed run has been converted into pass. All geometry assertions still require fresh native output.'],native_executed=False,controls_rerun=False,rc_or_spice_executed=False,qualified_pex=False,main_chip_integrated=False)
with (B/'geometry-source-only-peer.json').open('x') as out:json.dump(result,out,indent=2);out.write('\n')
print(json.dumps(dict(path=str(B/'geometry-source-only-peer.json'),**pin(B/'geometry-source-only-peer.json'))))
