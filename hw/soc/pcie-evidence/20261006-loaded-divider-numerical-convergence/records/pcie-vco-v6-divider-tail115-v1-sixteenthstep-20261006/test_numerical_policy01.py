# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual additional numerical-gate fault controls, with no EDA."""
from pathlib import Path
import copy,hashlib,json
from convergence_policy01 import evaluate
B=Path(__file__).resolve().parent
p=json.loads((B/'numerical-policy01.json').read_text())
base=dict(native_status='PASS_NATIVE_LOADED_FEEDBACK_SCREEN',vco_edges=244,initial_mapping=dict(vco_before_window=30,first_cml_nearest_global_vco=31,feedback_nearest_global_vco=[86,166,246],previous_cml_s=3.695e-9,first_cml_s=4.184e-9),vco_frequency_hz=8e9,feedback_frequency_hz=1e8,numerical_edge_times=dict(vco=[4.061e-9+k*125e-12 for k in range(244)],cml=[4.184e-9+k*500e-12 for k in range(61)],feedback=[10.91e-9,20.72e-9,30.56e-9]))
checks=[]
def case(name,change,expected,failed=None):
 z=copy.deepcopy(base);change(z);r=evaluate(base,z,p);ok=r['status']=='PASS_FINITE_OPEN_LOOP_NUMERICAL_SCREEN';assert ok==expected,(name,r)
 if failed:assert r['checks'][failed]is False,(name,failed,r)
 checks.append(dict(name=name,expected_pass=expected,actual_status=r['status'],actual_checks=r['checks'],details=r['details']))
case('identical_reference',lambda z:None,True)
def bounded(z):
 z['vco_frequency_hz']*=1+99e-6;z['feedback_frequency_hz']*=1+99e-6
 for seq in z['numerical_edge_times'].values():
  for i in range(len(seq)):seq[i]+=49e-12
case('declared_below_limits',bounded,True)
case('vco_101ppm',lambda z:z.update(vco_frequency_hz=8e9*(1+101e-6)),False,'vco_frequency_100ppm')
case('feedback_101ppm',lambda z:z.update(feedback_frequency_hz=1e8*(1+101e-6)),False,'feedback_frequency_100ppm')
for key in ['vco','cml','feedback']:
 def offset(z,key=key):z['numerical_edge_times'][key]=[v+51e-12 for v in z['numerical_edge_times'][key]]
 case('constant51ps_'+key+'_not_subtracted',offset,False,key+'_max_unaligned_phase_50ps')
case('wrong_initial_VCO_anchor',lambda z:z['initial_mapping'].update(first_cml_nearest_global_vco=32),False,'candidate_mapping')
case('first_window_input_clipped',lambda z:z['initial_mapping'].update(vco_before_window=31),False,'candidate_mapping')
case('last_window_input_added',lambda z:z.update(vco_edges=245),False,'candidate_mapping')
case('missing_CML',lambda z:z['numerical_edge_times']['cml'].pop(20),False,'cml_edge_census')
case('old_functional_failure_never_promoted',lambda z:z.update(native_status='FAIL_NATIVE_LOADED_FEEDBACK_SCREEN'),False,'candidate_native_functional')
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
r=dict(status='PASS_ACTUAL_ADDITIONAL_NUMERICAL_GATE_CONTROLS',checks=checks,inputs={str(q):pin(q)for q in [Path(__file__),B/'convergence_policy01.py',B/'numerical-policy01.json']},scope='Twelve pure event/frequency fixtures exercise actual supplementary gate. No wave/native/physical acceptance changes; originalfunctionalFAIL always blocks supplemental numericalPASS.')
(B/'numerical-controls01.json').write_text(json.dumps(r,indent=2)+'\n');print(len(checks),r['status'])
