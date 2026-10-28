#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pure same-row diagnosis of authenticated saved CDR captures; never acceptance."""
import hashlib
import json
from pathlib import Path
import stat
import numpy as np
import cdr_v58_saved_rows as saved

SAVED_SHA = 'b98bdc27fddf3fa30e51da019491cf44772474dbcb308714eed9bf6b8a6d121f'
TARGET_IDS = (59, 60, 61, 62, 71, 72, 87, 88, 111, 112, 115, 116)
UI, START, STOP, STEP = 125e-12, 2e-9, 2e-9 + 258 * 125e-12, .3125e-12
MAX_ROWS, MAX_FRAMES, MAX_RUNS = 250000, 65536, 65536
MAX_FRAME_BYTES = 512 * 1024 * 1024
COUNTS = dict(npn13g2=124, sg13_lv_nmos=50, rppd=98, cap_cmim=7, ptap1=221)
EXTERNAL = ('cp', 'cn', 'dp', 'dn', 'xp', 'xn', 'yp', 'yn', 'vip', 'vin', 'avdd')
SCHEMA = 'cdr-v59-tail-headroom-rows-v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def name(ident):
    return 'xpd.xd' + str(ident).zfill(4)


def _node(node, interface):
    return ('0' if node in ('avss', 'sub', 'wire_cref') else node) if node in interface else 'xpd.' + node.lower()


