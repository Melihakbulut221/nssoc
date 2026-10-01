#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify and publish one completed hold-diagnostic artifact, without native work.

The raw GitHub ZIP is immutable. A fresh cloud directory has a bounded safe
extraction and invokes the verifier from the producer's exact Git commit.
Publication cannot accept timing, adopt a checkpoint or replace another asset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import resource
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile

REPO = 'Melihakbulut221/nssoc'
TAG = 'evidence-20260927-chip-io'
RUN_ID = 36813322010
ARTIFACT_ID = 11140519443
SOURCE = 'ad4d8bb3a1294693f80e0e633d2312104f9899e3'
ARTIFACT_NAME = 'hold-diagnostic-final-1'
ASSET_NAME = 'timing-hold-diagnostic-complete-20261001.zip'
ARCHIVE_BYTES = 478807891
ARCHIVE_SHA256 = '70781280d44cafabf634bd6907551deb184aaeca174136ba91829124207d2a3d'
GIB = 1024**3
EXPECTED_MEMBERS = 144
EXPECTED_EXPANDED_BYTES = 945676244
MAX_MEMBERS = 5000
MAX_EXPANDED_BYTES = EXPECTED_EXPANDED_BYTES
MAX_MEMBER_BYTES = 512*1024**2
DISK_RESERVE = 2*GIB
METHODS = ('.github/workflows/timing-hold-diagnostic.yml',
           'scripts/run_cloud_hold_diagnostic.py', 'scripts/run_cloud_timing_experiment.py',
           'hw/soc/pnr/timing_hold_reproducibility.tcl', 'hw/soc/pnr/timing_hold_diagnostic_step.tcl',
           'sw/tests/hold_reproducibility_native.py', 'sw/tests/timing_hold_reproducibility_native.tcl')
MANIFEST = 'docs/evidence/timing-cloud-input-20260930.json'
LICENSES = ('LICENSES/Apache-2.0.txt', 'LICENSES/CERN-OHL-W-2.0.txt')
STAGES = ('reload_no_parasitics','grt_rebuilt_before_dpl','matched_before','same_state_repeat',
          'arrivals_recomputed','full_timing_recomputed','parasitics_reestimated','incremental_no_repair')


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def save(path, row):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(row, indent=2)+'\n')
    temporary.replace(path)


def fresh(path):
    path = Path(os.path.abspath(path))
    if any(parent.is_symlink() for parent in (path,*path.parents)):
        raise ValueError('Symlink output ancestor rejected')
    path.mkdir(parents=True, exist_ok=False)
    return path


def api(endpoint):
    return json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/{endpoint}']))


def stream_hash(source, maximum):
    digest, count = hashlib.sha256(), 0
    while chunk := source.read(1024**2):
        count += len(chunk)
        if count > maximum:
            raise ValueError('Stream exceeds exact pinned size')
        digest.update(chunk)
    return count, digest.hexdigest()


def download_archive(path):
    command = ['gh','api',f'repos/{REPO}/actions/artifacts/{ARTIFACT_ID}/zip']
    child = subprocess.Popen(command,stdout=subprocess.PIPE)
    count,digest = 0,hashlib.sha256()
    try:
        with path.open('xb') as target:
            while chunk := child.stdout.read(1024**2):
                count += len(chunk)
                if count > ARCHIVE_BYTES:
                    raise ValueError('Original ZIP download exceeds pinned byte budget')
                digest.update(chunk)
                target.write(chunk)
        if child.wait() or (count,digest.hexdigest()) != (ARCHIVE_BYTES,ARCHIVE_SHA256):
            raise ValueError('Original ZIP download does not match the pinned bytes')
    except BaseException:
        # This is our bounded network reader, never a native physical worker.
        if child.poll() is None:
            child.kill()
        child.wait()
        raise
    finally:
        child.stdout.close()


def command_hash(command,maximum):
    child = subprocess.Popen(command,stdout=subprocess.PIPE)
    try:
        value = stream_hash(child.stdout,maximum)
        if child.wait():
            raise ValueError('Authenticated byte stream command failed')
        return value
    except BaseException:
        if child.poll() is None:
            child.kill()
        child.wait()
        raise
    finally:
        child.stdout.close()


