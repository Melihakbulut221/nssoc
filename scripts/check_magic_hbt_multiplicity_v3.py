#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded native Nx fixture audit, with the separate finite-tap defect explicit."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import sys

import patch_magic_hbt_multiplicity_v3 as patcher

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PINS = {
    'fixture.gds': 'e5f18713d2c7ccb7d0390f38a237de2cc7b8dfc19ef123f508070fcb6d595934',
    'result.json': '1da7b6be96bb94632f9a7251e68e606f3d0d4a9ffc81b767f9e8e6034944dd70',
    'schematic.cir': 'e50ff7ceb1e5e4119fcf2709c1e966e98461f2218ed9c45d6438cf2a544cb30e',
}
PORTS = [f'{t}_N{n}_T{o}' for n in (1, 2, 4) for o in range(8) for t in 'CBE'] + ['SUB']


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(p):
    data = Path(p).read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def spice_lines(text):
    result = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('*'):
            continue
        if line.startswith('+'):
            require(bool(result), 'Orphan continuation')
            result[-1] += ' ' + line[1:].strip()
        else:
            result.append(line.strip())
    return result


def value(text):
    match = re.fullmatch(r'(-?\d+(?:\.\d+)?)([num]?)', text)
    require(match is not None, 'Unexpected native numeric token')
    return Decimal(match[1]) * {'': Decimal(1), 'n': Decimal('1e-9'), 'u': Decimal('1e-6'), 'm': Decimal('1e-3')}[match[2]]


def assess(spice, ext, log):
    require(log.count('exttospice finished.') == 1, 'Native extraction did not finish exactly once')
    require(not re.search(r'(?im)^(?:segmentation|traceback|fatal|error:)', log), 'Native failure cannot be a geometry result')
    rows = [s.split() for s in spice_lines(spice)]
    require(rows and rows[0][:2] == ['.subckt', 'hbt_axis_flat'] and rows[-1] == ['.ends'], 'Unexpected native subcircuit')
    ports = rows[0][2:]
    require(len(ports) == len(set(ports)), 'Duplicate native port')
    devices = rows[1:-1]
    require(all(len(r) == 9 and r[0].startswith('X') and r[5] == 'npn13g2' for r in devices), 'Unexpected native device syntax/model')
    require(len({r[0] for r in devices}) == len(devices), 'Duplicate native instance')
    extrows = [shlex.split(s) for s in ext.splitlines() if s.startswith('device ')]
    require(len(extrows) == len(devices), 'Native EXT/SPICE device count differs')
    require('parameters npn13g2 w1=le l1=we n1=Nx\n' in ext, 'Native component-count parameter missing')
    observed = []
    for r in devices:
        params = dict(token.split('=') for token in r[6:])
        require(set(params) == {'we', 'le', 'Nx'}, 'Exact native parameter set required')
        observed.append(dict(nodes=r[1:5], we=str(value(params['we'])), le=str(value(params['le'])), Nx=str(value(params['Nx']))))
    require('scale 1000 1 0.5\n' in ext, 'Frozen native extraction grid changed')
    native_ext = []
    for r in extrows:
        require(len(r) == 20 and r[:3] == ['device', 'msubckt', 'npn13g2'], 'Unexpected native EXT syntax/model')
        params = dict(token.split('=') for token in r[7:10])
        require(set(params) == {'w1', 'l1', 'Nx'}, 'Exact raw EXT parameters required')
        native_ext.append(dict(nodes=[n.removesuffix('!') for n in (r[17], r[11], r[14], r[10])],
                               we=str(Decimal(params['l1']) * Decimal('5e-9')),
                               le=str(Decimal(params['w1']) * Decimal('5e-9')),
                               Nx=str(Decimal(params['Nx']))))
    # Compare source geometry expectations, independently of the C implementation.
    expected = [dict(nodes=[f'{t}_N{n}_T{o}' for t in 'CBE'] + ['SUB'], we=str(Decimal('70e-9')), le=str(Decimal('900e-9')), Nx=str(Decimal(n))) for n in (1, 2, 4) for o in range(8)]
    canon = lambda row: (tuple(row['nodes']), Decimal(row['we']), Decimal(row['le']), Decimal(row['Nx']))
    aliases = {}

    def representative(node):
        node = node.removesuffix('!')  # Native ext2spice global off removes this marker.
        while node in aliases:
            node = aliases[node]
        return node

    equivalences = [shlex.split(line) for line in ext.splitlines() if line.startswith('equiv ')]
    for row in equivalences:
        require(len(row) == 3, 'Malformed native node equivalence')
        a, b = representative(row[1]), representative(row[2])
        if a != b:
            aliases[max(a, b)] = min(a, b)
    bridge_canon = lambda row: (tuple(representative(n) for n in row['nodes']), *canon(row)[1:])
    require(sorted(map(bridge_canon, native_ext)) == sorted(map(bridge_canon, observed)), 'Raw EXT/SPICE parameters or terminals differ')
    # Expected fixture graph is deliberately NOT collapsed by native equivalences:
    # a real short must remain a mismatch, not redefine the golden conductors.
    complete = len(observed) == 24 and len({canon(r) for r in observed}) == 24 and sorted(map(canon, observed)) == sorted(map(canon, expected)) and set(ports) == set(PORTS)
    errors = log.count('NSSOC terminal component geometry/connectivity failure')
    return dict(status='PASS_24_NATIVE_HBT_MULTIPLICITIES_ONLY' if complete and errors == 0 else 'GEOMETRY_MISMATCH_PRESERVED', hbts=len(observed), ports=len(ports), observed=observed, native_equivalences=equivalences, component_errors=errors, finite_tap_retained=False, substrate_model='Native Magic still identifies SUB with the bulk and omits the finite tap; separate known defect, never whole-device-network acceptance.', qualified_pex=False)


