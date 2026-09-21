#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run real-CPU external level IRQ, WFI and interrupt-register preservation checks.

Generated copies reuse the normal boot, ECC, clock gating and observation
infrastructure. --legacy-t0 deliberately restores the old scratch-register
clobber in a copied CRT; it never edits shipping firmware.
"""
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


def check_log(text, expect_t0_failure=False):
    fields = {}
    for line in text.splitlines():
        if not line.startswith('RECORD '):
            continue
        for key, value in re.findall(r'\b(\w+)=(\S+)', line):
            if key in fields:
                raise ValueError('Repeated record field: ' + key)
            fields[key] = value
    mask = '00000100' if expect_t0_failure else '00000000'
    expected = dict(done='1', slept='1', expired='0', sig='e1700002', mask=mask,
                    rounds='3', exit=mask, magic='600dc0de', traps='0', nmis='0',
                    wdog1='0', wdog2='0', wdog3='0', alert_minor='0', alert_int='0',
                    alert_bus='0', dblfault='0', console_chars='19', console_framing='0')
    for key, value in expected.items():
        if fields.get(key) != value:
            raise ValueError(f'{key}: expected {value}, got {fields.get(key)}')
    if not 0 < int(fields['cycles']) < int(fields['budget']):
        raise ValueError('Expired or invalid cycle budget')
    if text.splitlines().count('RECORD end') != 1:
        raise ValueError('Incomplete or repeated run')
    if text.splitlines().count('EXTIRQ assertions=4 sleep_wakes=2') != 1:
        raise ValueError('Missing or repeated external-source/WFI observation')
    if 'Se1700002M' + mask not in text or re.search(r'\b(?:FATAL|ERROR):', text):
        raise ValueError('Missing UART verdict or simulator error')
    return {'status': 'EXPECTED t0 FAILURE' if expect_t0_failure else 'PASS',
            'records': fields, 'external_assertions': 4, 'sleep_wakes': 2,
            'scope': 'Fault-free digital CPU test: masked pending level, vector 11, masking, t0 preservation and WFI wake with global interrupts on/off. No physical CDC/MTBF, pad or SEU qualification.'}


def legacy_crt(text):
    text, count = re.subn(
        r'^(vec_\w+): addi sp,sp,-32 ; sw t0,0\(sp\) ; li t0,(\S+) ; j irq_common$',
        lambda m: f'{m[1]}: li t0,{m[2]} ; j irq_common', text, flags=re.M)
    if count != 9:
        raise ValueError('Unexpected IRQ stub inventory')
    text = once(text, 'irq_common:\n', 'irq_common:\n  addi  sp, sp, -32\n')
    text = once(text, '  lw    t0, 0(sp)\n  lw    t1, 4(sp)\n  lw    t2, 8(sp)\n  lw    t3, 12(sp)',
                '  lw    t1, 4(sp)\n  lw    t2, 8(sp)\n  lw    t3, 12(sp)')
    return once(text, 'vec_nmi:\n  addi  sp, sp, -32\n  sw    t0, 0(sp)\n  li    t0, 31\n  j     irq_common',
                'vec_nmi:\n  li    t0, 31\n  j     irq_common')


def prepare(output, legacy_t0=False):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    q = shlex.quote
    monitor = (SOC/'tb/external_irq_monitor.vh').read_text()
    monitor = monitor[monitor.index('  wire [15:0] ext_probe_gpio;'):]
    for kind, filename in [('rtl', 'tb_soc_fi.v'), ('gl', 'tb_soc_fi_gl.v')]:
        text = (SOC/'tb'/filename).read_text()
        text = once(text, 'localparam integer CLK_HALF   = 5;', 'localparam integer CLK_HALF   = 10;')
        top = '  soc_top #(.ROM_INIT(`ROM_HEX)) dut (' if kind == 'rtl' else '  soc_top dut ('
        text = once(text, top, monitor + top)
        text = once(text, ".irq_external_i(1'b0)", '.irq_external_i(ext_probe_irq)')
        text = once(text, '.gpio_o     (),', '.gpio_o     (ext_probe_gpio),')
        text = once(text, '    $display("RECORD end");', '''    $display("EXTIRQ assertions=%0d sleep_wakes=%0d",ext_assertions,ext_sleep_wakes);
    if(ext_assertions!=4 || ext_sleep_wakes!=2 || rec_sig!==32'he1700002 || rec_rounds!=3 || rec_traps!=0 || rec_nmis!=0 || !done_q || !core_sleep || wdog_stage1 || wdog_stage2 || wdog_stage3 || saw_alert_major_int || saw_alert_major_bus || saw_double_fault || rx_framing_errors)$fatal(1,"External IRQ integration failed");
    $display("RECORD end");''')
        (output/f'tb_irq_{kind}.v').write_text(text)
    if legacy_t0:
        (output/'crt0-legacy.S').write_text(legacy_crt((SOC/'tb/sw/crt0.S').read_text()))
    for source, target in [('build_sw_fi.sh','build_sw.sh'),('fi_core.sh','build_rtl.sh'),('fi_core_gl.sh','build_gl.sh')]:
        text = (SOC/'flow'/source).read_text()
        text = once(text, 'SOC_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)', 'SOC_DIR='+q(str(SOC)))
        if source == 'build_sw_fi.sh':
            text = once(text, '"$SW/fi_workload.c"', q(str(SOC/'tb/sw/external_irq.c')))
            if legacy_t0:
                text = once(text, '"$SW/crt0.S"', q(str(output/'crt0-legacy.S')))
        else:
            kind = 'rtl' if source == 'fi_core.sh' else 'gl'
            original = 'tb_soc_fi.v' if kind == 'rtl' else 'tb_soc_fi_gl.v'
            anchor = '"$SOC_DIR/tb/'+original+'"'
            if text.count(anchor) != (1 if kind == 'rtl' else 2):
                raise ValueError('Changed testbench/provenance anchors')
            text = text.replace(anchor, q(str(output/f'tb_irq_{kind}.v')))
            if kind == 'rtl':
                text = once(text, '"$SOC_DIR/flow/$SW_BUILD"', 'bash '+q(str(output/'build_sw.sh')))
        (output/target).write_text(text)
    prefix = '#!/usr/bin/env bash\nset -euo pipefail\n'
    rtl = prefix + 'SOC_MEM_RDREG=1 SOC_REQ_REG=1 SOC_RF_SYNPRE=1 SOC_MEM_HARDEN=1 SOC_ROM_HARDEN=1 SOC_WAKE_GNT=1 bash '+q(str(output/'build_rtl.sh'))+' '+q(str(output/'rtl'))+'\n'
    rtl += f'eval "$(make --no-print-directory -f {q(str(SOC/"tools.soc.mk"))} printvars)"\n'
    rtl += f'timeout "${{PROBE_TIMEOUT:-1200}}" "$VVP" {q(str(output/"rtl/tb_soc_fi.vvp"))} +site=-1 +armed=1 +budget=100000 2>&1 | tee {q(str(output/"rtl-run.log"))}\n'
    gl = prefix + ': "${1:?mapped netlist with external IRQ required}"\n'
    gl += f'bash {q(str(output/"build_sw.sh"))} {q(str(output/"sw"))}\n'
    gl += f'bash {q(str(output/"build_gl.sh"))} "$1" {q(str(output/"sw"))} {q(str(output/"gl"))}\n'
    gl += 'GL_IVERILOG=${GL_IVERILOG:-$HOME/.local/opt/iverilog13/usr/bin/iverilog}\n'
    gl += f'timeout "${{PROBE_TIMEOUT:-1200}}" "$(dirname "$GL_IVERILOG")/vvp" {q(str(output/"gl/tb_soc_fi_gl.vvp"))} +site=-1 +armed=1 +budget=100000 2>&1 | tee {q(str(output/"gl-run.log"))}\n'
    for kind, script in [('rtl',rtl),('gl',gl)]:
        script += f'python3 {q(str(Path(__file__).resolve()))} --check {q(str(output/(kind+"-run.log")))}'+(' --expect-t0-failure' if legacy_t0 else '')+'\n'
        (output/f'run_{kind}.sh').write_text(script)
    sources = [Path(__file__), SOC/'rtl/soc_top.v', SOC/'tb/sw/crt0.S', SOC/'tb/sw/external_irq.c', SOC/'tb/external_irq_monitor.vh',
               *[SOC/'tb'/p for p in ('tb_soc_fi.v','tb_soc_fi_gl.v')],
               *[SOC/'flow'/p for p in ('build_sw_fi.sh','fi_core.sh','fi_core_gl.sh')],
               *sorted((SOC/'tb/sw').rglob('*.h'))]
    (output/'source-hashes.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},indent=2)+'\n')
    return {'prepared':str(output),'legacy_t0_negative_control':legacy_t0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare',type=Path)
    action.add_argument('--check',type=Path)
    parser.add_argument('--legacy-t0',action='store_true')
    parser.add_argument('--expect-t0-failure',action='store_true')
    args=parser.parse_args()
    try:
        result=prepare(args.prepare,args.legacy_t0) if args.prepare else check_log(args.check.read_text(),args.expect_t0_failure)
    except (ValueError,OSError,KeyError) as error:
        parser.exit(2,str(error)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
