#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Matched fresh ALU physical measurements; never adopt a layout automatically."""
import argparse
import collections
import copy
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import zipfile

import run_cloud_hold_diagnostic as hold
import prove_alu_state_partitions as partitions

common = hold.common
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'docs/evidence/timing-cloud-input-20260930.json'
MACRO_WITNESS = 'hw/soc/pnr/alu-physical-macro-witness.json'
PINS = {
    **partitions.PINS,
    MANIFEST: 'b8c3044903eff78728c4a5205a2e054576ad91ccdaa0bff28c59de3d88ae712a',
    'scripts/run_cloud_timing_experiment.py': '689c4dbd5a036fc1919d25c0d816f1740a878b11d7dfef432ae7e41c31197524',
    'scripts/run_cloud_hold_diagnostic.py': '61644cc59ae15f7a9166d0e5f8558c5c755581d69ae516725e7e3b768b69abe7',
    'hw/soc/pnr/timing_hold_reproducibility.tcl': '5514527288fd387ee42d2bfa8dc52b39abe1da16a106e82d4684cb5422bba6e6',
    'scripts/prove_alu_state_partitions.py': 'c548c9c436a074ff13e978d14dbf6dd9edfa6f107854ea1eaab9dd8766cea7b8',
    'sw/tests/test_alu_state_partitions.py': '9625cef3b41047ab1fb2be2ab46fff8887de70962a619707c6a27715b3602cc4',
    '.github/workflows/timing-alu-state-partitions.yml': '5bf83968bb5cca722a30d20a5c20b46a28221b6a180620a135d0f8a52ad03542',
    MACRO_WITNESS: '8a5136f7d8cdf3fd23e3b57023b5403d41cb2634072f406ee926a710b6573664',
}
OWN = ('scripts/run_cloud_alu_physical.py', 'hw/soc/pnr/alu_physical_flow.py',
       'hw/soc/pnr/alu_physical_geometry.tcl', 'hw/soc/pnr/alu_physical_audit.tcl',
       'sw/tests/test_cloud_alu_physical.py', '.github/workflows/timing-alu-physical.yml')
MAP_RUN = 37002748526
MAP_COMMIT = '622a1ae720ae727fde0cd7b9c070cf6b873c9da8'
MAP_ARTIFACT = 11224169147
MAP_ZIP = dict(bytes=17453417, sha256='fa4c2d938aa8c8183901da5d7ed82bdf74d73798054f8a4021d67a8226b84a79')
MAP_RESULT = dict(bytes=14648, sha256='2b0487fc1c8fc0bf9c7a64709907c1a1f9fb54cc5970d6260558fb32b28c6a2a')
NETLISTS = {
    'original': dict(bytes=10744356, sha256='13dd615dabe769c4c2809dfb1e4b2e182f55c265256aea0f279e4d31c8005e48'),
    'candidate': dict(bytes=10840030, sha256='ef20a6b368ad425af23ad72279e0d9bb31f2a06e92e42f405a20c6c3c71ac64f'),
}
# Bound only after independent review of a completed successful partition run.
# Neither the counterexample nor the monolithic timeout is a usable proof.
PROOF_BINDING = None
BOOT_FAILURE = dict(run_id=37002748526, source_commit='622a1ae720ae727fde0cd7b9c070cf6b873c9da8',
    variant='candidate', memory='vendor', artifact_id=11233351913,
    artifact=dict(bytes=614871, sha256='f94d5e9046a71adf536de24db530bc12d9435c8e72b6fe3bddc9cba71e57d3cb'),
    unresolved=True)
PROOF_ARTIFACT_KEYS = {'common', 'verdict', 'shard0', 'shard1', 'shard2', 'shard3'}
PROOF_METHOD_PINS = {name: PINS[name] for name in (*partitions.PINS, *partitions.OWN)}
GEOMETRY = ('signal-pins.tsv', 'macros.tsv', 'bounds.tsv', 'dbu.txt')
CORNER_NAMES = ['nom_fast_1p32V_m40C', 'nom_slow_1p08V_125C', 'nom_typ_1p20V_25C']
# These are the only orientations present in the exact 32-macro C10 witness.
ODB_ORIENTATION = {'N': 'R0', 'FS': 'MX'}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(path):
    return dict(bytes=path.stat().st_size, sha256=common.sha(path))


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', 'repos/Melihakbulut221/nssoc/'+path], text=True))


