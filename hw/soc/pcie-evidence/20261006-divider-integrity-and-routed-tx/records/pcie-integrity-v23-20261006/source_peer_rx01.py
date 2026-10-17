"""Independent source-only V23 review; never imports a producer or starts HDL."""
import ast
import datetime
import hashlib
import json
from pathlib import Path

R = Path.cwd()
B = Path(__file__).resolve().parent


def pin(p):
    p = Path(p)
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def literal(n, values):
    if isinstance(n, ast.Constant):
        return n.value
    if isinstance(n, ast.Name):
        return values[n.id]
    if isinstance(n, (ast.Tuple, ast.List)):
        values_out = [literal(x, values) for x in n.elts]
        return tuple(values_out) if isinstance(n, ast.Tuple) else values_out
    if isinstance(n, ast.Dict):
        return {literal(k, values): literal(v, values) for k, v in zip(n.keys, n.values)}
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
        return literal(n.left, values) + literal(n.right, values)
    raise ValueError(ast.dump(n))


def constants(path):
    values = {}
    for n in ast.parse(path.read_text()).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            try:
                values[n.targets[0].id] = literal(n.value, values)
            except (ValueError, KeyError):
                pass
        if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name) and isinstance(n.op, ast.Add):
            values[n.target.id] += literal(n.value, values)
    return values


f = json.loads((B / 'source-freeze01.json').read_text())
assert pin(B / 'source-freeze01.json') == dict(bytes=3778, sha256='446efb90f07eb3b2fe960498c55079afb385c3a89f8e2dad6dc02f028372b630')
checked = {}
for name, expected in f['sources'].items():
    assert pin(R / name) == expected, name
    checked[name] = expected
for name, expected in f['contracts'].items():
    assert pin(B / name) == expected, name
    checked[str((B / name).relative_to(R))] = expected
parent = R / f['baseline']['path']
assert pin(parent) == {k: f['baseline'][k] for k in ('bytes', 'sha256')}
checked[str(parent.relative_to(R))] = pin(parent)
g = constants(R / 'scripts/generate_pcie_integrity_header_v23.py')
assert len(g['EDITS']) == 15 and g['SOURCE_SHA'] == pin(parent)['sha256']
old = parent.read_text()
new_path = R / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v'
new = new_path.read_text()
forward = old
for before, after in g['EDITS']:
    assert forward.count(before) == 1
    forward = forward.replace(before, after)
assert forward.replace('integrity_v22', 'integrity_v23') == new
inverse = new.replace('integrity_v23', 'integrity_v22')
for before, after in reversed(g['EDITS']):
    assert inverse.count(after) == 1
    inverse = inverse.replace(after, before)
assert inverse.encode() == parent.read_bytes()

exact_bridges = []
for name in ('hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v22.v',
             'hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v22',
             'scripts/check_pcie_gen3_continuous_rx_integrity_v22.py'):
    child = name.replace('_v22', '_v23')
    assert (R / child).read_text().replace('_v23', '_v22') == (R / name).read_text()
    checked[name] = pin(R / name)
    exact_bridges.append(dict(old=name, new=child))
old_bench = R / 'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v22.py'
bench_path = R / 'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py'
bench = bench_path.read_text()
assert bench.replace('_v23', '_v22').replace('V23_', 'V22_').startswith(old_bench.read_text())
case_names = lambda p: [x.name for x in ast.parse(p.read_text()).body if isinstance(x, ast.AsyncFunctionDef) and x.decorator_list]
old_cases, new_cases = case_names(old_bench), case_names(bench_path)
assert len(old_cases) == 17 and len(new_cases) == 18 and old_cases == new_cases[:17]
checked[str(old_bench.relative_to(R))] = pin(old_bench)
start, end = ' // BEGIN V6 SHARED OLD VERDICT READS', ' // END V5 SLOT VERDICT CACHE'
assert new[new.index(start):new.index(end)] == old[old.index(start):old.index(end)]

public_path = R / 'sw/tests/test_pcie_gen3_continuous_rx_integrity_v23.py'
public = constants(public_path)
assert len(public['FAULTS']) == 12
for name, module, before, after, count, case in public['FAULTS']:
    assert (R / ('hw/soc/rtl/pcie/' + module + '.v')).read_text().count(before) == count, name
    assert case in new_cases and before != after, name
miter_path = R / 'sw/tests/test_pcie_gen3_integrity_v23_miter.py'
miter = constants(miter_path)
assert len(miter['HEADER_FAULTS']) == 6
for name, (before, after) in miter['HEADER_FAULTS'].items():
    assert new.count(before) == 1 and before != after, name
observer = miter['HEADER_OBSERVER']
for text in ("v23_in_pred={15'h7fff,v23_tail_valid};", 'v23_source_id != v23_last_stp_id+1',
             'v23_current_pred[v23_j] !== 1\'b1', 'v23_current_stp[v23_j] !== 1\'b1',
             'v23_current_base<=v23_next_base;', 'v23_current_base<=v23_accept_base;',
             'v23_current_base<=v23_current_base+4;', 'v23_accept_base<=v23_accept_base+16;',
             'reference.framer.control_carry_end[3]', 'V23_OBSERVER_OLD_PREDECESSOR'):
    assert text in observer, text
