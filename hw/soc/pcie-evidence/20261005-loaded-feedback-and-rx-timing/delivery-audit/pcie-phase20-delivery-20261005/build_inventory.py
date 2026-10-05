# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Verify complete finite capsules and copy exact evidence; no native reruns."""
from pathlib import Path
import hashlib
import json
import subprocess
import tarfile

R = Path.cwd()
O = Path(__file__).resolve().parent
C = R / 'hw/soc/pcie-evidence/20261005-loaded-feedback-and-rx-timing'
C.mkdir(parents=True, exist_ok=True)
sources, receipts, assets, components, capsules = {}, {}, {}, {}, []


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


def read(p):
    return json.loads(Path(p).read_text())


def copy(c, p, expected=None):
    p = Path(p)
    if not p.is_absolute():
        p = R / p
    actual = pin(p)
    if expected:
        assert actual == {k: expected[k] for k in actual}, p
    target = C / c / p.parent.name / p.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert pin(target) == actual, target
    else:
        target.write_bytes(p.read_bytes())
    key = str(target.relative_to(R))
    receipts[key] = {'original': str(p.relative_to(R)), **actual}
    components.setdefault(c, {'receipts': [], 'sources': []})['receipts'].append(key)
    data = read(p) if p.suffix == '.json' else None
    if isinstance(data, dict):
        for asset in data.get('assets', []):
            if asset.get('authenticated_roundtrip') is True and asset.get('anonymous_roundtrip') is True:
                url = asset['url']
                if url in assets:
                    assert assets[url]['sha256'] == asset['sha256']
                assets[url] = {**asset, 'receipt': key, 'overall_attempt_status': data['status']}
    return data


def add_sources(c, mapping):
    if isinstance(mapping, list):
        mapping = {row['repository_path']: row for row in mapping}
    for name, expected in mapping.items():
        p = Path(name)
        if not p.is_absolute():
            p = R / p
        actual = pin(p)
        assert actual == {k: expected[k] for k in actual}, p
        key = str(p.relative_to(R))
        if key in sources:
            assert sources[key] == actual
        sources[key] = actual
        components[c]['sources'].append(key)


def releases(c, b):
    for p in sorted(b.glob('*release*.json')):
        d = copy(c, p)
        # Preserve failed and interrupted attempts. Only individually verified
        # assets enter the public inventory; a partial run is never upgraded.
        for asset in d.get('assets', []):
            if not (asset.get('authenticated_roundtrip') is True and asset.get('anonymous_roundtrip') is True):
                continue
            key = asset['url']
            if key in assets:
                assert assets[key]['sha256'] == asset['sha256']
            assets[key] = {**asset, 'receipt': str((C/c/p.parent.name/p.name).relative_to(R)), 'overall_attempt_status': d['status']}


def capsule(c, archive, manifest_path, manifest, embedded_manifest=False):
    archive = Path(archive)
    expected = {name: {k: row[k] for k in ('bytes', 'sha256')} for name, row in manifest.items()}
    if embedded_manifest:
        expected['members.json'] = pin(manifest_path)
    published = [a for a in assets.values() if a['name'] == archive.name]
    assert len(published) == 1, (archive.name, len(published))
    apin = pin(archive)
    assert apin == {k: published[0][k] for k in apin}
    actual = {}
    with tarfile.open(archive, 'r|xz') as t:
        for member in t:
            assert member.isfile() and member.name not in actual
            actual[member.name] = {'bytes': member.size, 'sha256': hashlib.file_digest(t.extractfile(member), 'sha256').hexdigest()}
    assert actual == expected, (archive.name, set(actual) ^ set(expected))
    capsules.append({'component': c, 'archive': {'path': str(archive), **apin}, 'manifest': {'path': str(manifest_path), **pin(manifest_path)}, 'members': len(actual), 'public_url': published[0]['url']})


for version in (12, 13, 14):
    c = f'integrity-v{version}'
    b = R / f'hw/soc/out/pcie-integrity-v{version}-20261005'
    ready = copy(c, b/'ready-finite.json')
    add_sources(c, ready['source_allowlist'])
    for row in (ready['evidence'].values() if isinstance(ready['evidence'], dict) else ready['evidence']):
        copy(c, row['path'], row)
    for name in ['controls-members.json', 'native-members.json', 'timing-comparison.json', 'critical-path-attribution.json']:
        copy(c, b/name)
    if version == 14:
        for name in ['result.json', 'selected_z.v', 'run.log']:
            path = b/'peer-selected-z-01'/name
            if path.is_file():
                copy(c, path)
    releases(c, b)
    for kind in ('controls', 'native'):
        manifest_path = b/f'{kind}-members.json'
        manifest = read(manifest_path)
        part = 'default-controls' if kind == 'controls' else 'native-preplacement'
        name = f'pcie-integrity-v{version}-{part}-20261005.tar.xz'
        candidates = [Path('/dev/shm')/name, b/name]
        archive = next(p for p in candidates if p.exists())
        capsule(c, archive, manifest_path, manifest, embedded_manifest=True)
    components[c]['scope'] = ready.get('limitations', ready.get('scope'))


