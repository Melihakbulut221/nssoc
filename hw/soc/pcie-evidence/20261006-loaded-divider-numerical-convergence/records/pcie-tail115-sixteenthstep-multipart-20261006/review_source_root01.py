"""Read-only frozen-source, every-byte partition and actual inverse controls peer."""
from pathlib import Path
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys

B = Path(__file__).resolve().parent
def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())

f = B / 'source-freeze01.json'
assert pin(f) == dict(bytes=129583, sha256='d8adaa93da0e6a30cbce36c2f77bdc529f4968e5c89241c169d81afac7e8b924')
j = json.loads(f.read_text())
for p, h in j['inputs'].items():
    assert pin(p) == h, p
assert len(j['inputs']) == 509
manifest = json.loads((B / 'pcie-tail115-sixteenthstep-multipart-manifest01.json').read_text())
offset = 0
whole = hashlib.sha256()
for i, row in enumerate(manifest['parts']):
    assert row['name'] == manifest['archive']['name'] + f'.part{i:04d}'
    assert row['offset'] == offset and 0 < row['bytes'] <= 32 * 1024**2
    path = B / 'parts01' / row['name']
    assert pin(path) == {k: row[k] for k in ('bytes', 'sha256')}
    with path.open('rb') as stream:
        while data := stream.read(1024**2):
            whole.update(data)
            offset += len(data)
assert offset == 773973792 and whole.hexdigest() == '70f9431fa42ffd5039a8c4e6dce860a7603b5440a1414e3b2e473387b0db0763'
assert {k: manifest['archive'][k] for k in ('bytes', 'sha256')} == dict(bytes=offset, sha256=whole.hexdigest())
control_dir = B / 'peer-controls01'
control_dir.mkdir()
for name in ('prepare01.py', 'check_controls01.py'):
    shutil.copy2(B / name, control_dir / name)
    assert pin(B / name) == pin(control_dir / name)
env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE', 'PYTHONOPTIMIZE', 'LD_PRELOAD')}
with (control_dir / 'run.log').open('x') as log:
    subprocess.run([sys.executable, str(control_dir / 'check_controls01.py')], check=True, env=env, stdout=log, stderr=subprocess.STDOUT)
controls = json.loads((control_dir / 'controls01.json').read_text())
assert controls == json.loads((B / 'controls01.json').read_text())
launch = (B / 'launch01.py').read_text()
ast.parse(launch)
assert 'publish_pcie_native_capture_v4.py' in launch and "'evidence-20261006-pcie-closure'" in launch
assert 'start_new_session=True' in launch and 'm.verify(manifest' in launch
assert 'os.kill' not in launch and 'unlink' not in launch and 'clobber' not in launch
result = dict(status='PASS_SOURCE_ONLY_N16_IMMUTABLE_MULTIPART_PUBLICATION', freeze=pin(f),
              findings=[], pinned_files=509, ordered_parts=24, public_assets_expected=25,
              full_reconstruction=dict(bytes=offset, sha256=whole.hexdigest()),
              actual_independent_controls=controls['controls'], controls=pin(control_dir / 'controls01.json'),
              source=pin(__file__),
              scope='Reviewed complete split/verify/control/launcher sources, rehashed509 inputs and all24 ordered slices, independently reran five actual controls. Same immutable archive, V4 exact publisher, original120s child limits, fresh receipts and no native signaling. Publication and complete roundtrips not yet executed.',
              physical_acceptance=False)
(B / 'source-only-peer01-root.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(status=result['status'], pins=509, parts=24, controls=5)))
