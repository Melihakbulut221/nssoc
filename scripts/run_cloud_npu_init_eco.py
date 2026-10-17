#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Qualify one exact mapped Boolean ECO against unchanged vendor-model boot."""
import argparse
import json
import os
from pathlib import Path
import shutil

import check_npu_reconvergence_eco as native
import prepare_npu_reconvergence_eco as eco
import run_cloud_alu_qualification as q

ROOT = Path(__file__).resolve().parents[1]
OWN = ('scripts/prepare_npu_reconvergence_eco.py', 'scripts/check_npu_reconvergence_eco.py',
       'scripts/run_cloud_npu_init_eco.py', 'sw/tests/test_npu_reconvergence_eco.py',
       '.github/workflows/timing-npu-init-eco.yml')


def compile_command(original, source, candidate, executable):
    command = list(original)
    q.require(command.count(str(source)) == 1 and command.count('-o') == 1
              and command.count('-DTIMEOUT_CYCLES=3000000') == 1,
              'Original native compile source/output/workload differs')
    command[command.index(str(source))] = str(candidate)
    command[command.index('-o') + 1] = str(executable)
    return command


def verify_eco(output, row):
    source = Path(row['eco']['original_netlist_path'])
    candidate = output / 'eco/soc_top.netlist.v'
    q.common.verify_file(source, row['original_sources'][str(source)])
    q.require(eco.prepare(source.read_bytes()) == candidate.read_bytes(), 'ECO output differs from exact reversible transformation')
    expected = compile_command(row['original_compile']['command'], source, candidate,
                               Path(row['compiled_simulation_path']))
    q.require(row['compile']['command'] == expected, 'Unexpected modified native compile command')
    expected_sources = dict(row['original_sources'])
    del expected_sources[str(source)]
    expected_sources[str(candidate)] = q.pin(candidate)
    q.require(row['sources'] == expected_sources, 'Any other model/firmware/bench input changed')
    q.common.verify_file(output / 'compiled/original.vvp', row['original_compiled_simulation'])
    q.common.verify_file(output / 'compiled/factored.vvp', row['compiled_simulation'])
    for label, negative in [('factored', False), ('miswired_mux', True)]:
        directory = output / 'native-controls' / label
        q.require((directory / 'tb.v').read_text() == native.bench(negative), 'Native gate control source differs')
        parsed = native.parse((directory / 'run.log').read_text(), negative)
        q.require(parsed == row['eco']['native_controls']['results'][label]['observation'], 'Native control result differs')
        q.require(all(e['returncode'] == 0 for e in row['eco']['native_controls']['results'][label]['executions']), 'Native control did not complete')
    for name in OWN:
        q.common.verify_file(ROOT / name, row['methods'][name])


def prepare(output, work):
    q.require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full SoC preparation requires cloud runner')
    q.boot_prepare(output, work, 'candidate', 'vendor', None)
    row = json.loads((output / 'result.json').read_text())
    try:
        q.verify_outputs(output, row)
        q.require(row['status'] == 'COMPILED_READY_FOR_FOUR_STATE_BOOT' and row['cycle_bound'] == 3000000,
                  'Incomplete unchanged boot preparation')
        shutil.copyfile(output / 'result.json', output / 'original-preparation.json')
        row['original_sources'] = dict(row['sources'])
        row['original_compile'] = row['compile']
        row['original_compiled_simulation'] = row['compiled_simulation']
        row['original_compiled_simulation_path'] = row['compiled_simulation_path']
        (output / 'compiled').mkdir()
        shutil.copyfile(row['original_compiled_simulation_path'], output / 'compiled/original.vvp')
        source = work / 'producer/synthesis-candidate/soc_top.netlist.v'
        candidate = output / 'eco/soc_top.netlist.v'
        candidate.parent.mkdir()
        candidate.write_bytes(eco.prepare(source.read_bytes()))
        tools = work / 'oss-cad-suite/bin'
        controls = native.run(work / 'inputs/models/sg13g2_stdcell.v', output / 'native-controls',
                              str(tools / 'iverilog'), str(tools / 'vvp'))
        row['eco'] = dict(original_netlist_path=str(source), original=q.pin(source), candidate=q.pin(candidate),
                          original_gate=eco.OLD, retained_predecessor=eco.PREDECESSOR, replacement=eco.NEW,
                          binary_truth_table=eco.binary_truth_table(), native_controls=controls,
                          scope=eco.__doc__)
        for name in OWN:
            destination = output / 'methods' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
            row['methods'][name] = q.pin(destination)
        executable = work / 'npu-init-eco.vvp'
        command = compile_command(row['original_compile']['command'], source, candidate, executable)
        row['compile'] = q.alu.execute(command, output, 'eco-compile')
        q.require(row['compile']['returncode'] == 0, 'Real ECO netlist compile failed')
        del row['sources'][str(source)]
        row['sources'][str(candidate)] = q.pin(candidate)
        row['compiled_simulation'] = q.pin(executable)
        row['compiled_simulation_path'] = str(executable)
        shutil.copyfile(executable, output / 'compiled/factored.vvp')
        row['boot_command'] = [str(tools / 'vvp'), '-i', str(executable), '+flash0=' + str(output / 'firmware/flash0.hex')]
        verify_eco(output, row)
        for name, expected in row['sources'].items():
            q.common.verify_file(Path(name), expected)
        row['status'] = 'COMPILED_READY_FOR_FOUR_STATE_BOOT'
        row['scope'] = 'One exact Boolean mapped ECO; native controls pass. Unchanged 3M vendor-model MBIST/28-check boot required. No layout or timing acceptance.'
    except Exception as error:
        row.update(status='NPU_INIT_ECO_PREPARATION_FAILED', error=repr(error))
        raise
    finally:
        q.finish(output, row)


def run(output):
    row = json.loads((output / 'result.json').read_text())
    verify_eco(output, row)
    # This original strict runner raises on failed MBIST or fewer than28checks.
    # A green job therefore requires the actual repaired boot to pass.
    q.boot_resume(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work', type=Path)
    args = parser.parse_args()
    if args.phase == 'prepare':
        q.require(args.work is not None, 'Preparation needs isolated work path')
        prepare(args.output.resolve(), args.work.resolve())
    else:
        run(args.output.resolve())


if __name__ == '__main__':
    main()
