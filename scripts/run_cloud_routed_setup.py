#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reproduce routed timing then screen a source-bound, four-cell setup ECO."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
from read_opensta_phase_slacks import parse_phases

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-routed-setup'
APP = Path(os.environ['CLOUD_APPIMAGE'])


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    OUT.mkdir(exist_ok=False)
    result = dict(status='RUNNING', adopted=False,
                  scope='Actual routed baseline is remeasured. Candidate and paired baseline use fresh placement RC and require new routing/extraction/DRC before adoption. Full PHY and SRAM/RC qualification remain open.')
    def save():
        (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    def execute(command, log, env=None, expected_success=True):
        with log.open('w') as stream:
            rc = subprocess.call([str(x) for x in command], cwd=ROOT, env=env,
                                 stdout=stream, stderr=subprocess.STDOUT)
        text = log.read_text(errors='replace')
        if expected_success:
            if rc != 0 or re.search(r'(?m)^(?:Error:|\[ERROR)', text):
                print(f'Native command failed ({rc}); {log}:\n{text[-12000:]}', flush=True)
                raise RuntimeError(f'Native command failed ({rc}): {log}')
        return rc, text
    save()
    try:
        spec = json.loads((ROOT / 'docs/evidence/cloud-routed-setup-input-20261012.json').read_text())
        archive = OUT / 'input.tar.gz'
        subprocess.run(['curl', '--fail', '--location', '--retry', '4', spec['archive_url'], '-o', str(archive)], check=True)
        assert sha(archive) == spec['sha256']
        inputs = OUT / 'inputs'
        with tarfile.open(archive) as tar:
            tar.extractall(inputs, filter='data')
        manifest = json.loads((inputs / 'manifest.json').read_text())
        assert all(sha(inputs / name) == pin['sha256'] for name, pin in manifest['files'].items())
        original = json.loads((inputs / manifest['baseline_result']).read_text())
        template = (inputs / manifest['original_tcl']).read_text()
        for old, name in sorted(manifest['paths'].items(), key=lambda p:-len(p[0])):
            template = template.replace(old, str(inputs / name))
        odb = inputs / manifest['paths'][original['binding']['observations']['odb']['path']]
        sdc = inputs / manifest['paths'][original['binding']['observations']['sdc']['path']]
        exact = OUT / 'routed-baseline.tcl'
        exact.write_text(template)
        _, text = execute([APP, 'openroad', '-exit', exact], OUT / 'routed-baseline.log')
        measured = parse_phases(text, 'CORNER')
        for phase, values in original['phases'].items():
            assert measured[phase]['groups'].keys() == values['groups'].keys()
            for group, expected in values['groups'].items():
                assert abs(measured[phase]['groups'][group]['worst_slack_ns'] - expected['worst_slack_ns']) <= 1e-6
        result['routed_baseline'] = measured
        save()
        env = dict(os.environ, NSSOC_ROUTED_ODB=str(odb), NSSOC_SETUP_OUT=str(OUT))
        prep = ROOT / 'scripts/prepare_cloud_routed_setup.py'
        execute([APP, 'openroad', '-exit', '-python', prep], OUT / 'preparation.log', env)
        prefix = template.split('puts "Reading OpenROAD database')[0]
        result['estimates'] = {}
        for label in ('baseline', 'buffered'):
            dest = OUT / label
            dest.mkdir()
            lines = [prefix, f'read_db {{{OUT / (label + ".odb")}}}', f'read_sdc {{{sdc}}}',
                     'set_propagated_clock [all_clocks]']
            if label == 'buffered':
                lines.append('detailed_placement')
            lines += ['check_placement -verbose', 'global_connect',
                      'set_wire_rc -signal -layer Metal2', 'set_wire_rc -clock -layer Metal4',
                      'estimate_parasitics -placement',
                      f'write_db {{{dest / "placed.odb"}}}', f'write_def {{{dest / "placed.def"}}}',
                      f'write_verilog {{{dest / "netlist.v"}}}', f'write_sdc {{{dest / "placed.sdc"}}}']
            for corner in ('slow','typical','fast'):
                for delay in ('max','min'):
                    lines += [f'puts CORNER_{corner}_{delay}', f'report_checks -corner {corner} -path_delay {delay} -group_path_count 10 -fields {{slew cap fanout}} -digits 6']
                lines += [f'puts ELECTRICAL_{corner}', f'report_check_types -corner {corner} -max_slew -max_capacitance -max_fanout -violators -digits 6']
            script = dest / 'screen.tcl'
            script.write_text('\n'.join(lines) + '\n')
            assert 'read_spef' not in script.read_text()
            _, text = execute([APP, 'openroad', '-exit', script], dest / 'screen.log')
            result['estimates'][label] = parse_phases(text, 'CORNER')
            save()
        execute([APP, 'openroad', '-exit', '-python', prep], OUT / 'geometry-audit.log',
                dict(env, NSSOC_SETUP_MODE='audit'))
        libs = [inputs / name for name in manifest['files'] if name.endswith('_typ_1p20V_25C.lib')]
        standard = next(p for p in libs if 'stdcell' in str(p))
        proof = [APP, 'python3', ROOT / 'hw/soc/flow/check_eco_logic.py',
                 OUT / 'baseline/netlist.v', OUT / 'buffered/netlist.v', '--liberty', standard,
                 '--output', OUT / 'logic']
        for lib in libs:
            if lib != standard:
                proof += ['--macro-liberty', lib]
        execute(proof, OUT / 'logic.log')
        logic = json.loads((OUT / 'logic/result.json').read_text())
        assert logic['status'] == 'PASS within scope'
        result['logic'] = logic
        result['geometry'] = json.loads((OUT / 'geometry-audit.json').read_text())
        netlist = (OUT / 'buffered/netlist.v').read_text()
        pattern = r'sg13g2_buf_16\s+nssoc_setup_nand4_buffer01\s*\((.*?)\);'
        match = re.search(pattern, netlist, re.S)
        assert match
        bad = netlist[:match.start()] + 'sg13g2_inv_1 nssoc_setup_nand4_buffer01 (' + re.sub(r'\.X\s*\(', '.Y(', match[1]) + ');' + netlist[match.end():]
        fault = OUT / 'inverted-buffer.v'
        fault.write_text(bad)
        negative = [str(x) for x in proof]
        negative[negative.index(str(OUT / 'buffered/netlist.v'))] = str(fault)
        negative[negative.index(str(OUT / 'logic'))] = str(OUT / 'logic-negative')
        rc, log = execute(negative, OUT / 'logic-negative.log', expected_success=False)
        assert rc != 0 and 'Non-buffer instance added or removed' in log
        result['inverted_buffer_control'] = 'EXPECTED_FUNCTIONAL_CHANGE_REJECTED'
        before, after = result['estimates']['baseline'], result['estimates']['buffered']
        result['comparison'] = {k: dict(before_ns=v['worst_slack_ns'], after_ns=after[k]['worst_slack_ns'], delta_ns=after[k]['worst_slack_ns']-v['worst_slack_ns']) for k,v in before.items()}
        result['all_group_nonregressing_estimate'] = all(after[k]['groups'][g]['worst_slack_ns'] >= b['worst_slack_ns'] - 1e-6 for k,v in before.items() for g,b in v['groups'].items())
        result['status'] = 'COMPLETE_FOUR_CELL_ESTIMATE_REQUIRES_ROUTING_AND_EXTRACTION'
        assert all(sha(inputs / name) == pin['sha256'] for name,pin in manifest['files'].items())
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
