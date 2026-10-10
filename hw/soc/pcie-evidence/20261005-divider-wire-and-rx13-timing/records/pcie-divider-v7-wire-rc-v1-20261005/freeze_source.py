# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze actual completed geometry and all owned runtime bytes before RC peer."""
from pathlib import Path
import hashlib
import json

B = Path(__file__).resolve().parent
ROOT = B.parents[3]
G = B.parent / 'pcie-divider-v7-wire-v5-20261005'


def pin(p):
    p = Path(p)
    with p.open('rb') as stream:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


assert not (B / 'source-freeze.json').exists()
g = json.loads((G / 'geometry-execution.json').read_text())
assert g['status'] == 'PASS_DIVIDER_V7_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
c = json.loads((G / 'binding-controls01/result.json').read_text())
assert c['status'] == 'PASS_BASELINE_AND_FOUR_ACTUAL_COPIED_INPUT_BINDING_CONTROLS'
p = json.loads((G / 'saved-geometry-peer.json').read_text())
assert p['status'] == 'PASS_DIVIDER_V7_SAVED_GEOMETRY_AND_BINDING_CONTROLS' and not p['findings']
assert p['geometry_execution'] == pin(G / 'geometry-execution.json')
assert p['binding_controls'] == pin(G / 'binding-controls01/result.json')
inputs = {**g['inputs'], **g['outputs']}
runtime_receipt = B.parent / 'pcie-divider-v7-wire-v1-20261005/magic-runtime-restoration.json'
r = json.loads(runtime_receipt.read_text())
prefixes = ('nssoc-magic-area-product-v4-build/runtime/lib/', 'nssoc-magic-pad-stack-tech-v1/')
runtime = {str(Path('/dev/shm') / name): h for name, h in r['all_members'].items() if name.startswith(prefixes)}
assert len(runtime) == 398
inputs.update(runtime)
files = [*B.glob('*.py'), *B.glob('*bridge*.json'), B / 'audit-import-closure.json', B / 'mutation-plan.json',
         G / 'geometry-execution.json', G / 'geometry-source-only-peer.json', G / 'geometry-source-freeze.json',
         G / 'saved-geometry-peer.json', G / 'binding-controls01/result.json',
         G / 'binding-controls01/source-freeze.json', G / 'binding-controls01/run.py',
         G / 'binding-controls01/source-only-peer.json', G / 'binding-controls01/launch-preflight.json',
         runtime_receipt, B.parent / 'pcie-magic-area-product-v4-20261004/build.json',
         B.parent / 'pcie-vco-v6-local-v1-wire-20261005/run_native_rc.py',
         B.parent / 'pcie-vco-v6-local-v1-wire-20261005/audit_wire_rc.py',
         B.parent / 'pcie-vco-v6-local-v1-wire-20261005/check_native_mutations.py',
         Path('/home/hasanmelih/miniconda3/bin/python3'), Path('/usr/bin/tclsh8.6'),
         *[Path('/lib/x86_64-linux-gnu') / n for n in ['libtcl8.6.so', 'libc.so.6', 'libz.so.1', 'libm.so.6']],
         Path('/lib64/ld-linux-x86-64.so.2'), ROOT / 'scripts/check_magic_intrinsic_cap_retirement.py']
files += [Path(n) for n in json.loads((B / 'audit-import-closure.json').read_text())['files']]
nx = Path('/home/hasanmelih/miniconda3/lib/python3.14/site-packages/networkx')
files += sorted(nx.rglob('*.py'))
for path in files:
    inputs[str(path)] = pin(path)
assert inputs == {path: pin(path) for path in inputs}
result = dict(status='FROZEN_DIVIDER_V7_WIRE_RC_SOURCE_PENDING_INDEPENDENT_PEER', inputs=inputs,
              producer_sources={p.name: pin(p) for p in B.glob('*.py')},
              runtime398_files_full_rehashed=True, networkx_source_files=len(list(nx.rglob('*.py'))),
              expected=dict(devices=91, metal_terminals=198, body_terminals=85,
                            public_ports=7, anchors=205, wire_components=37),
              original_intrinsic_devices_and_body_nets_unchanged=True,
              actual_wire_rc_executed=False, qualified_pex=False,
              scope='Wire-only native RC and complete native/export graph/C contract; no RF, PVT, substrate-R or foundry qualification')
(B / 'source-freeze.json').write_text(json.dumps(result, indent=2) + '\n')
print(pin(B / 'source-freeze.json'), len(inputs), 'frozen inputs')
