# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add independent RC readback and immutable public native receipt, no rerun."""
from pathlib import Path
import hashlib
import json
import tarfile

B = Path(__file__).resolve().parent
ROOT = B.parents[3]
G = B.parent / 'pcie-divider-v7-wire-v5-20261005'


def pin(p):
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


peer = json.loads((B / 'root-saved-rc-peer.json').read_text())
assert peer['status'] == 'PASS_ROOT_INDEPENDENT_SAVED_DIVIDER_WIRE_GRAPH_AND_CAPACITANCE' and not peer['findings']
assert peer['inputs'] == {p: pin(Path(p)) for p in peer['inputs']}
release = json.loads((B / 'release-complete.json').read_text())
assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(release['assets']) == 1
asset = release['assets'][0]
assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
assert pin(B / asset['name']) == {k: asset[k] for k in ['bytes', 'sha256']}
members = json.loads((B / 'capture-members.json').read_text())
assert len(members) == 250
with tarfile.open(B / asset['name'], 'r|xz') as arc:
    seen = {}
    for m in arc:
        assert m.isfile() and m.name not in seen
        seen[m.name] = dict(bytes=m.size, sha256=hashlib.file_digest(arc.extractfile(m), 'sha256').hexdigest())
assert seen == {n: {k: h[k] for k in ['bytes', 'sha256']} for n, h in members.items()}
summary = dict(
    status='FINITE_DIVIDER_V7_NATIVE_GEOMETRY_AND_WIRE_RC_PROTOTYPE_READY',
    physical_intrinsics=dict(total=91, hbt=34, rppd=33, mim=6, finite_substrate_contacts=18),
    native_clusters=dict(all_retained=72, on_device_terminals=38, metal_conductors=37,
                         intrinsic_body_only=1, explicitly_auxiliary_without_metal_device_terminal_or_port=34),
    actual_references=dict(metal_terminals=198, preserved_intrinsic_body_terminals=85, public_ports=7, all_anchors=205),
    actual_native_RC=dict(resistors=312, capacitors=618, connected_conductors=37, disconnected_anchors=0,
                          full_capacitance_edges=306, collapsed_matrix_entries=1444,
                          every_R_edge_value_and_every_ground_mutual_C_attachment_preserved=True),
    actual_controls=dict(source_binding_baseline=1, expected_source_binding_rejections=4, exact_raw_RC_corruption_rejections=13),
    retained_failures=['V1 via-stack versus electrical-leaf census', 'V2 simplified comparison database versus actual91 devices',
                       'V3 report_lvs net-only database persistence', 'V4 all72 native clusters versus38 on devices',
                       'first source-only RC audit substitution before native', 'first RC control expected later rather than earlier strict graph-open rejection'],
    no_Magic_rerun_after_correct_native_extraction=True,
    geometry_saved_peer=dict(path=str(G / 'saved-geometry-peer.json'), **pin(G / 'saved-geometry-peer.json')),
    RC_independent_peer=dict(path=str(B / 'root-saved-rc-peer.json'), **pin(B / 'root-saved-rc-peer.json')),
    public_native_asset=asset, full_native_archive_readback=250,
    qualification=dict(full_PEX=False, substrate_R=False, RF_or_process_corner=False,
                       loaded_postlayout_division=False, full_clockbank_layout=False, main_chip_or_full_PHY=False, manufacturing=False))
(B / 'finite-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
paths = [B / n for n in ['root-saved-rc-peer.json', 'root_saved_rc_review.py', 'capture-members.json',
                        'capture-validation.json', 'release-complete.json', 'publish-complete.log',
                        'finite-summary.json', 'seal_finite_peer.py']]
paths += sorted(p for p in (B / 'release-complete.transport').rglob('*') if p.is_file())
files = {'peer/' + str(p.relative_to(B)): p for p in paths}
for name in ['Apache-2.0', 'CERN-OHL-W-2.0', 'CC-BY-4.0']:
    files['licenses/' + name + '.txt'] = ROOT / 'LICENSES' / (name + '.txt')
inventory = {n: dict(restore_path=str(p), **pin(p)) for n, p in files.items()}
cap = B / 'pcie-divider-v7-wire-rc01-independent-peers.tar.xz'
assert not cap.exists()
with tarfile.open(cap, 'x:xz') as arc:
    for n, p in files.items():
        arc.add(p, arcname=n, recursive=False)
seen = {}
with tarfile.open(cap, 'r|xz') as arc:
    for m in arc:
        assert m.isfile() and m.name not in seen
        seen[m.name] = dict(bytes=m.size, sha256=hashlib.file_digest(arc.extractfile(m), 'sha256').hexdigest())
assert seen == {n: {k: h[k] for k in ['bytes', 'sha256']} for n, h in inventory.items()}
assert all(pin(p) == seen[n] for n, p in files.items())
(B / 'peer-capture-members.json').write_text(json.dumps(inventory, indent=2) + '\n')
result = dict(status='PASS_ADDITIVE_FINITE_ROOT_PEER_ALLMEMBER_CAPTURE', archive=dict(path=str(cap), **pin(cap)),
              members=len(inventory), member_manifest=pin(B / 'peer-capture-members.json'),
              finite_summary=pin(B / 'finite-summary.json'), first_native_capsule_unchanged=True)
(B / 'peer-capture-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result), flush=True)
