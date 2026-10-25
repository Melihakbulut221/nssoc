#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only same-row observer for completed rejected normal TX 40168554741.

No simulator, continuation, source alteration or acceptance override. A future
reviewed cloud restoration controller must authenticate the complete seven-part
archive before invoking this module. No workflow is registered by this proposal.
"""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
UI, START, STOP = 125e-12, 2e-9, 34e-9
PHASES = (.3, .5, .7)
RESULT = 'docs/evidence/tx-normal-complete-rejected-result-20261025.json'
ROLES = 'docs/evidence/tx-canonical-clock-role-full-result-20261024.json'
METHOD = 'scripts/tx-normal-saved-capture-diagnosis-methods.json'

def digest(b):
    return hashlib.sha256(b).hexdigest()

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False)

def pin(path, expected):
    b = Path(path).read_bytes()
    assert digest(b) == expected, ('Changed authenticated source/input', str(path))
    return b

def frozen_functions(pins):
    # Compile only these exact, hash-checked pure functions; no producer main.
    env = dict(np=np, hashlib=hashlib, START=START, UI=UI, STOP=STOP, BITS=256)
    for path, names in [
        ('scripts/cloud_tx_data_driver.py', ['original_bit_output_screen']),
        ('scripts/cloud_tx_p4_drive3_builder.py',
         ['sequence', 'tree_plan', 'interface_screen', 'prestage_bias_currents', 'review'])]:
        raw = pin(ROOT/path, pins[path]); tree = ast.parse(raw)
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        assert {n.name for n in nodes} == set(names) and len(nodes) == len(names)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), path+'#frozen', 'exec'), env)
    pin(ROOT/'scripts/cloud_tx_stream.py', pins['scripts/cloud_tx_stream.py'])
    return env

def bracket(t, at):
    assert t.ndim == 1 and len(t) >= 2 and np.isfinite(t).all()
    assert np.all(np.diff(t) > 0) and np.isfinite(at) and t[0] <= at <= t[-1]
    j = int(np.searchsorted(t, at, side='left'))
    if j < len(t) and t[j] == at:
        a = b = j
    else:
        assert 0 < j < len(t)
        a, b = j-1, j
    return dict(left_row=a, right_row=b, left_time_s=float(t[a]),
                right_time_s=float(t[b]), requested_s=float(at),
                native_step_s=float(t[b]-t[a]), exact_native_row=a == b)

def point(t, values, name, row):
    assert 0 <= row < len(t)
    if name == '0':
        return 0.
    v = values['v('+name+')']
    assert len(v) == len(t) and np.isfinite(v[row])
    return float(v[row])

def hbt_point(t, values, name, spec, row):
    assert spec['model'] == 'npn13g2' and 1 <= spec['nx'] <= 10
    assert len(spec['terminals']) == 4
    c, b, e, sub = [point(t, values, n, row) for n in spec['terminals']]
    key = '@q.'+name+'.qnpn13g2[ic]'
    ic = float(values[key][row]); assert np.isfinite(ic)
    return dict(row=int(row), time_s=float(t[row]), terminals=spec['terminals'],
                collector_v=c, base_v=b, emitter_v=e, substrate_v=sub,
                vce_v=c-e, vbe_v=b-e, native_ic_a=ic,
                nx=spec['nx'], ic_per_emitter_a=ic/spec['nx'],
                thermal_state=None, thermal_status='NOT_SAVED_IN_ORIGINAL_CAPTURE')

def native_pairs(t, values, positives, negatives, row, sign):
    assert sign in (-1, 1) and len(positives) == len(negatives)
    assert len(positives) in (1, 3)
    assert len(set(positives+negatives)) == len(positives+negatives)
    out = []
    for p in positives:
        for n in negatives:
            pv, nv = point(t, values, p, row), point(t, values, n, row)
            out.append(dict(positive=p, negative=n, positive_v=pv, negative_v=nv,
                            signed_margin_v=(pv-nv)*sign, common_mode_v=(pv+nv)/2))
    return out

def groups(contract, bit):
    assert 0 <= bit < 256
    mapping = contract['interface_probes']
    labels = [('cmos', 'd'+str(bit % 32)), ('level_16', 'p16_'+str(bit % 16)),
              ('level_8', 'p8_'+str(bit % 8)), ('level_4', 'p4_'+str(bit % 4)),
              ('final', 'a' if bit % 2 == 0 else 'b')]
    return [(stage, mapping[prefix+'p'], mapping[prefix+'n']) for stage, prefix in labels] + [
        ('tx_output', ['op'], ['on'])]

def probe_inventory(contract):
    """Refuse any unavailable requested probe before the expensive frozen review."""
    mapping = contract['interface_probes']
    prefixes = ['d'+str(i) for i in range(32)] + ['p16_'+str(i) for i in range(16)]
    prefixes += ['p8_'+str(i) for i in range(8)] + ['p4_'+str(i) for i in range(4)] + ['a', 'b']
    assert set(mapping) == {p+s for p in prefixes for s in ('p', 'n')}
    assert all(len(v) == len(set(v)) == 3 for v in mapping.values())
    assert len({n for v in mapping.values() for n in v}) == 372
    vectors = contract['vectors']; available = set(vectors)
    assert len(vectors) == len(available)
    assert not {'v(mp)', 'v(mn)'} & available, 'Stale schematic output probes are not physical8088 public ports'
    requested = set(); per_bit = []
    for bit in range(256):
        rows = groups(contract, bit)
        assert [r[0] for r in rows] == ['cmos', 'level_16', 'level_8', 'level_4', 'final', 'tx_output']
        for stage, pp, nn in rows:
            assert len(pp) == len(nn) == (1 if stage == 'tx_output' else 3)
            assert len(set(pp+nn)) == len(pp+nn)
            requested.update('v('+n+')' for n in pp+nn)
        per_bit.append([r[0] for r in rows])
    clocks = contract['tree_plan']['clocks']
    expected_clocks = {p+str(i) for p,n in [('sp16_',16), ('sp8_',8), ('sp4_',4)] for i in range(n)} | {'sa','sb','s'}
    assert len(clocks) == 31 and {c['name'] for c in clocks} == expected_clocks
    requested.update('v('+c['name']+s+')' for c in clocks for s in ('p','n'))
    for name, spec in contract['hbt'].items():
        assert spec['model'] == 'npn13g2' and len(spec['terminals']) == 4
        requested.update('v('+n+')' for n in spec['terminals'] if n != '0')
        requested.add('@q.'+name+'.qnpn13g2[ic]')
    assert requested <= available, ('Missing requested diagnostic probes', sorted(requested-available))
    return dict(status='ALL_REQUESTED_DIAGNOSTIC_PROBES_PRESENT_BEFORE_FROZEN_REVIEW',
        all_256_bit_group_sets_checked=len(per_bit), stages_per_bit=per_bit[0],
        physical_interface_legs=len(mapping), public_clock_pairs=len(clocks),
        observed_hbt_count=len(contract['hbt']), requested_vector_count=len(requested),
        requested_vectors=sorted(requested), actual_interface_probes=mapping,
        public_clock_source_records=clocks, unavailable_diagnostics={
            'mux_output_diagnostic_only': dict(available=False, historical_public_nodes=['mp','mn'],
                reason='Exact physical8088 adapter removes these public ports and saved vectors when output14 is absorbed into the parent. Internal output-handoff roles are not separately bound by this diagnostic; no waveform alias is inferred.')})


def replay_receipt(actual, recorded):
    actual_sha = digest(canonical(actual).encode()); expected_sha = digest(canonical(recorded).encode())
    assert actual_sha == expected_sha and canonical(actual) == canonical(recorded)
    assert not actual['all_engineering_gates_passed']
    return dict(status='FROZEN_ORIGINAL_ELECTRICAL_REJECTION_REPRODUCED_BEFORE_DIAGNOSTICS',
        actual_review_canonical_sha256=actual_sha, recorded_review_canonical_sha256=expected_sha,
        full_original_review_replays=1, capture_transport=actual['capture_transport'],
        failed_hbt_count=len(actual['failed_hbts']), failed_mos_count=len(actual['failed_mos']),
        signals=actual['signals'], original_acceptance=False, new_simulation=False)


def stages_at(t, values, contract, bit, row):
    sign = 2*contract['bits'][bit]-1
    return {stage: native_pairs(t, values, p, n, row, sign)
            for stage, p, n in groups(contract, bit)}

def admitted_window(t, lo, hi):
    """Clip only diagnostic last-UI extent to an originally admitted endpoint."""
    assert np.isfinite([lo, hi, t[0], t[-1]]).all() and t[0] <= lo <= hi
    scan_hi = min(float(t[-1]), hi)
    if scan_hi != hi:
        assert abs(t[-1]-STOP) < 1e-18 and abs(hi-STOP) < 1e-18
        assert 0 < hi-scan_hi < 1e-18
    assert lo <= scan_hi
    return dict(requested_UI_bounds_s=[float(lo), float(hi)],
                native_scan_bounds_s=[float(lo), float(scan_hi)],
                admitted_endpoint_clipped=scan_hi != hi)

def crossing_brackets(t, y, level, lo, hi):
    assert y.shape == t.shape and np.isfinite(y).all()
    assert np.isfinite(level) and t[0] <= lo <= hi <= t[-1]
    ids = np.flatnonzero(((y[:-1] < level) != (y[1:] < level)) &
                        (t[:-1] <= hi) & (t[1:] >= lo))
    return [dict(left_row=int(i), right_row=int(i+1), left_time_s=float(t[i]),
                 right_time_s=float(t[i+1]), left_value=float(y[i]), right_value=float(y[i+1]),
                 threshold=float(level), before_below=bool(y[i] < level),
                 after_below=bool(y[i+1] < level)) for i in ids]

def bit_context(at):
    assert np.isfinite(at)
    if not START <= at < STOP:
        return None
    bit = int(np.floor((at-START)/UI))
    assert 0 <= bit < 256
    return bit

def below_segments(t, y, threshold, start):
    assert t.shape == y.shape and np.isfinite(y).all()
    active = np.flatnonzero(t >= start)
    ids = np.flatnonzero((t >= start) & (y < threshold))
    if not len(ids):
        return []
    def boundary(a, b, censored):
        return dict(rows=[int(a),int(b)], times_s=[float(t[a]),float(t[b])],
                    values=[float(y[a]),float(y[b])], threshold=float(threshold),
                    native_threshold_transition=bool((y[a] < threshold) != (y[b] < threshold)),
                    censored_by_observation_window=bool(censored))
    chunks = np.split(ids, np.flatnonzero(np.diff(ids) != 1)+1)
    return [dict(first_row=int(g[0]), last_row=int(g[-1]), samples=len(g),
                 first_time_s=float(t[g[0]]), last_time_s=float(t[g[-1]]),
                 entry=boundary(max(0,int(g[0])-1),int(g[0]),g[0]==active[0]),
                 exit=boundary(int(g[-1]),min(len(t)-1,int(g[-1])+1),g[-1]==len(t)-1),
                 sampled_span_s=float(t[g[-1]]-t[g[0]]),
                 sampled_span_is_not_exact_threshold_dwell=True) for g in chunks]

def catalog(contract, qualified):
    assert qualified['native_role_accepted'] is True and qualified['electrical_accepted'] is False
    assert qualified['qualified_input_hashes']['composed/output8088-wire.spice'] == '8286d54832432603f78739f30d0087e99a46f026d82a37ecd5e450d2167231c8'
    binding = qualified['binding']; assert not binding['canonical_mismatches']
    assert binding['canonical_counts'] == dict(muxes=31, HBTs=589, emitters=863)
    rows = {}; blocks = binding['all589_actual_devices']
    assert len(blocks) == 31
    for block in blocks:
        assert len(block['devices']) == 19
        for device in block['devices']:
            name = 'xtree.'+device['instance'].lower()
            assert name not in rows and name in contract['hbt']
            assert device['native_id'] == int(device['instance'][2:])
            terms = device['composed_terminals']
            assert [v['terminal'] for v in terms] == ['C', 'B', 'E', 'S']
            spec = contract['hbt'][name]
            assert spec['model'] == device['model'].lower() == 'npn13g2'
            assert spec['nx'] == device['parameters']['nx']
            assert spec['terminals'] == ['xtree.'+v['node'].lower() for v in terms]
            rows[name] = dict(macro=block['label'], kind=block['kind'], clock=block['clock'],
                              role=device['role'], bank=device['bank'], clock_leg=device['clock_leg'],
                              native_id=device['native_id'], native_clusters=device['native_clusters'],
                              parameters=device['parameters'], terminals=terms)
    assert len(rows) == 589
    return rows

def clock_at(t, values, contract, roles, names, row):
    clocks = {c['name']: c for c in contract['tree_plan']['clocks']}
    out = {}
    for name in sorted(set(names)):
        c = clocks[name]; p, n = [point(t, values, name+s, row) for s in ('p', 'n')]
        base = {}
        for device, role in roles.items():
            if role['clock'] == name and role['role'] == 'selector':
                leg = role['clock_leg']; assert leg in (name+'p', name+'n')
                actual = point(t, values, contract['hbt'][device]['terminals'][1], row)
                public = p if leg.endswith('p') else n
                base[device] = dict(clock_leg=leg, native_base_v=actual, public_minus_base_v=public-actual)
        assert len(base) == 4
        out[name] = dict(public_p_v=p, public_n_v=n, differential_v=p-n, common_mode_v=(p+n)/2,
                         source_origin_s=c['origin'], source_half_period_s=c['period'],
                         source_transition_index=float((t[row]-c['origin'])/c['period']),
                         selector_bases=base)
    return out

def analyze(t, values, contract, original, qualified):
    """Only call after full original review and immutable input authentication."""
    assert len(t) == 77681 and set(values) == set(contract['vectors'])
    assert len(values) == 14181 and len(contract['hbt']) == 604 and len(contract['mos']) == 5376
    assert contract['fault'] == 'none' and contract['streams'] == 32
    assert original['signals']['wrong_sign_samples'] == 14 and original['signals']['below_100mv_samples'] == 30
    assert len(original['failed_hbts']) == 76 and not original['failed_mos'] and not original['all_engineering_gates_passed']
    roles = catalog(contract, qualified)
    failed = original['failed_hbts']; assert 'xtree.xd5676' in failed
    active = np.flatnonzero(t >= START); assert len(active)
    hbts = {}; frames = {}
    def frame(row, bit):
        key = str(row)+':'+str(bit)
        if key not in frames:
            assert bit is None or 0 <= bit < 256
            valid = bool(START <= t[row] < STOP)
            assert valid or bit is None
            clocks = ([c['name'] for c in contract['tree_plan']['clocks']] if bit is None else
                      ['sp16_'+str(bit % 16), 'sp8_'+str(bit % 8), 'sp4_'+str(bit % 4),
                       'sa' if bit % 2 == 0 else 'sb', 's'])
            frames[key] = dict(row=int(row), time_s=float(t[row]), oracle_bit_index=bit,
                ui_position=float((t[row]-START)/UI),
                within_original_bit_window=valid,
                expected_source_bit=None if bit is None else contract['bits'][bit],
                bit_label_scope='No expected bit, sign or signed-stage diagnostic outside [START,STOP)',
                stages=None if bit is None else stages_at(t, values, contract, bit, row),
                clocks=clock_at(t, values, contract, roles, clocks, row),
                affected_hbts={n:hbt_point(t, values, n, contract['hbt'][n], row) for n in failed},
                measured_bias_currents={k:float(v[row]) for k,v in values.items() if k.startswith('i(')})
        return key
    for name in failed:
        spec = contract['hbt'][name]
        c, b, e, sub = [np.zeros_like(t) if n == '0' else values['v('+n+')'] for n in spec['terminals']]
        ce, be, ic = c-e, b-e, values['@q.'+name+'.qnpn13g2[ic]']/spec['nx']
        indices = dict(min_post_vce_v=int(active[np.argmin(ce[active])]),
                       max_post_vce_v=int(active[np.argmax(ce[active])]),
                       max_whole_abs_vce_v=int(np.argmax(abs(ce))),
                       max_whole_abs_vbe_v=int(np.argmax(abs(be))),
                       max_whole_abs_ic_per_emitter_a=int(np.argmax(abs(ic))))
        extrema = {}
        for key, row in indices.items():
            measured = ce[row] if key in ('min_post_vce_v', 'max_post_vce_v') else abs(
                ce[row] if key == 'max_whole_abs_vce_v' else be[row] if key == 'max_whole_abs_vbe_v' else ic[row])
            assert float(measured) == original['hbt_devices'][name][key]
            witness = hbt_point(t, values, name, spec, row)
            bit = bit_context(t[row])
            witness['frame'] = frame(row, bit)
            if name in roles:
                macro = roles[name]['macro']
                witness['same_macro_devices'] = {n:hbt_point(t,values,n,contract['hbt'][n],row)
                    for n,r in roles.items() if r['macro'] == macro}
                assert len(witness['same_macro_devices']) == 19
            extrema[key] = witness
        hbts[name] = dict(topology=roles.get(name), topology_status='BOUND_CANONICAL_TREE' if name in roles else
                         'FULL_OUTPUT_COMPOSITION_ROLE_NOT_YET_BOUND', extrema=extrema,
                         below_400mv_segments=below_segments(t,ce,.4,START))
    times = START+(np.arange(256)[:,None]+np.asarray(PHASES))*UI
    margin = (np.interp(times,t,values['v(op)'])-np.interp(times,t,values['v(on)']))*(2*np.asarray(contract['bits'])[:,None]-1)
    assert int((margin <= 0).sum()) == 14 and int((margin < .1).sum()) == 30
    assert float(margin.min()) == original['signals']['minimum_margin_v']
    events = []
    for bit, phase_index in np.argwhere(margin < .1):
        bit, phase_index = int(bit), int(phase_index)
        at = float(times[bit,phase_index]); b = bracket(t,at)
        events.append(dict(bit_index=bit, phase=PHASES[phase_index], source_bit=contract['bits'][bit],
            original_interpolated_margin_v=float(margin[bit,phase_index]), bracket=b,
            native_frames=[frame(row,bit) for row in dict.fromkeys([b['left_row'],b['right_row']])]))
    crossings = {}
    for bit in sorted({e['bit_index'] for e in events}):
        lo, hi = START+bit*UI, START+(bit+1)*UI; sign=2*contract['bits'][bit]-1
        window = admitted_window(t,lo,hi); scan_hi = window['native_scan_bounds_s'][1]
        group_rows = {}
        for stage, pp, nn in groups(contract,bit):
            for p in pp:
                for n in nn:
                    y=(values['v('+p+')']-values['v('+n+')'])*sign
                    group_rows[stage+':'+p+':'+n] = {str(level):crossing_brackets(t,y,level,lo,scan_hi)
                        for level in (0.,.1,.15)}
        crossings[str(bit)] = dict(**window, physical_pair_crossings=group_rows)
    return dict(status='DIAGNOSIS_ONLY_ORIGINAL_ELECTRICAL_REJECTION_REMAINS', accepted=False,
        original_rejection_reproduced=True, new_simulation=False, fitted_phase=False,
        unavailable_diagnostics=probe_inventory(contract)['unavailable_diagnostics'],
        thermal_state_available=False, thermal_reason='No thermal state vector was saved by the original 14181-vector contract.',
        original_sample_interpolation=True, diagnostic_crossing_interpolation=False,
        failed_sample_events=events, failed_hbt_same_row_witnesses=hbts, frames=frames,
        native_crossing_brackets_by_original_UI=crossings,
        unmapped_full_output_devices=sorted(set(failed)-set(roles)),
        conclusions_not_established=['causality', 'complete macro terminal KCL', 'thermal state',
                                     'circuit repair', 'full31 clock tree', 'full PHY', 'mainchip timing'])

def observe_restored(run, method, emit):
    """Future hosted-only entry. Disabled until restoration/controls review."""
    import os
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    assert method['readback_authorized'] is True
    pins = method['protected_files']
    for path, expected in pins.items():
        pin(ROOT/path, expected)
    result = json.loads(pin(ROOT/RESULT, method['source_summary_sha256']))
    qualified = json.loads(pin(ROOT/ROLES, method['qualified_roles_sha256']))
    assert result['status'] == 'REJECTED_ACTUAL8088_BRANCHTAILFEED_ORIGINAL_LOADED_GATES'
    assert result['full_capture'] and not result['native_process_saved'] and result['sources_unchanged']
    assert not result['electrical_screen_passed'] and not result['diagnostics']
    assert result['run_id'] == 40168554741 and result['case'] == 'none' and result['native_exit_code'] == 0
    assert result['controller_sha256'] == method['original_controller_sha256']
    # The cloud restoration controller must independently verify archive membership
    # and every original output. This helper pins each consumed member again.
    for name in ('bench.cir','contract.json','native.log','op.dat'):
        pin(run/name, result['outputs']['work/'+name])
    contract = json.loads((run/'contract.json').read_bytes())
    frozen = frozen_functions(pins)
    assert contract['bits'] == frozen['sequence']()
    assert contract['tree_plan']['nodes'] == frozen['tree_plan'](32)['nodes']
    assert len(contract['tree_plan']['clocks']) == 31
    emit('diagnostic-probe-inventory.json', probe_inventory(contract))
    original = frozen['review'](run,contract)
    assert canonical(original) == canonical(result['review']), 'Original full electrical rejection not exactly reproduced'
    emit('original-review-replay.json', replay_receipt(original, result['review']))
    from cloud_tx_stream import read_streamed_wave
    t, values, transport = read_streamed_wave(run/'wave.raw',contract['vectors'],STOP,contract['condition']['step_ps']*1e-12)
    assert transport == original['capture_transport']
    assert transport['raw_sha256'] == result['outputs']['work/wave.raw'] == method['raw_sha256']
    return analyze(t,values,contract,original,qualified)
