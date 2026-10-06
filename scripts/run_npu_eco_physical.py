#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh matched original/NPU-factored physical experiments after strict boot.

Use a previously restored exact C10 bundle and runtime locally. Reuse only the
old geometry/configuration/audit methods; never clear or replace the old failed
candidate's proof/boot guards. Placement/CTS/global-route estimates do not grant
final timing, post-layout equivalence, SRAM qualification or chip acceptance.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import check_npu_eco_physical_readiness as readiness
import npu_physical_process as owned
import run_cloud_alu_physical as physical

ROOT = Path(__file__).resolve().parents[1]
common = physical.common
require = physical.require
pin = physical.pin
VARIANTS = ('original', 'factored')
ADDITIONAL_PINS = {
    'scripts/run_cloud_alu_physical.py': '089309970e529cc7b9308b32bd04719acff34147a3e69b427a837797700c7525',
    'hw/soc/pnr/alu_physical_flow.py': '3955abd944439d2bd4305eebbea2eaa250523fffb239f453cc3168c218e69306',
    'hw/soc/pnr/alu_physical_geometry.tcl': '64ca8e1419059aaf1be6e443bc19a6a04bc53ee945baf5d4a04d7b0948012e00',
    'hw/soc/pnr/alu_physical_audit.tcl': '4f36340558ee7bb4a6c9f26bfdc50752561a137dc9c380b78d9bad3b34c46885',
    'scripts/check_npu_eco_physical_readiness.py': '3c082f1df3d3e8403de8e41d9a4b60d59e7244ba820926074a53fc450ce4dec4',
    'scripts/npu_physical_process.py': '39dedf775c53370fe7696fab46b198bf3d727c3dbf52dbd4148c3d70134ff526',
}
METHODS = {*physical.PINS, *physical.OWN, *ADDITIONAL_PINS,
           'scripts/run_npu_eco_physical.py', 'sw/tests/test_npu_eco_physical.py'}
NETLISTS = {'original': physical.NETLISTS['original'], 'factored': readiness.PHYSICAL_INPUT}


def capture_methods(output):
    result = {}
    for name in sorted(METHODS):
        source = ROOT / name
        digest = {**physical.PINS, **ADDITIONAL_PINS}.get(name)
        require(digest is None or common.sha(source) == digest, 'Changed physical method: ' + name)
        target = output / 'methods' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        result[name] = pin(target)
    return result


def require_gate(gate, variant):
    require(variant in VARIANTS, 'Only original and exact factored inputs are supported')
    require(gate.get('status') == 'READY_FOR_REVIEWED_PHYSICAL_EXPERIMENT_ONLY',
            'Strict NPU physical readiness is blocked: ' + str(gate.get('blocker')))
    bridge = gate['mapped_bridge']
    key = 'matched_original' if variant == 'original' else 'physical_input'
    require(bridge[key] == NETLISTS[variant], 'Readiness identified a different mapped input')
    source = Path(bridge[key + '_path'])
    require(pin(source) == NETLISTS[variant], 'Mapped input changed after readiness verification')
    require(gate['strict_boot']['firmware_checks'] == 28
            and gate['strict_boot']['vendor_eco_netlist'] == readiness.FACTORED
            and gate['binary_relation']['counts']['total'] == 34321,
            'Incomplete readiness relation or strict boot')
    return source


def resources(directory):
    sample = common.resource_sample(directory)
    require(sample['available_memory_bytes'] >= 9 * common.GIB
            and sample['free_disk_bytes'] >= 3 * common.GIB,
            'Insufficient local memory/disk reserve: ' + str(sample))
    return sample


