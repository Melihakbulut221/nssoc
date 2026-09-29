#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Archive exact artifacts from a pinned successful producer; never replace assets."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request

from archive_chip_fill import REPO, TAG, api, stream_hash


def validate_plan(plan):
    required = {'source_run', 'source_commit', 'source_branch', 'source_workflow',
                'source_event', 'artifacts'}
    if set(plan) != required:
        raise ValueError('Unexpected archival plan fields')
    if type(plan['source_run']) is not int or plan['source_run'] <= 0:
        raise ValueError('Invalid source run')
    if not re.fullmatch(r'[0-9a-f]{40}', plan['source_commit']):
        raise ValueError('Invalid source commit')
    if (not re.fullmatch(r'codex/[a-zA-Z0-9_-]+', plan['source_branch'])
            or not re.fullmatch(r'\.github/workflows/[a-zA-Z0-9_-]+\.yml', plan['source_workflow'])
            or plan['source_event'] != 'push'):
        raise ValueError('Unexpected producer branch/workflow/event')
    rows = plan['artifacts']
    if not isinstance(rows, list) or not rows:
        raise ValueError('Missing artifact mapping')
    for row in rows:
        if (set(row) != {'artifact_name', 'asset_name'}
                or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]+', row['artifact_name'])
                or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]+\.zip', row['asset_name'])):
            raise ValueError('Unsafe artifact or asset name')
    for key in ['artifact_name', 'asset_name']:
        if len({row[key] for row in rows}) != len(rows):
            raise ValueError('Ambiguous artifact mapping')
    return plan


def producer_ready(source, plan):
    expected = {'id': plan['source_run'], 'head_sha': plan['source_commit'],
                'head_branch': plan['source_branch'], 'path': plan['source_workflow'],
                'event': plan['source_event']}
    if (any(source.get(k) != v for k, v in expected.items())
            or source.get('head_repository', {}).get('full_name') != REPO
            or source.get('repository', {}).get('full_name') != REPO):
        raise ValueError('Unexpected producer identity')
    if source['status'] != 'completed':
        return False
    if source['conclusion'] != 'success':
        raise ValueError('Producer completed without success')
    return True


def resolve_artifacts(listing, plan):
    if listing['total_count'] != len(listing['artifacts']):
        raise ValueError('Incomplete artifact listing')
    resolved = []
    for wanted in plan['artifacts']:
        matches = [x for x in listing['artifacts'] if x['name'] == wanted['artifact_name']]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous source artifact')
        row = matches[0]
        if (type(row['id']) is not int or row['id'] <= 0 or row['expired']
                or type(row['size_in_bytes']) is not int or row['size_in_bytes'] <= 0
                or not re.fullmatch(r'sha256:[0-9a-f]{64}', row.get('digest') or '')
                or row['workflow_run']['id'] != plan['source_run']
                or row['workflow_run']['head_sha'] != plan['source_commit']
                or row['workflow_run']['head_branch'] != plan['source_branch']):
            raise ValueError('Artifact identity, digest, size or lifetime mismatch')
        resolved.append(dict(source_artifact_id=row['id'], artifact_name=row['name'],
                             name=wanted['asset_name'], bytes=row['size_in_bytes'],
                             sha256=row['digest'].removeprefix('sha256:')))
    if len({x['source_artifact_id'] for x in resolved}) != len(resolved):
        raise ValueError('Artifact ID reused')
    return resolved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--wait', action='store_true')
    args = parser.parse_args()
    raw_plan = args.plan.read_bytes()
    plan = validate_plan(json.loads(raw_plan))
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    record = dict(status='PREPARING', plan=plan,
                  plan_sha256=hashlib.sha256(raw_plan).hexdigest(),
                  method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  helper_sha256=hashlib.sha256(Path(__file__).with_name('archive_chip_fill.py').read_bytes()).hexdigest(),
                  assets=[], physical_acceptance=False, manufacturing_approval=False)

    def save():
        tmp = out / 'result.json.tmp'
        tmp.write_text(json.dumps(record, indent=2) + '\n')
        tmp.replace(out / 'result.json')

    save()
    try:
        while True:
            source = api(f'actions/runs/{plan["source_run"]}')
            record['producer_status'] = source['status']
            record['producer_conclusion'] = source['conclusion']
            if producer_ready(source, plan):
                break
            record['status'] = 'WAITING_FOR_PINNED_PRODUCER'
            save()
            if not args.wait:
                raise ValueError('Producer is incomplete; use --wait to monitor it')
            time.sleep(60)
        if args.plan.read_bytes() != raw_plan:
            raise ValueError('Plan changed while waiting')
        listing = api(f'actions/runs/{plan["source_run"]}/artifacts?per_page=100')
        resolved = resolve_artifacts(listing, plan)
        record.update(status='ARCHIVING', resolved_artifacts=resolved)
        save()
        for row in resolved:
            artifact_id, name = row['source_artifact_id'], row['name']
            metadata = api(f'actions/artifacts/{artifact_id}')
            one = dict(plan, artifacts=[dict(artifact_name=row['artifact_name'], asset_name=name)])
            if resolve_artifacts(dict(total_count=1, artifacts=[metadata]), one) != [row]:
                raise ValueError('Artifact changed after resolution')
            path = out / name
            with path.open('xb') as stream:
                subprocess.run(['gh', 'api', f'repos/{REPO}/actions/artifacts/{artifact_id}/zip'],
                               stdout=stream, check=True)
            expected = (row['bytes'], row['sha256'])
            with path.open('rb') as stream:
                actual = stream_hash(stream)
            record['current_download'] = dict(name=name, bytes=actual[0], sha256=actual[1])
            save()
            if actual != expected:
                raise ValueError('Artifact bytes mismatch')
            release = api(f'releases/tags/{TAG}')
            if not any(x['name'] == name for x in release['assets']):
                subprocess.run(['gh', 'release', 'upload', TAG, str(path), '--repo', REPO], check=True)
            matches = [x for x in api(f'releases/tags/{TAG}')['assets'] if x['name'] == name]
            if len(matches) != 1:
                raise ValueError('Ambiguous release asset')
            asset = matches[0]
            if (asset['size'], asset['digest']) != (row['bytes'], 'sha256:' + row['sha256']):
                raise ValueError('Refusing different existing release bytes')
            with subprocess.Popen(['gh', 'api', f'repos/{REPO}/releases/assets/{asset["id"]}',
                                   '-H', 'Accept: application/octet-stream'], stdout=subprocess.PIPE) as child:
                actual = stream_hash(child.stdout)
                if child.wait() or actual != expected:
                    raise ValueError('Authenticated release roundtrip mismatch')
            request = urllib.request.Request(asset['browser_download_url'],
                                             headers={'User-Agent': 'nssoc-evidence-verifier'})
            with urllib.request.urlopen(request, timeout=120) as stream:
                if stream_hash(stream) != expected:
                    raise ValueError('Anonymous release roundtrip mismatch')
            record['assets'].append(dict(row, asset_id=asset['id'], url=asset['browser_download_url'],
                source_commit=plan['source_commit'], source_run=plan['source_run'],
                local_roundtrip_verified=True, authenticated_roundtrip_verified=True,
                anonymous_roundtrip_verified=True, scope='Exact raw artifact bytes only.'))
            record['release_url'] = release['html_url']
            save()
            path.unlink()
            print('Published and verified', name, flush=True)
        record['status'] = 'PASS_PUBLISHED_BYTES_ONLY'
        save()
    except Exception as error:
        record.update(status='ERROR', error=repr(error))
        save()
        raise


if __name__ == '__main__':
    main()
