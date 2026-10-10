#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound seven-cell contact attribution; no geometry edits or LVS waiver."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import zipfile

import run_io_parent_lvs as native
from fetch_evidence_assets import fetch, verify
from run_io_tap_mask_probe import BASE, derivation_order

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT/'hw/soc/flow/io_tap_contact_probe.py'
ASSET = dict(name='closure-parent-boundary-case-37000437137-20261002.zip', bytes=7468692,
    sha256='0b4d68caae47be157a40bb31e87fc66e22c05761e0aafcbeb7ea824e4604a564',
    url='https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/'
        'closure-parent-boundary-case-37000437137-20261002.zip')
ARCHIVE_MEMBERS = 169
ARCHIVE_EXPANDED = 34915143
PRODUCER_SHA = '9e39269313d9683da35cf67a91bc4b15afed3970'
SELECTED = {
 'inputs/actual-adjacency.gds': ('actual-adjacency.gds', 'ae643bf0391b0d700bd3374b642f3afff4c94976d23014984e93005f3d334633'),
 'flat/lvs.lvsdb.gz': ('flat.lvsdb.gz', '025e237c8a570573a5005c8e2d6e297bc5b2468bf4c36f54ef407f9627bee56f'),
 'inputs/schematic.cir': ('schematic.cir', '2ee13d1a337c709ab5f46265f74b4b925da6bf710153a50ca2a10fa073cc287e'),
 'inputs/boundary.json': ('boundary.json', '7d2a07db50c1db1ac6b8ce9b4b2ea23effedba31c1d1396d5350db8e2ce0c2bc'),
 'result.json': ('producer-result.json', 'd42055377bea96ff5ada643f24882d42905f01ac182ab92b9c2afa4602d6261d'),
}
DRC = ROOT/'hw/soc/tools/ihp-drc-5e6d592'
DRC_BASE = 'ihp-sg13g2/libs.tech/klayout/tech/drc/'
DRC_LOCK = ROOT/'hw/soc/pnr/ihp-drc.lock.json'
DRC_LOCK_SHA = 'd47860e82e76d81897ce51452aa1f7a7bb76643da38093911b5cdb55a4ebf73a'
DRC_FILES = ['ihp-sg13g2.drc', 'rule_decks/layers_def.drc', 'rule_decks/feol/5_14_cont.drc',
             'rule_decks/sg13g2_tech_default.json']
METHODS = ['scripts/run_io_tap_contact_probe.py', 'hw/soc/flow/io_tap_contact_probe.py',
 'sw/tests/test_io_tap_contact_probe.py', '.github/workflows/io-tap-contact-probe.yml',
 'scripts/run_io_tap_mask_probe.py', 'scripts/run_io_parent_lvs.py',
 'scripts/fetch_evidence_assets.py', 'scripts/bootstrap_flow.py',
 'hw/soc/flow/prepare_ihp_drc.py', 'hw/soc/flow/prepare_ihp_lvs.py', 'hw/soc/flow/audit_klayout_lvs.py']
CONTROL_CASES = {'connected': True, 'rotation': True, 'split': False, 'wrong_net': False,
                 'missing_contact': False, 'wrong_transform': False, 'exception': False,
                 'missing_enclosure': False, 'pruned_unrelated_contact': True,
                 'pruned_selected_contact': False}
