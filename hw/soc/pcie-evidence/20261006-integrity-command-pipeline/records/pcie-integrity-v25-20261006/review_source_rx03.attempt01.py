#!/usr/bin/env python3
"""Read-only independent V25 additive source review; no producer imports."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

R = Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B = R / 'hw/soc/out/pcie-integrity-v25-20261006'


def pin(path):
    p = Path(path)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


def body_pin(text):
    b = text.encode()
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def load(name):
    return json.loads((B / name).read_text())


def full_bridge(x, kind):
    if kind == 'cache':
        before, after = x['before_body'], x['after_body']
        bp, ap = x['before_pin'], x['after_pin']
    else:
        before, after = x['parent_body'], x['candidate_body']
        bp, ap = x['parent_pin'], x['candidate_pin']
    assert body_pin(before) == bp and body_pin(after) == ap
    diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True)))
    assert diff == x['full_diff']
    return before, after


def functions(text):
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(text).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def main():
    freeze_path = B / 'source-freeze03.json'
    assert pin(freeze_path) == dict(bytes=63119, sha256='ed5cb88a99b8034d3eddf1e269de35d5704753153b4c9e51bdd84c4c021f583f')
    f = load('source-freeze03.json')
    assert len(f['sources']) == 253 and len(f['product_sources']) == 10
    checked = {}
    for name, expected in f['sources'].items():
        assert pin(R / name) == expected, name
        checked[name] = expected
    for name, expected in f['product_sources'].items():
        assert checked[name] == expected
    for expected in f['selected_tools'].values():
        assert pin(expected['path']) == {k: expected[k] for k in ('bytes', 'sha256')}
    assert f['functional_predicates'] == 42 and f['excluded_MAX4118_predicates'] == 1
    assert f['previous_freeze'] == pin(B / 'source-freeze02.json')
    old_receipt = load('source-only-peer-rx-findings01.json')
    assert old_receipt['findings'][0]['id'] == 'V25_CACHE_FAULT_WITNESS_OPTIONAL_SKIP'
    for record in ('rx-source-review01/source-readback01.json', 'rx-source-review02/source-readback02.json'):
        for row in load(record)['snapshots']:
            assert pin(row['snapshot']) == {k: row[k] for k in ('bytes', 'sha256')}

    initial = load('source-freeze01.json')['product_sources']
    second = load('source-freeze02.json')['product_sources']
    bench_name = 'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v25.py'
    arch_name = 'sw/tests/test_pcie_gen3_integrity_v25_architecture.py'
    assert {n for n in initial if initial[n] != second[n]} == {bench_name, arch_name}
    assert {n for n in initial if second[n] != f['product_sources'][n]} == {arch_name}
    cache02 = load('cache-quarantine-source-supplement02.json')
    assert not cache02['hdl_tests_executed'] and len(cache02['bridges']) == 2
    cache_bodies = {}
    for bridge in cache02['bridges']:
        before, after = full_bridge(bridge, 'cache')
        name = str(Path(bridge['after_path']).relative_to(R)) if Path(bridge['after_path']).is_absolute() else bridge['after_path']
        assert body_pin(before) == initial[name] and body_pin(after) == second[name]
        cache_bodies[name] = (before, after)
    gate03 = load('cache-observer-gate-supplement03.json')
    assert not gate03['hdl_run']
    assert gate03['before_body'] == cache_bodies[arch_name][1]
    assert body_pin(gate03['before_body']) == gate03['before'] == second[arch_name]
    assert body_pin(gate03['after_body']) == gate03['after'] == f['product_sources'][arch_name]
    assert ''.join(difflib.unified_diff(gate03['before_body'].splitlines(True), gate03['after_body'].splitlines(True))) == gate03['full_diff']
    assert (R / arch_name).read_text() == gate03['after_body']
    assert (R / bench_name).read_text() == cache_bodies[bench_name][1]

    before_funcs = functions(cache_bodies[bench_name][0])
    after_funcs = functions(cache_bodies[bench_name][1])
    bench_changes = {n for n in before_funcs if before_funcs[n] != after_funcs[n]}
    assert bench_changes == {'cache_fault_write_and_new_epoch_reuse'}, bench_changes
    before_funcs = functions(gate03['before_body'])
    after_funcs = functions(gate03['after_body'])
    gate_changes = {n for n in before_funcs if before_funcs[n] != after_funcs[n]}
    assert gate_changes == {'test_actual_all_public_transactions_with_command_and_bank_observers'}
    arch = gate03['after_body']
    bench = cache_bodies[bench_name][1]
    for required in (
        'candidate.framer.command_valid===1\'b1',
        'candidate.framer.fault_now===1\'b1',
        'candidate.framer.command_verdict_enable & candidate.framer.command_verdict_value',
        'v25_cache_before[v25_cache_i]=candidate.framer.slot_verdict[v25_cache_i]',
        '#0.002;',
        'candidate.framer.slot_verdict[v25_cache_i] !== v25_cache_before[v25_cache_i]',
        'V25_FAULT_COMMAND_CACHE_QUARANTINE',
        'assert cache, \'Mandatory V25 old-command cache observer was not visible at runtime\'',
        'assert cache_counts[0] == 8 and min(cache_counts[1:]) >= 8, cache_counts',
        'cache_quarantine_counts=cache_counts',
        'observer(), header_observer(), cache_observer()',
    ):
        assert required in arch, required
    assert 'serial_words(bytes(24) + wire_dllp(good) + token + bytes(2048))' in bench
    assert "'V25_ACTUAL_INVALID_CACHE_WRITE_WITNESS'" in bench
    assert 'assert fault_steps >= 8 and invalid_changes >= 8' in bench

    # Reconstruct the complete RTL from the unchanged V23 baseline in both directions.
    ledger = load('source-bridge-draft02.json')
    original = (R / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v').read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == ledger['baseline_sha256']
    generated = original
    assert len(ledger['edits']) == 14
    for edit in ledger['edits']:
        assert generated.count(edit['before']) == edit['count']
        generated = generated.replace(edit['before'], edit['after'])
    assert generated == (R / ledger['candidate']['path']).read_text()
    for edit in reversed(ledger['edits']):
        assert generated.count(edit['after']) == edit['count']
        generated = generated.replace(edit['after'], edit['before'])
    assert generated == original

    support_records = []
    for version in ('02', '03'):
        bridges = load('support-derivation' + version + '.json')['bridges']
        assert len(bridges) == 2
        for bridge in bridges:
            before, after = full_bridge(bridge, 'support')
            assert Path(bridge['parent']).read_text() == before
            assert Path(bridge['candidate']).read_text() == after
            assert functions(before) == functions(after)
            # Exact complete bodies and diff contain only fixed pin/path/version replacements.
            a, b = ast.parse(before), ast.parse(after)
            old_tries = [ast.dump(n, include_attributes=False) for n in a.body if isinstance(n, ast.Try)]
            new_tries = [ast.dump(n, include_attributes=False) for n in b.body if isinstance(n, ast.Try)]
            assert old_tries == new_tries
            support_records.append(dict(parent=bridge['parent'], candidate=bridge['candidate'],
                                        before=bridge['parent_pin'], after=bridge['candidate_pin']))
    launcher = B / 'launch_controls03.py'
    detacher = B / 'detach_controls03.py'
    for p in (launcher, detacher):
        text = p.read_text()
        assert "('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')" in text
        assert "source-only-peer-rx03.json" in text
        assert "source-freeze03.json" in text
    assert "str(R/'.venv/bin/python')" in detacher.read_text()
    assert not (B / 'status01.json').exists()
    assert not Path('/dev/shm/nssoc-integrity-v25-full-controls01').exists()

    snapshots = B / 'rx-source-review03'
    snapshots.mkdir(exist_ok=False)
    snapshot_records = []
    for p in [*(R / n for n in f['product_sources']), freeze_path, launcher, detacher,
              B / 'cache-quarantine-source-supplement02.json', B / 'cache-observer-gate-supplement03.json',
              B / 'support-derivation03.json']:
        target = snapshots / (p.name + '.snapshot.txt')
        with target.open('xb') as output:
            output.write(p.read_bytes())
        snapshot_records.append(dict(original=str(p), snapshot=str(target), **pin(target)))
    readback = snapshots / 'source-readback03.json'
    readback.write_text(json.dumps(dict(status='ALL253_INPUTS_TEN_PRODUCTS_REHASHED_ADDITIVE_SOURCE_READ',
        freeze=pin(freeze_path), inputs=checked, snapshots=snapshot_records), indent=2) + '\n')
    result = dict(status='PASS_SOURCE_ONLY_V25_REGISTERED_COMMAND_IMPLEMENTATION', findings=[],
        freeze=pin(freeze_path), launcher=pin(launcher), detacher=pin(detacher),
        source_pins=f['product_sources'], source_readback=pin(readback),
        prior_full_source_review=pin(B / 'source-only-peer-rx-findings01.json'),
        prior_review_method=pin(B / 'review_source_rx01.py'),
        previous_additive_readback=pin(B / 'rx-source-review02/source-readback02.json'),
        additive_sources={n: pin(B / n) for n in ('cache-quarantine-source-supplement02.json',
            'cache-observer-gate-supplement03.json','support-derivation02.json','support-derivation03.json')},
        complete_framer_inverse_edits=14, support_complete_bridges=support_records,
        resolved_findings=[dict(id='V25_CACHE_FAULT_WITNESS_OPTIONAL_SKIP',
            resolution='Previous-beat bytes24..31 good DLLP command coincides with actual next-beat byte32 parser fault. Pre-edge valid/enabled/active/fault and old good verdict are bound to the real cache; post-NBA changed bits are counted and all ownership/frontiers must clear. Eight distinct epoch tests preserve the independent fresh-owner byte scoreboard.'),
            dict(id='MANDATORY_OUTER_CACHE_OBSERVER_GATE',
                 resolution='The architecture positive must find the runtime V25_CACHE_QUARANTINE report, exactly eight epochs and at least eight actual fault-command/cache-change events; absence and zero counters reject. Direct-profile optional visibility no longer substitutes for the mandatory architecture gate.'),
            dict(id='UNKNOWN_EXTERNAL_CONTROL_PENDING_OWNERSHIP',
                 resolution='Actual command capture preserves old pending validity when procedural enabled is unknown, with known reset/epoch/fault priority retained. Ten X/Z inhibit hold/resume cases and two fault fallthrough cases are planned, not yet executed.')],
        reviewed_scope=old_receipt['source_scope'],
        profile_clarification='RING_DWORDS=16/MAX_ENCODED_BYTES=18 is an explicit stress override. Automatic sizing for MAX18 gives32. This is not evidence of the minimum automatically sized profile. The separate normal64 burst profile is also planned.',
        required_actual_controls=dict(selected_pytest=42, excluded_MAX4118=1, public_case_identities=19,
            current_mutants=dict(inherited_public=12, command_wrapper=8, block=2, component=11),
            historical_not_rerun='Five further V23 header faults and observer-negative; retained old cycle-miter evidence is not current general V25 cycle equivalence.'),
        planned_structural_boundary='Before any timing/adoption claim, actual mapped command Q must separate parser from all slot/verdict/cache writes, with payload bypass and writer/frontier/ending ownership checks.',
        method=pin(__file__),
        scope='Independent complete-source review ancestry plus exact additive full-body/AST/hash audit only. No producer/test imports or execution, no compiler, HDL, EDA, native or process signal. This gate permits only the frozen functional campaign after fresh resource/identity preflight; it does not assert functional success, mapping, timing, physical closure or top-level adoption.')
    output = B / 'source-only-peer-rx03.json'
    with output.open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], findings=[], result=pin(output),
                          input_count=len(checked), products=len(f['product_sources']),
                          launcher=pin(launcher), detacher=pin(detacher)), indent=2))


if __name__ == '__main__':
    main()