def topology(report, contract):
    """Join the complete current composition, then select two anonymous-net hops."""
    assert hashlib.sha256(Path(saved.__file__).read_bytes()).hexdigest() == SAVED_SHA, 'Saved helper source changed'
    records = contract['device_records']
    assert len(records) == contract['counts']['devices'] == 500, 'Incomplete device census'
    interface = contract['interface']
    assert len(interface) == len(set(interface)) == 26, 'Invalid interface'
    assert report['binding']['ports'] == [_node(x,interface) for x in interface], 'Bound interface mismatch'
    groups = report['binding']['groups']
    assert {k: len(v) for k, v in groups.items()} == COUNTS, 'Incomplete bound census'
    assert report['devices'] == groups['npn13g2'] and report['mos_devices'] == groups['sg13_lv_nmos'], 'Bound device view mismatch'
    assert report['native_caps'] == groups['cap_cmim'], 'Bound capacitor view mismatch'
    byid, nets, terms = {}, {}, {}
    for rec in records:
        ident = rec['native_id']
        assert type(ident) is int and ident > 0 and ident not in byid, 'Duplicate/invalid native ID'
        assert rec['instance'] == name(ident)[4:].upper(), 'Native instance mismatch'
        model = rec['model']
        assert model in COUNTS, 'Unknown device model'
        tt = rec['terminals']
        labels = [x['terminal'] for x in tt]
        assert labels and len(labels) == len(set(labels)), 'Duplicate terminal'
        if model == 'npn13g2':
            assert labels == ['C', 'B', 'E', 'S'], 'HBT terminal order changed'
        if model == 'sg13_lv_nmos':
            assert labels == ['D', 'G', 'S', 'B'], 'MOS terminal order changed'
        dev = groups[model][name(ident)]
        assert type(dev['native_id']) is int and dev['native_id'] == ident, 'Bound native ID mismatch'
        assert dev['nodes'] == [_node(x['node'], interface) for x in tt], 'Terminal contact mismatch'
        assert dev['parameters'] == rec['parameters'], 'Device parameters mismatch'
        if model == 'npn13g2':
            assert type(dev['nx']) is int and dev['nx'] == int(rec['parameters']['nx']) > 0, 'Emitter multiplicity mismatch'
        for x in tt:
            assert type(x['native_cluster']) is int and x['native_cluster'] > 0 and type(x['native_net']) is str, 'Invalid native net'
            pair = (x['native_cluster'], x['native_net'])
            assert nets.setdefault(x['native_cluster'], x['native_net']) == x['native_net'], 'Conflicting native net name'
            assert type(x['node']) is str and x['node'], 'Invalid contact node'
        byid[ident] = rec
        terms[ident] = {x['terminal']: (x['native_cluster'], x['native_net']) for x in tt}
    assert set(byid) == {v['native_id'] for g in groups.values() for v in g.values()}, 'Incomplete composition join'
    assert all(byid[i]['model'] == 'npn13g2' for i in TARGET_IDS), 'Target model mismatch'
    assert [groups['npn13g2'][name(i)]['nx'] for i in TARGET_IDS] == [4,4,2,2,4,4,4,4,4,4,2,2], 'Target multiplicity changed'

    def anonymous(ident):
        return {v for k, v in terms[ident].items() if k in ('C', 'B', 'E') and v[1].startswith('$') and v[1] != '$1'}

    chosen = set(TARGET_IDS)
    connected = set().union(*(anonymous(i) for i in chosen))
    hops = []
    for _ in range(2):
        added = {i for i, rec in byid.items() if rec['model'] == 'npn13g2'
                 and any(v in connected for k, v in terms[i].items() if k in ('C', 'B', 'E'))}
        chosen |= added
        connected |= set().union(*(anonymous(i) for i in chosen))
        hops.append(sorted(chosen))
    mos = {i for i, rec in byid.items() if rec['model'] == 'sg13_lv_nmos' and terms[i]['D'] in connected}
    gates = {terms[i]['G'] for i in mos}
    references = {i for i, rec in byid.items() if rec['model'] == 'sg13_lv_nmos'
                  and terms[i]['D'] == terms[i]['G'] and terms[i]['G'] in gates}
    mos |= references
    passive = {i for i, rec in byid.items() if rec['model'] in ('rppd', 'cap_cmim')
               and any(v in connected for v in terms[i].values())}
    selected = sorted(chosen | mos | passive)
    selected_names = {'v(' + x + ')' for x in EXTERNAL}
    selected_names.update('v('+x+')' for x in report['binding']['ports'] if x != '0')
    selected_names.update('v(' + x + ')' for x in report['binding']['aliases'].values())
    for ident in selected:
        rec = byid[ident]
        dev = groups[rec['model']][name(ident)]
        selected_names.update('v(' + x + ')' for x in dev['nodes'] if x != '0')
        if rec['model'] == 'npn13g2':
            selected_names.add('@q.' + name(ident) + '.qnpn13g2[ic]')
        if rec['model'] == 'sg13_lv_nmos':
            selected_names.add('@n.' + name(ident) + '.nsg13_lv_nmos[ids]')
    assert selected_names <= set(report['vectors']), 'Missing selected vector'
    selected_tails = {}
    for key, members in report['binding']['mos_tail_groups'].items():
        assert members and len(members) == len(set(members)), 'Invalid tail membership'
        overlap = set(members) & {name(i) for i in mos}
        if overlap:
            assert overlap == set(members), 'Partial stage tail'
            selected_tails[key] = list(members)
    shared = {}
    for ident in selected:
        for term in byid[ident]['terminals']:
            pair = (term['native_cluster'], term['native_net'])
            if pair in connected:
                shared.setdefault(str(pair[0]), dict(native_net=pair[1], contacts=[]))['contacts'].append(
                    dict(native_id=ident, terminal=term['terminal'], vector='v(' + _node(term['node'], interface) + ')'))
    probes = {label: ['v('+p+')','v('+n+')'] for label,p,n in
              [('delivered_clock','cp','cn'),('delivered_data','dp','dn'),
               ('comparator_x','xp','xn'),('comparator_y','yp','yn'),('VI_output','vip','vin'),
               ('D_gain_LP_LN','xpd.w_t060_c','xpd.w_t059_c'),
               ('D_upper_master_bases','xpd.w_t054_b','xpd.w_t056_b'),
               ('C_gain_LP_LN','xpd.w_t112_c','xpd.w_t111_c'),
               ('C_upper_master_bases','xpd.w_t106_b','xpd.w_t108_b')]}
    for label in ('aq','bq','cq','dq','ad','cd','s0','s1'):
        probes[label] = ['v('+report['binding']['aliases']['xpd.'+label+s]+')' for s in ('p','n')]
    assert all(set(pair) <= selected_names for pair in probes.values()), 'Missing differential probe'
    assert terms[60]['C'] == terms[54]['B'] and terms[59]['C'] == terms[56]['B'], 'D gain/master topology mismatch'
    assert terms[112]['C'] == terms[106]['B'] and terms[111]['C'] == terms[108]['B'], 'C gain/master topology mismatch'
    return dict(differential_probes=probes,hbt_ids=sorted(chosen), mos_ids=sorted(mos), reference_mos_ids=sorted(references),
                passive_ids=sorted(passive), selected_device_ids=selected, two_hop_hbt_ids=hops,
                selected_vectors=sorted(selected_names), selected_stage_tails=selected_tails,
                shared_topology_nets=shared,
                selected_records=[byid[i] for i in selected],
                rule='Two complete C/B/E hops on anonymous native nets from all12targets; then drain-connected MOS, diode references, and passive endpoints. Supply/clock nets do not expand the graph.',
                shared_net_contacts_are_not_ideal_voltage_aliases=True)


