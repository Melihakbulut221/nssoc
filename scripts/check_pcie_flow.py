#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Port-only RTL/native VC0 credit accounting and initialization controls."""
import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys

from check_pcie_integrity import pin, tool_environment
from check_pcie_integrity_native import LIB_SHA, MODEL_SHA, quote
from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
COMMON = ('soc_pcie_credit_tx',)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--top', choices=('soc_pcie_credit_tx',), default='soc_pcie_credit_tx')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--iverilog-dir', type=Path)
    parser.add_argument('--rtl-dir', type=Path)
    parser.add_argument('--native', action='store_true')
    for name in ('yosys', 'liberty', 'models'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    if args.native and (args.rtl_dir or any(getattr(args, n) is None for n in ('yosys', 'liberty', 'models', 'iverilog_dir'))):
        parser.error('Native run requires explicit tools/libraries and forbids mutated RTL')
    out = args.out.resolve()
    if out.exists():
        parser.error('Use a fresh output directory')
    rtl_dir = args.rtl_dir or ROOT/'hw/soc/rtl/pcie'
    rtl = [(rtl_dir/(name+'.v')).resolve() for name in COMMON]
    bench = ROOT/'hw/soc/tb/cocotb'/('test_'+args.top+'.py')
    makefile = bench.with_name('Makefile.'+args.top)
    files = [*rtl, bench, makefile, Path(__file__).resolve(),
             ROOT/'scripts/check_pcie_integrity.py', ROOT/'scripts/check_pcie_integrity_native.py',
             ROOT/'scripts/cocotb_results.py']
    expected = sum(isinstance(n, ast.AsyncFunctionDef) and bool(n.decorator_list) for n in ast.parse(bench.read_text()).body)
    if expected == 0:
        parser.error('No actual port cases')
    if args.native:
        args.liberty, args.models = args.liberty.resolve(), args.models.resolve()
        if pin(args.liberty)['sha256'] != LIB_SHA or pin(args.models)['sha256'] != MODEL_SHA:
            parser.error('Require the exact unmodified c4 SG13G2 library/model bytes')
        version = subprocess.check_output([str(args.iverilog_dir.resolve()/'iverilog'), '-V'], stderr=subprocess.STDOUT, text=True)
        import re
        match = re.search(r'Icarus Verilog version (\d+)', version)
        if not match or int(match[1]) < 13:
            parser.error('Native cell delayed ports require Icarus >=13')
        files += [args.liberty, args.models]
    before = {str(p): pin(p) for p in files}
    out.mkdir(parents=True)
    record = dict(status='RUNNING', top=args.top, inputs=before, expected_tests=expected,
                  mode='native' if args.native else 'rtl', commands=[],
                  scope='VC0 unscaled transmit credit accounting. Parsed trusted FC input; no FC advertisements, receive buffers, timers, PHY, SDF or SoC integration.')
    def save():
        (out/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    def execute(command, log_name, environment=None):
        with (out/log_name).open('x') as log:
            result = subprocess.run(command, cwd=out, env=environment, stdout=log, stderr=subprocess.STDOUT)
        record['commands'].append(dict(argv=command, returncode=result.returncode, log=log_name, log_pin=pin(out/log_name)))
        save()
        if result.returncode:
            raise RuntimeError('Control failed: '+str(out/log_name))
    try:
        save()
        simulation_sources = rtl
        if args.native:
            script = ('read_liberty -lib '+quote(args.liberty)+'; read_verilog -sv '+' '.join(map(quote, rtl))
                      +'; hierarchy -check -top '+args.top+'; flatten -noscopeinfo; synth -top '+args.top+' -noabc; '
                      +'dfflibmap -liberty '+quote(args.liberty)+'; abc -liberty '+quote(args.liberty)
                      +'; clean; check -assert; stat -liberty '+quote(args.liberty)
                      +'; write_json '+quote(out/'mapped.json')+'; write_verilog -noattr -noexpr '+quote(out/'mapped.v'))
            (out/'map.ys').write_text(script+'\n')
            execute([str(args.yosys.resolve()), '-Q', '-T', '-s', str(out/'map.ys')], 'map.log')
            cells = json.loads((out/'mapped.json').read_text())['modules'][args.top]['cells']
            if not cells or any(not c['type'].startswith('sg13g2_') for c in cells.values()):
                raise ValueError('Unimplemented or non-IHP mapped cells')
            record['mapped_cells'] = len(cells)
            simulation_sources = [out/'mapped.v', args.models]
        execute(['make', '-f', str(makefile), '--no-print-directory',
                 'VERILOG_SOURCES='+' '.join(map(str, simulation_sources)),
                 'SIM_BUILD='+str(out/'sim'), 'COCOTB_RESULTS_FILE='+str(out/'results.xml'),
                 'PCIE_NATIVE='+str(int(args.native))], 'simulation.log', tool_environment(args.iverilog_dir))
        counts = count_results([out/'results.xml'])
        record['tests'] = dict(zip(('passed', 'failed', 'skipped'), counts))
        if counts != (expected, 0, 0):
            raise ValueError('Missing, failed or skipped port cases')
        if before != {str(p): pin(p) for p in files}:
            raise ValueError('Sources changed during verification')
        record['status'] = 'PASS_PORT_ONLY_PCIE_CREDITS'
    except BaseException as error:
        record.update(status='FAIL', error=repr(error))
    finally:
        record['outputs'] = {str(p.relative_to(out)): pin(p) for p in out.rglob('*')
                             if p.is_file() and p.name!='result.json' and 'sim' not in p.relative_to(out).parts}
        save()
    print(record['status'], record.get('tests', record.get('error')))
    return int(record['status'] != 'PASS_PORT_ONLY_PCIE_CREDITS')


if __name__ == '__main__':
    raise SystemExit(main())
