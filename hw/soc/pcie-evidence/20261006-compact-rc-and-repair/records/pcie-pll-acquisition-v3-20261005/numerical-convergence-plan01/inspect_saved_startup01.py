"""Read saved native/replayed evidence only; no solver, capture, or download."""
from pathlib import Path
import hashlib
import json
import math
import struct

B = Path(__file__).resolve().parent
ROOT = Path.cwd()
A = Path('/dev/shm/nssoc-pll-acquisition-v1-step5-01')
C = Path('/dev/shm/nssoc-pll-acquisition-v3-step25-detached-02')
AR = Path('/dev/shm/nssoc-pll-acquisition-v1-step5-full-review-01/result.json')
CR = B.parent / 'replay-step25-01/result.json'
PAIR = CR.with_name('pair-result.json')

def pin(p):
    p = Path(p)
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())

def operation(p):
    header, data = p.read_bytes().split(b'Binary:\n', 1)
    lines = header.decode().splitlines()
    assert 'No. Variables: 825' in lines and 'No. Points: 1' in lines
    assert len(data) == 825 * 8
    assert all(math.isfinite(x) for x in struct.unpack('=825d', data))
    normalized = '\n'.join(x for x in lines if not x.startswith('Date:'))
    return normalized, data

native = [json.loads((p / 'result.json').read_text()) for p in (A, C)]
review = [json.loads(p.read_text()) for p in (AR, CR)]
for p, n, r in zip((A, C), native, review):
    assert n['status'] == 'PASS_NATIVE_STREAM_FINITE_SCREEN'
    assert r['status'] == 'PASS_LOSSLESS_AUTHOR_REPLAY_AND_INDEPENDENT_ACQUISITION_ARITHMETIC'
    assert r['native_result'] == pin(p / 'result.json')
    assert r['all539_author_safety_records_exact'] is True
    assert r['agreement']['all_predicates_exact'] is True
    assert n['zero_source_op'] is True and n['strict_numerical_diagnostics_pass'] is True
    for path, expected in n['outputs'].items():
        assert pin(p / path) == expected
    for path, expected in n['inputs'].items():
        assert pin(path) == expected
assert native[0]['devices'] == native[1]['devices'] and len(native[0]['devices']) == 539
assert review[0]['independent']['reference_edges_s'] == review[1]['independent']['reference_edges_s']
assert operation(A / 'op.raw') == operation(C / 'op.raw')
assert (A / 'spinit').read_bytes() == (C / 'spinit').read_bytes() == b'set num_threads=1\n'
old, current = [(p / 'bench.cir').read_text() for p in (A, C)]
assert old.replace('.tran 5e-12 1e-06 0 5e-12\n', '.tran 2.5e-12 1e-06 0 2.5e-12\n') == current
assert current.count('.tran 2.5e-12 1e-06 0 2.5e-12\n') == 1
assert current.count('.options reltol=1e-4 abstol=1e-12\n') == 1
assert not any(x.lower().startswith(('.ic ', '.nodeset ')) for x in current.splitlines())
first_reference = review[0]['independent']['reference_edges_s'][0]
rows = {}
for kind in native[0]['measurement']['edge_times']:
    aa = native[0]['measurement']['edge_times'][kind]
    cc = native[1]['measurement']['edge_times'][kind]
    rows[kind] = dict(
        first_saved_5ps_s=aa[:8], first_saved_2p5ps_s=cc[:8],
        saved_before_first_reference_5ps=[x for x in aa if x < first_reference],
        saved_before_first_reference_2p5ps=[x for x in cc if x < first_reference],
        warning='Chronological edges within original4ns measurement window; high-frequency lists are not a proven cross-run absolute oscillator ordinal alignment.')
for item in json.loads((B / 'external-source-receipt.json').read_text())['sources']:
    assert pin(item['saved_path']) == {k: item[k] for k in ('bytes', 'sha256')}
tran = (B / 'dctran.c').read_text()
assert 'delta=MIN(ckt->CKTfinalTime/100,ckt->CKTstep)/10;' in tran
assert 'ckt->CKTdelta /= 10;' in tran
assert 'ckt->CKTdelta = MIN(ckt->CKTdelta,ckt->CKTmaxStep);' in tran
init = (B / 'traninit.c').read_text()
assert 'ckt->CKTmaxStep   = job->TRANmaxStep;' in init
assert 'ckt->CKTdelmin = 1e-11*ckt->CKTmaxStep;' in init
assert json.loads(PAIR.read_text())['status'] == 'FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN'
proposal = current.replace('.tran 2.5e-12 1e-06 0 2.5e-12\n', '.tran 2.5e-12 1e-06 0 1.25e-12\n')
assert proposal.replace('.tran 2.5e-12 1e-06 0 1.25e-12\n', '.tran 2.5e-12 1e-06 0 2.5e-12\n') == current
assert not (B / 'candidate-max125-source-only.cir').exists()
(B / 'candidate-max125-source-only.cir').write_text(proposal)
paths = [Path(__file__), A / 'result.json', C / 'result.json', AR, CR, PAIR,
         B / 'external-source-receipt.json', B / 'dctran.c', B / 'traninit.c',
         B / 'candidate-max125-source-only.cir']