FULL_MASKS = ('ptap1_tie', 'ptap1_sub', 'pwell')
LOCAL_MASKS = ('pactiv', 'ptap1_mk', 'ptap1_exc', 'activ_drw', 'psd_drw', 'nwell_drw')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unpack(archive, destination):
    verify(archive, ASSET)
    inventory = {}; selected = {}
    with zipfile.ZipFile(archive) as source:
        infos = source.infolist()
        require(len(infos) == ARCHIVE_MEMBERS and sum(i.file_size for i in infos) == ARCHIVE_EXPANDED,
                'Original complete archive inventory differs')
        require(len({i.filename for i in infos}) == len(infos), 'Duplicate ZIP member')
        for info in infos:
            path = PurePosixPath(info.filename)
            require(not path.is_absolute() and '..' not in path.parts and '\\' not in info.filename
                    and str(path) == info.filename and not info.is_dir()
                    and (info.external_attr >> 16) & 0o170000 != 0o120000, 'Unsafe ZIP member')
            digest = hashlib.sha256(); data = bytearray()
            with source.open(info) as stream:
                while chunk := stream.read(1024**2):
                    digest.update(chunk)
                    if info.filename in SELECTED:
                        data.extend(chunk)
            inventory[info.filename] = dict(bytes=info.file_size, sha256=digest.hexdigest())
            if info.filename in SELECTED:
                name, expected = SELECTED[info.filename]
                require(digest.hexdigest() == expected, 'Pinned native input differs: '+info.filename)
                selected[name] = data
    require(set(selected) == {v[0] for v in SELECTED.values()}, 'Missing pinned native input')
    producer = json.loads(selected['producer-result.json'])
    require(producer['source_sha'] == PRODUCER_SHA and producer['run_id'] == '37000437137'
            and producer['status'] == 'COMPLETED_DIAGNOSTIC_BOUNDARY_COMPARISONS'
            and producer['lvs_accepted'] is False and producer['qualified_deck_acceptance'] is False,
            'Captured producer identity/scope differs')
    require(set(producer['output_sha256']) == set(inventory)-{'result.json'}, 'Capture inventory incomplete')
    require(all(inventory[name]['sha256'] == digest for name, digest in producer['output_sha256'].items()),
            'Original producer capture does not reproduce')
    flat = producer['cases']['flat']
    require(flat['native']['returncode'] == 0 and flat['audit']['status'] == 'FAIL'
            and flat['audit']['extraction_diagnostics'] == [], 'Original native comparison is incomplete')
    boundary = json.loads(selected['boundary.json'])
    require(boundary['preservation']['status'] == 'PASS_ALL_POLYGONS_INSTANCES_AND_NON_BOUNDARY_TEXTS_PRESERVED'
            and boundary['wrapper_gds_sha256'] == SELECTED['inputs/actual-adjacency.gds'][1],
            'Boundary annotation did not preserve physical geometry')
    destination.mkdir(exist_ok=False)
    for name, data in selected.items():
        (destination/name).write_bytes(data)
    return inventory


def drc_contract():
    require(native.sha(DRC_LOCK) == DRC_LOCK_SHA, 'DRC source lock changed')
    lock = json.loads(DRC_LOCK.read_text()); native.validate_lock(lock)
    require(lock['commit'] == '5e6d592e4002946a4616f798c357f0f3c06cf3b6', 'DRC revision differs')
    rows = {row['path']: row for row in lock['files']}
    pins = {str(DRC_LOCK): DRC_LOCK_SHA}; texts = {}
    for name in DRC_FILES:
        rel = DRC_BASE+name; row = rows[rel]; path = DRC/rel
        require(path.is_file() and not path.is_symlink() and path.stat().st_size == row['bytes']
                and native.sha(path) == row['sha256'], 'DRC dependency changed: '+name)
        pins[str(path)] = row['sha256']; texts[name] = path.read_text()
    # Pin both source and the specific interpretation used by this diagnostic.
    source_requirements = {
      'ihp-sg13g2.drc': ['cont_nseal = cont_drw.not(edgeseal_drw)',
          'contbar = cont_nseal.non_squares', 'cont_sq = cont_nseal.not(contbar)',
          'svaricap = nwell_drw.not_outside(svaricap_recog)'],
      'rule_decks/feol/5_14_cont.drc': ['act_sram = activ_drw.and(sram_drw)',
          'act_nsram = activ_drw.not(sram_drw)', 'cont_nsvaricap = cont_sq.not(svaricap)',
          'cnt_c_act = act_nsram.join(activ_mask).not(digibnd_drw)',
          'cont_nsvaricap.enclosed(cnt_c_act, cnt_c_value.um, euclidian)'],
      'rule_decks/layers_def.drc': ['activ_mask = get_polygons(1, 20)',
          'digibnd_drw = get_polygons(16, 0)', 'sram_drw = get_polygons(25, 0)',
          'nwell_drw = get_polygons(31, 0)', 'edgeseal_drw = get_polygons(39, 0)']}
    require(all(line in texts[name] for name, lines in source_requirements.items() for line in lines),
            'Exact DRC exception expressions differ')
    rules = json.loads(texts['rule_decks/sg13g2_tech_default.json'])['drc_rules']
    require({k:rules[k] for k in ('Cnt_a', 'Cnt_c', 'Cnt_c_digibnd', 'Cnt_c_sram')}
            == dict(Cnt_a=.16, Cnt_c=.07, Cnt_c_digibnd=.05, Cnt_c_sram=.006), 'DRC numeric contract differs')
    return dict(status='PINNED_DRC_BRANCH_INTERPRETATION_ONLY', minimum_enclosure_nm=70,
        contact_width_nm=160, alternative_enclosures_nm=dict(DigiBnd=50, SRAM=6),
        exception_requirements='No EdgeSeal, SRAM, DigiBnd, Activ-mask or NWell on any expanded contact. NWell absence excludes SVaricap because its recognized mask is a subset of NWell.',
        full_drc_executed=False, exact_expressions=source_requirements, source_sha256=pins), pins


