#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate predeclared finite timestep screen after two complete raw replays."""
import argparse
from bisect import bisect_left
import hashlib
import json
import math
from pathlib import Path

REVIEWER_SHA = '168a1563ed1847e752c67e3058b823200bfe2b3f4e2b345046a0ed13318530db'
DECLARATION_SHA = '4b8524ffdbba913840e2329374b69675e14a2b29c64af33155d84c4ca6fbff38'
WINDOWS = ((800e-9, 900e-9), (900e-9, 1e-6))
FREQUENCY_LIMIT_PPM = 100.0
PHASE_LIMIT_S = 50e-12


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pin(path):
    path = Path(path)
    with path.open('rb') as f:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


def windows(independent):
    ref = independent['reference_edges_s']
    fb = independent['feedback_edges_s']
    for values in [ref, fb]:
        require(len(values) > 2 and all(math.isfinite(x) for x in values), 'Finite actual edge census')
        require(all(a < b for a, b in zip(values, values[1:])), 'Strict actual edge order')
    ordinals = []
    for t in fb:
        i = bisect_left(ref, t)
        choices = [k for k in (i - 1, i) if 0 <= k < len(ref)]
        distances = sorted((abs(t - ref[k]), k) for k in choices)
        require(len(distances) == 1 or distances[0][0] != distances[1][0], 'Unambiguous actual ordinal')
        ordinals.append(distances[0][1])
    require(ordinals == independent['reference_ordinals'], 'Recomputed actual ordinal identity')
    result = []
    for lo, hi in WINDOWS:
        chosen = [(t, i) for t, i in zip(fb, ordinals) if lo <= t < hi]
        require(len(chosen) >= 9, 'Complete fixed-window edge coverage')
        ids = [i for _, i in chosen]
        require(all(b == a + 1 for a, b in zip(ids, ids[1:])), 'No cycle slip')
        phase = [t - ref[i] for t, i in chosen]
        require(all(abs(x) < 5e-9 for x in phase), 'Unambiguous phase interval')
        frequency = (len(chosen) - 1) / (chosen[-1][0] - chosen[0][0])
        span = max(phase) - min(phase)
        result.append(dict(interval_s=[lo, hi], reference_indices=ids, frequency_hz=frequency,
                           phase_s=phase, phase_span_s=span,
                           passed=abs(frequency / 1e8 - 1) <= 100e-6 and span <= PHASE_LIMIT_S))
    joined = result[0]['reference_indices'] + result[1]['reference_indices']
    require(all(b == a + 1 for a, b in zip(joined, joined[1:])), 'No inter-window slip')
    return result


def compare(first, second):
    a, b = windows(first), windows(second)
    rows = []
    for x, y in zip(a, b):
        require(x['reference_indices'] == y['reference_indices'], 'Matched reference ordinals')
        frequency_delta = abs(x['frequency_hz'] - y['frequency_hz']) / 1e8 * 1e6
        phase_delta = max(abs(p - q) for p, q in zip(x['phase_s'], y['phase_s']))
        checks = dict(both_individual_windows_pass=x['passed'] and y['passed'],
                      frequency_difference_100ppm=frequency_delta <= FREQUENCY_LIMIT_PPM,
                      matched_phase_difference_50ps=phase_delta <= PHASE_LIMIT_S)
        rows.append(dict(interval_s=x['interval_s'], reference_indices=x['reference_indices'],
                         frequency_difference_ppm=frequency_delta,
                         maximum_matched_phase_difference_s=phase_delta, checks=checks,
                         passed=all(checks.values())))
    return dict(passed=all(x['passed'] for x in rows), windows=rows)


