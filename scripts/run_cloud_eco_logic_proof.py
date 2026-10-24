#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove the limited logical ECO contract for one immutable completed cloud trial.

Producer capture validation is replayed with its own Git-bound source first.
Original C10 netlist, actual Liberty and SRAM interfaces are never rewritten.
All large inputs and native work belong on the explicitly selected cloud runner.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
import run_cloud_timing_experiment as common

REPO = Path(__file__).resolve().parents[1]
REPOSITORY = 'Melihakbulut221/nssoc'
MANIFEST = 'docs/evidence/timing-cloud-input-20260930.json'
MANIFEST_SHA = 'b8c3044903eff78728c4a5205a2e054576ad91ccdaa0bff28c59de3d88ae712a'
STANDARD = 'pdk/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
MACRO = 'inputs/hw/soc/out/external-review-20260919/route-closure-20260923/sram-chip-integration/independent_bb.v'
BEFORE = 'inputs/hw/soc/out/pipeline-timing-checkpointed-20260929/attempt3/chunk-010/01-openroad-resizertimingpostgrt/soc_top.nl.v'
CHECKER = 'hw/soc/flow/check_eco_logic_clones.py'
SOURCES = ('scripts/run_cloud_eco_logic_proof.py', 'scripts/run_cloud_timing_experiment.py',
           CHECKER, 'hw/soc/flow/eco_logic.py', 'hw/soc/flow/eco_logic_clones.py',
           'sw/tests/eco_logic_native.py', '.github/workflows/timing-eco-logic-proof.yml', MANIFEST)
TRIALS = {
    'xor_36990647399': dict(
        run_id=36990647399, source_commit='945881e8bd9854419f1f3066039c380658693a81',
        artifact_id=11219574425, artifact_name='xor-buffer-final-1',
        bytes=248148901, sha256='193b853c159cf5ca9c9e8d3482039a9286be2e9dad44c7d3c0c58954ad7a93d8',
        entrypoint='scripts/run_cloud_xor_buffer.py', kind='xor_buffer_trial',
        candidate='run/01-openroad-resizertimingpostgrt/rejected-candidate/soc_top.v',
        candidate_pin=dict(bytes=12107653,
                           sha256='133d4749a7f8d3c8562e86b98c9e8065e372cd22da1e8c3ad9986c6df7b42062')),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_pin(path):
    return dict(bytes=path.stat().st_size, sha256=common.sha(path))


def github_json(endpoint):
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{REPOSITORY}/{endpoint}']))


def validate_metadata(trial, run, artifact):
    require(run.get('id') == trial['run_id'] and run.get('head_sha') == trial['source_commit']
            and run.get('status') == 'completed' and run.get('conclusion') == 'success',
            'Producer must be the pinned successfully completed run')
    require(run.get('repository', {}).get('full_name') == REPOSITORY, 'Wrong producer repository')
    require(artifact.get('id') == trial['artifact_id'] and artifact.get('name') == trial['artifact_name']
            and artifact.get('expired') is False and artifact.get('size_in_bytes') == trial['bytes']
            and artifact.get('digest') == 'sha256:' + trial['sha256'], 'Artifact identity differs')
    origin = artifact.get('workflow_run', {})
    require(origin.get('id') == trial['run_id'] and origin.get('head_sha') == trial['source_commit'],
            'Artifact producer source differs')


def extract_zip(archive, destination):
    """No links, path aliases, duplicates or unbounded expanded artifact contents."""
    destination.mkdir()
    seen, total = set(), 0
    with zipfile.ZipFile(archive) as source:
        for info in source.infolist():
            name = str(common.safe_relative(info.filename))
            mode = info.external_attr >> 16
            require(name not in seen and not info.is_dir()
                    and not stat.S_ISLNK(mode) and (stat.S_IFMT(mode) in (0, stat.S_IFREG)),
                    'Unsafe/duplicate artifact ZIP member')
            total += info.file_size
            require(total <= 8 * common.GIB and info.file_size <= 2 * common.GIB,
                    'Artifact expanded size exceeds bounded capture')
            path = destination/name
            path.parent.mkdir(parents=True, exist_ok=True)
            with source.open(info) as incoming, path.open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing, 1024**2)
            require(path.stat().st_size == info.file_size, 'Truncated artifact member')
            seen.add(name)
    require(seen, 'Empty artifact')
    return dict(files=len(seen), expanded_bytes=total)


