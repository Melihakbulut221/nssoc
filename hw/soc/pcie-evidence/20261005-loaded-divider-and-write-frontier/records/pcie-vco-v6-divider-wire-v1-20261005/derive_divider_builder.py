# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate actual-divider composition contract; retain complete parent inverse."""
from pathlib import Path
import ast
import difflib
import hashlib
import json

B = Path(__file__).resolve().parent
ROOT = B.parents[3]
P = ROOT / 'scripts/build_pcie_vco_v6_hybrid_v1.py'
N = ROOT / 'scripts/build_pcie_clock_div4_v7_hybrid_v1.py'
G = B.parent / 'pcie-divider-v7-wire-v5-20261005'
INPUTS = dict(anchors=G / 'anchors.json', devices=G / 'device-location-geometry.json',
              geometry=G / 'wire-component-geometry.json',
              native=Path('/dev/shm/nssoc-div4-v7-wire-native-02/extracted.cir'),
              wires=Path('/dev/shm/nssoc-div4-v7-wire-rc-01/wires.spice'))


def pin(p):
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())


old = P.read_text()
text = old
operations = []


def change(a, b, count=1):
    global text
    assert text.count(a) == count, (a, text.count(a), count)
    assert a != b
    text = text.replace(a, b)
    operations.append(dict(old=a, new=b, count=count))


tree = ast.parse(old)
pins_node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PINS' for t in n.targets))
old_pins = ast.literal_eval(pins_node.value)
for name, value in old_pins.items():
    change(value, pin(INPUTS[name])['sha256'])
old_census = ast.get_source_segment(old, next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CENSUS' for t in n.targets)))
change(old_census, 'CENSUS = {\n    "npn13G2": 34,\n    "rppd": 33,\n    "cap_cmim": 6,\n    "ptap1": 18,\n}')
change('range(1, 63)', 'range(1, 92)', 2)
change('{"R": 889, "C": 765}', '{"R": 312, "C": 618}')
change('len(by_label) == len(ports) == 151', 'len(by_label) == len(ports) == 205')
change('len(owners) == 20 and set(owners.values()) == set(range(1, 21))', 'len(owners) == 37 and set(owners.values()) == set(range(1, 38))')
change('len(metal) == 145 and len(body) == 56', 'len(metal) == 198 and len(body) == 85')
change('== {1: 51, 2: 5}', '== {1: 85}')
change('len(public) == 6', 'len(public) == 7')
change('len(set(public.values())) == 6', 'len(set(public.values())) == 7')
change('Exact 62-device / 151-anchor', 'Exact 91-device / 205-anchor')
change('nssoc_vco_local_hybrid_open_v2', 'nssoc_clock_div4_v7_hybrid_open_v1', 2)
change('''                net = (
                    "BODY_SUBSTRATE"
                    if witness["native_cluster"] == 1
                    else "body_well_2"
                )''', '''                require(witness["native_cluster"] == 1, "Only actual native divider substrate")
                net = "BODY_SUBSTRATE"''')
for a, b in [('intrinsic_devices=62', 'intrinsic_devices=91'), ('metal_terminal_anchors=145', 'metal_terminal_anchors=198'),
             ('body_well_terminals=56', 'body_well_terminals=85'), ('finite_contacts=13', 'finite_contacts=18'),
             ('wire_components=20', 'wire_components=37'), ('public_ports=6', 'public_ports=7')]:
    change(a, b)
change('# Only the three exact, pinned native JSON binary-float serialization artifacts.', '# Only the two observed pinned-divider JSON binary-float serialization artifacts.')
change('''        "38.400000000000006": "38.4",
        "11.200000000000001": "11.2",
        "44.400000000000006": "44.4",''', '''        "38.400000000000006": "38.4",
        "12.700000000000001": "12.7",''')
inverse = text
for op in reversed(operations):
    assert inverse.count(op['new']) == op['count'], op
    inverse = inverse.replace(op['new'], op['old'])
assert inverse == old
compile(text, str(N), 'exec')
assert 'body_well_2' not in text and 'range(1, 92)' in text and '{"R": 312, "C": 618}' in text
assert not N.exists()
N.write_text(text)
record = dict(status='PASS_SOURCE_ONLY_DIVIDER_BUILDER_FULL_BYTE_DERIVATION',
              parent=dict(path=str(P), **pin(P)), new=dict(path=str(N), **pin(N)),
              operations=operations, whole_byte_inverse=True,
              full_diff=''.join(difflib.unified_diff(old.splitlines(True), text.splitlines(True))),
              native_inputs={str(p): pin(p) for p in INPUTS.values()},
              inherited_exact_parameter_census_and_wire_body_contract=True,
              composition_or_simulation_executed=False)
(B / 'divider-builder-source-bridge.json').write_text(json.dumps(record, indent=2) + '\n')
print(pin(N), 'full byte inverse PASS', flush=True)
