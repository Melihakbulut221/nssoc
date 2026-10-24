"""Derive separately named power-overlay loaded455 recipe from the frozen parent."""
from pathlib import Path
import ast
import difflib
import gzip
import hashlib
import json
import re

R = Path.cwd()
B = Path(__file__).resolve().parent
G = B.parent / 'pcie-divider-v7-power-v2-wire-v2-20261006'
OLD = B.parent / 'pcie-vco-v6-divider-wire-v1-20261005'
F = R / 'sw/tests/fixtures/pcie_clock_div4_v7_power_v2_hybrid_v1'

def pin(p):
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())

assert not F.exists()
F.mkdir()
for name in ['hybrid-open.spice', 'composition.json']:
    (F / name).write_bytes((B / 'composed01' / name).read_bytes())
(F / 'source-native-bijection.json').write_bytes((G / 'source-native-bijection.json').read_bytes())
(F / 'inputs').mkdir()
plan = json.loads((B / 'builder-source-freeze.json').read_text())
for name, path in plan['native_input_files'].items():
    p = Path(path)
    assert pin(p) == plan['inputs'][str(p)]
    data = p.read_bytes()
    (F / 'inputs' / (p.name + '.gz')).write_bytes(gzip.compress(data, mtime=0))
    assert gzip.decompress((F / 'inputs' / (p.name + '.gz')).read_bytes()) == data
# License metadata is additive; all frozen generated/input bytes stay exact.
for p in [q for q in F.rglob('*') if q.is_file()]:
    license_id = 'CERN-OHL-W-2.0' if '.spice' in p.name or '.cir' in p.name else 'CC-BY-4.0'
    Path(str(p) + '.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: ' + license_id + '\n')

bridges = []
def save(old, new, before, after):
    assert old.read_text() == before and not new.exists()
    ast.parse(after) if new.suffix == '.py' else None
    new.write_text(after)
    aa, zz = before.splitlines(True), after.splitlines(True)
    ops = [dict(tag=k, before=''.join(aa[a:b]), after=''.join(zz[c:d]))
           for k, a, b, c, d in difflib.SequenceMatcher(None, aa, zz, autojunk=False).get_opcodes()]
    assert ''.join(x['before'] for x in ops) == before
    assert ''.join(x['after'] for x in ops) == after
    bridges.append(dict(before=dict(path=str(old), **pin(old)),
                        after=dict(path=str(new), **pin(new)), opcodes=ops))

old = R / 'hw/soc/analog/pcie/pll_feedback_vco_v6_divider_wire_v1.spice'
new = R / 'hw/soc/analog/pcie/pll_feedback_vco_v6_divider_power_v2_wire_v1.spice'
s = old.read_text()
t = s.replace('nssoc_pll_feedback_vco_v6_divider_wire_v1', 'nssoc_pll_feedback_vco_v6_divider_power_v2_wire_v1').replace('nssoc_clock_div4_v7_hybrid_open_v1', 'nssoc_clock_div4_v7_power_v2_hybrid_open_v1')
save(old, new, s, t)

old = R / 'scripts/characterize_pcie_vco_v6_divider_wire_v1.py'
new = R / 'scripts/characterize_pcie_vco_v6_divider_power_v2_wire_v1.py'
s = old.read_text()
t = s.replace('build_pcie_clock_div4_v7_hybrid_v1', 'build_pcie_clock_div4_v7_power_v2_hybrid_v1').replace('pcie_clock_div4_v7_hybrid_v1', 'pcie_clock_div4_v7_power_v2_hybrid_v1').replace('nssoc_clock_div4_v7_hybrid_open_v1', 'nssoc_clock_div4_v7_power_v2_hybrid_open_v1').replace('pll_feedback_vco_v6_divider_wire_v1', 'pll_feedback_vco_v6_divider_power_v2_wire_v1').replace('nssoc-vco-v6-divider-wire-*', 'nssoc-vco-v6-divider-power-v2-wire-*').replace('wire_resistors=1201, wire_capacitors=1383', 'wire_resistors=1273, wire_capacitors=1422')
t, count = re.subn(r'BUILDER_SHA = "[a-f0-9]{64}"', 'BUILDER_SHA = "' + pin(R / 'scripts/build_pcie_clock_div4_v7_power_v2_hybrid_v1.py')['sha256'] + '"', t)
assert count == 1
pins = {name: pin(F / name)['sha256'] for name in ['hybrid-open.spice', 'composition.json', 'source-native-bijection.json']}
t, count = re.subn(r'^DIVIDER_PINS = .+$', 'DIVIDER_PINS = ' + repr(pins), t, flags=re.M)
assert count == 1
save(old, new, s, t)

old = R / 'sw/tests/test_pcie_vco_v6_divider_wire_v1.py'
new = R / 'sw/tests/test_pcie_vco_v6_divider_power_v2_wire_v1.py'
s = old.read_text()
t = s.replace('characterize_pcie_vco_v6_divider_wire_v1', 'characterize_pcie_vco_v6_divider_power_v2_wire_v1').replace("c['wire_resistors']==1201 and c['wire_capacitors']==1383", "c['wire_resistors']==1273 and c['wire_capacitors']==1422")
save(old, new, s, t)
(B / 'characterizer-source-bridge.json').write_text(json.dumps(bridges, indent=2) + '\n')
(B / 'composition-fixture-copy.json').write_text(json.dumps(dict(
    inputs={str(p): pin(p) for p in [*[(B / 'composed01' / x) for x in ['hybrid-open.spice', 'composition.json']], G / 'source-native-bijection.json']},
    outputs={str(p): pin(p) for p in F.rglob('*') if p.is_file()},
    lossless_gzip=True, frozen_generated_bytes_unchanged=True,
), indent=2) + '\n')
print('Prepared separate loaded455 power-overlay sources and exact fixture bytes')
