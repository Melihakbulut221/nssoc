"""Compose only the reviewed exact model after independent saved native RC peer."""
from pathlib import Path
import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys

R = Path.cwd()
B = Path(__file__).resolve().parent
C = B.parent / 'pcie-divider-v10-tail-v1-wire-rc-v1-20261006'


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


assert os.sched_getaffinity(0) == {10}
plan = json.loads((B / 'builder-source-freeze.json').read_text())
assert plan['inputs'] == {p: pin(p) for p in plan['inputs']}
builder_peer = json.loads((B / 'builder-source-only-peer-root.json').read_text())
assert builder_peer['status'] == 'PASS_SOURCE_ONLY_TAIL115_V1_DIVIDER_HYBRID_BUILDER'
assert builder_peer['freeze'] == pin(B / 'builder-source-freeze.json') and not builder_peer['findings']
rc_peer = json.loads((C / 'saved-rc-peer-pll.json').read_text())
assert rc_peer['status'] == 'PASS_INDEPENDENT_SAVED_TAIL115_V1_DIVIDER_WIRE_GRAPH_AND_CAPACITANCE' and not rc_peer['findings']
assert rc_peer['inputs'] == {p: pin(p) for p in rc_peer['inputs']}
native = json.loads((C / 'native-execution.json').read_text())
assert native['status'] == 'PASS_NATIVE_WIRE_RC_GRAPH_AND13_RAW_CONTROLS_ONLY'
assert native['outputs'] == {p: pin(p) for p in native['outputs']}
assert not (B / 'composed01').exists()
assert shutil.disk_usage('/dev/shm').free >= 1024**3
command = [sys.executable, str(R / 'scripts/build_pcie_clock_div4_v10_tail115_v1_hybrid_v1.py')]
for key, value in plan['native_input_files'].items():
    command += ['--' + key, value]
command += ['--pdk', str(Path.home() / '.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2'), '--out', str(B / 'composed01')]
env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE', 'GH_TOKEN', 'GITHUB_TOKEN')}
env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


with (B / 'composition01.log').open('x') as log:
    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env, preexec_fn=limits)
assert result.returncode == 0
assert plan['inputs'] == {p: pin(p) for p in plan['inputs']}
assert shutil.disk_usage('/dev/shm').free >= 512 * 1024**2
receipt = dict(status='COMPOSED_REVIEWED_MODEL_NO_NATIVE_SIMULATION', command=command,
               builder_peer=pin(B / 'builder-source-only-peer-root.json'), saved_rc_peer=pin(C / 'saved-rc-peer-pll.json'),
               source_freeze=pin(B / 'builder-source-freeze.json'), returncode=result.returncode,
               outputs={str(p): pin(p) for p in (B / 'composed01').rglob('*') if p.is_file()})
(B / 'composition01-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(receipt['status'])