def native_tcl(gds, fixture, out):
    require(set(fixture['ports']) == set(PORTS), 'Exact fixture port map required')
    for path in (gds, out):
        require(not re.search(r'[{}\n\r]', str(path)), 'Unsafe native path')
    lines = ['puts "NSSOC_LOADED_NATIVE_LIBRARIES [info loaded]"', f'cd {{{out}}}', 'drc off', 'gds readonly true', f'gds read {{{gds}}}', 'load nssoc_hbt_axis', 'flatten hbt_axis_flat', 'load hbt_axis_flat', 'select top cell']
    for i, name in enumerate(PORTS, 1):
        row = fixture['ports'][name]
        require(row['layer'] in (8, 10) and len(row['box']) == 4, 'Wrong native pin geometry')
        lines += ['box values ' + ' '.join(f'{v}um' for v in row['box']), f'label {name} center metal{1 if row["layer"] == 8 else 2}', f'port {name} make {i}', f'port {name} class inout', f'port {name} use signal']
    return '\n'.join(lines + ['save hbt_axis_flat', 'extract style ngspice()', 'extract all', 'feedback save feedback.tcl', 'ext2spice lvs', 'ext2spice global off', 'ext2spice cthresh infinite', 'ext2spice extresist off', 'ext2spice -o hbt.spice', 'quit -noprompt', ''])


def run(fixture, technology, build, out, faults):
    require(not out.exists(), 'Fresh output required')
    for name, sha in FIXTURE_PINS.items():
        require(pin(fixture / name)['sha256'] == sha, 'Frozen native fixture changed')
    build_record = json.loads((build / 'result.json').read_text())
    runtime = build / 'runtime/lib'
    require(pin(runtime / 'magic/tcl/tclmagic.so')['sha256'] == build_record['runtime_sha'], 'Native runtime changed')
    source = build / 'source/extract/ExtBasic.c'
    original = Path('/dev/shm/nssoc-hbt-terminal-build-02/source/extract/ExtBasic.c')
    require(source.read_bytes() == patcher.patch(original.read_bytes()), 'Compiled source differs from exact private patch')
    require(pin(source)['sha256'] == build_record['source_after_sha'], 'Build source pin differs')
    require(all(r['returncode'] == 0 for r in build_record['execution']), 'Private build failed')
    require(set(faults) == {'emitter_via_open_N2_T1', 'base_collector_short_N4_T6', 'missing_finger_N4_T7', 'emitter_width_N1_T1', 'missing_tap_contact', 'unchanged_clone_N4_T7'}, 'Exact geometry control inventory required')
    out.mkdir(parents=True)
    target = out / 'tech'
    shutil.copytree(technology, target)
    p = target / 'ihp-sg13g2-extract.tech'
    p.write_bytes(patcher.patch_technology(p.read_bytes()))
    sys.path.insert(0, str(ROOT / 'hw/soc/flow'))
    from check_pcie_rx_cell import execute
    record = dict(status='RUNNING', inputs={str(p): pin(p) for p in [Path(__file__).resolve(), Path(patcher.__file__), original, source, build / 'result.json', runtime / 'magic/tcl/tclmagic.so', *(fixture / n for n in FIXTURE_PINS), *faults.values()]}, technology={p.name: pin(p) for p in target.iterdir() if p.is_file()}, cases={}, qualified_pex=False)
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    fixtures = {'original': fixture / 'fixture.gds', **faults}
    for name, gds in fixtures.items():
        d = out / name
        d.mkdir()
        script = d / 'native.tcl'
        script.write_text(native_tcl(gds, json.loads((fixture / 'result.json').read_text()), d))
        ex = execute(['/usr/bin/env', 'CAD_ROOT=' + str(runtime), '/usr/bin/tclsh8.6', runtime / 'magic/tcl/magic.tcl', '-dnull', '-noconsole', '-rcfile', target / 'ihp-sg13g2.magicrc', script], d, 'native')
        require(ex['returncode'] == 0, 'Native extraction process failed')
        log = (d / 'native.log').read_text()
        require(f'NSSOC_LOADED_NATIVE_LIBRARIES {{{runtime}/magic/tcl/tclmagic.so Tclmagic}}' in log, 'Loaded native runtime not witnessed')
        result = assess((d / 'hbt.spice').read_text(), (d / 'hbt_axis_flat.ext').read_text(), log)
        expected = name in ('original', 'unchanged_clone_N4_T7')
        require((result['status'] == 'PASS_24_NATIVE_HBT_MULTIPLICITIES_ONLY') == expected, 'Unexpected physical control disposition: ' + name)
        record['cases'][name] = dict(execution=ex, measurement=result, missing_tap_contact_fault=(name == 'missing_tap_contact'), outputs={p.name: pin(p) for p in d.iterdir() if p.is_file()})
        (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
        print(name, result['status'], flush=True)
    for name, expected in record['inputs'].items():
        require(pin(name) == expected, 'Native experiment input changed')
    record['status'] = 'PASS_NATIVE_24_HBT_NX_FIVE_GEOMETRY_FAULTS_WITH_FINITE_TAP_MODEL_BLOCKER'
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ('fixture', 'technology', 'build', 'faults', 'out'):
        parser.add_argument('--' + n, type=Path, required=True)
    args = parser.parse_args()
    faults = {p.stem: p for p in args.faults.glob('*.gds')}
    try:
        run(args.fixture, args.technology, args.build, args.out, faults)
    except Exception as error:
        receipt = args.out / 'result.json'
        if receipt.is_file():
            record = json.loads(receipt.read_text())
            record.update(status='FAILED_OR_INCOMPLETE', error=repr(error))
            receipt.write_text(json.dumps(record, indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()