def program(deck_root):
    entry = (deck_root/BASE/'sg13g2.lvs').read_text()
    order = derivation_order(entry)
    paths = [deck_root/BASE/'rule_decks/custom_classes.lvs'] + [
        deck_root/BASE/f'rule_decks/{name}.lvs' for name in order]
    require(all(p.is_file() and not p.is_symlink() for p in paths), 'Missing exact derivation include')
    text = "require 'json'\nrequire 'logger'\nlogger = Logger.new($stdout)\nsource($input, 'ACTUAL_IO_ADJACENCY')\nraise 'wrong DBU' unless dbu == 0.001\nflat\nPARALLEL_RES = true\nSERIES_RES = true\n"
    text += ''.join('# %include '+str(p.resolve())+'\n' for p in paths)
    text += 'probe_layers = {\n'+''.join(f"  '{n}' => {n},\n" for n in FULL_MASKS+LOCAL_MASKS)+'}\n'
    text += """
# Duplicate only. Exact original derivations remain unchanged and unconnected.
roi = RBA::Region.new(RBA::Box.new(156780, 995930, 157220, 1076070))
out = {status: 'DERIVED_CONTACT_MASKS_ONLY', top: 'ACTUAL_IO_ADJACENCY', dbu_um: dbu, masks: {}}
probe_layers.each do |name, layer|
  region = RBA::Region.new
  layer.data.each_merged { |polygon| region.insert(polygon) }
  whole = ['ptap1_tie', 'ptap1_sub', 'pwell'].include?(name)
  region = region & roi unless whole
  region.merge
  out[:masks][name] = {scope: whole ? 'whole_seven_cell_parent' : 'stripe_roi',
    area_nm2: region.area, perimeter_nm: region.perimeter,
    polygons: region.each_merged.map { |polygon| polygon.to_s }.sort}
end
File.write($masks, JSON.pretty_generate(out))
"""
    return text


def check_controls(path):
    result = json.loads(path.read_text())
    require(result['status'] == 'PASS_NATIVE_CONTACT_CONTROLS' and result['klayout_version'] == '0.30.7'
            and result['actual_input_processed'] is False, 'Native control scope differs')
    require(set(result['cases']) == set(CONTROL_CASES)|{'overlapping_projection'}, 'Incomplete control census')
    require(all(result['cases'][name] == dict(expected_pass=value, actual_pass=value)
                for name, value in CONTROL_CASES.items()), 'Wrong native positive/negative control')
    require(result['cases']['overlapping_projection'] == dict(expected_length_nm=420, actual_length_nm=420),
            'Overlapping projection control failed')
    return result


