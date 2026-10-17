# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-only composition; no simulator import, deck dispatch, or active reads.

Two explicit polarity alternatives are retained. Neither is selected until the
separate loaded tuning and pump-reachability contract has actual evidence.
"""
from collections import Counter, defaultdict
from pathlib import Path
import difflib
import hashlib
import json
import re

R = Path.cwd()
B = Path(__file__).resolve().parent
N = Path('/dev/shm/nssoc-vco-v6-divider-tail115-v1-sixteenthstep-06-01')
O = R / 'hw/soc/out/pcie-tail115-pll-structure-20261006'
P = R / 'hw/soc/analog/pcie'
MODELS = {'npn13g2': 4, 'rppd': 3, 'cap_cmim': 2, 'sg13_hv_pmos': 4,
          'sg13_hv_nmos': 4, 'sg13_lv_pmos': 4, 'sg13_lv_nmos': 4,
          'ptap1': 2, 'ntap1': 2}
BODY_PORTS = ['body_substrate', 'wire_cref', 'div_body_substrate', 'div_wire_cref']
CHAIN = 'nssoc_pll_feedback_vco_v6_divider_tail115_v1_wire_v1'
INPUT_PINS = {
    str(N / 'result.json'): dict(bytes=426434, sha256='1428ee18fc41a19ff5b5a92c3cce2803f1c2fbbe29ce08c6a8c95c9610cf2ded'),
    str(O / 'result01.json'): dict(bytes=50969, sha256='f4b68b6ad9cc77823ddde789c311241bebee8a61959d8e3e36b7c57b118b2b86'),
}


def pin(path):
    path = Path(path)
    with path.open('rb') as f:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


def write_json(path, data):
    assert not path.exists(), path
    path.write_text(json.dumps(data, indent=2) + '\n')


def definitions(texts):
    result = {}
    for text in texts.values():
        active = None
        for line in text.lower().splitlines():
            words = line.split()
            if not words or words[0].startswith('*'):
                continue
            if words[0] == '.subckt':
                assert active is None and words[1] not in result
                active = words[1]
                assert len(words[2:]) == len(set(words[2:]))
                result[active] = (words[2:], [])
            elif words[0] == '.ends':
                assert active and (len(words) == 1 or words == ['.ends', active])
                active = None
            else:
                assert active
                result[active][1].append(words)
        assert active is None
    return result


def expand(defs, root):
    rows, wires = [], []

    def walk(model, path, nets, stack=()):
        assert model not in stack
        ports, body = defs[model]
        assert len(ports) == len(nets)
        mapping, seen = dict(zip(ports, nets)), set()

        def node(name):
            return mapping.get(name, path + '.' + name)

        for words in body:
            assert words[0] not in seen
            seen.add(words[0])
            here = path + '.' + words[0]
            if words[0][0] in ('r', 'c'):
                assert len(words) == 4
                wires.append(dict(path=here, kind=words[0][0], nets=[node(x) for x in words[1:3]], value=words[3]))
                continue
            assert words[0].startswith('x')
            if words[-1] in defs:
                walk(words[-1], here, [node(x) for x in words[1:-1]], stack + (model,))
                continue
            matches = [(m, n) for m, n in MODELS.items() if len(words) > n + 1 and words[n + 1] == m]
            assert len(matches) == 1, words
            model_name, count = matches[0]
            params = dict(x.split('=') for x in words[count + 2:])
            assert len(params) == len(words[count + 2:])
            rows.append(dict(path=here, model=model_name, nets=[node(x) for x in words[1:count + 1]], params=params))

    model, path, nets = root
    walk(model, path, nets)
    assert len(rows) == len({x['path'] for x in rows})
    assert len(wires) == len({x['path'] for x in wires})
    return rows, wires


def prefixed(row):
    # Only hierarchy-local nodes move; all public nets retain their exact names.
    return dict(row, path='xloop.' + row['path'],
                nets=['xloop.' + x if x.startswith('xchain.') else x for x in row['nets']])


def by_path(rows):
    return {x['path']: x for x in rows}


def observation_vectors(rows, fixture):
    vectors = [f'v({x})' for x in sorted({n for r in rows for n in r['nets']} - {'0'})]
    for line in fixture:
        if line.lower().startswith('v'):
            vectors.append('i(' + line.split()[0].lower() + ')')
    for node in ['clkp', 'clkn', 'qp', 'qn', 'fb', 'fbbar', 'vctrl', 'reference', 'reset', 'up', 'down']:
        if f'v({node})' not in vectors:
            vectors.append(f'v({node})')
    for row in rows:
        path, model = row['path'], row['model']
        if model == 'npn13g2':
            vectors += ['@q.' + path + '.qnpn13g2[ic]', 'v(' + path + '.t)']
        elif model.startswith('sg13_'):
            vectors.append('@n.' + path + '.n' + model + '[ids]')
        elif model == 'rppd':
            vectors.append('v(' + path + '.dt)')
    assert len(vectors) == len(set(vectors))
    return vectors


def safety_contract(row):
    model = row['model']
    common = dict(path=row['path'], model=model, terminals=row['nets'], all_capture_finite_required=True)
    if model == 'npn13g2':
        return dict(common, rule='inherited_hbt', settled_vce_min_v=0.4, all_capture_vce_max_v=1.6,
                    all_capture_abs_ic_per_nx_max_a=0.003, startup_off=1)
    if model.startswith('sg13_'):
        return dict(common, rule='inherited_mos', all_pair_terminal_abs_max_v=1.5 if '_lv_' in model else 3.3,
                    all_capture_abs_drain_per_um_max_a=0.002, inherited_geometry_range_required=True)
    if model in ('rppd', 'cap_cmim'):
        return dict(common, rule='inherited_passive', first_two_terminal_abs_max_v=3.3)
    assert model in ('ptap1', 'ntap1')
    return dict(common, rule='inherited_finite_contact', all_capture_terminal_abs_max_v=3.3,
                inferred_ohmic_current_reported=True, contact_current_qualified=False)


def main():
    assert not (B / 'composition01.json').exists()
    for path, expected in INPUT_PINS.items():
        assert pin(path) == expected
    prior = json.loads((O / 'result01.json').read_text())
    snapshot = O / 'active-immutable-fields-snapshot01.json'
    assert pin(snapshot) == prior['static_active_fields_snapshot']
    old = json.loads(snapshot.read_text())
    saved = json.loads((N / 'result.json').read_text())
    assert saved['status'] == 'PASS_NATIVE_LOADED_FEEDBACK_SCREEN'
    inputs = {**INPUT_PINS, str(snapshot): pin(snapshot)}
    # Bind immutable closed/static ancestors, never the changing PLL result.
    for path, expected in prior['inputs'].items():
        assert pin(path) == expected
        inputs[path] = expected
    for path, expected in saved['inputs'].items():
        assert pin(path) == expected
        inputs[path] = expected
    source_paths = [N / x for x in re.findall(r'^\.include "([^"]+)"', (N / 'bench.cir').read_text(), re.M)]
    source_paths += [P / 'pll_pfd_charge_pump_hv_v1.spice']
    texts = {p.name: p.read_text() for p in source_paths}
    assert len(texts) == len(source_paths)
    for p in source_paths:
        inputs[str(p)] = pin(p)
    baseline = (P / 'pll_loop_hbt_v1.spice').read_text()
    assert hashlib.sha256(baseline.encode()).hexdigest() == '2c1d0268da591654679e1c64bc2d811df660de1ca9b8ba0eda271060454233ec'
    inputs[str(P / 'pll_loop_hbt_v1.spice')] = pin(P / 'pll_loop_hbt_v1.spice')
    defs = definitions(texts)
    before, before_rc = expand(defs, saved['config']['roots'][0])
    assert by_path(before) == by_path(saved['devices']) and len(before) == 455
    expected_chain, expected_rc = list(map(prefixed, before)), list(map(prefixed, before_rc))
    old_other = [x for x in old['devices'] if not x['path'].startswith('xloop.xchain.')]
    assert len(old_other) == 115
    original_lines = [x for x in baseline.splitlines() if x and not x.startswith('*')]
    old_ports = original_lines[0].split()[2:]
    assert old_ports == ['ref', 'reset', 'clearb', 'clkp', 'clkn', 'qp', 'qn', 'fb', 'fbbar', 'up', 'down', 'vctrl', 'vco_avdd', 'div_avdd', 'core_vdd', 'avss', 'sub']
    assert original_lines[2] == 'XDET fb ref reset up down vctrl div_avdd avss sub nssoc_pll_pfd_cp_hv_v1'
    fixture = list(old['config']['fixture'])
    fixture += [x for x in saved['config']['fixture'] if x.split()[0] in ('VBODY', 'VWREF', 'VDIVBODY', 'VDIVWREF', 'CLOAD_CLKP', 'CLOAD_CLKN')]
    assert len(fixture) == 12 and not any(x.startswith('VCTRL ') for x in fixture)
    assert [x for x in fixture if x.startswith('CLOAD_')] == ['CLOAD_CLKP clkp 0 50f', 'CLOAD_CLKN clkn 0 50f']
    assert len(set(BODY_PORTS)) == 4 and all(x not in ('avss', 'sub', '0') for x in BODY_PORTS)
    rows_by_variant, bridges = {}, {}
    for label, detector in [('negative', 'fb ref'), ('positive', 'ref fb')]:
        top = f'nssoc_pll_tail115_connected570_{label}_v1'
        lines = list(original_lines)
        lines[0] = '.subckt ' + top + ' ' + ' '.join(old_ports + BODY_PORTS)
        lines[1] = 'XCHAIN ' + ' '.join(['vctrl', 'clearb', 'clkp', 'clkn', 'qp', 'qn', 'fb', 'fbbar', 'vco_avdd', 'div_avdd', 'core_vdd', 'avss', 'sub'] + BODY_PORTS) + ' ' + CHAIN
        lines[2] = 'XDET ' + detector + ' reset up down vctrl div_avdd avss sub nssoc_pll_pfd_cp_hv_v1'
        lines[-1] = '.ends ' + top
        assert lines[3:-1] == original_lines[3:-1]
        text = '* SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\n* SPDX-License-Identifier: CERN-OHL-W-2.0\n* Source-only candidate; polarity NOT SELECTED. Actual loaded tuning is prerequisite.\n* Four independent body/wire reference ports. No internal ideal sources.\n' + '\n'.join(lines) + '\n'
        name = f'loop-{label}01.spice'
        path = B / name
        assert not path.exists()
        path.write_text(text)
        root = [top, 'xloop', old['config']['roots'][0][2] + BODY_PORTS]
        rows, wires = expand(definitions({**texts, name: text}), root)
        assert len(rows) == 570 and Counter(x['kind'] for x in wires) == {'r': 1271, 'c': 1414}
        assert by_path([x for x in rows if x['path'].startswith('xloop.xchain.')]) == by_path(expected_chain)
        assert by_path(wires) == by_path(expected_rc)
        others = old_other if label == 'negative' else [dict(x, nets=[{'fb': 'reference', 'reference': 'fb'}.get(n, n) for n in x['nets']]) for x in old_other]
        assert by_path([x for x in rows if not x['path'].startswith('xloop.xchain.')]) == by_path(others)
        assert Counter(x['model'] for x in rows)['npn13g2'] == 64
        assert sum(x['model'] in ('ptap1', 'ntap1') for x in rows) == 31
        vectors = observation_vectors(rows, fixture)
        safety = [safety_contract(x) for x in rows]
        terminals = defaultdict(list)
        for row in rows:
            for index, node in enumerate(row['nets']):
                terminals[node].append(dict(path=row['path'], terminal_index=index))
        for wire in wires:
            for index, node in enumerate(wire['nets']):
                terminals[node].append(dict(path=wire['path'], terminal_index=index))
        rows_by_variant[label] = dict(root=root, source=pin(path), devices=rows, wire_elements=wires,
            model_counts=dict(Counter(x['model'] for x in rows)), safety_records=safety,
            startup_hbt_paths=[x['path'] for x in rows if x['model'] == 'npn13g2'],
            observation_vectors=vectors, vector_count=len(vectors), all_terminal_net_census=dict(sorted(terminals.items())),
            model_terminal_count=sum(len(x['nets']) for x in rows), unique_model_nets=len({n for x in rows for n in x['nets']}),
            body_reference_ports=BODY_PORTS, fixture=fixture, polarity_selected=False)
        bridges[label] = dict(parent=str(P / 'pll_loop_hbt_v1.spice'), parent_pin=pin(P / 'pll_loop_hbt_v1.spice'),
            target=str(path), target_pin=pin(path), original_complete_text=baseline, resulting_complete_text=text,
            full_unified_diff=''.join(difflib.unified_diff(baseline.splitlines(True), text.splitlines(True))),
            unchanged_filter_lines=lines[3:-1], unchanged_pfd_cp_source=pin(P / 'pll_pfd_charge_pump_hv_v1.spice'))
    # Snapshot exact include bytes locally without touching either native tree.
    include_dir = B / 'includes01'
    include_dir.mkdir()
    for name, text in texts.items():
        (include_dir / name).write_text(text)
        assert pin(include_dir / name) == pin(next(p for p in source_paths if p.name == name))
    result = dict(status='SOURCE_ONLY_570_COMPOSITION_NOT_SIMULATED_POLARITY_UNSELECTED', method=pin(__file__),
        inputs=inputs, include_sources={str(include_dir / n): pin(include_dir / n) for n in texts},
        components=dict(physical_vco=62, physical_divider=91, schematic_feedback=302, schematic_pfd=102, schematic_pump=10, schematic_filter=3),
        variants=rows_by_variant, safety_implementation_pending=True, native_deck_and_runner_not_created=True,
        active539_inputs_unchanged=True, qualification=False,
        scope='Exact source/graph/port/census construction only; no native models, controls or testbench simulation. Safety entries are inherited predicate contracts, not measured passes. Both polarity alternatives remain unselected.')
    assert all(pin(p) == v for p, v in inputs.items())
    write_json(B / 'source-bridges01.json', bridges)
    write_json(B / 'composition01.json', result)
    print(json.dumps(dict(composition=pin(B / 'composition01.json'), counts={k: dict(devices=len(v['devices']), vectors=v['vector_count'], model_terminals=v['model_terminal_count'], nets=v['unique_model_nets']) for k, v in rows_by_variant.items()})))


if __name__ == '__main__':
    main()
