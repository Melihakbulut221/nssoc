#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Require reachable failures for six faults in the real-codec scrub proof."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / 'hw/soc/formal'
MUTATIONS = {
    'wrong_write': ('rf_reg_q <= wr_data;', "rf_reg_q <= wr_data ^ 32'h1;"),
    'wrong_check': ('rf_chk_q <= wr_chk;', "rf_chk_q <= wr_chk ^ 8'h1;"),
    'wrong_port_b': ('raw_b = rf_data[raddr_b_i];', 'raw_b = rf_data[raddr_a_i];'),
    'scrub_corruption': ('assign scrub_data = out_s[31:0];',
                         "assign scrub_data = out_s[31:0] ^ 32'h1;"),
    'pointer_skips': ("ptr_q + 5'd1;", "ptr_q + 5'd2;"),
    'pointer_never_stalls': ('else if (scrub_go)    ptr_q <=',
                             "else if (1'b1)        ptr_q <="),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sby', default='sby')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    binary = shutil.which(args.sby)
    if binary is None: parser.error('SymbiYosys is required')
    binary = str(Path(binary).absolute())
    parent = ROOT / 'hw/soc/out/regfile-scrub-controls'
    parent.mkdir(parents=True, exist_ok=True)
    if args.output:
        out = args.output.resolve()
        out.mkdir(parents=True, exist_ok=False)
    else:
        out = Path(tempfile.mkdtemp(prefix='controls-', dir=parent))
    rtl = ROOT / 'hw/soc/rtl/ibex_regfile_secded.v'
    inputs = [rtl, FORMAL / 'regfile_scrub_complete.sby',
              FORMAL / 'regfile_scrub_complete_props.v',
              FORMAL / 'ibex_regfile_contract_props.v',
              ROOT / 'hw/rtl/secded_enc.v', ROOT / 'hw/rtl/secded_dec.v',
              Path(__file__).resolve()]
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    result = dict(source_sha256=hashes, controls=[], passed=False)
    original = rtl.read_text()
    env = {**os.environ, 'PATH': str(Path(binary).parent) + os.pathsep + os.environ['PATH']}
    try:
        for name, (before, after) in MUTATIONS.items():
            if original.count(before) != 1:
                raise RuntimeError(f'{name}: mutation anchor is not unique')
            mutant = out / (name + '.v')
            mutant.write_text(original.replace(before, after))
            config = out / (name + '.sby')
            text = inputs[1].read_text().replace('../rtl/ibex_regfile_secded.v',
                                                 'ibex_regfile_secded.v ' + str(mutant))
            text = text.replace('prove: mode prove', 'prove: mode bmc')
            text = text.replace('prove: depth 3', 'prove: depth 6')
            text = text.replace('timeout 600', 'timeout 90')
            config.write_text(text)
            work = out / name
            log = out / (name + '.log')
            with log.open('w') as stream:
                proc = subprocess.run([binary, '-f', '-d', str(work), str(config), 'prove'],
                                      cwd=FORMAL, env=env, stdout=stream,
                                      stderr=subprocess.STDOUT, timeout=120)
            status = (work / 'status').read_text().split()[0] if (work / 'status').exists() else 'MISSING'
            reached = 'Assert failed' in log.read_text() and (work / 'engine_0/trace.yw').is_file()
            passed = status == 'FAIL' and proc.returncode == 2 and reached
            result['controls'].append(dict(name=name, status=status, returncode=proc.returncode,
                                           reachable_counterexample=reached, passed=passed,
                                           mutant_sha256=digest(mutant), log_sha256=digest(log)))
            if not passed: raise RuntimeError(f'{name}: expected reachable FAIL; got {status}')
            print(f'{name}: expected reachable FAIL', flush=True)
        result['passed'] = True
    finally:
        result['sources_unchanged'] = all(digest(ROOT / p) == h for p, h in hashes.items())
        result['passed'] &= result['sources_unchanged']
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if not result['passed']: raise RuntimeError('Source changed during controls')


if __name__ == '__main__':
    main()
