#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Retain the exact completed fill artifacts without local disk duplication."""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

REPO = 'Melihakbulut221/nssoc'
TAG = 'evidence-20260927-chip-io'
SOURCE = 'bf2b7d1fdb976523736b7afa01d4d7754a6adb5f'
ARTIFACTS = (
    (10993697843, 'chip-irq-fill-candidate-20260928.zip', 41621861,
     '651d671531c7d698d498421649d01de650a22abdc8ee2ed0c770f2a7d167b41b'),
    (10993857831, 'chip-irq-fill-tiles-20260928.zip', 1505717713,
     'd98ea45eb47667db068b12f70f377b66fad613541ce50f179280677337cecd38'),
)


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{REPO}/{path}']))


def stream_hash(stream):
    h = hashlib.sha256()
    count = 0
    while data := stream.read(1024 * 1024):
        h.update(data)
        count += len(data)
    return count, h.hexdigest()


def main():
    out = Path('hw/soc/out/cloud-fill-archive')
    out.mkdir(parents=True, exist_ok=False)
    record = dict(status='RUNNING', source_run=36474119630, source_commit=SOURCE,
                  method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  assets=[], physical_acceptance=False, manufacturing_approval=False)

    def save():
        (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')

    save()
    try:
        source = api('actions/runs/36474119630')
        if source['head_sha'] != SOURCE or source['conclusion'] != 'success':
            raise ValueError('Unexpected fill producer or incomplete execution')
        for artifact_id, name, size, sha in ARTIFACTS:
            metadata = api(f'actions/artifacts/{artifact_id}')
            if (metadata['workflow_run']['id'] != 36474119630 or metadata['expired']
                    or metadata['digest'] != 'sha256:' + sha or metadata['size_in_bytes'] != size):
                raise ValueError('Artifact identity mismatch')
            path = out / name
            with path.open('xb') as stream:
                subprocess.run(['gh', 'api', f'repos/{REPO}/actions/artifacts/{artifact_id}/zip'],
                               stdout=stream, check=True)
            with path.open('rb') as stream:
                if stream_hash(stream) != (size, sha):
                    raise ValueError('Artifact download bytes mismatch')
            release = api(f'releases/tags/{TAG}')
            if not any(a['name'] == name for a in release['assets']):
                subprocess.run(['gh', 'release', 'upload', TAG, str(path), '--repo', REPO], check=True)
            release = api(f'releases/tags/{TAG}')
            asset = next(a for a in release['assets'] if a['name'] == name)
            if asset['size'] != size or asset['digest'] != 'sha256:' + sha:
                raise ValueError('Refusing different existing release bytes')
            with subprocess.Popen(['gh', 'api', f'repos/{REPO}/releases/assets/{asset["id"]}',
                                   '-H', 'Accept: application/octet-stream'], stdout=subprocess.PIPE) as child:
                actual = stream_hash(child.stdout)
                if child.wait() or actual != (size, sha):
                    raise ValueError('Authenticated release roundtrip mismatch')
            request = urllib.request.Request(asset['browser_download_url'],
                                             headers={'User-Agent': 'nssoc-evidence-verifier'})
            with urllib.request.urlopen(request, timeout=120) as stream:
                if stream_hash(stream) != (size, sha):
                    raise ValueError('Anonymous release roundtrip mismatch')
            record['assets'].append(dict(name=name, bytes=size, sha256=sha,
                source_artifact_id=artifact_id, asset_id=asset['id'], url=asset['browser_download_url'],
                source_commit=SOURCE, local_roundtrip_verified=True,
                authenticated_roundtrip_verified=True, anonymous_roundtrip_verified=True,
                scope='Exact raw fill artifact; generation and geometry evidence only.'))
            record['release_url'] = release['html_url']
            save()
            print('Published and verified', name, flush=True)
        record['status'] = 'PASS_PUBLISHED_BYTES_ONLY'
        save()
    except Exception as error:
        record.update(status='ERROR', error=repr(error))
        save()
        raise


if __name__ == '__main__':
    main()
