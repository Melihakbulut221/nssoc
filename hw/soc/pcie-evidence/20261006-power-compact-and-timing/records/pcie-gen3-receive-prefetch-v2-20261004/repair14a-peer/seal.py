# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Seal complete RX14A captures after independent read-only review."""
import gzip
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

R = Path.cwd()
B = R / 'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004'
O = Path(__file__).resolve().parent
A = Path('/dev/shm/pcie-rx-repair14a-route-nominal-rc-and-peer-20261005.tar.xz')
assert not A.exists()
assert shutil.disk_usage('/dev/shm').free >= 640 * 1024**2


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}


def j(p):
    return json.loads(Path(p).read_text())


review = j(O / 'review.json')
assert review['status'] in ('REVIEWED_RX14A_ZERO_ROUTER_DRC_AND_FUNCTION__NOMINAL_TIMING_PASS', 'REVIEWED_RX14A_ZERO_ROUTER_DRC_AND_FUNCTION__NOMINAL_TIMING_FAIL')
assert review['inputs_rehashed'] == {p: pin(p) for p in review['inputs_rehashed']}
compression_path = Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-physical-replay-01/owned-driver.json')
compression = j(compression_path)['lossless_closed_program']
compiled = compression_path.parent / 'sim/sim.vvp.gz'
assert pin(compiled) == compression['gzip']
with gzip.open(compiled, 'rb') as f:
    h = hashlib.sha256()
    size = 0
    while data := f.read(1024**2):
        h.update(data)
        size += len(data)
assert {'bytes': size, 'sha256': h.hexdigest()} == compression['raw'] == compression['full_decompressed_readback']

