#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Characterize an experimental HBT TX cell; never certifies PCIe compliance."""
import argparse
from bisect import bisect_left
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / 'hw/soc/analog/pcie'
PDK_REV = 'c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
MODEL_HASHES = {
    'cornerHBT.lib': 'bae3d705445de8d6b8de4aa798a0e3e5e7cab617d6495d9c56473bc5377de462',
    'sg13g2_hbt_mod.lib': 'ae9288f885dd30fab24b07ed1e7e02e69eac9154022a0a6da576985183b0bd79',
}
UI = 125e-12
START = 2e-9
BITS = 254
# Engineering screening limits, deliberately NOT PCI-SIG specification limits.
MIN_MARGIN = 0.1
MAX_VCE = 1.6


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prbs7(seed=127, count=BITS):
    """x^7 + x^6 + 1; output MSB, shift left; nonzero 7-bit state."""
    if not 1 <= seed <= 127:
        raise ValueError('PRBS7 requires a nonzero seven-bit seed')
    result = []
    state = seed
    for _ in range(count):
        result.append((state >> 6) & 1)
        state = ((state << 1) & 127) | (((state >> 6) ^ (state >> 5)) & 1)
    return result


def pwl(bits, invert=False):
    def level(bit):
        return 1.46 if bool(bit) != invert else 1.26
    points = [(0, level(bits[0]))]
    for i in range(1, len(bits)):
        if bits[i] != bits[i-1]:
            t = START + i * UI
            points.extend([(t, level(bits[i-1])), (t+10e-12, level(bits[i]))])
    points.append((START + len(bits)*UI, level(bits[-1])))
    return 'PWL(\n+ ' + '\n+ '.join(f'{t:.12g} {v}' for t, v in points) + ')'


def cases(quick=False):
    specs = [('hbt_typ', 27, 1.8)] if quick else itertools.product(
        ('hbt_typ', 'hbt_bcs', 'hbt_wcs'), (-40, 27, 125), (1.71, 1.8, 1.89))
    result = [dict(name=f'{c}_{t}_{v}', corner=c, temp=t, supply=v,
                   lanes=1, cap=100e-15, mode='prbs', fault=None) for c, t, v in specs]
    for name, lanes, cap, mode, fault in (
        ('load_250f', 1, 250e-15, 'prbs', None),
        ('load_500f', 1, 500e-15, 'prbs', None),
        ('bank4_prbs', 4, 100e-15, 'prbs', None),
        ('bank4_simultaneous', 4, 100e-15, 'alternating', None),
        ('control_no_bias', 1, 100e-15, 'prbs', 'no_bias'),
        ('control_swapped_output', 1, 100e-15, 'prbs', 'swapped'),
        ('control_overload', 1, 100e-12, 'prbs', 'overload'),
    ):
        result.append(dict(name=name, corner='hbt_typ', temp=27, supply=1.8,
                           lanes=lanes, cap=cap, mode=mode, fault=fault))
    if not quick:
        # Selected bank extremes in addition to the full single-cell matrix.
        for c, t, v in itertools.product(('hbt_bcs', 'hbt_wcs'), (-40, 125), (1.71, 1.89)):
            result.append(dict(name=f'bank4_{c}_{t}_{v}', corner=c, temp=t, supply=v,
                               lanes=4, cap=100e-15, mode='prbs', fault=None))
        result.append(dict(name='half_timestep', corner='hbt_typ', temp=27, supply=1.8,
                           lanes=1, cap=100e-15, mode='prbs', fault=None, step=.5e-12))
    return result


def deck(case, models):
    n = case['lanes']
    sequences = [prbs7(127-i*19) if case['mode'] == 'prbs'
                 else [j % 2 for j in range(BITS)] for i in range(n)]
    lines = ['NSSOC experimental TX characterization',
             f'.lib "{models / "cornerHBT.lib"}" {case["corner"]}',
             '.include "tx_cml.spice"', '.include "tx_bank4.spice"',
             f'.temp {case["temp"]}', '.options reltol=1e-4 abstol=1e-12',
             f'VDD supply 0 {case["supply"]}',
             # Illustrative lumped supply; not a package or extracted PDN model.
             'RPDN supply supply_l 0.1', 'LPDN supply_l avdd 100p',
             'CDECAP avdd 0 100p']
    vectors = ['v(avdd)', 'i(vdd)']
    for i, bits in enumerate(sequences):
        lines.extend([f'VIP{i} ip{i} 0 {pwl(bits)}', f'VIN{i} in{i} 0 {pwl(bits, True)}',
                      f'IREF{i} avdd ref{i} {0 if case["fault"] == "no_bias" else .002}',
                      f'RTERM{i} op{i} on{i} 100',
                      f'CP{i} op{i} 0 {case["cap"]}', f'CN{i} on{i} 0 {case["cap"]}'])
        prefix = 'xbank.x'+str(i) if n == 4 else 'xlane'
        if case['fault'] != 'no_bias':
            lines.append(f'.nodeset v(ref{i})=.9 v({prefix}.tail)=.55 '
                         f'v(op{i})=1.5 v(on{i})=1.5')
        vectors.extend([f'v(op{i})', f'v(on{i})', f'v({prefix}.tail)',
                        f'v(ref{i})', f'i(v.{prefix}.vtail)'])
    if n == 4:
        ports = ' '.join(f'ip{i} in{i} op{i} on{i} ref{i}' for i in range(4))
        lines.append(f'XBANK {ports} avdd 0 0 nssoc_tx_bank4')
    else:
        outputs = 'on0 op0' if case['fault'] == 'swapped' else 'op0 on0'
        lines.append(f'XLANE ip0 in0 {outputs} avdd 0 0 ref0 nssoc_tx_cml')
    lines.extend(['.control', 'set wr_singlescale', 'set wr_vecnames',
                  'set numdgt=12', 'save ' + ' '.join(vectors),
                  f'tran {case.get("step", 1e-12)} {START+BITS*UI:.12g} 0 {case.get("step", 1e-12)}',
                  'wrdata wave.dat ' + ' '.join(vectors), 'quit', '.endc', '.end'])
    return '\n'.join(lines)+'\n', sequences


