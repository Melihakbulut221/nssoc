#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prepare an isolated real-CPU Ethernet RTL/native-cell loopback test.

The existing FI build/bench supplies reset, CRT, ECC ROM loading and console
observation. Generated copies change only firmware, clocks, GMII ties and
packet assertions. No fault is injected; shipping RTL and FI defaults stay
untouched. --check independently rejects incomplete or failing result logs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex

SOC = Path(__file__).resolve().parents[1]
LENGTHS = (60, 61, 300, 511, 127, 512, 300, 300)
SIGNATURE = sum((f * 29 + i * 13 + 7) & 255
                for f, length in enumerate(LENGTHS) for i in range(length))


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected exactly one template anchor: {old!r}')
    return text.replace(old, new)


def check_log(path, kind):
    text = Path(path).read_text()
    fields = {}
    for line in text.splitlines():
        if not line.startswith('RECORD '):
            continue
        for key, value in re.findall(r'\b(\w+)=([^\s]+)', line):
            if key in fields:
                raise ValueError(f'Duplicate record field: {key}')
            fields[key] = value
    expected = dict(site='-1', armed='1', hit='0', done='1', slept='1',
                    expired='0', mask='00000000', rounds='8', exit='00000000',
                    magic='600dc0de', console_chars='19', console_hash='f48b7fa1',
                    console_framing='0', traps='0', mcause='00000000', nmis='0',
                    wdog1='0', wdog2='0', wdog3='0', alert_minor='0', alert_int='0',
                    alert_bus='0', dblfault='0')
    expected['kicks'] = '8' if kind == 'rtl' else '-1'
    if kind == 'gl':
        expected['wdog_rst_events'] = '0'
    if kind == 'rtl':
        expected['mem'] = '-1'
        expected.update({key: '0' for key in ('wdog_early', 'wdog_budget', 'rf_sec', 'rf_ded', 'rf_sec_seen', 'rf_ded_seen', 'scr_ramsec', 'scr_ramrd', 'scr_ramded', 'scr_romsec', 'scr_romrd', 'scr_romded')})
    expected['sig'] = f'{SIGNATURE:08x}'
    for key, value in expected.items():
        if fields.get(key) != value:
            raise ValueError(f'{key}: expected {value}, got {fields.get(key)}')
    if not 0 < int(fields['cycles']) < int(fields['budget']):
        raise ValueError('Invalid cycle count or expired budget')
    packet = f'ETH_{kind.upper()} frames=8 payload_bytes={sum(LENGTHS)} crc_checks=8'
    if text.count(packet) != 1 or text.splitlines().count('RECORD end') != 1:
        raise ValueError('Missing or repeated complete packet verdict')
    if re.search(r'\b(?:FATAL|ERROR):', text):
        raise ValueError('Simulator reported an error')
    return {'status': 'PASS', 'kind': kind, 'frames': len(LENGTHS),
            'payload_bytes': sum(LENGTHS), 'signature': f'{SIGNATURE:08x}',
            'records': fields, 'scope': 'Fault-free zero-delay CPU/GMII loopback; no PHY, SDF, fault campaign or throughput qualification.'}


