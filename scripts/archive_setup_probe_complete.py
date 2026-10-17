#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Archive completed native work from a workflow with a JSON comparison failure.

Only a pinned JSON-list representation fix is overlaid onto the producer's
Python verifier. Original capture, measurements and native sources stay intact.
No OpenROAD/AppImage invocation or timing acceptance occurs in this workflow.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

import archive_hold_diagnostic as common

REPO, TAG = common.REPO, common.TAG
SOURCE = 'df3dd93fca89487dac46e6506c005713dd294430'
FIX_SOURCE = 'bebfbe704748d8ab347db9a4db86b53670a6624c'
RUN = 36901798029
ARTIFACT = 11183060623
SIZE = 269855333
DIGEST = '0fdb41dedd3fbd36c63919d34e20b2eff0e5b7f71c4f60a56a83de16a8cdfa50'
NAME = 'timing-setup-probe-complete-20261001.zip'
MEMBERS, EXPANDED = 125, 517394979
COMMON_SHA = '04b89e92cee0bc60d68bc0f1d0d1f313231f622c56333547997108e65cea2c06'
COMPARATOR = 'scripts/compare_full_hold_endpoints.py'
OLD_SHA = '5e539b320b44187d032f70b9535328e9e618a21f1376de8a2869d9c1fe92fefd'
FIX_SHA = 'b51ca5a52d53b166623935bbfebe1275c24d1e43f967ec4bf3fbb829fa1144cb'
OLD_LINE = b'                changes.append(dict(corner=corner, endpoint=endpoint, before_seconds=left, after_seconds=right))\n'
NEW_LINES = (b'                # Receipts are persisted as JSON and independently reconstructed.\n'
             b'                # Emit JSON-native arrays so a changed pair roundtrips exactly.\n'
             b'                changes.append(dict(corner=corner, endpoint=endpoint,\n'
             b'                                    before_seconds=list(left), after_seconds=list(right)))\n')
METHODS = (*common.METHODS, '.github/workflows/timing-setup-probe.yml',
           'scripts/run_cloud_setup_probe.py', COMPARATOR, 'hw/soc/pnr/timing_setup_hold_probe_step.tcl')
STAGES = ('matched_before','after_repair_native','after_setup','after_full_update')
MANIFEST = common.MANIFEST
LICENSES = common.LICENSES


def pin(data):
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def identity(run, artifact):
    expected = dict(id=RUN,head_sha=SOURCE,head_branch='codex/complete-open-work',
        path='.github/workflows/timing-setup-probe.yml',event='workflow_dispatch',
        status='completed',conclusion='failure',run_attempt=1)
    if any(run.get(k) != v for k,v in expected.items()):
        raise ValueError('Unexpected producer: failed workflow with completed native output is required')
    if any(run.get(k,{}).get('full_name') != REPO for k in ('repository','head_repository')):
        raise ValueError('Unexpected producer repository')
    if any(artifact.get(k) != v for k,v in dict(id=ARTIFACT,name='setup-probe-final-1',
        expired=False,size_in_bytes=SIZE,digest='sha256:'+DIGEST).items()):
        raise ValueError('Wrong original artifact identity')
    if any(artifact.get('workflow_run',{}).get(k) != v for k,v in dict(id=RUN,head_sha=SOURCE,head_branch='codex/complete-open-work').items()):
        raise ValueError('Wrong original artifact lineage')


def download(path):
    child = subprocess.Popen(['gh','api',f'repos/{REPO}/actions/artifacts/{ARTIFACT}/zip'],stdout=subprocess.PIPE)
    try:
        count,digest = 0,hashlib.sha256()
        with path.open('xb') as sink:
            while chunk := child.stdout.read(1024**2):
                count += len(chunk)
                if count > SIZE: raise ValueError('Original archive exceeds pinned byte limit')
                sink.write(chunk);digest.update(chunk)
        if child.wait() or (count,digest.hexdigest()) != (SIZE,DIGEST):
            raise ValueError('Original archive digest differs')
    except BaseException:
        if child.poll() is None: child.kill()  # Only our network child; there is no native worker.
        child.wait();raise
    finally:
        child.stdout.close()


