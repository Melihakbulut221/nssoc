# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent source-only verification; never imports or executes producers."""
import ast
import datetime
import hashlib
import json
from pathlib import Path

B = Path(__file__).resolve().parent
ROOT = B.parents[3]

def pin(path):
    p = Path(path)
    with p.open('rb') as f:
        return {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}

def main():
    freeze_path = B / 'geometry-source-freeze.json'
    assert pin(freeze_path) == {'bytes': 308462, 'sha256': 'ec63a2040ca3e9fccebbc0a2d7ed95613bd2844d902540f24ca600844f5b1900'}
    f = json.loads(freeze_path.read_text())
    assert len(f['inputs']) == 1337
    for p, expected in f['inputs'].items():
        assert pin(p) == expected, p
    for p, expected in f['producer_sources'].items():
        assert pin(p) == expected, p
    substitutions = [
        ('v8-cap-v1', 'v7-compact-v2'),
        ('v8_cap_v1', 'v7_compact_v2'),
        ('V8_CAP_V1', 'V7_COMPACT_V2'),
        ('V8_CAP24', 'V7'),
        ('PASS_ACTUAL_CAP24_TWO_MIM_DELTA_POWER_AND_SIX_GEOMETRY_CONTROLS',
         'PASS_ACTUAL_COMPACT_INTRINSICS_POWER_AND_FOUR_GEOMETRY_CONTROLS'),
        ('PASS_INDEPENDENT_SAVED_CAP24_V1_NATIVE_RESULT',
         'PASS_INDEPENDENT_SAVED_COMPACT_V2_NATIVE_RESULT'),
        ('4361db967f0df1d340360f6b50461274b8a36cb49d208072a911cfd2077c78c1',
         'db400e586cadbedbea9ec8aec5466c0eba4789e262c90ebd0d321a1c2cbcf579'),
    ]
    bridges = json.loads((B / 'source-bridge01.json').read_text())
    assert len(bridges) == 7
    verified = []
    for r in bridges:
        old, new = Path(r['before']['path']), Path(r['after']['path'])
        for p, e in [(old, r['before']), (new, r['after'])]:
            assert pin(p) == {k: e[k] for k in ('bytes', 'sha256')}
        before, after = old.read_text(), new.read_text()
        assert ''.join(o['before'] for o in r['opcodes']) == before
        assert ''.join(o['after'] for o in r['opcodes']) == after
        for o in r['opcodes']:
            if o['tag'] == 'equal':
                assert o['before'] == o['after']
        inverse = after
        for a, b in substitutions:
            inverse = inverse.replace(a, b)
        assert inverse == before, new
        assert ast.dump(ast.parse(inverse), include_attributes=False) == ast.dump(ast.parse(before), include_attributes=False)
        verified.append({'before': str(old), 'after': str(new), 'after_pin': pin(new),
                         'full_ledger_forward_inverse': True, 'independent_narrow_inverse': True})
    old_b = Path(bridges[0]['before']['path']).parent
    assert (B / 'native_unsimplified.lvs').read_bytes() == (old_b / 'native_unsimplified.lvs').read_bytes()
    checker = ROOT / 'hw/soc/flow/check_pcie_clock_div4_v7_v2.py'
    assert pin(checker)['sha256'] == '24c89628c6d61226344214e077b5fa535c5570e4a7853fbd109e8cb1b1fcd163'
    names = ['require', 'atomic', 'lifecycle', 'limits', 'scratch_bytes', 'guard_resources', 'execute']
    funcs = {n.name: n for n in ast.parse(checker.read_text()).body if isinstance(n, ast.FunctionDef)}
    assert set(names) <= set(funcs)
    function_pins = {n: hashlib.sha256(ast.dump(funcs[n], include_attributes=False).encode()).hexdigest() for n in names}
    G = Path('/dev/shm/nssoc-div4-v8-cap-v1-layout-01')
    C = Path('/dev/shm/nssoc-div4-v8-cap-v1-checks-01')
    NP = B.parent / 'pcie-divider-v8-cap-v1-20261006/native-saved-peer-rx.json'
    native = json.loads(NP.read_text())
    assert native['status'] == 'PASS_INDEPENDENT_SAVED_CAP24_V1_NATIVE_RESULT' and native['findings'] == []
    assert native['checks'] == pin(C / 'result.json')
    assert native['geometry'] == pin(C / 'power-geometry.json')
    assert native['GDS'] == pin(G / 'nssoc_clock_div4_v8_cap_v1_layout.gds')
    result = json.loads((C / 'result.json').read_text())
    assert result['outputs'] == {n: pin(C / n)['sha256'] for n in result['outputs']}
    assert result['power_geometry_audit']['status'] == 'PASS_ACTUAL_CAP24_TWO_MIM_DELTA_POWER_AND_SIX_GEOMETRY_CONTROLS'
    assert f['original_source_and_all_intrinsic_models_unchanged'] is False
    fresh = ['/dev/shm/nssoc-div4-v8-cap-v1-wire-geometry-01', '/dev/shm/nssoc-div4-v8-cap-v1-wire-native-01']
    assert not any(Path(p).exists() for p in fresh)
    assert not (B / 'geometry-execution.json').exists()
    receipt = {
        'status': 'PASS_SOURCE_ONLY_DIVIDER_V8_CAP24_WIRE_GEOMETRY',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'freeze': pin(freeze_path), 'findings': [],
        'method': pin(__file__), 'source_bridge': pin(B / 'source-bridge01.json'),
        'source_pins': f['producer_sources'], 'verified_input_count': len(f['inputs']),
        'full_source_read': True, 'verified_whole_sources': verified,
        'exact_owned_checker_functions_ast_sha256': function_pins,
        'saved_native_peer': pin(NP), 'checks': pin(C / 'result.json'),
        'geometry': pin(C / 'power-geometry.json'),
        'GDS': pin(G / 'nssoc_clock_div4_v8_cap_v1_layout.gds'),
        'fresh_roots_absent_at_review': fresh,
        'review_observations': [
            'All seven complete producer bodies and native wrapper read. Independent narrow full-text inverse restricts changes to fresh roots/top, correct new GDS pin, and Cap24 native/source classification.',
            'Fresh flat unsimplified native extraction retains taps, disables simplify/combine/purge, exports actual LayoutToNetlist, and requires skipped-option logs. No comparison is claimed.',
            '725 leaves include 91 electrical primitives and 634 vias. All seven metal unions and all six via layers remain mandatory, including TopMetal2/TopVia2.',
            'Native geometry must prove all 283 terminals, 198 metal references, 85 separately preserved body terminals, 205 anchors and seven ports. No body shortcut or source-derived native graph substitutes for extraction.',
            'Complete 72-cluster partition requires 38 electrical nets, 37 actual metal conductors, one body-only net and 34 auxiliary clusters with no terminal, metal, or port. No purge or weakened bijection.',
            'Strict source/native parameter, location and bidirectional 38-net binding operates on current Cap24 metadata. Only XCP/XCN are changed 20 to 24 um; the other 89 intrinsic geometries, bias and connections remain inherited.',
            'Exact reviewed owner functions are cloned into private globals with CPU10, native 2 GiB, 80 MiB scratch plus 24 MiB reserve, 1 GiB entry and 512 MiB continuous floor; no healthy elapsed watchdog, terminal guards and exact child cleanup retained.',
        ],
        'limitations': [
            'Source-only permission for the fresh owned geometry campaign; no reviewed producer, native extraction, control or EDA operation executed by this peer.',
            'Counts beyond already completed standalone Cap24 native checks are predeclared requirements until the fresh geometry stages actually finish.',
            'No RC qualification, loaded division, clock-bank or full-PHY acceptance claim.',
        ],
    }
    target = B / 'geometry-source-only-peer.json'
    assert not target.exists()
    target.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'receipt': str(target), 'pin': pin(target), 'input_count': len(f['inputs'])}))

if __name__ == '__main__':
    main()
