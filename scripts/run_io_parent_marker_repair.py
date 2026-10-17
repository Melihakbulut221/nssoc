#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Repair only 26 absent actual-parent RC markers, then retain strict LVS results.

The first comparison uses the exact completed baseline's unchanged schematic.
Only afterwards, a separate case canonicalizes explicit straight-resistor ps
under the immutable original model. No terminal or tap A/P correction is made.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import run_io_strict_parent_lvs as baseline

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'hw/soc/flow'))
from repair_io_resistor_markers import PINNED, canonicalize_straight_spacing  # noqa: E402

native = baseline.native
require = baseline.require
TOP = baseline.TOP
BASELINE_RUN = 36992719056
BASELINE_SOURCE = '103528bc68cfc4bb8b36509ef3037787c73201af'
BASELINE_SHA = 'c01f367b60f3ab254c3c1cacc5889d8010503e57d9333d214681528c62b84d55'
REFERENCE_SHA = '1a1a545e3d279e234f99939baddd915118a63e83aea94c684d78459fe600a663'
MODEL_SHA = PINNED['libs.tech/ngspice/models/resistors_mod.lib']
HELPER = ROOT/'hw/soc/flow/repair_parent_resistor_markers.py'
METHODS = tuple(dict.fromkeys((*baseline.METHODS, 'scripts/run_io_parent_marker_repair.py',
    'scripts/extract_gds_hierarchy.py', 'hw/soc/flow/repair_parent_resistor_markers.py',
    'sw/tests/test_io_parent_marker_repair.py', '.github/workflows/io-parent-marker-repair.yml')))


def validate_baseline(directory):
    result_path = directory/'result.json'
    require(result_path.is_file() and not result_path.is_symlink() and native.sha(result_path) == BASELINE_SHA,
            'Wrong completed baseline receipt')
    result = json.loads(result_path.read_text())
    require(result['source_sha'] == BASELINE_SOURCE and result['run_id'] == str(BASELINE_RUN)
            and result['status'] == 'FAIL_STRICT_SEVEN_INSTANCE_PARENT', 'Unexpected baseline identity/verdict')
    baseline.validate_parent(directory/'inputs/prior-parent')
    pins = {str(result_path): BASELINE_SHA}
    expected = {'inputs/actual-adjacency.gds': baseline.PARENT_INPUTS['actual-adjacency.gds'],
        'inputs/schematic.cir': REFERENCE_SHA, 'original-reference/inputs/resistors_mod.lib': MODEL_SHA,
        'original-reference/inputs/sg13g2_io.cdl': baseline.CDL_SHA}
    for name, digest in expected.items():
        path = directory/name
        require(path.is_file() and not path.is_symlink() and native.sha(path) == digest
                and result['output_sha256'][name] == digest, 'Baseline input differs: '+name)
        pins[str(path)] = digest
    prepared, _ = baseline.reference(baseline.read_io_cdl_text(directory/'original-reference/inputs/sg13g2_io.cdl'))
    require(prepared.encode() == (directory/'inputs/schematic.cir').read_bytes(), 'Baseline reference cannot be reproduced')
    return result, pins


def spacing_reference(text, model):
    require(native.sha(model) == MODEL_SHA, 'Straight spacing requires exact original model')
    require(hashlib.sha256(text.encode()).hexdigest() == REFERENCE_SHA, 'Straight spacing requires exact baseline reference')
    changed, edits = canonicalize_straight_spacing(text)
    require(len(edits) == 26 and all('b=0' in e['before'] and '$[rppd]' in e['before'] for e in edits),
            'Unexpected straight resistor inventory')
    for edit in edits:
        require(edit['after'] == edit['before'].replace('ps=180n', 'ps=0'), 'Non-spacing change detected')
    return changed, dict(model_sha256=MODEL_SHA, expression='leff=(b+1)*l+(2/kappa*weff+ps)*b',
        restriction='Explicit b=0 only: leff=l, independent of ps; original comparison retained.',
        edits=edits, vendor_terminals_changed=False, tap_parameters_changed=False)


def compare(deck, inputs, case, mode):
    case.mkdir(parents=True, exist_ok=False)
    detail = dict(native=native.execute(baseline.command(deck, inputs, case, mode), case/'run.log'))
    detail['audit_process'] = native.execute([str(native.APP), 'python', str(native.AUDIT),
        str(case/'lvs.lvsdb.gz'), '--top', TOP, '--deck-log', str(case/'deck.log'),
        '--output', str(case/'audit.json')], case/'audit.log')
    detail['audit'] = baseline.verdict(case, detail['native'], detail['audit_process'])
    detail['status'] = detail['audit']['status']
    return detail


def capture_sources(output, pins):
    for name in pins:
        source = Path(name)
        if source == native.APP or source.is_relative_to(output): continue
        dest = output/'sources'/source.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(source.read_bytes())


