#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check independent load-pin threshold conversion with unchanged IHP Liberty.

This is a timing-engine regression, not chip timing acceptance. The deliberately
large load may violate the real slew limit; that violation must remain visible.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def literal(value):
    return '"' + ''.join('\\' + c if c in '\\"$[]' else c for c in str(value)) + '"'


def conversion(lib):
    text = lib.read_text()
    values = {}
    for key in ('slew_lower_threshold_pct_rise', 'slew_upper_threshold_pct_rise',
                'slew_derate_from_library'):
        match = re.search(r'\b' + key + r'\s*:\s*([\d.eE+-]+)\s*;', text)
        if not match:
            raise ValueError(f'Missing library threshold: {lib}: {key}')
        values[key] = float(match[1])
    width = values['slew_upper_threshold_pct_rise'] - values['slew_lower_threshold_pct_rise']
    derate = values['slew_derate_from_library']
    if not (0 < width <= 100 and 0 < derate <= 1):
        raise ValueError('Invalid threshold interval/derate')
    return width / derate


def inspect_report(text, loads, ratio):
    # Restrict parsing to complete timing paths, before the electrical report.
    paths = text.split('\nmax slew')[0]
    numbers = r'([\d.eE+-]+)'
    driver = re.findall(r'^\s*\d+\s+' + numbers + r'\s+' + numbers
                        + r'\s+' + numbers + r'\s+' + numbers
                        + r'\s+\^\s+b/X\s', paths, re.M)
    sinks = re.findall(r'^\s*' + numbers + r'\s+' + numbers + r'\s+' + numbers
                       + r'\s+\^\s+m/A_BM\[(\d+)\]', paths, re.M)
    if len(driver) != loads or len(sinks) != loads or {int(v[3]) for v in sinks} != set(range(loads)):
        raise ValueError('Missing, duplicate or unexpected load paths')
    errors = []
    for source, sink in zip(driver, sinks):
        driver_slew, load_slew = float(source[1]), float(sink[0])
        expected = driver_slew * ratio
        if not all(math.isfinite(x) and x > 0 for x in (driver_slew, load_slew, expected)):
            raise ValueError('Invalid transition value')
        errors.append(abs(load_slew - expected))
    maximum = max(errors)
    return {'status': 'PASS' if maximum < 1e-5 else 'FAIL', 'loads': loads,
            'maximum_conversion_error_ns': maximum,
            'load_slew_min_ns': min(float(v[0]) for v in sinks),
            'load_slew_max_ns': max(float(v[0]) for v in sinks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sta', nargs='+', required=True, help='Executable and optional launcher arguments')
    parser.add_argument('--std-lib', type=Path, required=True)
    parser.add_argument('--macro-lib', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    std, macro = args.std_lib.resolve(strict=True), args.macro_lib.resolve(strict=True)
    executable = shutil.which(args.sta[0])
    if not executable:
        parser.error('STA executable/launcher is unavailable')
    pins = {str(p): digest(p) for p in (std, macro, Path(__file__).resolve(),
                                      Path(executable).resolve(strict=True))}
    record = {'status': 'RUNNING', 'scope': 'Timing-engine regression only; no layout/STA signoff',
              'input_sha256': pins, 'command_prefix': args.sta, 'cases': []}
    ratio = conversion(macro) / conversion(std)
    record['expected_threshold_ratio'] = ratio
    try:
        for loads in (1, 64):
            mask = '{' + ','.join(["1'b0"] * (64 - loads) + ['mask'] * loads) + '}'
            verilog = out / f'load{loads}.v'
            verilog.write_text('module probe(input clk, input data, output [63:0] q);\n'
                              'wire mask; sg13g2_buf_1 b(.A(data),.X(mask));\n'
                              'RM_IHPSG13_1P_2048x64_c2_bm_bist m(.A_CLK(clk), '
                              ".A_MEN(1'b1),.A_WEN(1'b1),.A_REN(1'b1),.A_DLY(1'b0),"
                              ".A_ADDR(11'b0),.A_DIN(64'b0),.A_BM(" + mask + '),.A_DOUT(q),'
                              ".A_BIST_CLK(1'b0),.A_BIST_EN(1'b0),.A_BIST_MEN(1'b0),"
                              ".A_BIST_WEN(1'b0),.A_BIST_REN(1'b0),.A_BIST_ADDR(11'b0),"
                              ".A_BIST_DIN(64'b0),.A_BIST_BM(64'b0));\nendmodule\n")
            tcl = out / f'load{loads}.tcl'
            tcl.write_text(f'read_liberty {literal(std)}\nread_liberty {literal(macro)}\n'
                           f'read_verilog {literal(verilog)}\nlink_design probe\n'
                           'create_clock -name clk -period 20 [get_ports clk]\n'
                           'set_clock_transition 0.15 [get_clocks clk]\n'
                           'set_input_delay -clock clk 2 [get_ports data]\n'
                           'set_input_transition 0.15 [get_ports data]\n'
                           'set_output_delay -clock clk 2 [get_ports q*]\n'
                           'set_load 0.006 [get_ports q*]\n'
                           'report_checks -rise_to [get_pins {m/A_BM*}] -path_delay max '
                           '-group_path_count 64 -endpoint_path_count 1 '
                           '-fields {fanout cap slew} -digits 8\n'
                           'report_check_types -max_slew -max_capacitance -violators\nexit\n')
            pins.update({str(p): digest(p) for p in (verilog, tcl)})
            log = out / f'load{loads}.log'
            with log.open('x') as stream:
                child = subprocess.Popen([*args.sta, '-no_splash', '-exit', str(tcl)],
                                         stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = child.wait(timeout=120)
                except BaseException:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait()
                    raise
            text = log.read_text()
            if code or re.search(r'^\s*(Error|Warning):', text, re.M):
                raise ValueError(f'Tool did not complete cleanly: {log}')
            result = inspect_report(text, loads, ratio)
            result['log_sha256'] = digest(log)
            record['cases'].append(result)
        if any(digest(Path(n)) != h for n, h in pins.items()):
            raise ValueError('Input changed during measurement')
        record['status'] = 'PASS' if all(x['status'] == 'PASS' for x in record['cases']) else 'FAIL'
    except Exception as error:
        record.update(status='ERROR', error=str(error))
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(record['status'])
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
