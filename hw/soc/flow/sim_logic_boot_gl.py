#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reproduce functional whole mapped-SoC immutable-ROM boot, without preload.

Use the synthesis and normal firmware output directories from the same logic-ROM
build. Icarus >=13 is required for the vendor flip-flop models. No SDF is applied.
Verilator is a supplemental randomized two-state control, not X-propagation proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

SOC = Path(__file__).resolve().parents[1]
SRAM_MODELS = (
    'RM_IHPSG13_1P_2048x64_c2_bm_bist.v',
    'RM_IHPSG13_1P_core_behavioral_bm_bist.v',
    'RM_IHPSG13_2P_256x16_c2_bm_bist.v',
    'RM_IHPSG13_2P_core_behavioral_bm_bist_ideal.v',
    'RM_IHPSG13_2P_core_behavioral_ideal.v',
)
SYMBOLS = dict(EXIT_CODE_ADDR='exit_code', EXIT_MAGIC_ADDR='exit_magic',
               CHECKS_ADDR='checks', FAILS_ADDR='fails')

CELL_PROBE = '''`timescale 1ns/1ps
module tb_native_cell_gate;
reg clk=0, rst=0, d=0;
wire q;
always #10 clk=~clk;
sg13g2_dfrbpq_1 ff(.CLK(clk),.RESET_B(rst),.D(d),.Q(q));
initial begin
 #45; if(q!==0) $fatal(1,"Native reset assertion failed");
 rst=1; d=1;
 #10; if(q!==1) $fatal(1,"Native positive-edge data capture failed");
 d=0;
 #5; if(q!==1) $fatal(1,"Native flip-flop did not hold data");
 #5; rst=0;
 #1; if(q!==0) $fatal(1,"Native asynchronous reset reassertion failed");
 #9; rst=1;
 #20; if(q!==0) $fatal(1,"Native zero data capture failed");
 $display("NATIVE_CELL_GATE PASS"); $finish;
end
endmodule
'''


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_builds(synthesis, firmware):
    """Reject mismatched loader manifests or subsequently changed loader files."""
    manifests = []
    for directory in (synthesis, firmware):
        manifest = json.loads((directory / 'boot-rom/manifest.json').read_text())
        if digest(directory / 'boot-rom/soc_logic_boot_rom.v') != manifest['rtl_sha256']:
            raise ValueError('Generated ROM RTL differs from its manifest')
        manifests.append(manifest)
    if manifests[0] != manifests[1]:
        raise ValueError('Synthesis and firmware loader manifests differ')
    if digest(firmware / 'test_soc.bin') != manifests[0]['image_sha256']:
        raise ValueError('Firmware loader bytes differ from the fixed ROM image')
    text = (synthesis / 'soc_top.netlist.v').read_text()
    if re.search(r'\bRM_IHPSG13_1P_(?:1024x32|512x16)_', text):
        raise ValueError('Legacy SRAM ROM is present in the mapped design')
    for master, count in [('RM_IHPSG13_1P_2048x64_c2_bm_bist', 4),
                          ('RM_IHPSG13_2P_256x16_c2_bm_bist', 16)]:
        if len(re.findall(r'^\s*' + master + r'\s+', text, re.M)) != count:
            raise ValueError('Unsupported mapped RAM/Ethernet macro configuration')
    return manifests[0]


def read_symbols(nm, elf):
    output = subprocess.check_output([nm, str(elf)], text=True)
    symbols = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] in SYMBOLS.values():
            name = parts[2]
            if name in symbols:
                raise ValueError('Duplicate firmware status symbol')
            value = int(parts[0], 16)
            if value % 4 or not 0 <= value < 32768:
                raise ValueError('Firmware status symbol is outside aligned SRAM')
            symbols[name] = value
    if set(symbols) != set(SYMBOLS.values()) or len(set(symbols.values())) != 4:
        raise ValueError('Missing or aliased firmware status symbols')
    return symbols


def run_logged(command, path, timeout):
    start = time.monotonic()
    with path.open('x') as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        try:
            code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            code = 124
        except BaseException:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
            raise
    return dict(command=command, returncode=code, elapsed_s=time.monotonic() - start)


