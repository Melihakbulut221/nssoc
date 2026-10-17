# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite copied-source corruption controls; no circuit/model execution."""
from pathlib import Path
import copy
import json
import compose_source01 as c

B = Path(__file__).resolve().parent


def check(label, texts, loop, fixture, expected):
    rows, wires = c.expand(c.definitions({**texts, 'candidate.spice': loop}), expected['root'])
    assert c.by_path(rows) == c.by_path(expected['devices']), 'exact_570_model_graph'
    assert c.by_path(wires) == c.by_path(expected['wire_elements']), 'exact_2685_wire_graph'
    assert fixture == expected['fixture'], 'exact_external_fixture_and_loads'
    ports = c.definitions({'candidate.spice': loop})[expected['root'][0]][0]
    assert ports[-4:] == c.BODY_PORTS, 'four_distinct_boundary_ports'
    assert len(rows) == 570 and len(expected['safety_records']) == 570
    assert len(expected['startup_hbt_paths']) == 64
    return label


def replace_once(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)


def main():
    composition = json.loads((B / 'composition01.json').read_text())
    originals = {p.name: p.read_text() for p in (B / 'includes01').iterdir()}
    inputs = {str(p): c.pin(p) for p in [B / 'compose_source01.py', B / 'composition01.json', B / 'tuning-contract01.json', *(B / 'includes01').iterdir(), B / 'loop-negative01.spice', B / 'loop-positive01.spice']}
    outcomes = []
    for label in ['negative', 'positive']:
        expected = composition['variants'][label]
        check(label, originals, (B / f'loop-{label}01.spice').read_text(), expected['fixture'], expected)
        outcomes.append(dict(case=label + '_whole_graph_positive', passed=True, kind='positive'))
    expected = composition['variants']['negative']
    loop = (B / 'loop-negative01.spice').read_text()
    fixture = expected['fixture']
    mutations = []
    detector = next(x for x in loop.splitlines() if x.startswith('XDET '))
    mutations.append(('remove_actual_pfd_pump', originals, replace_once(loop, detector + '\n', ''), fixture, 'exact_570_model_graph'))
    mutations.append(('short_pump_to_ground', originals, replace_once(loop, 'up down vctrl div_avdd', 'up down 0 div_avdd'), fixture, 'exact_570_model_graph'))
    mutations.append(('wrong_feedback_net', originals, replace_once(loop, 'XDET fb ref', 'XDET fbbar ref'), fixture, 'exact_570_model_graph'))
    mutations.append(('wrong_polarity_for_named_variant', originals, replace_once(loop, 'XDET fb ref', 'XDET ref fb'), fixture, 'exact_570_model_graph'))
    chain = next(x for x in loop.splitlines() if x.startswith('XCHAIN '))
    mutations.append(('short_body_and_wire_boundaries', originals, replace_once(loop, chain, chain.replace(' div_body_substrate div_wire_cref ', ' div_body_substrate div_body_substrate ')), fixture, 'exact_2685_wire_graph'))
    mutations.append(('remove_one_50ff_load', originals, loop, [x for x in fixture if not x.startswith('CLOAD_CLKN ')], 'exact_external_fixture_and_loads'))
    filter_line = next(x for x in loop.splitlines() if x.startswith('XRHI '))
    mutations.append(('remove_upper_finite_filter', originals, replace_once(loop, filter_line + '\n', ''), fixture, 'exact_570_model_graph'))
    t = dict(originals)
    wire = next(x for x in t['divider-hybrid-open.spice'].splitlines() if x.startswith('R'))
    tokens = wire.split(); tokens[-1] = '999999'
    t['divider-hybrid-open.spice'] = replace_once(t['divider-hybrid-open.spice'], wire + '\n', ' '.join(tokens) + '\n')
    mutations.append(('actual_wire_resistance_corruption', t, loop, fixture, 'exact_2685_wire_graph'))
    t = dict(originals)
    device = next(x for x in t['divider-hybrid-open.spice'].splitlines() if ' l=11.5u ' in x)
    t['divider-hybrid-open.spice'] = replace_once(t['divider-hybrid-open.spice'], device, device.replace('l=11.5u', 'l=12.7u'))
    mutations.append(('revert_actual_second_tail', t, loop, fixture, 'exact_570_model_graph'))
    t = dict(originals)
    t['pll_pfd_charge_pump_hv_v1.spice'] = replace_once(t['pll_pfd_charge_pump_hv_v1.spice'], 'XPSOURCE source pb vdd vdd sg13_hv_pmos w=6.4u', 'XPSOURCE source pb vdd vdd sg13_hv_pmos w=6.5u')
    mutations.append(('actual_pump_geometry_corruption', t, loop, fixture, 'exact_570_model_graph'))
    for label, texts, body, fx, diagnostic in mutations:
        try:
            check(label, texts, body, fx, expected)
        except AssertionError as error:
            assert str(error) == diagnostic, (label, str(error), diagnostic)
            outcomes.append(dict(case=label, passed=True, kind='negative', actual_diagnostic=str(error)))
        else:
            raise AssertionError('Undetected source fault ' + label)
    assert all(c.pin(p) == v for p, v in inputs.items())
    result = dict(status='PASS_12_ACTUAL_COPIED_SOURCE_GRAPH_CONTROLS_NO_NATIVE', method=c.pin(__file__),
                  inputs=inputs, outcomes=outcomes, positive=2, negative=10, native_simulation=False)
    assert len(outcomes) == 12
    c.write_json(B / 'source-controls01.json', result)
    print(json.dumps(dict(result=c.pin(B / 'source-controls01.json'), cases=len(outcomes))))


if __name__ == '__main__':
    main()
