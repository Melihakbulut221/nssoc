#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded, separate phase-aware diagnosis; never replaces a failed producer."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import re

import numpy as np

PRODUCER_SHA = '39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886'
MODEL_SHA = 'ae9288f885dd30fab24b07ed1e7e02e69eac9154022a0a6da576985183b0bd79'
RESULT_SHA = 'e9575e34e8d17c807abcc94b883dad1022d84dd556e62c094679249cc675cfb1'
START, STOP = 992e-9, 1e-6


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def cycles(times, clock, values, start, stop):
    """Exact linear zero crossings, trapezoidal time averages of saved samples."""
    times, clock, values = (np.asarray(x, dtype=float) for x in (times, clock, values))
    require(times.ndim == clock.ndim == values.ndim == 1, 'Scalar vectors')
    require(len(times) == len(clock) == len(values) and len(times) >= 3, 'Vector lengths')
    require(np.isfinite(times).all() and np.isfinite(clock).all() and np.isfinite(values).all(), 'Finite vectors')
    require(np.all(np.diff(times) > 0), 'Strict time order')
    require(times[0] <= start < stop <= times[-1], 'Complete declared window')
    indices = np.flatnonzero((clock[:-1] <= 0) & (clock[1:] > 0))
    edges = times[indices] - clock[indices] * np.diff(times)[indices] / (clock[indices + 1] - clock[indices])
    edges = edges[(edges >= start) & (edges <= stop)]
    require(len(edges) >= 4, 'At least three complete clock cycles')
    means = []
    for left, right in zip(edges[:-1], edges[1:]):
        lo, hi = np.searchsorted(times, [left, right], side='right')
        t = np.concatenate(([left], times[lo:hi], [right]))
        v = np.concatenate(([np.interp(left, times, values)], values[lo:hi], [np.interp(right, times, values)]))
        require(right > left and np.all(np.diff(t) >= 0), 'Bounded interpolated cycle')
        means.append(float(np.trapezoid(v, t) / (right - left)))
    centers = (edges[:-1] + edges[1:]) / 2
    rates = np.diff(means) / np.diff(centers) * 1e-9
    active = values[(times >= edges[0]) & (times <= edges[-1])]
    return dict(cycles=len(means), complete_cycle_window_s=[float(edges[0]), float(edges[-1])],
                centers_s=centers.tolist(), means=means, min=float(active.min()), max=float(active.max()),
                mean_span=float(max(means) - min(means)),
                signed_first_last_rate_per_ns=float((means[-1] - means[0]) / (centers[-1] - centers[0]) * 1e-9),
                max_abs_adjacent_mean_rate_per_ns=float(np.max(np.abs(rates))),
                max_abs_change_of_mean=float(np.max(np.abs(np.diff(means)))))


