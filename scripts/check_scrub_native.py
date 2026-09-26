#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Map SCRUBCTL, check unknown-state recovery, and replay the actual failed cone."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'hw/soc/flow'))
from sim_logic_boot_gl import check_native_cell, run_logged  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quote(path):
    text = str(path.resolve())
    if any(char in text for char in '\n\r"\\'):
        raise ValueError('Unsupported Yosys path')
    return '"' + text + '"'


def check(out, pdk, tools):
    out = out.absolute()
    if out.exists() or out.is_symlink():
        raise ValueError('Refusing existing output')
    if not out.resolve().is_relative_to(ROOT/'hw/soc/out'):
        raise ValueError('Output must be under hw/soc/out')
    out.mkdir(parents=True)
    result = {'status': 'FAIL', 'scope': 'Native mapped SCRUBCTL recovery and known-value semantics; not whole-SoC acceptance', 'commands': []}
    try:
        rtl = ROOT/'hw/soc/rtl/soc_scrub.v'
        tb = ROOT/'hw/soc/tb/tb_scrub_native_clear.v'
        negative = ROOT/'hw/soc/tb/fixtures/scrub_counter_clear_pre_fix.v'
        ntb = ROOT/'hw/soc/tb/fixtures/tb_scrub_clear_negative.v'
        lib = pdk/'libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        model = pdk/'libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v'
        lock = json.loads((ROOT/'hw/soc/pnr/ihp-native-boot.lock.json').read_text())
        pins = {row['path']: row['sha256'] for row in lock['files']}
        for path in (lib, model):
            if sha(path) != pins['ihp-sg13g2/'+str(path.relative_to(pdk))]:
                raise ValueError('Native model/library differs from lock')
        sources = [Path(__file__), rtl, tb, negative, ntb, lib, model]
        result['inputs'] = {str(p): sha(p) for p in sources}
        iverilog, yosys, vvp = (str(tools/name) for name in ('iverilog', 'yosys', 'vvp'))
        version = subprocess.run([iverilog, '-V'], capture_output=True, text=True, check=True).stdout
        match = re.search(r'Icarus Verilog version (\d+)', version)
        if not match or int(match[1]) < 13:
            raise ValueError('Native models require Icarus >=13')
        result['iverilog'] = version.splitlines()[0]
        result['yosys'] = subprocess.check_output([yosys, '-V'], text=True).strip()
        gate = check_native_cell('iverilog', iverilog, model, out/'native-cell')
        result['native_cell'] = gate
        if not gate['passed']:
            raise ValueError('Native cell compatibility failed')
        def run(command, name, expected=0):
            row = run_logged(command, out/(name+'.log'), 300)
            row['log_sha256'] = sha(out/(name+'.log'))
            result['commands'].append(row)
            if row['returncode'] != expected:
                raise ValueError(name+' returned '+str(row['returncode']))
            return (out/(name+'.log')).read_text()
        script = (f'read_verilog {quote(rtl)}\nsynth -top soc_scrub -flatten\n'
                  f'dfflibmap -liberty {quote(lib)}\nopt\n'
                  f'abc -liberty {quote(lib)} -D 20000\nclean\n'
                  f'write_verilog -noattr {quote(out/"netlist.v")}\n')
        (out/'synth.ys').write_text(script)
        run([yosys, '-s', str(out/'synth.ys')], 'synthesis')
        for label, bench, design, top, expected, banner in (
            ('positive', tb, out/'netlist.v', 'tb_scrub_native_clear', 0,
             'SCRUB_NATIVE_CLEAR PASS sources=6 saturation=65535 clear_event=1'),
            ('negative', ntb, negative, 'tb', 1,
             'Unknown startup count survives clear'),
        ):
            run([iverilog, '-g2012', '-DFUNCTIONAL', '-s', top, '-o', str(out/(label+'.vvp')),
                 str(bench), str(design), str(model)], label+'-compile')
            text = run([vvp, str(out/(label+'.vvp'))], label+'-run', expected)
            if banner not in text:
                raise ValueError(label+' missing expected assertion/banner')
        result['sources_unchanged'] = all(sha(p)==value for name,value in result['inputs'].items() for p in [Path(name)])
        if not result['sources_unchanged']:
            raise ValueError('Inputs changed during run')
        result['status'] = 'PASS'
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result['error'] = str(error)
    finally:
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'hw/soc/out/scrub-native')
    parser.add_argument('--pdk', type=Path, default=ROOT/'hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2')
    parser.add_argument('--tools', type=Path, default=ROOT/'hw/soc/tools/oss-cad-suite/bin')
    args = parser.parse_args()
    try:
        result = check(args.output, args.pdk.resolve(), args.tools.resolve())
    except ValueError as error:
        parser.exit(2, str(error)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
