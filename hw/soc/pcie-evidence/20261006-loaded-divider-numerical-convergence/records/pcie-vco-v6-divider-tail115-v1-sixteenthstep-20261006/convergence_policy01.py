# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additional numerical screen; original native functional gates stay unchanged."""
def evaluate(reference, candidate, policy):
    checks={};details={}
    for label,c in [('reference',reference),('candidate',candidate)]:
        mapping=c['initial_mapping']
        checks[label+'_mapping']=(c['vco_edges']==policy['edge_counts']['vco'] and mapping['vco_before_window']==policy['vco_before_window'] and mapping['first_cml_nearest_global_vco']==policy['first_cml_global_vco'] and mapping['feedback_nearest_global_vco']==policy['feedback_global_vco'] and mapping['previous_cml_s']<4e-9<=mapping['first_cml_s'])
        checks[label+'_native_functional']=c['native_status']=='PASS_NATIVE_LOADED_FEEDBACK_SCREEN'
    for signal in ['vco','feedback']:
        a=reference[signal+'_frequency_hz'];b=candidate[signal+'_frequency_hz']
        ppm=abs(b/a-1)*1e6;details[signal+'_frequency_delta_ppm']=ppm
        checks[signal+'_frequency_100ppm']=ppm<=policy['frequency_limit_ppm']
    for signal in ['vco','cml','feedback']:
        a=reference['numerical_edge_times'][signal];b=candidate['numerical_edge_times'][signal]
        equal=len(a)==len(b)==policy['edge_counts'][signal]
        checks[signal+'_edge_census']=equal
        if equal:
            delta=[(y-x)*1e12 for x,y in zip(a,b)]
            details[signal+'_unaligned_delta_ps']=delta
            checks[signal+'_max_unaligned_phase_50ps']=max(map(abs,delta))<=policy['phase_limit_ps']
        else:checks[signal+'_max_unaligned_phase_50ps']=False
    return dict(status='PASS_FINITE_OPEN_LOOP_NUMERICAL_SCREEN'if all(checks.values())else'FAIL_FINITE_OPEN_LOOP_NUMERICAL_SCREEN',checks=checks,details=details,physical_acceptance=False,scope=policy['scope'])
