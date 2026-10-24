#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native isolated ESD terminals and measured geometry; no bank/PEX/stress claim."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import shlex
import struct
import sys

import check_magic_hbt_multiplicity_v3 as h

FAULTS = ('width_vdd','width_vss','removed_device','pad_open','pad_short','collector_open','excluded_geometry','well_split')


def operator_assess(mag, expected):
    """Exact Manhattan-region union comparison, including disconnected tiles."""
    if '<< esd_interact_yes >>' not in mag or '<< esd_interact_no >>' not in mag:
        raise ValueError('Native interaction copied an empty region')
    scale = re.findall(r'^magscale (\d+) (\d+)$',mag,re.M)
    if len(scale) > 1 or (scale and Decimal(scale[0][1]) == 0):
        raise ValueError('Ambiguous native MAG scale')
    # MAG omits magscale when the saved geometry uses the technology's
    # unscaled 10-nm lambda. Explicit refinement overrides that default.
    unit = Decimal('.01') if not scale else Decimal('.01')*Decimal(scale[0][0])/Decimal(scale[0][1])
    observed = {'esd_interact_yes':[], 'esd_interact_no':[]}
    layer = None
    for line in mag.splitlines():
        if line.startswith('<< '):
            layer = line[3:-3]
        elif line.startswith('rect ') and layer in observed:
            observed[layer].append([Decimal(x)*unit for x in line.split()[1:]])
        elif line.startswith('tri ') and layer in observed:
            raise ValueError('Unsupported non-Manhattan operator control')
    for layer,key in [('esd_interact_yes','interacting'),('esd_interact_no','noninteracting')]:
        want = [[Decimal(str(x)) for x in row] for row in expected[key]]
        got = observed[layer]
        xs = sorted({x for r in want+got for x in (r[0],r[2])})
        ys = sorted({y for r in want+got for y in (r[1],r[3])})
        if not got or not want:
            raise ValueError('Native interaction copied an empty region')
        for xa,xb in zip(xs,xs[1:]):
            for ya,yb in zip(ys,ys[1:]):
                x,y = (xa+xb)/2,(ya+yb)/2
                inside = lambda rows: any(a < x < c and b < y < d for a,b,c,d in rows)
                if inside(want) != inside(got):
                    raise ValueError('Native interacting/noninteracting polygon differs')
    return dict(status='PASS_NATIVE_GEOMETRIC_REGION_OPERATORS',
                cases=['overlap','edge_touch','disjoint','entire_connected_nonrectangular_region'],
                reference_netlist_used=False)


def value(token):
    match = re.fullmatch(r'(\d+(?:\.\d+)?)([pun]?)', token)
    if match is None:
        raise ValueError('Unsupported native geometry number')
    return Decimal(match[1])*{'':Decimal(1),'p':Decimal('1e-12'),
                             'u':Decimal('1e-6'),'n':Decimal('1e-9')}[match[2]]


def validate_fixture(r):
    if r.get('top') != 'nssoc_esd_fixture' or len(r.get('devices',[])) != 32:
        raise ValueError('Exact 32-device fixture required')
    wanted_ports = {'SUB'} | {f'{p}{i:02d}' for p in ('PAD','VDD') for i in range(32)}
    if set(r.get('ports',{})) != wanted_ports:
        raise ValueError('Exact 65 physical ports required')
    for i,d in enumerate(r['devices']):
        if d != dict(index=i,model='diodevdd_2kv' if i < 16 else 'diodevss_2kv',
                     orientation=i % 8,terminals=[f'VDD{i:02d}',f'PAD{i:02d}','SUB']):
            raise ValueError('Fixture model/orientation/terminal contract differs')
    for name, rows in r['ports'].items():
        if len(rows) != (32 if name == 'SUB' else 1):
            raise ValueError('Physical pin occurrence census differs')
        for p in rows:
            if set(p) != {'layer','box'} or p['layer'] not in (8,10) or len(p['box']) != 4:
                raise ValueError('Physical pin binding differs')


def completed(log):
    if log.count('NSSOC_ESD_NATIVE_COMPLETE') != 1 or log.count('exttospice finished.') != 1 or re.search(
            r'Grid scaling is finer|(^|\n)(Error|ERROR)|Unable to|Unknown command|'
            r'Unrecognized|appears too early|compatible substrate|No matching device', log):
        raise ValueError('Native execution incomplete or technology error')


