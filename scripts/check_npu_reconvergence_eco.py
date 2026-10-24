#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native four-state controls of the proposed Boolean NPU cone factoring."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess

import prepare_npu_reconvergence_eco as eco

MODEL_SHA = '28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4'


def bench(negative=False):
    # Reuse the exact native-cell topology, with only the four input and output
    # conductor names relocated. Keep the predecessor in both compared forms.
    names = dict(_026035_='a', _043474_='b', _032758_='c', _043517_='d',
                 _043518_='intermediate', _043519_='value')
    def relocate(text):
        return re.sub('|'.join(map(re.escape, names)), lambda m: names[m[0]], text)
    original = relocate(eco.PREDECESSOR + '\n' + eco.OLD)
    candidate = relocate(eco.PREDECESSOR + '\n' + eco.NEW)
    if negative:
        candidate = candidate.replace('.A1(nssoc_npu_init_cd)', '.A1(nssoc_npu_init_b_n)')
    sources = []
    for name, gates in [('gold', original), ('gate', candidate)]:
        sources.append('module ' + name + '(input a,b,c,d,output value);\nwire intermediate;\n' + gates + '\nendmodule\n')
    lines = ['`timescale 1ns/1ps', *sources, 'module tb;', 'reg a,b,c,d; wire original,candidate;',
             'gold g(a,b,c,d,original); gate h(a,b,c,d,candidate);', 'initial begin']
    for index, values in enumerate(itertools.product('01xz', repeat=4)):
        lines.append("{a,b,c,d}=4'b" + ''.join(values) + '; #1;')
        lines.append(f'$display("CASE {index} inputs=%b%b%b%b original=%b candidate=%b",a,b,c,d,original,candidate);')
    lines += ['$finish;end', 'endmodule']
    return '\n'.join(lines) + '\n'


def parse(log, negative=False):
    rows = re.findall(r'^CASE (\d+) inputs=([01xz]{4}) original=([01xz]) candidate=([01xz])$', log, re.M)
    assert len(rows) == 256 and [int(r[0]) for r in rows] == list(range(256))
    assert [r[1] for r in rows] == [''.join(v) for v in itertools.product('01xz', repeat=4)]
    mismatches = []
    defined = 0
    for index, values, original, candidate in rows:
        if set(values) <= {'0', '1'}:
            a, b, c, d = map(int, values)
            # Independent reference: expand the sum of products; do not reuse
            # the transformation's implementation or treat X as a binary bit.
            expected = int(((not a) and (not b)) or (a and c and d))
            assert original == str(expected)
            if candidate != str(expected):
                mismatches.append(int(index))
        if original in '01':
            defined += 1
            if not negative:
                assert candidate == original, (values, original, candidate)
    target = next(r for r in rows if r[1] == 'x011')
    assert target[2:] == ('x', '1')
    if negative:
        assert mismatches, 'Deliberately miswired mux escaped the binary reference'
    else:
        assert not mismatches
    return dict(vectors=256, binary_vectors=16, original_defined_vectors=defined,
                binary_mismatch_cases=mismatches, reconvergence_control=list(target))


def run(model, output, compiler='iverilog', runtime='vvp'):
    assert hashlib.sha256(model.read_bytes()).hexdigest() == MODEL_SHA
    output.mkdir(parents=True, exist_ok=False)
    results = {}
    for label, negative in [('factored', False), ('miswired_mux', True)]:
        d = output / label
        d.mkdir()
        (d / 'tb.v').write_text(bench(negative))
        commands = [[compiler, '-g2005-sv', '-DFUNCTIONAL', '-s', 'tb', '-o', str(d / 'sim.vvp'), str(d / 'tb.v'), str(model)],
                    [runtime, '-i', str(d / 'sim.vvp')]]
        executions = []
        for stage, cmd in zip(('compile', 'run'), commands):
            with (d / (stage + '.log')).open('x') as log:
                r = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, check=False)
            executions.append(dict(command=cmd, returncode=r.returncode))
            assert r.returncode == 0
        results[label] = dict(executions=executions, observation=parse((d / 'run.log').read_text(), negative))
    pins = {str(p.relative_to(output)): dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            for p in output.rglob('*') if p.is_file()}
    record = dict(status='PASS_NATIVE_256_VECTOR_FACTORING_AND_ACTUAL_MISWIRE_CONTROL', model_sha256=MODEL_SHA,
                  results=results, outputs=pins, scope='Local native gate transformation only; not full SoC, timing or metastability acceptance.')
    (output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.model.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