def prepare(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    monitored = (SOC / 'tb/ethernet_loopback_monitor.vh').read_text()
    # Keep the monitor's provenance header out of the generated bench body.
    monitored = monitored[monitored.index('  reg eth_clk=0;'):]
    final = '''    $display("ETH_KIND frames=%0d payload_bytes=%0d crc_checks=%0d",eth_frames,eth_total,eth_frames);
    if(eth_frames!=8 || eth_total!=2171 || eth_bytes!=0 || rec_mask!==0 || rec_rounds!=8 || rec_traps!=0 || rec_nmis!=0 || !done_q || !core_sleep || wdog_stage1 || wdog_stage2 || wdog_stage3 || saw_alert_major_int || saw_alert_major_bus || saw_double_fault || rx_framing_errors)$fatal(1,"Whole-chip Ethernet KIND test failed");
'''
    for kind, name in [('rtl', 'tb_soc_fi.v'), ('gl', 'tb_soc_fi_gl.v')]:
        text = (SOC / 'tb' / name).read_text()
        text = replace_once(text, 'localparam integer CLK_HALF   = 5;', 'localparam integer CLK_HALF   = 10;')
        top = '  soc_top dut (' if kind == 'gl' else '  soc_top #(.ROM_INIT(`ROM_HEX)) dut ('
        text = replace_once(text, top, monitored + top)
        text = replace_once(text,
            ".eth_rx_clk_i(clk), .eth_tx_clk_i(clk), .eth_rxd_i(8'b0),\n      .eth_rx_dv_i(1'b0), .eth_rx_er_i(1'b0), .eth_mdio_i(1'b1),",
            ".eth_rx_clk_i(eth_clk), .eth_tx_clk_i(eth_clk), .eth_rxd_i(eth_txd),\n      .eth_rx_dv_i(eth_en), .eth_rx_er_i(eth_er), .eth_mdio_i(1'b1),\n      .eth_txd_o(eth_txd), .eth_tx_en_o(eth_en), .eth_tx_er_o(eth_er),")
        verdict = final.replace('ETH_KIND', 'ETH_' + kind.upper()).replace('KIND', 'gate' if kind == 'gl' else 'RTL')
        text = replace_once(text, '    $display("RECORD end");', verdict + '    $display("RECORD end");')
        (output / f'tb_eth_{kind}.v').write_text(text)
    for name, target in [('build_sw_fi.sh', 'build_sw.sh'), ('fi_core.sh', 'build_rtl.sh'), ('fi_core_gl.sh', 'build_gl.sh')]:
        text = (SOC / 'flow' / name).read_text()
        text = replace_once(text, 'SOC_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)', 'SOC_DIR=' + shlex.quote(str(SOC)))
        if name == 'build_sw_fi.sh':
            text = replace_once(text, '"$SW/fi_workload.c"', shlex.quote(str(SOC / 'tb/sw/ethernet_loopback.c')))
        else:
            kind = 'rtl' if name == 'fi_core.sh' else 'gl'
            original = 'tb_soc_fi.v' if kind == 'rtl' else 'tb_soc_fi_gl.v'
            anchor = '"$SOC_DIR/tb/' + original + '"'
            count = 1 if kind == 'rtl' else 2  # GL compile and provenance list.
            if text.count(anchor) != count:
                raise ValueError('Build/bench provenance anchors changed')
            text = text.replace(anchor, shlex.quote(str(output / f'tb_eth_{kind}.v')))
            if kind == 'rtl':
                text = replace_once(text, '"$SOC_DIR/flow/$SW_BUILD"', 'bash ' + shlex.quote(str(output / 'build_sw.sh')))
        (output / target).write_text(text)
    q = shlex.quote
    common = '#!/usr/bin/env bash\nset -euo pipefail\n'
    rtl = common + f'bash {q(str(output / "build_rtl.sh"))} {q(str(output / "rtl"))}\n'
    rtl = rtl.replace('bash ', 'SOC_MEM_RDREG=1 SOC_REQ_REG=1 SOC_RF_SYNPRE=1 SOC_MEM_HARDEN=1 SOC_ROM_HARDEN=1 SOC_WAKE_GNT=1 bash ', 1)
    rtl += f'eval "$(make --no-print-directory -f {q(str(SOC / "tools.soc.mk"))} printvars)"\n'
    rtl += f'timeout "${{PROBE_TIMEOUT:-2400}}" "$VVP" {q(str(output / "rtl/tb_soc_fi.vvp"))} +site=-1 +armed=1 +budget=300000 2>&1 | tee {q(str(output / "rtl-run.log"))}\n'
    gl = common + ': "${1:?mapped soc_top netlist required}"\n'
    gl += f'bash {q(str(output / "build_sw.sh"))} {q(str(output / "sw"))}\n'
    gl += f'bash {q(str(output / "build_gl.sh"))} "$1" {q(str(output / "sw"))} {q(str(output / "gl"))}\n'
    gl += 'GL_IVERILOG=${GL_IVERILOG:-$HOME/.local/opt/iverilog13/usr/bin/iverilog}\n'
    gl += f'timeout "${{PROBE_TIMEOUT:-2400}}" "$(dirname "$GL_IVERILOG")/vvp" {q(str(output / "gl/tb_soc_fi_gl.vvp"))} +site=-1 +armed=1 +budget=300000 2>&1 | tee {q(str(output / "gl-run.log"))}\n'
    for kind, script in [('rtl', rtl), ('gl', gl)]:
        script += f'python3 {q(str(Path(__file__).resolve()))} --check {q(str(output / (kind + "-run.log")))} --kind {kind}\n'
        (output / f'run_{kind}.sh').write_text(script)
    sources = [Path(__file__), SOC/'tb/sw/ethernet_loopback.c', SOC/'tb/ethernet_loopback_monitor.vh',
               *[SOC/'tb'/name for name in ('tb_soc_fi.v', 'tb_soc_fi_gl.v')],
               *[SOC/'flow'/name for name in ('build_sw_fi.sh', 'fi_core.sh', 'fi_core_gl.sh')],
               *sorted((SOC/'tb/sw').rglob('*.h')),
               *sorted((SOC/'tb/sw/lib').glob('*.c'))]
    inventory = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (output / 'source-hashes.json').write_text(json.dumps(inventory, indent=2) + '\n')
    return {'prepared': str(output), 'run': ['bash ' + q(str(output/'run_rtl.sh')), 'bash ' + q(str(output/'run_gl.sh')) + ' /path/to/soc_top.nl.v']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare', type=Path)
    action.add_argument('--check', type=Path)
    parser.add_argument('--kind', choices=('rtl', 'gl'), default='gl')
    args = parser.parse_args()
    try:
        result = prepare(args.prepare) if args.prepare else check_log(args.check, args.kind)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, str(error) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