def native_tcl(gds, record, out, grid=1):
    if grid not in (1,2) or any(c in str(gds)+str(out) for c in '{}\n\r'):
        raise ValueError('Unsafe native path or grid')
    lines = ['puts "NSSOC_LOADED_NATIVE_LIBRARIES [info loaded]"',f'cd {{{out}}}',
             'drc off',f'scalegrid {grid} 1','puts "NSSOC_PREIMPORT_GRID_UM [cif scale out]"',
             'gds readonly true',f'gds read {{{gds}}}', 'load nssoc_esd_fixture',
             'flatten esd_flat','load esd_flat','select top cell']
    for i,(name,rows) in enumerate(record['ports'].items(),1):
        if not re.fullmatch(r'(SUB|PAD[0-9]{2}|VDD[0-9]{2})',name):
            raise ValueError('Unsupported port syntax')
        for p in rows:
            lines += ['box values '+' '.join(str(x)+'um' for x in p['box']),
                      f'label {name} center '+{8:'metal1',10:'metal2'}[p['layer']]]
        lines += [f'port {name} make {i}',f'port {name} class inout',f'port {name} use signal']
    lines += ['save esd_flat','extract style ngspice()','extract all','ext2spice lvs',
              'ext2spice merge none','ext2spice global off','ext2spice cthresh infinite',
              'ext2spice extresist off','ext2spice -o esd.spice',
              'puts NSSOC_ESD_NATIVE_COMPLETE','quit -noprompt']
    return '\n'.join(lines)+'\n'


