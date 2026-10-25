# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind surviving exact direct-test births, then own only the not-yet-run miter."""
import datetime
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

B = Path(__file__).resolve().parent
M = B.parent
ROOT = M.parents[4]
spec = importlib.util.spec_from_file_location('frozen_max4118_controller', M/'run.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
life = old.life
pin = old.pin


def read(path):
    return json.loads(Path(path).read_text())


def identity(pid):
    path = Path('/proc')/str(pid)
    try:
        fields = (path/'stat').read_text().rsplit(') ', 1)[1].split()
        return dict(pid=pid, state=fields[0], ppid=int(fields[1]),
                    process_group=int(fields[2]), start_ticks=fields[19])
    except (FileNotFoundError, ProcessLookupError):
        return None


def same(row):
    current = identity(row['pid'])
    return current and current['start_ticks'] == row['start_ticks'] and current['state'] != 'Z'


def snapshot_tree(seeds):
    rows = {int(p.name): identity(int(p.name)) for p in Path('/proc').iterdir() if p.name.isdigit()}
    rows = {p: v for p, v in rows.items() if v}
    included = {r['pid'] for r in seeds if same(r)}
    while True:
        extra = {p for p, r in rows.items() if r['ppid'] in included}
        if extra <= included:
            break
        included |= extra
    return [rows[p] for p in sorted(included) if p in rows and rows[p]['state'] != 'Z']


def closed_functional(stage, returncode):
    """Observed assertions do not fabricate the orphan pytest's unavailable wait status."""
    captures = list((old.W/stage).rglob('capture/result.json'))
    assert len(captures) == 1, captures
    result_path = captures[0]
    result = read(result_path)
    assert result['mode'] == 'rtl' and result['max_encoded_bytes'] == 4118
    assert result['address_space_limit_bytes'] == 2*1024**3
    assert result['minimum_packet_ring_dwords'] == 2048
    for field in ['inputs', 'runtime']:
        assert result[field] == {p: pin(p) for p in result[field]}, field
    assert result['outputs'] == {n: pin(result_path.parent/n) for n in result['outputs']}
    pytest_file = M/(stage+'-pytest.xml')
    pytest_cases = list(ET.parse(pytest_file).getroot().iter('testcase'))
    assert len(pytest_cases) == 1 and '4118' in pytest_cases[0].attrib['name']
    cocotb_file = result_path.parent/'results.xml'
    cases = list(ET.parse(cocotb_file).getroot().iter('testcase')) if cocotb_file.exists() else []
    counts = dict(passed=sum(not any(c.find(t) is not None for t in ['failure', 'error', 'skipped']) for c in cases),
                  failed=sum(any(c.find(t) is not None for t in ['failure', 'error']) for c in cases),
                  skipped=sum(c.find('skipped') is not None for c in cases))
    passed = (len(cases) == 13 and counts == dict(passed=13, failed=0, skipped=0)
              and result['tests'] == counts
              and result['status'] == 'PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX'
              and not any(pytest_cases[0].find(t) is not None for t in ['failure', 'error', 'skipped'])
              and returncode in (None, 0))
    if not passed:
        assert result['status'] == 'FAIL' or any(pytest_cases[0].find(t) is not None for t in ['failure', 'error']), 'Incomplete or ambiguous capture'
    if passed and stage == 'miter':
        scope = read(result_path.parent/'miter-scope.json')
        assert scope['maximum'] == 4118 and scope['status'] == 'PASS_THIRTEEN_CYCLE_EXACT_PUBLIC_PORT_CASES'
        assert scope['source_pins'] == {p: pin(ROOT/p) for p in scope['source_pins']}
    return dict(name=stage, passed=passed, returncode=returncode,
                returncode_provenance='unavailable_non_child_orphan' if returncode is None else 'waited_owned_child',
                helper_result=dict(path=str(result_path), **pin(result_path)),
                pytest_xml=dict(path=str(pytest_file), **pin(pytest_file)),
                actual_cocotb_counts=counts, actual_cocotb_case_count=len(cases),
                actual_cocotb_names=[c.attrib['name'] for c in cases])


def main():
    assert os.sched_getaffinity(0) == {2}
    assert not (B/'status.json').exists()
    policy = read(B/'policy.json')
    for path, expected in policy['pins'].items():
        assert pin(path) == expected, path
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == policy['boot_id']
    peer = read(B/'source-peer.json')
    assert peer['status'] == 'PASS_SOURCE_ONLY_MAX4118_EXACT_BIRTH_RECOVERY'
    assert peer['policy'] == pin(B/'policy.json') and not peer['findings']
    for row in policy['lost_controllers']:
        assert not same(row), ('Old controller returned', row)
    # Exact seeds can finish after the peer cut. The saved terminal witnesses
    # then decide completion, never a PID disappearance by itself.
    seeds = list(policy['adopted_births'])
    for row in seeds:
        if same(row):
            assert (Path('/proc')/str(row['pid'])/'cmdline').read_bytes().hex() == row['argv_hex']
            assert os.sched_getaffinity(row['pid']) == {2}
    old.subreaper()
    old.guard(entry=True)
    owner = life.ProcessOwner(B/'owner.json')
    record = dict(status='ADOPTING_EXISTING_DIRECT_TEST', controller=life.process_identity(os.getpid()),
                  boot_id=policy['boot_id'], policy=pin(B/'policy.json'), peer=pin(B/'source-peer.json'),
                  old_controller_abruptly_lost=True, original_parent_wait_status_recoverable=False,
                  stages=[], observed_external=[], healthy_elapsed_watchdog=None)
    known = {(r['pid'], r['start_ticks']): r for r in seeds}
    fds = {}

    def save():
        record['utc'] = datetime.datetime.now(datetime.UTC).isoformat()
        life.atomic(B/'status.json', record)

    def observe():
        current = snapshot_tree(list(known.values()))
        for row in current:
            key = (row['pid'], row['start_ticks'])
            known[key] = row
            if key not in fds:
                try:
                    fd = os.pidfd_open(row['pid'])
                except ProcessLookupError:
                    # Normal child exit after the process-table snapshot.
                    continue
                if not same(row):
                    os.close(fd)
                    continue
                fds[key] = fd
        record['observed_external'] = list(known.values())
        record['current_external'] = current
        return current

    def stop_external():
        report = dict(before=observe(), signals=[])
        for sig in [signal.SIGTERM, signal.SIGKILL]:
            for row in observe():
                key = (row['pid'], row['start_ticks'])
                if same(row) and key in fds:
                    try:
                        signal.pidfd_send_signal(fds[key], sig)
                        report['signals'].append(dict(identity=row, signal=int(sig)))
                    except ProcessLookupError:
                        pass
            if sig == signal.SIGTERM:
                deadline = time.monotonic()+5
                while observe() and time.monotonic() < deadline:
                    time.sleep(.05)
        report['after'] = observe()
        return report

    def verify():
        owner.check()
        record['resource'] = old.guard()
        for path, expected in policy['pins'].items():
            assert pin(path) == expected, path

    save()
    try:
        with owner:
            try:
                last = 0
                while observe():
                    owner.check()
                    record['resource'] = old.guard()
                    if time.monotonic()-last >= 5:
                        save()
                        last = time.monotonic()
                    time.sleep(.1)
                verify()
                record['stages'].append(closed_functional('direct', None))
                record['status'] = 'EXISTING_DIRECT_CLOSED_STARTING_ONLY_UNRUN_MITER'
                save()
                original_policy = read(M/'policy.json')
                stage = original_policy['stages'][1]
                assert stage['name'] == 'miter'
                assert not (old.W/'miter').exists() and not (M/'miter.log').exists()
                verify()
                with (M/'miter.log').open('x') as log:
                    process = owner.launch('native', stage['command'], cwd=ROOT,
                        stdout=log, stderr=subprocess.STDOUT, preexec_fn=old.limits,
                        env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1', 'TMPDIR':str(old.W),
                             'OMP_NUM_THREADS':'1','YOSYS_MAX_THREADS':'1',
                             'PATH':str(ROOT/'hw/soc/tools/cocotb-venv/bin')+':'+os.environ['PATH']})
                    record['status'] = 'RUNNING_MITER'
                    record['miter_identity'] = life.process_identity(process.pid)
                    save()
                    last = 0
                    while process.poll() is None:
                        owner.check()
                        record['resource'] = old.guard()
                        if time.monotonic()-last >= 5:
                            record['current_owned'] = old.descendants()
                            save()
                            last = time.monotonic()
                        time.sleep(.1)
                    code = owner.complete(process)
                    owner.check()
                    verify()
                assert not any(r['state'] != 'Z' for r in old.descendants())
                record['stages'].append(closed_functional('miter', code))
                record['current_owned'] = old.descendants()
                owner.check()
            except BaseException:
                record['external_cleanup'] = stop_external()
                record['owned_tree_cleanup'] = old.cleanup_tree()
                raise
        owner.check()
        verify()
        record['status'] = ('COMPLETE_TWO_PROFILES_XML_VERIFIED_REQUIRES_RECOVERY_AWARE_SEAL'
                            if all(r['passed'] for r in record['stages'])
                            else 'CLOSED_TWO_PROFILES_FAILURE_RETAINED_REQUIRES_RECOVERY_AWARE_SEAL')
    except BaseException as error:
        record.update(status='INTERRUPTED_OR_ERROR_RECOVERY_RETAINED', error=repr(error))
        raise
    finally:
        record['stop_reason'] = owner.reason
        save()
        for fd in fds.values():
            os.close(fd)


if __name__ == '__main__':
    main()
