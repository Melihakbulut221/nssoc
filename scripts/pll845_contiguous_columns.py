#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Byte-exact contiguous copies for repeated acquisition reads, never a new gate."""
import ast
import hashlib
import json
import time
import numpy as np

REQUIRED = ('time', 'v(reference)', 'v(fb)', 'v(clkp)', 'v(clkn)', 'v(vctrl)', 'v(up)', 'v(down)')
CHUNK_ROWS = 4096

def columns(names, values, progress=None):
    assert len(names) == len(set(names)), 'Unique original column names'
    assert values.ndim == 2 and values.shape[1] == len(names) and values.shape[0] > 1
    assert values.dtype == np.dtype('<f8'), 'Original binary64 dtype'
    assert set(REQUIRED) <= set(names), 'Every unchanged analyzer input'
    indices = [names.index(n) for n in REQUIRED]
    cached = {n: np.empty(values.shape[0], dtype='<f8') for n in REQUIRED}
    digest = hashlib.sha256()
    for start in range(0, len(values), CHUNK_ROWS):
        stop = min(start + CHUNK_ROWS, len(values))
        block = np.take(values[start:stop], indices, axis=1)
        assert np.isfinite(block).all(), 'Every cached value finite'
        for i, name in enumerate(REQUIRED):
            cached[name][start:stop] = block[:, i]
        rebuilt = np.column_stack([cached[n][start:stop] for n in REQUIRED])
        assert np.array_equal(block.view('<u8'), rebuilt.view('<u8')), 'Exact original sample bits'
        digest.update(block.tobytes(order='C'))
        if progress is not None and (start == 0 or stop == len(values) or start % (CHUNK_ROWS * 64) == 0):
            progress('CACHE_ORIGINAL_ANALYZER_COLUMNS', rows_done=stop, rows_total=len(values))
    output = {name: values[:, i] for i, name in enumerate(names)}
    output.update(cached)
    assert len(output) == len(names) and all(output[n].flags.c_contiguous for n in REQUIRED)
    receipt = dict(rows=len(values), original_columns=len(names), cached_columns=list(REQUIRED),
                   cached_bytes=sum(v.nbytes for v in cached.values()), chunk_rows=CHUNK_ROWS,
                   selected_row_major_binary64_sha256=digest.hexdigest(),
                   exact_sample_bits_checked=True, samples_removed=0, columns_removed=0,
                   resampled=False, changed_thresholds=False, original_raw_retained=True)
    return output, receipt

def analyzer_inputs(path, diagnosis):
    tree = ast.parse(path.read_text())
    wanted = {'independent_edges', 'monotone_ordinals', 'independent_analysis'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    found = {n.slice.value for node in nodes for n in ast.walk(node)
             if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)
             and n.value.id == 'data' and isinstance(n.slice, ast.Constant)}
    assert found == {'time', 'v(reference)', 'v(fb)', 'v(vctrl)'}
    # Diagnosis is source-pinned by the adapter manifest. Include its complete
    # declared vector list, including differential-clock inputs.
    assert set(REQUIRED) == found | {'time','v(clkp)','v(clkn)','v(vctrl)','v(up)','v(down)'}
    return sorted(found)

def controls(analyze, diagnose):
    names = ['unused0', *REQUIRED, 'unused1']
    t = np.linspace(0, 1e-6, 32001, dtype='<f8')
    results = []
    for case in ('passing', 'frequency_rejection', 'control_rejection'):
        values = np.empty((len(t), len(names)), dtype='<f8')
        for i in range(len(names)): values[:, i] = (i + 1) * 0.03125
        values[:,names.index('time')] = t
        reference = 1.25 + np.sin(2*np.pi*100e6*t - .4)
        feedback = 1.25 + np.sin(2*np.pi*(100e6 if case != 'frequency_rejection' else 91e6)*t - .4)
        values[:,names.index('v(reference)')] = reference
        values[:,names.index('v(fb)')] = feedback
        values[:,names.index('v(vctrl)')] = 1.8 if case == 'control_rejection' else .8
        values[:,names.index('v(clkp)')] = 1.0 + .25*np.sin(2*np.pi*8e9*t)
        values[:,names.index('v(clkn)')] = 1.0 - .25*np.sin(2*np.pi*8e9*t)
        values[:,names.index('v(up)')] = np.where(reference > 1.25, 2.5, 0)
        values[:,names.index('v(down)')] = np.where(feedback > 1.25, 2.5, 0)
        before = hashlib.sha256(values.tobytes()).hexdigest()
        strided = {n:values[:,i] for i,n in enumerate(names)}
        cached, receipt = columns(names, values)
        assert set(cached) == set(strided)
        for name in names:
            assert np.array_equal(cached[name].view('<u8'), strided[name].view('<u8'))
        a, b = analyze(strided), analyze(cached)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
        da, db = diagnose(strided, a), diagnose(cached, b)
        assert json.dumps(da, sort_keys=True) == json.dumps(db, sort_keys=True)
        assert a['passed'] == (case == 'passing'), (case, a['passed'])
        assert before == hashlib.sha256(values.tobytes()).hexdigest()
        results.append(dict(case=case, acquisition_passed=a['passed'],
                            all_acquisition_fields_exact=True, all_cycle_fields_exact=True,
                            all_sample_bits_exact=True, original_input_unchanged=True))
    bad = []
    invalid = [
        ('duplicate_names', ['time'] * len(names), values),
        ('missing_input', [n if n != 'v(up)' else 'absent' for n in names], values),
        ('shape', names, values[:,:-1]),
        ('dtype', names, values.astype('<f4')),
        ('single_row', names, values[:1]),
    ]
    for label, ns, vs in invalid:
        try: columns(ns, vs)
        except AssertionError: bad.append(label)
        else: raise AssertionError('Invalid cache input accepted: ' + label)
    nonfinite = values.copy(); nonfinite[-1,names.index('v(fb)')] = np.nan
    try: columns(names, nonfinite)
    except AssertionError: bad.append('nonfinite_selected_value')
    else: raise AssertionError('Nonfinite selected value accepted')
    return dict(status='PASS_BYTE_EXACT_STORAGE_ADAPTATION_CONTROLS_NOT_NATIVE_PHY_ACCEPTANCE',
                cases=results, rejected=bad,
                scope='Fixture equivalence only. Original full-column capture validation remains mandatory.')
