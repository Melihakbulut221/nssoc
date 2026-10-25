# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal closed MAX4118 attempts, including actual failures; no simulation rerun."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import xml.etree.ElementTree as ET

B = Path(__file__).resolve().parent
ROOT = B.parents[4]
W = Path('/dev/shm/nssoc-integrity-v18-max4118-01')
L = Path('/dev/shm/nssoc-integrity-v18-max4118-lifecycle01')


def pin(p):
    p = Path(p)
    with p.open('rb') as stream:
        return dict(bytes=p.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def read(p):
    return json.loads(Path(p).read_text())


def encoded(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def main():
    status = read(B / 'status.json')
    assert status['status'] in {'COMPLETE_PENDING_INDEPENDENT_XML_REVIEW_AND_SEAL',
                                'FAILED_CASES_RETAINED_PENDING_REVIEW_AND_SEAL'}
    assert not status['current_descendants']
    policy = read(B / 'policy.json')
    assert status['policy'] == pin(B / 'policy.json')
    assert policy['pins'] == {p: pin(p) for p in policy['pins']}
    target_runtime = read(B / 'runtime-targets-observed01.json')
    assert target_runtime['files'] == {p: pin(p) for p in target_runtime['files']}
    owner = read(B / 'owner.json')
    assert owner['status'] == 'HEALTHY' and len(owner['processes']) == 2
    assert len(status['stages']) == 2
    rows = []
    for stage, owned in zip(status['stages'], owner['processes']):
        assert owned['status'] == 'REAPED_NO_LIVE_MEMBERS'
        assert owned['returncode'] == stage['returncode']
        assert not owned['members_at_leader_exit']
        root = W / stage['name']
        records = list(root.rglob('capture/result.json'))
        assert len(records) == 1
        path = records[0]
        actual = read(path)
        assert actual['mode'] == 'rtl' and actual['max_encoded_bytes'] == 4118
        assert actual['address_space_limit_bytes'] == 2 * 1024**3
        assert actual['minimum_packet_ring_dwords'] == 2048
        assert actual['inputs'] == {p: pin(p) for p in actual['inputs']}
        assert actual['runtime'] == {p: pin(p) for p in actual['runtime']}
        assert actual['outputs'] == {n: pin(path.parent / n) for n in actual['outputs']}
        pytest_xml = ET.parse(B / (stage['name'] + '-pytest.xml')).getroot()
        pytest_cases = list(pytest_xml.iter('testcase'))
        assert len(pytest_cases) == 1 and '4118' in pytest_cases[0].attrib['name']
        xml = path.parent / 'results.xml'
        cases = list(ET.parse(xml).getroot().iter('testcase')) if xml.exists() else []
        counts = dict(passed=sum(not any(c.find(t) is not None for t in ('failure', 'error', 'skipped')) for c in cases),
                      failed=sum(any(c.find(t) is not None for t in ('failure', 'error')) for c in cases),
                      skipped=sum(c.find('skipped') is not None for c in cases))
        passed = stage['returncode'] == 0
        if passed:
            assert len(cases) == 13 and counts == dict(passed=13, failed=0, skipped=0)
            assert actual['tests'] == counts
            assert actual['status'] == 'PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX'
            assert not any(pytest_cases[0].find(t) is not None for t in ('failure', 'error', 'skipped'))
        else:
            assert any(pytest_cases[0].find(t) is not None for t in ('failure', 'error'))
            assert actual['status'] == 'FAIL'
        if stage['name'] == 'miter' and passed:
            scope = read(path.parent / 'miter-scope.json')
            assert scope['maximum'] == 4118
            assert scope['status'] == 'PASS_THIRTEEN_CYCLE_EXACT_PUBLIC_PORT_CASES'
            assert scope['source_pins'] == {p: pin(ROOT / p) for p in scope['source_pins']}
        rows.append(dict(name=stage['name'], returncode=stage['returncode'], passed=passed,
                         helper_result=pin(path), helper_status=actual['status'],
                         actual_cocotb_counts=counts, actual_cocotb_case_count=len(cases),
                         case_names=[c.attrib['name'] for c in cases], pytest_xml=pin(B / (stage['name'] + '-pytest.xml'))))
    passed = all(r['passed'] for r in rows)
    review = dict(status='PASS_BOTH_MAX4118_FUNCTIONAL_PROFILES' if passed else 'CLOSED_MAX4118_FUNCTIONAL_FAILURES_RETAINED',
                  source_freeze=pin(B.parent / 'source-freeze.json'), method=pin(__file__),
                  controller_status=pin(B / 'status.json'), policy=pin(B / 'policy.json'),
                  source_peer=pin(B / 'source-peer.json'), rows=rows,
                  actual_pytest_executions=2, expected_cases_each=13, skipped_count=sum(r['actual_cocotb_counts']['skipped'] for r in rows),
                  scope='Only actual RTL MAX_ENCODED_BYTES=4118, RING_DWORDS=2048 serial-oracle and V11/V18 cycle miter. No mapped MAX4118, physical timing, complete formal, full PHY or main-chip acceptance. CPU6 native MAX150 and its constraints untouched.',
                  underlying_runtime_first_observed_after_launch=True)
    review_bytes = encoded(review)
    files = {}
    for prefix, root in [('functional', W), ('lifecycle-controls', L)]:
        for p in sorted(root.rglob('*')):
            if p.is_symlink():
                continue
            if p.is_file():
                files[prefix + '/' + str(p.relative_to(root))] = p
    methods = ['run.py', 'policy.json', 'source-peer.json', 'source_peer_pll.py',
               'source-peer-pll.log', 'lifecycle_controls.py', 'lifecycle-controls.json',
               'lifecycle-controls.log', 'status.json', 'owner.json', 'active-checkpoint.json',
               'runtime-targets-observed01.json', 'controller.log', 'direct.log', 'miter.log',
               'direct-pytest.xml', 'miter-pytest.xml', 'seal.py',
               'continue_preservation.py', 'preservation-policy.json', 'preservation-source-peer.json']
    for name in methods:
        p = B / name
        assert p.is_file(), ('Mandatory completed evidence', name)
        files['method/' + name] = p
    for name in policy['pins']:
        p = Path(name)
        if p.is_relative_to(ROOT) and 'tools' not in p.relative_to(ROOT).parts:
            files['source/' + str(p.relative_to(ROOT))] = p
    members = {n: pin(p) for n, p in files.items()}
    members['review.json'] = dict(bytes=len(review_bytes), sha256=hashlib.sha256(review_bytes).hexdigest())
    member_bytes = encoded(members)
    archive = B / 'pcie-integrity-v18-max4118-complete-20261005.tar.xz'
    with tarfile.open(archive, 'x:xz', preset=1) as tar:
        for name, path in files.items():
            assert pin(path) == members[name]
            tar.add(path, arcname=name, recursive=False)
        for name, data in [('review.json', review_bytes), ('member-pins.json', member_bytes)]:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    expected = {**members, 'member-pins.json': dict(bytes=len(member_bytes), sha256=hashlib.sha256(member_bytes).hexdigest())}
    with tarfile.open(archive, 'r:xz') as tar:
        assert len(tar.getmembers()) == len(expected)
        assert {m.name for m in tar.getmembers()} == set(expected)
        for member in tar:
            assert member.isfile()
            with tar.extractfile(member) as stream:
                observed = dict(bytes=member.size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())
            assert observed == expected[member.name]
    assert all(pin(p) == members[n] for n, p in files.items())
    validation = B / 'pcie-integrity-v18-max4118-validation-20261005.json'
    validation.write_bytes(encoded(dict(**review, archive=dict(path=str(archive), **pin(archive)),
                                       full_member_readback=True, member_count=len(expected))))
    package = B / 'pcie-integrity-v18-max4118-package-20261005.json'
    package.write_bytes(encoded(dict(status='CLOSED_CAPTURE_BINDING', validation=pin(validation),
                                    archive=pin(archive), members=expected)))
    print(json.dumps(dict(status=review['status'], archive=pin(archive), members=len(expected)), indent=2))


if __name__ == '__main__':
    main()
