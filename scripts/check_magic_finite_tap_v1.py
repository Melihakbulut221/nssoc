#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native finite-tap isolated geometry audit; not full bank or PEX acceptance."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys
import struct

import check_magic_hbt_multiplicity_v3 as h


def validate_fixture(record):
    if record.get('top') != 'nssoc_finite_taps':
        raise ValueError('Wrong fixture top')
    wanted_ports = {f'T{i:03d}' for i in range(132)} | {f'W{i:03d}' for i in range(108, 132)}
    if set(record.get('ports', {})) != wanted_ports or len(record.get('devices', [])) != 132:
        raise ValueError('Exact 108 substrate and 24 well fixtures required')
    for index, row in enumerate(record['devices']):
        model = 'ptap1' if index < 108 else 'ntap1'
        ordinal = index if index < 108 else index-108
        w, length = [(Decimal('.78'), Decimal('.78')), (Decimal(2), Decimal(2)),
                     (Decimal(2), Decimal(3))][ordinal//8 % 3]
        if 24 <= index < 108:
            w = length = Decimal(2)
        wanted = dict(tie=f'T{index:03d}', body='BULK' if model == 'ptap1' else f'W{index:03d}',
                      model=model, w_um=float(w), l_um=float(length), orientation=ordinal % 8)
        if {k: row.get(k) for k in wanted} != wanted or set(row) != set(wanted) | {'resistance_ohm'}:
            raise ValueError('Exact native PCell geometry catalog differs')
        resistance = Decimal(980)/(w*length+2*(w+length))
        if format(row['resistance_ohm'], '.6g') != format(float(resistance), '.6g'):
            raise ValueError('Pinned foundry coefficient formula differs')
    for name, row in record['ports'].items():
        if row.get('layer') != (8 if name.startswith('T') else 31) or len(row.get('box', [])) != 4:
            raise ValueError('Physical port binding differs')


def completed_native(log):
    if log.count('NSSOC_FINITE_TAP_NATIVE_COMPLETE') != 1 or re.search(
            r'Grid scaling is finer|NSSOC devresist|NSSOC terminal component|(^|\n)(Error|ERROR)|Unable to|Unknown command', log):
        raise ValueError('Native execution incomplete or geometry/grid error')


def native_tcl(gds, record, out, grid=1):
    if grid not in (1, 2):
        raise ValueError('Unsupported exact grid refinement')
    for p in (gds, out):
        if any(c in str(p) for c in '{}\n\r'):
            raise ValueError('Unsafe native path')
    lines = ['puts "NSSOC_LOADED_NATIVE_LIBRARIES [info loaded]"', f'cd {{{out}}}',
             'drc off', f'scalegrid {grid} 1',
             'puts "NSSOC_PREIMPORT_GRID_UM [cif scale out]"',
             'gds readonly true', f'gds read {{{gds}}}',
             'load nssoc_finite_taps', 'flatten finite_taps_flat',
             'load finite_taps_flat', 'select top cell']
    for i, (name, p) in enumerate(record['ports'].items(), 1):
        if not re.fullmatch('[TW][0-9]{3}', name):
            raise ValueError('Unexpected tap port')
        layer = {8: 'metal1', 31: 'nwell'}[p['layer']]
        lines += ['box values '+' '.join(str(v)+'um' for v in p['box']),
                  f'label {name} center {layer}', f'port {name} make {i}',
                  f'port {name} class inout', f'port {name} use signal']
    lines += ['save finite_taps_flat', 'extract style ngspice()', 'extract all',
              'ext2spice lvs', 'ext2spice global off', 'ext2spice cthresh infinite',
              'ext2spice extresist off', 'ext2spice -o taps.spice',
              'puts NSSOC_FINITE_TAP_NATIVE_COMPLETE', 'quit -noprompt']
    return '\n'.join(lines)+'\n'


def assess(spice, ext, log, record):
    validate_fixture(record)
    completed_native(log)
    rows = [s.split() for s in h.spice_lines(spice)]
    top = [r for r in rows if r[0].lower() == '.subckt']
    if len(top) != 1 or top[0][1] != 'finite_taps_flat' or set(top[0][2:]) != set(record['ports']) or len(top[0][2:]) != len(record['ports']):
        raise ValueError('Exact tap port inventory differs')
    if not rows or rows[0] != top[0] or rows[-1] != ['.ends']:
        raise ValueError('Unexpected native subcircuit structure')
    devices = rows[1:-1]
    if any(not r[0].startswith('X') or len(r) != 7 for r in devices):
        raise ValueError('Unexpected native device syntax or extra element')
    if len(devices) != len(record['devices']) or any(r[3] not in ('ptap1', 'ntap1') for r in devices):
        raise ValueError('Exact finite tap device inventory differs')
    if len({r[0] for r in devices}) != len(devices):
        raise ValueError('Duplicate device identity')
    by_tie = {r[1]: r for r in devices}
    if len(by_tie) != len(devices) or set(by_tie) != {d['tie'] for d in record['devices']}:
        raise ValueError('Missing, shorted or repeated tap terminal')
    exts = [shlex.split(s) for s in ext.splitlines() if s.startswith('device ')]
    if len(exts) != len(devices):
        raise ValueError('Raw native device census differs')
    raw_by_tie = {}
    for row in exts:
        if row[1] != 'csubckt' or row[2] not in ('ptap1', 'ntap1'):
            raise ValueError('Unexpected raw device')
        # Native csubckt exports: bbox, parameter tokens, substrate, then
        # terminal tuples (name perimeter attribute), preserving both sides.
        start = next((i for i in range(7,len(row)) if '=' not in row[i]), None)
        if start is None or len(row)-start != 7:
            raise ValueError('Malformed raw terminal/parameter inventory')
        terminal = row[start+1]
        if terminal in raw_by_tie:
            raise ValueError('Repeated raw tap terminal')
        raw_by_tie[terminal] = (row, start)
    if set(raw_by_tie) != set(by_tie):
        raise ValueError('Raw/SPICE tie bridge differs')
    bulk = set(); details = []
    scale = [s.split() for s in ext.splitlines() if s.startswith('scale ')]
    if len(scale) != 1:
        raise ValueError('Missing native grid scale')
    unit_um = Decimal(scale[0][3])/100
    for expected in record['devices']:
        row = by_tie[expected['tie']]; raw, start = raw_by_tie[expected['tie']]
        if row[1] == row[2] or row[2] in record['ports'] and expected['model'] == 'ptap1':
            raise ValueError('Finite substrate branch is shorted or externally relabelled')
        if row[3] != expected['model'] or raw[2] != row[3]:
            raise ValueError('Tap model differs')
        if raw[start+1] != row[1] or raw[start+4].removesuffix('!') != row[2]:
            raise ValueError('Raw/SPICE terminal bridge differs')
        params = dict(t.split('=') for t in row[4:])
        rawparams = dict(t.split('=') for t in raw[7:start])
        if set(params) != {'r','w','l'} or set(rawparams) != set(params):
            raise ValueError('Exact supported foundry parameter inventory differs')
        dims = sorted(h.value(params[k])*Decimal('1e6') for k in ('w','l'))
        wanted = sorted(Decimal(str(expected[k])) for k in ('w_um','l_um'))
        if dims != wanted or sorted(Decimal(rawparams[k])*unit_um for k in ('w','l')) != wanted:
            raise ValueError('Native geometry dimensions differ')
        # Native output uses %g: compare its exact six significant-digit
        # rendering of the unmodified PCell calculator, not a fitted tolerance.
        exact_rendering = Decimal(format(expected['resistance_ohm'], '.6g'))
        stored = struct.unpack('f', struct.pack('f', float(exact_rendering)))[0]
        exported = Decimal(format(stored, '.5f'))
        if Decimal(rawparams['r']) != exact_rendering or Decimal(params['r']) != exported:
            raise ValueError('Foundry finite resistance or raw/export bridge differs')
        if expected['model'] == 'ptap1':
            bulk.add(row[2])
        elif row[2] != expected['body']:
            raise ValueError('Native well terminal differs')
        details.append(dict(tie=row[1], body=row[2], model=row[3], parameters=params))
    if len(bulk) != 1:
        raise ValueError('Native common substrate partition differs')
    return dict(status='PASS_ISOLATED_NATIVE_FINITE_TAPS_NO_BANK_ACCEPTANCE',
                ptap_count=108, ntap_count=24, port_count=len(record['ports']),
                native_grid_um=str(unit_um), substrate=next(iter(bulk)), devices=details,
                full_bank_qualified=False, qualified_pex=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--technology', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root/'hw/soc/flow'))
    from check_pcie_rx_cell import execute
    record = json.loads((args.fixture/'result.json').read_text())
    validate_fixture(record)
    for path, sha in record['inputs'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != sha:
            raise ValueError('Native PCell or generator source changed')
    input_paths = [Path(__file__), args.fixture/'result.json', args.runtime/'magic/tcl/tclmagic.so',
                   *args.technology.iterdir(), root/'scripts/check_magic_hbt_multiplicity_v3.py',
                   root/'hw/soc/flow/check_pcie_rx_cell.py']
    before = {str(p): h.pin(p) for p in input_paths if p.is_file()}
    for name, sha in record['outputs'].items():
        if hashlib.sha256((args.fixture/name).read_bytes()).hexdigest() != sha:
            raise ValueError('Source fixture changed')
    args.out.mkdir()
    cases = {}
    for name, filename, grid, positive in [
            ('nominal','fixture.gds',1,True), ('initial_10nm','fixture.gds',2,True),
            ('missing_contact','missing_contact.gds',1,False),
            ('width_change','width_change.gds',1,False),
            ('tie_short','tie_short.gds',1,False)]:
        path=args.out/name; path.mkdir()
        script=path/'native.tcl'; script.write_text(native_tcl(args.fixture/filename,record,path,grid))
        rt=args.runtime
        execution=execute(['/usr/bin/env','CAD_ROOT='+str(rt),'/usr/bin/tclsh8.6',rt/'magic/tcl/magic.tcl',
                           '-dnull','-noconsole','-rcfile',args.technology/'ihp-sg13g2.magicrc',script],path,'native')
        if execution['returncode'] != 0:
            raise ValueError('Native process failed; not a geometry-negative pass')
        log=(path/'native.log').read_text()
        completed_native(log)
        try:
            outcome=assess((path/'taps.spice').read_text(),(path/'finite_taps_flat.ext').read_text(),log,record)
        except ValueError as exc:
            reasons = {'missing_contact': 'Missing, shorted or repeated tap terminal',
                       'width_change': 'Native geometry dimensions differ',
                       'tie_short': 'Exact tap port inventory differs'}
            if positive or str(exc) != reasons[name]:
                raise
            outcome=dict(status='REJECTED_ACTUAL_GEOMETRY_FAULT',reason=str(exc))
        else:
            if not positive:
                raise ValueError('Actual geometry fault escaped')
            if Decimal(outcome['native_grid_um']) != Decimal('.005')*grid or float(re.search(
                    r'NSSOC_PREIMPORT_GRID_UM ([0-9.]+)', log)[1]) != struct.unpack('f', struct.pack('f', .005*grid))[0]:
                raise ValueError('Requested native grid was not actually applied')
        cases[name]=dict(execution=execution,outcome=outcome,
                        outputs={p.name:h.pin(p) for p in path.iterdir() if p.is_file()})
    if any(h.pin(Path(p)) != value for p, value in before.items()):
        raise ValueError('Native source/runtime changed during execution')
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != value for p, value in record['inputs'].items()):
        raise ValueError('PCell source changed during execution')
    result=dict(status='PASS_ISOLATED_NATIVE_TAP_CONTROLS',cases=cases,
                inputs=before,
                technology={p.name:h.pin(p) for p in args.technology.iterdir() if p.is_file()},
                qualification=False)
    (args.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__ == '__main__':
    main()