def verify_file(path, size, digest):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size or sha(path) != digest:
        raise ValueError('Missing or changed pinned file: '+str(path))


def verify_producer(run, artifact):
    expected = dict(id=RUN_ID, head_sha=SOURCE, head_branch='codex/complete-open-work',
                    path='.github/workflows/timing-hold-diagnostic.yml', event='workflow_dispatch',
                    status='completed', conclusion='success', run_attempt=1)
    if any(run.get(key) != value for key,value in expected.items()):
        raise ValueError('Unexpected or incomplete native producer')
    if any(run.get(key,{}).get('full_name') != REPO for key in ('repository','head_repository')):
        raise ValueError('Unexpected native producer repository')
    expected_artifact = dict(id=ARTIFACT_ID, name=ARTIFACT_NAME, size_in_bytes=ARCHIVE_BYTES,
                             digest='sha256:'+ARCHIVE_SHA256, expired=False)
    if any(artifact.get(key) != value for key,value in expected_artifact.items()):
        raise ValueError('Unexpected original artifact identity or bytes')
    workflow = artifact.get('workflow_run',{})
    if any(workflow.get(key) != value for key,value in dict(id=RUN_ID,head_sha=SOURCE,head_branch='codex/complete-open-work').items()):
        raise ValueError('Artifact is not from the pinned native run')


def inventory_zip(archive):
    infos = archive.infolist()
    if not infos or len(infos) > MAX_MEMBERS:
        raise ValueError('Empty or excessive ZIP member inventory')
    result, expanded = {}, 0
    for item in infos:
        name = item.filename
        relative = PurePosixPath(name)
        mode = item.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if (not name or '\x00' in name or item.orig_filename != name or '\\' in name
                or relative.is_absolute() or '..' in relative.parts or str(relative) != name
                or name == '.' or ':' in relative.parts[0] or item.is_dir()
                or kind not in (0,stat.S_IFREG) or item.flag_bits & 1
                or item.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
                or name in result):
            raise ValueError('Unsafe, duplicate or unsupported ZIP member: '+name)
        if item.file_size < 0 or item.file_size > MAX_MEMBER_BYTES:
            raise ValueError('ZIP member exceeds expansion budget')
        expanded += item.file_size
        if expanded > MAX_EXPANDED_BYTES:
            raise ValueError('ZIP total exceeds expansion budget')
        result[name] = item
    for name in result:
        if any(str(parent) in result for parent in PurePosixPath(name).parents if str(parent) != '.'):
            raise ValueError('ZIP file/directory prefix collision')
    return result, expanded


def extract(archive_path, output, expected_expanded=None, expected_members=None):
    with zipfile.ZipFile(archive_path) as archive:
        members, expanded = inventory_zip(archive)
        if ((expected_expanded is not None and expanded != expected_expanded)
                or (expected_members is not None and len(members) != expected_members)):
            raise ValueError('ZIP does not match the pinned completed member census')
        free_bytes = shutil.disk_usage(output.parent).free
        if free_bytes < expanded+DISK_RESERVE:
            raise ValueError(f'Insufficient extraction disk: free={free_bytes}, required={expanded+DISK_RESERVE}')
        output = fresh(output)
        inventory = {}
        for name,item in members.items():
            destination = output/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest, count = hashlib.sha256(), 0
            with archive.open(item) as source, destination.open('xb') as target:
                while chunk := source.read(1024**2):
                    count += len(chunk)
                    if count > item.file_size:
                        raise ValueError('ZIP member expands beyond declared size')
                    digest.update(chunk)
                    target.write(chunk)
            if count != item.file_size:
                raise ValueError('Incomplete ZIP member')
            inventory[name] = dict(bytes=count,sha256=digest.hexdigest(),crc32=item.CRC)
            destination.chmod(0o444)
    return dict(member_count=len(inventory),expanded_bytes=expanded,
                free_disk_before_bytes=free_bytes,files=inventory)


def git_blob(repo, name):
    return subprocess.check_output(['git','-C',str(repo),'show',f'{SOURCE}:{name}'])