def validate_input(t, d, report):
    assert isinstance(t, np.ndarray) and t.ndim == 1 and t.dtype.kind == 'f' and t.dtype.itemsize == 8, 'Invalid time array'
    assert 1 < len(t) <= MAX_ROWS, 'Capture row budget'
    vectors = report['vectors']
    assert all(type(x) is str for x in vectors) and len(vectors) == len(set(vectors)) == 1151, 'Invalid vector census'
    capture = report['raw_capture']
    order = capture['logical_vector_order']
    assert len(order) == len(set(order)) == 1152 and order[0] == 'time' and set(order[1:]) == set(vectors), 'Invalid capture vector order'
    assert list(d) == order[1:], 'Missing/extra/reordered vector'
    assert type(capture['header_rows']) is int and capture['header_rows'] == len(t) and capture['columns'] == 1152, 'Capture shape mismatch'
    assert np.isfinite(t).all() and np.all(np.diff(t) > 0), 'Invalid time ordering'
    assert t[0] == 0 and abs(t[-1] - STOP) < 1e-18, 'Shifted/incomplete time range'
    assert float(t[0]) == capture['start_s'] and float(t[-1]) == capture['end_s'], 'Capture endpoint mismatch'
    maximum = float(np.diff(t).max())
    assert maximum <= STEP * 1.00001 and maximum == capture['max_step_s'], 'Capture timestep mismatch'
    assert capture['complete_unmodified_rows'] is True, 'Incomplete capture'
    assert type(capture['raw_sha256']) is str and len(capture['raw_sha256']) == 64 and all(x in '0123456789abcdef' for x in capture['raw_sha256']), 'Invalid raw digest'
    assert type(capture['header_bytes']) is int and 0 < capture['header_bytes'] <= 1048576, 'Invalid native header size'
    assert capture['raw_bytes'] == capture['header_bytes'] + len(t) * 1152 * 8, 'Capture byte shape mismatch'
    for vector in order[1:]:
        arr = d[vector]
        assert isinstance(arr, np.ndarray) and arr.shape == t.shape and arr.dtype.kind == 'f' and arr.dtype.itemsize == 8, ('Invalid signal array', vector)
        assert np.isfinite(arr).all(), ('Nonfinite signal', vector)


def runs(indices):
    """Complete inclusive index runs, with no omitted equal extrema or violations."""
    indices = np.asarray(indices, dtype=np.int64)
    if not len(indices):
        return []
    cuts = np.flatnonzero(np.diff(indices) != 1) + 1
    chunks = np.split(indices, cuts)
    assert len(chunks) <= MAX_RUNS, 'Index run budget'
    return [dict(first_row=int(x[0]), last_row=int(x[-1]), count=len(x)) for x in chunks]


