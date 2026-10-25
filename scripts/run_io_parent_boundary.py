#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare witnessed diagnostic boundary annotations with a named-body overlay.

The original 53-file deck remains byte-pinned and unchanged. One isolated copy
attaches a substrate annotation to physical pwell_sub; no global/implicit joins,
parameter tolerances or port/device guards are changed. Results are diagnostic.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.request

import run_io_parent_marker_repair as marker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'hw/soc/flow'))
import io_parent_boundary as boundary  # noqa: E402

native = marker.native
require = marker.require
SOURCE_RUN = 36995165800
SOURCE_SHA = '64fafdc470c5379529fd5be0afb286110f748dd9'
RESULT_SHA = '669eadf38f9fae166f03d9eb0330990bc3523071ac8df855dcac2fc2f87962f3'
REFERENCE_SHA = '2ee13d1a337c709ab5f46265f74b4b925da6bf710153a50ca2a10fa073cc287e'
HELPER = ROOT/'hw/soc/flow/io_parent_boundary.py'
METHODS = tuple(dict.fromkeys((*marker.METHODS, 'scripts/run_io_parent_boundary.py',
    'hw/soc/flow/io_parent_boundary.py', 'scripts/make_chip_io_floorplan.py',
    'sw/tests/test_io_parent_boundary.py', '.github/workflows/io-parent-boundary.yml')))
CONNECTIONS = 'ihp-sg13g2/libs.tech/klayout/tech/lvs/rule_decks/general_connections.lvs'
BEFORE = 'connect(pwell_sub, pwell)\n'
AFTER = BEFORE+'# Diagnostic boundary: attach one witnessed body label, never join separate bodies.\nconnect(pwell_sub, substrate_text)\n'


def overlay_text(text):
    require(text.count(BEFORE) == 1 and 'connect(pwell_sub, substrate_text)' not in text, 'Unexpected substrate attachment baseline')
    return text.replace(BEFORE, AFTER)


def validate_source(source):
    require(native.sha(source/'result.json') == RESULT_SHA, 'Wrong completed marker receipt')
    result = json.loads((source/'result.json').read_text())
    require(result['source_sha'] == SOURCE_SHA and result['run_id'] == str(SOURCE_RUN)
            and result['status'] == 'COMPLETED_ISOLATED_MARKER_REPAIR_AND_STRICT_COMPARISONS', 'Wrong completed marker identity')
    selected = {'inputs/actual-adjacency.gds':boundary.SOURCE_GDS_SHA,
        'straight-spacing/flat/lvs.lvsdb.gz':boundary.SOURCE_DB_SHA,
        'straight-spacing/schematic.cir':REFERENCE_SHA}
    pins = {str(source/'result.json'):RESULT_SHA}
    for name, digest in selected.items():
        path = source/name
        require(path.is_file() and not path.is_symlink() and native.sha(path) == digest
                and result['output_sha256'][name] == digest, 'Changed marker evidence: '+name)
        pins[str(path)] = digest
    return result, pins


def prepare_overlay(directory):
    deck, original_pins = native.verify_deck(); lock = json.loads(native.LOCK.read_text())
    directory.mkdir(parents=True, exist_ok=False); changes = []
    for row in lock['files']:
        source = native.DECK/row['path']; target = directory/row['path']; target.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        if row['path'] == CONNECTIONS:
            updated = overlay_text(raw.decode()).encode(); changes.append(dict(path=row['path'],
                original_sha256=native.sha(source), before=BEFORE, after=AFTER)); raw = updated
        target.write_bytes(raw)
    require(len(changes) == 1, 'Expected exactly one isolated attachment edit')
    pins = {str(p):native.sha(p) for p in directory.rglob('*') if p.is_file()}
    require(len(pins) == len(lock['files']), 'Overlay file inventory changed')
    return directory/deck.relative_to(native.DECK), pins, dict(original_files=len(lock['files']),
        original_pins=original_pins, changes=changes, no_virtual_connections=True,
        taps_enabled=True, strict_ports_enabled=True, parameter_rules_unchanged=True,
        unmodified_qualified_deck=False)


