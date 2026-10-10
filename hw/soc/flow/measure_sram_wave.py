#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure observed DP SRAM transitions; never synthesize a Liberty model.

Inputs independently reconstruct memory contents. Timing uses interpolated 50%
clock/output crossings and 20%-80% output slew. Startup is excluded from energy.
Finite patterns cannot qualify unmeasured addresses, arcs, setup/hold or PEX.
"""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_wave(path, step_ns, stop_ns):
    with Path(path).open() as stream:
        header = stream.readline().split()
        require(header and header[0] == 'time' and len(set(header)) == len(header),
                'Missing or duplicate wave columns')
        rows = [list(map(float, line.split())) for line in stream]
    require(len(rows) >= 2, 'Missing wave samples')
    for i, row in enumerate(rows):
        require(len(row) == len(header) and all(math.isfinite(v) for v in row),
                'Incomplete or nonfinite sample')
        if i:
            require(0 < (row[0] - rows[i-1][0]) * 1e9 <= step_ns * 1.025,
                    'Nonmonotonic or missing timestep')
    require(abs(rows[0][0]) < 1e-18 and rows[-1][0] * 1e9 >= stop_ns - 1e-6,
            'Truncated waveform')
    return header, rows


def crossings(rows, column, level, rising=True, start=-math.inf, stop=math.inf):
    result = []
    for a, b in zip(rows, rows[1:]):
        av, bv = a[column], b[column]
        crosses = av < level <= bv if rising else av > level >= bv
        if crosses:
            t = a[0] + (b[0] - a[0]) * (level - av) / (bv - av)
            if start <= t < stop:
                result.append(t)
    return result


def analyze(header, rows, config):
    vdd = config['voltage']
    step = config['maxstep_ns']
    transition = config['input_transition_ns']
    require(vdd > 0 and step > 0 and transition > 0, 'Invalid measurement conditions')
    idx = {name: i for i, name in enumerate(header)}
    times = [row[0] for row in rows]
    columns = ['v(vdd)', 'v(clk1)', 'v(clk2)']
    columns += [f'v({kind}_{i})' for kind, width in
                [('a1', 8), ('a2', 8), ('we1', 2), ('we2', 2),
                 ('d1', 16), ('d2', 16), ('q2', 16)] for i in range(width)]
    require(set(columns) <= idx.keys(), 'Missing observed input/output columns')

    def word(row, node, width):
        values = [row[idx[f'v({node}_{i})']] for i in range(width)]
        require(all(v <= .25*vdd or v >= .75*vdd for v in values),
                'Ambiguous digital input or output')
        return sum(int(v >= .75*vdd) << i for i, v in enumerate(values))

    events = []
    for port, name in [(1, 'write_schedule'), (2, 'read_schedule')]:
        edge_times = crossings(rows, idx[f'v(clk{port})'], .5*vdd)
        plan = config[name]
        require(len(edge_times) == len(plan), 'Missing or extra clock edge')
        for t, expected in zip(edge_times, plan):
            require(abs(t*1e9 - expected['edge'] - transition/2) <= step*1.1,
                    'Clock edge differs from stimulus')
            row = rows[bisect.bisect_left(times, t)]
            require(abs(row[idx['v(vdd)']] - vdd) <= .001, 'Supply differs from corner')
            address, data, enable = (word(row, f'a{port}', 8),
                                     word(row, f'd{port}', 16), word(row, f'we{port}', 2))
            require((address, data, enable) == (expected['addr'], expected.get('data', 0),
                                               expected.get('we', 0)), 'Stimulus mismatch')
            events.append((t, port, address, data, enable))
    memory, reads = {}, []
    for t, port, address, data, enable in sorted(events):
        if port == 1 and enable:
            require(enable == 3 or address in memory, 'Partial write before initialization')
            value = memory.get(address, 0)
            for byte in range(2):
                if enable & (1 << byte):
                    mask = 255 << (8*byte)
                    value = (value & ~mask) | (data & mask)
            memory[address] = value
        elif port == 2:
            require(enable == 0 and address in memory, 'Unsupported write/read-before-write')
            reads.append({'time_s': t, 'address': address, 'expected': memory[address]})
    require(len(reads) >= 2, 'Insufficient read transitions')
    measurements, stable_count = [], 0
    for n, read in enumerate(reads):
        start = read['time_s']
        stop = reads[n+1]['time_s'] if n+1 < len(reads) else times[-1]
        observed = [row for row in rows if start+5.5e-9 <= row[0] < stop]
        require(len(observed) >= 10, 'Missing stable output observation window')
        for row in observed:
            require(word(row, 'q2', 16) == read['expected'], 'Wrong output or hold failure')
        stable_count += len(observed)
        if not n:
            continue
        previous = reads[n-1]['expected']
        for bit in range(16):
            before, after = previous >> bit & 1, read['expected'] >> bit & 1
            if before == after:
                continue
            col = idx[f'v(q2_{bit})']
            values = [.2, .5, .8] if after else [.8, .5, .2]
            measured = [crossings(rows, col, level*vdd, bool(after), start, stop)
                        for level in values]
            require(all(len(x) == 1 for x in measured),
                    'Missing or repeated output threshold crossing')
            a, b, c = [x[0] for x in measured]
            require(start <= a <= b <= c < stop, 'Invalid output transition order')
            measurements.append(dict(read=n, bit=bit, direction='rise' if after else 'fall',
                                     delay_ns=(b-start)*1e9, slew_20_80_ns=(c-a)*1e9))
    require(measurements and {m['direction'] for m in measurements} == {'rise', 'fall'},
            'Missing rising/falling transitions')
    summary = {}
    for direction in ['rise', 'fall']:
        subset = [m for m in measurements if m['direction'] == direction]
        summary[direction] = {'count': len(subset)}
        for key in ['delay_ns', 'slew_20_80_ns']:
            summary[direction]['min_'+key] = min(m[key] for m in subset)
            summary[direction]['max_'+key] = max(m[key] for m in subset)
    energy = None
    current = idx.get('i(vvdd)', idx.get('vvdd#branch'))
    if current is not None:
        # Integrate total delivered supply energy on [8 ns, end], clipping the
        # first interval exactly rather than including supply-ramp startup.
        joules = 0.0
        begin = 8e-9
        for a, b in zip(rows, rows[1:]):
            if b[0] <= begin:
                continue
            t0 = max(a[0], begin)
            pa = -a[idx['v(vdd)']]*a[current]
            pb = -b[idx['v(vdd)']]*b[current]
            p0 = pa+(pb-pa)*(t0-a[0])/(b[0]-a[0])
            joules += (p0+pb)*.5*(b[0]-t0)
        require(joules > 0, 'Nonpositive supply energy or reversed current sign')
        energy = dict(window_start_ns=8, window_end_ns=times[-1]*1e9,
                      total_pj=joules*1e12, mean_mw=joules/(times[-1]-begin)*1e3,
                      scope='Total schematic supply energy for the specified pattern; not per-arc internal power or isolated leakage')
    return dict(status='PASS_OBSERVED_PATTERN_TIMING', reads=reads,
                stable_samples=stable_count, summary=summary, transitions=measurements,
                supply_energy=energy, interpolation='Linear voltage threshold interpolation',
                timing_resolution_bound_ns=step, characterization_complete=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wave', type=Path)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    result = analyze(*read_wave(args.wave, config['maxstep_ns'], config['stop_ns']), config)
    result['input_sha256'] = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [args.wave, args.config, Path(__file__)]}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(result['status'])


if __name__ == '__main__':
    main()