def artifact_download(meta, path):
    require(meta['expired'] is False and isinstance(meta['digest'], str) and meta['digest'].startswith('sha256:'),
            'Artifact lacks immutable API identity')
    with path.open('xb') as stream:
        subprocess.run(['gh', 'api', 'repos/Melihakbulut221/nssoc/actions/artifacts/'+str(meta['id'])+'/zip'],
                       stdout=stream, check=True)
    common.verify_file(path, dict(bytes=meta['size_in_bytes'], sha256=meta['digest'][7:]))


def validate_proof_binding(binding):
    require(isinstance(binding, dict), 'No independently accepted partition proof has been bound')
    require(binding.get('schema') == 1 and type(binding.get('run_id')) is int and binding['run_id'] > 0
            and binding.get('run_attempt') == 1 and re.fullmatch('[0-9a-f]{40}', binding.get('source_commit', '')),
            'Invalid partition producer identity')
    require(set(binding.get('artifacts', {})) == PROOF_ARTIFACT_KEYS, 'Incomplete partition artifact binding')
    ids = set()
    for key, entry in binding['artifacts'].items():
        expected_name = ('alu-partition-common-1' if key == 'common' else 'alu-partition-verdict-1' if key == 'verdict'
                         else 'alu-partition-shard-'+key[-1]+'-1')
        require(entry.get('name') == expected_name and type(entry.get('id')) is int and entry['id'] > 0
                and entry['id'] not in ids and type(entry.get('bytes')) is int and 0 < entry['bytes'] < 1024**3
                and re.fullmatch('[0-9a-f]{64}', entry.get('sha256', '')), 'Invalid partition artifact identity')
        ids.add(entry['id'])
    return binding


def require_execution_ready():
    binding = validate_proof_binding(PROOF_BINDING)
    # No command-line/environment override exists. Clearing this blocker
    # requires a reviewed source change backed by diagnosis and qualification;
    # a binary SAT success alone cannot waive the preserved four-state failure.
    require(BOOT_FAILURE['unresolved'] is False, 'Unresolved candidate/vendor four-state boot failure blocks physical work')
    return binding


def restore_proof_archive(archive, destination):
    destination.mkdir()
    with zipfile.ZipFile(archive) as source:
        require(len(source.namelist()) == len(set(source.namelist())), 'Duplicate partition archive member')
        require(sum(x.file_size for x in source.infolist()) <= 2*common.GIB, 'Partition archive expansion too large')
        for item in source.infolist():
            relative = common.safe_relative(item.filename.rstrip('/'))
            require(not stat.S_ISLNK(item.external_attr >> 16), 'Linked partition archive member')
            target = destination/relative
            if item.is_dir(): target.mkdir(parents=True, exist_ok=True); continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(item) as stream, target.open('xb') as out: shutil.copyfileobj(stream, out, 1024**2)


