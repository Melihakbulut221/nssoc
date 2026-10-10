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
X = R / 'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004'
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


def archive(path, expected, members):
    path = Path(path)
    check(path, expected)
    seen = {}
    with tarfile.open(path, 'r:xz') as tar:
        for member in tar:
            assert member.isfile() and not member.issparse()
            assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            assert member.name not in seen and member.name in members
            with tar.extractfile(member) as stream:
                actual = dict(bytes=member.size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())
            assert actual == {key: members[member.name][key] for key in actual}, member.name
            seen[member.name] = actual
    assert set(seen) == set(members)
    archives.append(dict(path=str(path), **pin(path), members=len(seen), member_pins=seen))
    print(path.name, len(seen), flush=True)


package = load(P / 'pair02-package.json')
assert package['status'] == 'PASS_CLOSED_MATCHED_PHYSICAL_PAIR_ALL_ARCHIVE_MEMBERS'
assert package['candidate_adopted'] is False and package['timing_accepted'] is False
assert load(P / 'pair02-status.json')['status'] == 'FAILED_PRESERVED'
assert load(P / 'pair02-comparison-recovered01.json')['native_reexecuted'] is False
peer = load(P / 'comparison-recovery-peer-pll01.json')
assert peer['findings'] == []
check(P / 'comparison-recovery-peer-pll01.json', package['independent_recovery_peer'])
sources = {}
for name, value in load(P / 'source-freeze07.json')['sources'].items():
    check(name, value)
    sources[str(Path(name).relative_to(R))] = value
assert len(sources) == 6
archive(package['archive']['path'], package['archive'], package['members'])
allowed = {'.py', '.json', '.log', '.xml', '.tcl', '.ys', '.sdc', '.rpt', '.tsv'}
for name, value in package['members'].items():
    if name.startswith(('review/', 'native/')) and value['bytes'] < 700000 and Path(name).suffix in allowed:
        add(value['restore_path'], value)
for name in ['pair02-package.json', 'pair02-release01.json', 'pair02-publish01.log', 'pair02-seal01.log']:
    add(P / name)
release = load(P / 'pair02-release01.json')
assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
assets = list(release['assets'])

finite = X / 'repair16one-finite01/ready-finite.json'
d = load(finite)
assert not d['active_product_sources'] and not d['physical_acceptance']
assert d['router_drc'] == 0 and d['nominal_RC_only']
for name, value in d['compact_files'].items():
    add(value['copy'], value, R / name)
add(finite)
rx_package_name = str((X / 'repair16one-peer/package.json').relative_to(R))
rx_package = load(d['compact_files'][rx_package_name]['copy'])
assert rx_package['status'] == 'PASS_COMPLETE_IMMUTABLE_MEMBER_READBACK'
archive(d['archive']['path'], d['archive'], rx_package['members'])
assets += d['public_assets']
assert len(assets) == 5 and len({a['asset_id'] for a in assets}) == 5
for a in assets:
    assert a['authenticated_roundtrip'] and a['anonymous_roundtrip']
for a in archives:
    a['public_asset'] = next(v for v in assets if all(a[k] == v[k] for k in ('bytes', 'sha256')))
assert sum(a['members'] for a in archives) == 810
out = dict(status='PASS_CLOSED_NPU_PAIR_AND_ROUTED_RX_ALL_810_MEMBERS',
           utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
           sources=sources, compact=compact, archives=archives, public_assets=assets,
           members=810, full_phy_acceptance=False, full_chip_final_timing_accepted=False,
           production_acceptance=False,
           scope='Fresh matched chip global-route estimates and actual RX16one detailed-route nominal RC. Both setup targets remain open. The later running chip repair, RX17 and analog experiments are excluded.')
(B / 'closed-review01.json').write_text(json.dumps(out, indent=2) + '\n')
print(dict(sources=len(sources), compact=len(compact), members=810))