def check_native_cell(simulator, tool, library, out):
    """Reject a simulator/model incompatibility before compiling the entire SoC.

    The untouched IHP model routes reset through a $recrem delayed argument.
    Compiling successfully is insufficient evidence that those signals work.
    """
    out.mkdir(exist_ok=False)
    bench = out / 'tb_native_cell_gate.v'
    bench.write_text(CELL_PROBE)
    if simulator == 'iverilog':
        command = [tool, '-g2005-sv', '-s', 'tb_native_cell_gate',
                   '-o', str(out / 'sim.vvp'), str(bench), str(library)]
        runs = [[str(Path(tool).with_name('vvp')), '-i', str(out / 'sim.vvp')]]
    else:
        command = [tool, '--binary', '--timing', '-Wno-fatal', '--top-module',
                   'tb_native_cell_gate', '--Mdir', str(out / 'obj_dir'), '-j', '2',
                   '--x-initial', 'unique', '--x-assign', 'unique', str(bench), str(library)]
        runs = [[str(out / 'obj_dir/Vtb_native_cell_gate'), '+verilator+rand+reset+2',
                 '+verilator+seed+' + str(seed)] for seed in (1, 29)]
    original = digest(library)
    result = dict(library=str(library), library_sha256=original,
                  compile=run_logged(command, out / 'compile.log', 120), runs=[])
    if result['compile']['returncode'] == 0:
        for number, run in enumerate(runs):
            log = out / f'run-{number}.log'
            status = run_logged(run, log, 10)
            status['pass_banner'] = 'NATIVE_CELL_GATE PASS' in log.read_text()
            result['runs'].append(status)
    result['passed'] = (result['compile']['returncode'] == 0
                        and len(result['runs']) == len(runs)
                        and all(r['returncode'] == 0 and r['pass_banner'] for r in result['runs'])
                        and digest(library) == original)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('synthesis', 'firmware', 'pdk', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--nm', default=str(SOC / 'tools/rvgcc/bin/riscv-none-elf-nm'))
    parser.add_argument('--simulator', choices=('iverilog', 'verilator'), default='iverilog')
    parser.add_argument('--tool', help='Path to the selected simulator executable')
    parser.add_argument('--timeout', type=int, default=14400, help='Run wall seconds')
    parser.add_argument('--cycles', type=int, default=1000000)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args(argv)
    if args.timeout <= 0 or args.cycles <= 0:
        parser.error('Timeout and cycle bound must be positive')
    syn, fw, pdk, out = (getattr(args, key).resolve()
                         for key in ('synthesis', 'firmware', 'pdk', 'output'))
    manifest = validate_builds(syn, fw)
    symbols = read_symbols(args.nm, fw / 'app.elf')
    tool = shutil.which(args.tool or args.simulator)
    if tool is None:
        raise ValueError('Simulator executable unavailable; supply --tool')
    version = subprocess.run([tool, '-V' if args.simulator == 'iverilog' else '--version'],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             check=True).stdout
    if args.simulator == 'iverilog':
        match = re.search(r'Icarus Verilog version (\d+)', version)
        if not match or int(match[1]) < 13:
            raise ValueError('Native flip-flop models require Icarus >=13')
    sources = [SOC / 'tb/tb_soc_logic_boot_gl.v', syn / 'soc_top.netlist.v',
               SOC / 'tb/flash_w25q128jv.v',
               pdk / 'libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v']
    sources += [pdk / 'libs.ref/sg13g2_sram/verilog' / name for name in SRAM_MODELS]
    tracked = sources + [fw / name for name in ('app.elf', 'flash0.hex', 'test_soc.bin')]
    tracked += [directory / 'boot-rom' / name for directory in (syn, fw)
                for name in ('manifest.json', 'soc_logic_boot_rom.v')]
    hashes = {str(p): dict(sha256=digest(p), bytes=p.stat().st_size) for p in tracked}
    defines = ['-DFUNCTIONAL', '-DTIMEOUT_CYCLES=' + str(args.cycles)]
    defines += [f"-D{macro}=32'h{symbols[symbol]:08x}" for macro, symbol in SYMBOLS.items()]
    if args.simulator == 'iverilog':
        command = [tool, '-g2005-sv', '-s', 'tb_logicrom_gl', '-o', str(out / 'sim.vvp')]
        runs = [[str(Path(tool).with_name('vvp')), '-i', str(out / 'sim.vvp'),
                 '+flash0=' + str(fw / 'flash0.hex')]]
    else:
        command = [tool, '--binary', '--timing', '-Wno-fatal', '--top-module',
                   'tb_logicrom_gl', '--Mdir', str(out / 'obj_dir'), '-j', '4',
                   '--x-initial', 'unique', '--x-assign', 'unique']
        runs = [[str(out / 'obj_dir/Vtb_logicrom_gl'), '+flash0=' + str(fw / 'flash0.hex'),
                 '+verilator+rand+reset+2', '+verilator+seed+' + str(seed)] for seed in (1, 29)]
    command += defines + list(map(str, sources))
    out.mkdir(parents=True, exist_ok=False)
    record = dict(scope='Functional boot only. No ROM/RAM preload, SDF or fault qualification. '
                  'Verilator is a supplemental randomized two-state control.',
                  simulator=args.simulator, version=version, loader_manifest=manifest,
                  symbols=symbols, sources=hashes, compile_command=command, run_commands=runs,
                  run_timeout_s=args.timeout, cycle_bound=args.cycles)
    (out / 'inputs.json').write_text(json.dumps(record, indent=2) + '\n')
    if args.prepare_only:
        return 0
    cell_gate = check_native_cell(args.simulator, tool, sources[3], out / 'native-cell-gate')
    if not cell_gate['passed']:
        result = dict(native_cell_gate=cell_gate, passed=False, runs=[],
                      reason='Native cell simulator compatibility failed; whole SoC not compiled')
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        return 1
    result = dict(native_cell_gate=cell_gate,
                  compile=run_logged(command, out / 'compile.log', 1800), runs=[])
    if result['compile']['returncode'] == 0:
        for number, run in enumerate(runs):
            log = out / f'run-{number}.log'
            status = run_logged(run, log, args.timeout)
            status['pass_banner'] = 'LOGICROM_GL PASS checks=28' in log.read_text()
            result['runs'].append(status)
            (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    result['sources_unchanged'] = all(digest(p) == info['sha256'] for p, info in hashes.items())
    result['passed'] = (result['compile']['returncode'] == 0 and result['sources_unchanged']
                        and len(result['runs']) == len(runs)
                        and all(r['returncode'] == 0 and r['pass_banner'] for r in result['runs']))
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
