# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Copy closed RX16one evidence to SSD and emit an explicit finite allowlist."""
import datetime
import hashlib
import json
import shutil
from pathlib import Path

R = Path.cwd()
B = R / 'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004'
O, C = B / 'repair16one-peer', B / 'repair16one-continuation01'
F = B / 'repair16one-finite01'
assert not F.exists()
F.mkdir()


def pin(p):
    with Path(p).open('rb') as f:
        return {'bytes': Path(p).stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


def j(p):
    return json.loads(Path(p).read_text())


peer = j(O / 'saved-result-peer-rx01.json')
assert peer['findings'] == [] and peer['archive_members'] == 110
terminal = j(C / 'result.json')
assert terminal['status'] == 'COMPLETE_RX16ONE_FINITE_ROUTE_RC_REVIEW_PUBLICATION'
release, package = j(O / 'release.json'), j(O / 'package.json')
archive = Path(package['archive']['path'])
assert pin(archive) == {k: package['archive'][k] for k in ('bytes', 'sha256')}
saved_archive = F / archive.name
shutil.copyfile(archive, saved_archive)
assert pin(saved_archive) == pin(archive)

# Native bodies remain in the fully read archive. Only finite receipts, methods,
# logs and saved publication transcripts are copied into the compact inventory.
files = set()
for folder in (O, C):
    for p in folder.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.pyc'):
            assert not p.is_symlink() and p.stat().st_size < 2 * 1024**2
            files.add(p)
for p in (B / 'repair16-source').iterdir():
    if p.is_file():
        assert p.stat().st_size < 2 * 1024**2
        files.add(p)
method_names = ['postroute_repair16_one04.py', 'normalize_repair16one.py', 'proof_gate_repair16one.py', 'replay_repair16one.py', 'drt_repair16one.py', 'detailed_rc_repair16one.py', 'owned_lifecycle16.py', 'eco-proof/compare.py', 'eco-proof/mutations.py']
files.update(B / n for n in method_names)
copied = {}
generated_license = 'SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n'
for p in sorted(files):
    rel = p.relative_to(R)
    dest = F / 'compact' / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    before = pin(p)
    shutil.copyfile(p, dest)
    assert pin(dest) == before == pin(p)
    copied[str(rel)] = {'original': str(p), 'copy': str(dest), **before}
    if p.suffix != '.py':
        dest.with_name(dest.name + '.license').write_text(generated_license)

ready = {
    'status': 'READY_FINITE_RX16ONE_MEASURED_IMPROVEMENT__4NS_TIMING_NOT_CLOSED',
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'active_product_sources': [],
    'source_scope': 'No new active RTL or test source is adopted. These are out-of-tree physical ECO/proof/route/review method snapshots and finite evidence only.',
    'method_source_pins': {str(B / n): pin(B / n) for n in method_names},
    'independent_saved_peer': {'path': str(O / 'saved-result-peer-rx01.json'), **pin(O / 'saved-result-peer-rx01.json')},
    'archive': {'path': str(saved_archive), **pin(saved_archive), 'members': 110, 'original_ram_path': str(archive)},
    'public_assets': release['assets'], 'saved_transport_operations': peer['actual_transport_operations'],
    'nominal_cell_corner_slack_ns': peer['nominal_cell_corner_slack_ns'],
    'SS_setup_gain_vs14a_ns': peer['SS_setup_gain_vs14a_ns'],
    'router_drc': 0, 'binary_state_bits': 1804, 'binary_functions': 5443,
    'actual_kernel_negative_controls': 10, 'native_port_cases': 6,
    'nominal_RC_only': True, 'physical_acceptance': False,
    'adoption_boundary': peer['adoption_boundary'],
    'compact_files': copied,
    'compact_file_count': len(copied), 'compact_original_bytes': sum(x['bytes'] for x in copied.values()),
    'sidecars': 'Generated metadata/transcript copies have CC-BY-4.0 SPDX sidecars. Python method bytes retain their original SPDX headers. No source or raw byte changed.',
    'capsule_excludes_later_peer': 'The immutable 110-member public capsule predates this independent saved peer and finite builder. Both later methods/receipts are retained in the compact allowlist; the existing public capsule was not replaced.',
    'history': 'Source-only and actual tool failures, original GRT screen rejection and subsequent route-trial selection are retained. This measured result does not erase prior failed candidates.',
    'builder': {'path': str(Path(__file__)), **pin(__file__)},
}
out = F / 'ready-finite.json'
out.write_text(json.dumps(ready, indent=2) + '\n')
checkpoint = {
    'status': 'CLOSED_RX16ONE_ROUTE_RC_PUBLICATION__TIMING_OPEN',
    'utc': ready['utc'], 'ready': {'path': str(out), **pin(out)},
    'terminal': {'path': str(C / 'result.json'), **pin(C / 'result.json')},
    'release': {'path': str(O / 'release.json'), **pin(O / 'release.json')},
    'supersedes_for_status_only': str(B / 'repair16-source/active-checkpoint16one.json'),
    'next': 'Saved critical-path analysis only; no new native repair or adoption authorized by this record.',
}
(F / 'closed-checkpoint01.json').write_text(json.dumps(checkpoint, indent=2) + '\n')
print(json.dumps({'ready': str(out), **pin(out), 'compact_files': len(copied), 'compact_bytes': ready['compact_original_bytes'], 'archive': ready['archive']}))