def validate_partition_evidence(common_dir, shard_dirs, verdict_path, source_commit):
    """Reparse complete immutable native evidence without executing a new proof."""
    prepared = json.loads((common_dir/'result.json').read_text())
    require(prepared['github_source_commit'] == source_commit and prepared['status'] == 'COMMON_MITER_PREPARED_NOT_PROVED'
            and prepared['complete_inputs_rechecked'] is True, 'Incomplete common proof preparation')
    require(set(prepared['methods']) == set(PROOF_METHOD_PINS), 'Incomplete proof method inventory')
    partitions.verify_inventory(common_dir, prepared['outputs'])
    for name, expected_sha in PROOF_METHOD_PINS.items():
        expected = prepared['methods'][name]
        require(expected['sha256'] == expected_sha, 'Unreviewed partition method')
        common.verify_file(common_dir/'methods'/name, expected); common.verify_file(ROOT/name, expected)
    manifest = common.validate_manifest(json.loads((ROOT/MANIFEST).read_text()))
    require(prepared['runtime'] == manifest['runtime'], 'Partition runtime differs from exact pinned runtime')
    require(prepared['original_graph'] == partitions.replay.MEMBERS['original-lifted.json']
            and prepared['corrected_graph'] == partitions.TIMEOUT_MEMBERS['corrected-candidate-lifted.json'],
            'Partition proof identifies different lifted graphs')
    reconstruction = prepared['reconstruction_checks']
    require(reconstruction['graph_object_equal'] is True and reconstruction['labels_object_equal'] is True
            and reconstruction['proposal_exact_serialized_pin'] == partitions.TIMEOUT_MEMBERS['corrected-state-proposal.json'],
            'Partition reconstructed a different state relation')
    common.verify_file(common_dir/'common-miter.il', prepared['common_miter'])
    common.verify_file(common_dir/'plan.json', prepared['plan'])
    plan = partitions.validate_plan(json.loads((common_dir/'plan.json').read_text()))
    require((plan['symbolic_input_bits'], plan['total_output_bits'], len(plan['groups'])) == (10828, 34321, 269),
            'Partition proof does not cover the whole original boundary')
    interface = prepared['native_interface']
    require(interface['symbolic_inputs'] == {'in_'+n: w for n, w in plan['symbolic_inputs'].items()}
            and interface['symbolic_input_bits'] == 10828 and interface['native_groups'] == 269,
            'Native common miter input/group interface differs from the complete plan')
    rows = []
    for directory in shard_dirs:
        row = json.loads((directory/'result.json').read_text())
        require(row['status'] == 'ALL_ASSIGNED_GROUPS_VISITED' and row['complete_inputs_rechecked'] is True
                and row['github_source_commit'] == source_commit and row['execution']['returncode'] == 0
                and row['common_miter'] == prepared['common_miter'] and row['plan'] == prepared['plan']
                and row['methods'] == prepared['methods'], 'Unmatched or incomplete native partition shard')
        partitions.verify_inventory(directory, row['outputs'])
        parsed = partitions.parse_shard((directory/'partitions.log').read_text(), plan, row['shard'], directory, write_logs=False)
        require(parsed == row['groups'], 'Partition verdict differs from raw native proof log')
        rows.append(row)
    recomputed = partitions.aggregate(plan, rows)
    require(recomputed['state_bijection_proved'] is True, 'Some output equations remain unproved')
    actual = json.loads(verdict_path.read_text())
    require(all(actual.get(k) == v for k, v in recomputed.items()) and actual['github_source_commit'] == source_commit
            and actual['common_miter'] == prepared['common_miter'] and actual['plan'] == prepared['plan'],
            'Final aggregate differs from independently replayed complete proof')
    require(actual['shard_results'] == {str(row['shard']): pin(path/'result.json') for row, path in zip(rows, shard_dirs)},
            'Aggregate refers to different native shard receipts')
    return dict(status='COMPLETE_BINARY_RELATION_REPARSED_NO_NEW_NATIVE_PROOF', source_commit=source_commit,
        common_miter=prepared['common_miter'], plan=prepared['plan'], methods=prepared['methods'], runtime=prepared['runtime'],
        complete_groups=269, complete_output_obligation_bits=34321, symbolic_input_bits=10828,
        no_internal_assumptions=True, verdict=pin(verdict_path), native_execution=False,
        scope='Equal initial corresponding FF/latch state and identical opaque SRAM behavior are required. No reset reachability, four-state boot, CDC, memory internal, post-placement equivalence or physical acceptance.')


