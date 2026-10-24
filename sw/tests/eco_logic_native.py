#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Tiny native Yosys macro-interface controls; no chip acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(checker, liberty, output):
    output.mkdir(parents=True, exist_ok=False)
    macro = output/'macro.v'
    macro.write_text('(* blackbox *) module CHECK_MACRO(input [1:0] A, input CLK, output [1:0] Y); endmodule\n')
    before = output/'before.v'
    before.write_text('module soc_top(input [1:0] a, input clk, output [1:0] y); '
                      'CHECK_MACRO m(.A(a), .CLK(clk), .Y(y)); endmodule\n')
    cases = {
        'buffered_macro': ('{a[1], b}', 'CLK', True),
        'changed_macro_input': ('{a[0], b}', 'CLK', False),
        'unknown_macro_pin': ('{a[1], b}', 'BAD', False),
    }
    receipts = {}
    for name, (data, clock_pin, expected) in cases.items():
        after = output/(name+'.v')
        after.write_text('module soc_top(input [1:0] a, input clk, output [1:0] y); wire b; '
            'sg13g2_buf_2 buf_new(.A(a[0]), .X(b)); '
            f'CHECK_MACRO m(.A({data}), .{clock_pin}(clk), .Y(y)); endmodule\n')
        command = [sys.executable, str(checker), str(before), str(after),
                   '--liberty', str(liberty), '--macro-verilog', str(macro),
                   '--output', str(output/name)]
        with (output/(name+'.log')).open('w') as stream:
            result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=False)
        passed = result.returncode == 0
        if passed != expected:
            raise ValueError(f'Native macro control {name}: expected {expected}, return {result.returncode}')
        if passed:
            proof = json.loads((output/name/'result.json').read_text())
            if (proof.get('status') != 'PASS within scope' or proof.get('retained_cells') != 1
                    or proof.get('positive_buffers_before') != 0 or proof.get('positive_buffers_after') != 1):
                raise ValueError('Positive macro/buffer proof has unexpected scope')
        elif name == 'changed_macro_input':
            if 'State/macro input changed: m' not in (output/(name+'.log')).read_text():
                raise ValueError('Negative macro control failed for an unrelated reason')
        elif name == 'unknown_macro_pin':
            if 'does not have a port named' not in (output/name/'after.log').read_text():
                raise ValueError('Unknown-pin native control failed for an unrelated reason')
        receipts[name] = dict(expected_equivalent=expected, returncode=result.returncode,
                              unexpected_pass=False, command=command)
    row = dict(status='PASS_NATIVE_ECO_CONTROLS', cases=receipts,
               sources={str(p): digest(p) for p in (Path(__file__), checker, liberty, macro, before)},
               outputs={str(p.relative_to(output)): digest(p) for p in output.rglob('*') if p.is_file()},
               candidate_adopted=False, timing_accepted=False, manufacturing_approval=False)
    (output/'result.json').write_text(json.dumps(row, indent=2)+'\n')
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checker', type=Path, required=True)
    parser.add_argument('--liberty', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.checker.resolve(), args.liberty.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
