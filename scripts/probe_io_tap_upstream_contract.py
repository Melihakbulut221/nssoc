#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict upstream tap regression and geometry-identical hierarchy negative control."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import urllib.request

import run_io_parent_lvs as native

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT/'hw/soc/pnr/io-tap-upstream-contract.lock.json'
SELF = ROOT/'scripts/probe_io_tap_upstream_contract.py'
OWN = ('scripts/probe_io_tap_upstream_contract.py', 'sw/tests/test_io_tap_upstream_contract.py',
       'hw/soc/pnr/io-tap-upstream-contract.lock.json')
TOP = 'test_ntap_ptap_ext_deep'
COMMIT = '5e6d592e4002946a4616f798c357f0f3c06cf3b6'
CASES = ('original', 'wrong_perimeter', 'reversed_terminals', 'wrong_top_port', 'promoted_markers')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def lock():
    value = json.loads(LOCK.read_text())
    require(value['schema'] == 1 and value['commit'] == COMMIT and value['top'] == TOP,
            'Wrong independent upstream source identity')
    expected = {'test_ntap_ptap_ext_deep.gds', 'test_ntap_ptap_ext_deep.cdl',
                'test_ntap_ptap_ext_deep.yaml', 'run_regression.py'}
    require(len(value['files']) == 4 and {r['name'] for r in value['files']} == expected,
            'Incomplete upstream fixture inventory')
    for row in value['files']:
        require(row['name'] == Path(row['path']).name and '..' not in Path(row['path']).parts
                and not Path(row['path']).is_absolute()
                and row['url'] == 'https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+COMMIT+'/'+row['path']
                and 0 < row['bytes'] < 200000 and len(row['sha256']) == 64
                and len(row['git_blob']) == 40, 'Unsafe or unpinned upstream input')
    require(value['markers'] == dict(layers=[[31, 0], [40, 0]], shapes=7, cells=['nmos', 'pmos']),
            'Unexpected hierarchy-only mutation')
    return value


def verify_raw(raw, row):
    require(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'],
            'Upstream input byte identity differs')
    require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == row['git_blob'],
            'Upstream Git blob identity differs')


def reference_variant(original, variant):
    replacements = {
      'wrong_perimeter': ('RT1 VSS B_SUB ptap1 A=21.276p P=141.84u',
                          'RT1 VSS B_SUB ptap1 A=21.276p P=200u'),
      'reversed_terminals': ('RT1 VSS B_SUB ptap1 A=21.276p P=141.84u',
                             'RT1 B_SUB VSS ptap1 A=21.276p P=141.84u'),
      'wrong_top_port': ('.SUBCKT test_ntap_ptap_ext_deep VDD VSS vin vout',
                         '.SUBCKT test_ntap_ptap_ext_deep VDD VSS wrong_vin vout')}
    require(variant in CASES, 'Unknown strict comparison case')
    if variant in ('original', 'promoted_markers'):
        return original
    before, after = replacements[variant]
    require(original.count(before) == 1, 'Independent reference line changed')
    return original.replace(before, after)


def command(deck, gds, schematic, output):
    args = [str(native.APP), 'klayout', '-b', '-zz', '-r', str(deck)]
    for key, value in dict(input=gds, schematic=schematic, topcell=TOP, report=output/'lvs.lvsdb.gz',
                          log=output/'deck.log', target_netlist=output/'extracted.cir',
                          run_mode='deep', thr=1, disable_tap_extraction='false',
                          ignore_top_ports_mismatch='false').items():
        args.extend(['-rd', f'{key}={value}'])
    return args


def execute(args, log):
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2*1024**3,)*2)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    started = time.monotonic()
    with log.open('x') as stream:
        result = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT,
                                preexec_fn=limits, timeout=120, check=False)
    return dict(command=args, returncode=result.returncode, elapsed_seconds=time.monotonic()-started,
                address_space_limit_bytes=2*1024**3, watchdog_seconds=120)


