#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact physical terminal bindings and chunked voltage envelopes; never safety approval."""
import copy
from itertools import combinations
import numpy as np

def binding(composition, coverage, table):
    assert table[0] == ['0', 'time', 'time']
    assert [r[0] for r in table] == list(map(str, range(len(table))))
    assert len({r[1] for r in table}) == len(table)
    columns = {r[1]: (int(r[0]), r[2]) for r in table}
    external = coverage['external_mapping']
    def expected(node):
        return (None if external[node] == '0' else 'v(' + external[node].lower() + ')') if node in external else 'v(xloop.' + node.lower() + ')'
    def index(node, vector):
        assert vector == expected(node), ('Physical node/probe mismatch', node, vector)
        if vector is None:
            assert node in external and external[node] == '0'
            return -1
        assert vector in columns and columns[vector][1] == 'voltage', ('Missing physical voltage', vector)
        return columns[vector][0]
    records = composition['device_records']
    assert len({d['instance'] for d in records}) == len(records)
    assert len({d['native_id'] for d in records}) == len(records)
    probes = coverage['native_terminal_probes']
    keyed = {(p['instance'], p['terminal']): p for p in probes}
    assert len(keyed) == len(probes)
    want = {(d['instance'], t['terminal']) for d in records for t in d['terminals']}
    assert set(keyed) == want
    specs = []
    def add(instance, model, terminals, indices, auxiliary=False):
        for term, col in zip(terminals, indices, strict=True):
            specs.append(dict(instance=instance, model=model, kind='terminal', positive=term,
                              negative='global_zero', left=col, right=-1, auxiliary=auxiliary))
        for a, b in combinations(range(len(terminals)), 2):
            specs.append(dict(instance=instance, model=model, kind='difference', positive=terminals[a],
                              negative=terminals[b], left=indices[a], right=indices[b], auxiliary=auxiliary))
    for d in records:
        terms = d['terminals']
        assert terms and len({t['terminal'] for t in terms}) == len(terms)
        indices = []
        for t in terms:
            p = keyed[d['instance'], t['terminal']]
            assert all(p[k] == d[k] for k in ('instance', 'native_id', 'model'))
            assert p['node'] == t['node'] and p['explicit_zero_reference'] == (p['vector'] is None)
            indices.append(index(t['node'], p['vector']))
        add(d['instance'], d['model'], [t['terminal'] for t in terms], indices)
    aux = composition['auxiliary_contact_models']
    contacts = {r['instance']: r for r in coverage['auxiliary_contact_probes']}
    assert len(contacts) == len(coverage['auxiliary_contact_probes']) == len(aux)
    assert len({r['instance'] for r in aux}) == len(aux)
    assert set(contacts) == {r['instance'] for r in aux}
    assert not (set(contacts) & {r['instance'] for r in records})
    for r in aux:
        p = contacts[r['instance']]
        add(r['instance'], r.get('model', 'auxiliary_contact'), ['body', 'metal'],
            [index(r['body_node'], p['body']), index(r['metal_node'], p['metal'])], True)
    assert len(specs) == sum(len(d['terminals']) * (len(d['terminals']) + 1) // 2 for d in records) + 3 * len(aux)
    return specs

def envelopes(names, values, specs, chunk_rows=256):
    assert type(chunk_rows) is int and chunk_rows > 0
    assert names[0] == 'time' and len(set(names)) == len(names)
    assert values.ndim == 2 and values.shape[1] == len(names) and len(values) > 1
    assert specs and all(-1 <= s[k] < len(names) for s in specs for k in ('left', 'right'))
    left = np.array([s['left'] for s in specs]); right = np.array([s['right'] for s in specs])
    lo = np.full(len(specs), np.inf); hi = np.full(len(specs), -np.inf)
    lt = np.zeros(len(specs)); ht = np.zeros(len(specs))
    cols = np.arange(len(specs)); previous = None
    for start in range(0, len(values), chunk_rows):
        block = np.asarray(values[start:start + chunk_rows])
        assert np.isfinite(block).all(), 'Nonfinite recorded column'
        time = block[:, 0]
        assert np.all(np.diff(time) > 0)
        assert (time[0] == 0 if previous is None else time[0] > previous), 'Nonmonotonic chunk boundary'
        previous = float(time[-1])
        a = np.take(block, left, axis=1); a[:, left == -1] = 0
        b = np.take(block, right, axis=1); b[:, right == -1] = 0
        v = a - b
        low = np.argmin(v, axis=0); high = np.argmax(v, axis=0)
        lv = v[low, cols]; hv = v[high, cols]
        lower = lv < lo; higher = hv > hi
        lo[lower] = lv[lower]; lt[lower] = time[low[lower]]
        hi[higher] = hv[higher]; ht[higher] = time[high[higher]]
    results = []
    for i, spec in enumerate(specs):
        use_low = abs(lo[i]) > abs(hi[i]) or (abs(lo[i]) == abs(hi[i]) and lt[i] <= ht[i])
        results.append(dict(**spec, minimum_v=float(lo[i]), minimum_time_s=float(lt[i]),
                            maximum_v=float(hi[i]), maximum_time_s=float(ht[i]),
                            maximum_abs_v=float(max(abs(lo[i]), abs(hi[i]))),
                            maximum_abs_time_s=float(lt[i] if use_low else ht[i])))
    return dict(rows=len(values), start_s=float(values[0, 0]), end_s=float(values[-1, 0]),
                chunk_rows=chunk_rows, measurements=results, samples_dropped=0,
                interpolated_samples=0, full_device_safety_accepted=False, full_phy_accepted=False,
                scope='Every bound terminal and unordered terminal pair; signed voltages only. No inferred current, device limit, oxide/junction reliability, temperature, PVT, RF/PEX or PHY qualification.')

def controls():
    table = [['0','time','time'], ['1','v(xloop.a)','voltage'], ['2','v(xloop.b)','voltage']]
    comp = dict(device_records=[dict(instance='X1', native_id=1, model='fixture',
                 terminals=[dict(terminal='A',node='a'),dict(terminal='B',node='b'),dict(terminal='S',node='gnd')])],
                auxiliary_contact_models=[dict(instance='Xaux',body_node='b',metal_node='gnd')])
    cov = dict(external_mapping={'gnd':'0'}, auxiliary_contact_probes=[dict(instance='Xaux',body='v(xloop.b)',metal=None)],
               native_terminal_probes=[dict(instance='X1', native_id=1, model='fixture',terminal=t,node=n,vector=v,explicit_zero_reference=v is None)
               for t,n,v in [('A','a','v(xloop.a)'),('B','b','v(xloop.b)'),('S','gnd',None)]])
    plan = binding(comp,cov,table); assert len(plan) == 9
    data = np.array([[0.,1.,.5],[1.,-2.,1.],[2.,3.,-1.],[3.,0.,0.],[4.,3.,-1.]])
    original = data.copy()
    out = envelopes([r[1] for r in table],data,plan,2)
    pair = next(r for r in out['measurements'] if r['instance']=='X1' and r['positive']=='A' and r['negative']=='B')
    assert (pair['minimum_v'],pair['minimum_time_s'],pair['maximum_v'],pair['maximum_time_s']) == (-3.,1.,4.,2.)
    ground = next(r for r in out['measurements'] if r['instance']=='X1' and r['positive']=='S' and r['kind']=='terminal')
    assert ground['minimum_v'] == ground['maximum_v'] == 0 and ground['maximum_abs_time_s'] == 0
    assert np.array_equal(data,original)
    assert envelopes([r[1]for r in table],data,plan,3)['measurements']==out['measurements']
    rejected=[]
    def reject(name, fn):
        try: fn()
        except (AssertionError,KeyError,ValueError): rejected.append(name)
        else: raise AssertionError('Invalid evidence accepted: '+name)
    bad=copy.deepcopy(cov);bad['native_terminal_probes'].pop()
    reject('missing_terminal',lambda:binding(comp,bad,table))
    bad=copy.deepcopy(cov);bad['native_terminal_probes'].append(copy.deepcopy(bad['native_terminal_probes'][0]))
    reject('duplicate_terminal',lambda:binding(comp,bad,table))
    bad=copy.deepcopy(cov);bad['native_terminal_probes'][0]['vector']='v(xloop.b)'
    reject('swapped_physical_vector',lambda:binding(comp,bad,table))
    bad=copy.deepcopy(cov);bad['native_terminal_probes'][0]['native_id']=999
    reject('wrong_native_identity',lambda:binding(comp,bad,table))
    bad=copy.deepcopy(cov);bad['native_terminal_probes'][0].update(vector=None,explicit_zero_reference=True)
    reject('false_ground',lambda:binding(comp,bad,table))
    bad=copy.deepcopy(comp);bad['device_records'].append(copy.deepcopy(bad['device_records'][0]))
    reject('duplicate_device',lambda:binding(bad,cov,table))
    bad=copy.deepcopy(cov);bad['auxiliary_contact_probes']=[]
    reject('missing_auxiliary_contact',lambda:binding(comp,bad,table))
    bad=copy.deepcopy(table);bad[1][2]='current'
    reject('wrong_voltage_unit',lambda:binding(comp,cov,bad))
    reject('missing_raw_column',lambda:binding(comp,cov,table[:-1]))
    bad=data.copy();bad[2,2]=np.nan
    reject('nonfinite_chunk_boundary',lambda:envelopes([r[1]for r in table],bad,plan,2))
    bad=data.copy();bad[2,0]=bad[1,0]
    reject('duplicate_time_chunk_boundary',lambda:envelopes([r[1]for r in table],bad,plan,2))
    assert len(rejected)==11
    return dict(known_signed_pair_and_extrema_times=True,first_tie_preserved=True,
                chunk_partition_invariant=True,source_unchanged=True,rejected=rejected)
