#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real Ibex UART reception/IRQ/WFI regression, using only serial input pins."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex

SOC = Path(__file__).resolve().parents[1]


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unsupported source anchor: ' + old)
    return text.replace(old, new)


def verify_sources(output):
    root = SOC.parents[1]
    for manifest, base in [('source-hashes.json', root), ('prepared-hashes.json', output)]:
        identities = json.loads((output/manifest).read_text())
        if not identities:
            raise ValueError('Empty input manifest')
        for name, digest in identities.items():
            path = (base/name).resolve()
            if not path.is_relative_to(base.resolve()):
                raise ValueError('Input path escapes its scope')
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('Input changed: '+name)


def check_log(text, corrupt_byte=False):
    fields = {}
    for line in text.splitlines():
        if line.startswith('RECORD '):
            for key, value in re.findall(r'\b(\w+)=(\S+)', line):
                if key in fields:
                    raise ValueError('Repeated record: ' + key)
                fields[key] = value
    mask = '00000001' if corrupt_byte else '00000000'
    expected = dict(done='1', slept='1', expired='0', sig='a1170001', mask=mask,
                    rounds='5', exit=mask, magic='600dc0de', traps='0', nmis='0',
                    wdog1='0', wdog2='0', wdog3='0', alert_minor='0', alert_int='0',
                    alert_bus='0', dblfault='0', console_chars='19', console_framing='0')
    for key, value in expected.items():
        if fields.get(key) != value:
            raise ValueError(f'{key}: expected {value}, got {fields.get(key)}')
    if not 0 < int(fields['cycles']) < int(fields['budget']):
        raise ValueError('Expired cycle budget')
    if text.splitlines().count('RECORD end') != 1:
        raise ValueError('Incomplete/repeated run')
    if text.splitlines().count('UART_RX frames=6 sleep_wakes=1') != 1:
        raise ValueError('Missing serial peer/WFI observations')
    if 'Sa1170001M'+mask not in text or re.search(r'\b(?:FATAL|ERROR):', text):
        raise ValueError('Missing serial verdict or simulator error')
    return dict(status='EXPECTED DATA FAILURE' if corrupt_byte else 'PASS',
                records=fields, frames=6, sleep_wakes=1,
                scope='RTL CPU/APB/serial RX/fast IRQ/WFI integration; no physical, gate-level, CDC MTBF or radiation acceptance.')


def prepare(output, corrupt_byte=False):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    q = shlex.quote
    monitor = (SOC/'tb/uart_rx_monitor.vh').read_text()
    monitor = monitor[monitor.index('  wire [15:0] rx_probe_gpio;'):]
    if corrupt_byte:
        monitor = once(monitor, "8'h35", "8'h34")
    bench = (SOC/'tb/tb_soc_fi.v').read_text()
    bench = once(bench, 'localparam integer CLK_HALF   = 5;', 'localparam integer CLK_HALF   = 10;')
    top = '  soc_top #(.ROM_INIT(`ROM_HEX)) dut ('
    bench = once(bench, top, monitor + top)
    bench = once(bench, ".uart_rx_i  (1'b1)", '.uart_rx_i  (rx_probe_pin)')
    bench = once(bench, ".gpio_i     (16'h0000)", '.gpio_i     (rx_probe_ack)')
    bench = once(bench, '.gpio_o     (),', '.gpio_o     (rx_probe_gpio),')
    bench = once(bench, '    $display("RECORD end");',
                 '    $display("UART_RX frames=%0d sleep_wakes=%0d",rx_probe_frames,rx_probe_sleep_wakes);\n    $display("RECORD end");')
    (output/'tb_uart_rx.v').write_text(bench)
    for source, target in [('build_sw_fi.sh','build_sw.sh'), ('fi_core.sh','build_rtl.sh')]:
        text = (SOC/'flow'/source).read_text()
        text = once(text, 'SOC_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)', 'SOC_DIR='+q(str(SOC)))
        if source == 'build_sw_fi.sh':
            text = once(text, '"$SW/fi_workload.c"', q(str(SOC/'tb/sw/uart_rx.c')))
        else:
            text = once(text, '"$SOC_DIR/tb/tb_soc_fi.v"', q(str(output/'tb_uart_rx.v')))
            text = once(text, '"$SOC_DIR/flow/$SW_BUILD"', 'bash '+q(str(output/'build_sw.sh')))
        (output/target).write_text(text)
    script = '#!/usr/bin/env bash\nset -euo pipefail\n'
    script += 'SOC_MEM_RDREG=1 SOC_REQ_REG=1 SOC_RF_SYNPRE=1 SOC_MEM_HARDEN=1 SOC_ROM_HARDEN=1 SOC_WAKE_GNT=1 bash '+q(str(output/'build_rtl.sh'))+' '+q(str(output/'rtl'))+'\n'
    script += f'eval "$(make --no-print-directory -f {q(str(SOC/"tools.soc.mk"))} printvars)"\n'
    script += f'timeout "${{PROBE_TIMEOUT:-1200}}" "$VVP" {q(str(output/"rtl/tb_soc_fi.vvp"))} +site=-1 +armed=1 +budget=100000 2>&1 | tee {q(str(output/"rtl-run.log"))}\n'
    script += f'python3 {q(str(Path(__file__).resolve()))} --check {q(str(output/"rtl-run.log"))}'+(' --corrupt-byte' if corrupt_byte else '')+'\n'
    (output/'run_rtl.sh').write_text(script)
    sources = [Path(__file__), SOC/'rtl/soc_uart.v',
               SOC/'rtl/soc_top.v', SOC/'tb/sw/uart_rx.c', SOC/'tb/sw/crt0.S',
               SOC/'tb/tb_soc_fi.v', SOC/'tb/uart_rx_monitor.vh',
               SOC/'flow/fi_core.sh', SOC/'flow/build_sw_fi.sh',
               *sorted((SOC/'tb/sw').rglob('*.h'))]
    (output/'source-hashes.json').write_text(json.dumps(
        {str(p.relative_to(SOC.parents[1])): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}, indent=2)+'\n')
    (output/'prepared-hashes.json').write_text(json.dumps({
        name: hashlib.sha256((output/name).read_bytes()).hexdigest()
        for name in ['tb_uart_rx.v','build_sw.sh','build_rtl.sh','run_rtl.sh']}, indent=2)+'\n')
    return dict(prepared=str(output), corrupt_byte=corrupt_byte)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', type=Path)
    action.add_argument('--check', type=Path)
    parser.add_argument('--corrupt-byte', action='store_true')
    args = parser.parse_args()
    try:
        result = prepare(args.prepare, args.corrupt_byte) if args.prepare else check_log(args.check.read_text(), args.corrupt_byte)
        if args.check:
            verify_sources(args.check.parent)
            result['sources_unchanged'] = True
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, str(error)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