def git_blob(repo,commit,name):
    return subprocess.check_output(['git','-C',str(repo),'show',f'{commit}:{name}'])


def exact_overlay(original, corrected):
    if pin(original)['sha256'] != OLD_SHA or pin(corrected)['sha256'] != FIX_SHA:
        raise ValueError('Comparator bytes differ from the reviewed source pins')
    if original.count(OLD_LINE) != 1 or original.replace(OLD_LINE,NEW_LINES) != corrected:
        raise ValueError('Overlay is not solely the exact tuple-to-JSON-list representation fix')
    return ''.join(difflib.unified_diff(original.decode().splitlines(True),corrected.decode().splitlines(True),
        fromfile=SOURCE+'/'+COMPARATOR,tofile=FIX_SOURCE+'/'+COMPARATOR))


def prepare_verifiers(repo,capture,review):
    original = common.fresh(review/'producer-source')
    pins = {}
    for name in (*METHODS,MANIFEST,*LICENSES):
        data = git_blob(repo,SOURCE,name);pins[name] = pin(data)
        target=original/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);target.chmod(0o444)
        if name in METHODS: common.verify_file(capture/'methods'/name,**dict(size=len(data),digest=pins[name]['sha256']))
    result = json.loads((capture/'result.json').read_text())
    if result.get('github_source_commit') != SOURCE or result.get('method_files') != {name:pins[name] for name in METHODS}:
        raise ValueError('Captured methods differ from exact producer Git blobs')
    common.verify_file(capture/'source-manifest.json',pins[MANIFEST]['bytes'],pins[MANIFEST]['sha256'])
    fixed = git_blob(repo,FIX_SOURCE,COMPARATOR)
    diff = exact_overlay((original/COMPARATOR).read_bytes(),fixed)
    overlay = review/'verifier-overlay'
    shutil.copytree(original,overlay)
    target = overlay/COMPARATOR;target.chmod(0o644);target.write_bytes(fixed);target.chmod(0o444)
    overlay_pins = {}
    for name,p in pins.items():
        expected = pin(fixed) if name == COMPARATOR else p
        common.verify_file(overlay/name,expected['bytes'],expected['sha256']);overlay_pins[name]=expected
    (review/'comparator-exact.diff').write_text(diff)
    receipt = dict(producer_commit=SOURCE,corrected_comparator_commit=FIX_SOURCE,
        sole_overlaid_path=COMPARATOR,original_sha256=OLD_SHA,corrected_sha256=FIX_SHA,
        original_sources=pins,overlay_sources=overlay_pins,
        raw_capture_modified=False,measurements_modified=False,thresholds_modified=False,
        native_tools_reexecuted=False,scope='Only tuple-to-JSON-list construction is changed; comparison values and guards are unchanged.')
    common.save(review/'verifier-overlay.json',receipt)
    return original,overlay,receipt


def invoke_verifier(source,capture,review,label):
    command=[sys.executable,'-B',str(source/'scripts/run_cloud_setup_probe.py'),'validate',
        '--directory',str(capture),'--manifest',str(source/MANIFEST)]
    with (review/(label+'.log')).open('xb') as stream:
        completed=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
            preexec_fn=common.verifier_limits,check=False)
    receipt=dict(command=command,returncode=completed.returncode,address_space_limit_bytes=4*common.GIB,
        native_tools_reexecuted=False,verifier_source_commit=SOURCE,
        comparator_source_commit=FIX_SOURCE if label == 'corrected-verifier' else SOURCE)
    common.save(review/(label+'.json'),receipt)
    return completed.returncode


