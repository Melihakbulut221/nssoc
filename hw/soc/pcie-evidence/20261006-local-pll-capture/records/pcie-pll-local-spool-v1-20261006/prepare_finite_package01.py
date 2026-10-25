"""Prepare the closed six-source delivery; live PLL status is only a snapshot."""
from pathlib import Path
import hashlib
import json

R = Path.cwd()
B = R / 'hw/soc/out/pcie-pll-local-spool-v1-20261006'
D = B / 'finite01'


def pin(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


validation_path = D / 'pcie-pll-local-spool-v1-controls-and-launch-validation-20261006.json'
validation = json.loads(validation_path.read_text())
assert validation['status'] == 'PASS_FULL_MEMBER_LOCAL_PLL_SPOOL_FINITE_CAPTURE'
peer_path = D / 'saved-finite-peer-vco01.json'
peer = json.loads(peer_path.read_text())
assert peer['status'] == 'PASS_INDEPENDENT_SAVED_LOCAL_PLL_SPOOL_CONTROLS_AND_LAUNCH'
assert not peer['findings']
for key, path in [('archive', Path(validation['archive']['path'])),
                  ('validation', validation_path), ('members', D / 'members.json')]:
    assert {k: peer[key][k] for k in ('bytes', 'sha256')} == pin(path), key
manifest = json.loads((D / 'members.json').read_text())
evidence = {}
for entry in manifest['files'].values():
    path = Path(entry['path'])
    if path.is_relative_to(B):
        assert pin(path) == {key: entry[key] for key in ('bytes', 'sha256')}
        evidence[str(path.relative_to(R))] = pin(path)
for path in D.iterdir():
    if path.is_file() and (path.suffix in ('.py', '.log', '.json')):
        evidence[str(path.relative_to(R))] = pin(path)
for path in [Path(__file__), B / 'finite-seal01-controller.log']:
    evidence[str(path.relative_to(R))] = pin(path)
result = dict(
    status='FINITE_LOCAL_PLL_SPOOL_METHODS_CONTROLS_AND_ACTUAL_LAUNCH_NOT_NATIVE_COMPLETION',
    source_allowlist=validation['source_allowlist'],
    archive=validation['archive'], validation=dict(path=str(validation_path), **pin(validation_path)),
    members=validation['members'], member_count=validation['member_count'],
    logical_data_bytes=validation['logical_data_bytes'],
    historical_campaigns=validation['campaigns'],
    historical_executions=sum(item['cases'] for item in validation['campaigns']),
    historical_failed_executions=sum(item['failed'] for item in validation['campaigns']),
    current_predicates=69, current_predicate_groups=validation['current_test_counts'],
    composite_basis='Complete03: core30 + capture16 + worker21 PASS. '
                    'Bridge05 reran all final capture18 PASS after header-prefix strengthening. '
                    'Final core/worker source bytes unchanged from Complete03. '
                    'Publisher01 12PASS/2FAIL remains historical.',
    source_freeze=validation['source_freeze'], aggregate_peer=validation['aggregate_peer'],
    launch_support_peer=validation['support_peer'],
    saved_finite_peer=dict(path=str(peer_path), **pin(peer_path)),
    independent_saved_peer_record=peer,
    evidence=evidence, evidence_original_relative_paths=True,
    active_native_excluded=True, active_publication_excluded=True,
    native_completion=False, numerical_convergence=False, physical_acceptance=False,
    prior_native_failure='Original maxstep run stopped at383.288ns after upload deadline; '
                         '121 retained public parts are incomplete waveform, not resumable solver state.',
    limitations=['File-fault fixtures do not constitute empirical power-loss testing.',
                 '10GiB physically allocated reservation is separate from8GiB payload cap and is not a quota.',
                 'New native keeps original539devices,1us,TSTEP2.5ps,TMAX1.25ps,100ppm/50ps and no phase-offset removal.',
                 'Native and publisher processes are independent; completion, public readback and numerical replay are separate gates.',
                 'Archived live observation is an immutable startup snapshot, not a claim of current/terminal state.'],
    public_tag='evidence-20261006-pcie-closure')
target = D / 'pcie-pll-local-spool-v1-finite-package-20261006.json'
with target.open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(path=str(target), **pin(target), sources=len(result['source_allowlist']),
                      records=len(evidence), member_count=result['member_count'])))
