"""Separate Bias8 model recipe; preserve all measured parents and thresholds."""
from pathlib import Path
import ast
import difflib
import gzip
import hashlib
import json
import re

R = Path.cwd()
B = Path(__file__).resolve().parent
G = B.parent / 'pcie-divider-v9-bias-v1-wire-v1-20261006'
F = R / 'sw/tests/fixtures/pcie_clock_div4_v9_bias8_v1_hybrid_v1'


def pin(p):
    data = p.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


assert not F.exists()
F.mkdir()
(F / 'inputs').mkdir()
for name in ['hybrid-open.spice', 'composition.json']:
    (F / name).write_bytes((B / 'composed01' / name).read_bytes())
(F / 'source-native-bijection.json').write_bytes((G / 'source-native-bijection.json').read_bytes())
plan = json.loads((B / 'builder-source-freeze.json').read_text())
nr, nc = plan['total_chain_resistors'], plan['total_chain_capacitors']
for name, path in plan['native_input_files'].items():
    p = Path(path)
    assert pin(p) == plan['inputs'][str(p)]
    data = p.read_bytes()
    target = F / 'inputs' / (p.name + '.gz')
    target.write_bytes(gzip.compress(data, mtime=0))
    assert gzip.decompress(target.read_bytes()) == data
for p in [p for p in F.rglob('*') if p.is_file()]:
    license_id = 'CERN-OHL-W-2.0' if '.spice' in p.name or '.cir' in p.name else 'CC-BY-4.0'
    Path(str(p) + '.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: ' + license_id + '\n')
bridges = []


def save(old, new, before, after):
    assert old.read_text() == before and not new.exists()
    if new.suffix == '.py':
        ast.parse(after)
    new.write_text(after)
    a, z = before.splitlines(True), after.splitlines(True)
    ops = [dict(tag=t, before=''.join(a[i:j]), after=''.join(z[k:l]))
           for t, i, j, k, l in difflib.SequenceMatcher(None, a, z, autojunk=False).get_opcodes()]
    assert ''.join(o['before'] for o in ops) == before and ''.join(o['after'] for o in ops) == after
    bridges.append(dict(before=dict(path=str(old), **pin(old)), after=dict(path=str(new), **pin(new)), opcodes=ops))


