"""Run finite composition/fault and actual short lifecycle controls, no SPICE."""
from pathlib import Path
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

B = Path(__file__).resolve().parent
R = Path.cwd()
assert os.sched_getaffinity(0) == {10}
env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE', 'GH_TOKEN', 'GITHUB_TOKEN')}
env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')


def pin(p):
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


for label, source, temp, expected in [
    ('source', R / 'sw/tests/test_pcie_vco_v6_divider_tail115_v1_wire_v1.py', 'pytest01', 32),
    ('handoff', B / 'test_launcher01_handoff.py', 'pytest-handoff01', 4),
]:
    log = B / (label + '-controls01.log')
    xml = B / (label + '-controls01.xml')
    assert not log.exists() and not xml.exists() and not (B / temp).exists()
    command = [sys.executable, '-m', 'pytest', '-q', str(source), '--basetemp', str(B / temp), '--junitxml', str(xml)]
    start = time.monotonic()
    with log.open('x') as f:
        process = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, env=env, preexec_fn=limits)
    cases = list(ET.parse(xml).getroot().iter('testcase')) if xml.exists() else []
    counts = dict(passed=0, failed=0, skipped=0)
    for case in cases:
        key = 'failed' if any(case.find(x) is not None for x in ('failure', 'error')) else 'skipped' if case.find('skipped') is not None else 'passed'
        counts[key] += 1
    receipt = dict(returncode=process.returncode, **counts, command=command,
                   seconds=time.monotonic() - start, source=pin(source), log=pin(log),
                   xml=pin(xml) if xml.exists() else None, no_analog_simulation=True)
    (B / (label + '-controls-receipt.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    assert process.returncode == 0 and counts == dict(passed=expected, failed=0, skipped=0), receipt
    print(label, counts, flush=True)
