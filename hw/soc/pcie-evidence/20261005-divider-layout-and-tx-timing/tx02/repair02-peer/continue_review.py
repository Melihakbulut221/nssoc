# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Wait for the existing route/RC controller, then review and publish once."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import sys

R = Path.cwd()
sys.path.insert(0, str(R / 'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life

life.FAILURE_GRACE_SECONDS = 15.0
B = R / 'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005'
O = Path(__file__).resolve().parent
W = B / 'tx02-review-continuation-01'
F = B / 'tx02-continuation-03/result.json'
M = json.loads((O / 'continuation-manifest.json').read_text())


def pin(p):
    p = Path(p)
    with p.open('rb') as stream:
        return {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def source_check():
    assert M['sources'] == {p: pin(p) for p in M['sources']}
    assert shutil.disk_usage('/dev/shm').free >= 528 * 1024**2


assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == M['boot_id']
source_check()
assert pin(O / 'chain-source-only-peer.json')['sha256'] == M['chain_peer_sha256']
assert shutil.disk_usage('/dev/shm').free >= 1024**3
W.mkdir()
identity = M['watched_identity']
record = {'status': 'WAITING_EXISTING_TX02_ROUTE_RC_CONTROLLER', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'watched_identity': identity, 'method': pin(__file__), 'manifest': pin(O / 'continuation-manifest.json'), 'cpu_affinity': sorted(os.sched_getaffinity(0)), 'elapsed_watchdog_seconds': None, 'physical_acceptance': False, 'qualified_rc': False, 'steps': []}


def save():
    life.atomic(W / 'result.json', record)


save()
try:
    with life.ProcessOwner(W / 'owned-processes.json') as owner:
        while True:
            owner.check()
            current = life.process_identity(identity['pid'])
            live = current is not None and current['start_ticks'] == identity['start_ticks'] and current['state'] != 'Z'
            if not live:
                break
            assert Path(f"/proc/{identity['pid']}/cmdline").read_bytes().hex() == M['watched_cmdline_hex']
            owner.cancelled.wait(5)
        route_rc = json.loads(F.read_text())
        assert route_rc['status'] == 'COMPLETE_ROUTE_AND_NOMINAL_RC_INDEPENDENT_REVIEW_REQUIRED', route_rc
        assert pin(route_rc['rc_receipt']['path']) == {k: route_rc['rc_receipt'][k] for k in ('bytes', 'sha256')}
        record['route_rc_receipt'] = pin(F)
        for name, cmd, logfile in [
            ('review', [sys.executable, str(O / 'review.py')], O / 'review.log'),
            ('seal', [sys.executable, str(O / 'seal.py')], O / 'seal.log'),
            ('publish', [sys.executable, str(R / 'scripts/publish_pcie_native_capture_v3.py'), '--out', str(O / 'release.json'), '/dev/shm/pcie-tx-repair02-route-nominal-rc-and-peer-20261005.tar.xz', str(O / 'pcie-tx-repair02-finite-physical-validation-20261005.json'), str(O / 'package.json')], O / 'publish.log'),
        ]:
            source_check()
            owner.check()
            record['status'] = 'RUNNING_' + name.upper()
            save()
            with logfile.open('x') as stream:
                child = owner.launch('native', cmd, stdout=stream, stderr=stream)
                record['owned_child'] = life.process_identity(child.pid)
                save()
                code = owner.wait(child)
            record['steps'].append({'name': name, 'command': cmd, 'returncode': code, 'log': {'path': str(logfile), **pin(logfile)}})
            save()
            assert code == 0, (name, code)
            source_check()
        release = json.loads((O / 'release.json').read_text())
        assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
        assert len(release['assets']) == 3
        expected = {p.name: pin(p) for p in [Path('/dev/shm/pcie-tx-repair02-route-nominal-rc-and-peer-20261005.tar.xz'), O / 'pcie-tx-repair02-finite-physical-validation-20261005.json', O / 'package.json']}
        assert {row['name'] for row in release['assets']} == set(expected)
        for row in release['assets']:
            assert row['authenticated_roundtrip'] and row['anonymous_roundtrip']
            assert {k: row[k] for k in ('bytes', 'sha256')} == expected[row['name']]
        record.update(status='COMPLETE_TX02_REVIEW_AND_THREE_PUBLIC_IMMUTABLE_ASSETS', release={'path': str(O / 'release.json'), **pin(O / 'release.json')}, owned_child=None)
        save()
except BaseException as error:
    record.update(status='FAILED_RETAINED', error=repr(error))
    save()
    raise
