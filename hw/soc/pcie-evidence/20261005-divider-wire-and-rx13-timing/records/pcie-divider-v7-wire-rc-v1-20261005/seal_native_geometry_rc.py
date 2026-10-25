# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal all closed native geometry, RC and failed revisions; no EDA rerun."""
from pathlib import Path
import hashlib
import json
import tarfile

B = Path(__file__).resolve().parent
ROOT = B.parents[3]
G = B.parent / 'pcie-divider-v7-wire-v5-20261005'


def pin(p):
    with p.open('rb') as stream:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


assert json.loads((G / 'geometry-execution.json').read_text())['status'] == 'PASS_DIVIDER_V7_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
assert json.loads((G / 'saved-geometry-peer.json').read_text())['status'] == 'PASS_DIVIDER_V7_SAVED_GEOMETRY_AND_BINDING_CONTROLS'
assert json.loads((B / 'native-wire-audit.json').read_text())['status'] == 'PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
assert json.loads((B / 'controls-v2/result.json').read_text())['status'] == 'PASS_SAVED_NATIVE_BASELINE_AND13_EXACT_RC_CORRUPTION_CONTROLS_V2'
files = {}
excluded = {'continuation.json', 'seal-native-geometry-rc.log', 'capture-members.json', 'capture-validation.json'}
for i in range(1, 6):
    directory = B.parent / f'pcie-divider-v7-wire-v{i}-20261005'
    for p in sorted(directory.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.name not in excluded and not p.name.endswith('.tar.xz'):
            files[f'geometry-v{i}/' + str(p.relative_to(directory))] = p
for p in sorted(B.rglob('*')):
    if p.is_file() and '__pycache__' not in p.parts and p.name not in excluded and not p.name.endswith('.tar.xz') and not any(part.startswith('root-') or part.startswith('root_') for part in p.relative_to(B).parts):
        files['wire-rc-v1/' + str(p.relative_to(B))] = p
for name in ['nssoc-div4-v7-wire-native-01', 'nssoc-div4-v7-wire-native-02',
             'nssoc-div4-v7-wire-geometry-diagnostic01', 'nssoc-div4-v7-wire-geometry-05',
             'nssoc-div4-v7-binding-controls-01']:
    directory = Path('/dev/shm') / name
    assert directory.is_dir()
    for p in sorted(directory.rglob('*')):
        if p.is_file():
            files['native/' + name + '/' + str(p.relative_to(directory))] = p
directory = Path('/dev/shm/nssoc-div4-v7-wire-rc-01')
for p in sorted(directory.iterdir()):
    assert p.is_file()
    files['native/rc01/' + p.name] = p
layout = Path('/dev/shm/nssoc-div4-v7-layout-01')
for name in ['nssoc_clock_div4_v7_layout.gds', 'nssoc_clock_div4_v7_layout.lef', 'result.json', 'schematic.cir']:
    files['original-layout/' + name] = layout / name
for name in ['Apache-2.0', 'CERN-OHL-W-2.0', 'CC-BY-4.0']:
    files['licenses/' + name + '.txt'] = ROOT / 'LICENSES' / (name + '.txt')
assert all(p.is_file() and not p.is_symlink() for p in files.values())
members = {name: dict(restore_path=str(p), **pin(p)) for name, p in files.items()}
assert sum(h['bytes'] for h in members.values()) < 40 * 1024**2
archive = B / 'pcie-divider-v7-wire-geometry-v5-and-rc01-complete.tar.xz'
assert not archive.exists()
with tarfile.open(archive, 'x:xz') as arc:
    for name, p in files.items():
        arc.add(p, arcname=name, recursive=False)
observed = {}
with tarfile.open(archive, 'r|xz') as arc:
    for item in arc:
        assert item.isfile() and item.name not in observed
        observed[item.name] = dict(bytes=item.size, sha256=hashlib.file_digest(arc.extractfile(item), 'sha256').hexdigest())
assert observed == {n: {k: h[k] for k in ['bytes', 'sha256']} for n, h in members.items()}
assert all(pin(p) == observed[name] for name, p in files.items())
(B / 'capture-members.json').write_text(json.dumps(members, indent=2) + '\n')
result = dict(status='PASS_CLOSED_DIVIDER_GEOMETRY_RC_CAPTURE_ALLMEMBER_READBACK', archive=dict(path=str(archive), **pin(archive)),
              members=len(members), source_files_full_readback=True, member_manifest=pin(B / 'capture-members.json'),
              all_prior_V1_V5_geometry_failures_retained=True, first_RC_control_harness_failure_retained=True,
              original_native_RC_not_rerun=True, source_derivation_attempt01_retained=True,
              independent_RC_saved_peer_pending=True, qualified_PEX=False, loaded_division_simulated=False,
              private_compiled_runtime_excluded=True)
(B / 'capture-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result), flush=True)