def load_verified(capture, review):
    capture, review = Path(capture), Path(review)
    r = json.loads((capture / 'result.json').read_text())
    q = json.loads(review.read_text())
    require(q['native_result'] == pin(capture / 'result.json'), 'Full replay exact result pin')
    require(q['status'] == 'PASS_LOSSLESS_AUTHOR_REPLAY_AND_INDEPENDENT_ACQUISITION_ARITHMETIC', 'Complete raw review')
    require(r['status'] == q['native_authoritative_status'] == 'PASS_NATIVE_STREAM_FINITE_SCREEN', 'Both authoritative native screens pass')
    require(q['all539_author_safety_records_exact'] is True and r['safety']['passed'] is True, 'All539 safety replay')
    require(len(r['safety']['all_device_bounds']) == 539 and len(r['devices']) == 539, 'Exact device coverage')
    require(all(x['passed'] is True for x in r['safety']['all_device_bounds']), 'Every stored device predicate')
    require(r['measurement']['passed'] is True and r['strict_numerical_diagnostics_pass'] is True, 'Native functional and numerical screens')
    require(q['rows'] == r['rows'] and q['values'] == r['values'], 'Complete sample census')
    require(r['rows'] > 1 and r['values'] == r['rows'] * len(r['columns']), 'Complete native column census')
    require(q['full_raw_sha256'] == r['raw_sha256'], 'Full raw byte identity')
    require(q['canonical_payload_sha256'] == r['canonical_payload_sha256'], 'Full payload identity')
    require(q['independent']['passed'] is True and q['agreement']['all_predicates_exact'] is True, 'Independent finite predicates')
    methods = [p for p in q['inputs'] if Path(p).name == 'review_pcie_pll_acquisition_v1.py']
    require(len(methods) == 1 and q['inputs'][methods[0]]['sha256'] == REVIEWER_SHA, 'Frozen replay method')
    require(all(q['inputs'].get(p) == value for p, value in r['inputs'].items()), 'Complete source/model replay closure')
    for path, expected in q['inputs'].items():
        require(pin(path) == expected, 'Immutable review input: ' + path)
    for path, expected in r['outputs'].items():
        require(pin(capture / path) == expected, 'Immutable native output: ' + path)
    return r, q


def run(first, first_review, second, second_review, declaration):
    declaration = Path(declaration)
    require(pin(declaration)['sha256'] == DECLARATION_SHA, 'Pre-completion pair declaration')
    d = json.loads(declaration.read_text())
    require(pin(Path(first) / 'result.json')['sha256'] == d['first_result_sha256'], 'Declared first capture')
    require(pin(first_review)['sha256'] == d['first_full_review_sha256'], 'Declared first full review')
    a, qa = load_verified(first, first_review)
    b, qb = load_verified(second, second_review)
    require(a['config']['step_s'] == 5e-12 and b['config']['step_s'] == 2.5e-12, 'Declared distinct timesteps')
    require({k:v for k,v in a['config'].items() if k != 'step_s'} == {k:v for k,v in b['config'].items() if k != 'step_s'}, 'Unchanged complete physical configuration')
    require(a['config']['stop_s'] == b['config']['stop_s'] == 1e-6, 'Full1us captures')
    require(a['devices'] == b['devices'], 'Exact539 native graph')
    for p in a['inputs'].keys() & b['inputs'].keys():
        require(a['inputs'][p] == b['inputs'][p], 'Unchanged common source/model input: ' + p)
    old = (Path(first) / 'bench.cir').read_text()
    new = (Path(second) / 'bench.cir').read_text()
    line = '.tran 5e-12 1e-06 0 5e-12'
    require(old.count(line) == 1 and old.replace(line, '.tran 2.5e-12 1e-06 0 2.5e-12') == new, 'Literal native deck differs only timestep')
    result = compare(qa['independent'], qb['independent'])
    result.update(status='PASS_FINITE_NOMINAL_TIMESTEP_SCREEN' if result['passed'] else 'FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN',
                  inputs={str(Path(p)):pin(p) for p in [Path(__file__), declaration, Path(first)/'result.json', first_review, Path(second)/'result.json', second_review]},
                  scope='Two source-bound nominal1us captures and full public raw replays. Matched phase difference is not zero phase error; no PVT/jitter/thermal/layout/foundry/fullPLL qualification.')
    return result


def main():
    parser = argparse.ArgumentParser()
    for name in ['first','first-review','second','second-review','declaration','out']:
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    result = run(args.first, args.first_review, args.second, args.second_review, args.declaration)
    require(not args.out.exists(), 'Fresh comparison output')
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['passed'] is True and result['status'] == 'PASS_FINITE_NOMINAL_TIMESTEP_SCREEN' else 1


if __name__ == '__main__':
    raise SystemExit(main())