def proof_gate(work, output):
    """No physical run starts with absent, incomplete, narrowed or failed proof."""
    binding = require_execution_ready()
    run = api('actions/runs/'+str(binding['run_id']))
    require(run['head_sha'] == binding['source_commit'] and run['status'] == 'completed' and run['conclusion'] == 'success'
            and run['run_attempt'] == 1, 'Bound partition producer is not a complete success')
    captures = {}; archive_pins = {}
    for key, expected in binding['artifacts'].items():
        meta = api('actions/artifacts/'+str(expected['id']))
        require(meta['id'] == expected['id'] and meta['name'] == expected['name']
                and meta['workflow_run']['id'] == binding['run_id'] and meta['workflow_run']['head_sha'] == binding['source_commit']
                and meta['size_in_bytes'] == expected['bytes'] and meta['digest'] == 'sha256:'+expected['sha256'],
                'Bound partition artifact provenance changed')
        archive = work/('proof-'+key+'.zip'); artifact_download(meta, archive)
        archive_pins[key] = pin(archive); captures[key] = work/('proof-'+key)
        restore_proof_archive(archive, captures[key])
    verdict = captures['verdict']/'alu-partition-verdict.json'
    require({str(p.relative_to(captures['verdict'])) for p in captures['verdict'].rglob('*') if p.is_file()} ==
            {'alu-partition-verdict.json'}, 'Unexpected aggregate artifact contents')
    checked = validate_partition_evidence(captures['common'], [captures['shard'+str(i)] for i in range(4)], verdict,
                                          binding['source_commit'])
    shutil.copyfile(verdict, output/'partition-proof-result.json')
    checked.update(binding=binding, exact_archive_pins=archive_pins)
    common.save(output/'partition-proof-independent-review.json', checked)
    return checked


def restore_mapping(archive, output, variant):
    common.verify_file(archive, MAP_ZIP)
    require(variant in NETLISTS, 'Unsupported physical variant')
    with zipfile.ZipFile(archive) as z:
        require(len(z.namelist()) == len(set(z.namelist())), 'Duplicate map member')
        for name, expected, dest in [('result.json', MAP_RESULT, output/'mapping-result.json'),
                                    (variant+'/soc_top.netlist.v', NETLISTS[variant], output/'mapped-input.v')]:
            require(z.getinfo(name).file_size == expected['bytes'], 'Wrong mapping member size')
            with z.open(name) as source, dest.open('xb') as target:
                shutil.copyfileobj(source, target, 1024**2)
            common.verify_file(dest, expected)
    row = json.loads((output/'mapping-result.json').read_text())
    require(row['github_source_commit'] == MAP_COMMIT
            and row['status'] == 'PASS_REPRODUCED_ORIGINAL_AND_CANDIDATE_32_SRAM_MAPPING_ONLY', 'Wrong source map verdict')
    check = row['mapping'][variant]['checks']
    require(check['top_ports'] == 79 and collections.Counter(check['macros'].values()) ==
            {'SP6TSRAM512x64': 16, 'DP8TSRAMDP256x16': 16}, 'Changed source macro/port census')
    require(row['outputs'][variant+'/soc_top.netlist.v'] == NETLISTS[variant], 'Wrong map output pin')
    return row


def fresh_config(original, netlist, template, mapping):
    require(original['CLOCK_PERIOD'] == 20 and original['CLOCK_PORT'] == ['clk_i', 'eth_rx_clk_i', 'eth_tx_clk_i'],
            'Original clock contract differs')
    require(original['PNR_SDC_FILE'] == original['SIGNOFF_SDC_FILE'], 'Original constraint files differ')
    macros = {name: master for master, entry in original['MACROS'].items() for name in entry['instances']}
    require(macros == mapping and collections.Counter(macros.values()) == {'SP6TSRAM512x64': 16, 'DP8TSRAMDP256x16': 16},
            'Original macro names/masters differ from exact mapped netlist')
    changed = copy.deepcopy(original)
    changed.update(VERILOG_FILES=[str(netlist)], FP_DEF_TEMPLATE=str(template),
                   FP_TEMPLATE_MATCH_MODE='strict', FP_TEMPLATE_COPY_POWER_PINS=False)
    require(not changed.get('IO_PIN_ORDER_CFG') and not changed.get('FP_PIN_ORDER_CFG'), 'Competing pin placement configuration')
    for name in original:
        if name != 'VERILOG_FILES': require(changed[name] == original[name], 'Original physical/SDC setting changed')
    return changed


def macro_contract(config, dbu, witness):
    require(witness['schema'] == 1 and witness['dbu'] == dbu and len(witness['macros']) == 32, 'Incomplete macro name witness')
    logical = {name: (master, int(round(spec['location'][0]*dbu)), int(round(spec['location'][1]*dbu)),
                     ODB_ORIENTATION[spec['orientation']])
               for master, entry in config['MACROS'].items() for name, spec in entry['instances'].items()}
    captured = {r['logical']: (r['master'], r['x_dbu'], r['y_dbu'], r['orientation']) for r in witness['macros']}
    require(len(captured) == 32 and captured == logical, 'Macro witness differs from source config')
    expected = {r['native']: captured[r['logical']] for r in witness['macros']}
    require(len(expected) == 32, 'Native macro witness is not bijective')
    return expected