def run(output, original):
    output = output.resolve(); original = original.resolve()
    require(output.is_relative_to(native.OUTPUT_ROOT.resolve()) and original.is_relative_to(native.OUTPUT_ROOT.resolve()),
            'Output or original inputs escape project output')
    output.mkdir(parents=True, exist_ok=False)
    target = output/'result.json'
    result = dict(schema=1, status='PREPARING', source_sha=os.environ.get('GITHUB_SHA'),
        run_id=os.environ.get('GITHUB_RUN_ID'), baseline_run=BASELINE_RUN, baseline_source=BASELINE_SOURCE,
        cases={}, parent_lvs_accepted=False, full_chip_lvs_accepted=False, manufacturing_approval=False,
        candidate_adopted=False, scope='Isolated actual seven-instance subgraph; every native FAIL is retained.')
    try:
        native.verify_runtime(native.APP, 'x86_64'); deck, pins = native.verify_deck()
        original_receipt, input_pins = validate_baseline(original); pins.update(input_pins)
        pins.update({str(ROOT/name): native.sha(ROOT/name) for name in METHODS})
        pins[str(native.APP)] = native.APP_SHA256
        result['input_sha256'] = pins
        capture_sources(output, pins)
        native.check_pins(pins)
        native.write_json(target, result)
        result['baseline_cases'] = {name: c['audit'] for name, c in original_receipt['cases'].items()}
        (output/'baseline-result.json').write_bytes((original/'result.json').read_bytes())
        result['controls_process'] = native.execute([str(native.APP), 'python', str(native.CONTROL),
            str(output/'controls')], output/'controls.log')
        require(result['controls_process']['returncode'] == 0, 'Native strict controls failed')
        result['controls'] = native.validate_controls(output/'controls/result.json')
        pins.update(result['controls']['input_sha256']); pins.update(result['controls']['output_sha256'])
        result['marker_controls_process'] = native.execute([str(native.APP), 'python', str(HELPER),
            'controls', str(output/'marker-controls')], output/'marker-controls.log')
        require(result['marker_controls_process']['returncode'] == 0, 'Native marker controls failed')
        result['marker_controls'] = json.loads((output/'marker-controls/result.json').read_text())
        require(result['marker_controls']['status'] == 'PASS_TINY_NATIVE_MARKER_CONTROLS', 'Missing marker control verdict')
        inputs = output/'inputs'; inputs.mkdir()
        for source, name in [('inputs/actual-adjacency.gds', 'original.gds'), ('inputs/schematic.cir', 'schematic.cir'),
                             ('original-reference/inputs/resistors_mod.lib', 'resistors_mod.lib')]:
            (inputs/name).write_bytes((original/source).read_bytes())
            pins[str(inputs/name)] = native.sha(inputs/name)
        result['repair_process'] = native.execute([str(native.APP), 'python', str(HELPER), 'repair',
            str(inputs/'original.gds'), str(inputs/'actual-adjacency.gds'), str(inputs/'repair.json')], output/'repair.log')
        require(result['repair_process']['returncode'] == 0, 'Marker preflight/repair/preservation failed')
        result['repair'] = json.loads((inputs/'repair.json').read_text())
        require(result['repair']['source_sha256'] == baseline.PARENT_INPUTS['actual-adjacency.gds']
                and result['repair']['status'] == 'REPAIRED_RECOGNITION_REQUIRES_LVS_AND_DRC'
                and result['repair']['native_roundtrip']['status'] == 'PASS_ALL_GEOMETRY_TEXT_AND_INSTANCE_TRANSFORMS_EXCEPT_26_MARKERS'
                and result['repair']['byte_preservation']['added_boundaries'] == 26
                and result['repair']['byte_preservation']['every_original_byte_preserved'], 'Incomplete marker receipt')
        pins[str(inputs/'actual-adjacency.gds')] = result['repair']['output_sha256']
        pins[str(inputs/'repair.json')] = native.sha(inputs/'repair.json')
        # The exact original-reference cases are completed and saved first.
        for mode in ('deep', 'flat'):
            native.check_pins(pins)
            result['status'] = 'RUNNING_UNCHANGED_REFERENCE_'+mode.upper(); native.write_json(target, result)
            result['cases']['unchanged-reference-'+mode] = compare(deck, inputs, output/'unchanged-reference'/mode, mode)
            native.write_json(target, result)
        spacing = output/'straight-spacing'; spacing.mkdir()
        (spacing/'actual-adjacency.gds').write_bytes((inputs/'actual-adjacency.gds').read_bytes())
        text, proof = spacing_reference(baseline.read_io_cdl_text(inputs/'schematic.cir'), inputs/'resistors_mod.lib')
        (spacing/'schematic.cir').write_text(text); native.write_json(spacing/'model-proof.json', proof)
        result['straight_spacing_proof'] = proof
        for name in ('actual-adjacency.gds', 'schematic.cir', 'model-proof.json'):
            pins[str(spacing/name)] = native.sha(spacing/name)
        for mode in ('deep', 'flat'):
            native.check_pins(pins)
            result['status'] = 'RUNNING_STRAIGHT_SPACING_'+mode.upper(); native.write_json(target, result)
            result['cases']['straight-spacing-'+mode] = compare(deck, spacing, spacing/mode, mode)
            native.write_json(target, result)
        result['reference_case_pass'] = {variant: all(result['cases'][variant+'-'+mode]['status'] == 'PASS within comparison scope'
            for mode in ('deep', 'flat')) for variant in ('unchanged-reference', 'straight-spacing')}
        result['status'] = 'COMPLETED_ISOLATED_MARKER_REPAIR_AND_STRICT_COMPARISONS'
        capture_sources(output, pins)
        native.check_pins(pins)
    except BaseException as exc:
        result.update(status='ERROR_OR_INCOMPLETE_REPAIR_COMPARISON', error=str(exc)); raise
    finally:
        result['output_sha256'] = {str(p.relative_to(output)): native.sha(p) for p in sorted(output.rglob('*')) if p.is_file() and p != target}
        native.write_json(target, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline-inputs', type=Path, required=True)
    args = parser.parse_args(); run(args.output, args.baseline_inputs)


if __name__ == '__main__': main()
