# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read selected closed public capsules, without rerunning any DUT or tool."""
import gzip
import hashlib
import io
import json
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

R = Path.cwd()
O = Path(__file__).resolve().parent


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


def read(p):
    return json.loads(Path(p).read_text())


specs = []
for component, base, manifest, release in [
    ('recovered-events', 'pcie-recovered-events-20261005', 'package.json', 'release.json'),
    ('vco-v5-peer', 'pcie-vco-v5-local-v1-wire-20261005', 'peer-validation.json', 'release-peer.json'),
    ('vco-v5-phase', 'pcie-vco-v5-local-v1-wire-20261005', 'diagnosis-validation.json', 'release-diagnosis.json'),
    ('tx01', 'pcie-gen3-transmit-v4-repair-20261005/repair01-peer', 'package.json', 'release.json'),
]:
    b = R / 'hw/soc/out' / base
    d = read(b / manifest)
    specs.append((component, Path(d['archive']['path']), b / manifest, d['members'], b / release))
for v, kind in [(9, 'native'), (10, 'native'), (10, 'controls')]:
    b = R / f'hw/soc/out/pcie-integrity-v{v}-20261005'
    rel = b / f'{kind}-release.json'
    a = next(Path(x['path']) for x in read(rel)['files'] if x['path'].endswith('.tar.xz'))
    m = b / f'{kind}-members.json'
    manifest = read(m)
    # The archive explicitly adds the separately saved member manifest itself.
    expected = {**manifest, 'members.json': pin(m)}
    specs.append((f'integrity-v{v}-{kind}', a, m, expected, rel))

records = []
for component, archive, manifest_path, expected, release_path in specs:
    release = read(release_path)
    assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
    asset = next(a for a in release['assets'] if a['name'] == archive.name)
    assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
    assert pin(archive) == {k: asset[k] for k in ('bytes', 'sha256')}
    expected = {name: {k: value[k] for k in ('bytes', 'sha256')} for name, value in expected.items()}
    actual, xmls, gzip_readbacks = {}, [], []
    raw_by_compressed = {}
    if component == 'recovered-events':
        val = read(manifest_path.parent / 'validation.json')
        for row in val['complete_compiled_program_readbacks']:
            assert row['full_readback'] is True
            raw_by_compressed[row['gzip']['sha256']] = row['raw']
    with tarfile.open(archive, 'r|xz') as tar:
        for member in tar:
            assert member.isfile() and member.name not in actual
            stream = tar.extractfile(member)
            if member.name.endswith('results.xml'):
                data = stream.read()
                digest = hashlib.sha256(data).hexdigest()
                cases = list(ET.fromstring(data).iter('testcase'))
                xmls.append({'name': member.name, 'cases': len(cases), 'failures': sum(c.find('failure') is not None or c.find('error') is not None for c in cases), 'skipped': sum(c.find('skipped') is not None for c in cases)})
            elif component == 'recovered-events' and member.name.endswith('.vvp.gz'):
                assert member.size < 16 * 1024**2
                data = stream.read()
                digest = hashlib.sha256(data).hexdigest()
                assert digest in raw_by_compressed
                h, size = hashlib.sha256(), 0
                with gzip.GzipFile(fileobj=io.BytesIO(data)) as f:
                    while chunk := f.read(1024**2):
                        h.update(chunk)
                        size += len(chunk)
                raw = {'bytes': size, 'sha256': h.hexdigest()}
                assert raw == raw_by_compressed[digest]
                gzip_readbacks.append({'name': member.name, 'raw': raw})
            else:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            actual[member.name] = {'bytes': member.size, 'sha256': digest}
    assert actual == expected, (component, set(actual) ^ set(expected))
    if component == 'recovered-events':
        assert len(gzip_readbacks) == len(raw_by_compressed)
        final = [x for x in xmls if 'controls09' in x['name'] and 'test_actual_recovered_lanes_to0' in x['name']]
        assert len(final) == 1 and final[0]['cases'] == 11 and final[0]['failures'] == final[0]['skipped'] == 0
    records.append({'component': component, 'archive': {'path': str(archive), **pin(archive)}, 'manifest': {'path': str(manifest_path), **pin(manifest_path)}, 'release': {'path': str(release_path), **pin(release_path)}, 'member_count': len(actual), 'XML_recounts': xmls, 'full_program_gzip_readbacks': gzip_readbacks})

result = {'status': 'PASS_SELECTED_SEVEN_LOCAL_PUBLIC_CAPSULE_FULL_MEMBER_REPLAY', 'method': pin(__file__), 'capsules': records, 'capsule_count': len(records), 'members_rehashed': sum(r['member_count'] for r in records), 'scope': 'Seven complete local capsules matched to existing authenticated and anonymous publication receipts. No fresh remote retrieval or HDL/native/SAT/analog execution. Recovered-event saved XML and compiled gzip bytes independently reduced; historical failures retained. VCO raw wave replay is the separately attributed root peer, not this audit. RX10 already-public capture is covered by its earlier independent peer and exact public cleanup ledger, not a new capsule replay here.'}
(O / 'archive-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(result['capsule_count'], result['members_rehashed'], pin(O / 'archive-audit.json'))