def spans(t, vce, indices):
    result = []
    for block in runs(indices):
        a, b = block['first_row'], block['last_row']
        result.append(dict(**block, first_s=float(t[a]), last_s=float(t[b]),
                           sampled_duration_s=float(t[b] - t[a]),
                           first_signed_vce_v=float(vce[a]), last_signed_vce_v=float(vce[b]),
                           previous_row=None if a == 0 else a-1,
                           next_row=None if b+1 == len(t) else b+1,
                           left_capture_censored=a == 0, right_capture_censored=b+1 == len(t),
                           threshold_crossing_interpolation=False))
    return result


def same_row(row, d, report, topo):
    def voltage(node):
        return 0. if node == '0' else float(d['v('+node+')'][row])
    hbts, mos, passive = {}, {}, {}
    for ident in topo['hbt_ids']:
        key=name(ident);dev=report['devices'][key]
        c,b,e,s=map(voltage,dev['nodes']);ic=float(d['@q.'+key+'.qnpn13g2[ic]'][row])
        hbts[key]=dict(C_v=c,B_v=b,E_v=e,S_v=s,VCE_v=c-e,VBE_v=b-e,Ic_a=ic,Ic_per_emitter_a=ic/dev['nx'])
    for ident in topo['mos_ids']:
        key=name(ident);dev=report['mos_devices'][key]
        vd,vg,vs,vb=map(voltage,dev['nodes'])
        mos[key]=dict(D_v=vd,G_v=vg,S_v=vs,B_v=vb,VDS_v=vd-vs,VGS_v=vg-vs,VGD_v=vg-vd,
                      Ids_a=float(d['@n.'+key+'.nsg13_lv_nmos[ids]'][row]))
    for rec in topo['selected_records']:
        if rec['native_id'] in topo['passive_ids']:
            key=name(rec['native_id']);dev=report['binding']['groups'][rec['model']][key]
            a,b=map(voltage,dev['nodes'][:2])
            passive[key]=dict(nodes=dev['nodes'][:2],first_v=a,second_v=b,first_minus_second_v=a-b,
                              current_inferred=False)
    shared={}
    for cluster,net in topo['shared_topology_nets'].items():
        contacts=net['contacts'];reference=contacts[0]['vector'];rv=float(d[reference][row])
        shared[cluster]=dict(native_net=net['native_net'],reference_vector=reference,
                            contact_minus_reference_v={x['vector']:float(d[x['vector']][row])-rv for x in contacts})
    return dict(hbt=hbts,mos=mos,passive=passive,
                differential_v={k:float(d[p][row])-float(d[n][row]) for k,(p,n) in topo['differential_probes'].items()},
                stage_tail_current_a={k:sum(mos[n]['Ids_a'] for n in members) for k,members in topo['selected_stage_tails'].items()},
                distinct_shared_net_contact_drops=shared)


