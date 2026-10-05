# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Review closed RX14A preservation from saved bytes; no network/native rerun."""
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent

def pin(path):
    path = Path(path)
    with path.open('rb') as source:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(source, 'sha256').hexdigest())

def digest_stream(stream):
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
        size += len(chunk)
    return dict(bytes=size, sha256=digest.hexdigest())

def read(path):
    return json.loads(Path(path).read_text())

release = read(HERE / 'release.json')
assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
assert release['publisher_revision'] == 3 and not release['explicit_stop']
assert len(release['assets']) == len(release['files']) == 3
package_path = HERE / 'pcie-rx-repair14a-preroute-package-20261005.json'
validation_path = HERE / 'pcie-rx-repair14a-preroute-validation-20261005.json'
package = read(package_path)
assert package['status'] == 'PASS_IMMUTABLE_PREROUTE_FULL_MEMBER_READBACK'
archive = Path(package['archive']['path'])
assert pin(archive) == {key: package['archive'][key] for key in ('bytes', 'sha256')}
restore_paths = set()
with tarfile.open(archive, 'r:xz') as capture:
    assert set(capture.getnames()) == set(package['members'])
    assert len(capture.getmembers()) == len(package['members']) == package['member_count'] == 151
    for member in capture.getmembers():
        expected = package['members'][member.name]
        assert member.isfile() and member.size == expected['bytes']
        path = Path(expected['restore_path'])
        assert path.is_absolute() and '..' not in path.parts
        assert str(path) not in restore_paths
        restore_paths.add(str(path))
        actual_pin = {key: expected[key] for key in ('bytes', 'sha256')}
        with capture.extractfile(member) as stream:
            assert digest_stream(stream) == actual_pin
        assert pin(path) == actual_pin, path
assert not any('repair14a-drt-01' in path or 'repair14a-detailed-rc-01' in path for path in restore_paths)
for root in ('nssoc-rx-prefetch-v2-postroute-repair-14a',
             'nssoc-rx-prefetch-v2-postroute-repair-14b',
             'nssoc-rx-prefetch-v2-postroute-repair-14a-targeted-01',
             'nssoc-rx-prefetch-v2-postroute-repair-14b-targeted-01',
             'nssoc-rx-prefetch-v2-repair14a-equivalence',
             'nssoc-rx-prefetch-v2-repair14a-physical-replay-01'):
    assert any(path.startswith('/dev/shm/' + root + '/') for path in restore_paths)
for row, asset in zip(release['files'], release['assets']):
    path = Path(row['path'])
    assert path.name == row['name'] == asset['name']
    assert pin(path) == {key: row[key] for key in ('bytes', 'sha256')} == {key: asset[key] for key in ('bytes', 'sha256')}
    assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
    assert asset['url'].endswith('/' + asset['name'])
for field, path in [('source', 'scripts/publish_pcie_native_capture_v3.py'),
                    ('predecessor', 'scripts/publish_pcie_native_capture_v2.py'),
                    ('process_owner', 'scripts/characterize_pcie_clock_trim_stream_v2.py')]:
    assert pin(path) == release[field]
journal = release['transport_journal']
assert pin(journal['path']) == {key: journal[key] for key in ('bytes', 'sha256')}
attempts = read(journal['path'])
streams = 0
owners = []
for attempt in attempts:
    assert attempt['status'] == 'PASS' and attempt['returncode'] == 0
    assert not attempt['deadline_triggered'] and not attempt['stderr_limit_triggered']
    for kind in ('stderr', 'stdout'):
        observed = attempt[kind]
        assert pin(observed['path']) == {key: observed[key] for key in ('bytes', 'sha256')}
        assert attempt[kind + '_capture_complete']
        with gzip.open(observed['path'], 'rb') as stream:
            assert digest_stream(stream) == observed['uncompressed']
        streams += 1
    owner = read(attempt['owned_processes'])
    assert owner['cleanup'] is None
    for process in owner['processes']:
        assert process['status'] == 'REAPED_NO_LIVE_MEMBERS'
        assert process['returncode'] == 0 and not process['members_at_leader_exit']
    owners.append(dict(path=attempt['owned_processes'], **pin(attempt['owned_processes'])))
    if 'response' in attempt:
        response = attempt['response']
        assert pin(response['path']) == {key: response[key] for key in ('bytes', 'sha256')}
    if attempt['kind'] in ('authenticated', 'anonymous'):
        download = attempt['observed_download']
        assert download['mismatching_chunk'] is None
        assert any(download['bytes'] == asset['bytes'] and download['sha256'] == asset['sha256'] for asset in release['assets'])
validation = read(validation_path)
assert not validation['new_final_detailed_route_completed']
assert not validation['changed_design_nominal_RC_completed']
assert not validation['physical_acceptance'] and not validation['qualified_rc']
assert validation['completed_proof_ports']['canonical_states'] == 1804
assert validation['completed_proof_ports']['canonical_targets'] == 5443
assert validation['completed_proof_ports']['actual_mutation_controls'] == 10
assert len(validation['completed_proof_ports']['actual_port_cases']) == 6
result = dict(status='PASS_RX14A_CLOSED_PREROUTE_CAPTURE_AND_THREE_PUBLIC_ASSETS_SAVED_REVIEW',
              utc=datetime.datetime.now(datetime.UTC).isoformat(),
              method=pin(__file__), release=pin(HERE / 'release.json'),
              package=pin(package_path), validation=pin(validation_path),
              archive=dict(path=str(archive), **pin(archive)),
              archive_full_readback_members=len(package['members']),
              all_unique_absolute_restore_paths_rehashed=True,
              public_assets=release['assets'], transport_attempts=len(attempts),
              full_gzip_stream_readbacks=streams, transport_owner_pins=owners,
              new_final_detailed_route_completed=False,
              changed_design_nominal_RC_completed=False,
              physical_acceptance=False, qualified_rc=False,
              scope='Only closed four closed GRT candidates/reports plus selected14a, native gate expansion, exact reused gold, 1804-state/5443-function proof, 10 actual mutation controls and 6 native port cases. All151 archive members and original restore paths, 15 saved successful transport attempts/30 compressed streams, closed transport owners and immutable three public-asset pins rehashed. Active route outputs excluded. No EDA, proof, controls or network rerun; no final timing, full PHY or main-chip acceptance.')
with (HERE / 'publication-review.json').open('x') as output:
    json.dump(result, output, indent=2)
    output.write('\n')
print(json.dumps(dict(path=str(HERE / 'publication-review.json'), **pin(HERE / 'publication-review.json'))))
