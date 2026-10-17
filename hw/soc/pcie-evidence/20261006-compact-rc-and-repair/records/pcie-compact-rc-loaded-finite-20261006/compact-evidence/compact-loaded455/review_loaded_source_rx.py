# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import ast,gzip,hashlib,json
B=Path(__file__).resolve().parent;R=Path.cwd()
def pin(p):
 p=Path(p);return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
fpath=B/'source-freeze01.json';f=json.loads(fpath.read_text());assert pin(fpath)==dict(bytes=46745,sha256='5f06ac298985dead231d75d9f0ee62d0002cfe17362d30c9746f5867143863c6')
assert f['pins']=={p:pin(p)for p in f['pins']}
assert f['new_sources']=={p:pin(R/p)for p in f['new_sources']}
bridges=[]
for n in ('characterizer-source-bridge.json','launcher-source-bridge.json'):
 for b in json.loads((B/n).read_text()):
  a=Path(b['before']['path']).read_text();z=Path(b['after']['path']).read_text()
  assert a==''.join(x['before']for x in b['opcodes']) and z==''.join(x['after']for x in b['opcodes'])
  bridges.append(dict(before=b['before'],after=b['after']))
a=(R/'scripts/characterize_pcie_vco_v6_divider_power_v2_wire_v1.py').read_text();z=(R/'scripts/characterize_pcie_vco_v6_divider_compact_v2_wire_v1.py').read_text()
# Reviewed complete diff: symbols/fixtures, measured wire count and owned scratch namespace only.
fun=lambda s:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
fa,fz=fun(a),fun(z);assert fa.keys()==fz.keys();changed=[k for k in fa if fa[k]!=fz[k]];assert set(changed)=={'topology','config','guard'}
assert all(fa[k]==fz[k]for k in ('Meter','deck','run_native','run'))
# Exact test reproduction preserves all25 semantic/lifecycle controls.
ta=(R/'sw/tests/test_pcie_vco_v6_divider_power_v2_wire_v1.py').read_text();tz=(R/'sw/tests/test_pcie_vco_v6_divider_compact_v2_wire_v1.py').read_text()
assert ta.replace('characterize_pcie_vco_v6_divider_power_v2_wire_v1','characterize_pcie_vco_v6_divider_compact_v2_wire_v1').replace("c['wire_resistors']==1273 and c['wire_capacitors']==1422","c['wire_resistors']==1271 and c['wire_capacitors']==1414")==tz
assert f['controls']['passed']==25 and f['controls']['returncode']==0
assert f['actual_handoff_controls']['passed']==4 and f['actual_handoff_controls']['returncode']==0
fixtures=R/'sw/tests/fixtures/pcie_clock_div4_v7_compact_v2_hybrid_v1'
assert (fixtures/'hybrid-open.spice').read_bytes()==(B/'composed01/hybrid-open.spice').read_bytes()
assert (fixtures/'composition.json').read_bytes()==(B/'composed01/composition.json').read_bytes()
for p in (fixtures/'inputs').glob('*.gz'):
 raw=gzip.decompress(p.read_bytes());assert raw and p.with_name(p.name+'.license').exists()
 bf=json.loads((B/'builder-source-freeze.json').read_text());target=next(Path(x) for x in bf['native_input_files'].values() if Path(x).name==p.name.removesuffix('.gz'));assert raw==target.read_bytes()
# All source/data pins include saved RC peer, initial failed census controls and actual lifecycle raw captures.
rc=next(p for p in f['pins']if p.endswith('/saved-rc-peer-pll.json'));assert json.loads(Path(rc).read_text())['findings']==[]
assert not Path('/dev/shm/nssoc-vco-v6-divider-compact-v2-wire-06-01').exists()
r=dict(status='PASS_SOURCE_ONLY_LOADED455_WIRE_MODEL',freeze=pin(fpath),findings=[],review_method=pin(__file__),verified_pins=len(f['pins']),new_product_sources=len(f['new_sources']),whole_byte_bridges=bridges,changed_characterizer_functions=changed,source_controls=f['controls'],handoff_controls=f['actual_handoff_controls'],scope='Full changed sources/launcher read; all untouched safety/streaming/deck/measurement functions AST exact. Actual455 devices,64 HBT OFF,31 contacts,956vectors and distinct body/wire ideal bench references retained. Measured combined1271R1414C replaces prior1273R1422C. Final25+4 saved controls pinned. No simulation or reviewed production method executed by peer. Physical headroom/division/frequency still require actual native results; no qualified substrate PEX or full PHY claim.')
(B/'source-only-peer01-rx.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
