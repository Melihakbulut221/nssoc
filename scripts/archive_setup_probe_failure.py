#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Archive one failed native probe unchanged; inspect only bounded failure evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile

import archive_hold_diagnostic as common

REPO, TAG = common.REPO, common.TAG
RUN = 36858091870
SOURCE = '0e76a3a4d9b3234b4958ab9f5da6c5ab55ee246a'
ARTIFACT = 11160082372
SIZE = 72242239
DIGEST = '429bee9737177359086e0f1aef4c1604ba37b3ce2d2cfcb5c98de091c6417deb'
NAME = 'timing-setup-probe-failure-20261001.zip'
COMMON_SHA = '04b89e92cee0bc60d68bc0f1d0d1f313231f622c56333547997108e65cea2c06'
MAX_SELECTED = 2*1024**2
SELECTED = ('result.json','native-diagnostic.log','worker.log','run/flow.log','run/error.log',
            'run/01-openroad-resizertimingpostgrt/openroad-resizertimingpostgrt.log')


def identity(run,artifact):
    expected = dict(id=RUN,head_sha=SOURCE,head_branch='codex/complete-open-work',
                    path='.github/workflows/timing-setup-probe.yml',event='push',
                    status='completed',conclusion='failure',run_attempt=1)
    if any(run.get(k) != v for k,v in expected.items()):
        raise ValueError('Unexpected failed producer identity')
    if any(run.get(k,{}).get('full_name') != REPO for k in ('repository','head_repository')):
        raise ValueError('Unexpected source repository')
    if any(artifact.get(k) != v for k,v in dict(id=ARTIFACT,name='setup-probe-final-1',
            expired=False,size_in_bytes=SIZE,digest='sha256:'+DIGEST).items()):
        raise ValueError('Unexpected original artifact identity')
    if any(artifact.get('workflow_run',{}).get(k) != v for k,v in dict(id=RUN,head_sha=SOURCE,head_branch='codex/complete-open-work').items()):
        raise ValueError('Artifact source differs')


def download(path):
    child = subprocess.Popen(['gh','api',f'repos/{REPO}/actions/artifacts/{ARTIFACT}/zip'],stdout=subprocess.PIPE)
    try:
        count,digest = 0,hashlib.sha256()
        with path.open('xb') as target:
            while chunk := child.stdout.read(1024**2):
                count += len(chunk)
                if count > SIZE: raise ValueError('Download exceeds exact byte budget')
                target.write(chunk);digest.update(chunk)
        if child.wait() or (count,digest.hexdigest()) != (SIZE,DIGEST):
            raise ValueError('Original ZIP byte verification failed')
    except BaseException:
        if child.poll() is None: child.kill()  # Our network reader, never native work.
        child.wait()
        raise
    finally:
        child.stdout.close()


def selected_failure(path,output):
    output = common.fresh(output)
    with zipfile.ZipFile(path) as z:
        members,expanded = common.inventory_zip(z)
        if any(name not in members or members[name].file_size > MAX_SELECTED for name in ('capture.json',*SELECTED)):
            raise ValueError('Missing or oversized selected failure evidence')
        def read(name):
            with z.open(members[name]) as source: data = source.read(MAX_SELECTED+1)
            if len(data) != members[name].file_size or len(data) > MAX_SELECTED:
                raise ValueError('Truncated or oversized selected member')
            return data
        capture_raw = read('capture.json');capture = json.loads(capture_raw)
        if (capture.get('observation',{}).get('status') != 'FAILED_PRESERVED'
                or capture.get('complete_diagnostic_evidence') is not False
                or capture.get('restart_checkpoint_accepted') is not False):
            raise ValueError('Expected explicitly incomplete failed capture')
        if set(members) != set(capture['files']) | {'capture.json'}:
            raise ValueError('ZIP membership differs from capture inventory')
        (output/'capture.json').write_bytes(capture_raw)
        pins = {}
        for name in SELECTED:
            data = read(name);pin = capture['files'][name]
            if (pin['bytes'] != len(data) or pin['sha256'] != hashlib.sha256(data).hexdigest()
                    or pin.get('source_truncated_during_copy') is not False
                    or pin.get('observed_source_bytes') != len(data)):
                raise ValueError('Selected failure bytes do not match capture pins')
            target = output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            pins[name] = dict(bytes=len(data),sha256=pin['sha256'])
        result = json.loads((output/'result.json').read_text())
        if result.get('status') != 'FAILED_PRESERVED' or result.get('github_source_commit') != SOURCE:
            raise ValueError('Wrong failed result source/state')
        for row in (result,capture):
            if any(row.get(key) is not False for key in ('candidate_adopted','timing_accepted','manufacturing_approval')):
                raise ValueError('Failure evidence cannot claim acceptance')
        log = (output/SELECTED[-1]).read_text()
        if not all(marker in log for marker in ("Assertion '!this->empty()' failed",'dbJournal','journalEnd()')):
            raise ValueError('Missing original native journal failure signature')
    return dict(zip_members=len(members),declared_expanded_bytes=expanded,selected_files=pins,
                full_native_output_validation=False,native_repair_succeeded=False)


