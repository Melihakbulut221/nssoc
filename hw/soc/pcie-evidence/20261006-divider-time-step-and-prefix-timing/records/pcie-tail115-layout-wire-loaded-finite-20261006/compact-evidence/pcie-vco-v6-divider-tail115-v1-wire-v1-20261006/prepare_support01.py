"""Derive exact launch, handoff controls, sealer and freezer after RC census."""
from pathlib import Path
import ast
import difflib
import hashlib
import json

B = Path(__file__).resolve().parent
OLD = B.parent / 'pcie-vco-v6-divider-bias8-v1-wire-v1-20261006'
plan = json.loads((B / 'builder-source-freeze.json').read_text())
nr, nc = plan['total_chain_resistors'], plan['total_chain_capacitors']


def pin(p):
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())


for name, receipt in [('launch_probe01.py', 'launcher-source-bridge.json'),
                      ('test_launcher01_handoff.py', 'handoff-source-bridge.json'),
                      ('seal_probe01.py', 'sealer-source-bridge.json'),
                      ('freeze_source01.py', 'freezer-source-bridge.json')]:
    old, new = OLD / name, B / name
    assert not new.exists()
    a = old.read_text()
    z = a.replace('divider_bias8_v1_wire_v1', 'divider_tail115_v1_wire_v1').replace('divider-bias8-v1-wire', 'divider-tail115-v1-wire').replace('div4_v9_bias8_v1_hybrid', 'div4_v10_tail115_v1_hybrid').replace('div4-v9-bias-v1', 'div4-v10-tail-v1').replace('divider-v9-bias-v1', 'divider-v10-tail-v1')
    z = z.replace('loaded455_bias8_launcher01', 'loaded455_tail115_launcher01').replace('BIAS8_V1_DIVIDER', 'TAIL115_V1_DIVIDER').replace('DIVIDER_BIAS8_V1_WIRE_MODEL', 'DIVIDER_TAIL115_V1_WIRE_MODEL')
    z = z.replace("controls['passed'] == 30", "controls['passed'] == 32")
    z = z.replace('devices;1271R/1414C.', f'devices;{nr}R/{nc}C.')
    ast.parse(z)
    new.write_text(z)
    aa, zz = a.splitlines(True), z.splitlines(True)
    ops = [dict(tag=t, before=''.join(aa[i:j]), after=''.join(zz[k:l])) for t, i, j, k, l in difflib.SequenceMatcher(None, aa, zz, autojunk=False).get_opcodes()]
    assert ''.join(o['before'] for o in ops) == a and ''.join(o['after'] for o in ops) == z
    (B / receipt).write_text(json.dumps(dict(before=dict(path=str(old), **pin(old)), after=dict(path=str(new), **pin(new)), opcodes=ops), indent=2) + '\n')
print('Support sources prepared without running native or tests')