def shape_snapshot(layout):
    return {cell.name: {'instances': sorted((inst.cell.name, str(inst.cplx_trans), str(inst.a), str(inst.b), inst.na, inst.nb)
                             for inst in cell.each_inst()),
        'layers': {str(layout.get_info(idx)): sorted(str(s) for s in cell.shapes(idx).each())
                   for idx in layout.layer_indices()}}
        for cell in layout.each_cell()}


def promote(original, destination, report):
    import klayout.db as db
    before = db.Layout(); before.read(str(original)); after = db.Layout(); after.read(str(original))
    require(before.dbu == .001 and [c.name for c in before.top_cells()] == [TOP], 'Unexpected upstream geometry')
    top = after.top_cell(); moved = []
    for name in ('nmos', 'pmos'):
        cell = after.cell(name); require(cell is not None and cell.child_instances() == 0, 'Unexpected tap hierarchy')
        uses = [(c, i) for c in after.each_cell() for i in c.each_inst() if i.cell.name == name]
        require(len(uses) == 1 and uses[0][0].name == TOP and not uses[0][1].is_regular_array(),
                'Marker parent transform is not unique')
        trans = uses[0][1].cplx_trans
        for layer, datatype in ((31, 0), (40, 0)):
            idx = after.find_layer(layer, datatype); require(idx is not None, 'Missing marker layer')
            for shape in list(cell.shapes(idx).each()):
                require(shape.is_box() or shape.is_polygon(), 'Non-polygon marker cannot be promoted')
                polygon = shape.polygon.transformed(trans)
                top.shapes(idx).insert(polygon)
                moved.append(dict(cell=name, layer=f'{layer}/{datatype}', before=str(shape),
                                  transform=str(trans), after=str(polygon)))
            cell.shapes(idx).clear()
    require(len(moved) == 7, 'Expected exactly seven marker shapes')
    after.write(str(destination))
    persisted = db.Layout(); persisted.read(str(destination))
    require(persisted.dbu == before.dbu, 'DBU changed')
    a, b = shape_snapshot(before), shape_snapshot(persisted)
    require(set(a) == set(b), 'Cell inventory changed')
    for name in a:
        require(a[name]['instances'] == b[name]['instances'], 'An instance changed')
        require(set(a[name]['layers']) == set(b[name]['layers']), 'Layer inventory changed')
        for layer in a[name]['layers']:
            if layer not in ('31/0', '40/0') or name not in (TOP, 'nmos', 'pmos'):
                require(a[name]['layers'][layer] == b[name]['layers'][layer], 'Non-marker local geometry changed')
    xor = {}
    for idx in before.layer_indices():
        info = before.get_info(idx); other = persisted.find_layer(info)
        require(other is not None, 'Lost physical layer')
        first = db.Region(before.top_cell().begin_shapes_rec(idx))
        second = db.Region(persisted.top_cell().begin_shapes_rec(other))
        difference = first ^ second; xor[str(info)] = difference.area()
        require(difference.is_empty(), 'Flattened physical geometry changed')
    save(report, dict(status='SEVEN_MARKERS_PROMOTED_ONLY', klayout_version=db.__version__,
                      moved=moved, layer_xor_area_dbu2=xor, all_flat_geometry_preserved=True,
                      non_marker_local_geometry_and_all_instances_preserved=True,
                      original_sha256=native.sha(original), promoted_sha256=native.sha(destination)))


def exact_top_ports(layout, reference):
    expected = ['vdd', 'vin', 'vout', 'vss']
    def top(ports):
        found = [rows for name, rows in ports.items() if name.casefold() == TOP.casefold()]
        return len(found) == 1 and sorted(p.casefold() for p in found[0]) == expected
    return top(layout['ports']) and top(reference['ports'])