validation = {
    'status': review['status'],
    'router_drc_violations': 0, 'same_logical_netlist_after_detailed_route': True,
    'nominal_rc_cell_corner_slack_ns': review['nominal_rc_cell_corner_slack_ns'],
    'SS_setup_improvement_vs_published13_ns': review['SS_setup_improvement_vs13_ns'],
    'unannotated_drivers': 78, 'unannotated_classification': 'All78 unconnected outputs of input-only CTS dummy load cells; all78 clock-input pins independently located on correct extracted SPEF nets. Zero partially unannotated drivers.',
    'saved_canonical_binary_kernel_receipt_revalidated': review['saved_canonical_binary_kernel_receipt_revalidated'],
    'saved_native_port_XML_cases_recounted': 6, 'saved_actual_kernel_fault_controls': 10,
    'full_compiled_program_gzip_readback': compression,
    'peer': {'path': str(O / 'review.json'), **pin(O / 'review.json')},
    'all_nominal_cell_corner_timing_nonnegative': review['all_nominal_cell_corner_timing_nonnegative'], 'max_slew_cap_violations_reported': review['max_slew_cap_violations_reported'], 'qualified_rc': False, 'physical_acceptance': False,
    'constraints': 'Unchanged4ns,0.2ns I/O,0.1ns input slew,0.01pF output load, propagatedclock, no false/multicycle exceptions. Nominal extractedRC reused across three cell corners; not distinctRC process corners.',
    'scope': 'Default150 standalone byte receiver, not strictwidePCS/currentwidepacket receiver. Complete raw repair14a/GRT/proof/port/DRT/RC captures retained. Existing actual proof execution binding revalidated on saved expanded native graphs; proof fault controls inspected but not rerun. New DRT01 and RC01 native executions completed; originalgold expansion reused exactly from completedRX11; this packaging does not rerun tools, no fullchip/foundry/PDN/PHY signoff. Earlier failures and original sources remain unchanged.',
}
V = O / 'pcie-rx-repair14a-finite-physical-validation-20261005.json'
V.write_text(json.dumps(validation, indent=2) + '\n')
files = {}
roots = [
    '/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-14a',
    '/dev/shm/nssoc-rx-prefetch-v2-repair14a-equivalence',
    '/dev/shm/nssoc-rx-prefetch-v2-repair14a-physical-replay-01',
    '/dev/shm/nssoc-rx-prefetch-v2-repair14a-drt-01',
    '/dev/shm/nssoc-rx-prefetch-v2-repair14a-detailed-rc-01',
]
for name in roots:
    directory = Path(name)
    assert directory.is_dir(), f"Missing required completed native capture: {directory}"
    for p in sorted(directory.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            assert not p.is_symlink()
            files['native/' + directory.name + '/' + str(p.relative_to(directory))] = p
for name in ['postroute_repair14a.py', 'normalize_repair14a.py', 'proof_gate_repair14a.py', 'replay_repair14a.py', 'drt_repair14a.py', 'detailed_rc_repair14a.py', 'newtool-readonly-comparison.json', 'eco-proof/compare.py', 'eco-proof/mutations.py']:
    files['method/' + name] = B / name
for p in sorted((B / 'repair14-source').glob('*')):
    if p.is_file() and p.suffix in ('.py', '.json', '.log', '.txt', '.diff'):
        files['preservation/repair14-source/' + p.name] = p
# Controller's live status/owner files are not static capsule inputs. Its final
# dependent-stage binding is published after this seal completes.
for name in ('run.py', 'manifest.json'):
    files['controller/' + name] = B / 'repair14a-continuation01' / name
for path in review['inputs_rehashed']:
    p = Path(path)
    if p.is_relative_to(Path('/dev/shm')) and p not in files.values():
        assert p.is_file() and not p.is_symlink()
        files['bound-input/' + str(p.relative_to('/dev/shm'))] = p
for path in review['inputs_rehashed']:
    p = Path(path)
    if p.is_relative_to(R) and p.suffix in ('.py', '.v') and 'tools' not in p.parts:
        files['source/' + str(p.relative_to(R))] = p
for name in ['hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_prefetch_v2.v', 'LICENSES/CERN-OHL-W-2.0.txt', 'LICENSES/Apache-2.0.txt']:
    files['source/' + name] = R / name
files['prior-proved-native/routed.v'] = Path('/dev/shm/nssoc-rx-prefetch-v2-drt-01/routed.v')
files['preservation/owned-driver.json'] = compression_path
for name in ['pcie-rx-repair13-finite-physical-validation-20261005.json', 'package.json', 'release.json', 'review.json']:
    files['prior-published/repair13/' + name] = B / 'repair13-peer' / name
for name in ['review.py', 'review.json', 'review.log', 'seal.py', 'source-bridge.json', 'source-freeze.json']:
    files['peer/' + name] = O / name
files['validation.json'] = V
notice = O / 'NOTICES.txt'
notice.write_text('Finite standalone RX14A signal-routing evidence. Project source licences retained. Generated netlists refer to pinned IHP SG13G2 cells; upstream PDK libraries/models and tool binaries are hash-pinned, not redistributed. All complete RX14A output files are retained losslessly. Earlier routed13 inputs are bound through their prior public capsule manifest/release. Actual nominal timing status is recorded in validation; no qualified processRC, fullchip, foundryDRC, PDN or PCIe product acceptance.\n')
files['NOTICES.txt'] = notice
members = {n: pin(p) for n, p in files.items()}
minimum = shutil.disk_usage('/dev/shm').free
with tarfile.open(A, 'x:xz', preset=3) as t:
    for n, p in files.items():
        free = shutil.disk_usage('/dev/shm').free
        minimum = min(minimum, free)
        assert free >= 528 * 1024**2
        assert A.stat().st_size < 70 * 1024**2
        t.add(p, arcname=n, recursive=False)
assert members == {n: pin(p) for n, p in files.items()}
with tarfile.open(A, 'r|xz') as t:
    actual = {}
    for m in t:
        assert m.isfile() and m.name not in actual
        actual[m.name] = {'bytes': m.size, 'sha256': hashlib.file_digest(t.extractfile(m), 'sha256').hexdigest()}
assert actual == members
record = {'status': 'PASS_COMPLETE_IMMUTABLE_MEMBER_READBACK', 'archive': {'path': str(A), **pin(A)}, 'validation': pin(V), 'member_count': len(members), 'members': members, 'minimum_shared_free_bytes_during_archive': minimum, 'files_unlinked': []}
(O / 'package.json').write_text(json.dumps(record, indent=2) + '\n')
print(record['archive'], record['member_count'], 'minimum_shared_free', minimum)