def verify_complete(original,overlay,capture,review,inventory):
    # Reproduce the persisted JSON reconstruction failure without rerunning native tools.
    if invoke_verifier(original,capture,review,'original-verifier') == 0:
        raise ValueError('Original serialization defect was not reproduced')
    oldlog=(review/'original-verifier.log').read_text()
    if 'ValueError: Independent diagnostic reconstruction differs' not in oldlog:
        raise ValueError('Original verifier failed for an unrelated reason')
    if invoke_verifier(overlay,capture,review,'corrected-verifier') != 0:
        raise ValueError('Corrected verifier rejected full captured evidence')
    # No expected/result mutation is permitted in either verifier phase.
    for name,p in inventory['files'].items(): common.verify_file(capture/name,p['bytes'],p['sha256'])
    if {str(p.relative_to(capture)) for p in capture.rglob('*') if p.is_file()} != set(inventory['files']):
        raise ValueError('Verifier changed original capture membership')
    row=json.loads((capture/'result.json').read_text())
    if row.get('status') != 'COMPLETE_DIAGNOSTIC_ONLY' or any(row.get(k) is not False for k in ('candidate_adopted','timing_accepted','manufacturing_approval')):
        raise ValueError('Not a complete diagnostic-only native result')
    if any(row['native_runs'][name]['returncode'] != 0 for name in ('native-controls','native-diagnostic')):
        raise ValueError('Native completion missing')
    native=row['diagnostic']['native']
    if tuple(stage['name'] for stage in native['stages']) != STAGES:
        raise ValueError('Four full native stages are required')
    summary=dict(status='VERIFIED_COMPLETE_NATIVE_DIAGNOSTIC_FROM_FAILED_WORKFLOW',
        source_run=RUN,source_commit=SOURCE,workflow_conclusion='failure',native_returncode=0,
        original_verifier_reconstruction_failed=True,corrected_overlay_verifier_passed=True,
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,
        measurements_modified=False,thresholds_changed=False,native_tools_reexecuted=False,
        selected_source_metrics=row['selected_source_metrics'],sdc_sha256=row['sdc_sha256'],
        native_runs=row['native_runs'],stage_measurements=native['stages'],
        timing_metrics=native['timing_metrics'],repair_invocation=native['repair_invocation'],
        buffer_budget=native['buffer_budget'],full_endpoint_comparisons=row['diagnostic']['full_endpoint_comparisons'],
        independently_checked_stages=row['diagnostic']['independently_checked_stages'],
        scope='Full original artifact and four-stage diagnostic closure verified after a JSON representation-only verifier fix; no timing candidate adoption or manufacturing approval.')
    common.save(review/'summary.json',summary)
    for name in ('result.json','capture.json'):
        shutil.copyfile(capture/name,review/('producer-'+name))
    return summary


def publish(archive,review):
    common.verify_file(archive,SIZE,DIGEST)
    release=common.api(f'releases/tags/{TAG}')
    matches=[a for a in release['assets'] if a['name']==NAME]
    reused=bool(matches)
    if len(matches)>1:raise ValueError('Ambiguous release asset')
    if not matches:
        subprocess.run(['gh','release','upload',TAG,str(archive),'--repo',REPO],check=True)
        release=common.api(f'releases/tags/{TAG}');matches=[a for a in release['assets'] if a['name']==NAME]
    if len(matches)!=1:raise ValueError('Missing immutable release asset')
    asset=matches[0];url=f'https://github.com/{REPO}/releases/download/{TAG}/{NAME}'
    if (asset['size'],asset.get('digest'),asset['browser_download_url']) != (SIZE,'sha256:'+DIGEST,url):
        raise ValueError('Refusing conflicting release bytes')
    common.save(review/'release-asset.json',asset)
    actual=common.command_hash(['gh','api',f'repos/{REPO}/releases/assets/{asset["id"]}',
        '-H','Accept: application/octet-stream'],SIZE)
    if actual != (SIZE,DIGEST):raise ValueError('Authenticated roundtrip differs')
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'nssoc-evidence-verifier'}),timeout=120) as stream:
        if common.stream_hash(stream,SIZE) != (SIZE,DIGEST):raise ValueError('Anonymous roundtrip differs')
    common.verify_file(archive,SIZE,DIGEST)
    return dict(name=NAME,asset_id=asset['id'],url=url,bytes=SIZE,sha256=DIGEST,
        original_zip_unchanged=True,reused_existing_matching_asset=reused,github_api_digest_verified=True,
        authenticated_roundtrip_verified=True,anonymous_roundtrip_verified=True)