paths += [p / name for p in (A, C) for name in ('bench.cir', 'op.raw', 'spinit', 'run.log', 'execution.json')]
report = dict(
    status='SAVED_STARTUP_INSPECTED_SOURCE_ONLY_MAXSTEP_EXPERIMENT_PROPOSAL',
    inputs={str(p): pin(p) for p in paths},
    no_native_run=True, no_raw_download=True,
    common_op=dict(variables=825, bytes=6600, exact_binary_payload_equal=True,
                   payload_sha256=hashlib.sha256(operation(A / 'op.raw')[1]).hexdigest(),
                   exact_header_equal_except_Date=True),
    all_reference_edges_exact=True, first_reference_threshold_crossing_s=first_reference,
    edge_observations=rows,
    actual_time_grids=[dict(rows=n['rows'], **n['time_grid']) for n in native],
    same_physical_device_graph=539,
    saved_screens=dict(both_strict_numerical_pass=True, old_pair_passed=False,
                      old_pair_status='FAIL_FINITE_NOMINAL_TIMESTEP_SCREEN'),
    solver_source=dict(
        authority='Upstream ngspice-47 source, version matched; no claim of direct binary instruction instrumentation or Debian source reproduction.',
        initial_delta='min(TSTOP/100,TSTEP)/10, then additional /10 at initial breakpoint, before later adaptive reductions',
        expected_initial_delta_s_for_old5ps=5e-14,
        expected_initial_delta_s_for_retained2p5ps=2.5e-14,
        expected_initial_delta_s_for_proposed_TSTEP2p5ps_TMAX1p25ps=2.5e-14,
        confounding='Historical pair changes TSTEP and TMAX simultaneously. TSTEP affects initial delta. TMAX also changes CKTdelmin, history seed and later adaptive steps, so the new proposal is a maximum-step refinement, not a claim of identical subsequent numerical grid.',
        saved_runtime_unchanged=True, method_option_not_explicitly_overridden=True),
    interpretation='Identical solved OP and reference waveform, but divider-chain edge differences already precede the first reference pulse. Numerical startup sensitivity is supported as a hypothesis; the saved4ns-window edges do not establish the first oscillator transition or uniquely prove the cause of the settled695ps offset. Original raw phase FAIL is unchanged.',
    proposal=dict(
        literal_only_change=['.tran 2.5e-12 1e-06 0 2.5e-12', '.tran 2.5e-12 1e-06 0 1.25e-12'],
        duration_s=1e-6, start_s=0, TSTEP_s=2.5e-12, TMAX_s=1.25e-12,
        fixed_windows_s=[[800e-9,900e-9],[900e-9,1e-6]],
        frequency_difference_limit_ppm=100, raw_matched_phase_difference_limit_s=50e-12,
        individual_frequency_limit_ppm=100, individual_phase_span_limit_s=50e-12,
        nearest_reference_ordinal_no_slip_required=True, offset_removal_or_retiming=False,
        other_required_gates='Same539devices, native-off startup checks and exactOP, strict numerics and all-device bounds, full endpoint/sample coverage, full lossless public replay and independent arithmetic.',
        predictor_work_estimate='At least800001 native rows for1us under1.25ps cap (adaptive points add rows),826columns, >=5.286GB uncompressed sample payload. Roughly twice existing401607-row work; no runtime guarantee.',
        resource_requirements='Unchanged CPU12,1GiB nativeAS,50MiB localcapture backpressure and512MiB shared freefloor, bounded publisherV3, unique prefix, no healthy timeout. Source reviewer and approximately320+ publicasset capacity required.',
        implementation_gate='Do not invoke frozen acquisitionV3 with unsupported1.25ps. Create separate versioned bridge accepting independent TSTEP/TMAX metadata, literal deck inverse and exact bounded method delta, include semantic mutation controls for TMAX omission/relaxed limits/wrongbaseline, then independent source/lifecycle review.',
        no_acceptance_from_short_probe='Any optional first20ns startup probe must be separately named and cannot satisfy1us acquisition orpairconvergence. A short probe changing onlyTSTEP at fixedTMAX could diagnose initial-grid sensitivity, but is not included in this proposed long-run acceptance.',
        action='Source-only proposal; no new solver launched. Preserve all prior failed and completed captures.'))
output = B / 'saved-startup-and-max125-proposal01.json'
assert not output.exists()
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(status=report['status'], output=pin(output), op=report['common_op'], proposal_deck=pin(B/'candidate-max125-source-only.cir'))))