def geometry_check(directory, config, witness=None):
    dbu = int((directory/'dbu.txt').read_text())
    require(dbu > 0, 'Invalid database units')
    rows = list(hold.read_rows(directory/'macros.tsv', ['instance', 'master', 'x_dbu', 'y_dbu', 'orientation', 'status']))
    if witness is None:
        require(common.sha(ROOT/MACRO_WITNESS) == PINS[MACRO_WITNESS], 'Exact captured native macro witness changed')
        witness = json.loads((ROOT/MACRO_WITNESS).read_text())
    expected = macro_contract(config, dbu, witness)
    actual = {}
    for row in rows:
        require(row['instance'] not in actual and row['status'] in {'FIRM', 'LOCKED', 'PLACED'}, 'Duplicate/unplaced macro')
        actual[row['instance']] = (row['master'], int(row['x_dbu']), int(row['y_dbu']), row['orientation'])
    require(actual == expected and len(actual) == 32, 'Macro master/position/orientation differs')
    pins = list(hold.read_rows(directory/'signal-pins.tsv',
        ['name', 'direction', 'signal_type', 'layer', 'x0_dbu', 'y0_dbu', 'x1_dbu', 'y1_dbu', 'status']))
    require(len({r['name'] for r in pins}) == 301 and len(pins) == len({tuple(r.values()) for r in pins}),
            'Incomplete or duplicate actual signal-terminal boxes')
    for row in pins:
        require(row['direction'] in {'INPUT', 'OUTPUT', 'INOUT'} and row['signal_type'] not in {'POWER', 'GROUND'}
                and row['status'] in {'PLACED', 'FIRM', 'LOCKED'}, 'Invalid signal-terminal placement')
        require(int(row['x0_dbu']) < int(row['x1_dbu']) and int(row['y0_dbu']) < int(row['y1_dbu']), 'Empty pin box')
    bounds = list(hold.read_rows(directory/'bounds.tsv', ['kind', 'x0_dbu', 'y0_dbu', 'x1_dbu', 'y1_dbu']))
    require({r['kind'] for r in bounds} == {'die', 'core'} and len(bounds) == 2, 'Incomplete die/core geometry')
    for row in bounds:
        expected = [int(round(v*dbu)) for v in config['DIE_AREA' if row['kind'] == 'die' else 'CORE_AREA']]
        require([int(row[k]) for k in ('x0_dbu', 'y0_dbu', 'x1_dbu', 'y1_dbu')] == expected, 'Die/core bounds changed')
    return {name: pin(directory/name) for name in GEOMETRY}


def audit_check(step, template_step, config, source_sdc_sha):
    row = json.loads((step/'audit.json').read_text())
    require(row['status'] == 'FRESH_GLOBAL_ROUTE_ESTIMATE_ONLY' and not any(row[k] for k in
            ('timing_accepted', 'candidate_adopted', 'manufacturing_approval')), 'Unexpected acceptance claim')
    before, after = geometry_check(template_step, config), geometry_check(step, config)
    require(before == after, 'Template pin or macro geometry changed during placement/CTS/GRT')
    checked = hold.validate_stage(step/'fresh_grt', row['hold_stage'], source_sdc_sha)
    require(sorted(checked['corner_names']) == CORNER_NAMES, 'Original PVT corner set changed')
    setup = {}
    for record in hold.read_rows(step/'setup-endpoints.tsv', ['endpoint', 'global_vertex_slack_seconds']):
        require(record['endpoint'] not in setup, 'Duplicate setup endpoint')
        setup[record['endpoint']] = hold.seconds(record['global_vertex_slack_seconds'])
    require(sorted(setup) == checked['endpoint_names'], 'Setup/hold endpoint coverage differs')
    negatives = sum(v is not None and v < 0 for v in setup.values())
    require(row['setup_endpoint_count'] == len(setup) and row['setup_negative_endpoint_count'] == negatives
            and row['timing_metrics']['setup_violating_endpoints'] == negatives
            and row['timing_metrics']['hold_violating_endpoints'] == checked['negative_vertex_endpoints'],
            'Aggregate setup/hold counts disagree with complete endpoint exports')
    for name, value in row['timing_metrics'].items():
        if name.endswith('_seconds'): require(hold.seconds(str(value)) is not None, 'Invalid timing aggregate')
        else: hold.exact_count(value)
    return dict(native=row, hold=checked, geometry=after, setup_endpoints=len(setup), setup_negative_endpoints=negatives)


