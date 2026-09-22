#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Map the PCIe register backend to IHP cells and test unmodified native models."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quote(path):
    return '"'+str(path).replace('\\', '\\\\').replace('"', '\\"')+'"'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--liberty', type=Path, required=True)
    p.add_argument('--models', type=Path, required=True)
    p.add_argument('--yosys', type=Path, required=True)
    p.add_argument('--iverilog-dir', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'hw/soc/out'):
        p.error('Use a fresh directory below hw/soc/out')
    a.liberty, a.models = a.liberty.resolve(), a.models.resolve()
    env = {**os.environ, 'PATH': str(a.iverilog_dir.resolve())+os.pathsep+os.environ['PATH'],
           'PCIE_CFG_ID': '65535'}  # Default unassigned ffff:0000, no RTL overrides.
    iv = subprocess.check_output([str(a.iverilog_dir.resolve()/'iverilog'), '-V'], stderr=subprocess.STDOUT, text=True)
    version = re.search(r'Icarus Verilog version (\d+)', iv)
    if not version or int(version[1]) < 13:
        p.error('Unmodified IHP delayed timing inputs require Icarus >=13')
    out.mkdir(parents=True)
    sources = [ROOT/'hw/soc/rtl/pcie/soc_pcie_tlp_regs.v',
               ROOT/'hw/soc/tb/cocotb/test_soc_pcie_tlp_regs.py',
               ROOT/'hw/soc/tb/cocotb/Makefile.soc_pcie_tlp_regs',
               ROOT/'scripts/cocotb_results.py', Path(__file__).resolve()]
    before = {str(f.relative_to(ROOT)): sha(f) for f in sources}
    record = {'status': 'FAIL', 'scope': 'IHP mapped block simulation; no SDF/layout/link/PHY',
              'inputs': before, 'liberty_sha256': sha(a.liberty), 'models_sha256': sha(a.models),
              'iverilog': iv.splitlines()[0], 'commands': []}
    try:
        script = ('read_liberty -lib '+quote(a.liberty)+'; read_verilog -sv '+quote(sources[0])+
                  '; hierarchy -check -top soc_pcie_tlp_regs; synth -top soc_pcie_tlp_regs -noabc; '
                  'dfflibmap -liberty '+quote(a.liberty)+'; abc -liberty '+quote(a.liberty)+
                  '; clean; check -assert; stat -liberty '+quote(a.liberty)+
                  '; write_json '+quote(out/'mapped.json')+'; write_verilog -noattr -noexpr '+quote(out/'mapped.v'))
        (out/'map.ys').write_text(script+'\n')
        commands = [[str(a.yosys.resolve()), '-Q', '-T', '-s', str(out/'map.ys')],
                    ['make', '-C', str(ROOT/'hw/soc/tb/cocotb'), '-f', 'Makefile.soc_pcie_tlp_regs',
                     'VERILOG_SOURCES='+str(out/'mapped.v')+' '+str(a.models),
                     'COMPILE_ARGS=-g2012 -gspecify', 'PCIE_APB_TIMEOUT=256',
                     'SIM_BUILD='+str(out/'sim'), 'COCOTB_RESULTS_FILE='+str(out/'results.xml')]]
        for index, command in enumerate(commands):
            log = out/f'{index}.log'
            with log.open('x') as stream:
                proc = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=120)
            record['commands'].append({'argv': command, 'returncode': proc.returncode, 'log_sha256': sha(log)})
            assert proc.returncode == 0, 'Command failed: '+str(log)
        cells = json.loads((out/'mapped.json').read_text())['modules']['soc_pcie_tlp_regs']['cells']
        assert cells and all(c['type'].startswith('sg13g2_') for c in cells.values()), 'Unmapped cell'
        assert count_results([out/'results.xml']) == (6, 0, 0), 'Incomplete native simulation'
        assert before == {str(f.relative_to(ROOT)): sha(f) for f in sources}, 'Source drift'
        assert sha(a.liberty) == record['liberty_sha256'] and sha(a.models) == record['models_sha256'], 'Library drift'
        record.update(status='PASS', cells=len(cells), tests={'passed': 6, 'failed': 0, 'skipped': 0},
                      outputs={name: sha(out/name) for name in ('mapped.json', 'mapped.v', 'results.xml', 'map.ys')})
    except (AssertionError, OSError, ValueError, subprocess.SubprocessError) as error:
        record['error'] = str(error)
    (out/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    print(record['status'], record.get('error', 'mapped IHP block, six native-model tests'))
    return int(record['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