def pin_native_methods(repo, extracted, output):
    """Resolve source by full commit ID, never execute unverified archive code."""
    native = output/'native-source'
    native.mkdir(exist_ok=False)
    pins = {}
    for name in (*METHODS,MANIFEST,*LICENSES):
        data = git_blob(repo,name)
        target = native/name
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
        target.chmod(0o444)
        pins[name] = dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        if name in METHODS:
            verify_file(extracted/'methods'/name,len(data),pins[name]['sha256'])
    result = json.loads((extracted/'result.json').read_text())
    if result.get('github_source_commit') != SOURCE or result.get('method_files') != {name:pins[name] for name in METHODS}:
        raise ValueError('Captured source identity is not the producer Git tree')
    verify_file(extracted/'source-manifest.json',pins[MANIFEST]['bytes'],pins[MANIFEST]['sha256'])
    return native,pins


def verifier_limits():
    resource.setrlimit(resource.RLIMIT_AS,(4*GIB,4*GIB))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def verify_capture(native, extracted, review):
    command = [sys.executable,'-B',str(native/'scripts/run_cloud_hold_diagnostic.py'),'validate',
               '--directory',str(extracted),'--manifest',str(native/MANIFEST)]
    with (review/'verifier.log').open('xb') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, preexec_fn=verifier_limits, check=False)
    save(review/'verifier.json',dict(command=command,returncode=result.returncode,
              source_commit=SOURCE,native_tools_reexecuted=False,address_space_limit_bytes=4*GIB))
    if result.returncode:
        raise ValueError('Pinned producer verifier rejected the complete artifact')
    row = json.loads((extracted/'result.json').read_text())
    if row.get('status') != 'COMPLETE_DIAGNOSTIC_ONLY' or any(row.get(key) is not False for key in ('candidate_adopted','timing_accepted','manufacturing_approval')):
        raise ValueError('Unexpected diagnostic completion or acceptance claim')
    stages = row['diagnostic']['native']['stages']
    if tuple(stage['name'] for stage in stages) != STAGES:
        raise ValueError('Missing completed native stage')
    summary = dict(status='VERIFIED_COMPLETE_DIAGNOSTIC_ONLY',source_commit=SOURCE,source_run=RUN_ID,
        source_artifact_id=ARTIFACT_ID,archive_sha256=ARCHIVE_SHA256,
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,thresholds_changed=False,
        selected_source_metrics=row['selected_source_metrics'],sdc_sha256=row['sdc_sha256'],
        native_runs=row['native_runs'],stage_measurements=stages,
        independently_checked_stages=row['diagnostic']['independently_checked_stages'],
        scope='Native diagnostic evidence only; no optimizer trial, candidate acceptance or signoff.')
    save(review/'summary.json',summary)
    for source,name in [(extracted/'result.json','producer-result.json'),(extracted/'capture.json','producer-capture.json')]:
        shutil.copyfile(source,review/name)
    return summary


def publish(archive,review):
    # Existing equal bytes may be verified after an interrupted prior publication;
    # different bytes fail closed. Never pass --clobber or delete an asset.
    verify_file(archive,ARCHIVE_BYTES,ARCHIVE_SHA256)
    release = api(f'releases/tags/{TAG}')
    matches = [item for item in release['assets'] if item['name'] == ASSET_NAME]
    reused = bool(matches)
    if len(matches) > 1:
        raise ValueError('Ambiguous release asset')
    if not matches:
        subprocess.run(['gh','release','upload',TAG,str(archive),'--repo',REPO],check=True)
        release = api(f'releases/tags/{TAG}')
        matches = [item for item in release['assets'] if item['name'] == ASSET_NAME]
    if len(matches) != 1:
        raise ValueError('Missing unique immutable release asset')
    asset = matches[0]
    if asset['size'] != ARCHIVE_BYTES or asset.get('digest') != 'sha256:'+ARCHIVE_SHA256:
        raise ValueError('Refusing different release bytes')
    expected_url = f'https://github.com/{REPO}/releases/download/{TAG}/{ASSET_NAME}'
    if asset['browser_download_url'] != expected_url:
        raise ValueError('Unexpected release destination')
    save(review/'release-asset.json',asset)
    actual = command_hash(['gh','api',f'repos/{REPO}/releases/assets/{asset["id"]}',
                           '-H','Accept: application/octet-stream'],ARCHIVE_BYTES)
    if actual != (ARCHIVE_BYTES,ARCHIVE_SHA256):
        raise ValueError('Authenticated release byte roundtrip differs')
    request = urllib.request.Request(expected_url,headers={'User-Agent':'nssoc-evidence-verifier'})
    with urllib.request.urlopen(request,timeout=120) as stream:
        if stream_hash(stream,ARCHIVE_BYTES) != (ARCHIVE_BYTES,ARCHIVE_SHA256):
            raise ValueError('Anonymous release byte roundtrip differs')
    verify_file(archive,ARCHIVE_BYTES,ARCHIVE_SHA256)
    return dict(name=ASSET_NAME,asset_id=asset['id'],url=expected_url,bytes=ARCHIVE_BYTES,
                sha256=ARCHIVE_SHA256,original_zip_unchanged=True,reused_existing_matching_asset=reused,
                github_api_digest_verified=True,authenticated_roundtrip_verified=True,
                anonymous_roundtrip_verified=True,release_url=release['html_url'])


