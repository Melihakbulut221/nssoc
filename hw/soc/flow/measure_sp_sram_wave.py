#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reconstruct SP512 writes and audit actual 64-bit transistor readback."""
import argparse
import bisect
import hashlib
import json
from pathlib import Path

from measure_sram_wave import read_wave, crossings, require


def analyze(header, rows, plan):
    idx = {s: i for i, s in enumerate(header)}
    vdd = 1.2
    times = [r[0] for r in rows]
    edges = crossings(rows, idx['v(clk)'], .6)
    require(len(edges) == len(plan), 'Missing or extra SP clock edge')

    def word(row, prefix, width):
        values = [row[idx[f'v({prefix}_{i})']] for i in range(width)]
        require(all(v <= .3 or v >= .9 for v in values), 'Ambiguous SP input/output')
        return sum(int(v >= .9) << i for i, v in enumerate(values))

    state, reads, transitions = {}, [], []
    previous_read = None
    stable_count = 0
    for n, (t, expected) in enumerate(zip(edges, plan)):
        require(abs(t*1e9-expected['edge_ns']-.05) <= .055, 'Unexpected SP clock time')
        row = rows[bisect.bisect_left(times, t)]
        require(abs(row[idx['v(vdd)']]-vdd) < .001, 'Unexpected supply')
        address, data, mask = word(row, 'a', 9), word(row, 'd', 64), word(row, 'we', 8)
        require((address, data, mask) == (expected['addr'], expected['din'], expected['we']),
                'SP stimulus mismatch')
        if mask:
            require(mask == 255 or address in state, 'Partial write to unknown word')
            value = state.get(address, 0)
            for byte in range(8):
                if mask & (1 << byte):
                    bits = 255 << (8*byte)
                    value = (value & ~bits) | (data & bits)
            state[address] = value
            previous_read = None
            continue
        require(address in state, 'Read before write')
        value = state[address]
        stop = edges[n+1] if n+1 < len(edges) else times[-1]
        samples = [row for row in rows if t+15e-9 <= row[0] < stop]
        require(len(samples) >= 30, 'Incomplete SP observation window')
        for row in samples:
            require(word(row, 'q', 64) == value, 'SP readback/byte-mask mismatch')
        stable_count += len(samples)
        reads.append(dict(address=address, expected=value, time_ns=t*1e9,
                          observed_samples=len(samples)))
        if previous_read is not None:
            for bit in range(64):
                old, new = previous_read >> bit & 1, value >> bit & 1
                if old == new:
                    continue
                levels = [.2, .5, .8] if new else [.8, .5, .2]
                hit = [crossings(rows, idx[f'v(q_{bit})'], f*vdd, bool(new), t, stop)
                       for f in levels]
                require(all(len(h) == 1 for h in hit), 'Missing or repeated SP output crossing')
                a, b, c = [h[0] for h in hit]
                require(t <= a <= b <= c < stop, 'Invalid SP output transition order')
                transitions.append(dict(bit=bit, read_time_ns=t*1e9,
                                        direction='rise' if new else 'fall',
                                        delay_ns=(b-t)*1e9, slew_20_80_ns=(c-a)*1e9))
        previous_read = value
    require(len(reads) == 4 and len(state) == 2, 'Incomplete two-address/masked-write pattern')
    require(transitions, 'No observed SP timing transitions')
    summary = {}
    for direction in ['rise', 'fall']:
        subset = [m for m in transitions if m['direction'] == direction]
        require(subset, 'Missing SP transition direction')
        summary[direction] = dict(count=len(subset), max_delay_ns=max(m['delay_ns'] for m in subset),
                                  max_slew_20_80_ns=max(m['slew_20_80_ns'] for m in subset))
    return dict(status='PASS_FULL_SP_TWO_ADDRESS_BYTE_WRITE_PATTERN',
                reads=reads, stable_samples=stable_count, transitions=transitions, summary=summary,
                timing_scope='Consecutive read cycles only; 50% delay and 20%-80% output slew, 50 ps maximum step',
                characterization_complete=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wave', type=Path)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())['cycles']
    result = analyze(*read_wave(args.wave, .05, 150), plan)
    result['input_sha256'] = {str(q.resolve()): hashlib.sha256(q.read_bytes()).hexdigest()
                              for q in [args.wave, args.plan, Path(__file__),
                                        Path(__file__).with_name('measure_sram_wave.py')]}
    with args.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(result['status'])


if __name__ == '__main__':
    main()