def diagnostic(t, d, report, contract):
    validate_input(t, d, report)
    topo = topology(report, contract)
    active = np.flatnonzero(t >= START)
    assert len(active), 'Empty original active mask'
    planned, witnesses, windows = set(), {}, {}
    total_runs = 0

    def adjacent(row):
        planned.update(range(max(0, row-1), min(len(t), row+2)))

    def fixed_window(row):
        # Original START/UI grid, not a fitted event or observed-clock phase.
        grid = START + np.arange(-16, 260, dtype=np.float64) * UI
        grid_index = int(np.searchsorted(grid, t[row], side='right') - 1)
        assert 0 <= grid_index < len(grid)-1, 'Extremum outside UI grid'
        ui_index = grid_index - 16
        requested = [START + (ui_index-1) * UI, START + (ui_index+2) * UI]
        lo, hi = max(0., requested[0]), min(float(t[-1]), requested[1])
        ids = np.flatnonzero((t >= lo) & (t <= hi))
        assert len(ids), 'Empty fixed window'
        planned.update(map(int, ids))
        adjacent(int(ids[0])); adjacent(int(ids[-1]))
        windows[ui_index] = dict(ui_index=ui_index, original_boundary_s=START+ui_index*UI,
                                offsets_ui=[-1,2], requested_s=requested, retained_s=[lo,hi],
                                clipped_at_capture=[lo != requested[0], hi != requested[1]],
                                first_row=int(ids[0]), last_row=int(ids[-1]), rows=len(ids),
                                every_native_row_in_window=True)

    for ident in TARGET_IDS:
        key = name(ident)
        dev = report['devices'][key]
        vc, vb, ve = [d['v(' + x + ')'] for x in dev['nodes'][:3]]
        current = d['@q.' + key + '.qnpn13g2[ic]']
        vce = vc - ve
        replay = dict(minimum_active_vce_v=float(vce[active].min()),
                      maximum_alltime_abs_vce_v=float(np.abs(vce).max()),
                      maximum_alltime_abs_vbe_v=float(np.abs(vb-ve).max()),
                      maximum_alltime_abs_ic_per_emitter_a=float(np.abs(current).max()/dev['nx']))
        assert replay == report['device_checks'][key], ('Original HBT scalar mismatch', key)
        extremes = {}
        for label, indices, value in [
            ('minimum_active_vce', active[vce[active] == replay['minimum_active_vce_v']], replay['minimum_active_vce_v']),
            ('maximum_alltime_abs_vce', np.flatnonzero(np.abs(vce) == replay['maximum_alltime_abs_vce_v']), replay['maximum_alltime_abs_vce_v'])]:
            tie_runs = runs(indices)
            total_runs += len(tie_runs)
            first, last = int(indices[0]), int(indices[-1])
            for block in tie_runs:
                adjacent(block['first_row']); adjacent(block['last_row'])
            # Fixed full windows at first and last equal extrema; all other ties
            # remain complete in tie_runs and have adjacent boundary rows.
            for row in {first,last}:
                fixed_window(row)
            extremes[label] = dict(value_v=value, tie_count=len(indices), tie_runs=tie_runs,
                                   primary_tie_policy='first native row; last and every tie-run boundary retained',
                                   first=saved.hbt_point(t,d,first,key,dev),
                                   last=saved.hbt_point(t,d,last,key,dev),
                                   first_simultaneous=same_row(first,d,report,topo),
                                   last_simultaneous=same_row(last,d,report,topo),
                                   first_active=bool(t[first] >= START), last_active=bool(t[last] >= START))
        violations = dict(minimum_active_vce_below_0p4=spans(t,vce,active[vce[active] < .4]),
                          maximum_alltime_abs_vce_above_1p6=spans(t,vce,np.flatnonzero(np.abs(vce) > 1.6)))
        for blocks in violations.values():
            total_runs += len(blocks)
            for block in blocks:
                adjacent(block['first_row']); adjacent(block['last_row'])
        witnesses[key] = dict(native_id=ident, original_scalar_replay=replay, extrema=extremes, violation_spans=violations)
    assert total_runs <= MAX_RUNS, 'Aggregate index run budget'
    frame_rows = sorted(planned)
    assert len(frame_rows) <= MAX_FRAMES, 'Frame row budget'
    assert len(frame_rows)*(len(topo['selected_vectors'])+2)*8 <= MAX_FRAME_BYTES, 'Frame byte budget'
    return dict(schema=SCHEMA, status='SAVED_CAPTURE_DIAGNOSTIC_ONLY',
                target_ids=list(TARGET_IDS), selected_vectors=topo['selected_vectors'], frame_rows=frame_rows,
                topology=topo, devices=witnesses, fixed_windows=[windows[i] for i in sorted(windows)],
                original_capture=report['raw_capture'],
                time_float64_le_sha256=digest(np.asarray(t,dtype='<f8').tobytes()),
                report_canonical_sha256=digest(canonical(report)), contract_canonical_sha256=digest(canonical(contract)),
                limits=dict(minimum_active_vce_v=.4, maximum_alltime_abs_vce_v=1.6,
                            maximum_alltime_abs_vbe_v=1., maximum_alltime_abs_ic_per_emitter_a_exclusive=.003,
                            original_active_start_s=START, sampler_clock_to_valid_s=.3*UI, comparator_clock_to_valid_s=.6*UI),
                retained_same_row_quantities='Every selected terminal voltage and saved HBT Ic/MOS Ids; shared contacts distinct. Stage currents must be summed at the same row.',
                omitted_capture_quantities=['HBT base/emitter currents','MOS gate/body currents','resistor current vectors','unsaved internal wire RC vertices','source-side cp0/cn0/dp0/dn0 voltages','thermal states'],
                bounds=dict(maximum_rows=MAX_ROWS,maximum_frames=MAX_FRAMES,maximum_index_runs=MAX_RUNS,maximum_frame_bytes=MAX_FRAME_BYTES),
                original_full_measurement_replay_required_separately=True,
                native_archive_and_raw_hash_admission_required_separately=True,
                interpolation_for_new_diagnostic=False, original_measurement_interpolation_unchanged=True,
                clock_rephasing=False, new_simulation=False, cause_established=False,
                electrical_accepted=False, cdr_accepted=False, full_phy_accepted=False)