def run(output,repo,publish_requested):
    output = fresh(output)
    review = output/'review'
    review.mkdir()
    record = dict(status='PREPARING',source_commit=SOURCE,source_run=RUN_ID,source_artifact=ARTIFACT_ID,
                  candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,
                  native_tools_reexecuted=False,publication_requested=publish_requested,
                  archive_method_sha256=sha(Path(__file__)),archive_source_commit=os.environ.get('GITHUB_SHA'))
    save(review/'result.json',record)
    try:
        free_bytes = shutil.disk_usage(output).free
        if free_bytes < ARCHIVE_BYTES+DISK_RESERVE:
            raise ValueError('Insufficient cloud disk even before download')
        source = api(f'actions/runs/{RUN_ID}')
        artifact = api(f'actions/artifacts/{ARTIFACT_ID}')
        save(review/'producer-run.json',source)
        save(review/'producer-artifact.json',artifact)
        verify_producer(source,artifact)
        archive = output/ASSET_NAME
        download_archive(archive)
        verify_file(archive,ARCHIVE_BYTES,ARCHIVE_SHA256)
        record['status'] = 'VERIFYING_CAPTURE'
        save(review/'result.json',record)
        extracted = output/'capture'
        inventory = extract(archive,extracted,EXPECTED_EXPANDED_BYTES,EXPECTED_MEMBERS)
        save(review/'member-inventory.json',inventory)
        native,pins = pin_native_methods(repo,extracted,review)
        save(review/'native-source-pins.json',dict(commit=SOURCE,files=pins))
        # Preserve the new independent publication code and its licensing.
        for name in ('scripts/archive_hold_diagnostic.py','.github/workflows/timing-hold-diagnostic-archive.yml',
                     'sw/tests/test_archive_hold_diagnostic.py',*LICENSES):
            target = review/'archive-source'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(Path(repo)/name,target)
        verify_capture(native,extracted,review)
        verify_file(archive,ARCHIVE_BYTES,ARCHIVE_SHA256)
        record.update(status='PASS_VERIFIED_DIAGNOSTIC_ONLY',member_count=inventory['member_count'],
                      expanded_bytes=inventory['expanded_bytes'],archive_bytes=ARCHIVE_BYTES,
                      archive_sha256=ARCHIVE_SHA256,native_source_pins=pins)
        save(review/'result.json',record)
        if publish_requested:
            record['asset'] = publish(archive,review)
            record['status'] = 'PASS_PUBLISHED_BYTES_AND_DIAGNOSTIC_VERIFIED'
        # Bind every compact evidence file except the self-referential final receipt.
        record['review_files'] = {str(path.relative_to(review)):dict(bytes=path.stat().st_size,sha256=sha(path))
                                 for path in sorted(review.rglob('*')) if path.is_file() and path.name not in {'result.json','result.json.tmp'}}
        save(review/'result.json',record)
        print(json.dumps(record,indent=2))
        return 0
    except Exception as error:
        record.update(status='FAILED_PRESERVED',error=repr(error))
        save(review/'result.json',record)
        print(str(error),file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--publish',action='store_true')
    args = parser.parse_args()
    return run(args.output,args.repo.resolve(),args.publish)


if __name__ == '__main__':
    raise SystemExit(main())
