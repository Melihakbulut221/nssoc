#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Tiny native parent-connectivity controls; generic geometry, not IHP signoff.

Run with the pinned AppImage Python and a fresh output directory. Hierarchical
geometry is extracted before flattening a copy for strict graph comparison.
No net-name joining, global-net connection, device removal or parameter waiver
is used. The generic TAP class checks both ordered terminals and A/P; it is not
the IHP CustomTap combiner or the production rule deck.
"""
import hashlib
import json
from pathlib import Path
import resource
import sys


LIMIT = 384 * 1024**2
resource.setrlimit(resource.RLIMIT_AS, (LIMIT, LIMIT))
import klayout.db as db
import klayout.dbcore as dbcore


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


class TapClass(db.DeviceClass):
    def __init__(self):
        super().__init__()
        self.name = 'TAP'
        for name in ('TIE', 'WELL'):
            self.add_terminal(db.DeviceTerminalDefinition(name))
        for name in ('A', 'P'):
            self.add_parameter(db.DeviceParameterDefinition(name, name, 0, True))
            self.enable_parameter(name, True)


class TapFactory(db.DeviceClassFactory):
    def create_class(self):
        return TapClass()


def layout(case):
    ly = db.Layout()
    ly.dbu = 0.001
    top, child = ly.create_cell('TOP'), ly.create_cell('CHILD')
    layers = {name: ly.layer(index, 0) for index, name in enumerate(
        ('active', 'poly', 'body', 'contact', 'metal1', 'via1', 'metal2', 'tap_p', 'tap_n'), 1)}

    def box(cell, name, coords):
        cell.shapes(layers[name]).insert(db.Box(*coords))

    def label(cell, name, text, x, y):
        cell.shapes(layers[name]).insert(db.Text(text, db.Trans(x, y)))

    box(child, 'body', (-1000, -1500, 8500, 7000))
    label(child, 'body', 'BODY', -500, -500)
    for number, y in enumerate((0, 4000), 1):
        height = 1200 if case == 'wrong_width' and number == 1 else 1000
        box(child, 'active', (0, y, 4000, y + height))
        gate_right = 2200 if case == 'wrong_length' and number == 1 else 2000
        box(child, 'poly', (1000, y - 1000, gate_right, y + 2000))
        for x, name in ((100, 'S' + str(number)), (2500, 'VDD')):
            box(child, 'metal1', (x, y + 100, x + 800, y + 900))
            box(child, 'contact', (x + 100, y + 300, x + 300, y + 700))
            label(child, 'metal1', name, x + 400, y + 500)
        box(child, 'metal1', (1100, y - 900, 1900, y - 100))
        box(child, 'contact', (1300, y - 700, 1700, y - 300))
        label(child, 'metal1', 'G' + str(number), 1500, y - 500)
    box(child, 'tap_n', (6000, -500, 8000, 2500))
    tie = (6750, 0, 7250, 2000) if case == 'wrong_tap_perimeter' else (6500, 500, 7500, 1500)
    if case == 'wrong_tap_area':
        tie = (6250, 750, 7750, 1250)  # A=0.75; P stays4, isolates A checking.
    box(child, 'tap_p', tie)
    label(child, 'tap_p', 'TIE', 7000, 1000)
    top.insert(db.CellInstArray(child.cell_index(), db.Trans()))
    if case != 'same_name_open':
        box(top, 'metal2', (2700, 300, 3200, 4700))
    box(top, 'via1', (2800, 300, 3100, 700))
    if case != 'missing_via':
        box(top, 'via1', (2800, 4300, 3100, 4700))
    return ly, layers


def extract(ly, layers):
    l2n = db.LayoutToNetlist(db.RecursiveShapeIterator(ly, ly.cell('TOP'), []))
    regions = {name: l2n.make_layer(index, name) for name, index in layers.items()}
    gate = regions['active'] & regions['poly']
    sd = regions['active'] - gate
    l2n.extract_devices(db.DeviceExtractorMOS4Transistor('NMOS'),
                       {'SD': sd, 'G': gate, 'tG': regions['poly'],
                        'W': regions['body'], 'tB': regions['body']})
    factory = TapFactory()
    l2n.extract_devices(db.DeviceExtractorDiode('TAP', factory),
                       {'P': regions['tap_p'], 'N': regions['tap_n']})
    for name in ('poly', 'body', 'contact', 'metal1', 'via1', 'metal2', 'tap_p', 'tap_n'):
        l2n.connect(regions[name])
    l2n.connect(sd)
    for a, b in [('contact', 'metal1'), ('poly', 'contact'), ('metal1', 'via1'),
                 ('via1', 'metal2'), ('tap_n', 'body')]:
        l2n.connect(regions[a], regions[b])
    l2n.connect(sd, regions['contact'])
    l2n.extract_netlist()
    return l2n


def schematic(reverse_tap=False):
    netlist = db.Netlist()
    mos = db.DeviceClassMOS4Transistor()
    mos.name = 'NMOS'
    tap = TapClass()
    netlist.add(mos)
    netlist.add(tap)
    circuit = db.Circuit()
    circuit.name = 'TOP'
    netlist.add(circuit)
    nets = {name: circuit.create_net(name) for name in ('G1', 'G2', 'S1', 'S2', 'VDD', 'BODY', 'TIE')}
    for number in (1, 2):
        device = circuit.create_device(mos, 'M' + str(number))
        for terminal, net in {'S': 'S' + str(number), 'G': 'G' + str(number), 'D': 'VDD', 'B': 'BODY'}.items():
            device.connect_terminal(terminal, nets[net])
        for parameter, value in {'W': 1, 'L': 1, 'AS': 1, 'AD': 2, 'PS': 4, 'PD': 6}.items():
            device.set_parameter(parameter, value)
    device = circuit.create_device(tap, 'T1')
    device.connect_terminal('TIE', nets['BODY' if reverse_tap else 'TIE'])
    device.connect_terminal('WELL', nets['TIE' if reverse_tap else 'BODY'])
    device.set_parameter('A', 1)
    device.set_parameter('P', 4)
    return netlist


def run(out):
    out.mkdir(parents=True, exist_ok=False)
    cases = {}
    for name in ('connected', 'same_name_open', 'missing_via', 'wrong_width',
                 'wrong_length', 'wrong_tap_perimeter', 'wrong_tap_area', 'reversed_tap_terminals'):
        directory = out/name
        directory.mkdir()
        ly, layers = layout(name)
        layer_info = {key: ly.get_info(index) for key, index in layers.items()}
        ly.write(str(directory/'layout.gds'))
        # Exercise GDS hierarchy readback, not only the in-memory constructor.
        ly = db.Layout()
        ly.read(str(directory/'layout.gds'))
        layers = {key: ly.layer(info) for key, info in layer_info.items()}
        l2n = extract(ly, layers)
        diagnostics = list(l2n.each_log_entry())
        assert not diagnostics, 'Unexpected native extraction diagnostics'
        l2n.write(str(directory/'hierarchy.l2n'))
        original = l2n.netlist()
        (directory/'hierarchy.txt').write_text(str(original))
        flattened = original.dup()
        flattened.flatten()
        reference = schematic(name == 'reversed_tap_terminals')
        (directory/'layout-netlist.txt').write_text(str(flattened))
        (directory/'reference-netlist.txt').write_text(str(reference))
        actual = db.NetlistComparer().compare(flattened, reference)
        devices = list(flattened.circuit_by_name('TOP').each_device())
        mos = [d for d in devices if d.device_class().name == 'NMOS']
        tap = [d for d in devices if d.device_class().name == 'TAP']
        assert len(mos) == 2 and len(tap) == 1, 'Missing or extra physical devices'
        drain_nets = [d.net_for_terminal('D') for d in mos]
        # Native physical cluster IDs, never labels or Python wrapper identity.
        drain_cluster_ids = [net.cluster_id for net in drain_nets]
        distinct_drain_nets = len(set(drain_cluster_ids))
        expected_drain_nets = 2 if name in ('same_name_open', 'missing_via') else 1
        assert distinct_drain_nets == expected_drain_nets, 'Parent bridge did not control physical connectivity'
        tap_parameters = {p: tap[0].parameter(p) for p in ('A', 'P')}
        expected_tap = {'A': 0.75 if name == 'wrong_tap_area' else 1.0,
                        'P': 5.0 if name == 'wrong_tap_perimeter' else 4.0}
        assert tap_parameters == expected_tap, 'Tap negative control did not isolate expected A/P'
        cases[name] = {'actual_match': actual, 'expected_match': name == 'connected',
                       'hierarchical_circuits': [c.name for c in original.each_circuit()],
                       'distinct_drain_nets_after_parent_extraction': distinct_drain_nets,
                       'drain_cluster_ids': drain_cluster_ids,
                       'extraction_diagnostics': [],
                       'device_counts': {'NMOS4': len(mos), 'TAP': len(tap)},
                       'mos_parameters': [{p: d.parameter(p) for p in ('W', 'L')} for d in mos],
                       'tap_parameters': tap_parameters,
                       'tap_terminal_order': [t.name for t in tap[0].device_class().terminal_definitions()],
                       'mutation_scope': 'reference terminal polarity' if name == 'reversed_tap_terminals' else 'physical geometry',
                       'files': {p.name: sha(p) for p in sorted(directory.iterdir())}}
        print(name, actual, flush=True)
    passed = all(row['actual_match'] == row['expected_match'] for row in cases.values())
    method = Path(__file__).resolve()
    appimage = method.parents[2]/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
    input_paths = (method, appimage)
    runtime_paths = (Path(sys.executable).resolve(), Path(dbcore.__file__).resolve())
    record = {'status': 'PASS_NATIVE_PARENT_CONTEXT_CONTROLS' if passed else 'FAIL',
              'scope': 'Generic hierarchical physical extraction and strict flattened comparison; not IHP deck or Vdd acceptance',
              'klayout_version': db.__version__, 'cases': cases,
              'method_sha256': {'sw/tests/io_parent_lvs_native.py': sha(Path(__file__))},
              'native_bindings': {'path': dbcore.__file__, 'sha256': sha(Path(dbcore.__file__))},
              'input_sha256': {str(path): sha(path) for path in input_paths},
              'runtime_namespace': 'Interpreter and binding paths exist only inside the AppImage /nix/store mount',
              'runtime_namespace_sha256': {str(path): sha(path) for path in runtime_paths},
              'output_sha256': {str(path.resolve()): sha(path) for path in sorted(out.rglob('*')) if path.is_file()},
              'primary_api_docs': ['https://www.klayout.de/doc/code/class_LayoutToNetlist.html',
                                   'https://www.klayout.de/doc/code/class_DeviceExtractorDiode.html',
                                   'https://www.klayout.de/doc/code/class_NetlistComparer.html'],
              'memory_limit_bytes': LIMIT, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'manufacturing_approval': False}
    (out/'result.json').write_text(json.dumps(record, indent=2) + '\n')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(run(Path(sys.argv[1]).resolve()))
