from pathlib import Path
import hashlib
import json

B = Path(__file__).resolve().parent
W = B.parent

def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())

assert not (B / 'source-freeze.json').exists()
g = json.loads((W / 'geometry-execution.json').read_text())
assert g['status'] == 'PASS_DIVIDER_V7_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
assert g['outputs'] == {p: pin(p) for p in g['outputs']}
inputs = {**g['inputs'], **g['outputs']}
for p in [W / 'geometry-execution.json', W / 'geometry-source-only-peer.json',
          W / 'geometry-source-freeze.json', B / 'run.py', Path(__file__), B / 'source-bridge.json']:
    inputs[str(p)] = pin(p)
assert inputs == {p: pin(p) for p in inputs}
result = dict(status='FROZEN_COPIED_INPUT_BINDING_CONTROL_SOURCE', inputs=inputs,
              cases=['positive', 'reference_clock_swap', 'reference_pullup_length',
                     'reference_missing_tap', 'native_mim_area_corruption'],
              no_native_device_extraction=True, no_physical_design_mutation=True,
              method=pin(B / 'run.py'))
(B / 'source-freeze.json').write_text(json.dumps(result, indent=2) + '\n')
print(len(inputs), pin(B / 'source-freeze.json'))
