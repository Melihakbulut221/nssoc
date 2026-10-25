# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify finite physical captures without including running experiments."""
from pathlib import Path
import datetime
import hashlib
import json
import tarfile

R = Path.cwd()
B = Path(__file__).absolute().parent
P = R / 'hw/soc/out/npu-eco-physical-runner-20261006'
X = R / 'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005'
load = lambda p: json.loads(Path(p).read_text())


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def check(path, expected):
    assert pin(path) == {key: expected[key] for key in ('bytes', 'sha256')}, str(path)


compact = {}
archives = []


def add(path, expected=None, original=None):
    path = Path(path)
    expected = expected or pin(path)
    check(path, expected)
    name = str(Path(original or path).relative_to(R))
    value = dict(copy=str(path), **{key: expected[key] for key in ('bytes', 'sha256')})
    assert name not in compact or compact[name] == value
    compact[name] = value


def archive(path, expected, members=None):
    path = Path(path)
    check(path, expected)
    seen = {}
    with tarfile.open(path, 'r:xz') as tar:
        for member in tar:
            assert member.isfile() and not member.issparse()
            assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            assert member.name not in seen
            with tar.extractfile(member) as stream:
                actual = dict(bytes=member.size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())
            if members and member.name in members:
                assert actual == {key: members[member.name][key] for key in actual}, member.name
            seen[member.name] = actual
    assert not members or set(members) <= set(seen)
    archives.append(dict(path=str(path), **pin(path), members=len(seen), member_pins=seen))
    print(path.name, len(seen), flush=True)


sources = {}
assets = []
A = R / 'hw/soc/out/pcie-bias8-layout-wire-loaded-finite-20261006'
d = load(A / 'ready-finite01.json')
assert d['future_second_stage_reference_experiment_excluded']
for name, h in d['sources'].items():
    check(name, h)
    sources[str(Path(name).relative_to(R))] = h
for name, h in d['compact_evidence'].items():
    add(name, h)
for name, h in d['public_receipts'].items():
    add(name, h)
for name in ['ready-finite01.json', 'finite-snapshot01.json', 'seal_finite01.py', 'release-additive01.json']:
    add(A / name)
analog_archives = {}
for row in [*d['archives'], d['additive_archive']]:
    key = (row['bytes'], row['sha256'])
    if key in analog_archives:
        assert row['path'] == analog_archives[key]['path'] and row['members'] == analog_archives[key]['members']
    else:
        analog_archives[key] = row
for row in analog_archives.values():
    manifest = Path(row['manifest'])
    if 'manifest_pin' in row:
        check(manifest, row['manifest_pin'])
    m = load(manifest)
    archive(row['path'], row, m.get('members', m))
    add(manifest)
assets += d['assets']

V = R / 'hw/soc/out/pcie-integrity-v23-20261006'
d = load(V / 'ready-finite.json')
assert not d['adopted'] and not d['physical_acceptance']
assert not d['native']['all_three_setup_nonnegative']
for name, h in d['source_allowlist'].items():
    check(R / name, h)
    sources[name] = h
for name, h in d['evidence'].items():
    add(R / name, h)
add(V / 'ready-finite.json')
for name, h in d['releases'].items():
    receipt = V / name
    check(receipt, h)
    release = load(receipt)
    assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
    for row in release['files']:
        path = Path(row['path'])
        check(path, row)
        if path.name.endswith('.tar.xz'):
            expected = load(V / 'native-members.json') if name == 'native-release01.json' else None
            archive(path, row, expected)
    assets += release['assets']

M = R / 'hw/soc/out/pcie-integrity-v18-20261005/max4118-01'
d = load(M / 'ready-finite.json')
assert not d['source_allowlist'] and d['functional']['direct']['passed'] == d['functional']['miter']['passed'] == 13
assert d['functional']['direct']['original_parent_waitcode'] is None
assert d['functional']['miter']['owned_waitcode'] == 0
for name, h in d['evidence'].items():
    add(R / name, h)
add(M / 'ready-finite.json')
manifest = d['archive_member_manifest']
check(manifest['path'], manifest)
archive(d['archive']['path'], d['archive'], load(manifest['path'])['members'])
assets += d['assets']

terminal = load(X / 'repair05-continuation01/result.json')
assert terminal['status'] == 'COMPLETE_TX05_FINITE_ROUTE_RC_REVIEW_PUBLICATION'
review = load(X / 'repair05-peer/review.json')
assert not review['physical_acceptance'] and not review['qualified_rc']
assert review['canonical_binary_kernel_replay']['mismatches'] == []
assert review['canonical_binary_kernel_replay']['matched'] == 11680
for name, h in review['inputs_rehashed'].items():
    check(name, h)
package = load(X / 'repair05-peer/package.json')
archive(package['archive']['path'], package['archive'], package['members'])
for directory in ['repair05-source', 'repair05-continuation01', 'repair05-peer']:
    for p in (X / directory).rglob('*'):
        if p.is_file() and p.stat().st_size < 700000 and p.suffix in ('.json', '.py', '.log', '.xml', '.tcl', '.txt') and '__pycache__' not in p.parts:
            add(p)
release = load(X / 'repair05-peer/release.json')
assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
assets += release['assets']

assert len(sources) == 36 and len(archives) == 10
assert sum(a['members'] for a in archives) == 2543
assert len(assets) == len({a['asset_id'] for a in assets}) == 19
for asset in assets:
    assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
for a in archives:
    a['public_asset'] = next(v for v in assets if all(a[k] == v[k] for k in ('bytes', 'sha256')))
out = dict(status='PASS_CLOSED_PCIE_FUNCTIONAL_AND_PHYSICAL_CAPTURES_2543_MEMBERS',
           utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           sources=sources, compact=compact, archives=archives, public_assets=assets,
           members=2543, full_phy_acceptance=False, full_chip_final_timing_accepted=False,
           production_acceptance=False,
           scope='Closed V9 geometry/RC and full34ns function failure; V23 accepted-header candidate with retained controls and setup failure; completed V18 MAX4118 direct13/miter13; TX05 actual detailed-route nominalRC setup improvement. Later analog and RTL candidates, RX17, PLL acquisition and main chip repair are excluded.')
(B / 'closed-review02.json').write_text(json.dumps(out, indent=2) + '\n')
print(dict(sources=len(sources), compact=len(compact), members=2543, public_assets=len(assets)))

