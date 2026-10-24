# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Signed HBT observations; process-monitor breakdown is not full SOA.

Preserves every existing circuit acceptance gate. In particular a forward
VBE peak is never relabelled a reverse emitter-base breakdown measurement.
"""
import numpy as np

SOURCE = 'https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/03_bjt_params.html#npn13g2-specs'
CONDITIONS = 'https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/04_meas_cond.html'


def signed_hbt_observation(t, collector, base, emitter, current, nx):
    vectors = [np.asarray(v, dtype=float) for v in (t,collector,base,emitter,current)]
    assert all(v.ndim == 1 and len(v) == len(vectors[0]) and len(v)>0 and np.isfinite(v).all() for v in vectors)
    assert np.all(np.diff(vectors[0])>0) and isinstance(nx,int) and nx>0
    t,c,b,e,ic=vectors
    values={'forward_be':b-e, 'reverse_eb':e-b, 'reverse_cb':c-b, 'forward_ce':c-e,
            'absolute_current_per_emitter':abs(ic)/nx}
    peaks={}
    for name,y in values.items():
        i=int(np.argmax(y))
        peaks[name]={'value':float(y[i]),'time_s':float(t[i]),'native_index':i,
            'collector_v':float(c[i]),'base_v':float(b[i]),'emitter_v':float(e[i]),
            'unit':'A' if name=='absolute_current_per_emitter' else 'V'}
    return {'signed_native_peaks':peaks,
        'legacy_abs_vbe_1v_exceeded':bool(np.max(abs(b-e))>1.),
        'comparison_to_process_monitor_table':{
            'reverse_eb_at_or_above_1v_min':bool(np.max(e-b)>=1.),
            'reverse_cb_at_or_above_3p8v_min':bool(np.max(c-b)>=3.8),
            'forward_ce_at_or_above_1p4v_min':bool(np.max(c-e)>=1.4),
            'absolute_current_per_emitter_above_3p5ma':bool(np.max(abs(ic)/nx)>.0035)},
        'source':SOURCE,'measurement_conditions':CONDITIONS,
        'qualified_safe_operating_area':False,'acceptance_changed':False,
        'scope':'Process-monitor comparison only: BVCEO/BVCBO/BVEBO are measured under distinct open-terminal/current conditions, not transistor operating limits under this waveform. No forward-VBE maximum or lifetime/SOA acceptance inferred; original heuristic and circuit gates remain unchanged.'}


def polarity_controls():
    def measure(be):
        return signed_hbt_observation([0.,1e-9,2e-9],[.9,.9,.9],be,[0.,0.,0.],[.001,.001,.001],1)
    forward=measure([.7,1.023,.8]);reverse=measure([.7,-1.023,.8])
    assert forward['legacy_abs_vbe_1v_exceeded'] and reverse['legacy_abs_vbe_1v_exceeded']
    assert not forward['comparison_to_process_monitor_table']['reverse_eb_at_or_above_1v_min']
    assert reverse['comparison_to_process_monitor_table']['reverse_eb_at_or_above_1v_min']
    assert not forward['qualified_safe_operating_area'] and not reverse['qualified_safe_operating_area']
    assert forward['signed_native_peaks']['forward_be']['native_index']==1
    assert reverse['signed_native_peaks']['reverse_eb']['native_index']==1
    rejected=[]
    for label,args in [
        ('nonfinite',([0.,1.],[1.,float('nan')],[.5,.5],[0.,0.],[.001,.001],1)),
        ('missing_sample',([0.,1.],[1.],[.5,.5],[0.,0.],[.001,.001],1)),
        ('duplicate_time',([0.,0.],[1.,1.],[.5,.5],[0.,0.],[.001,.001],1)),
        ('zero_emitters',([0.,1.],[1.,1.],[.5,.5],[0.,0.],[.001,.001],0))]:
        try:signed_hbt_observation(*args)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Invalid polarity capture accepted: '+label)
    return {'forward_reverse_distinction_proved':True,'original_abs_vbe_failure_retained':True,'no_soa_acceptance':True,'rejected':rejected}
