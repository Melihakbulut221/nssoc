"""Curate only closed publisher V2 evidence and retained V1 failure evidence."""
from pathlib import Path
import hashlib
import json

R = Path.cwd()
B = Path(__file__).resolve().parent
S = R / 'hw/soc/out/pcie-local-spool-publisher-v2-20261006'
F = S / 'finite01'
OLD = R / 'hw/soc/out/pcie-pll-local-spool-v1-20261006'
C = R / 'hw/soc/pcie-evidence/20261006-local-publisher-log-race'
def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())

assert not C.exists()
validation = json.loads((F / 'pcie-local-spool-publisher-v2-controls-validation-20261006.json').read_text())
old = json.loads((OLD / 'publisher-failure01/validation.json').read_text())
assert validation['status'] == 'PASS_FINITE_PUBLISHER_V2_ARCHIVE_FULL_READBACK'
assert validation['members'] == 1457 and old['members'] == 1313
public = json.loads((F / 'release01.json').read_text())
assert public['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(public['assets']) == 4
for asset in public['assets']:
    assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
    path = next(Path(row['path']) for row in public['files'] if row['name'] == asset['name'])
    assert pin(path) == {k: asset[k] for k in ('bytes', 'sha256')}
saved = json.loads((F / 'saved-finite-peer-pll01.json').read_text())
delivery = json.loads((F / 'saved-release-peer-pll02.json').read_text())
assert saved['status'].startswith('PASS') and delivery['status'].startswith('PASS')
assert not Path('/proc/389818').exists(), 'Finite four-asset publication must be closed'
sources = validation['sources']
for path, expected in sources.items():
    assert pin(R / path) == expected
paths = set()
for folder in (S, F, OLD / 'publisher-failure01'):
    for p in folder.iterdir():
        if p.is_file() and p.suffix in ('.py', '.json', '.log', '.xml'):
            paths.add(p)
for name in ('launch_publisher01.py', 'policy.json', 'launch-once.json', 'detached-receipt.json', 'root-launch01.log'):
    paths.add(S / 'launch01' / name)
for name in ('seal_publisher_failure01.py', 'seal_publisher_failure02.py'):
    paths.add(OLD / name)
for p in (OLD / 'publisher-failure01').glob('*'):
    if p.is_file() and p.suffix in ('.py', '.json', '.log'):
        paths.add(p)
paths.add(R / 'hw/soc/out/pcie-local-spool-publisher-v2-seal01.log')
paths.add(OLD / 'publication01/publication.json')
paths.add(OLD / 'launch01/publication.log')
paths.add(Path(__file__))
# The public transport receipts remain complete in finite local records. The
# compact inventory does not copy either live spool or independent worker tree.
for p in (F / 'release01.transport').rglob('*'):
    if p.is_file() and p.suffix == '.json':
        paths.add(p)
assert not any(p.is_relative_to(S / 'publication01') for p in paths)
C.mkdir(parents=True)
files = {}
sidecars = []
for p in sorted(paths):
    expected = pin(p)
    target = C / 'records' / p.relative_to(R / 'hw/soc/out')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(p.read_bytes())
    assert pin(target) == expected
    files[str(target.relative_to(C))] = dict(source=str(p.relative_to(R)), **expected)
    sidecar = Path(str(target) + '.license')
    license_id = 'Apache-2.0' if p.suffix == '.py' else 'CC-BY-4.0'
    sidecar.write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: ' + license_id + '\n')
    sidecars.append(str(sidecar.relative_to(C)))
archives = [dict(**validation['archive'], members=1457, manifest=validation['manifest']),
            dict(**old['archive'], members=1313, manifest=old['manifest'])]
inventory = dict(status='PASS_FINITE_PUBLISHER_V2_FIX_AND_RETAINED_V1_FAILURE_DELIVERY',
                 sources=sources, files=files, sidecars=sidecars, archives=archives,
                 public_assets=public['assets'], members=2770,
                 current_predicates=31, historical_executions=93, historical_passed=88, historical_failed=5,
                 active_journals_excluded=True, native_completion=False, full_phy_acceptance=False,
                 full_chip_final_timing_accepted=False, production_acceptance=False,
                 scope='Two tested sources and finite immutable controls/reviews/startup. Failed V1 host stat race retained; separate native continued. Active publisher/native timing or acquisition results excluded.')
p = C / 'delivery-inventory.json'
p.write_text(json.dumps(inventory, indent=2) + '\n')
Path(str(p) + '.license').write_text('SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\nSPDX-License-Identifier: CC-BY-4.0\n')
(B / 'source-allowlist.json').write_text(json.dumps(sources, indent=2) + '\n')
(B / 'evidence-allowlist.json').write_text(json.dumps({str(p.relative_to(R)): pin(p) for p in C.rglob('*') if p.is_file()}, indent=2) + '\n')
print(dict(status=inventory['status'], compact=len(files), sources=2, members=2770, assets=4))