def inspect_database(directory):
    import klayout.db as db
    from audit_klayout_lvs import assess, read_pairs
    diagnostics = []
    pairs = read_pairs(directory/'lvs.lvsdb.gz', diagnostics)
    audit = assess(pairs, TOP, (directory/'deck.log').read_text(), diagnostics)
    database = db.LayoutVsSchematic(); database.read(str(directory/'lvs.lvsdb.gz'))
    def census(netlist):
        cells = []; counts = Counter(); taps = []; ports = {}
        for circuit in netlist.each_circuit():
            cells.append(circuit.name)
            ports[circuit.name] = sorted(p.name() for p in circuit.each_pin())
            for device in circuit.each_device():
                kind = device.device_class().name.lower(); counts[kind] += 1
                if kind in ('ptap1', 'ntap1'):
                    taps.append(dict(circuit=circuit.name, kind=kind,
                        parameters={p.name:device.parameter(p.id()) for p in device.device_class().parameter_definitions()},
                        terminals={t.name:device.net_for_terminal(t.id()).name
                                   for t in device.device_class().terminal_definitions()}))
        return dict(circuits=cells, counts=dict(counts), taps=taps, ports=ports)
    layout = census(database.netlist()); reference = census(database.reference)
    ports_match = exact_top_ports(layout, reference)
    strict_reasons = audit['reasons'] + ([] if ports_match else ['Exact four-port top census mismatch'])
    save(directory/'audit.json', dict(audit=audit, klayout_version=db.__version__,
        strict_status='FAIL' if strict_reasons else 'PASS', strict_reasons=strict_reasons,
        exact_top_ports_match=ports_match, layout=layout, reference=reference,
        input_sha256={str(directory/n):native.sha(directory/n) for n in ('lvs.lvsdb.gz', 'deck.log')}))


def check_case(name, value):
    require(name in CASES and value['klayout_version'] == '0.30.7', 'Wrong native case/runtime')
    audit = value['audit']; layout = value['layout']; reference = value['reference']
    expected = {'sg13_lv_nmos': 2, 'sg13_lv_pmos': 2, 'ptap1': 1, 'ntap1': 1}
    require(reference['counts'] == expected, 'Reference device census changed')
    require(audit['extraction_diagnostics'] == [] and audit['circuits'], 'Incomplete or unresolved extraction')
    expected_deck_pass = name in ('original', 'wrong_top_port')
    require(audit['status'] == ('PASS within comparison scope' if expected_deck_pass else 'FAIL'),
            'Captured deck positive/negative result differs')
    require(bool(audit['reasons']) != expected_deck_pass, 'Inconsistent audit verdict')
    ports_match = exact_top_ports(layout, reference)
    strict_reasons = audit['reasons'] + ([] if ports_match else ['Exact four-port top census mismatch'])
    require(value['exact_top_ports_match'] == ports_match == (name != 'wrong_top_port')
            and value['strict_reasons'] == strict_reasons
            and value['strict_status'] == ('FAIL' if strict_reasons else 'PASS')
            and value['strict_status'] == ('PASS' if name == 'original' else 'FAIL'),
            'Complete strict circuit/port audit differs')
    require(layout['counts'] == (dict(sg13_lv_nmos=2, sg13_lv_pmos=2)
                                if name == 'promoted_markers' else expected), 'Native extraction census differs')
    if name != 'promoted_markers':
        require(len(layout['taps']) == 2, 'Missing native tap records')
        expected_taps = lock()['expected_taps']
        require({t['kind'] for t in layout['taps']} == set(expected_taps), 'Missing/duplicated tap kind')
        for tap in layout['taps']:
            e = expected_taps[tap['kind']]
            require(set(tap['parameters']) == {'A', 'P'} and set(tap['terminals']) == {'TIE', 'WELL'},
                    'Wrong tap parameter/terminal API')
            require(all(abs(tap['parameters'][k]-e[k]) < 1e-12 for k in ('A', 'P'))
                    and tap['terminals']['TIE'] == e['TIE']
                    and tap['terminals']['WELL'] not in ('', e['TIE']), 'Literal native tap geometry/terminal differs')
    else:
        require(layout['taps'] == [], 'Expected hierarchy diagnostic did not reproduce')


