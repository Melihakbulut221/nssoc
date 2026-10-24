#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Isolated strict Vss LVS with coherent upstream GDS/CDL/LEF and native deck.

No active PDK or chip view is updated. A mismatch is retained as a failure;
reference A/P, ordered terminals and undeclared globals are never inferred.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import urllib.request

import extract_gds_hierarchy as gds
import io_tap_topology_audit as topology
import run_io_parent_lvs as native
from io_tap_contract_audit import quantity
from io_cell_schematic import parse_io_cdl, read_io_cdl_text, select_io_cdl

ROOT = Path(__file__).resolve().parents[1]
TOP = 'sg13g2_IOPadVss'
COMMIT = '5e6d592e4002946a4616f798c357f0f3c06cf3b6'
VIEWS = {
    'gds': (71424000, '6cbc6d5fd5a90932e8a96ea6493085767e844b55'),
    'cdl': (38738, 'fb26e68b55bddf20c28a523f7676beba582920fd'),
    'lef': (96886, '4ad7181d2871258b6afa151e5835dfa06eadadfb'),
}
GDS_PREFIX_BYTES = 71422884
GDS_ZERO_PADDING_BYTES = 1116
METHODS = (
    'scripts/run_coherent_io_lvs.py', 'scripts/run_io_parent_lvs.py',
    'scripts/extract_gds_hierarchy.py', 'scripts/io_tap_topology_audit.py',
    'scripts/io_tap_contract_audit.py', 'hw/soc/flow/io_cell_schematic.py',
    'hw/soc/flow/transistor_schematic.py', 'hw/soc/flow/audit_klayout_lvs.py',
    'hw/soc/flow/prepare_ihp_drc.py', 'hw/soc/flow/prepare_ihp_lvs.py',
    'scripts/bootstrap_flow.py', 'scripts/fetch_evidence_assets.py',
    'sw/tests/io_parent_lvs_native.py', '.github/workflows/coherent-io-lvs.yml',
)


def metadata(kind):
    size, blob = VIEWS[kind]
    path = f'{topology.VIEW_BASE}/{kind}/sg13g2_io.{kind}'
    return dict(size=size, sha=blob, path=path,
                html_url=f'{topology.REPO}/blob/{COMMIT}/{path}',
                download_url=f'https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/{COMMIT}/{path}')


def download_view(kind, destination):
    expected = metadata(kind)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Upstream view output must be fresh')
    count = 0
    with urllib.request.urlopen(expected['download_url'], timeout=60) as response, destination.open('xb') as output:
        while chunk := response.read(1024**2):
            count += len(chunk)
            if count > expected['size']:
                raise ValueError('View download exceeds the pinned byte count')
            output.write(chunk)
    return topology.verify_view(destination, expected, COMMIT, kind)


def normalize_main_taps(text):
    """Only XR->R for the current explicit two-node A/P primitive dialect."""
    if '\r' in text:
        raise ValueError('Only exact LF CDL is supported')
    lines = text.splitlines(keepends=True)
    changes = []
    for index, line in enumerate(lines):
        words = line.split()
        if not words or not words[0].upper().startswith('XR'):
            continue
        if (len(words) != 6 or not re.fullmatch(r'XR[0-9]+', words[0])
                or words[3] not in ('ptap1', 'ntap1')
                or not words[4].startswith('A=') or not words[5].startswith('P=')
                or any(quantity(token.split('=', 1)[1]) <= 0 for token in words[4:])):
            raise ValueError('Unsupported main-library tap dialect: '+line.rstrip())
        offset = len(line)-len(line.lstrip())
        replacement = line[:offset]+line[offset+1:]
        changes.append(dict(line=index+1, before=line, after=replacement,
                            reason='R-prefixed native CustomTap; same ordered nodes and explicit A/P'))
        lines[index] = replacement
    restored = lines.copy()
    for change in changes:
        restored[change['line']-1] = change['before']
    if ''.join(restored) != text:
        raise ValueError('Tap conversion is not byte reversible')
    return ''.join(lines), changes