def publish(path,review):
    common.verify_file(path,SIZE,DIGEST)
    release = common.api(f'releases/tags/{TAG}')
    matches = [a for a in release['assets'] if a['name'] == NAME]
    if len(matches) > 1: raise ValueError('Ambiguous release asset')
    if not matches:
        subprocess.run(['gh','release','upload',TAG,str(path),'--repo',REPO],check=True)
        release = common.api(f'releases/tags/{TAG}')
        matches = [a for a in release['assets'] if a['name'] == NAME]
    if len(matches) != 1: raise ValueError('Missing immutable release asset')
    asset = matches[0];url = f'https://github.com/{REPO}/releases/download/{TAG}/{NAME}'
    if (asset['size'],asset.get('digest'),asset['browser_download_url']) != (SIZE,'sha256:'+DIGEST,url):
        raise ValueError('Refusing conflicting release bytes')
    common.save(review/'release-asset.json',asset)
    actual = common.command_hash(['gh','api',f'repos/{REPO}/releases/assets/{asset["id"]}',
                                  '-H','Accept: application/octet-stream'],SIZE)
    if actual != (SIZE,DIGEST): raise ValueError('Authenticated roundtrip differs')
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'nssoc-evidence-verifier'}),timeout=120) as stream:
        if common.stream_hash(stream,SIZE) != (SIZE,DIGEST): raise ValueError('Anonymous roundtrip differs')
    common.verify_file(path,SIZE,DIGEST)
    return dict(name=NAME,asset_id=asset['id'],url=url,bytes=SIZE,sha256=DIGEST,original_zip_unchanged=True,
                github_api_digest_verified=True,authenticated_roundtrip_verified=True,anonymous_roundtrip_verified=True)


def run(output):
    output = common.fresh(output);review = output/'review';review.mkdir()
    record = dict(status='PREPARING',source_run=RUN,source_commit=SOURCE,source_artifact=ARTIFACT,
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,native_reexecuted=False,
        full_native_output_validation=False,method_sha256=common.sha(Path(__file__)),helper_sha256=common.sha(Path(common.__file__)))
    common.save(review/'result.json',record)
    try:
        if record['helper_sha256'] != COMMON_SHA: raise ValueError('Shared archival helper changed')
        if shutil.disk_usage(output).free <= SIZE+128*1024**2: raise ValueError('Insufficient cloud disk reserve')
        source = common.api(f'actions/runs/{RUN}');artifact = common.api(f'actions/artifacts/{ARTIFACT}')
        common.save(review/'producer-run.json',source);common.save(review/'producer-artifact.json',artifact)
        identity(source,artifact)
        path = output/NAME;download(path);common.verify_file(path,SIZE,DIGEST)
        record['failure_evidence'] = selected_failure(path,review/'selected')
        common.save(review/'result.json',record)
        root = Path(__file__).resolve().parents[1]
        for name in ('scripts/archive_setup_probe_failure.py','scripts/archive_hold_diagnostic.py',
                     '.github/workflows/timing-setup-probe-failure-archive.yml','LICENSES/Apache-2.0.txt'):
            target = review/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,target)
        record['assets'] = [publish(path,review)]
        record['review_files'] = {str(item.relative_to(review)): dict(bytes=item.stat().st_size,sha256=common.sha(item))
                                 for item in sorted(review.rglob('*')) if item.is_file() and item != review/'result.json'}
        record.update(status='PASS_ARCHIVED_FAILED_NATIVE_EVIDENCE',release_tag=TAG,
                      release_url=f'https://github.com/{REPO}/releases/tag/{TAG}',
                      scope='Original failed native ZIP bytes preserved. Only selected failure logs/result/capture independently checked; no complete diagnostic or successful repair claimed.')
        common.save(review/'result.json',record)
        print(json.dumps(record,indent=2));return 0
    except Exception as error:
        record.update(status='FAILED_PRESERVED',error=repr(error));common.save(review/'result.json',record)
        print(str(error));return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    return run(parser.parse_args().output)


if __name__ == '__main__':
    raise SystemExit(main())