def capture_audit(step, destination):
    """Preserve completed raw candidate views even when a later guard rejects them."""
    for name in (*GEOMETRY, 'audit.json', 'setup-endpoints.tsv', 'setup.rpt', 'hold.rpt', 'electrical.rpt'):
        if (step/name).is_file(): shutil.copyfile(step/name, destination/name)
    if (step/'fresh_grt').is_dir(): shutil.copytree(step/'fresh_grt', destination/'fresh_grt', dirs_exist_ok=True)
    views = {}
    for suffix, native in [('odb', 'odb'), ('def', 'def'), ('sdc', 'sdc'), ('v', 'nl.v')]:
        source = step/('soc_top.'+native)
        if source.is_file():
            target = destination/('soc_top.'+suffix); shutil.copyfile(source, target); views[target.name] = pin(target)
    return views


def run(variant, output, work):
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full physical work is cloud-only')
    require(variant in NETLISTS, 'Unsupported physical variant')
    output, work = common.fresh_directory(output), common.fresh_directory(work)
    row = dict(status='PREPARING', variant=variant, github_source_commit=os.environ.get('GITHUB_SHA'),
        candidate_adopted=False, timing_accepted=False, manufacturing_approval=False,
        full_soc_functional_accepted=False, boot_acceptance_inherited=False, final_route_or_signoff=False,
        preserved_boot_failure=copy.deepcopy(BOOT_FAILURE),
        scope='Matched fresh placement/CTS/global-route estimates with fixed C10 IO boxes and 32 SRAM locations. Qualified SRAM Liberty/RC, fresh logic proof of physical exports, detailed routing/DRC/LVS and manufacturing acceptance remain required.')
    methods = {}; inputs = {}; capture = output/'capture'; capture.mkdir(); run_dir = None
    try:
        for name in (*PINS, *OWN):
            if name in PINS: require(common.sha(ROOT/name) == PINS[name], 'Changed frozen dependency')
            dest = output/'methods'/name; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT/name).read_bytes()); methods[name] = pin(dest)
        row['methods'] = methods; common.save(output/'result.json', row)
        row['corrected_equivalence_gate'] = proof_gate(work, output)
        manifest = common.validate_manifest(json.loads((ROOT/MANIFEST).read_text()))
        required_disk = manifest['archive']['bytes']+sum(p['bytes'] for p in manifest['files'].values())+common.RUNTIME_BYTES+5*common.GIB
        sample = common.resource_sample(work)
        require(sample['available_memory_bytes'] >= 9*common.GIB and sample['free_disk_bytes'] >= required_disk,
                'Insufficient cloud memory/disk headroom')
        row['resources_before'] = sample
        archive = work/'source.tar.gz'; common.download(manifest['archive'], archive)
        bundle = work/'bundle'; common.restore(archive, bundle, manifest['files'])
        runtime = work/'runtime.AppImage'; common.download(manifest['runtime'], runtime); runtime.chmod(0o755)
        map_meta = api('actions/artifacts/'+str(MAP_ARTIFACT))
        require(map_meta['id'] == MAP_ARTIFACT and map_meta['name'] == 'alu-qualification-map-1'
                and map_meta['workflow_run']['id'] == MAP_RUN and map_meta['workflow_run']['head_sha'] == MAP_COMMIT
                and map_meta['size_in_bytes'] == MAP_ZIP['bytes'] and map_meta['digest'] == 'sha256:'+MAP_ZIP['sha256'],
                'Map artifact source identity differs')
        mapped_zip = work/'mapped.zip'; artifact_download(map_meta, mapped_zip)
        mapped = restore_mapping(mapped_zip, output, variant)
        original = common.translate(json.loads((bundle/manifest['config']).read_text()), bundle, manifest['files'])
        old_state = common.translate(json.loads((bundle/manifest['initial_state']).read_text()), bundle, manifest['files'])
        template, source_sdc = Path(old_state['def']), Path(old_state['sdc'])
        cfg = fresh_config(original, output/'mapped-input.v', template, mapped['mapping'][variant]['checks']['macros'])
        common.save(output/'config.json', cfg); common.save(output/'initial-state.json', dict(nl=str(output/'mapped-input.v'), metrics={}))
        inputs = dict(mapped=NETLISTS[variant], source_sdc=pin(source_sdc), raw_pnr_sdc=pin(Path(cfg['PNR_SDC_FILE'])),
                      shared_def_template=pin(template), runtime=pin(runtime), config=pin(output/'config.json'),
                      nl_only_initial_state=pin(output/'initial-state.json'), mapping_result=MAP_RESULT)
        row.update(immutable_inputs=inputs, original_selected_metrics=manifest['selected_source_metrics'],
                   original_macro_geometry=cfg['MACROS'], mapping_source=dict(run=MAP_RUN, source_commit=MAP_COMMIT,
                   artifact_id=MAP_ARTIFACT, archive=MAP_ZIP, netlist=NETLISTS[variant]))
        run_dir = work/'run'; run_dir.mkdir()
        command = [str(runtime), 'python', str(output/'methods/hw/soc/pnr/alu_physical_flow.py'),
            '--flow', 'ALUFreshPhysical', '--manual-pdk', '--pdk-root', str(bundle/manifest['pdk_root']),
            '--pdk', manifest['pdk'], '--force-run-dir', str(run_dir),
            '--with-initial-state', str(output/'initial-state.json'), str(output/'config.json')]
        result = hold.execute(command, output, row, 'fresh-physical', hold.clean_environment())
        require(result['returncode'] == 0, 'Fresh native physical flow failed; captured evidence retained')
        geometry_steps = list(run_dir.glob('*-openroad-aluphysicaltemplategeometry'))
        audit_steps = list(run_dir.glob('*-openroad-aluphysicalfreshrouteaudit'))
        require(len(geometry_steps) == len(audit_steps) == 1, 'Missing or duplicate fresh audit stages')
        final_views = capture_audit(audit_steps[0], capture)
        row['final_views'] = final_views
        require(set(final_views) == {'soc_top.odb', 'soc_top.def', 'soc_top.sdc', 'soc_top.v'}, 'Incomplete final physical views')
        checked = audit_check(audit_steps[0], geometry_steps[0], cfg, inputs['source_sdc']['sha256'])
        row.update(status='FRESH_PHYSICAL_COMPLETE_ESTIMATE_ONLY', native_validation=checked, final_views=final_views)
        for name, expected in manifest['files'].items(): common.verify_file(bundle/name, expected)
        for name, expected in methods.items(): common.verify_file(output/'methods'/name, expected)
        for path, expected in [(runtime, inputs['runtime']), (output/'mapped-input.v', inputs['mapped']),
                (output/'config.json', inputs['config']), (output/'initial-state.json', inputs['nl_only_initial_state'])]:
            common.verify_file(path, expected)
        row['all_inputs_rechecked'] = True
    except BaseException as exc:
        row.update(status='FAILED_PRESERVED', error=repr(exc)); raise
    finally:
        # Preserve real startup/audit failures as well as successful summaries.
        # Large native databases remain in the full job work directory unless a
        # completed candidate has already been explicitly captured above.
        if run_dir is not None:
            audit_steps = list(run_dir.glob('*-openroad-aluphysicalfreshrouteaudit'))
            if len(audit_steps) == 1 and 'final_views' not in row:
                row['final_views'] = capture_audit(audit_steps[0], capture)
            for path in sorted(run_dir.rglob('*')):
                if path.is_file() and not path.is_symlink() and path.suffix in {'.log', '.json', '.tcl', '.rpt'}:
                    relative = path.relative_to(run_dir)
                    target = output/'native-logs'/relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
        row['outputs'] = {str(p.relative_to(output)): pin(p) for p in sorted(output.rglob('*'))
                          if p.is_file() and p != output/'result.json'}
        common.save(output/'result.json', row)
        summary = output.with_name(output.name+'-summary'); summary.mkdir(exist_ok=False)
        shutil.copyfile(output/'result.json', summary/'result.json')
        if (output/'config.json').exists(): shutil.copyfile(output/'config.json', summary/'config.json')
        for name in GEOMETRY:
            if (capture/name).exists(): shutil.copyfile(capture/name, summary/name)
    return row