def execute(command, output, record):
    """No healthy elapsed-time kill; retain the exact owned leader for cleanup."""
    before = resources(output)
    started = time.monotonic()
    child = None

    def interrupted(signum, frame):
        raise InterruptedError('Native physical observer received signal ' + str(signum))

    previous = {s: signal.signal(s, interrupted) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        with (output / 'fresh-physical.log').open('xb') as log:
            # Keep interruption pending until the owned handle is assigned.
            # Child setup restores the original mask before applying limits.
            mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})

            def child_setup():
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
                common.limits()

            try:
                child = owned.owned_popen(command, cwd=output, env=physical.hold.clean_environment(),
                    stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, close_fds=True,
                    start_new_session=True, preexec_fn=child_setup)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, mask)
            record.update(status='RUNNING_FRESH_PHYSICAL', native_identity=child.nssoc_owned_identity,
                          boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                          command=command, resources_before_native=before,
                          native_address_space_limit_bytes=8 * common.GIB)
            while True:
                result = child.poll()
                record.update(phase_elapsed_seconds=time.monotonic() - started, utc=common.now())
                common.save(output / 'result.json', record)
                if result is not None:
                    break
                time.sleep(1)
        return {'command': command, 'returncode': result, 'elapsed_seconds': time.monotonic() - started,
                'completed': common.now(), 'resources_before': before}
    except BaseException:
        if child is not None:
            owned.stop_failed_group(child)
        raise
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def verify_bundle(bundle, runtime):
    manifest = common.validate_manifest(json.loads((ROOT / physical.MANIFEST).read_text()))
    require(common.sha(ROOT / physical.MANIFEST) == physical.PINS[physical.MANIFEST], 'Changed source manifest')
    for name, expected in manifest['files'].items():
        common.verify_file(bundle / name, expected)
    common.verify_file(runtime, manifest['runtime'])
    require(os.access(runtime, os.X_OK), 'Exact runtime is not executable')
    return manifest


def capture_template(step, output):
    target = output / 'capture-template'
    target.mkdir(exist_ok=True)
    for name in physical.GEOMETRY:
        if (step / name).is_file():
            shutil.copyfile(step / name, target / name)
    return {name: pin(target / name) for name in physical.GEOMETRY if (target / name).is_file()}


def verify_saved_geometry(output, config, expected):
    require(set(expected) == set(physical.GEOMETRY), 'Incomplete saved template inventory')
    before = physical.geometry_check(output / 'capture-template', config)
    after = physical.geometry_check(output / 'capture', config)
    require(before == expected, 'Saved original template geometry changed')
    require(before == after, 'Actual template and final pin/macro geometry differ')
    return before


def preserve(run_dir, output, row):
    capture = output / 'capture'
    if run_dir is not None:
        templates = list(run_dir.glob('*-openroad-aluphysicaltemplategeometry'))
        if len(templates) == 1 and 'template_geometry' not in row:
            row['template_geometry'] = capture_template(templates[0], output)
        audits = list(run_dir.glob('*-openroad-aluphysicalfreshrouteaudit'))
        if len(audits) == 1 and 'final_views' not in row:
            row['final_views'] = physical.capture_audit(audits[0], capture)
        for path in sorted(run_dir.rglob('*')):
            if path.is_file() and not path.is_symlink() and path.suffix in {'.log', '.json', '.tcl', '.rpt'}:
                target = output / 'native-logs' / path.relative_to(run_dir)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    row['outputs'] = {str(p.relative_to(output)): pin(p) for p in sorted(output.rglob('*'))
                      if p.is_file() and p != output / 'result.json'}
    common.save(output / 'result.json', row)