assert 34 * 16 * 1024 == 557056 and 45 * 2 * 16 == 1440
assert f['predicates']['total_pytest_selected'] == 13 + 14 + 8 == 35

support = json.loads((B / 'support-source-supplement02.json').read_text())
sanitized = "**{k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')}"
for name, value in support['original'].items():
    assert pin(B / name) == value
    assert pin(B / 'support-source01' / name) == value
for name, value in support['final'].items():
    assert pin(B / name) == value
    checked[str((B / name).relative_to(R))] = value
assert (B / 'launch_controls02.py').read_text().replace(sanitized, '**os.environ') == (B / 'launch_controls01.py').read_text()
detached = (B / 'detach_controls02.py').read_text().replace(sanitized, '**os.environ').replace('launch_controls02.py', 'launch_controls01.py')
detached = detached.replace(str(support['final']['launch_controls02.py']), str(support['original']['launch_controls01.py']))
assert detached == (B / 'detach_controls01.py').read_text()
life = R / 'scripts/characterize_pcie_clock_trim_stream_v2.py'
assert pin(life)['sha256'] == '39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886'
checked[str(life.relative_to(R))] = pin(life)
assert not (B / 'controls-status01.json').exists()
assert not Path('/dev/shm/nssoc-integrity-v23-public-controls01').exists()
receipt = dict(
    status='PASS_SOURCE_ONLY_V23_ADJACENT_HEADER_RELATION',
    utc=datetime.datetime.now(datetime.UTC).isoformat(), freeze=pin(B / 'source-freeze01.json'), findings=[],
    sources=f['sources'], support_methods=support['final'], support_supplement=pin(B / 'support-source-supplement02.json'),
    checked_pins=checked, method=pin(Path(__file__)),
    review=dict(
        complete_source_inverse='All 15 literal edits independently evaluated by a restricted AST-literal reader; complete forward bytes and complete inverse bytes match frozen V22. No producer import or execution.',
        unchanged_bridges=exact_bridges,
        unchanged_cache='Complete V6 old-verdict read through V5 slot-verdict cache body byte-identical to V22. V22 cache literals are inherited evidence, not newly executed.',
        temporal='Adjacent relation uses the old accepted tail at each actual acceptance; current/next relation banks match the exact data writer promotion/shift/input priorities. First-header j0 uses current relation before the same-step carry-end j3; later carry uses registered packet mismatch. STP resets mismatch and first header sets it; reset/start/abort/fault clear ownership.',
        ownership='Independent observer carries old predecessor-present/STP masks and absolute accepted-word identities through the same observed reference bank movement. Consumed header must have a present STP predecessor and identity exactly one after the last actual STP. Actual j15-to-next-j0 and minimum same-beat witnesses remain required.',
        public_oracle='All 17 prior decorated public cases are an exact prefix after version-only normalization. Added 18th checks packet bytes/count/drain and, in the miter, all 16 STP positions, cross-block first header, same-beat minimum end, and missing-old-predecessor acceptance witnesses.',
        fourstate='Literal relation uses !== against the original scalar header predicate, including ternary X/Z semantics. Planned 557056 binary tuples and 1440 selected X/Z tuples; this is not arbitrary sequential four-state equivalence.',
        faults='12 original public mutations bind real RTL strings and named actual cases. Six new header mutations plus six inherited miter mutations require semantic simulator failures and compiled output. Separate deliberately broken predecessor observer is labelled observer validation. Actual positive and negative executions remain mandatory.',
        cache_fault_witness='Since both products now share the same cache writer, miter takes candidate cache snapshot before NBA and compares settled same-positive-edge values after 0.002ns, retaining actual fault-step, changed invalid cache, atomic owner-clear and fresh-epoch checks.',
        launcher='Reviewed whole controller and detacher. Source/peer gates, exclusive fresh roots, lexical .venv Python, CPU6, whole pytest 2GiB AS, no healthy watchdog, ProcessOwner wait and terminal/context checks retained. Both final02 environments remove all three Python override variables.',
        planned_counts=dict(selected_pytest=35, excluded_MAX4118=2, public_cases_per_positive=18, public_mutants=12, miter_product_mutants=12, observer_negative=1, literal_mutants=5, source_inverse_checks=2)),
    resolved_findings=[dict(finding='Original support01 inherited Python environment overrides at detached entry and owned pytest.', resolution='Additive support02 strips PYTHONPATH/PYTHONHOME/PYTHONEXECUTABLE at both boundaries; exact whole-source inverse checked. Original support bytes retained, nine frozen product files unchanged.')],
    scope='Source-only authorization for the declared functional controls. No HDL, tests, native mapping, timing, simulator, signals, or producer execution by this review. No functional PASS, timing improvement, or physical closure is inferred.'
)
target = B / 'source-only-peer-rx01.json'
assert not target.exists()
target.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(dict(status=receipt['status'], receipt=pin(target), checked_pins=len(checked), selected=35, actual_controls_executed=0), indent=2))
