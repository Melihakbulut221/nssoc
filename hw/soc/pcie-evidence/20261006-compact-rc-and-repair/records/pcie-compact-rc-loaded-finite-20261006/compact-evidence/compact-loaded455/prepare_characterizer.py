"""Derive separate compact routing recipe; parent models/screens stay frozen."""
from pathlib import Path
import ast,difflib,gzip,hashlib,json,re
R=Path.cwd();B=Path(__file__).resolve().parent;G=B.parent/'pcie-divider-v7-compact-v2-wire-v1-20261006';F=R/'sw/tests/fixtures/pcie_clock_div4_v7_compact_v2_hybrid_v1'
def pin(p):b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
assert not F.exists();F.mkdir();(F/'inputs').mkdir()
for name in ['hybrid-open.spice','composition.json']:(F/name).write_bytes((B/'composed01'/name).read_bytes())
(F/'source-native-bijection.json').write_bytes((G/'source-native-bijection.json').read_bytes())
plan=json.loads((B/'builder-source-freeze.json').read_text())
for name,path in plan['native_input_files'].items():
 p=Path(path);assert pin(p)==plan['inputs'][str(p)];data=p.read_bytes();target=F/'inputs'/(p.name+'.gz');target.write_bytes(gzip.compress(data,mtime=0));assert gzip.decompress(target.read_bytes())==data
for p in [p for p in F.rglob('*')if p.is_file()]:
 license_id='CERN-OHL-W-2.0'if '.spice'in p.name or '.cir'in p.name else 'CC-BY-4.0';Path(str(p)+'.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: '+license_id+'\n')
bridges=[]
def save(old,new,a,b):
 assert old.read_text()==a and not new.exists()
 if new.suffix=='.py':ast.parse(b)
 new.write_text(b);aa,zz=a.splitlines(True),b.splitlines(True);ops=[dict(tag=k,before=''.join(aa[i:j]),after=''.join(zz[x:y]))for k,i,j,x,y in difflib.SequenceMatcher(None,aa,zz,autojunk=False).get_opcodes()];assert ''.join(x['before']for x in ops)==a and ''.join(x['after']for x in ops)==b;bridges.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=ops))
old=R/'hw/soc/analog/pcie/pll_feedback_vco_v6_divider_power_v2_wire_v1.spice';new=R/'hw/soc/analog/pcie/pll_feedback_vco_v6_divider_compact_v2_wire_v1.spice';a=old.read_text();b=a.replace('divider_power_v2_wire_v1','divider_compact_v2_wire_v1').replace('div4_v7_power_v2_hybrid_open_v1','div4_v7_compact_v2_hybrid_open_v1');save(old,new,a,b)
old=R/'scripts/characterize_pcie_vco_v6_divider_power_v2_wire_v1.py';new=R/'scripts/characterize_pcie_vco_v6_divider_compact_v2_wire_v1.py';a=old.read_text();b=a.replace('div4_v7_power_v2_hybrid','div4_v7_compact_v2_hybrid').replace('divider_power_v2_wire_v1','divider_compact_v2_wire_v1').replace('nssoc-vco-v6-divider-power-v2-wire-*','nssoc-vco-v6-divider-compact-v2-wire-*').replace('wire_resistors=1273, wire_capacitors=1422','wire_resistors=1271, wire_capacitors=1414').replace('== 1273 and sum(x.startswith("C") for x in wire_lines) == 1422','== 1271 and sum(x.startswith("C") for x in wire_lines) == 1414')
b,n=re.subn(r'BUILDER_SHA = "[a-f0-9]{64}"','BUILDER_SHA = "'+pin(R/'scripts/build_pcie_clock_div4_v7_compact_v2_hybrid_v1.py')['sha256']+'"',b);assert n==1
pins={n:pin(F/n)['sha256']for n in ['hybrid-open.spice','composition.json','source-native-bijection.json']};b,n=re.subn(r'^DIVIDER_PINS = .+$','DIVIDER_PINS = '+repr(pins),b,flags=re.M);assert n==1;save(old,new,a,b)
old=R/'sw/tests/test_pcie_vco_v6_divider_power_v2_wire_v1.py';new=R/'sw/tests/test_pcie_vco_v6_divider_compact_v2_wire_v1.py';a=old.read_text();b=a.replace('characterize_pcie_vco_v6_divider_power_v2_wire_v1','characterize_pcie_vco_v6_divider_compact_v2_wire_v1').replace("c['wire_resistors']==1273 and c['wire_capacitors']==1422","c['wire_resistors']==1271 and c['wire_capacitors']==1414");save(old,new,a,b)
(B/'characterizer-source-bridge.json').write_text(json.dumps(bridges,indent=2)+'\n');(B/'composition-fixture-copy.json').write_text(json.dumps(dict(inputs={str(p):pin(p)for p in [B/'composed01'/n for n in ['hybrid-open.spice','composition.json']]+[G/'source-native-bijection.json']},outputs={str(p):pin(p)for p in F.rglob('*')if p.is_file()},lossless_gzip=True,frozen_generated_bytes_unchanged=True),indent=2)+'\n')
print('Separate compact loaded455 sources prepared')
