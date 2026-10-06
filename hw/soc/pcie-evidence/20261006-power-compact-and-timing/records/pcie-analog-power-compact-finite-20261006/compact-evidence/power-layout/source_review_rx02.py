"""Independent source-only powerV2 review; never execute producer/native methods."""
from pathlib import Path
from decimal import Decimal
import ast
import hashlib
import json

R = Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B = Path(__file__).resolve().parent


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


def functions(p):
    return {n.name: ast.dump(n, include_attributes=False)
            for n in ast.parse(Path(p).read_text()).body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


freeze = B / 'source-freeze02.json'
assert pin(freeze) == dict(bytes=85759, sha256='8d49e95f0088b0975a7ed2736556a3514f075d21e6b59f886a3e4561c9f732db')
f = json.loads(freeze.read_text())
assert len(f['inputs']) == 313
for p, expected in f['inputs'].items():
    assert pin(p) == expected, p
for p, expected in f['product_sources'].items():
    assert pin(p) == expected, p
bridges = json.loads((B / 'source-bridge02.json').read_text())
assert len(bridges) == 6
bridge_results = []
for bridge in bridges:
    for side in ('before', 'after'):
        p = Path(bridge[side]['path'])
        assert pin(p) == {k: bridge[side][k] for k in ('bytes', 'sha256')}
        reconstructed = ''.join(op[side] for op in bridge['opcodes']).encode()
        assert reconstructed == p.read_bytes(), (side, str(p))
    bridge_results.append(dict(before=bridge['before'], after=bridge['after'], complete_byte_inverse=True))
flow = R / 'hw/soc/flow'
old = functions(flow / 'check_pcie_clock_div4_v7_power_v1.py')
new = functions(flow / 'check_pcie_clock_div4_v7_power_v2.py')
unchanged = ['require', 'atomic', 'lifecycle', 'limits', 'scratch_bytes', 'guard_resources', 'execute', 'fault_reference', 'mutation_source', 'validate_expanded_devices', 'validate_lvs', 'lef_script']
assert all(old[n] == new[n] for n in unchanged)
maker_old = (flow / 'make_pcie_clock_div4_v7_power_v1.py').read_text()
maker_new = (flow / 'make_pcie_clock_div4_v7_power_v2.py').read_text()
assert maker_old.replace('power v1', 'power v2').replace('power_v1', 'power_v2').replace('            vn_columns=3,\n', '            vn_columns=2,\n') == maker_new
# Independent arithmetic against the read frozen official PCell code. The
# generic lower M5 and lower TopMetal1 rectangles are contained by the outer
# enclosures, so the auditor's merged-region formulas are exact for this case.
techpath = next(Path(p) for p in f['inputs'] if p.endswith('/sg13g2_tech.json'))
tech = json.loads(techpath.read_text())['techParams']
t = lambda name: Decimal(str(tech[name]))
vn_x = 2*t('Vn_a') + t('Vn_b')
vn_y = 3*t('Vn_a') + 2*t('Vn_b')
tv1 = 2*t('TV1_a') + t('TV1_b')
tv2 = 2*t('TV2_a') + t('TV2_b')
assert max(vn_x, vn_y) + 2*t('Vn_c1') <= tv1 + 2*t('TV1_c')
assert tv1 + 2*t('TV1_d') <= tv2 + 2*t('TV2_c')
assert 2*t('TV1_a') + 2*t('TV1_b') >= t('TM1_a')
assert 2*t('TV2_a') + 2*t('TV2_b') >= t('TM2_a')
assert tv2 + 2*max(t('TV2_c'), t('TV2_d')) <= 6
def cuts(nx, ny):
    size, space = t('Vn_a'), t('Vn_b')
    wx, wy = nx*size+(nx-1)*space, ny*size+(ny-1)*space
    return {(i*(size+space)-wx/2, j*(size+space)-wy/2,
             i*(size+space)-wx/2+size, j*(size+space)-wy/2+size)
            for i in range(nx) for j in range(ny)}
assert cuts(2, 1) <= cuts(2, 3)
controls = []
raw = Path(f['controls']['raw_directory'])
for p in sorted(raw.rglob('*.owned.json')):
    j = json.loads(p.read_text())
    assert len(j['processes']) == 1
    assert j['processes'][0]['status'] in ('REAPED_NO_LIVE_MEMBERS', 'FAILURE_REAPED')
    controls.append(dict(path=str(p), pin=pin(p), status=j['status'], child_status=j['processes'][0]['status']))
assert len(controls) == 6
assert '60 passed' in (B / 'source-controls03.log').read_text()
# Supplemental launch-runtime pin gate is completed by the final peer receipt.
report = dict(status='INDEPENDENT_POWER_V2_SOURCE_BODY_REVIEW_COMPLETE_AWAITING_LAUNCH_RUNTIME_ADDENDUM',
              freeze=pin(freeze), source_pins=f['product_sources'], launcher=pin(B/'launch02.py'),
              input_count=313, bridge_results=bridge_results, unchanged_checker_function_asts=unchanged,
              pdk_geometry_arithmetic=dict(Via4_width_um=str(vn_x), Via4_height_um=str(vn_y),
                                           TopVia1_span_um=str(tv1), TopVia2_span_um=str(tv2),
                                           old_2_by_1_cuts_retained_exactly=True),
              saved_lifecycle_controls=controls, saved_control_count=60,
              review='Full V2 auditor read. All678 original leaf instance keys and placements are retained, old cell per-layer geometry remains exact, and exactly47 extras bind uniquely by actual transform and native class. Every added cell layer/cut/enclosure region must equal independent frozen-tech formulas, with no unexpected layer accepted. All old recursive drawings/texts/bbox stay exact or subset only on seven allowed power layers. Eight full strap rectangles are checked in actual GDS. The fourth narrow control removes one actual added Via4 array from the native instance geometry while retaining old instances and upper straps; exact binding must reject it. Original21 native gates and12 checker lifecycle/validation function ASTs remain unchanged. The 2x3 Via4 correction is source-derived and has not been measured by DRC.',
              controls_limit='Saved60 controls are source/parser/lifecycle tests. The four actual native-geometry controls run only after fresh native generation; no such generation or geometry audit was executed by this reviewer. Teardown receipt can remain HEALTHY before its post-context signal guard raises, as explicitly preserved by its actual test.',
              native_executed=False, product_acceptance=False)
out = B / 'source-body-review02-rx.json'
assert not out.exists()
out.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(dict(path=str(out), **pin(out))))
