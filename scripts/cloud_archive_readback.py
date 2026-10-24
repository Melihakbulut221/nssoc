#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run bulk archive readback on GitHub, returning a source-bound small receipt."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import urllib.request

from migrate_outputs_to_cloud import REPO, atomic


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path], text=True))


def remote_bytes(asset):
    data = urllib.request.urlopen(asset['browser_download_url'], timeout=120).read()
    if len(data) != asset['size'] or 'sha256:' + hashlib.sha256(data).hexdigest() != asset['digest']:
        raise ValueError('Remote receipt digest differs')
    return data


def check_result(result, manifest):
    if (result.get('status') != 'PASS_EVERY_REMOTE_ARCHIVE_MEMBER'
            or result.get('manifest_sha256') != manifest['sha256']
            or result.get('manifest_url') != manifest['url']):
        raise ValueError('Hosted proof is not bound to this exact manifest')


def wait_verified_readback(manifest, tag, statefile):
    request = 'readback-' + manifest['sha256']
    state = json.loads(statefile.read_text()) if statefile.exists() else {}
    if state.get('manifest_sha256', manifest['sha256']) != manifest['sha256']:
        raise ValueError('Readback request changed')
    if not state.get('run'):
        def find():
            rows = json.loads(subprocess.check_output(['gh', 'run', 'list', '-R', REPO,
                '--workflow', 'cloud-migration-checks.yml', '--limit', '100',
                '--json', 'databaseId,displayTitle'], text=True))
            found = [r['databaseId'] for r in rows if r['displayTitle'] == 'cloud-migration-checks ' + request]
            if len(found) > 1:
                raise RuntimeError('Ambiguous readback run')
            return found[0] if found else None
        run = find()
        if not run and not state.get('dispatch_attempted'):
            state.update(dispatch_attempted=True, manifest_sha256=manifest['sha256'])
            atomic(statefile, state)
            subprocess.run(['gh', 'workflow', 'run', 'cloud-migration-checks.yml', '-R', REPO,
                '--ref', 'codex/complete-open-work', '-f', 'request_id=' + request,
                '-f', 'verification_tag=' + tag, '-f', 'verification_manifest=' + manifest['name']], check=True)
        for _ in range(12):
            run = run or find()
            if run:
                break
            time.sleep(10)
        if not run:
            raise RuntimeError('Readback dispatch uncertain; inspect request before retry')
        state['run'] = run
        atomic(statefile, state)
    run = state['run']
    while True:
        result = api(f'repos/{REPO}/actions/runs/{run}')
        if result['status'] == 'completed':
            if result['conclusion'] != 'success':
                raise RuntimeError('Hosted readback failed: ' + str(run))
            break
        time.sleep(15)
    release = api(f'repos/{REPO}/releases/tags/cloud-results-{run}-1-archive-readback')
    asset = next(a for a in release['assets'] if a['name'] == 'archive-readback.json')
    proof = json.loads(remote_bytes(asset))
    check_result(proof, manifest)
    state.update(proof=proof, proof_url=asset['browser_download_url'], status='PASS')
    atomic(statefile, state)
    return state


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Bulk readback requires a GitHub-hosted workflow')
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    parser.add_argument('--manifest', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'cloud-migration-[a-z0-9-]+', args.tag) or not re.fullmatch(r'[a-z0-9.-]+\.manifest\.json', args.manifest):
        raise ValueError('Unexpected archive identity')
    release = api(f'repos/{REPO}/releases/tags/{args.tag}')
    assets = {a['name']: a for a in release['assets']}
    source = assets[args.manifest]
    raw = remote_bytes(source)
    manifest = json.loads(raw)
    receipt = manifest['receipt']
    archive_asset = assets[receipt['name']]
    if (archive_asset['browser_download_url'] != receipt['url']
            or archive_asset['size'] != receipt['bytes']
            or archive_asset['digest'] != 'sha256:' + receipt['sha256']):
        raise ValueError('Manifest archive does not match immutable release asset')
    from migrate_cloud_transients import verify_archive
    from publish_cloud_results import publish_results
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / 'archive.tar.gz'
        subprocess.run(['curl', '--fail', '--location', '--retry', '4', '--silent', '--show-error', receipt['url'], '-o', str(target)], check=True)
        with target.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if target.stat().st_size != receipt['bytes'] or digest != receipt['sha256']:
            raise ValueError('Hosted downloaded archive differs')
        verify_archive(target, manifest['entries'])
    proof = dict(status='PASS_EVERY_REMOTE_ARCHIVE_MEMBER', manifest_url=source['browser_download_url'],
        manifest_sha256=hashlib.sha256(raw).hexdigest(), archive_sha256=receipt['sha256'],
        archive_url=receipt['url'], entries=len(manifest['entries']),
        logical_bytes=sum(r.get('bytes', 0) for r in manifest['entries']),
        source_head=os.environ['GITHUB_SHA'], run_id=os.environ['GITHUB_RUN_ID'])
    result = Path('archive-readback.json')
    atomic(result, proof)
    publish_results('archive-readback', [result])


if __name__ == '__main__':
    main()