def run(variant, output, work, bundle, runtime, *, boot_archive, boot_run, boot_artifact):
    require(variant in VARIANTS, 'Unsupported physical variant')
    output = common.fresh_directory(output)
    (output / 'capture').mkdir()
    row = {'status': 'PREPARING', 'variant': variant, 'utc': common.now(),
           'candidate_adopted': False, 'timing_accepted': False, 'manufacturing_approval': False,
           'full_soc_functional_accepted': False, 'final_route_or_signoff': False,
           'preserved_old_boot_failure': copy.deepcopy(physical.BOOT_FAILURE),
           'affinity': sorted(os.sched_getaffinity(0)),
           'scope': 'Matched C10 placement/CTS/global-route estimates only, after exact ECO boot. '
                    'Qualified SRAM Liberty/RC, fresh post-layout equivalence, detailed routing, '
                    'all timing classes, DRC/LVS and manufacturing acceptance remain required.'}
    run_dir = None
    try:
        methods = capture_methods(output)
        row['methods'] = methods
        gate = readiness.check(archive=boot_archive, run_path=boot_run, artifact_path=boot_artifact)
        row['readiness'] = gate
        common.save(output / 'readiness.json', gate)
        source = require_gate(gate, variant)
        row['boot_inputs'] = {key: {'path': str(Path(path).absolute()), **pin(path)}
                              for key, path in [('archive', boot_archive), ('run_path', boot_run),
                                                ('artifact_path', boot_artifact)]}
        # No native process or physical work directory exists before this gate.
        row['resources_before'] = resources(output)
        work = common.fresh_directory(work)
        bundle, runtime = Path(bundle).absolute(), Path(runtime).absolute()
        manifest = verify_bundle(bundle, runtime)
        target = output / 'mapped-input.v'
        shutil.copyfile(source, target)
        common.verify_file(target, NETLISTS[variant])
        mapping = json.loads((ROOT / readiness.MAPPING / 'native01/result.json').read_text())
        original = common.translate(json.loads((bundle / manifest['config']).read_text()), bundle, manifest['files'])
        state = common.translate(json.loads((bundle / manifest['initial_state']).read_text()), bundle, manifest['files'])
        template, source_sdc = Path(state['def']), Path(state['sdc'])
        cfg = physical.fresh_config(original, target, template, mapping['stages'][variant]['mapping_contract']['macros'])
        common.save(output / 'config.json', cfg)
        common.save(output / 'initial-state.json', {'nl': str(target), 'metrics': {}})
        inputs = {'mapped': pin(target), 'source_sdc': pin(source_sdc),
                  'raw_pnr_sdc': pin(Path(cfg['PNR_SDC_FILE'])), 'shared_def_template': pin(template),
                  'runtime': pin(runtime), 'config': pin(output / 'config.json'),
                  'nl_only_initial_state': pin(output / 'initial-state.json')}
        row.update(immutable_inputs=inputs, original_selected_metrics=manifest['selected_source_metrics'])
        run_dir = work / 'run'
        run_dir.mkdir()
        command = [str(runtime), 'python', str(output / 'methods/hw/soc/pnr/alu_physical_flow.py'),
                   '--flow', 'ALUFreshPhysical', '--manual-pdk', '--pdk-root', str(bundle / manifest['pdk_root']),
                   '--pdk', manifest['pdk'], '--force-run-dir', str(run_dir),
                   '--with-initial-state', str(output / 'initial-state.json'), str(output / 'config.json')]
        row['execution'] = execute(command, output, row)
        require(row['execution']['returncode'] == 0, 'Fresh native physical flow failed; retained')
        geometry = list(run_dir.glob('*-openroad-aluphysicaltemplategeometry'))
        audits = list(run_dir.glob('*-openroad-aluphysicalfreshrouteaudit'))
        require(len(geometry) == len(audits) == 1, 'Missing/duplicate fresh audit stages')
        row['template_geometry'] = capture_template(geometry[0], output)
        row['final_views'] = physical.capture_audit(audits[0], output / 'capture')
        require(set(row['final_views']) == {'soc_top.odb', 'soc_top.def', 'soc_top.sdc', 'soc_top.v'},
                'Incomplete physical exports')
        row['native_validation'] = physical.audit_check(audits[0], geometry[0], cfg, inputs['source_sdc']['sha256'])
        verify_saved_geometry(output, cfg, row['template_geometry'])
        require(verify_bundle(bundle, runtime) == manifest, 'Source bundle changed during physical work')
        for name, expected in methods.items():
            common.verify_file(ROOT / name, expected)
            common.verify_file(output / 'methods' / name, expected)
        for name, key in [('mapped-input.v', 'mapped'), ('config.json', 'config'),
                          ('initial-state.json', 'nl_only_initial_state')]:
            common.verify_file(output / name, inputs[key])
        require(readiness.check(archive=boot_archive, run_path=boot_run, artifact_path=boot_artifact) == gate,
                'Readiness evidence changed during physical work')
        row.update(status='FRESH_NPU_PHYSICAL_COMPLETE_ESTIMATE_ONLY', all_inputs_rechecked=True)
    except BaseException as error:
        row.update(status='FAILED_PRESERVED', error=repr(error))
        raise
    finally:
        preserve(run_dir, output, row)
    return row


