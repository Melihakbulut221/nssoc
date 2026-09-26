#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Lint the prepared SoC; reject any change to the explicit diagnostic ledger.

The ledger retains frozen/upstream warnings as technical debt, not clean RTL.
No warning class is disabled. Every diagnostic, including intentional ones,
keeps its path, line, column, message and multiplicity. Updating it is a review
operation, deliberately not a command-line option on the acceptance runner.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'hw/soc/flow'))
from interface_profile import resolve

POLICY = ROOT/'hw/soc/lint-policy.json'
WARNING = re.compile(r'^%Warning-([A-Z0-9_]+): (.*?):(\d+):(\d+): (.*)$')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diagnostics(log, root=ROOT, aliases=None):
    rows = Counter()
    for line in log.splitlines():
        if not line.startswith('%Warning'): continue
        match = WARNING.fullmatch(line)
        if not match: raise ValueError('Unparsed diagnostic: '+line)
        code, path, number, column, message = match.groups()
        absolute = str(Path(path).resolve())
        relative = (aliases or {}).get(absolute)
        if relative is None: relative = Path(absolute).relative_to(root.resolve()).as_posix()
        key = json.dumps([code, relative, int(number), int(column), message], separators=(',', ':'))
        rows[key] += 1
    return rows


def compare(actual, expected):
    return dict(new=dict(actual-Counter(expected)), stale=dict(Counter(expected)-actual))


def owned_policy(rows):
    """Noninformational own-RTL diagnostics need an exact architectural reason."""
    issues = []
    informational = {'UNUSEDPARAM', 'UNUSEDSIGNAL', 'PINCONNECTEMPTY', 'GENUNNAMED', 'DECLFILENAME'}
    gates = ('soc_top.u_ibex.core_clock_gate_i.en_latch',
             'soc_top.g_clkgate.u_npu_cg.en_latch', 'soc_top.g_clkgate.u_bus_cg.en_latch')
    resets = {'hw/soc/rtl/soc_top.v': ('soc_top.rst_sync', 'soc_top.por_sync'),
              'hw/soc/rtl/soc_eth.v': tuple('soc_top.u_eth.'+x+'_reset' for x in ('logic','rx','tx'))}
    for key in rows:
        code, path, _, _, message = json.loads(key)
        if not path.startswith('hw/soc/rtl/'): continue
        if code in informational: continue
        if code == 'LATCH' and path == 'hw/soc/rtl/prim_clock_gating.v' and any(
            message == f"Latch inferred for signal '{g}' (not all control paths of combinational always assign a value)" for g in gates): continue
        if code == 'SYNCASYNCNET' and any(message == f"Signal flopped as both synchronous and async: '{r}'" for r in resets.get(path, ())): continue
        issues.append(key)
    return issues


def nettype_errors(root=ROOT):
    files = sorted((root/'hw/soc/rtl').rglob('*.v')) + [root/'hw/soc/rtl/soc_logic_boot_rom.v.in']
    errors = []
    for path in files:
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', path.read_text(), flags=re.S)
        # Timescale may precede the guard; no declarations may escape it.
        text = re.sub(r'^\s*`timescale[^\n]*', '', text)
        if (not text.lstrip().startswith('`default_nettype none') or
            not text.rstrip().endswith('`default_nettype wire') or
            text.count('`default_nettype none') != 1 or text.count('`default_nettype wire') != 1):
            errors.append(str(path.relative_to(root)))
    return errors


def physical_regfile(text):
    """Select exactly the chparam SYNPRE=1 used by synthesis, in an output copy.

    Verilator's -G applies only to the top module. Ibex has no public SYNPRE
    parameter, so this local default substitution selects the same parameter
    without editing the tracked drop-in register file or the upstream core.
    """
    old = 'parameter integer SYNPRE = 0;'
    if text.count(old) != 1: raise ValueError('Unexpected register-file SYNPRE declaration')
    return text.replace(old, 'parameter integer SYNPRE = 1;')