def run(output, cached=None):
    output = output.resolve(); output.mkdir(parents=True, exist_ok=False)
    value = lock(); result = dict(status='PREPARING', cases={}, diagnostic_only=True,
        original_fixture_unchanged=True, actual_chip_or_io_geometry_changed=False,
        io_lvs_accepted=False, full_chip_lvs_accepted=False, qualified_deck_acceptance=False,
        manufacturing_approval=False)
    target = output/'result.json'; pins = {}
    try:
        native.verify_runtime(native.APP, 'x86_64'); deck, pins = native.verify_deck()
        pins[str(native.APP)] = native.APP_SHA256
        for name, digest in value['method_sha256'].items():
            require(native.sha(ROOT/name) == digest, 'Frozen dependency changed: '+name)
            pins[str(ROOT/name)] = digest
        pins.update({str(ROOT/n):native.sha(ROOT/n) for n in OWN})
        inputs = output/'inputs'; inputs.mkdir()
        for row in value['files']:
            if cached:
                raw = (cached/row['name']).read_bytes()
            else:
                with urllib.request.urlopen(row['url'], timeout=40) as stream:
                    raw = stream.read(row['bytes']+1)
            verify_raw(raw, row); path = inputs/row['name']; path.write_bytes(raw)
            pins[str(path)] = row['sha256']
        require('--ignore_top_ports_mismatch >' in (inputs/'run_regression.py').read_text(),
                'Upstream regression context changed')
        for path in list(pins):
            source = Path(path)
            if source == native.APP or source.is_relative_to(inputs):
                continue
            destination = output/'sources'/source.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(source.read_bytes())
        gds = inputs/'test_ntap_ptap_ext_deep.gds'; cdl = inputs/'test_ntap_ptap_ext_deep.cdl'
        result['promotion_process'] = execute([str(native.APP), 'python', str(SELF), 'promote',
            str(gds), str(inputs/'promoted.gds'), str(output/'promotion.json')], output/'promotion.log')
        require(result['promotion_process']['returncode'] == 0, 'Hierarchy-only geometry proof failed')
        pins[str(inputs/'promoted.gds')] = native.sha(inputs/'promoted.gds')
        result['promotion'] = json.loads((output/'promotion.json').read_text())
        for case in CASES:
            directory = output/case; directory.mkdir()
            schematic = directory/'schematic.cir'; schematic.write_text(reference_variant(cdl.read_text(), case))
            case_gds = inputs/'promoted.gds' if case == 'promoted_markers' else gds
            process = execute(command(deck, case_gds, schematic, directory), directory/'run.log')
            require(process['returncode'] == 0, 'Native deck execution incomplete: '+case)
            inspection = execute([str(native.APP), 'python', str(SELF), 'inspect', str(directory)], directory/'inspect.log')
            require(inspection['returncode'] == 0, 'Native database audit incomplete: '+case)
            review = json.loads((directory/'audit.json').read_text()); check_case(case, review)
            result['cases'][case] = dict(process=process, inspection=inspection, review=review)
            save(target, result)
        native.check_pins(pins)
        result['input_sha256'] = pins
        result['status'] = 'PASS_STRICT_UPSTREAM_CONTROLS_WITH_REPRODUCED_HIERARCHY_FAILURE'
        result['conclusion'] = ('Untouched independent fixture passes strict LVS with literal non-square A/P. '
            'Geometry-identical parent promotion loses both taps and fails. The deck alone misses an unused '
            'renamed reference top port, which the additional exact port census rejects. This qualifies neither project I/O taps '
            'nor a general hierarchy contract; the unresolved I/O intended-geometry/reference contract remains open.')
    except BaseException as exc:
        result.update(status='FAILED_OR_INCOMPLETE_PROBE', error=str(exc)); raise
    finally:
        result['output_sha256'] = {str(p.relative_to(output)):native.sha(p) for p in output.rglob('*')
                                   if p.is_file() and p != target}
        save(target, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='action', required=True)
    root = sub.add_parser('run'); root.add_argument('--output', type=Path, required=True); root.add_argument('--cached', type=Path)
    promote_parser = sub.add_parser('promote')
    for arg in ('original', 'destination', 'report'):
        promote_parser.add_argument(arg, type=Path)
    inspect_parser = sub.add_parser('inspect'); inspect_parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    if args.action == 'run':
        run(args.output, args.cached)
    elif args.action == 'promote':
        promote(args.original, args.destination, args.report)
    else:
        inspect_database(args.directory)


if __name__ == '__main__':
    main()