def vss_reference(raw):
    """Select the exact independently checked three-cell contract before adapting.

    Other library cells include two model-less XR declarations in this commit;
    no model is invented for them. Any extra selected dependency still fails
    the ordinary strict reachable-cell check below.
    """
    definitions, globals_ = parse_io_cdl(raw)
    wanted = {TOP.casefold(), *topology.CHILD_MAPS}
    bodies = {name: body for name, body in definitions.items() if name.casefold() in wanted}
    if len(bodies) != 3:
        raise ValueError('The checked Vss reference closure requires three exact cells')
    prefix = '.GLOBAL '+' '.join(globals_)+'\n' if globals_ else ''
    selected_raw = prefix+'\n\n'.join(bodies.values())+'\n'
    adapted, changes = normalize_main_taps(selected_raw)
    selected, reachable, selected_globals = select_io_cdl(adapted, TOP)
    if set(reachable) != set(bodies) or selected_globals != globals_:
        raise ValueError('Selected reference dependency/global closure differs')
    return selected_raw, selected, changes, list(reachable), globals_


def unpad_coherent_gds(source, destination):
    """Retain the pinned original; remove only its exact zero tail after ENDLIB.

    The derived prefix is subsequently validated by the unchanged strict GDS
    extractor. No record, coordinate, label or cell is rewritten here.
    """
    if source.resolve() == destination.resolve() or destination.exists() or destination.is_symlink():
        raise FileExistsError('Unpadded derivative must be a fresh distinct file')
    expected = topology.verify_view(source, metadata('gds'), COMMIT, 'gds')
    if expected['bytes'] != GDS_PREFIX_BYTES+GDS_ZERO_PADDING_BYTES:
        raise ValueError('Pinned GDS/prefix/padding lengths differ')
    source_hash, prefix_hash = hashlib.sha256(), hashlib.sha256()
    created = False
    try:
        with os.fdopen(os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError('Pinned GDS must be a regular file')
            with destination.open('xb') as output:
                created = True
                remaining, last = GDS_PREFIX_BYTES, b''
                while remaining:
                    chunk = stream.read(min(1024**2, remaining))
                    if not chunk:
                        raise ValueError('Truncated GDS prefix')
                    remaining -= len(chunk)
                    source_hash.update(chunk)
                    prefix_hash.update(chunk)
                    output.write(chunk)
                    last = (last+chunk)[-4:]
                if last != bytes.fromhex('00040400'):
                    raise ValueError('Expected exact ENDLIB at the pinned prefix boundary')
                tail = stream.read(GDS_ZERO_PADDING_BYTES+1)
                if len(tail) != GDS_ZERO_PADDING_BYTES or any(tail):
                    raise ValueError('Expected only the exact zero padding after ENDLIB')
                source_hash.update(tail)
            after = os.fstat(stream.fileno())
            visible = source.stat()
            identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
            if identity(before) != identity(after) or identity(after) != identity(visible):
                raise ValueError('Original GDS changed while copying its prefix')
        if source_hash.hexdigest() != expected['sha256'] or native.sha(destination) != prefix_hash.hexdigest():
            raise ValueError('Original or derived GDS digest changed')
        return dict(status='EXACT_ZERO_PADDING_ONLY_DERIVATIVE', original=expected,
            prefix=dict(bytes=GDS_PREFIX_BYTES,sha256=prefix_hash.hexdigest()),
            padding=dict(bytes=GDS_ZERO_PADDING_BYTES,sha256=hashlib.sha256(tail).hexdigest(),all_zero=True),
            endlib_offset=GDS_PREFIX_BYTES-4,endlib_hex='00040400',
            original_retained=True,padding_only_difference=True,geometry_records_modified=False,
            strict_prefix_validation='Required separately by unchanged extract_gds_hierarchy.py',lvs_accepted=False)
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise


def prepare(output):
    inputs = output/'inputs'
    inputs.mkdir()
    views = {}
    for kind in VIEWS:
        path = inputs/f'sg13g2_io.{kind}'
        views[kind] = dict(metadata=metadata(kind), identity=download_view(kind, path))
    raw = read_io_cdl_text(inputs/'sg13g2_io.cdl')
    contract = topology.audit(raw, read_io_cdl_text(inputs/'sg13g2_io.lef'))
    if contract['status'] != 'REFERENCE_TOPOLOGY_MATCH' or contract['formal_order'] != ['vdd','vss','iovdd','iovss']:
        raise ValueError('Pinned main Vss named topology or formal order differs')
    selected_raw, selected, changes, cells, globals_ = vss_reference(raw)
    with (inputs/'schematic.cir').open('x') as stream:
        stream.write(selected)
    with (inputs/'selected-source.cdl').open('x') as stream:
        stream.write(selected_raw)
    unpadded = inputs/'unpadded-source.gds'
    padding = unpad_coherent_gds(inputs/'sg13g2_io.gds', unpadded)
    subset = gds.extract(unpadded, [TOP], inputs/'subset', padding['prefix']['sha256'])
    permutations = topology.migration_indices(['iovdd','iovss','vdd','vss'], contract['formal_order'])
    if permutations != [2,3,0,1]:
        raise ValueError('Unexpected old-caller migration contract')
    receipt = dict(status='PREPARED_COHERENT_VSS_NATIVE_LVS_PENDING', commit=COMMIT, views=views,
        reference_contract=contract, dialect_changes=changes, dialect_line_scope='selected-source.cdl',
        explicit_globals=globals_, selected_subcircuits=cells, subset=subset, padding_transport_adapter=padding,
        ordered_pin_contract=dict(current_formals=contract['formal_order'],
            old_formals=['iovdd','iovss','vdd','vss'], old_actual_indices_for_new_order=permutations,
            old_callers_changed=False, parent_wrapper_added=False),
        globals_inferred=False, geometry_changed=False, tap_parameters_changed=False,
        full_chip_lvs_accepted=False, manufacturing_approval=False)
    native.write_json(inputs/'preparation.json', receipt)
    return receipt


def command(deck, inputs, case, mode):
    if mode not in ('deep', 'flat'):
        raise ValueError('Only strict deep or flat comparison is supported')
    args = [str(native.APP), 'klayout', '-b', '-zz', '-r', str(deck)]
    values = dict(input=inputs/'subset/subset.gds', schematic=inputs/'schematic.cir',
        topcell=TOP, report=case/'lvs.lvsdb.gz', log=case/'deck.log',
        target_netlist=case/'extracted.cir', run_mode=mode, thr=1,
        disable_tap_extraction='false', ignore_top_ports_mismatch='false')
    for key, value in values.items():
        args.extend(['-rd', f'{key}={value}'])
    return args


def strict_verdict(case, execution, audit_execution):
    expected = [case/name for name in ('lvs.lvsdb.gz','deck.log','extracted.cir','audit.json')]
    if execution['returncode'] != 0 or any(not p.is_file() or not p.stat().st_size for p in expected):
        raise ValueError('Incomplete native Vss extraction/comparison')
    audit = json.loads((case/'audit.json').read_text())
    if audit.get('top') != TOP or not audit.get('circuits'):
        raise ValueError('Missing strict native top/circuits')
    replay = native.assess(audit['circuits'], TOP, (case/'deck.log').read_text(), audit.get('extraction_diagnostics', []))
    if any(audit.get(key) != value for key, value in replay.items()):
        raise ValueError('Native audit cannot be independently replayed')
    if not ((audit.get('status') == 'PASS within comparison scope' and audit_execution['returncode'] == 0 and not audit.get('reasons'))
            or (audit.get('status') == 'FAIL' and audit_execution['returncode'] == 1 and audit.get('reasons'))):
        raise ValueError('Inconsistent native comparison/audit verdict')
    for name in ('lvs.lvsdb.gz','deck.log'):
        path = case/name
        if audit.get('inputs', {}).get(str(path)) != {'bytes':path.stat().st_size,'sha256':native.sha(path)}:
            raise ValueError('Audit is not bound to the exact native reports')
    return audit


def run(output, controls):
    output = output.resolve()
    if not output.is_relative_to(native.OUTPUT_ROOT.resolve()):
        raise ValueError('Output must remain inside NSSOC hw/soc/out')
    output.mkdir(parents=True, exist_ok=False)
    record = dict(schema=1, status='PREPARING', upstream_commit=COMMIT, top=TOP, cases={},
        source_sha=os.environ.get('GITHUB_SHA'), run_id=os.environ.get('GITHUB_RUN_ID'),
        scope='Isolated coherent-library Vss deep/flat diagnostic; no active PDK, layout, parent or caller mutation',
        cell_lvs_accepted=False, full_chip_lvs_accepted=False, manufacturing_approval=False,
        active_pdk_updated=False, original_layout_changed=False)
    result = output/'result.json'
    native.write_json(result, record)
    try:
        record['launch_available_memory_bytes'] = native.require_resources()
        free_disk = shutil.disk_usage(output).free
        if free_disk < 2*native.GIB:
            raise ValueError('Coherent I/O comparison requires 2 GiB free disk on the isolated worker')
        record['launch_free_disk_bytes'] = free_disk
        pins = {str(ROOT/name):native.sha(ROOT/name) for name in METHODS}
        record['controls'] = native.validate_controls(controls)
        pins.update(record['controls']['input_sha256'])
        pins.update(record['controls']['output_sha256'])
        pins[str(controls.resolve())] = native.sha(controls)
        deck, deck_pins = native.verify_deck()
        pins.update(deck_pins)
        native.verify_runtime(native.APP, 'x86_64')
        pins[str(native.APP)] = native.APP_SHA256
        record['preparation'] = prepare(output)
        pins.update({str(path):native.sha(path) for path in (output/'inputs').rglob('*') if path.is_file()})
        record['input_sha256'] = pins
        native.write_json(result, record)
        for mode in ('deep','flat'):
            native.check_pins(pins)
            case = output/mode
            case.mkdir()
            row = dict(status='RUNNING', launch_available_memory_bytes=native.require_resources())
            record['cases'][mode] = row
            record['status'] = 'RUNNING_'+mode.upper()
            native.write_json(result, record)
            row['native'] = native.execute(command(deck, output/'inputs', case, mode), case/'run.log')
            native.write_json(result, record)
            args = [str(native.APP), 'python', str(native.AUDIT), str(case/'lvs.lvsdb.gz'),
                    '--top', TOP, '--deck-log', str(case/'deck.log'), '--output', str(case/'audit.json')]
            row['audit_process'] = native.execute(args, case/'audit.log')
            row['audit'] = strict_verdict(case, row['native'], row['audit_process'])
            row['status'] = row['audit']['status']
            row['output_sha256'] = {str(p):native.sha(p) for p in case.iterdir() if p.is_file()}
            native.check_pins(pins)
            native.write_json(result, record)
        passed = all(row['status'] == 'PASS within comparison scope' for row in record['cases'].values())
        record.update(status='PASS_COHERENT_VSS_ONLY' if passed else 'FAIL_COHERENT_VSS_LVS', cell_lvs_accepted=passed)
        native.write_json(result, record)
        return record
    except Exception as error:
        record.update(status='ERROR_OR_INCOMPLETE_COHERENT_VSS', error=repr(error))
        native.write_json(result, record)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--controls', type=Path, required=True)
    args = parser.parse_args()
    try:
        row = run(args.output, args.controls)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, str(error)+'\n')
    print(row['status'])
    return 0 if row['status'] == 'PASS_COHERENT_VSS_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
