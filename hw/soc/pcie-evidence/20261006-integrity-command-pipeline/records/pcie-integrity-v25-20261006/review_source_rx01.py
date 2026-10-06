#!/usr/bin/env python3
"""Independent frozen V25 source review; never imports producer or test code."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

R = Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B = R / 'hw/soc/out/pcie-integrity-v25-20261006'
S = B / 'rx-source-review01'


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def snapshot(path):
    return (S / (Path(path).name + '.snapshot.txt')).read_text()


def funcs(text):
    return {n.name: ast.dump(n, include_attributes=False)
            for n in ast.parse(text).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def main():
    readback = json.loads((S / 'source-readback01.json').read_text())
    assert len(readback['inputs']) == 212
    for row in readback['snapshots']:
        assert pin(row['snapshot']) == {k: row[k] for k in ('bytes', 'sha256')}
    freeze = json.loads(snapshot('source-freeze01.json'))
    assert len(freeze['product_sources']) == 10
    for name, expected in freeze['product_sources'].items():
        assert pin(S / (Path(name).name + '.snapshot.txt')) == expected
    bridges = []
    for file in ('source-derivation01.json', 'support-derivation01.json'):
        for bridge in json.loads(snapshot(file))['bridges']:
            before, after = bridge['parent_body'], bridge['candidate_body']
            assert Path(bridge['parent']).read_text() == before
            assert pin(bridge['parent']) == bridge['parent_pin']
            assert snapshot(bridge['candidate']) == after
            assert pin(S / (Path(bridge['candidate']).name + '.snapshot.txt')) == bridge['candidate_pin']
            diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                              fromfile=bridge['parent'], tofile=bridge['candidate']))
            assert diff == bridge['full_diff']
            if bridge.get('version_only'):
                assert before.replace('v23', 'v25').replace('V23', 'V25') == after
            bridges.append(dict(parent=bridge['parent'], candidate=bridge['candidate'],
                                before=bridge['parent_pin'], after=bridge['candidate_pin'],
                                full_body_and_diff_equal=True))
    assert len(bridges) == 7
    ledger = json.loads(snapshot('source-bridge-draft02.json'))
    old = (R / 'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v').read_text()
    assert hashlib.sha256(old.encode()).hexdigest() == ledger['baseline_sha256']
    new = snapshot(ledger['candidate']['path'])
    forward = old
    for edit in ledger['edits']:
        assert forward.count(edit['before']) == edit['count']
        forward = forward.replace(edit['before'], edit['after'])
    assert forward == new
    inverse = new
    for edit in reversed(ledger['edits']):
        assert inverse.count(edit['after']) == edit['count']
        inverse = inverse.replace(edit['after'], edit['before'])
    assert inverse == old and len(ledger['edits']) == 14
    generator = ast.parse(snapshot('generate_pcie_integrity_command_v25.py'))
    constants = {n.targets[0].id: n.value.value for n in generator.body
                 if isinstance(n, ast.Assign) and len(n.targets) == 1
                 and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Constant)}
    for name in ('DECLARATIONS', 'CAPTURE', 'APPLY'):
        assert constants[name] in new
    assert constants['OLD_WRITES'] in old and constants['OLD_WRITES'] not in new
    assert 'if(enabled) begin\n       command_valid<=0;' in constants['CAPTURE']
    assert 'else command_valid<=0' not in constants['CAPTURE']
    assert 'if(enabled && command_valid) begin' in constants['APPLY']

    bench = snapshot('test_soc_pcie_gen3_continuous_rx_integrity_v25.py')
    oldbench = (R / 'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py').read_text()
    first18 = oldbench.replace('V23', 'V25').replace('v23', 'v25')
    assert bench.startswith(first18)
    cases = [n.name for n in ast.parse(bench).body
             if isinstance(n, ast.AsyncFunctionDef) and n.decorator_list]
    assert len(cases) == 19
    assert funcs(bench)['crc4'] == funcs(oldbench)['crc4']
    for name in ('tlp', 'wire_tlp', 'dllp', 'wire_dllp', 'serial_words'):
        assert funcs(bench)[name] == funcs(oldbench)[name]
    def ports(text):
        return next(ast.dump(n, include_attributes=False) for n in ast.parse(text).body
                    if isinstance(n, ast.ClassDef) and n.name == 'Ports')
    assert ports(bench) == ports(oldbench)
    arch = snapshot('test_pcie_gen3_integrity_v25_architecture.py')
    generated = (B / 'static-test-construction01/wrapper/soc_pcie_gen3_continuous_rx_integrity_v25.v').read_text()
    assert 'v22_fault_step_events' not in arch and 'v22_invalid_difference_events' not in arch
    assert 'v22_fault_step_events' not in generated and 'v22_invalid_difference_events' not in generated
    assert "if hasattr(d, 'v22_fault_step_events'):" in bench
    assert "if hasattr(d, 'v22_fault_step_events'):" in first18
    collection = (B / 'collection01.log').read_text()
    assert '42/43 tests collected (1 deselected)' in collection
    assert len([line for line in collection.splitlines() if '::test_' in line]) == 42
    construction = json.loads((B / 'static-test-construction01/result.json').read_text())
    assert construction['no_compiler_or_simulation'] and len(construction['files']) == 12
    for path, expected in construction['files'].items():
        assert pin(R / path) == expected
    oldsupport = json.loads(snapshot('support-derivation01.json'))['bridges'][0]['parent_body']
    support = snapshot('launch_controls01.py')
    for name in ('pin', 'shared_floor', 'limits'):
        assert funcs(oldsupport)[name] == funcs(support)[name]
    a = next(n for n in ast.parse(oldsupport.replace('V24', 'V25').replace('v24', 'v25')).body if isinstance(n, ast.Try))
    b = next(n for n in ast.parse(support).body if isinstance(n, ast.Try))
    assert ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)
    finding = dict(id='V25_CACHE_FAULT_WITNESS_OPTIONAL_SKIP', severity='blocking_source_control_coverage',
        file='sw/tests/test_pcie_gen3_integrity_v25_architecture.py',
        detail='The architecture wrapper does not emit either inherited v22 fault/cache-change counter. The public cache-fault test conditionally skips all actual fault-edge cache-change checks, so its eight epochs alone do not prove a V25 pending-command cache write was invalidated. The writer now applies an OLD command; the old same-parser-step stimulus is not that witness.',
        required='Add a V25-specific pre/post-NBA observer of real pending OLD command and cache changes at the fault edge; shift the stimulus so that command contains an actual good verdict, require eight actual changing epochs, and retain the independent fresh-owner byte scoreboard. Preserve source01 and publish an additive freeze before launch.')
    receipt = dict(status='FINDINGS_V25_SOURCE01_LAUNCH_HELD', findings=[finding],
        freeze=readback['freeze'], source_readback=pin(S / 'source-readback01.json'),
        full_body_bridges=bridges, complete_framer_inverse_edits=14,
        public_cases=cases, unchanged_scalar_oracle_and_ports_class=True,
        retained_first18_cases_after_label_change=True,
        collection_only=dict(selected=42, excluded_MAX4118=1, log=pin(B / 'collection01.log')),
        static_hdl_construction_only=dict(files=12, record=pin(B / 'static-test-construction01/result.json')),
        source_scope=['Complete writer command fields and all seven slot writers plus verdict/cache input relocation reviewed.',
                      'Reserved occupancy, parser math/default frontier, bank writers, descriptor transfer and fault/public handshake priority remain V23 except exact declared one-stage visibility.',
                      'External X/Z enabled/active ownership holds are now explicitly preserved; component source contains ten hold/resume and two unknown-fault fallthrough checks, not an arbitrary-state full-framer equivalence claim.',
                      'Nominal comparison restricts ready1/no fault/both active to +1 output while preserving parser/event cadence; independent byte transactions handle stalls and fault discard.',
                      'Ending application and command emptiness are separate from parser ending. Pending reset/start/flush/abort/bad-block/overflow tests and named new command mutants are source-reviewed but unexecuted.',
                      'The 12 inherited public, eight command-wrapper, two block and eleven component mutants are current planned controls; additional old V23 header/miter negatives remain historical unless separately run.',
                      'Selected tools, source pins, lexical venv and Python env sanitation bind the detached CPU6/2GiB campaign; same inherited owner try/post-wait/post-context code and floors are preserved.'],
        launcher=pin(S / 'launch_controls01.py.snapshot.txt'),
        detacher=pin(S / 'detach_controls01.py.snapshot.txt'), method=pin(__file__),
        scope='Independent source/hash/full-text/AST review only. No producer/test function imported or executed; no compiler, HDL, EDA or native launched. This is not a passing launch gate or functional/timing/adoption evidence.')
    (B / 'source-only-peer-rx-findings01.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(result=pin(B / 'source-only-peer-rx-findings01.json'), findings=1,
                          inputs=212, products=10, bridges=7, framer_edits=14), indent=2))


if __name__ == '__main__':
    main()
