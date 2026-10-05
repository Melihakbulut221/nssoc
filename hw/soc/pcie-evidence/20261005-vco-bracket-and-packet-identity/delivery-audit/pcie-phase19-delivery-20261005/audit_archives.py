# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read completed finite capsules; no simulator or native design run."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import tarfile
import xml.etree.ElementTree as ET

R = Path.cwd()
O = Path(__file__).resolve().parent


def pin(p):
    with Path(p).open('rb') as f:
        return {'bytes': Path(p).stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


def read(p):
    return json.loads(Path(p).read_text())


specs = []
b = R / 'hw/soc/out/pcie-vco-v6-local-v1-wire-20261005'
for bias in ('wired06-02', 'wired085-01'):
    rel = b / f'release-{bias}.json'
    archive = Path(read(rel)['files'][0]['path'])
    manifest = b / f'members-{bias}.json'
    specs.append((f'vco-v6-{bias}', archive, manifest, read(manifest), rel))
for component, base, manifest, rel in [
    ('vco-v6-peer', 'pcie-vco-v6-local-v1-wire-20261005', 'peer-validation.json', 'release-peer.json'),
    ('event-packet-type', 'pcie-event-packet-type-20261005', 'package.json', 'release.json'),
]:
    b = R / 'hw/soc/out' / base
    d = read(b / manifest)
    specs.append((component, Path(d['archive']['path']), b / manifest, d['members'], b / rel))
b = R / 'hw/soc/out/pcie-integrity-v11-20261005'
for kind in ('controls', 'native'):
    rel = b / f'{kind}-release.json'
    archive = next(Path(p['path']) for p in read(rel)['files'] if p['path'].endswith('.tar.xz'))
    manifest = b / f'{kind}-members.json'
    specs.append((f'integrity-v11-{kind}', archive, manifest, {**read(manifest), 'members.json': pin(manifest)}, rel))
b = R / 'hw/soc/out/pcie-pll-acquisition-20261004/pair-v1-source'
archive = Path(read(b / 'ready-finite.json')['capsule']['path'])
with tarfile.open(archive) as t:
    data = t.extractfile('members.json').read()
expected = {n: {k: p[k] for k in ('bytes', 'sha256')} for n, p in json.loads(data).items()}
expected['members.json'] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
specs.append(('pll-pair-method', archive, b / 'ready-finite.json', expected, b / 'release.json'))

records = []
for component, archive, manifest, expected, rel in specs:
    release = read(rel)
    assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
    asset = next(a for a in release['assets'] if a['name'] == archive.name)
    assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
    assert pin(archive) == {k: asset[k] for k in ('bytes', 'sha256')}
    expected = {n: {k: p[k] for k in ('bytes', 'sha256')} for n, p in expected.items()}
    actual, xmls, programs = {}, [], []
    raw_pins = {}
    if component == 'event-packet-type':
        for row in read(manifest.parent / 'validation.json')['case_readbacks']:
            prog = row['compiled_full_gzip_readback']
            raw_pins[prog['gzip']['sha256']] = prog['raw']
    with tarfile.open(archive, 'r|xz') as tar:
        for m in tar:
            assert m.isfile() and m.name not in actual
            f = tar.extractfile(m)
            if m.name.endswith('results.xml'):
                data = f.read()
                digest = hashlib.sha256(data).hexdigest()
                cases = list(ET.fromstring(data).iter('testcase'))
                xmls.append({'member': m.name, 'cases': len(cases), 'failed': sum(c.find('failure') is not None or c.find('error') is not None for c in cases), 'skipped': sum(c.find('skipped') is not None for c in cases)})
            elif component == 'event-packet-type' and m.name.endswith('.vvp.gz'):
                data = f.read()
                digest = hashlib.sha256(data).hexdigest()
                with gzip.GzipFile(fileobj=io.BytesIO(data)) as z:
                    h, size = hashlib.sha256(), 0
                    while block := z.read(1024**2):
                        size += len(block)
                        h.update(block)
                raw = {'bytes': size, 'sha256': h.hexdigest()}
                assert raw == raw_pins[digest]
                programs.append({'member': m.name, 'raw': raw})
            else:
                digest = hashlib.file_digest(f, 'sha256').hexdigest()
            actual[m.name] = {'bytes': m.size, 'sha256': digest}
    assert actual == expected, (component, set(actual) ^ set(expected))
    if component == 'event-packet-type':
        assert len(programs) == 7
        assert sum(x['failed'] for x in xmls) == 5
        positives = [x for x in xmls if not x['failed']]
        assert sorted(x['cases'] - x['skipped'] for x in positives) == [8, 11]
    records.append({'component': component, 'archive': {'path': str(archive), **pin(archive)}, 'manifest': {'path': str(manifest), **pin(manifest)}, 'release': {'path': str(rel), **pin(rel)}, 'members': len(actual), 'XML_recounts': xmls, 'compiled_program_full_readbacks': programs})
result = {'status': 'PASS_FINITE_PHASE19_SEVEN_COMPLETE_CAPSULE_REPLAY', 'method': pin(__file__), 'capsule_count': len(records), 'member_count': sum(x['members'] for x in records), 'capsules': records, 'scope': 'Complete local archived bytes compared with retained authenticated/anonymous publication receipts. Packet-type saved XML and all compiled gzip programs re-reduced. VCO waveform numerical audit belongs to the retained independent all-sample peer. No new simulation, SAT, physical execution, remote retrieval or product acceptance.'}
(O / 'archive-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(result['capsule_count'], result['member_count'])