def run(output,repo,publish_requested):
    output=common.fresh(output);review=output/'review';review.mkdir()
    record=dict(status='PREPARING',source_run=RUN,source_commit=SOURCE,source_artifact=ARTIFACT,
        producer_workflow_conclusion='failure',archive_source_commit=os.environ.get('GITHUB_SHA'),
        archive_method_sha256=common.sha(Path(__file__)),shared_helper_sha256=common.sha(Path(common.__file__)),
        comparator_fix_commit=FIX_SOURCE,candidate_adopted=False,timing_accepted=False,
        manufacturing_approval=False,measurements_modified=False,thresholds_changed=False,
        native_tools_reexecuted=False,publication_requested=publish_requested)
    common.save(review/'result.json',record)
    try:
        if record['shared_helper_sha256'] != COMMON_SHA:raise ValueError('Shared archival helper changed')
        if shutil.disk_usage(output).free < SIZE+EXPANDED+common.DISK_RESERVE:raise ValueError('Insufficient cloud disk reserve')
        source=common.api(f'actions/runs/{RUN}');artifact=common.api(f'actions/artifacts/{ARTIFACT}')
        common.save(review/'producer-run.json',source);common.save(review/'producer-artifact.json',artifact)
        identity(source,artifact)
        archive=output/NAME;download(archive);common.verify_file(archive,SIZE,DIGEST)
        record['status']='VERIFYING_CAPTURE';common.save(review/'result.json',record)
        capture=output/'capture';inventory=common.extract(archive,capture,EXPANDED,MEMBERS)
        common.save(review/'member-inventory.json',inventory)
        original,overlay,overlay_receipt=prepare_verifiers(repo,capture,review)
        for name in ('scripts/archive_setup_probe_complete.py','scripts/archive_hold_diagnostic.py',
            '.github/workflows/timing-setup-probe-complete-archive.yml','sw/tests/test_archive_setup_probe_complete.py',*LICENSES):
            target=review/'archive-source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/name,target)
        verify_complete(original,overlay,capture,review,inventory)
        for base,key in ((original,'original_sources'),(overlay,'overlay_sources')):
            for name,p in overlay_receipt[key].items():
                common.verify_file(base/name,p['bytes'],p['sha256'])
        common.verify_file(archive,SIZE,DIGEST)
        record.update(status='PASS_COMPLETE_DIAGNOSTIC_OVERLAY_VERIFIED',member_count=MEMBERS,
            expanded_bytes=EXPANDED,archive_bytes=SIZE,archive_sha256=DIGEST,
            native_returncode=0,original_sources_verified=True,overlay=overlay_receipt)
        if publish_requested:
            record['asset']=publish(archive,review);record['status']='PASS_PUBLISHED_COMPLETE_NATIVE_DIAGNOSTIC'
        record['review_files']={str(p.relative_to(review)):dict(bytes=p.stat().st_size,sha256=common.sha(p))
            for p in sorted(review.rglob('*')) if p.is_file() and p != review/'result.json'}
        common.save(review/'result.json',record);print(json.dumps(record,indent=2));return 0
    except Exception as error:
        record.update(status='FAILED_PRESERVED',error=repr(error));common.save(review/'result.json',record)
        print(str(error),file=sys.stderr);return 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args();return run(args.output,args.repo.resolve(),args.publish)


if __name__=='__main__':
    raise SystemExit(main())
