#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise the chip shell with native IHP IO models and a pin-stimulus core.

This is an IO wiring/serial-status test, not execution of the real CPU or PHY,
and not electrical, ESD, timing or physical padframe qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from generate_chip_io import CONTRACT, ROOT, generate


def fixture(contract):
    ports = contract['core_ports']
    stub = ['`timescale 1ns/1ps', '`default_nettype none',
            '// Pin stimulus only; not an implementation of the core.', 'module soc_top (']
    stub += [',\n'.join('    {} {} {}{}'.format(
        p['direction'], 'reg' if p['direction'] == 'output' else 'wire',
        '' if p['width'] == 1 else f'[{p["width"]-1}:0] ', n) for n, p in ports.items()), ');',
        'initial begin']
    stub += [f'    {n}=0;' for n, p in ports.items() if p['direction'] == 'output']
    stub += ['end', 'endmodule', '`default_nettype wire']
    declarations = ['wire VDD=1, VSS=0, IOVDD=1, IOVSS=0;']
    connections = ['.VDD(VDD)', '.VSS(VSS)', '.IOVDD(IOVDD)', '.IOVSS(IOVSS)']
    statements = []
    consumed = {f['port'] for f in contract['status_lsb_first']}
    for b in contract['bidirectional']:
        n, width = b['pad'], ports[b['input']]['width']
        bus = '' if width == 1 else f'[{width-1}:0] '
        declarations += [f'tri {bus}{n};', f'reg {bus}ext_{n}=0;', f'reg en_{n}=0;',
                         f'assign {n}=en_{n} ? ext_{n} : {width}\'bz;']
        connections.append(f'.{n}({n})')
        consumed.update([b['input'], b['enable']])
        if b.get('output'):
            consumed.add(b['output'])
        else:
            declarations += [f'pullup({n});']
        for value in [0] + [1 << i for i in range(width)] + [(1 << width)-1]:
            statements += [f'dut.u_core.{b["enable"]}=0; en_{n}=1; ext_{n}={width}\'h{value:x}; #2;',
                           f'if(dut.u_core.{b["input"]} !== {width}\'h{value:x}) $fatal(1,"{n} input");']
        statements += [f'en_{n}=0; #2;']
        if b.get('output'):
            for value in [0] + [1 << i for i in range(width)] + [(1 << width)-1]:
                statements += [f'dut.u_core.{b["enable"]}={width}\'h{(1<<width)-1:x};',
                               f'dut.u_core.{b["output"]}={width}\'h{value:x}; #2;',
                               f'if({n} !== {width}\'h{value:x}) $fatal(1,"{n} output");',
                               f'if(dut.u_core.{b["input"]} !== {n}) $fatal(1,"{n} loopback");']
            statements += [f'dut.u_core.{b["enable"]}=0; #2;',
                           f'if({n} !== {width}\'bz) $fatal(1,"{n} release");']
        else:
            statements += [f'dut.u_core.{b["enable"]}=1; #2;',
                           f'if({n} !== 0) $fatal(1,"{n} open drain low");',
                           f'dut.u_core.{b["enable"]}=0; #2;',
                           f'if({n} !== 1) $fatal(1,"{n} pullup release");',
                           f'en_{n}=1; ext_{n}=0; #2;',
                           f'if({n} !== 0) $fatal(1,"{n} incorrectly drives high");', f'en_{n}=0;']
    for n, p in ports.items():
        if n in consumed:
            continue
        width = p['width']
        bus = '' if width == 1 else f'[{width-1}:0] '
        pn = 'pad_' + n
        declarations.append(f'{"reg" if p["direction"] == "input" else "wire"} {bus}{pn}' +
                            ('=0;' if p['direction'] == 'input' else ';'))
        if p['direction'] == 'input':
            declarations += [f'wire {bus}{pn}_wire;', f'assign {pn}_wire={pn};']
            connections.append(f'.{pn}({pn}_wire)')
        else:
            connections.append(f'.{pn}({pn})')
        target, observed = (pn, f'dut.u_core.{n}') if p['direction'] == 'input' else (f'dut.u_core.{n}', pn)
        # Walking one checks every bit's mapping, beyond all-zero/all-one truth.
        for value in [0] + [1 << i for i in range(width)] + [0]:
            statements += [f'{target}={width}\'h{value:x}; #2;',
                           f'if({observed} !== {width}\'h{value:x}) $fatal(1,"{pn} mapping");']
    declarations += ['reg pad_test_clk=0, pad_test_req=0;', 'wire pad_test_ready, pad_test_data;',
                     'reg [191:0] received;', 'integer k, waits;']
    for n in ('clk', 'req'):
        declarations += [f'wire pad_test_{n}_wire;', f'assign pad_test_{n}_wire=pad_test_{n};']
        connections.append(f'.pad_test_{n}(pad_test_{n}_wire)')
    connections += [f'.pad_test_{n}(pad_test_{n})' for n in ('ready', 'data')]
    statements += ['pad_rst_ni=1; #1; pad_rst_ni=0; #2; pad_rst_ni=1;',
                   'dut.u_core.mbist_fail_expected_o=64\'hfedcba9876543210;',
                   'dut.u_core.mbist_fail_actual_o=64\'h0123456789abcdef;',
                   'dut.u_core.mbist_fail_addr_o=13\'h1234;',
                   'dut.u_core.mbist_fail_phase_o=5;', 'dut.u_core.mbist_fail_background_o=8\'ha6;',
                   'dut.u_core.mbist_busy_o=0; dut.u_core.mbist_done_o=1; dut.u_core.mbist_failed_o=1;',
                   'dut.u_core.eth_mbist_done_o=3; dut.u_core.eth_mbist_failed_o=2;',
                   'pad_test_req=1; waits=0;',
                   'while(pad_test_ready !== 1 && waits<40) begin tick; waits=waits+1; end',
                   'if(pad_test_ready !== 1) $fatal(1,"pad status timeout");',
                   'for(k=0;k<192;k=k+1) begin received[k]=pad_test_data; tick; end',
                   '''if(received !== {32'h4d420001,1'b0,8'ha6,3'd5,64'h0123456789abcdef,
                       64'hfedcba9876543210,13'h1234,2'd2,2'd3,1'b1,1'b1,1'b0})
                       $fatal(1,"pad status frame");''',
                   '$display("PASS native IHP IO: all mapped pins, bidirectional release, open drain and serial MBIST frame");', '$finish;']
    tb = ['`timescale 1ns/1ps', '`default_nettype none', 'module tb_chip_io;'] + declarations
    tb += ['nssoc_chip dut(' + ','.join(connections) + ');',
           'task tick; begin #3; pad_clk_i=1; #4; pad_clk_i=0; #5; pad_test_clk=1; #4; pad_test_clk=0; end endtask',
           'initial begin'] + statements + ['end', 'initial begin #100000; $fatal(1,"timeout"); end',
                                           'endmodule', '`default_nettype wire']
    return '\n'.join(stub)+'\n', '\n'.join(tb)+'\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pdk', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT/'hw/soc/out') or out.exists():
        ap.error('Use a new directory under hw/soc/out')
    out.mkdir(parents=True)
    contract = json.loads(CONTRACT.read_text())
    wrapper, _ = generate(contract)
    stub, tb = fixture(contract)
    for name, text in [('nssoc_chip.v', wrapper), ('core_stimulus.v', stub), ('tb_chip_io.v', tb)]:
        (out/name).write_text(text)
    native = args.pdk.resolve()/'libs.ref/sg13g2_io/verilog/sg13g2_io.v'
    suite = ROOT/'hw/soc/tools/oss-cad-suite/bin'
    rtl = ROOT/'hw/soc/rtl/chip/soc_status_serial.v'
    files = [Path(__file__).resolve(), ROOT/'scripts/generate_chip_io.py', CONTRACT, rtl, native,
             suite/'iverilog', suite/'vvp'] + list(out.glob('*.v'))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    pins = {str(p): sha(p) for p in files}
    cases = {}
    # Native models remain unchanged. Mutants alter actual wrapper connectivity.
    mutations = {'baseline': None,
                 'i2c_drives_high': (".c2p(1'b0)", ".c2p(1'b1)"),
                 'gpio_always_drives': ('.c2p_en(gpio_oe_o[0])', ".c2p_en(1'b1)"),
                 'gpio_lane_permutation': ('GPIO_LANE_PERMUTATION', ''),
                 'gpio_input_swap': ('.p2c(gpio_i[0])', '.p2c(gpio_i[1])'),
                 'status_payload_swap': ('mbist_fail_actual_o, mbist_fail_expected_o',
                                         'mbist_fail_expected_o, mbist_fail_actual_o')}
    for name, mutation in mutations.items():
        source = wrapper
        if name == 'gpio_lane_permutation':
            a, b = '.p2c(gpio_i[0])', '.p2c(gpio_i[2])'
            assert source.count(a) == source.count(b) == 1
            source = source.replace(a, '__SWAP_PIN__').replace(b, a).replace('__SWAP_PIN__', b)
        elif mutation:
            old, new = mutation
            assert old in source
            source = source.replace(old, new)
        candidate = out/(name+'.v'); candidate.write_text(source)
        cmd = [str(suite/'iverilog'), '-g2012', '-s', 'tb_chip_io', '-o', str(out/(name+'.vvp')),
               str(native), str(rtl), str(candidate), str(out/'core_stimulus.v'), str(out/'tb_chip_io.v')]
        build = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        (out/(name+'-compile.log')).write_text(build.stdout+build.stderr)
        if build.returncode:
            raise RuntimeError('Compilation failed: '+name)
        run = subprocess.run([str(suite/'vvp'), str(out/(name+'.vvp'))], capture_output=True, text=True, timeout=60)
        log = run.stdout+run.stderr; (out/(name+'.log')).write_text(log)
        passed = run.returncode == 0 and log.count('PASS native IHP IO:') == 1 and 'FATAL' not in log
        if passed != (name == 'baseline') or (name != 'baseline' and 'FATAL' not in log):
            raise RuntimeError('Unexpected verdict: '+name)
        cases[name] = dict(returncode=run.returncode, accepted=passed, log_sha256=sha(out/(name+'.log')))
    assert all(sha(Path(p)) == h for p, h in pins.items())
    record = dict(status='PASS_NATIVE_IO_TRANSPORT_WITH_REJECTED_WIRING_MUTATIONS', cases=cases,
                  input_sha256=pins, scope=__doc__, timing_accepted=False, manufacturing_approval=False)
    (out/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    print(record['status'])


if __name__ == '__main__':
    main()
