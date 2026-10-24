#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Count actual SRAM clock edges and joint controls from a mapped-design VCD.

Requires every mapped SRAM instance and every functional clock port, including
ECC and dual-port packet RAMs. Controls changing at the same VCD timestamp as
a rising clock are rejected because VCD cannot establish sampling order.
BIST must remain disabled. This measures activity, not silicon power.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from select_pnr_profile import mapped_macros
from vcd_activity import parse_header

STATES = tuple(f'{i:03b}' for i in range(8))  # MEN, WEN, REN


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def ports(master):
    match = re.fullmatch(r'RM_IHPSG13_([12])P_\d+x\d+_c2_bm_bist', master)
    if not match:
        raise ValueError('Unsupported SRAM master: '+master)
    return ('A', 'B') if match[1] == '2' else ('A',)


def collect(vcd, netlist, scope, start_ns, end_ns):
    if not all(math.isfinite(x) for x in (start_ns, end_ns)) or not 0 <= start_ns < end_ns:
        raise ValueError('Require finite 0 <= start_ns < end_ns')
    inventory = mapped_macros(netlist)
    hashes = dict(vcd=digest(vcd), netlist=digest(netlist))
    entries = {name: {'master': master, 'ports': {p: {'rising_edges': 0,
               'state_edges': dict.fromkeys(STATES, 0)} for p in ports(master)}}
               for name, master in inventory.items()}
    with Path(vcd).open() as stream:
        ids, scale_ps = parse_header(stream)
        header_end = stream.tell()
        stream.seek(0)
        header = stream.read(header_end)
        if len(re.findall(r'\$timescale\s+\d+\s*[munpf]?s\s+\$end', header)) != 1:
            raise ValueError('VCD requires one explicit timescale')
        if scale_ps <= 0:
            raise ValueError('Unsupported sub-picosecond VCD timescale')
        paths = {}
        for ident, aliases in ids.items():
            for name, width, _ in aliases:
                name = name.replace('\\', '')
                if name in paths and paths[name] != (ident, width):
                    raise ValueError('Duplicate VCD path: '+name)
                paths[name] = ident, width
        signals = {}
        for name, entry in entries.items():
            for port in entry['ports']:
                key = name, port
                pins = {}
                for suffix in ('CLK', 'MEN', 'WEN', 'REN', 'BIST_EN'):
                    path = f'{scope}.{name}.{port}_{suffix}'
                    if path not in paths or paths[path][1] != 1:
                        raise ValueError('Missing or non-scalar macro pin: '+path)
                    pins[suffix] = paths[path][0]
                signals[key] = pins
        wanted = {ident for pins in signals.values() for ident in pins.values()}
        values = dict.fromkeys(wanted, 'x')
        pending = {}
        time = 0
        start = start_ns * 1000 / scale_ps
        end = end_ns * 1000 / scale_ps
        sampled = False

        def flush(now, next_time):
            nonlocal sampled
            after = values | pending
            # Check every interval intersecting the requested window, including
            # quiet/gated clocks and a start lying between VCD timestamps.
            inside = now < end and next_time > start
            if inside:
                sampled = True
                for (name, port), pins in signals.items():
                    if after[pins['CLK']] not in '01' or after[pins['BIST_EN']] != '0':
                        raise ValueError(f'Unknown clock or active/unknown BIST: {name}/{port} at {now}')
            if start <= now < end:
                for (name, port), pins in signals.items():
                    clock = pins['CLK']
                    if values[clock] not in '01' and after[clock] == '1':
                        raise ValueError(f'Unknown-to-high clock transition: {name}/{port} at {now}')
                    if values[clock] == '0' and after[clock] == '1':
                        controls = [pins[s] for s in ('MEN', 'WEN', 'REN', 'BIST_EN')]
                        if any(values[i] != after[i] for i in controls):
                            raise ValueError(f'Ambiguous control/clock sampling: {name}/{port} at {now}')
                        state = ''.join(values[pins[s]] for s in ('MEN', 'WEN', 'REN'))
                        if set(state) - {'0', '1'}:
                            raise ValueError(f'Unknown SRAM control: {name}/{port} at {now}')
                        row = entries[name]['ports'][port]
                        row['rising_edges'] += 1
                        row['state_edges'][state] += 1
            values.update(pending)
            pending.clear()

        for raw in stream:
            line = raw.strip()
            if not line:
                continue
            if line.startswith('#'):
                new_time = int(line[1:])
                if new_time < time:
                    raise ValueError('VCD timestamps moved backwards')
                if new_time != time:
                    flush(time, new_time)
                    time = new_time
            elif line[0] in '01xXzZ':
                value, ident = line[0].lower(), line[1:]
                if ident in wanted:
                    if ident in pending and pending[ident] != value:
                        raise ValueError('Multiple transitions at one VCD timestamp: '+ident)
                    pending[ident] = value
            elif line[0] in 'bB':
                value, ident = line[1:].split()
                if ident in wanted:
                    if len(value) != 1:
                        raise ValueError('Non-scalar value on macro control')
                    if ident in pending and pending[ident] != value.lower():
                        raise ValueError('Multiple transitions at one VCD timestamp: '+ident)
                    pending[ident] = value.lower()
        flush(time, time)
        if time < end or not sampled:
            raise ValueError('VCD does not cover the complete requested window')
    if hashes != dict(vcd=digest(vcd), netlist=digest(netlist)):
        raise ValueError('Inputs changed while collecting SRAM activity')
    return dict(format=1, scope='Mapped SRAM functional-port rising-edge activity; BIST disabled.',
                state_order=['MEN','WEN','REN'], start_ns=start_ns, end_ns=end_ns,
                elapsed_ns=end_ns-start_ns, source_sha256=hashes, macros=entries)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('vcd', type=Path)
    ap.add_argument('--netlist', required=True, type=Path)
    ap.add_argument('--scope', required=True, help='Mapped soc_top path in the VCD, e.g. tb.dut')
    ap.add_argument('--start-ns', required=True, type=float)
    ap.add_argument('--end-ns', required=True, type=float)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    try:
        if args.output.exists():
            raise ValueError('Refusing to replace activity evidence')
        result = collect(args.vcd, args.netlist, args.scope, args.start_ns, args.end_ns)
        with args.output.open('x') as stream:
            stream.write(json.dumps(result, indent=2)+'\n')
    except (OSError, ValueError, KeyError) as error:
        ap.exit(2, str(error)+'\n')


if __name__ == '__main__':
    main()