def compare(original, factored):
    rows, configs = [], []
    for variant, root in zip(VARIANTS, (original, factored)):
        row = json.loads((root / 'result.json').read_text())
        require(row['variant'] == variant and row['status'] == 'FRESH_NPU_PHYSICAL_COMPLETE_ESTIMATE_ONLY'
                and row['all_inputs_rechecked'] is True and row['execution']['returncode'] == 0,
                'Incomplete physical arm')
        require(not any(row[k] for k in ('candidate_adopted', 'timing_accepted', 'manufacturing_approval',
                                        'full_soc_functional_accepted', 'final_route_or_signoff')), 'Unexpected acceptance')
        require_gate(row['readiness'], variant)
        for entry in row['boot_inputs'].values():
            require(pin(entry['path']) == {k: entry[k] for k in ('bytes', 'sha256')}, 'Boot input changed')
        require(readiness.check(**{key: Path(entry['path']) for key, entry in row['boot_inputs'].items()})
                == row['readiness'], 'Stored readiness does not match complete saved evidence')
        require(set(row['methods']) == METHODS and row['immutable_inputs']['mapped'] == NETLISTS[variant],
                'Wrong physical source/method inventory')
        for name, expected in row['outputs'].items():
            common.verify_file(root / str(common.safe_relative(name)), expected)
        for name, expected in row['methods'].items():
            common.verify_file(ROOT / name, expected)
        config = json.loads((root / 'config.json').read_text())
        common.verify_file(root / 'config.json', row['immutable_inputs']['config'])
        require(config.pop('VERILOG_FILES') == [str(root / 'mapped-input.v')], 'Wrong physical netlist path')
        for name in physical.GEOMETRY:
            common.verify_file(root / 'capture' / name, row['native_validation']['geometry'][name])
        verify_saved_geometry(root, config, row['template_geometry'])
        checked = physical.audit_check(root / 'capture', root / 'capture-template', config,
                                       row['immutable_inputs']['source_sdc']['sha256'])
        require(checked == row['native_validation'], 'Stored timing does not match complete raw audit')
        rows.append(row)
        configs.append(config)
    require(configs[0] == configs[1], 'Unmatched physical configuration')
    for key in ('readiness', 'methods', 'affinity', 'original_selected_metrics'):
        require(rows[0][key] == rows[1][key], 'Unmatched physical ' + key)
    for key in ('source_sdc', 'raw_pnr_sdc', 'shared_def_template', 'runtime'):
        require(rows[0]['immutable_inputs'][key] == rows[1]['immutable_inputs'][key], 'Unmatched input ' + key)
    require(rows[0]['native_validation']['geometry'] == rows[1]['native_validation']['geometry'],
            'Actual pin/macro geometry differs')
    before, after = [r['native_validation']['native']['timing_metrics'] for r in rows]
    require(set(before) == set(after), 'Unmatched timing metrics')
    return {'status': 'MATCHED_NPU_FRESH_GLOBAL_ROUTE_COMPARISON_ONLY', 'original': before, 'factored': after,
            'factored_minus_original': {k: after[k] - before[k] for k in before},
            'same_actual_pins_and_macros': True, 'same_constraints_and_corners': True,
            'candidate_adopted': False, 'timing_accepted': False, 'manufacturing_approval': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=VARIANTS)
    parser.add_argument('--output', type=Path, required=True)
    for name in ('work', 'bundle', 'runtime', 'boot-archive', 'boot-run', 'boot-artifact',
                 'compare-original', 'compare-factored'):
        parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    if args.compare_original or args.compare_factored:
        require(args.compare_original and args.compare_factored and args.variant is None,
                'Both comparison arms required')
        with args.output.open('x') as stream:
            stream.write(json.dumps(compare(args.compare_original.absolute(), args.compare_factored.absolute()), indent=2) + '\n')
    else:
        require(args.variant and all(getattr(args, name) for name in
                ('work', 'bundle', 'runtime', 'boot_archive', 'boot_run', 'boot_artifact')), 'All native inputs required')
        run(args.variant, args.output, args.work, args.bundle, args.runtime,
            boot_archive=args.boot_archive, boot_run=args.boot_run, boot_artifact=args.boot_artifact)


if __name__ == '__main__':
    main()