def compare(original, candidate):
    binding = require_execution_ready()
    rows = [json.loads((root/'result.json').read_text()) for root in (original, candidate)]
    configs = [json.loads((root/'config.json').read_text()) for root in (original, candidate)]
    for variant, root, row in zip(NETLISTS, (original, candidate), rows):
        require(row['variant'] == variant and row['status'] == 'FRESH_PHYSICAL_COMPLETE_ESTIMATE_ONLY'
                and row['all_inputs_rechecked'] is True, 'Incomplete matched physical arm')
        require(row['mapping_source']['netlist'] == NETLISTS[variant], 'Wrong matched mapped input')
        common.verify_file(root/'config.json', row['immutable_inputs']['config'])
        require(set(row['methods']) == set(PINS) | set(OWN), 'Incomplete physical source inventory')
        for name, expected in row['methods'].items(): common.verify_file(ROOT/name, expected)
        for name in GEOMETRY:
            common.verify_file(root/name, row['native_validation']['geometry'][name])
    require(rows[0]['github_source_commit'] == rows[1]['github_source_commit']
            and rows[0]['methods'] == rows[1]['methods'], 'Different physical recipes')
    require(rows[0]['github_source_commit'] == os.environ.get('GITHUB_SHA'), 'Comparison checkout differs from native producer')
    require(rows[0]['corrected_equivalence_gate'] == rows[1]['corrected_equivalence_gate'], 'Different complete binary proof gates')
    gate = rows[0]['corrected_equivalence_gate']
    require(gate['binding'] == binding and gate['status'] == 'COMPLETE_BINARY_RELATION_REPARSED_NO_NEW_NATIVE_PROOF'
            and gate['complete_groups'] == 269 and gate['complete_output_obligation_bits'] == 34321
            and gate['symbolic_input_bits'] == 10828 and gate['no_internal_assumptions'] is True,
            'Matched physical arms lack the bound complete binary proof')
    for cfg in configs: cfg.pop('VERILOG_FILES')
    require(configs[0] == configs[1], 'Unmatched physical configurations')
    for key in ('source_sdc', 'raw_pnr_sdc', 'shared_def_template', 'runtime'):
        require(rows[0]['immutable_inputs'][key] == rows[1]['immutable_inputs'][key], 'Unmatched original input '+key)
    require(rows[0]['native_validation']['geometry'] == rows[1]['native_validation']['geometry'],
            'Actual shared IO/macro geometry differs')
    before, after = [row['native_validation']['native']['timing_metrics'] for row in rows]
    return dict(status='MATCHED_FRESH_GLOBAL_ROUTE_COMPARISON_ONLY', original=before, candidate=after,
        candidate_minus_original={k: after[k]-before[k] for k in before},
        original_selected_c10_reference=rows[0]['original_selected_metrics'],
        same_actual_pins_and_macros=True, same_constraints_and_corners=True,
        candidate_adopted=False, timing_accepted=False, full_soc_functional_accepted=False, manufacturing_approval=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=NETLISTS); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work', type=Path); parser.add_argument('--compare-original', type=Path)
    parser.add_argument('--compare-candidate', type=Path); args = parser.parse_args()
    if args.compare_original or args.compare_candidate:
        require(args.compare_original and args.compare_candidate and not args.variant, 'Both comparison arms required')
        result = compare(args.compare_original, args.compare_candidate); common.save(args.output, result)
    else:
        require(args.variant and args.work, 'Variant and work directory required')
        result = run(args.variant, args.output.resolve(), args.work.resolve())
    print(result['status'])


if __name__ == '__main__': main()