for c, dirname, cases, peers in [
    ('loaded-vco', 'pcie-vco-v6-feedback-v1-20261005', ['06-01', '085-01', 'disconnect-02', 'modulus-02'], ['endpoint-peer', 'observer-repair', 'fault-peer']),
    ('bias-vco', 'pcie-vco-v6-feedback-bias-v1-20261005', ['085-01', '06-01', 'disconnect-01'], ['bias-peer']),
]:
    b = R/'hw/soc/out'/dirname
    ready = copy(c, b/'finite-ready.json')
    add_sources(c, ready['source_pins'])
    for pattern in ['*source-freeze*.json', '*source-only-peer*.json', '*members*.json', '*validation*.json', 'root-wave-peer*.json', 'root_wave_peer.py', 'paired-comparison.json']:
        for path in sorted(b.glob(pattern)):
            copy(c, path)
    releases(c, b)
    for case in cases:
        val = read(b/f'validation-{case}.json')
        capsule(c, val['archive']['path'], b/f'members-{case}.json', read(b/f'members-{case}.json'))
    for peer in peers:
        val = read(b/f'{peer}-validation.json')
        manifest_path = b/f'{peer}-members.json'
        capsule(c, val['archive']['path'], manifest_path, read(manifest_path))
    components[c]['scope'] = ready.get('limitations')

c = 'rx11'
b = R/'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair11-peer02'
for name in ['review.py', 'review.json', 'source-bridge.json', 'source-freeze.json', 'root-source-only-peer.json', 'package.json', 'pcie-rx-repair11-finite-physical-validation-20261005.json']:
    copy(c, b/name)
releases(c, b)
package = read(b/'package.json')
capsule(c, package['archive']['path'], b/'package.json', package['members'])
components[c]['scope'] = 'Actual RX11 detailed routing0routerDRC, same netlist, nominal SS setup-.610481ns/hold+.030615ns. Saved-output peer path error corrected without native reruns. No qualifiedRC/finaltiming/fullchip acceptance.'

for name in ['ci-cocotb-runtime-validation.json', 'ci-missing-cocotb-reproduction.log']:
    copy('ci-preparation', O/name)
copy('ci-preparation', R/'hw/soc/out/resume-after-abrupt-20261005-1454/github-snapshot.json')
audit = {'status': 'PASS_ALL_DECLARED_CAPSULE_MEMBERS_REHASHED', 'method': pin(__file__), 'capsule_count': len(capsules), 'member_count': sum(x['members'] for x in capsules), 'capsules': capsules, 'scope': 'All complete local capsule bytes independently rehashed against retained authenticated and anonymous public receipts. No new native execution or product approval.'}
(O/'archive-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
copy('delivery-audit', O/'archive-audit.json')
copy('delivery-audit', Path(__file__))
assert len(sources) == 41, len(sources)
for item in components.values():
    item['sources'] = sorted(set(item['sources']))
    item['receipts'] = sorted(set(item['receipts']))
inventory = {'status': 'VERIFIED_FINITE_PHASE20_DELIVERY_NOT_PRODUCT_ACCEPTANCE', 'date': '2026-10-05', 'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), 'sources': dict(sorted(sources.items())), 'components': components, 'copied_receipts': dict(sorted(receipts.items())), 'published_assets': list(assets.values()), 'counts': {'new_frozen_sources': len(sources), 'copied_receipts': len(receipts), 'public_assets': len(assets), 'capsules': len(capsules), 'members_rehashed': audit['member_count']}, 'excluded': ['New TX02DRT03/RX12DRT and publicationV3/PLL restart work remain separate active work, not completed design evidence.', 'Full PCIeGen3x4/SERDES/CDR/LTSSM/controller policy, final timing/qualifiedRC/PVT/ESD, mainchip/DFT and production approval remain open.']}
(C/'delivery-inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
(O/'ready-source-allowlist.txt').write_text('\n'.join(sorted(sources))+'\n')
(O/'inventory-result.json').write_text(json.dumps({'inventory': str((C/'delivery-inventory.json').relative_to(R)), **pin(C/'delivery-inventory.json'), **inventory['counts']}, indent=2)+'\n')
print(inventory['counts'])
