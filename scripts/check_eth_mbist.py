#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Execute dual-clock Ethernet SRAM MBIST, faults and post-test cross-port data.

Native mode uses actual PDK functional models. Replacement mode exercises the
mapped adapter against an explicitly supplied independent SRAM contract model;
neither mode is a transistor/timing/layout qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pdk', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--replacement-model', type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT/'hw/soc/out'):
        parser.error('Output must be inside hw/soc/out')
    out.mkdir(parents=True, exist_ok=False)
    tool = ROOT/'hw/soc/tools/oss-cad-suite/bin'
    files = [ROOT/'hw/soc/rtl/dft'/name for name in
             ('soc_eth_fifo_sram.v', 'soc_sram_mbist.v', 'soc_sram_zero_check.v')]
    files.append(ROOT/'hw/soc/tb/tb_eth_fifo_mbist.v')
    if args.replacement_model:
        files += [ROOT/'hw/soc/techmap/independent_sram_map.v', args.replacement_model.resolve()]
    else:
        sram = args.pdk.resolve()/'libs.ref/sg13g2_sram/verilog'
        files += [sram/name for name in ('RM_IHPSG13_2P_256x16_c2_bm_bist.v',
                  'RM_IHPSG13_2P_core_behavioral_bm_bist_ideal.v',
                  'RM_IHPSG13_2P_core_behavioral_ideal.v')]
    pins = {str(p): sha(p) for p in [*files, Path(__file__), tool/'iverilog', tool/'vvp']}
    result = dict(passed=False, scope=__doc__, replacement=bool(args.replacement_model),
                  input_sha256=pins, cases=[])
    def save():
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    try:
        command = [str(tool/'iverilog'), '-g2012', '-DFUNCTIONAL', '-s',
                   'tb_eth_fifo_mbist', '-o', str(out/'sim.vvp'), *map(str, files)]
        result['compile_command'] = command
        save()
        with (out/'compile.log').open('x') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
        for mode, bank in [(0, 0), (3, 0), (4, 0), (7, 0), (8, 0)] + [(m, b) for m in (1, 2, 5, 6) for b in range(8)]:
            start = time.monotonic()
            name = f'mode{mode}-bank{bank}'
            log = out/(name+'.log')
            with log.open('x') as stream:
                q = subprocess.run([str(tool/'vvp'), str(out/'sim.vvp'),
                                    f'+MODE={mode}', f'+BANK={bank}'], stdout=stream,
                                   stderr=subprocess.STDOUT, timeout=180)
            from check_soc_mbist_integration import passed_log
            passed = q.returncode == 0 and passed_log(log.read_text())
            result['cases'].append(dict(case=name, passed=passed, elapsed=time.monotonic()-start,
                                        log_sha256=sha(log)))
            save()
            if not passed:
                raise RuntimeError('Failed: '+str(log))
        result['sources_unchanged'] = all(sha(Path(p)) == h for p, h in pins.items())
        result['passed'] = result['sources_unchanged'] and len(result['cases']) == 37
    finally:
        save()
    print(f"Ethernet MBIST: {len(result['cases'])} cases; passed={result['passed']}")
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
