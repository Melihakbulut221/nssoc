from pathlib import Path
import difflib
import hashlib
import json

B = Path(__file__).resolve().parent
OLD = B.parent / 'pcie-divider-v7-power-v2-wire-20261005'

def pin(p):
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())

old_freeze = json.loads((OLD / 'geometry-source-freeze.json').read_text())
assert old_freeze['inputs'] == {p: pin(Path(p)) for p in old_freeze['inputs']}
names = ['run_geometry', 'probe_native_cells', 'probe_device_locations',
         'probe_wire_components', 'probe_terminal_anchors', 'prepare_anchors',
         'bind_source_ids']
bridges = []
for name in names:
    old = OLD / (name + '.py')
    new = B / old.name
    before = old.read_text()
    after = before
    for a, b in [
        ('nssoc-div4-v7-power-v2-wire-native-01', 'nssoc-div4-v7-power-v2-wire-native-02'),
        ('nssoc-div4-v7-power-v2-wire-geometry-01', 'nssoc-div4-v7-power-v2-wire-geometry-02'),
    ]:
        after = after.replace(a, b)
    if name == 'prepare_anchors':
        a = '8484a6f3db8e91923ec6e5d2184bf6ba80570b2c894b5e4f563b637e0165ee3f'
        assert after.count(a) == 1
        after = after.replace(a, '663b60fc14cc9c8e2b4d9a5a758aee6bcd61bdf307c6b3a69a28e63bc470340c')
    if name == 'probe_wire_components':
        a = 'assert ACTIVE_METALS==[8,10,30,50,67,126]\nassert regions[134].is_empty() and regions[133].is_empty()'
        assert after.count(a) == 1
        after = after.replace(a, 'assert ACTIVE_METALS==[8,10,30,50,67,126,134]\nassert not regions[134].is_empty() and not regions[133].is_empty()')
    assert not new.exists()
    new.write_text(after)
    aa, zz = before.splitlines(True), after.splitlines(True)
    ops = [dict(tag=k, before=''.join(aa[a:b]), after=''.join(zz[c:d]))
           for k, a, b, c, d in difflib.SequenceMatcher(None, aa, zz, autojunk=False).get_opcodes()]
    assert ''.join(x['before'] for x in ops) == before
    assert ''.join(x['after'] for x in ops) == after
    bridges.append(dict(before=dict(path=str(old), **pin(old)),
                        after=dict(path=str(new), **pin(new)), opcodes=ops))
(B / 'draft-source-bridge.json').write_text(json.dumps(bridges, indent=2) + '\n')
(B / 'native_unsimplified.lvs').write_bytes((OLD / 'native_unsimplified.lvs').read_bytes())
(B / 'draft-only.json').write_text(json.dumps(dict(
    status='SOURCE_CORRECTION_ONLY_NO_NEW_NATIVE', prior_freeze=pin(OLD / 'geometry-source-freeze.json'),
    prior_review_findings=pin(OLD / 'geometry-source-peer-findings01-rx.json'),
    corrections=['Exact actual PowerV2 GDS pin', 'All seven actual metal layers and nonempty TopMetal2/TopVia2'],
    native_scratch_paths_fresh=True, device_or_threshold_relaxation=False,
    source_expected_census=dict(devices=91, terminals=283, anchors=205, body=85, conductors=37, raw_clusters=72),
    new_native_executed=False,
), indent=2) + '\n')
