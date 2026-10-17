# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Complete current V23 regression after the recorded observer repairs."""
from pathlib import Path
import hashlib
import json
import os
import resource
import sys
import xml.etree.ElementTree as ET

R = Path.cwd()
B = Path(__file__).absolute().parent
sys.path.insert(0, str(R / 'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life


def pin(p):
    p = Path(p)
    with p.open('rb') as stream:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


assert pin(life.__file__)['sha256'] == '39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886'
assert os.sched_getaffinity(0) == {14}
ready = R / 'hw/soc/out/pcie-integrity-v23-20261006/ready-finite.json'
frozen = json.loads(ready.read_text())['source_allowlist']
assert frozen == {name: pin(R / name) for name in frozen}
output = B / 'v23-final-controls01'
output.mkdir()
scratch = Path('/dev/shm/nssoc-integrity-v23-current-full-controls04')
assert not scratch.exists()
command = [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
           'sw/tests/test_pcie_gen3_integrity_v23_header.py',
           'sw/tests/test_pcie_gen3_integrity_v23_miter.py',
           'sw/tests/test_pcie_gen3_continuous_rx_integrity_v23.py',
           'sw/tests/test_pcie_gen3_integrity_v23_block_burst.py',
           '-k', 'not 4118', '--basetemp=' + str(scratch),
           '--junitxml=' + str(output / 'tests.xml')]
row = dict(status='RUNNING_CURRENT_V23_FULL_NON4118_REGRESSION',
           owner=life.process_identity(os.getpid()), source_pins=frozen,
           ready=pin(ready), command=command, method=pin(__file__),
           boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
           elapsed_watchdog_seconds=None, full_phy_acceptance=False)
owner = life.ProcessOwner(output / 'owned-processes.json')
life.atomic(output / 'result.json', row)


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


try:
    with owner:
        with (output / 'tests.log').open('x') as log:
            child = owner.launch('native', command, stdout=log, stderr=log,
                                 preexec_fn=limits,
                                 env={**{k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE')},
                                      'TMPDIR': '/dev/shm', 'PYTHONDONTWRITEBYTECODE': '1',
                                      'OMP_NUM_THREADS': '1', 'YOSYS_MAX_THREADS': '1'})
            row['child'] = life.process_identity(child.pid)
            life.atomic(output / 'result.json', row)
            row['returncode'] = owner.wait(child)
            owner.check()
        assert frozen == {name: pin(R / name) for name in frozen}
        cases = list(ET.parse(output / 'tests.xml').iter('testcase'))
        row['cases'] = [dict(c.attrib, failed=c.find('failure') is not None,
                             error=c.find('error') is not None, skipped=c.find('skipped') is not None) for c in cases]
        row['passed'] = sum(not any(c.find(k) is not None for k in ['failure', 'error', 'skipped']) for c in cases)
        row['status'] = 'PASS_CURRENT_V23_FULL_NON4118_REGRESSION' if row['returncode'] == 0 and row['passed'] == len(cases) else 'FAILED_CURRENT_V23_REGRESSION_RETAINED'
except BaseException as error:
    row.update(status='FAILED_CURRENT_V23_REGRESSION_RETAINED', error=repr(error))
    raise
finally:
    row['stop_reason'] = owner.reason
    row['outputs'] = {str(p): pin(p) for p in output.iterdir() if p.is_file() and p.name != 'result.json'}
    life.atomic(output / 'result.json', row)