def git_bytes(commit, path):
    return subprocess.check_output(['git', '-C', str(REPO), 'show', f'{commit}:{path}'])


def verify_producer_sources(capture, trial):
    row = json.loads((capture/'result.json').read_text())
    require(row.get('github_source_commit') == trial['source_commit']
            and row.get('diagnostic_kind') == trial['kind'], 'Captured producer source/kind differs')
    require(row.get('manifest_sha256') == MANIFEST_SHA, 'Captured C10 manifest differs')
    methods = row.get('method_files')
    require(isinstance(methods, dict) and trial['entrypoint'] in methods, 'Missing original validator source')
    actual = {str(p.relative_to(capture/'methods')) for p in (capture/'methods').rglob('*') if p.is_file()}
    require(actual == set(methods), 'Captured method tree differs from inventory')
    for name, pin in methods.items():
        common.safe_relative(name)
        common.pin(pin)
        common.verify_file(capture/'methods'/name, pin)
        blob = git_bytes(trial['source_commit'], name)
        require(len(blob) == pin['bytes'] and hashlib.sha256(blob).hexdigest() == pin['sha256'],
                f'Captured method is not the exact producer Git blob: {name}')
    return methods


def bundle_inputs(bundle, manifest):
    """Select original unpowered state.nl and actual custom SRAM interfaces."""
    state = json.loads((bundle/manifest['initial_state']).read_text())
    config = json.loads((bundle/manifest['config']).read_text())
    require(state.get('nl') == '@BUNDLE@/' + BEFORE, 'Selected C10 original state.nl differs')
    require(config.get('STD_CELL_LIBRARY') == 'sg13g2_stdcell', 'Selected standard library differs')
    macros = config.get('MACROS', {})
    require(set(macros) == {'SP6TSRAM512x64', 'DP8TSRAMDP256x16'}, 'Selected macro interfaces differ')
    for macro in macros.values():
        require(macro.get('vh') == ['@BUNDLE@/' + MACRO], 'Selected SRAM Verilog interface differs')
    for name in (BEFORE, STANDARD, MACRO):
        common.verify_file(bundle/name, manifest['files'][name])
    return bundle/BEFORE, bundle/STANDARD, bundle/MACRO


def execute(command, output, name):
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    # The proof has no GitHub access and cannot inherit user Python code paths.
    for key in ('GH_TOKEN', 'GITHUB_TOKEN', 'PYTHONPATH', 'PYTHONHOME'):
        env.pop(key, None)
    with (output/(name+'.log')).open('w') as log:
        result = subprocess.run(list(map(str, command)), stdout=log, stderr=subprocess.STDOUT,
                                env=env, stdin=subprocess.DEVNULL, check=False)
    receipt = dict(command=list(map(str, command)), returncode=result.returncode)
    common.save(output/(name+'-execution.json'), receipt)
    return result.returncode


