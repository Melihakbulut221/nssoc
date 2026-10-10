# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal the closed matched experiment, failed predecessor and native import control."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile

B = Path(__file__).absolute().parent
R = B.parents[3]
sys.path.insert(0, str(R / 'scripts'))
import run_npu_eco_physical as physical


def load(path):
    return json.loads(Path(path).read_text())


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size,
                'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


state = load(B / 'pair02-status.json')
assert state['status'] == 'COMPLETE_MATCHED_ESTIMATES_ONLY'
identity = state['controller']
proc = Path('/proc') / str(identity['pid']) / 'stat'
if proc.exists():
    raw = proc.read_text()
    fields = raw[raw.rfind(')') + 2:].split()
    assert fields[19] != str(identity['start_ticks']) or fields[0] == 'Z'
assert load(B / 'pair01-status.json')['status'] == 'FAILED_PRESERVED'
control = load(B / 'template-control06/control.json')
assert control['status'] == 'PASS_NATIVE_MACRO_LEF_TEMPLATE_CONTROL_FIXED32MACROS301PINS'
peer = load(B / 'saved-template-peer-rx01.json')
assert peer['status'].startswith('PASS') and not peer.get('findings')
comparison = physical.compare(B / 'pair02-original', B / 'pair02-factored')
assert comparison == load(B / 'pair02-comparison.json')
files = {}


def add(name, path):
    path = Path(path)
    assert path.is_file() and not path.is_symlink()
    assert name not in files and not Path(name).is_absolute() and '..' not in Path(name).parts
    files[name] = path


for directory in ['pair01-original', 'pair02-original', 'pair02-factored', 'template-control06']:
    for path in sorted((B / directory).rglob('*')):
        if path.is_file():
            add('native/' + str(path.relative_to(B)), path)
for path in sorted(B.iterdir()):
    if (path.is_file() and path.suffix in ('.py', '.json', '.log', '.xml')
            and not path.name.startswith(('pair02-package', 'pair02-seal', 'pair02-release'))):
        add('review/' + path.name, path)
external = {}
for name, expected in control['inputs'].items():
    path = Path(name)
    assert pin(path) == expected
    if path.suffix == '.AppImage':
        external[name] = dict(expected, reason='Exact runtime retained locally and bound by the existing source-bundle manifest.')
    else:
        add('template-inputs/' + str(path.relative_to(R)), path)
for name in ['LICENSES/Apache-2.0.txt', 'LICENSES/CERN-OHL-W-2.0.txt', 'LICENSES/CC-BY-4.0.txt']:
    add('notices/' + name, R / name)
add('notices/IHP-PDK-LICENSE', B / 'bundle01/pdk/LICENSE')
pins = {name: dict(restore_path=str(path), **pin(path)) for name, path in files.items()}
archive = B / 'nssoc-npu-eco-fresh-physical-pair02-20261006.tar.xz'
assert not archive.exists()
with tarfile.open(archive, 'w:xz', preset=3) as tar:
    for name, path in files.items():
        tar.add(path, arcname=name, recursive=False)
seen = {}
with tarfile.open(archive, 'r:xz') as tar:
    for item in tar:
        assert item.isfile() and not item.issparse() and item.name not in seen and item.name in pins
        with tar.extractfile(item) as stream:
            actual = dict(bytes=item.size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())
        assert actual == {key: pins[item.name][key] for key in actual}
        seen[item.name] = actual
assert set(seen) == set(pins)
for name, path in files.items():
    assert pin(path) == seen[name]
result = dict(status='PASS_CLOSED_MATCHED_PHYSICAL_PAIR_ALL_ARCHIVE_MEMBERS',
              archive=dict(path=str(archive), **pin(archive)), members=pins,
              external_inputs=external, comparison=comparison,
              template_terminal_authority='native/template-control06/control.json',
              stale_template_execute_snapshots_preserved=True,
              scope='Matched fresh global-route estimates only. Historical failed template import and exact corrected control retained. Detailed routing, qualified SRAM/RC, functional equivalence of physical exports and final chip timing/DRC/LVS remain open.',
              candidate_adopted=False, timing_accepted=False, manufacturing_approval=False)
(B / 'pair02-package.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(status=result['status'], archive=result['archive'], members=len(pins))))
