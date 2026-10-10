#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare array/macro RAM with the same cocotb bus stimulus; require real PDK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pdk', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--macro-source', type=Path, help='Explicit scratch source for negative controls')
    ap.add_argument('--harden', type=int, choices=(0, 1), default=1)
    ap.add_argument('--rdreg', type=int, choices=(0, 1), default=1)
    ap.add_argument('--words', type=int, choices=(8192, 16384), default=8192)
    args = ap.parse_args()
    if args.words == 16384 and args.harden:
        ap.error('16384-word macro mapping is unprotected only')
    tool = shutil.which('iverilog')
    if not tool:
        ap.error('iverilog is required on PATH')
    version = subprocess.run([tool, '-V'], capture_output=True, text=True, check=True).stdout
    match = re.search(r'Icarus Verilog version (\d+)', version)
    if not match or int(match[1]) < 13:
        ap.error('Native IHP SRAM models require Icarus >=13; version 12 returns unknown read data')
    from cocotb_tools.runner import get_runner
    root = Path(__file__).resolve().parents[3]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    inputs = [root / 'hw/soc/rtl/soc_mem.v', root / 'hw/soc/rtl/soc_mem_sram.v',
              root / 'hw/soc/rtl/soc_mem_ecc.v', root / 'hw/rtl/secded_enc.v',
              root / 'hw/rtl/secded_dec.v', root / 'hw/soc/tb/cocotb/tb_soc_mem_parity.v',
              root / 'hw/soc/tb/cocotb/test_soc_mem_parity.py', Path(__file__).resolve()]
    if args.macro_source:
        inputs[1] = args.macro_source.resolve()
    models = args.pdk.resolve() / 'libs.ref/sg13g2_sram/verilog'
    inputs += [models / f for f in ('RM_IHPSG13_1P_2048x64_c2_bm_bist.v',
                                   'RM_IHPSG13_1P_core_behavioral_bm_bist.v')]
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    hashes = {str(p): digest(p) for p in inputs}
    (out / 'inputs.json').write_text(json.dumps(hashes, indent=2) + '\n')
    renamed = []
    for path, name in zip(inputs[:2], ('soc_mem_array', 'soc_mem_macro')):
        text, count = re.subn(r'(?m)^module soc_mem\b', 'module ' + name, path.read_text())
        assert count == 1
        target = out / (name + '.v')
        target.write_text(text)
        renamed.append(target)
    sources = renamed + inputs[2:6] + inputs[-2:]
    # Only the declarations in private copies are renamed so both alternatives
    # can coexist. The RTL and every PDK model remain untouched and hash-bound.
    os.environ.update(PARITY_WORDS=str(args.words), PARITY_RDREG=str(args.rdreg))
    runner = get_runner('icarus')
    result = dict(passed=False, sources_unchanged=False, words=args.words,
                  harden=args.harden, rdreg=args.rdreg, tests=0,
                  macro_source_override=bool(args.macro_source),
                  scope='RAM bus parity; not timing or ROM initialization')
    try:
        runner.build(sources=sources, hdl_toplevel='tb_soc_mem_parity',
                     parameters=dict(WORDS=args.words, HARDEN=args.harden, RDREG=args.rdreg),
                     build_dir=out / 'build', always=True, timescale=('1ns', '1ps'))
        shutil.copy2(inputs[6], out / inputs[6].name)
        runner.test(hdl_toplevel='tb_soc_mem_parity', test_module='test_soc_mem_parity',
                    test_dir=out, results_xml='results.xml')
    finally:
        xml = out / 'results.xml'
        if xml.exists():
            cases = list(ET.parse(xml).getroot().iter('testcase'))
            result['tests'] = len(cases)
            result['passed'] = len(cases) == 1 and all(
                c.find('failure') is None and c.find('error') is None
                and c.find('skipped') is None for c in cases)
        result['sources_unchanged'] = all(digest(Path(p)) == h for p, h in hashes.items())
        result['passed'] &= result['sources_unchanged']
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