def run(trial_name, output, work):
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full artifact/native work is cloud-only')
    trial = TRIALS[trial_name]
    output = common.fresh_directory(output)
    work = common.fresh_directory(work)
    row = dict(schema=1, status='PREPARING', trial=trial_name, producer=trial,
               github_source_commit=os.environ.get('GITHUB_SHA'), candidate_adopted=False,
               timing_accepted=False, manufacturing_approval=False,
               scope='Limited retained-input/state and combinational-clone equation proof; '
                     'excludes SRAM internals, initialization, analog, CDC, timing and physical connectivity.')
    common.save(output/'result.json', row)
    try:
        methods = {}
        for name in SOURCES:
            common.safe_relative(name)
            source, target = REPO/name, output/'methods'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            methods[name] = file_pin(target)
        row['methods'] = methods
        manifest_path = output/'methods'/MANIFEST
        require(common.sha(manifest_path) == MANIFEST_SHA, 'Published C10 manifest changed')
        manifest = common.validate_manifest(json.loads(manifest_path.read_text()))
        run_info = github_json(f"actions/runs/{trial['run_id']}")
        artifact_info = github_json(f"actions/artifacts/{trial['artifact_id']}")
        validate_metadata(trial, run_info, artifact_info)
        common.save(output/'producer-run.json', run_info)
        common.save(output/'producer-artifact.json', artifact_info)
        archive = work/'producer.zip'
        with archive.open('xb') as stream:
            subprocess.run(['gh', 'api', f"repos/{REPOSITORY}/actions/artifacts/{trial['artifact_id']}/zip"],
                           stdout=stream, check=True)
        common.verify_file(archive, trial)
        capture = work/'producer'
        row['artifact_extraction'] = extract_zip(archive, capture)
        row['producer_methods'] = verify_producer_sources(capture, trial)
        for name in ('capture.json', 'result.json', 'source-manifest.json', 'source-state.json', 'source-config.json'):
            target = output/'producer-records'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(capture/name, target)
        command = [sys.executable, capture/'methods'/trial['entrypoint'], 'validate',
                   '--directory', capture, '--manifest', manifest_path]
        require(execute(command, output, 'original-capture-validation') == 0,
                'Original source-bound producer capture validation failed')
        candidate = capture/trial['candidate']
        common.verify_file(candidate, trial['candidate_pin'])
        row['original_capture_validation'] = 'PASS'
        row['phase'] = 'immutable-bundle-and-runtime'
        common.save(output/'result.json', row)
        common.download(manifest['archive'], work/'input.tar.gz')
        bundle = work/'bundle'
        common.restore(work/'input.tar.gz', bundle, manifest['files'])
        before, liberty, macro = bundle_inputs(bundle, manifest)
        runtime = work/'runtime.AppImage'
        common.download(manifest['runtime'], runtime)
        runtime.chmod(0o755)
        row['runtime'] = manifest['runtime']
        row['proof_inputs'] = {str(p): file_pin(p) for p in (before, candidate, liberty, macro)}
        row['phase'] = 'native-controls'
        common.save(output/'result.json', row)
        command = [runtime, 'python', output/'methods/sw/tests/eco_logic_native.py',
                   '--checker', output/'methods'/CHECKER, '--liberty', liberty,
                   '--output', output/'controls']
        require(execute(command, output, 'native-controls') == 0, 'Native equation/macro controls failed')
        row['controls'] = json.loads((output/'controls/result.json').read_text())
        require(row['controls'].get('status') == 'PASS_NATIVE_ECO_CONTROLS', 'Incomplete native controls')
        row['phase'] = 'full-netlist-proof'
        common.save(output/'result.json', row)
        command = [runtime, 'python', output/'methods'/CHECKER, before, candidate,
                   '--liberty', liberty, '--macro-verilog', macro, '--output', output/'proof']
        code = execute(command, output, 'proof')
        require(code == 0, 'Proof rejected or could not support the candidate; inspect unchanged raw proof log')
        proof = json.loads((output/'proof/result.json').read_text())
        require(proof.get('status') == 'PASS within scope', 'Missing limited proof result')
        for name, pin in row['proof_inputs'].items():
            common.verify_file(Path(name), pin)
        common.verify_file(runtime, manifest['runtime'])
        for name, pin in methods.items():
            common.verify_file(output/'methods'/name, pin)
        row.update(status='PASS_LIMITED_ECO_LOGIC_ONLY', proof=proof, phase='complete')
    except Exception as error:
        row.update(status='FAILED_PRESERVED', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        row['outputs'] = {str(p.relative_to(output)): file_pin(p)
                          for p in sorted(output.rglob('*')) if p.is_file() and p != output/'result.json'}
        common.save(output/'result.json', row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', choices=tuple(TRIALS), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    run(args.trial, args.output.resolve(), args.work.resolve())


if __name__ == '__main__':
    main()
