# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Close RX13 checkpoint and freeze a finite exact delivery; no native rerun."""
from pathlib import Path
import datetime
import hashlib
import json
import tarfile

O = Path(__file__).resolve().parent
B = O.parent
R = B.parents[3]
def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return {'bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
def load(path):
    return json.loads(Path(path).read_text())
def write(path, value):
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2) + '\n')
review = load(B/'repair13-peer/publication-review.json')
assert review['status'] == 'PASS_RX13_COMPLETED_CAPTURE_AND_THREE_IMMUTABLE_PUBLIC_ASSETS_REVIEW'
controller = load(B/'repair13-continuation01/result.json')
assert pin(B/'repair13-continuation01/result.json') == review['controller']
assert controller['status'] == 'COMPLETE_RX13_FINITE_ROUTE_RC_REVIEW_PUBLICATION'
assert pin(B/'repair13-peer/release.json') == review['release']
assert pin(B/'repair13-peer/review_delivery.py') == review['method']
oldcp = B/'repair13-source/active-checkpoint.json'
old = load(oldcp)
assert old['status'] == 'ACTIVE_RX13_ROUTE_WITH_GUARDED_DURABLE_RC_REVIEW_SEAL_PUBLICATION'
identities = [controller['controller_identity'], *[x['identity'] for x in controller['stages']], *old['live_identity_snapshot'].values()]
for identity in identities:
    proc = Path('/proc')/str(identity['pid'])/'stat'
    if proc.exists():
        fields = proc.read_text().rsplit(') ', 1)[1].split()
        assert fields[19] != str(identity['start_ticks']) or fields[0] == 'Z', identity
archives = []
for directory, package_name, review_name in [
    ('repair13-peer', 'package.json', 'publication-review.json'),
    ('repair13-preroute-preservation', 'pcie-rx-repair13-preroute-package-20261005.json', 'publication-review.json'),
]:
    directory = B/directory
    package = load(directory/package_name)
    reviewed = load(directory/review_name)
    assert pin(directory/package_name) == reviewed['package']
    assert pin(directory/'release.json') == reviewed['release']
    archive = Path(package['archive']['path'])
    assert pin(archive) == {k: package['archive'][k] for k in ['bytes', 'sha256']}
    members = package['members']
    seen = set()
    with tarfile.open(archive, 'r:xz') as tar:
        for member in tar:
            assert member.isfile() and member.name in members and member.name not in seen
            seen.add(member.name)
            with tar.extractfile(member) as stream:
                actual = {'bytes': member.size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
            assert actual == {k: members[member.name][k] for k in ['bytes', 'sha256']}, member.name
    assert seen == set(members)
    release = load(directory/'release.json')
    assert len(release['assets']) == 3
    assert all(x['authenticated_roundtrip'] and x['anonymous_roundtrip'] for x in release['assets'])
    archives.append({'archive': package['archive'], 'members': len(seen), 'manifest': {'path': str((directory/package_name).relative_to(R)), **pin(directory/package_name)}, 'saved_review': {'path': str((directory/review_name).relative_to(R)), **pin(directory/review_name)}, 'public_assets': release['assets']})
old_snapshot = B/'repair13-source/active-checkpoint-before-completion.json'
assert not old_snapshot.exists()
old_snapshot.write_bytes(oldcp.read_bytes())
newcp = {'status': 'CLOSED_RX13_CAPTURE_PUBLIC_TIMING_STILL_FAILS', 'utc': datetime.datetime.now(datetime.UTC).isoformat(), 'previous_active_snapshot': {'path': str(old_snapshot.relative_to(R)), **pin(old_snapshot)}, 'terminal_controller': {'path': str((B/'repair13-continuation01/result.json').relative_to(R)), **pin(B/'repair13-continuation01/result.json')}, 'independent_review': {'path': str((B/'repair13-peer/publication-review.json').relative_to(R)), **pin(B/'repair13-peer/publication-review.json')}, 'all_exact_prior_owner_births_closed': True, 'archives': archives, 'measured_nominal_corner_slacks_ns': review['nominal_cell_corner_slacks_ns'], 'physical_acceptance': False, 'qualified_rc': False, 'resume': ['Do not rerun completed RX13 route/RC/proof/ports.', 'Restore missing bytes only from these exact public assets and complete member maps; retain old running checkpoint snapshot as historical evidence.', 'RX13 SS setup remains -0.441603 ns. Next RX14 must be separately named and independently source-reviewed, preserving 4 ns constraints, hold margin, proof and port gates.'], 'scope': 'Closed standalone default150 RX13. No active child/controller remains. No full-chip or qualified-RC signoff.'}
replacement = oldcp.with_suffix('.completed.tmp')
replacement.write_text(json.dumps(newcp, indent=2)+'\n')
replacement.replace(oldcp)
files = {}
for directory in ['repair13-source', 'repair13-peer', 'repair13-continuation01', 'repair13-preroute-preservation']:
    for path in sorted((B/directory).rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            assert not path.is_symlink()
            files[str(path.relative_to(R))] = pin(path)
for name in ['drt_repair13.py', 'postroute_repair13.py', 'normalize_repair13.py', 'replay_repair13.py', 'proof_gate_repair13.py', 'detailed_rc_repair13.py']:
    path = B/name
    files[str(path.relative_to(R))] = pin(path)
files[str(Path(__file__).relative_to(R))] = pin(__file__)
ready = {'status': 'READY_FINITE_RX13_ROUTE_RC_PROOF_AND_DUAL_PUBLIC_CAPTURE', 'utc': datetime.datetime.now(datetime.UTC).isoformat(), 'new_product_source_allowlist': {}, 'compact_files': files, 'compact_file_count': len(files), 'compact_bytes': sum(x['bytes'] for x in files.values()), 'archives': archives, 'full_member_readbacks_this_delivery': sum(x['members'] for x in archives), 'measured_nominal_corner_slacks_ns': review['nominal_cell_corner_slacks_ns'], 'delta_vs_RX12_ns': review['delta_vs_RX12_ns'], 'saved_proof_states': 1804, 'saved_proof_targets': 5443, 'saved_fault_controls': 10, 'saved_port_cases': 6, 'retained_publication_failure': review['retained_actual_failed_transport'], 'checkpoint_preserved_and_updated': True, 'physical_acceptance': False, 'qualified_rc': False, 'limitations': ['SS setup -0.441603 ns remains failing despite +0.080198 ns improvement; SS hold +0.021680 ns remains positive with less margin.', 'Nominal RC reused across slow/typical/fast cell libraries; qualified separate RC corners and full-chip timing remain open.', 'Zero router DRC, exact saved proof and six native ports cover the default150 standalone byte receiver, not final widePCS/full PHY or main-chip acceptance.', 'Exact prior originalgold expansion reused. No completed EDA, proof, port or network run repeated during delivery.', 'Actual anonymous publication deadline failure retained with exact matching 33,947,648-byte prefix and closed owned process; retry succeeded.'], 'scope': 'Finite closed evidence allowlist including compact transport streams and preserved failed preparations. Root owns combined phase25 documentation, licensing, staging and push. RX14 and active MAX4118 captures are excluded.'}
write(O/'ready-finite.json', ready)
print(json.dumps({'path': str(O/'ready-finite.json'), **pin(O/'ready-finite.json'), 'files': len(files), 'bytes': ready['compact_bytes'], 'archive_members': ready['full_member_readbacks_this_delivery']}))
