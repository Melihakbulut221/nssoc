"""Detach the frozen V4 publisher for three immutable finite evidence assets."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

R = Path.cwd()
B = R / 'hw/soc/out/pcie-pll-local-spool-v1-20261006'
D = B / 'finite01'


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


source = R / 'scripts/publish_pcie_native_capture_v4.py'
assert pin(source)['sha256'] == '1b73bd49b86090a6eeff1cf16af36a2a17a4885bb748ecc301435ee796b3b585'
package_path = D / 'pcie-pll-local-spool-v1-finite-package-20261006.json'
package = json.loads(package_path.read_text())
assert package['status'] == 'FINITE_LOCAL_PLL_SPOOL_METHODS_CONTROLS_AND_ACTUAL_LAUNCH_NOT_NATIVE_COMPLETION'
peer = json.loads((D / 'saved-finite-peer-vco01.json').read_text())
assert peer['status'] == 'PASS_INDEPENDENT_SAVED_LOCAL_PLL_SPOOL_CONTROLS_AND_LAUNCH'
assert not peer['findings'] and pin(D / 'saved-finite-peer-vco01.json') == {
    key: package['saved_finite_peer'][key] for key in ('bytes', 'sha256')}
files = [Path(package[key]['path']) for key in ('archive', 'validation')] + [package_path]
for key, path in zip(('archive', 'validation'), files):
    assert pin(path) == {field: package[key][field] for field in ('bytes', 'sha256')}
receipt = D / 'publication-release01.json'
assert not receipt.exists()
with (D / 'publication-once.json').open('x') as stream:
    json.dump(dict(method=pin(__file__), source=pin(source),
                   files={str(path): pin(path) for path in files}), stream, indent=2)
command = ['taskset', '-c', '14', str(R / 'hw/soc/tools/cocotb-venv/bin/python'),
           str(source), '--tag', 'evidence-20261006-pcie-closure',
           '--out', str(receipt), *map(str, files)]
environment = {key: value for key, value in os.environ.items()
               if key not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE', 'LD_PRELOAD')}
environment['PYTHONDONTWRITEBYTECODE'] = '1'
with (D / 'publication-controller.log').open('x') as stream:
    process = subprocess.Popen(command, cwd=R, stdin=subprocess.DEVNULL,
                               stdout=stream, stderr=subprocess.STDOUT,
                               start_new_session=True, close_fds=True, env=environment)
fields = (Path('/proc') / str(process.pid) / 'stat').read_text().rsplit(') ', 1)[1].split()
record = dict(status='DETACHED_FINITE_PUBLISHER_ACTUAL_TERMINAL_RECEIPT_REQUIRED',
              pid=process.pid, start_ticks=fields[19], process_group=int(fields[2]),
              boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              command=command, receipt=str(receipt), method=pin(__file__),
              source=pin(source), files={str(path): pin(path) for path in files},
              native_processes_owned=False)
with (D / 'publication-detached.json').open('x') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps(record))
