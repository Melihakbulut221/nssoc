#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replay one complete targeted-hold archive with exact producer Python; no native tools."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import archive_hold_diagnostic as common

SOURCE = 'ea0d78f4be2f808318508f020b0d81c44ff380c7'
RUN = 36968724381
ARTIFACT = 11211540042
SIZE = 270228757
DIGEST = 'b57c433455e59f396ec91d40456c473c4a11fd78e413ff1c093e388d38460f4e'
MEMBERS, EXPANDED = 153, 518785253
COMMON_SHA = '04b89e92cee0bc60d68bc0f1d0d1f313231f622c56333547997108e65cea2c06'
METHODS = common.METHODS + ('.github/workflows/timing-targeted-hold.yml',
    'scripts/run_cloud_targeted_hold.py','scripts/compare_full_hold_endpoints.py',
    'scripts/run_timing_experiments.py','scripts/timing_process_guard.py',
    'hw/soc/pnr/timing_targeted_hold_probe_step.tcl',
    'hw/soc/pnr/timing_targeted_hold_probe_helpers.tcl',
    'hw/soc/pnr/timing_repair_experiment.tcl','sw/tests/timing_hold_targeted_native.tcl')
MANIFEST = common.MANIFEST
STAGES = ('matched_before','after_repair_native','after_hold','after_full_update')


def source_blob(name):
    # Immutable full commit reference, independent of the checkout's depth/history.
    return subprocess.check_output(['gh','api','-H','Accept: application/vnd.github.raw+json',
        f'repos/{common.REPO}/contents/{name}?ref={SOURCE}'])


def pin_sources(capture,review):
    result=json.loads((capture/'result.json').read_text())
    if result.get('github_source_commit')!=SOURCE or set(result.get('method_files',{}))!=set(METHODS):
        raise ValueError('Captured producer source identity or method closure differs')
    native=common.fresh(review/'producer-source');pins={}
    for name in (*METHODS,MANIFEST,*common.LICENSES):
        data=source_blob(name);pin=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        if name in METHODS:
            if result['method_files'][name]!=pin:raise ValueError('Captured method differs from immutable Git source: '+name)
            common.verify_file(capture/'methods'/name,pin['bytes'],pin['sha256'])
        elif name==MANIFEST:
            common.verify_file(capture/'source-manifest.json',pin['bytes'],pin['sha256'])
            if result.get('manifest_sha256')!=pin['sha256']:raise ValueError('Result manifest pin differs')
        target=native/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);target.chmod(0o444);pins[name]=pin
    common.save(review/'producer-source-pins.json',dict(source_commit=SOURCE,files=pins,overlay=False))
    return native,pins


def unchanged_files(root,pins):
    if any(path.is_symlink() for path in root.rglob('*')):
        raise ValueError('Verifier introduced a symlink')
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    if actual!=set(pins):raise ValueError('Verifier changed file membership')
    for name,pin in pins.items():common.verify_file(root/name,pin['bytes'],pin['sha256'])


def replay(native,capture,review,inventory,source_pins):
    command=[sys.executable,'-B',str(native/'scripts/run_cloud_targeted_hold.py'),'validate',
        '--directory',str(capture),'--manifest',str(native/MANIFEST)]
    with (review/'producer-verifier.log').open('xb') as log:
        completed=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
            preexec_fn=common.verifier_limits,timeout=300,check=False)
    common.save(review/'producer-verifier.json',dict(command=command,returncode=completed.returncode,
        source_commit=SOURCE,address_space_limit_bytes=4*common.GIB,pure_verifier_timeout_seconds=300,
        native_tools_reexecuted=False,source_overlay=False))
    if completed.returncode:raise ValueError('Exact producer rejected the complete archive')
    unchanged_files(capture,inventory['files']);unchanged_files(native,source_pins)
    row=json.loads((capture/'result.json').read_text());diag=row['diagnostic'];native_result=diag['native']
    for value in (row,diag,native_result):
        if any(value.get(k) is not False for k in ('candidate_adopted','timing_accepted','manufacturing_approval')):
            raise ValueError('Diagnostic archive cannot accept timing or a candidate')
    if row.get('status')!='COMPLETE_DIAGNOSTIC_ONLY' or tuple(s['name'] for s in native_result['stages'])!=STAGES:
        raise ValueError('Missing complete four-stage diagnostic')
    if any(row['native_runs'][phase]['returncode']!=0 for phase in ('native-controls','native-diagnostic')):
        raise ValueError('Native producer completion is missing')
    summary=dict(status='VERIFIED_COMPLETE_TARGETED_DIAGNOSTIC_ONLY',source_commit=SOURCE,
        source_run=RUN,source_artifact=ARTIFACT,archive_bytes=SIZE,archive_sha256=DIGEST,
        member_count=inventory['member_count'],expanded_bytes=inventory['expanded_bytes'],
        complete_zip_crc_and_sha256_verified=True,exact_producer_verifier_passed=True,
        full_stage_physical_and_corner_path_replay=True,capture_and_source_unchanged_after_replay=True,
        native_tools_reexecuted=False,source_overlay=False,thresholds_changed=False,
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,resumable_checkpoint=False,
        native_runs=row['native_runs'],timing_metrics=native_result['timing_metrics'],
        aggregate_guard_assessment=diag['aggregate_guard_assessment'],
        buffer_budget=native_result['buffer_budget'],repair_invocation=native_result['repair_invocation'],
        independently_checked_stages=diag['independently_checked_stages'],
        full_endpoint_comparisons=diag['full_endpoint_comparisons'],
        scope='Exact completed native diagnostic and its full evidence were replayed by producer Python. Failed original C10 timing guards remain failed; no accepted timing/layout candidate or manufacturing approval.')
    common.save(review/'summary.json',summary)
    for name in ('result.json','capture.json'):shutil.copyfile(capture/name,review/('producer-'+name))
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    common.verify_file(Path(common.__file__),Path(common.__file__).stat().st_size,COMMON_SHA)
    common.verify_file(args.archive,SIZE,DIGEST)
    review=common.fresh(args.output)
    try:
        inventory=common.extract(args.archive,review/'capture',EXPANDED,MEMBERS)
        common.save(review/'zip-inventory.json',inventory)
        native,pins=pin_sources(review/'capture',review)
        summary=replay(native,review/'capture',review,inventory,pins)
        common.verify_file(args.archive,SIZE,DIGEST)
        # Only our fresh, fully verified extraction is removed; compact proof,
        # exact source, original input ZIP and failure evidence remain preserved.
        shutil.rmtree(review/'capture')
        common.save(review/'result.json',dict(status='PASS_FULL_ARCHIVE_REPLAY_DIAGNOSTIC_ONLY',
            summary_sha256=common.sha(review/'summary.json'),capture_removed_after_success=True,
            candidate_adopted=False,timing_accepted=False,manufacturing_approval=False))
        print(summary['status'])
        return 0
    except Exception as error:
        common.save(review/'result.json',dict(status='FAILED_FULL_ARCHIVE_REPLAY_PRESERVED',
            error_type=type(error).__name__,error=str(error),capture_removed_after_success=False,
            candidate_adopted=False,timing_accepted=False,manufacturing_approval=False))
        raise


if __name__=='__main__':
    raise SystemExit(main())