old = R / 'hw/soc/analog/pcie/pll_feedback_vco_v6_divider_cap24_v1_wire_v1.spice'
new = R / 'hw/soc/analog/pcie/pll_feedback_vco_v6_divider_bias8_v1_wire_v1.spice'
a = old.read_text()
z = a.replace('divider_cap24_v1_wire_v1', 'divider_bias8_v1_wire_v1').replace('div4_v8_cap24_v1_hybrid_open_v1', 'div4_v9_bias8_v1_hybrid_open_v1')
save(old, new, a, z)
old = R / 'scripts/characterize_pcie_vco_v6_divider_cap24_v1_wire_v1.py'
new = R / 'scripts/characterize_pcie_vco_v6_divider_bias8_v1_wire_v1.py'
a = old.read_text()
z = a.replace('div4_v8_cap24_v1_hybrid', 'div4_v9_bias8_v1_hybrid').replace('divider_cap24_v1_wire_v1', 'divider_bias8_v1_wire_v1').replace('nssoc-vco-v6-divider-cap24-v1-wire-*', 'nssoc-vco-v6-divider-bias8-v1-wire-*')
z = z.replace('wire_resistors=1271, wire_capacitors=1414', f'wire_resistors={nr}, wire_capacitors={nc}').replace('== 1271 and sum(x.startswith("C") for x in wire_lines) == 1414', f'== {nr} and sum(x.startswith("C") for x in wire_lines) == {nc}')
z = z.replace('loaded_physical_vco_v6_and_divider_v8_cap24_wire_div80', 'loaded_physical_vco_v6_and_divider_v9_bias8_wire_div80')
z = z.replace('REFERENCE = ANALOG / "clock_div4_hbt_v8.spice"', 'REFERENCE = ANALOG / "clock_div4_hbt_v9.spice"\nREFERENCE_PARENT = ANALOG / "clock_div4_hbt_v8.spice"\nREFERENCE_PARENT_SHA = "87a9c9af0df878208e644987b3318f715d1c54e4b60bbce6944a6af21c2c86dc"')
z, count = re.subn(r'^REFERENCE_SHA = "[a-f0-9]{64}"', 'REFERENCE_SHA = "' + pin(R / 'hw/soc/analog/pcie/clock_div4_hbt_v9.spice')['sha256'] + '"', z, flags=re.M)
assert count == 1
node = next(n for n in ast.parse(z).body if isinstance(n, ast.FunctionDef) and n.name == 'reference_rows')
lines = z.splitlines(True)
z = ''.join(lines[:node.lineno - 1]) + (B / 'reference_rows-fragment.py').read_text() + ''.join(lines[node.end_lineno:])
z = z.replace('c["sources"] += [str(REFERENCE),str(CHAIN),', 'c["sources"] += [str(REFERENCE_PARENT),str(REFERENCE),str(CHAIN),')
z, count = re.subn(r'BUILDER_SHA = "[a-f0-9]{64}"', 'BUILDER_SHA = "' + pin(R / 'scripts/build_pcie_clock_div4_v9_bias8_v1_hybrid_v1.py')['sha256'] + '"', z)
assert count == 1
pins = {name: pin(F / name)['sha256'] for name in ['hybrid-open.spice', 'composition.json', 'source-native-bijection.json']}
z, count = re.subn(r'^DIVIDER_PINS = .+$', 'DIVIDER_PINS = ' + repr(pins), z, flags=re.M)
assert count == 1
save(old, new, a, z)
old = R / 'sw/tests/test_pcie_vco_v6_divider_cap24_v1_wire_v1.py'
new = R / 'sw/tests/test_pcie_vco_v6_divider_bias8_v1_wire_v1.py'
a = old.read_text()
z = a.replace('characterize_pcie_vco_v6_divider_cap24_v1_wire_v1', 'characterize_pcie_vco_v6_divider_bias8_v1_wire_v1').replace("c['wire_resistors']==1271 and c['wire_capacitors']==1414", f"c['wire_resistors']=={nr} and c['wire_capacitors']=={nc}")
z = z.replace('test_authoritative_v8_reference_changes_only_two_coupling_mims', 'test_authoritative_v9_reference_retains_cap24_and_changes_only_two_pulldowns')
z = z.replace("assert changed=={'xchain.xdiv.xcp','xchain.xdiv.xcn'}", "assert changed=={'xchain.xdiv.xcp','xchain.xdiv.xcn','xchain.xdiv.xdp','xchain.xdiv.xdn'}")
z = z.replace("if row['path'] in changed:expected=dict(expected,params={'w':'24u','l':'24u'})", "if row['path'] in {'xchain.xdiv.xcp','xchain.xdiv.xcn'}:expected=dict(expected,params={'w':'24u','l':'24u'})\n        if row['path'] in {'xchain.xdiv.xdp','xchain.xdiv.xdn'}:expected=dict(expected,params=dict(expected['params'],l='8u'))")
z += '''


@pytest.mark.parametrize('name',['xchain.xdiv.xdp','xchain.xdiv.xdn'])
def test_bias8_pulldown_rollback_rejects_actual_native8_geometry(name):
    _, original, texts=m.previous.config()
    rows,_=m.reference_rows(original,texts)
    row=next(r for r in rows if r['path']==name)
    assert row['params']=={'w':'1u','l':'8u','b':'0','sw_et':'1'}
    row['params']['l']='7u'
    with pytest.raises(ValueError,match='geometry/value'):
        m.source_correspondence(json.loads((m.DIVIDER/'composition.json').read_text()),json.loads((m.DIVIDER/'source-native-bijection.json').read_text()),rows)
'''
save(old, new, a, z)
(B / 'characterizer-source-bridge.json').write_text(json.dumps(bridges, indent=2) + '\n')
(B / 'composition-fixture-copy.json').write_text(json.dumps(dict(
    inputs={str(p): pin(p) for p in [B / 'composed01' / n for n in ['hybrid-open.spice', 'composition.json']] + [G / 'source-native-bijection.json']},
    outputs={str(p): pin(p) for p in F.rglob('*') if p.is_file()},
    lossless_gzip=True, frozen_generated_bytes_unchanged=True), indent=2) + '\n')
print('Separate Bias8 loaded455 sources prepared')