def sources(profile):
    soc = ROOT/'hw/soc'
    bundle, define = resolve(profile, soc)
    env = dict(os.environ, IBEX_REGFILE='secded', IBEX_FAULT_PORT='1', IBEX_GEN='gen')
    ibex = subprocess.check_output(['bash','-c',
        'source hw/soc/flow/ibex_sources.sh; ibex_sources "$PWD/hw/soc"'], cwd=ROOT, env=env, text=True)
    files = [Path(p).resolve() for p in ibex.splitlines()]
    files += [p for p in sorted((soc/'rtl').glob('*.v')) if p.name not in ('soc_mem_sram.v','ibex_regfile_secded.v')]
    files += [ROOT/'hw/rtl'/name for name in ('tmr_voter.v','pilot_top.v','lif_core.v','aer_fifo.v','scrub.v')]
    files = list(dict.fromkeys(files)) + [bundle]
    watched = files + list((soc/'rtl').glob('*.vh')) + list((ROOT/'hw/rtl').glob('*.vh'))
    watched += [bundle.with_suffix('.json'), POLICY, Path(__file__), ROOT/'hw/soc/flow/ibex_sources.sh']
    return files, define, {str(p.relative_to(ROOT)):sha(p) for p in watched}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=['base','full'], default=os.environ.get('SOC_INTERFACE_PROFILE','base'))
    parser.add_argument('--memory', choices=['array','sram-logic'], default='array')
    parser.add_argument('--mbist', action='store_true', help='Power-on system SRAM MBIST; requires sram-logic')
    parser.add_argument('--rom-image', type=Path, help='Compiled loader binary; required for sram-logic lint')
    parser.add_argument('--output', type=Path, default=ROOT/'hw/soc/out/lint')
    suite = Path(os.environ.get('OSS_CAD_SUITE',ROOT/'hw/soc/tools/oss-cad-suite'))
    parser.add_argument('--verilator', type=Path, default=suite/'bin/verilator')
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT/'hw/soc/out'): parser.error('Output must be inside hw/soc/out')
    if out.exists(): parser.error('Refusing to replace evidence: '+str(out))
    if args.mbist and args.memory != 'sram-logic': parser.error('--mbist requires --memory sram-logic')
    if args.memory == 'sram-logic' and not args.rom_image: parser.error('sram-logic requires --rom-image')
    if args.memory == 'array' and args.rom_image: parser.error('--rom-image requires sram-logic')
    if args.rom_image and not args.rom_image.resolve().is_relative_to(ROOT): parser.error('ROM image must be inside this repository')
    policy = json.loads(POLICY.read_text())
    errors = nettype_errors()
    if errors: parser.error('Nettype discipline failed: '+', '.join(errors))
    files, define, hashes = sources(args.profile)
    version = subprocess.check_output([str(args.verilator),'--version'],text=True).strip()
    if version != policy['verilator_version']: parser.error('Unreviewed Verilator version: '+version)
    out.mkdir(parents=True)
    aliases = {}
    additional = []
    rom_manifest = None
    profile_key = args.profile
    if args.memory == 'sram-logic':
        from gen_logic_boot_rom import generate
        generator_inputs = [args.rom_image.resolve(), ROOT/'hw/soc/rtl/soc_logic_boot_rom.v.in',
                            ROOT/'hw/soc/flow/gen_logic_boot_rom.py', ROOT/'sw/golden/secded.py']
        hashes.update({str(p.relative_to(ROOT)):sha(p) for p in generator_inputs})
        rom_manifest = generate(args.rom_image, out/'boot-rom')
        rom = out/'boot-rom/soc_logic_boot_rom.v'
        rf_source = ROOT/'hw/soc/rtl/ibex_regfile_secded.v'
        rf_copy = out/'ibex_regfile_secded.v'
        rf_copy.write_text(physical_regfile(rf_source.read_text()))
        macros = [ROOT/'hw/soc/pnr'/f'RM_IHPSG13_1P_{size}_c2_bm_bist_bb.v'
                  for size in ('2048x64','1024x32','512x16')]
        files = [ROOT/'hw/soc/rtl/soc_mem_sram.v' if p.name == 'soc_mem.v' else
                 rf_copy if p == rf_source else p for p in files]
        files += [rom] + macros
        aliases = {str(rom):'hw/soc/rtl/soc_logic_boot_rom.v.in', str(rf_copy):str(rf_source.relative_to(ROOT))}
        additional = ['-DSOC_LOGIC_BOOT_ROM','-GWAKE_GNT=1']
        watched = files + [out/'boot-rom/manifest.json']
        hashes.update({str(p.relative_to(ROOT)):sha(p) for p in watched})
        profile_key += '-sram-logic'
    if args.mbist:
        mbist_files = sorted((ROOT/'hw/soc/rtl/dft').glob('*.v'))
        files += mbist_files
        hashes.update({str(p.relative_to(ROOT)):sha(p) for p in mbist_files})
        additional.append('-DSOC_SRAM_MBIST')
        profile_key += '-mbist'
    command = [str(args.verilator.resolve()), '--lint-only', '--Wall', '-Wno-fatal', '--top-module', 'soc_top',
               '--timing', '--Mdir', str(out/'obj_dir'), '-DSG13G2_ICG_BEHAVIOURAL', '-GMEM_RDREG=1', '-GREQ_REG=1',
               '-I'+str(ROOT/'hw/soc/rtl'), '-I'+str(ROOT/'hw/rtl')]
    if define: command.append(define)
    command += additional + list(map(str, files))
    with (out/'verilator.log').open('x') as stream:
        proc = subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=180)
    log = (out/'verilator.log').read_text()
    actual = diagnostics(log, aliases=aliases)
    delta = compare(actual,policy['profiles'][profile_key])
    own_issues = owned_policy(actual)
    unchanged = all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in hashes.items())
    immutable_drift = [p for p,h in policy['immutable_sha256'].items()
                       if p in hashes and hashes[p] != h]
    passed = (proc.returncode == 0 and '- Verilator: Built from ' in log and
              bool(actual) and not any(delta.values()) and not own_issues and unchanged and not immutable_drift)
    record = dict(status='PASS_WITH_RECORDED_WARNINGS' if passed else 'FAIL', profile=profile_key,
                  scope='soc_top RTL lint, MEM_RDREG=1, REQ_REG=1; array uses SYNPRE=0/WAKE_GNT=0; sram-logic uses SYNPRE=1/WAKE_GNT=1, SRAM blackboxes, generated fixed ROM; no mapped-netlist or physical/CDC signoff',
                  rom_manifest=rom_manifest, diagnostic_aliases=aliases,
                  command=command,returncode=proc.returncode,verilator_version=version,source_sha256=hashes,
                  sources_unchanged=unchanged,immutable_drift=immutable_drift,diagnostics=dict(actual),
                  counts=dict(Counter({code:sum(n for k,n in actual.items() if json.loads(k)[0]==code)
                                       for code in {json.loads(k)[0] for k in actual}})),
                  delta=delta,own_unaccepted=own_issues,log_sha256=sha(out/'verilator.log'))
    (out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    if not passed: raise SystemExit('FAIL: inspect '+str(out/'result.json'))
    print(f'PASS with {sum(actual.values())} explicitly recorded warnings ({profile_key}); not warning-free RTL')


if __name__ == '__main__':
    main()