def run(output, archive=None):
    output = output.resolve()
    require(output.is_relative_to(native.OUTPUT_ROOT.resolve()), 'Output escapes project')
    output.mkdir(parents=True, exist_ok=False)
    result = dict(status='PREPARING', source_sha=os.environ.get('GITHUB_SHA'), run_id=os.environ.get('GITHUB_RUN_ID'),
        scope='Read-only 234 direct Vss contact ownership and conditional literal-perimeter bound in the exact seven-cell parent.',
        prior_db_provenance='Captured producer used the disclosed one-line substrate TEXT attachment overlay. This probe changes no deck and uses original derivations; prior DB remains diagnostic, not qualified-deck acceptance.',
        lvs_accepted=False, qualified_deck_acceptance=False, full_chip_changed=False, manufacturing_approval=False)
    path = output/'result.json'; native.write_json(path, result)
    try:
        native.verify_runtime(native.APP, 'x86_64'); _, pins = native.verify_deck()
        contract, drc_pins = drc_contract(); pins.update(drc_pins)
        pins[str(native.APP)] = native.APP_SHA256
        pins.update({str(ROOT/name): native.sha(ROOT/name) for name in METHODS})
        result['input_sha256'] = pins
        for name in pins:
            source = Path(name)
            if source == native.APP:
                continue
            target = output/'sources'/source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(source.read_bytes())
        native.write_json(output/'drc-rule-contract.json', contract)
        proc = native.execute([str(native.APP), 'python', str(HELPER), 'controls', str(output/'controls.json')], output/'controls.log')
        result['controls_process'] = proc
        require(proc['returncode'] == 0, 'Tiny native controls failed before actual input')
        result['controls'] = check_controls(output/'controls.json')
        if archive is None:
            cache = output/'archive'; cache.mkdir(); fetch(ASSET, cache); archive = cache/ASSET['name']
        result['archive_inventory'] = unpack(archive, output/'inputs')
        generated = output/'derivation.drc'; generated.write_text(program(native.DECK))
        result['derivation_program_sha256'] = native.sha(generated)
        result['derivation_process'] = native.execute([str(native.APP), 'klayout', '-b', '-zz', '-r', str(generated),
            '-rd', 'input='+str(output/'inputs/actual-adjacency.gds'), '-rd', 'masks='+str(output/'masks.json')], output/'derivation.log')
        require(result['derivation_process']['returncode'] == 0, 'Exact source mask derivation failed')
        result['analysis_process'] = native.execute([str(native.APP), 'python', str(HELPER), 'inspect', str(output)], output/'analysis.log')
        require(result['analysis_process']['returncode'] == 0, 'Contact/mask/extraction/DRC branch gate failed')
        result['analysis'] = json.loads((output/'analysis.json').read_text())
        require(result['analysis']['status'] == 'PASS_CONTACT_ATTRIBUTION_DIAGNOSTIC_ONLY', 'Incomplete contact attribution')
        for name, expected in pins.items():
            require(native.sha(name) == expected, 'Input changed during diagnostic: '+name)
        for _, (name, expected) in SELECTED.items():
            require(native.sha(output/'inputs'/name) == expected, 'Captured input changed during diagnostic: '+name)
        result['status'] = 'PASS_CONTACT_ATTRIBUTION_DIAGNOSTIC_ONLY'
    except BaseException as exc:
        result['status'] = 'FAILED_DIAGNOSTIC'; result['error'] = str(exc)
        raise
    finally:
        result['output_sha256'] = {str(p.relative_to(output)): native.sha(p) for p in sorted(output.rglob('*'))
                                  if p.is_file() and p != path and p.name != ASSET['name']}
        native.write_json(path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--archive', type=Path, help='Optional already-downloaded exact immutable archive')
    args = parser.parse_args(); run(args.output, args.archive)


if __name__ == '__main__':
    main()
