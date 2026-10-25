#!/usr/bin/env python3
"""Independent saved-record fact check; never runs a producer or native tool."""
from pathlib import Path
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

R=Path('/home/hasanmelih/Documents/ChatGPT/nnsoc')
B=R/'hw/soc/out/pcie-phase34-delivery-20261006'
V=R/'hw/soc/out/pcie-integrity-v24-20261006'
inputs={}
def pin(path):
    p=Path(path); p=p if p.is_absolute() else R/p
    data=p.read_bytes()
    r={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    inputs[str(p)]=r
    return r

def read(path):
    p=Path(path); p=p if p.is_absolute() else R/p
    pin(p)
    return json.loads(p.read_text())

def bind(row):
    p=Path(row['path']); actual=pin(p)
    assert all(actual[k]==row[k] for k in ('bytes','sha256')),p
    return p

D=R/'docs/145-pcie-divider-time-step-and-prefix-timing.md'
docpin=pin(D)
assert docpin=={'bytes':6463,'sha256':'972d73dc8fb07dce25c7c27ca5d97b55e63958ff96800776e06d7da3e32274eb'}
doc=' '.join(D.read_text().split())
required=[
    'All 455 electrical screens and every original functional check pass',
    'finite nominal test. It does not close numerical convergence',
    '1,079.469 ppm','443.174 ps','V11 remains the stable baseline',
    'The first two results remain FAIL',
    '6,523,869, 13,031,469 and 26,046,669 finite values',
    'Five component tests cover token classification and carry-column relationships',
    'The product control history contains 44 executions: 43 pass',
    'one retained host-diagnostic failure', 'all 42 current predicates',
    'Two MAX4118 predicates remain excluded',
    'It does not claim a single clean 42-test run or mapped-netlist functional equivalence',
    'with no routing, extracted timing, main-chip integration or full PHY acceptance claimed',
]
assert all(x in doc for x in required)
assert 'packing relationships' not in doc
old=read(B/'doc145-wording-findings-rx01.json')
assert old['document']!=docpin if 'document' in old else True
intervals=read(B/'doc145-extra-intervals-rx01.json')
assert intervals['findings']==[] and intervals['status'].startswith('PASS_')
for suffix in ('py','log'):pin(B/f'doc145-extra-intervals-rx01.{suffix}')
rawpeers=[]; natives=[]
for name,finite,frequency,status in [
    ('',6523869,8102491691.349728,'FAIL_NATIVE_LOADED_FEEDBACK_SCREEN'),
    ('halfstep-',13031469,8137405935.630378,'FAIL_NATIVE_LOADED_FEEDBACK_SCREEN'),
    ('quarterstep-',26046669,8146190013.755915,'PASS_NATIVE_LOADED_FEEDBACK_SCREEN')]:
    peer=read(R/f'hw/soc/out/pcie-tail115-{name}wave-peer-rx-20261006/result.json')
    assert peer['findings']==[] and peer['native_acceptance_changed'] is False
    assert peer['finite_values']==finite
    assert len(peer['all64_HBT_VCE'])==64
    assert peer['fixed_ordinal_advance']==4
    assert peer['original_native_status']==status
    rootname='wire' if not name else name.rstrip('-')
    nativepath=Path(f'/dev/shm/nssoc-vco-v6-divider-tail115-v1-{rootname}-06-01/result.json')
    native=read(nativepath)
    assert native['status']==status and native['safety']['passed']
    assert math.isclose(native['measurement']['vco_frequency_hz'],frequency,abs_tol=0.001)
    assert len(native['devices'])==455
    assert len(native['safety']['all_device_bounds'])==455
    assert all(x['passed'] for x in native['safety']['all_device_bounds'])
    assert native['values']==finite
    natives.append(native);rawpeers.append(peer)
assert natives[0]['devices']==natives[1]['devices']==natives[2]['devices']
for i,n in enumerate(natives):
    assert n['config']['step_s']==[5e-12,2.5e-12,1.25e-12][i]
    assert n['config']['stop_s']==34e-9 and n['config']['window_s']==[4e-9,34e-9]
    assert n['config']['wire_resistors']==1271 and n['config']['wire_capacitors']==1414
for key in ('fixture','roots','minimum_states','vctrl','extra_vectors'):
    assert natives[0]['config'][key]==natives[1]['config'][key]==natives[2]['config'][key]
cml_delta_ps=max(abs(a-b)*1e12 for a,b in zip(natives[1]['measurement']['edge_times']['cml'],natives[2]['measurement']['edge_times']['cml'],strict=True))
assert abs(cml_delta_ps-35.271489535912636)<1e-8
assert [x['finite_values'] for x in rawpeers]==[6523869,13031469,26046669]
for i,c in enumerate(intervals['captures']):
    counts=c['actual_vco_period_counts']
    assert counts['whole_native_div80']==[80,80]
    assert len(counts['native_hbt_div4'])==60
    assert counts['native_hbt_div4']==rawpeers[i]['CML_interval_counts']
assert rawpeers[2]['CML_interval_counts']==[4]*60
assert all(p['CML_interval_counts'].count(3)==1 and p['CML_interval_counts'].count(4)==59 for p in rawpeers[:2])
ppm=(rawpeers[2]['vco_frequency_hz']/rawpeers[1]['vco_frequency_hz']-1)*1e6
assert abs(ppm-1079.4690832707233)<1e-6
assert rawpeers[2]['numerical_convergence_claim'] is False
synthetic=read(R/'hw/soc/out/pcie-divider-bucket-oracle-diagnostic-20261006/result01.json')
assert synthetic['status']=='PASS_SYNTHETIC_BUCKET_PHASE_SENSITIVITY_REGRESSION_NO_ORACLE_ADOPTION'
pin(R/'hw/soc/out/pcie-vco-v6-divider-tail115-v1-quarterstep-20261006/step-comparison01.json')
policy=read(B/'doc145-numerical-policy-peer-vco01.json')
assert policy['findings']==[]

geom=read('/dev/shm/nssoc-div4-v10-tail-v1-checks-01/power-geometry.json')
assert geom['changed_reference_length_um']=={'DIV__XSECOND__XBIAS':[12.7,11.5]}
assert geom['unchanged_intrinsics']==90 and geom['physical_primitives']==91
assert len(geom['controls'])==10 and all(x['status']=='EXPECTED_REJECTION' for x in geom['controls'])
physical=read(R/'hw/soc/out/pcie-divider-v10-tail-v1-20261006/native-saved-peer-rx.json')
assert physical['findings']==[] and physical['full_member_readback']==340
assert len(physical['positive_stages'])+len(physical['expected_negative_stages'])==21
rc=read(R/'hw/soc/out/pcie-divider-v10-tail-v1-wire-rc-v1-20261006/saved-rc-peer-pll.json')
assert rc['findings']==[] and rc['resistors']==382 and rc['capacitors']==649
assert rc['full_pex_qualified'] is False
composition=read(R/'sw/tests/fixtures/pcie_clock_div4_v10_tail115_v1_hybrid_v1/composition.json')
assert composition['intrinsic_devices']==91
assert composition['metal_terminal_anchors']+composition['body_well_terminals']==283
assert composition['full_pex_qualified'] is False
pin(R/'hw/soc/analog/pcie/clock_div4_hbt_v10.spice')
pin(R/'sw/tests/fixtures/pcie_clock_div4_v10_tail115_v1_hybrid_v1/source-native-bijection.json')

component=read(V/'component-validation01.json')
assert len(component['pytest_cases'])==5 and component['predicate']['mode_comparisons']==3796416
assert component['predicate']['actual_mutants']==4
for row in component['raw_cases']: bind(row)
controls=read(V/'pcie-integrity-v24-composite-controls-validation-20261006.json')
assert (controls['pytest_executions'],controls['passed_executions'],controls['historical_failed_executions'])==(44,43,1)
assert controls['current_42_predicates_covered'] and controls['MAX4118_excluded']
assert controls['public_profiles']=={'direct':18,'cycle_miter':18,'unchanged_latency':True}
xmlcounts=[]
for campaign in controls['campaigns']:
    p=bind(campaign); cases=list(ET.parse(p).getroot().iter('testcase'))
    passed=sum(not any(c.tag in ('failure','error','skipped') for c in row) for row in cases)
    failed=sum(any(c.tag in ('failure','error') for c in row) for row in cases)
    skipped=sum(any(c.tag=='skipped' for c in row) for row in cases)
    assert (passed,failed,skipped)==(campaign['passed'],campaign['failed'],campaign['skipped'])
    xmlcounts.append({'passed':passed,'failed':failed,'skipped':skipped})
assert xmlcounts==[{'passed':41,'failed':1,'skipped':0},{'passed':2,'failed':0,'skipped':0}]
peer=read(V/'native-saved-peer-vco.json')
assert peer['findings']==[]
assert (peer['actual_native_cells'],peer['actual_native_FFs'],peer['archive_members'])==(98919,9490,182)
assert sum(len(x['all_group_slacks_ns']) for x in peer['all24raw_STA_group_values_reparsed'])==24
slacks={'slow_max':-3.634856,'slow_min':.356499,'typical_max':-.827638,'typical_min':.254520,'fast_max':.823255,'fast_min':.170948}
assert peer['repaired_slacks_ns']==slacks
assert abs(peer['delta_SS_vs_V23_ns']+.443174)<1e-12
ready=read(V/'ready-finite.json')
assert not ready['adopted'] and not ready['physical_acceptance'] and ready['stable_baseline']=='V11'
for f in ('critical-path-attribution.json','candidate-decision.json','timing-comparison.json','pcie-integrity-v24-native-validation-20261006.json','delivery02/saved-delivery-peer-rx02.json'):pin(V/f)
for ext in ('py','log'):pin(B/f'doc145-review-rx01-attempt01.{ext}')
pin(__file__)
assert pin(D)==docpin
result={
 'status':'PASS_INDEPENDENT_DOC145_FACTUAL_REVIEW', 'findings':[],
 'utc':datetime.now(timezone.utc).isoformat(), 'document':{'path':str(D),**docpin},
 'method':{'path':str(Path(__file__)),**pin(__file__)}, 'inputs':inputs,
 'review_method_history':'Initial saved-reader attempt assumed the older 5ps peer had a frequency field added only to later peers. Original method/log retained; final reader uses each actual native measurement frequency. No producer or evidence bytes changed.',
 'numerical_wording_peer_binding':'The narrower VCO peer bound the preclarification doc. Its numerical paragraphs are unchanged; this full review binds the final exact doc after both V24 wording fixes.',
 'closed_wording_findings':['Separate five component matrix tests from product bank-packing coverage.','Qualify 44 executions as product control history, with five standalone component tests separate.'],
 'claims':{
  'three_full_raw_finite_values':[p['finite_values'] for p in rawpeers],
  'all64_HBT_per_capture_independently_recounted':True,
  'all455_safety_records_per_capture_saved_producer_pass':True,
  'all_reported_divider_edges_and_interval_counts_independently_recounted':True,
  'whole_div80_intervals_per_capture':[80,80],
  'original_statuses':[p['original_native_status'] for p in rawpeers],
  'quarterstep_frequency_change_ppm':ppm,'unaligned_CML_edge_delta_ps':cml_delta_ps,'numerical_convergence_claim':False,
  'loaded_wire_resistors':1271,'loaded_wire_capacitors':1414,'duration_ns':34,'acceptance_window_ns':[4,34],
  'geometry_one_reference_delta':[12.7,11.5], 'unchanged_intrinsics':90,
  'physical_checks':21,'geometry_controls':10,'native_devices':91,'native_terminals':283,
  'RC_resistors':382,'RC_capacitors':649,'RC_qualified':False,
  'component_tests_separate':5,'component_comparisons':3796416,
  'product_executions':44,'product_passed':43,'historical_failed':1,'current_product_predicates':42,
  'campaign_XML_recount':xmlcounts,'MAX4118_excluded':2,'direct_profiles':18,'miter_profiles':18,
  'native_cells':98919,'native_FFs':9490,'native_archive_members':182,'raw_STA_values':24,
  'repaired_slacks_ns':slacks,'SS_regression_ps':443.174,'adopted':False,'stable_baseline':'V11'
 },
 'scope':'Full document read and exact saved-receipt/XML bindings. Earlier independently streamed raw/archive peers reused; this turn adds full saved-wave all-stage interval recount. All455 electrical screens remain exact producer results; all64 HBT and source/native terminal mapping independently recounted. No simulator, EDA, functional test, public upload, source or Git edit. Planned C34 inventory link intentionally excluded until root constructs delivery; no aggregate asset/member count appears in document.'
}
(B/'doc145-peer-rx01.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'document':docpin,'inputs':len(inputs),'findings':[]}))
