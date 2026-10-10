# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve complete TX05 captures after exact saved-output review."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import tarfile

R = Path.cwd()
B = R / 'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005'
O = Path(__file__).resolve().parent
N = Path('/dev/shm')
A = N / 'pcie-tx-repair05-route-nominal-rc-and-peer-20261006.tar.xz'


def pin(p):
    p = Path(p)
    with p.open('rb') as stream:
        return {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def read(p):
    return json.loads(Path(p).read_text())


assert not A.exists()
assert shutil.disk_usage(N).free >= 1024**3
review = read(O / 'review.json')
assert review['status'] == 'REVIEWED_TX05_ZERO_ROUTER_DRC_AND_FUNCTION__MEASURED_NOMINAL_TIMING'
assert review['inputs_rehashed'] == {p: pin(p) for p in review['inputs_rehashed']}
T = N / 'nssoc-tx-path-v4-repair05-physical-replay-02'
ports = read(T / 'result.json')
compressed = T / 'sim/sim.vvp.gz'
assert pin(compressed) == ports['outputs']['sim/sim.vvp.gz']
digest = hashlib.sha256()
size = 0
with gzip.open(compressed, 'rb') as stream:
    while chunk := stream.read(1024**2):
        digest.update(chunk)
        size += len(chunk)
expanded = {'bytes': size, 'sha256': digest.hexdigest()}
assert expanded == ports['lossless_closed_program']['raw']

validation = {
    'status': 'REVIEWED_ROUTER_DRC_AND_FUNCTION_WITH_MEASURED_NOMINAL_TIMING',
    'router_drc_violations': 0,
    'same_logical_netlist_after_detailed_route': True,
    'nominal_rc_cell_corner_slack_ns': review['nominal_rc_cell_corner_slack_ns'],
    'nominal_prior_and_improvement': review['nominal_prior_and_improvement'],
    'nominal_all_cell_corners_pass': review['nominal_all_cell_corners_pass'],
    'unannotated_output_analysis': review['unannotated_output_analysis'],
    'canonical_binary_kernel_replay': review['canonical_binary_kernel_replay'],
    'saved_native_port_XML_cases_recounted': 3,
    'saved_actual_kernel_fault_controls': 10,
    'full_compiled_program_gzip_readback': expanded,
    'peer': {'path': str(O / 'review.json'), **pin(O / 'review.json')},
    'qualified_rc': False,
    'physical_acceptance': False,
    'constraints': 'Unchanged 4 ns, I/O constraints and propagated clock; no false or multicycle exceptions. Same nominal RC reused across three cell corners, not three RC corners.',
    'scope': 'Standalone TXv4 four-lane scrambling/fixed130 gearbox. Completed TX05 actual-SPEF-first candidate/proof/ports02/DRT01/RC01 preserved; original ports01 interpreter failure retained; no new native rerun by this sealer. Actual measured timing is retained regardless of pass/fail. No full-chip/PHY/PDN/foundry acceptance.',
}
V = O / 'pcie-tx-repair05-finite-physical-validation-20261006.json'
V.write_text(json.dumps(validation, indent=2) + '\n')
files = {}
roots = {
    'nssoc-tx-path-v4-postroute-repair-05': ('repaired.v', 'repaired.odb', 'repaired.sdc', 'result.json'),
    'nssoc-tx-path-v4-repair05-equivalence': ('gold.json.gz', 'gate.json.gz', 'normalization.json', 'proof-execution-binding.json', 'equivalence.json', 'mutation-controls.json'),
    'nssoc-tx-path-v4-repair05-physical-replay-02': ('results.xml', 'simulation.log', 'sim/sim.vvp.gz', 'result.json'),
    'nssoc-tx-path-v4-repair05-drt-01': ('routed.v', 'routed.odb', 'routed.sdc', 'native.log', 'router-drc.rpt', 'result.json'),
    'nssoc-tx-path-v4-repair05-detailed-rc-01': ('routed.spef', 'native.log', 'extract.tcl', 'result.json'),
}
for name, mandatory in roots.items():
    directory = N / name
    assert directory.is_dir() and all((directory / p).is_file() for p in mandatory), name
    for p in sorted(directory.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            assert not p.is_symlink()
            files['native/' + name + '/' + str(p.relative_to(directory))] = p
for path in review['inputs_rehashed']:
    p = Path(path)
    if p.is_relative_to(R) and p.suffix in ('.py', '.v') and 'tools' not in p.parts:
        files['source/' + str(p.relative_to(R))] = p
for name in ['postroute_repair05.py', 'normalize_repair05.py', 'replay_repair05_resume02.py', 'owned_lifecycle05.py', 'drt_repair05.py', 'detailed_rc_repair05.py', 'proof_gate_repair05.py', 'proof05/compare.py', 'proof05/mutations.py', 'repair05-continuation01/run.py']:
    files['method/' + name] = B / name
for name in ['hw/soc/rtl/pcie/soc_pcie_gen3_tx_path_v4.v', 'hw/soc/rtl/pcie/soc_pcie_gen3_gearbox.v', 'scripts/check_pcie_integrity_native.py', 'scripts/cocotb_results.py', 'LICENSES/CERN-OHL-W-2.0.txt', 'LICENSES/Apache-2.0.txt']:
    files['source/' + name] = R / name
for name in ['result.json', 'extract.tcl', 'native.log']:
    files['prior-native-rc/' + name] = N / 'nssoc-tx-path-v4-repair03-detailed-rc-01' / name
for name in ['source-freeze.json', 'source-bridge.json', 'source-only-peer-rx.json', 'proof-source-freeze02.json', 'proof-source-bridge.json', 'proof-source-only-peer-rx02.json', 'ports02-source-freeze.json', 'ports02-source-only-peer-rx.json', 'route-rc-source-freeze.json', 'route-rc-source-bridge.json', 'route-rc-source-only-peer-rx.json', 'pre-drt-proof-port-review.json', 'owned_lifecycle05-before02.py', 'proof-source-review-rx01-findings.json', 'test_owned_lifecycle05.py', 'lifecycle-controls02.log', 'binding-controls02.log', 'ports-launch01.json', 'ports-launch01.log', 'ports-launch02.json', 'ports-launch02.log']:
    files['preservation/repair05-source/' + name] = B / 'repair05-source' / name
for name in ['review.json','package.json','release.json','pcie-tx-repair03-finite-physical-validation-20261005.json']:
    files['prior-published/repair03/' + name] = B / 'repair03-peer' / name
for name in ['package.json','pcie-tx-repair05-preroute-validation-20261006.json','release01.json']:
    files['prior-preroute-publication/' + name] = B / 'repair05-preroute-preservation' / name
for name in ['review.py', 'review.json', 'review.log', 'seal.py', 'source-derivation.json', 'source-freeze.json']:
    files['peer/' + name] = O / name
for name in ['run.py', 'manifest.json', 'source-only-peer-vco.json', 'launch.py', 'launch.json', 'detached-confirmed.json']:
    files['continuation/' + name] = B / 'repair05-continuation01' / name
files['validation.json'] = V
members = {name: pin(p) for name, p in files.items()}
minimum = shutil.disk_usage(N).free
with tarfile.open(A, 'x:xz', preset=3) as archive:
    for name, p in files.items():
        minimum = min(minimum, shutil.disk_usage(N).free)
        assert minimum >= 528 * 1024**2 and A.stat().st_size < 200 * 1024**2
        archive.add(p, arcname=name, recursive=False)
assert A.stat().st_size < 200 * 1024**2
assert members == {name: pin(p) for name, p in files.items()}
actual = {}
with tarfile.open(A, 'r|xz') as archive:
    for member in archive:
        assert member.isfile() and member.name not in actual
        actual[member.name] = {'bytes': member.size, 'sha256': hashlib.file_digest(archive.extractfile(member), 'sha256').hexdigest()}
assert actual == members
record = {'status': 'PASS_COMPLETE_IMMUTABLE_MEMBER_READBACK', 'archive': {'path': str(A), **pin(A)}, 'validation': {'path': str(V), **pin(V)}, 'member_count': len(members), 'members': members, 'minimum_shared_free_bytes_during_archive': minimum, 'files_unlinked': []}
(O / 'package.json').write_text(json.dumps(record, indent=2) + '\n')
print(record['archive'], record['member_count'])