def interpolate(times, values, t):
    idx = bisect_left(times, t)
    if idx == 0 or idx == len(times):
        raise ValueError('Measurement outside captured time interval')
    weight = (t-times[idx-1])/(times[idx]-times[idx-1])
    return values[idx-1] + weight*(values[idx]-values[idx-1])


def measure(path, case, sequences):
    with path.open() as source:
        header = next(source).split()
        rows = [list(map(float, line.split())) for line in source if line.strip()]
    expected_columns = 3 + 5*case['lanes']
    expected_header = ['time', 'v(avdd)', 'i(vdd)']
    for lane in range(case['lanes']):
        prefix = 'xbank.x'+str(lane) if case['lanes'] == 4 else 'xlane'
        expected_header.extend([f'v(op{lane})', f'v(on{lane})', f'v({prefix}.tail)',
                                f'v(ref{lane})', f'i(v.{prefix}.vtail)'])
    if header != expected_header or not rows or any(
            len(r) != expected_columns or not all(math.isfinite(v) for v in r) for r in rows):
        raise ValueError('Incomplete or nonfinite waveform')
    columns = list(zip(*rows))
    times = columns[0]
    if times[0] > 1e-15 or times[-1] < START+BITS*UI-1e-15 or any(
            b <= a or b-a > 1.01e-12 for a, b in zip(times, times[1:])):
        raise ValueError('Incomplete time coverage or excessive timestep')
    # Discard bias/input settling and the first 16 bits. All stress data after
    # the stimulus start remain checked, not only bit-center observations.
    begin = bisect_left(times, START)
    duration = times[-1]-times[begin]
    avg_current = sum((columns[2][j]+columns[2][j-1])*.5*(times[j]-times[j-1])
                      for j in range(begin+1, len(times)))/duration
    lanes = []
    for lane, bits in enumerate(sequences):
        op, on, tail, bias, itail = columns[3+5*lane:8+5*lane]
        diff = [p-n for p, n in zip(op, on)]
        samples = [(interpolate(times, diff, START+(bit+phase)*UI), bits[bit])
                   for bit in range(16, BITS) for phase in (.3, .5, .7)]
        margins = [v if bit else -v for v, bit in samples]
        vces = [v-t for column in (op, on) for v, t in zip(column[begin:], tail[begin:])]
        # Reference is diode connected, tail emitter grounded. Conservative
        # emitter-current bound also upper-bounds tail collector current.
        stress_max = max(max(vces), max(tail[begin:]), max(bias[begin:]))
        stress_min = min(min(vces), min(tail[begin:]), min(bias[begin:]))
        positive = [v for v, b in samples if b]
        negative = [v for v, b in samples if not b]
        lane_result = dict(samples=len(samples), sign_errors=sum(m <= 0 for m in margins),
                           min_signed_margin_v=min(margins),
                           sampled_eye_height_v=min(positive)-max(negative),
                           median_diff_swing_v=sorted(positive)[len(positive)//2]
                           - sorted(negative)[len(negative)//2],
                           min_vce_v=stress_min, max_vce_v=stress_max,
                           peak_tail_emitter_current_a=max(itail[begin:]),
                           common_mode_min_v=min((p+n)/2 for p, n in zip(op[begin:], on[begin:])),
                           common_mode_max_v=max((p+n)/2 for p, n in zip(op[begin:], on[begin:])))
        lane_result['screen_pass'] = (min(margins) >= MIN_MARGIN and
                                     0.4 <= stress_min and stress_max <= MAX_VCE and
                                     0 <= min(itail[begin:]) and max(itail[begin:]) < .003*8)
        lanes.append(lane_result)
    return dict(rows=len(rows), lanes=lanes, analog_supply_power_w=-avg_current*case['supply'],
                supply_min_v=min(columns[1][begin:]), supply_max_v=max(columns[1][begin:]),
                screen_pass=all(l['screen_pass'] for l in lanes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdk', required=True, type=Path, help='Root containing libs.tech')
    parser.add_argument('--ngspice', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args()
    out, exe = args.out.resolve(), args.ngspice.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'hw/soc/out'):
        parser.error('Use a fresh output directory below hw/soc/out')
    models = args.pdk.resolve()/'libs.tech/ngspice/models'
    inputs = [DESIGN/'tx_cml.spice', DESIGN/'tx_bank4.spice', Path(__file__).resolve()]
    sources = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    model_hashes = {name: sha(models/name) for name in ('cornerHBT.lib', 'sg13g2_hbt_mod.lib')}
    if model_hashes != MODEL_HASHES:
        parser.error('PDK model bytes differ from the characterized revision')
    out.mkdir(parents=True)
    record = dict(status='FAIL', scope='Pre-layout ideal-resistor TX feasibility; NOT PCIe qualification',
                  pdk_reference_revision=PDK_REV, model_hashes=model_hashes, sources=sources,
                  tool_sha256=sha(exe), tool_version=subprocess.check_output([str(exe), '--version'],
                  text=True, stderr=subprocess.STDOUT), ui_s=UI, bits_per_lane=BITS,
                  thresholds=dict(min_signed_margin_v=MIN_MARGIN, min_vce_v=.4,
                                  max_vce_v=MAX_VCE, max_tail_emitter_a=.024),
                  quick=args.quick, cases=[])
    try:
        for case in cases(args.quick):
            directory = out/case['name']
            directory.mkdir()
            for source in inputs[:2]:
                (directory/source.name).write_bytes(source.read_bytes())
            text, sequences = deck(case, models)
            (directory/'bench.cir').write_text(text)
            # -n prevents host .spiceinit from changing models/solver settings.
            with (directory/'ngspice.log').open('w') as log:
                process = subprocess.run([str(exe), '-n', '-b', 'bench.cir'], cwd=directory,
                                         stdout=log, stderr=subprocess.STDOUT, timeout=180)
            entry = {**case, 'exit_code': process.returncode,
                     'bench_sha256': sha(directory/'bench.cir'),
                     'log_sha256': sha(directory/'ngspice.log')}
            record['cases'].append(entry)
            log_text = (directory/'ngspice.log').read_text()
            if process.returncode or any(term in log_text.lower() for term in
                                        ('error', 'timestep too small', 'aborted')):
                raise RuntimeError(f'Simulator failed: {case["name"]}')
            entry['numerical_warnings'] = [line for line in log_text.splitlines() if
                any(term in line.lower() for term in ('warning', 'nan', 'stepping'))]
            wave = directory/'wave.dat'
            entry['measurements'] = measure(wave, case, sequences)
            entry['wave_sha256'] = sha(wave)
            with wave.open('rb') as src, gzip.open(directory/'wave.dat.gz', 'wb') as dst:
                for chunk in iter(lambda: src.read(1024*1024), b''):
                    dst.write(chunk)
            entry['compressed_wave_sha256'] = sha(directory/'wave.dat.gz')
            wave.unlink()
            entry['expected_screen_pass'] = case['fault'] is None
            entry['accepted'] = entry['measurements']['screen_pass'] == entry['expected_screen_pass']
            print(case['name'], 'ACCEPTED' if entry['accepted'] else 'REJECTED',
                  entry['measurements']['lanes'][0]['min_signed_margin_v'], flush=True)
        if sources != {str(p.relative_to(ROOT)): sha(p) for p in inputs} or model_hashes != {
                name: sha(models/name) for name in model_hashes}:
            raise RuntimeError('Inputs changed during characterization')
        if not args.quick:
            by_name = {c['name']: c['measurements'] for c in record['cases']}
            baseline, half = by_name['hbt_typ_27_1.8'], by_name['half_timestep']
            delta = abs(baseline['lanes'][0]['min_signed_margin_v']-
                        half['lanes'][0]['min_signed_margin_v'])
            power_delta = abs(baseline['analog_supply_power_w']/half['analog_supply_power_w']-1)
            record['timestep_convergence'] = dict(margin_delta_v=delta,
                power_relative_delta=power_delta, passed=delta < .001 and power_delta < .002)
        success = all(c['accepted'] for c in record['cases']) and record.get(
            'timestep_convergence', {}).get('passed', True)
        record['status'] = 'FAIL' if not success else (
            'REVIEW' if any(c['numerical_warnings'] for c in record['cases']) else 'PASS')
    except Exception as exc:
        record['error'] = str(exc)
        raise
    finally:
        (out/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    return {'PASS': 0, 'FAIL': 1, 'REVIEW': 2}[record['status']]


if __name__ == '__main__':
    raise SystemExit(main())