def assess(spice, ext, log, record):
    validate_fixture(record); completed(log)
    rows = [s.split() for s in h.spice_lines(spice)]
    tops = [r for r in rows if r[0].lower() == '.subckt']
    if len(tops) != 1 or tops[0][1] != 'esd_flat' or len(tops[0][2:]) != 65 or set(tops[0][2:]) != set(record['ports']):
        raise ValueError('Exact ESD port inventory differs')
    if rows[0] != tops[0] or rows[-1] != ['.ends']:
        raise ValueError('Unexpected subcircuit structure')
    devices = rows[1:-1]
    if len(devices) != 32 or any(len(d) != 7 or not d[0].startswith('X') or d[4] not in
                               ('diodevdd_2kv','diodevss_2kv') for d in devices):
        raise ValueError('Exact native ESD device inventory differs')
    if len({d[0] for d in devices}) != 32:
        raise ValueError('Duplicate native instance')
    by_pad = {d[2]:d for d in devices}
    if set(by_pad) != {f'PAD{i:02d}' for i in range(32)}:
        raise ValueError('Native emitter connection differs')
    raw = [shlex.split(s) for s in ext.splitlines() if s.startswith('device ')]
    if len(raw) != 32 or any(len(d) != 14 or d[1] != 'subckt' for d in raw):
        raise ValueError('Raw native device census/syntax differs')
    raw_by_pad = {d[11]:d for d in raw}
    if set(raw_by_pad) != set(by_pad):
        raise ValueError('Raw/SPICE emitter bridge differs')
    scales = [s.split() for s in ext.splitlines() if s.startswith('scale ')]
    if len(scales) != 1:
        raise ValueError('Missing native scale')
    unit = Decimal(scales[0][3])/100
    details = []
    for want in record['devices']:
        d = by_pad[want['terminals'][1]]; e = raw_by_pad[d[2]]
        if d[1:4] != want['terminals'] or d[4] != want['model']:
            raise ValueError('Native ordered ESD terminal/model differs')
        if [e[8],e[11],e[7]] != d[1:4] or e[2] != d[4] or e[9:11] != ['0','0'] or e[12] != '0':
            raise ValueError('Raw/SPICE ordered terminal bridge differs')
        params = dict(s.split('=') for s in d[5:])
        if set(params) != {'ea','ep'}:
            raise ValueError('Native measured emitter parameter inventory differs')
        area, perimeter = map(Decimal,e[13].split(','))
        measured = [value(params['ea'])*Decimal('1e12'),value(params['ep'])*Decimal('1e6')]
        if measured != [area*unit*unit,perimeter*unit]:
            raise ValueError('Raw/SPICE geometry bridge differs')
        if measured != [Decimal('35.0028'),Decimal('58.08')]:
            raise ValueError('Measured native 2-kV emitter geometry differs')
        details.append(dict(model=d[4],terminals=d[1:4],area_um2=str(measured[0]),perimeter_um=str(measured[1])))
    return dict(status='PASS_ISOLATED_NATIVE_ESD_GEOMETRY_AND_TERMINALS',
                count=32, ports=65, native_grid_um=str(unit), devices=details,
                full_bank_qualified=False, qualified_pex=False, esd_stress_qualified=False,
                raw_geometry_annotations_are_not_compact_model_parameters=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('fixture','runtime','technology','out','pdk','appimage'):
        p.add_argument('--'+name,type=Path,required=True)
    a = p.parse_args(); root = Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'hw/soc/flow'))
    from check_pcie_rx_cell import execute
    r = json.loads((a.fixture/'result.json').read_text()); validate_fixture(r)
    for path, sha in r['inputs'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != sha:
            raise ValueError('Fixture source changed')
    for name,sha in r['outputs'].items():
        if hashlib.sha256((a.fixture/name).read_bytes()).hexdigest() != sha:
            raise ValueError('Fixture geometry changed')
    inputs = [Path(__file__),a.fixture/'result.json',a.runtime/'magic/tcl/tclmagic.so',
              *a.technology.iterdir(),root/'scripts/check_magic_hbt_multiplicity_v3.py',
              root/'hw/soc/flow/check_pcie_rx_cell.py',root/'scripts/audit_magic_esd_geometry_v1.py',a.appimage]
    before = {str(x):h.pin(x) for x in inputs if x.is_file()}
    a.out.mkdir(); cases = {}
    for name, grid in [('nominal',1),('initial_10nm',2),*[(n,1) for n in FAULTS]]:
        dest = a.out/name; dest.mkdir()
        script = dest/'native.tcl'
        script.write_text(native_tcl(a.fixture/('fixture.gds' if name in ('nominal','initial_10nm') else name+'.gds'),r,dest,grid))
        rt = a.runtime
        run = execute(['/usr/bin/env','CAD_ROOT='+str(rt),'/usr/bin/tclsh8.6',rt/'magic/tcl/magic.tcl',
                       '-dnull','-noconsole','-rcfile',a.technology/'ihp-sg13g2.magicrc',script],dest,'native')
        if run['returncode'] != 0:
            raise ValueError('Native process failure is not a successful negative control')
        log = (dest/'native.log').read_text(); completed(log)
        native_error = None
        try:
            native_result = assess((dest/'esd.spice').read_text(),(dest/'esd_flat.ext').read_text(),log,r)
        except ValueError as error:
            native_error = str(error)
            native_result = dict(status='FAIL_NATIVE_GRAPH_OR_GEOMETRY',reason=native_error)
        mask_run = execute([a.appimage,'python',root/'scripts/audit_magic_esd_geometry_v1.py',
            '--pdk',a.pdk,'--gds',a.fixture/('fixture.gds' if name in ('nominal','initial_10nm') else name+'.gds'),
            '--top','nssoc_esd_fixture','--out',dest/'geometry.json'],dest,'geometry')
        if mask_run['returncode'] not in (0,1) or not (dest/'geometry.json').exists():
            raise ValueError('Geometry process failure is not a negative control')
        geometry = json.loads((dest/'geometry.json').read_text())
        mask_ok = geometry['status'] == 'PASS_FIXED_NATIVE_ESD_MASKS'
        if mask_run['returncode'] != (0 if mask_ok else 1):
            raise ValueError('Geometry status/exit mismatch')
        reasons = {'width_vdd':'Measured native 2-kV emitter geometry differs',
                   'width_vss':'Measured native 2-kV emitter geometry differs',
                   'removed_device':'Exact native ESD device inventory differs',
                   'pad_open':'Native emitter connection differs',
                   'pad_short':'Exact ESD port inventory differs',
                   'collector_open':'Native ordered ESD terminal/model differs',
                   'excluded_geometry':'Exact native ESD device inventory differs',
                   'well_split':'Native emitter connection differs'}
        if name in FAULTS:
            if native_error != reasons[name]:
                raise ValueError('Actual native fault reason differs')
            if name in ('width_vdd','width_vss','excluded_geometry','well_split') and mask_ok:
                raise ValueError('Semiconductor mask fault escaped')
            if native_error is None and mask_ok:
                raise ValueError('Actual geometry fault escaped')
            result = dict(status='REJECTED_ACTUAL_GEOMETRY_FAULT',reason=native_error,
                          native=native_result,mask_status=geometry['status'])
        else:
            if native_error or not mask_ok or geometry['marker_count'] != 32:
                raise ValueError('Positive native graph/mask result failed')
            result = native_result
            if Decimal(result['native_grid_um']) != Decimal('.005'):
                raise ValueError('Actual native ESD grid differs')
            pre = re.findall(r'NSSOC_PREIMPORT_GRID_UM ([0-9.]+)',log)
            if len(pre) != 1 or float(pre[0]) != struct.unpack('f',struct.pack('f',.005*grid))[0]:
                raise ValueError('Actual preimport grid differs')
            result['requested_preimport_grid_um'] = str(Decimal('.005')*grid)
            result['import_refined_to_preserve_native_5nm_coordinates'] = grid == 2
            result['mask_status'] = geometry['status']
        cases[name] = dict(execution=run,geometry_execution=mask_run,outcome=result,outputs={x.name:h.pin(x) for x in dest.iterdir() if x.is_file()})
    if any(h.pin(Path(x)) != value for x,value in before.items()) or any(
            hashlib.sha256(Path(x).read_bytes()).hexdigest() != value for x,value in r['inputs'].items()):
        raise ValueError('Native source/runtime changed during execution')
    (a.out/'result.json').write_text(json.dumps(dict(status='PASS_ISOLATED_NATIVE_ESD_CONTROLS',
        cases=cases,inputs=before,qualification=False),indent=2)+'\n')


if __name__ == '__main__':
    main()
