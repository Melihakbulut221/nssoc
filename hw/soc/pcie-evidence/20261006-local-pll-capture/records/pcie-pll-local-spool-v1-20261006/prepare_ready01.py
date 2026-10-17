"""Finalize finite delivery only after all three public dual byte readbacks."""
from pathlib import Path
import hashlib
import json

R = Path.cwd()
B = R / 'hw/soc/out/pcie-pll-local-spool-v1-20261006'
D = B / 'finite01'


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


package_path = D / 'pcie-pll-local-spool-v1-finite-package-20261006.json'
package = json.loads(package_path.read_text())
release_path = D / 'publication-release01.json'
release = json.loads(release_path.read_text())
launch = json.loads((D / 'publication-detached.json').read_text())
process = Path('/proc') / str(launch['pid'])
if process.exists():
    fields = (process / 'stat').read_text().rsplit(') ', 1)[1].split()
    assert fields[19] != str(launch['start_ticks']) or fields[0] == 'Z', 'Publisher still live'
assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
assert release['publisher_revision'] == 4
assert release['tag'] == 'evidence-20261006-pcie-closure'
expected = {Path(package[key]['path']).name: package[key]
            for key in ('archive', 'validation')}
expected[package_path.name] = dict(path=str(package_path), **pin(package_path))
assert len(release['assets']) == len(expected) == 3
assert {asset['name'] for asset in release['assets']} == set(expected)
for asset in release['assets']:
    entry = expected[asset['name']]
    assert asset['authenticated_roundtrip'] is True and asset['anonymous_roundtrip'] is True
    assert {key: asset[key] for key in ('bytes', 'sha256')} == pin(entry['path'])
for path, value in package['source_allowlist'].items():
    assert pin(R / path) == value
evidence = dict(package['evidence'])
for path, value in evidence.items():
    assert pin(R / path) == value
for path in [package_path, release_path, D / 'publication-detached.json',
             D / 'publication-once.json', D / 'publication-controller.log',
             B / 'dispatch_publication01.py', Path(__file__)]:
    evidence[str(path.relative_to(R))] = pin(path)
result = dict(
    status='READY_FINITE_LOCAL_PLL_SPOOL_69_CONTROLS_NATIVE_STILL_ACTIVE',
    source_allowlist=package['source_allowlist'],
    controls=dict(current_predicates=69, groups=package['current_predicate_groups'],
                  historical_executions=package['historical_executions'],
                  historical_failed_executions=package['historical_failed_executions']),
    source_freeze=package['source_freeze'],
    archives=dict(controls_and_launch=dict(**package['archive'], member_count=package['member_count'])),
    archive_total_members=package['member_count'],
    full_logical_data_bytes=package['logical_data_bytes'],
    finite_package=dict(path=str(package_path), **pin(package_path)),
    saved_delivery_peer=package['saved_finite_peer'],
    source_peer=package['aggregate_peer'], support_peer=package['launch_support_peer'],
    releases={str(release_path.relative_to(R)): pin(release_path)}, assets=release['assets'],
    evidence=evidence, evidence_original_relative_paths=True,
    active_native_checkpoint=str(B / 'launch01/active-checkpoint.json'),
    native_completion=False, numerical_convergence=False, physical_acceptance=False,
    scope=package['limitations'])
target = B / 'ready-finite.json'
with target.open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(path=str(target), **pin(target), sources=len(result['source_allowlist']),
                      records=len(evidence), archives=1, members=result['archive_total_members'],
                      assets=len(result['assets']))))
