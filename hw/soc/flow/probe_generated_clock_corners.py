#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure generated-clock corner isolation with seven actual IHP cells.

This diagnostic compares identical constraints/netlist under multiple loaded
Liberty corners and under one corner per process. It neither changes a timing
limit nor treats its small example as product timing acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

NETLIST = '''// SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
// SPDX-License-Identifier: CERN-OHL-W-2.0
module clock_probe(input clk, input rst_n, input data, output q, output gtx);
wire c0,c1,c2,d0,d1;
sg13g2_buf_16 cbuf0(.A(clk),.X(c0));
sg13g2_buf_8 cbuf1(.A(c0),.X(c1));
sg13g2_buf_4 cbuf2(.A(c1),.X(gtx));
sg13g2_buf_16 launchbuf(.A(clk),.X(c2));
sg13g2_dfrbpq_1 ff(.D(data),.CLK(c2),.RESET_B(rst_n),.Q(d0));
sg13g2_dlygate4sd3_1 delay0(.A(d0),.X(d1));
sg13g2_buf_4 outputbuf(.A(d1),.X(q));
endmodule
'''
SDC = '''create_clock -name input_clk -period 8 [get_ports clk]
create_generated_clock -name output_clk -source [get_ports clk] -divide_by 1 [get_ports gtx]
set_propagated_clock [all_clocks]
set_clock_uncertainty .25 [all_clocks]
set_clock_transition .15 [get_clocks input_clk]
set_driving_cell -lib_cell sg13g2_buf_4 -pin X [all_inputs]
set_load .006 [all_outputs]
set_false_path -from [get_ports rst_n]
set_input_delay -clock input_clk -max 3 [get_ports data]
set_input_delay -clock input_clk -min .5 [get_ports data]
set_output_delay -clock output_clk -max 2.5 [get_ports q]
set_output_delay -clock output_clk -min -.5 [get_ports q]
set_timing_derate -early .95
set_timing_derate -late 1.05
'''


def tcl_path(path):
    # No substitution of dollar signs, brackets or braces from file paths.
    import base64
    value = base64.b64encode(str(path).encode()).decode()
    return '[encoding convertfrom utf-8 [binary decode base64 ' + value + ']]'


def slacks(text):
    values = {}
    for block in text.split('Startpoint: ')[1:]:
        endpoint = re.search(r'^Endpoint: (\S+)', block, re.M)
        slack = re.search(r'([-\d.]+)\s+slack \((MET|VIOLATED)\)', block)
        if endpoint is None or slack is None or endpoint[1] in values:
            raise ValueError('Missing or ambiguous timing path')
        values[endpoint[1]] = float(slack[1])
    if set(values) != {'ff', 'q'}:
        raise ValueError('Both ordinary and generated-clock paths are required')
    return values


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdk', type=Path, required=True)
    parser.add_argument('--sta', default='sta')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    tool = shutil.which(args.sta)
    if tool is None:
        raise ValueError('OpenSTA is unavailable')
    libs = {corner: args.pdk.resolve() / 'libs.ref/sg13g2_stdcell/lib' /
            ('sg13g2_stdcell_' + suffix + '.lib') for corner, suffix in
            [('fast', 'fast_1p32V_m40C'), ('slow', 'slow_1p08V_125C'),
             ('typ', 'typ_1p20V_25C')]}
    hashes = {corner: dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
              for corner, path in libs.items()}
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    netlist = out / 'clock_probe.v'
    netlist.write_text(NETLIST)
    (out / 'constraints.sdc').write_text(SDC)
    results = dict(scope=__doc__, libraries=hashes,
                   version=subprocess.check_output([tool, '-version'], text=True).strip(),
                   runs={}, comparison={})
    for tag, corners in [('multi', list(libs))] + [(c, [c]) for c in libs]:
        script = 'define_corners ' + ' '.join(corners) + '\n'
        for corner in corners:
            script += f'read_liberty -corner {corner} {tcl_path(libs[corner])}\n'
        script += f'read_verilog {tcl_path(netlist)}\nlink_design clock_probe\n' + SDC
        for corner in corners:
            for kind in ('max', 'min'):
                report = out / f'{tag}-{corner}-{kind}.rpt'
                script += (f'report_checks -corner {corner} -path_delay {kind} '
                           f'-format full_clock_expanded -digits 9 > {tcl_path(report)}\n')
        path = out / (tag + '.tcl')
        path.write_text(script)
        command = [tool, '-exit', str(path)]
        with (out / (tag + '.log')).open('x') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=60)
        results['runs'][tag] = dict(command=command, returncode=result.returncode)
        if result.returncode:
            raise RuntimeError('STA execution failed; inspect the retained log')
    for corner in libs:
        values = {}
        for kind in ('max', 'min'):
            multi = slacks((out / f'multi-{corner}-{kind}.rpt').read_text())
            single = slacks((out / f'{corner}-{corner}-{kind}.rpt').read_text())
            values[kind] = dict(multi=multi, single=single,
                                delta_ns={p: multi[p] - single[p] for p in multi})
        results['comparison'][corner] = values
    results['generated_clock_difference_observed'] = any(
        abs(kind['delta_ns']['q']) > 1e-6
        for corner in results['comparison'].values() for kind in corner.values())
    results['ordinary_path_unchanged'] = all(
        abs(kind['delta_ns']['ff']) < 1e-6
        for corner in results['comparison'].values() for kind in corner.values())
    (out / 'result.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results['comparison'], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
