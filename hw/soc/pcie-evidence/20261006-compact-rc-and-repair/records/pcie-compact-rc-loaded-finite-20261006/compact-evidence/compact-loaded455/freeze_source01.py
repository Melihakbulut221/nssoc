"""Freeze all new loaded455 sources, exact fixtures and actual controls."""
from pathlib import Path
import hashlib
import json
import sys

R = Path.cwd()
B = Path(__file__).resolve().parent
sys.path.insert(0, str(R / 'scripts'))
import characterize_pcie_vco_v6_divider_compact_v2_wire_v1 as m

def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())

assert not (B / 'source-freeze01.json').exists()
controls = json.loads((B / 'source-controls-receipt.json').read_text())
assert controls['returncode'] == 0 and controls['passed'] == 25
handoff = json.loads((B / 'handoff-controls-receipt.json').read_text())
assert handoff['returncode'] == 0 and handoff['passed'] == 4
rc = B.parent / 'pcie-divider-v7-compact-v2-wire-rc-v1-20261006'
rc_peer = json.loads((rc / 'saved-rc-peer-pll.json').read_text())
assert rc_peer['status'] == 'PASS_INDEPENDENT_SAVED_COMPACT_V2_DIVIDER_WIRE_GRAPH_AND_CAPACITANCE' and rc_peer['findings'] == []
assert rc_peer['inputs'] == {p: pin(p) for p in rc_peer['inputs']}
products = [R / 'scripts/build_pcie_clock_div4_v7_compact_v2_hybrid_v1.py',
            R / 'scripts/characterize_pcie_vco_v6_divider_compact_v2_wire_v1.py',
            m.CHAIN, R / 'sw/tests/test_pcie_vco_v6_divider_compact_v2_wire_v1.py',
            *[p for p in m.DIVIDER.rglob('*') if p.is_file()]]
paths = set(products)
for module in list(sys.modules.values()):
    raw = getattr(module, '__file__', None)
    if raw and Path(raw).is_relative_to(R / 'scripts') and raw.endswith('.py'):
        paths.add(Path(raw))
for bias, fault in [(.6, ''), (.85, ''), (.6, 'disconnect_divider_clock'), (.6, 'wrong_feedback_modulus')]:
    c, rows, texts = m.config(bias, fault)
    paths.update(Path(p) for p in c['sources'])
    assert len(rows) == 455 and len(m.n.vectors(rows, c['extra_vectors'])) == 956
    (B / ('recipe-' + str(bias) + '-' + (fault or 'nominal') + '.json')).write_text(json.dumps(dict(
        config=c, devices=rows, vector_count=956,
        included_texts={name: dict(bytes=len(text.encode()), sha256=hashlib.sha256(text.encode()).hexdigest()) for name, text in texts.items()},
    ), indent=2) + '\n')
paths.update(m.n.MODELS.glob('*.lib'))
paths.update(m.n.OSDI)
paths.add(m.n.NG)
paths.update(m.core.HYBRID / x for x in m.core.PINS)
paths.update(Path(p) for p in rc_peer['inputs'])
paths.add(rc / 'saved-rc-peer-pll.json')
paths.update(p for p in B.rglob('*') if p.is_file() and p.suffix != '.pyc' and '__pycache__' not in p.parts)
record = dict(status='FROZEN_SOURCE_ONLY_455_DEVICE_ACTUAL_VCO_DIVIDER_COMPACT_V2_WIRE_MODEL',
              new_sources={str(p.relative_to(R)): pin(p) for p in products},
              pins={str(p.resolve()): pin(p) for p in sorted(paths)},
              controls=controls, actual_handoff_controls=handoff,
              predeclared=dict(vctrl=.6, stop_s=34e-9, step_s=5e-12,
                               window_s=[4e-9, 34e-9], intrinsics=455, HBT=64,
                               finite_contacts=31, vectors=956, wire_R=1271, wire_C=1414,
                               CPU=10, AS=2*1024**3, own_limit=80*1024**2,
                               floor=512*1024**2, elapsed_watchdog=None),
              source_peer_required_before_native=True, qualified_PEX=False,
              main_chip_integrated=False)
(B / 'source-freeze01.json').write_text(json.dumps(record, indent=2) + '\n')
print(len(paths), len(products), pin(B / 'source-freeze01.json'))
