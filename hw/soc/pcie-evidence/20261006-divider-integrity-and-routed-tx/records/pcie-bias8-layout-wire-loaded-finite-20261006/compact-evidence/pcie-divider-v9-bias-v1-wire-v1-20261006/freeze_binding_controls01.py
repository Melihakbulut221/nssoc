# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze five copied-input controls only against completed exact new geometry."""
from pathlib import Path
import hashlib
import json

B = Path(__file__).resolve().parent
OLD = B.parent / 'pcie-divider-v8-cap-v1-wire-v1-20261006'
C = B / 'binding-controls01'


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


assert not (C / 'source-freeze.json').exists()
g = json.loads((B / 'geometry-execution.json').read_text())
assert g['status'] == 'PASS_DIVIDER_V9_BIAS8_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
assert g['inputs'] == {p: pin(p) for p in g['inputs']}
assert g['outputs'] == {p: pin(p) for p in g['outputs']}
assert len(g['steps']) == 7 and all(s['execution']['returncode'] == 0 for s in g['steps'])
previous = json.loads((OLD / 'binding-controls01/source-freeze.json').read_text())
assert previous['inputs'] == {p: pin(p) for p in previous['inputs']}
inputs = {**previous['inputs'], **g['inputs'], **g['outputs']}
paths = [B / 'prepare_binding_controls01.py', Path(__file__),
         B / 'geometry-source-freeze.json', B / 'geometry-execution.json',
         B / 'geometry-source-only-peer.json', C / 'run.py', C / 'source-bridge.json',
         OLD / 'binding-controls01/source-freeze.json',
         OLD / 'binding-controls01/source-only-peer-rx.json',
         OLD / 'binding-controls01/run.py']
for p in paths:
    inputs[str(p)] = pin(p)
assert inputs == {p: pin(p) for p in inputs}
(C / 'source-freeze.json').write_text(json.dumps(dict(
    status='FROZEN_SOURCE_FOR_FIVE_COPIED_INPUT_CONTROLS', inputs=inputs,
    physical_mutation=False), indent=2) + '\n')
print(len(inputs), pin(C / 'source-freeze.json'))