def run(campaign, part_path, out):
    import characterize_pcie_clock_trim_stream_v2 as frozen
    campaign, part_path, out = map(Path, (campaign, part_path, out))
    require(sha(frozen.__file__) == PRODUCER_SHA, 'Frozen producer identity')
    require(sha(campaign / 'result.json') == RESULT_SHA, 'Exact original failed campaign')
    r = json.loads((campaign / 'result.json').read_text())
    for name, digest in r['source_sha256'].items():
        require(sha(name) == digest, 'Unchanged original input: ' + name)
    require(r['status'] == 'ERROR_INCOMPLETE' and len(r['cases']) == 1, 'Preserved first-case failure')
    c = r['cases'][0]
    require(c['case']['step_s'] == .5e-12 and c['capture']['rows'] == 2000011, 'Exact first1us capture')
    folder = campaign / c['case']['name']
    ledger_path = folder / 'capture/parts/parts.json'
    ledger = json.loads(ledger_path.read_text())
    require(sha(ledger_path) == c['capture']['ledger_sha256'], 'Frozen parts ledger')
    p = ledger['parts'][-1]
    require(p['index'] == 30 and p['first_row'] + p['rows'] == 2000011 and p['rows'] == 33931, 'Exact final published part')
    require(part_path.stat().st_size == p['bytes'] and sha(part_path) == p['sha256'], 'Compressed part identity')
    with lzma.open(part_path, 'rb') as f:
        raw = f.read(p['uncompressed_bytes'] + 1)
    require(len(raw) == p['uncompressed_bytes'] and hashlib.sha256(raw).hexdigest() == p['uncompressed_sha256'], 'Raw part identity')
    columns = ledger['columns']
    require(columns == c['capture']['columns'] and len(columns) == 167 and len(set(columns)) == 167, 'Exact column bijection')
    a = np.frombuffer(raw, dtype='<f8').reshape((p['rows'], 167))
    require(np.isfinite(a).all(), 'Finite raw samples')
    data = dict(zip(columns, a.T))
    ts = data['time']
    require(ts[-1] == STOP and ts[0] < START and np.all((np.diff(ts) > 0) & (np.diff(ts) <= .5e-12 + 4 * np.spacing(STOP))), 'Native final time grid')
    clock = data['v(clkp)'] - data['v(clkn)']
    circuit = (folder / frozen.base.prior.FILE).read_text()
    parent_circuit = next(Path(n) for n in r['source_sha256'] if n.endswith('/' + c['case']['name'] + '/' + frozen.base.prior.FILE))
    require(circuit == parent_circuit.read_text(), 'Exact original circuit text')
    hbts = frozen.base.driver.contract(circuit, 4)
    require(set(columns) == {'time', *frozen.base.prior.vectors(hbts)}, 'Source-derived observation set')
    thermal_names = sorted(n for n in columns if n.endswith('.t)') or n.endswith('.dt)'))
    require(len(thermal_names) == 53, 'Every53 thermal node')
    thermal = {n: cycles(ts, clock, data[n], START, STOP) for n in thermal_names}
    model = next(Path(n) for n in r['source_sha256'] if n.endswith('/sg13g2_hbt_mod.lib'))
    require(sha(model) == MODEL_SHA, 'Frozen HBT thermal model')
    mt = model.read_text(errors='replace')
    require("cth = '1.60E-12*(Nx*0.25)**0.95'" in mt and "rth = '1*selft*3.26E+03*(4/Nx)**0.9'" in mt, 'Exact native thermal coefficients')

    def voltage(name):
        return np.zeros(len(ts)) if name == 'avss' else data[f'v({name})' if name in ('avdd', 'clkp', 'clkn') else f'v(xosc.{name})']

    hbt_metrics = {}
    for name, (nodes, nx) in hbts.items():
        col, base, emitter = map(voltage, nodes)
        ic, ib = (data[f'@q.xosc.{name}.qnpn13g2[{pin}]'] for pin in ('ic', 'ib'))
        power = (col - emitter) * ic + (base - emitter) * ib
        t = thermal[f'v(xosc.{name}.t)']
        power_cycles = cycles(ts, clock, power, START, STOP)
        current_cycles = cycles(ts, clock, ic, START, STOP)
        rth, cth = 3260 * (4 / nx)**.9, 1.6e-12 * (nx * .25)**.95
        hbt_metrics[name] = dict(nx=nx, thermal_resistance_k_per_w=rth, thermal_capacitance_j_per_k=cth,
            nominal_local_rc_time_constant_s=rth*cth, terminal_power_proxy_cycles=power_cycles,
            collector_current_cycles=current_cycles, mean_thermal_dissipation_proxy_w=float(np.mean(t['means'])) / rth,
            limitation='VCE*Ic+VBE*Ib is external terminal power proxy; internal VBIC generated heat and stored electrical energy are not directly observed. Rth*Cth is local model coefficient, not full coupled oscillator eigenmode.')
    windows = c['measurement']['consecutive2ns_windows']
    trajectory = {n: [dict(window_s=w['declared_window_s'], **w['thermal_nodes'][n]) for w in windows] for n in thermal_names}
    representative = data['v(xosc.xfn.t)']
    injected = {}
    for name, delta in [('constant_drift', .02 * (ts - START) * 1e9), ('late_drift', .04 * np.maximum(ts - (STOP - 2e-9), 0) * 1e9)]:
        value = cycles(ts, clock, representative + delta, START, STOP)
        require(value['max_abs_adjacent_mean_rate_per_ns'] > .019, 'Actual-wave injected drift must be detected')
        injected[name] = dict(max_abs_adjacent_mean_rate_per_ns=value['max_abs_adjacent_mean_rate_per_ns'], expected_above_per_ns=.019)
    require(not out.exists(), 'Fresh diagnostic output')
    out.mkdir(parents=True)
    result = dict(status='COMPLETE_PHASE_AWARE_DIAGNOSIS_NO_ACCEPTANCE', source_sha256=sha(__file__),
        original_status=r['status'], original_error=r['error'], original_thermal_metric_pass=False,
        original_guard_or_limit_modified=False, simulator_rerun=False, declared_window_s=[START, STOP],
        raw_part=dict(**p, local_compressed_and_raw_hash_replay=True),
        source_inputs={str(campaign/'result.json'):sha(campaign/'result.json'),str(ledger_path):sha(ledger_path),str(model):sha(model),str(folder/frozen.base.prior.FILE):sha(folder/frozen.base.prior.FILE),str(Path(frozen.__file__)):sha(frozen.__file__)},
        thermal_cycles=thermal, hbt_metrics=hbt_metrics, actual_wave_mutation_controls=injected,
        all53_max_cycle_mean_rate_per_ns=max(v['max_abs_adjacent_mean_rate_per_ns'] for v in thermal.values()),
        all53_max_cycle_mean_span_k=max(v['mean_span'] for v in thermal.values()),
        scope='Only complete clock cycles within fixed992–1000ns in exact final published part. All500 saved2ns summaries remain source-bound but are not independently raw-replayed here. No full-time safety revalidation, timestep agreement, infinite-time equilibrium, PLL/CDR/PCIe or PEX acceptance; frozen endpoint FAIL remains.')
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    (out/'saved-full-trajectory.json').write_text(json.dumps(trajectory, indent=2)+'\n')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('campaign', 'part', 'out'):
        ap.add_argument('--'+name, type=Path, required=True)
    args = ap.parse_args()
    r = run(args.campaign, args.part, args.out)
    print(json.dumps({k:r[k] for k in ('status','all53_max_cycle_mean_rate_per_ns','all53_max_cycle_mean_span_k','actual_wave_mutation_controls')}, indent=2))


if __name__ == '__main__':
    main()
