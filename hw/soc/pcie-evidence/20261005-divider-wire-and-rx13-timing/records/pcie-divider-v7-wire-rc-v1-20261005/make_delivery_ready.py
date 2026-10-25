# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Finite immutable delivery inventory; root owns Git curation and publication."""
from pathlib import Path
import hashlib
import json
import tarfile

B = Path(__file__).resolve().parent
ROOT = B.parents[3]


def pin(p):
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


capsules, receipts = {}, {}
for label, manifest_name in [('complete', 'capture-members.json'), ('peer', 'peer-capture-members.json')]:
    receipt_path = B / f'release-{label}.json'
    release = json.loads(receipt_path.read_text())
    assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(release['assets']) == 1
    asset = release['assets'][0]
    assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
    cap = B / asset['name']
    assert pin(cap) == {k: asset[k] for k in ['bytes', 'sha256']}
    expected = json.loads((B / manifest_name).read_text())
    seen = {}
    with tarfile.open(cap, 'r|xz') as arc:
        for member in arc:
            assert member.isfile() and member.name not in seen
            seen[member.name] = dict(bytes=member.size, sha256=hashlib.file_digest(arc.extractfile(member), 'sha256').hexdigest())
    assert seen == {n: {k: h[k] for k in ['bytes', 'sha256']} for n, h in expected.items()}
    capsules[str(cap.relative_to(ROOT))] = pin(cap)
    receipts[label] = dict(receipt=dict(path=str(receipt_path.relative_to(ROOT)), **pin(receipt_path)),
                           manifest=dict(path=str((B / manifest_name).relative_to(ROOT)), **pin(B / manifest_name)),
                           members=len(seen), asset=asset)
summary = json.loads((B / 'finite-summary.json').read_text())
assert summary['status'] == 'FINITE_DIVIDER_V7_NATIVE_GEOMETRY_AND_WIRE_RC_PROTOTYPE_READY'
roots = [B, *(B.parent / f'pcie-divider-v7-wire-v{i}-20261005' for i in range(1, 6))]
excluded = {'continuation.json', 'delivery-ready.json', 'make-delivery-ready.log'}
files = [p for directory in roots for p in directory.rglob('*') if p.is_file() and not p.is_symlink()
         and '__pycache__' not in p.parts and p.name not in excluded and not p.name.endswith('.tar.xz')]
assert len(files) == len(set(files))
compact = {str(p.relative_to(ROOT)): pin(p) for p in sorted(files)}
assert sum(h['bytes'] for h in compact.values()) < 12 * 1024**2
result = dict(status='READY_FINITE_DIVIDER_V7_WIRE_GEOMETRY_RC_AND_FULL_FAILURE_HISTORY',
              new_source_pins={}, method_pins={n: h for n, h in compact.items() if n.endswith(('.py', '.lvs'))},
              finite_ready=dict(path=str((B / 'finite-summary.json').relative_to(ROOT)), **pin(B / 'finite-summary.json')),
              compact_allowlist=compact, compact_count=len(compact), compact_bytes=sum(h['bytes'] for h in compact.values()),
              capsules=capsules, public_captures=receipts, all_public_readbacks_passed=True,
              all_capsule_members_rehashed=True, no_new_product_RTL_source_in_this_evidence_cut=True,
              all_unique_closed_native_bytes_preserved_offline_and_publicly=True,
              no_active_native_or_publisher_owned=True, no_product_acceptance=True,
              next_step='Separately versioned actual VCO + divider wire model; preserve91 divider intrinsics and85 body terminals, source peer before simulation.')
assert compact == {n: pin(ROOT / n) for n in compact}
assert not (B / 'delivery-ready.json').exists()
(B / 'delivery-ready.json').write_text(json.dumps(result, indent=2) + '\n')
print(pin(B / 'delivery-ready.json'), result['compact_count'], result['compact_bytes'], flush=True)
