# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Wait for the existing owned route, then run exactly one frozen RC job."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import sys
import time

R = Path.cwd()
sys.path.insert(0, str(R / 'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life
# Outer controller must allow the child RC wrapper its own five-second cleanup.
life.FAILURE_GRACE_SECONDS = 15.0

B = Path(__file__).resolve().parent
O = B / 'tx02-continuation-03'
O.mkdir()
F = Path('/dev/shm/nssoc-tx-path-v4-repair02-drt-03/result.json')
METHOD = B / 'detailed_rc_repair02_resume03.py'
EXPECTED = 'b24d086741f136cd202814f4f5e586cd438932db9d2935e0fedf590023fffc31'


def pin(p):
    with Path(p).open('rb') as f:
        return {'bytes': Path(p).stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


assert pin(METHOD)['sha256'] == EXPECTED
native = json.loads(F.read_text())['pid']
stat = Path(f'/proc/{native}/stat').read_text().rsplit(')', 1)[1].split()
controller = int(stat[1])
identity = life.process_identity(controller)
assert identity is not None
assert b'drt_repair02_resume03.py' in Path(f'/proc/{controller}/cmdline').read_bytes()
record = {'status': 'WAITING_EXISTING_TX02_ROUTE', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'method': pin(__file__), 'rc_method': pin(METHOD), 'lifecycle': pin(life.__file__), 'watched_controller': identity, 'watched_native_pid': native, 'source_peer': pin(B / 'repair02-source/resume03-source-only-peer.json'), 'elapsed_watchdog_seconds': None, 'cpu_affinity': sorted(os.sched_getaffinity(0)), 'qualified_rc': False, 'physical_acceptance': False}


def save():
    life.atomic(O / 'result.json', record)


save()
try:
    with life.ProcessOwner(O / 'owned-processes.json') as owner:
        while True:
            owner.check()
            current = life.process_identity(controller)
            live = current is not None and current['start_ticks'] == identity['start_ticks'] and current['state'] != 'Z'
            if not live:
                break
            owner.cancelled.wait(5)
        route = json.loads(F.read_text())
        assert route['status'] == 'COMPLETE_TX02_SIGNAL_DRT_ZERO_ROUTER_DRC_SAME_NETLIST__RC_REQUIRED', route.get('error', route['status'])
        assert route['returncode'] == 0
        assert pin(METHOD)['sha256'] == EXPECTED
        record.update(status='RUNNING_FRESH_NOMINAL_RC', route_receipt=pin(F))
        save()
        with (O / 'rc.log').open('x') as log:
            process = owner.launch('native', [sys.executable, str(METHOD)], stdout=log, stderr=log)
            record['rc_controller_pid'] = process.pid
            save()
            code = owner.wait(process)
        assert code == 0, f'RC exit {code}'
        result = Path('/dev/shm/nssoc-tx-path-v4-repair02-detailed-rc-02/result.json')
        rc = json.loads(result.read_text())
        assert rc['status'] == 'COMPLETE_UNQUALIFIED_NOMINAL_RC_REVIEW_REQUIRED'
        record.update(status='COMPLETE_ROUTE_AND_NOMINAL_RC_INDEPENDENT_REVIEW_REQUIRED', rc_receipt={'path': str(result), **pin(result)})
        save()
except BaseException as error:
    record.update(status='FAILED_RETAINED', error=repr(error))
    save()
    raise