def run(output, source):
    output=output.resolve();source=source.resolve()
    require(output.is_relative_to(native.OUTPUT_ROOT.resolve()) and source.is_relative_to(native.OUTPUT_ROOT.resolve()), 'Path escapes project output')
    output.mkdir(parents=True, exist_ok=False); target=output/'result.json'
    result=dict(status='PREPARING',source_sha=os.environ.get('GITHUB_SHA'),run_id=os.environ.get('GITHUB_RUN_ID'),
        original_marker_run=SOURCE_RUN,original_marker_source=SOURCE_SHA,cases={},diagnostic_only=True,
        full_chip_changed=False,qualified_deck_acceptance=False,lvs_accepted=False,manufacturing_approval=False)
    try:
        native.verify_runtime(native.APP,'x86_64');_,pins=native.verify_deck()
        previous,original_pins=validate_source(source);pins.update(original_pins)
        pins.update({str(ROOT/name):native.sha(ROOT/name) for name in METHODS});pins[str(native.APP)]=native.APP_SHA256
        result['original_four_case_verdicts']={n:r['audit'] for n,r in previous['cases'].items()}
        (output/'original-marker-result.json').write_bytes((source/'result.json').read_bytes())
        lef=output/'original-c4.lef'
        url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_io/lef/sg13g2_io.lef'
        with urllib.request.urlopen(url,timeout=60) as stream: raw=stream.read(96881)
        require(len(raw)==96880,'Wrong original LEF size');lef.write_bytes(raw)
        require(native.sha(lef)==boundary.LEF_SHA,'Wrong original LEF hash');pins[str(lef)]=boundary.LEF_SHA
        result['input_sha256']=pins;marker.capture_sources(output,pins);native.check_pins(pins)
        result['controls_process']=native.execute([str(native.APP),'python',str(HELPER),'controls',str(output/'controls')],output/'controls.log')
        require(result['controls_process']['returncode']==0,'Boundary controls failed')
        result['controls']=json.loads((output/'controls/result.json').read_text())
        result['prepare_process']=native.execute([str(native.APP),'python',str(HELPER),'prepare',
            str(source/'inputs/actual-adjacency.gds'),str(source/'straight-spacing/flat/lvs.lvsdb.gz'),str(lef),str(output/'inputs')],output/'prepare.log')
        require(result['prepare_process']['returncode']==0,'Physical boundary proof/preparation failed')
        inputs=output/'inputs';result['boundary']=json.loads((inputs/'boundary.json').read_text())
        (inputs/'schematic.cir').write_bytes((source/'straight-spacing/schematic.cir').read_bytes())
        for name in ('actual-adjacency.gds','boundary.json','schematic.cir'):pins[str(inputs/name)]=native.sha(inputs/name)
        deck,overlay_pins,receipt=prepare_overlay(output/'diagnostic-deck');pins.update(overlay_pins)
        result['diagnostic_deck']=receipt;native.write_json(output/'deck-overlay.json',receipt)
        for mode in ('deep','flat'):
            native.check_pins(pins);result['status']='RUNNING_DIAGNOSTIC_BOUNDARY_'+mode.upper();native.write_json(target,result)
            result['cases'][mode]=marker.compare(deck,inputs,output/mode,mode);native.write_json(target,result)
        native.check_pins(pins);native.verify_deck()
        result['status']='COMPLETED_DIAGNOSTIC_BOUNDARY_COMPARISONS'
        result['diagnostic_comparisons_pass']=all(c['status']=='PASS within comparison scope' for c in result['cases'].values())
    except BaseException as exc:
        result.update(status='ERROR_OR_INCOMPLETE_BOUNDARY_COMPARISON',error=str(exc));raise
    finally:
        result['output_sha256']={str(p.relative_to(output)):native.sha(p) for p in output.rglob('*') if p.is_file() and p!=target}
        native.write_json(target,result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--marker-inputs',type=Path,required=True);args=parser.parse_args();run(args.output,args.marker_inputs)


if __name__=='__main__':main()