def verify_frames(path, t, d, diagnosis, proof):
    path = Path(path)
    assert stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink(), 'Nonregular frame file'
    rows, names = diagnosis['frame_rows'], diagnosis['selected_vectors']
    columns = ['native_row', 'time', *names]
    assert proof['columns'] == columns and proof['frame_rows'] == rows and proof['dtype'] == '<f8', 'Frame schema mismatch'
    assert proof['rows'] == len(rows) and proof['bytes'] == len(rows)*len(columns)*8 == path.stat().st_size, 'Partial/extra frame bytes'
    with path.open('rb') as src:
        assert hashlib.file_digest(src, 'sha256').hexdigest() == proof['sha256'], 'Frame digest mismatch'
    mm = np.memmap(path, mode='r', dtype='<f8', shape=(len(rows),len(columns)))
    try:
        for first in range(0,len(rows),256):
            ids = np.asarray(rows[first:first+256],dtype=np.int64)
            expected = np.column_stack([ids,t[ids],*[d[n][ids] for n in names]]).astype('<f8',copy=False)
            assert mm[first:first+len(ids)].tobytes() == expected.tobytes(), 'Frame changed native float64 bits'
    finally:
        del mm


def write_frames(path, t, d, diagnosis, report, contract):
    """Exclusive binary writer; failed partial bytes remain, never a success proof."""
    assert canonical(diagnostic(t,d,report,contract)) == canonical(diagnosis), 'Stale/modified diagnosis'
    path = Path(path)
    assert not path.exists() and not path.is_symlink(), 'Frame destination exists'
    assert all(not p.is_symlink() for p in [path.parent,*path.parent.parents]), 'Symlink frame parent'
    rows, names = diagnosis['frame_rows'], diagnosis['selected_vectors']
    assert rows and all(type(i) is int and 0 <= i < len(t) < 2**53 for i in rows), 'Invalid frame row'
    assert rows == sorted(set(rows)), 'Duplicate/unordered frame row'
    columns = ['native_row','time',*names]
    h = hashlib.sha256()
    with path.open('xb') as out:
        for first in range(0,len(rows),256):
            ids = np.asarray(rows[first:first+256],dtype=np.int64)
            block = np.column_stack([ids,t[ids],*[d[n][ids] for n in names]]).astype('<f8',copy=False).tobytes()
            assert out.write(block) == len(block), 'Short frame write'
            h.update(block)
    proof = dict(schema='cdr-v59-tail-headroom-frame-matrix-v1',columns=columns,frame_rows=rows,
                 rows=len(rows),bytes=len(rows)*len(columns)*8,sha256=h.hexdigest(),dtype='<f8',
                 native_row_encoding='exact float64 integer, bounded below 2**53',
                 diagnosis_sha256=digest(canonical(diagnosis)),complete=False,
                 interpolation=False,electrical_accepted=False,cdr_accepted=False,full_phy_accepted=False)
    verify_frames(path,t,d,diagnosis,proof)
    proof['complete'] = True
    return proof
