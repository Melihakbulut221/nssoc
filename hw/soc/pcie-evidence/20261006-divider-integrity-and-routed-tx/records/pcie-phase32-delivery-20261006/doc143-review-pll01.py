# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-result fact/scope check; no producer or native execution."""
from pathlib import Path
import datetime,hashlib,json
R=Path.cwd();O=R/'hw/soc/out';B=Path(__file__).resolve().parent
inputs={}
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def load(p):
 p=Path(p);inputs[str(p)]=pin(p);return json.loads(p.read_text())
def check(p,h):assert pin(p)=={k:h[k]for k in('bytes','sha256')},str(p)
doc=R/'docs/143-pcie-divider-and-routed-transmitter.md';text=doc.read_text();inputs[str(doc)]=pin(doc)
v=load(O/'pcie-integrity-v23-20261006/ready-finite.json')
for name,h in v['evidence'].items():check(R/name,h)
c=v['controls'];assert(c['pytest_executions'],c['passed_executions'],c['historical_failed_executions'])==(47,37,10)
assert[(x['passed'],x['failed'])for x in c['campaigns']]==[(28,7),(6,3),(3,0)]
assert(c['direct_public_profile_cases'],c['cycle_miter_profile_cases'],c['literal_binary_vectors'],c['literal_xz_vectors'])==(18,18,557056,1440)
assert c['actual_block_burst']==dict(accepted_blocks=15,bytes=786,packets=25,promotions=14,changed_relation_promotions=13,simultaneous_promotion_accept=13,input_stall_cycles=38,output_stall_cycles=6)
assert c['surviving_wrapper_promotion_mutant_now_real_framer_detected_at_ns']==28 and c['MAX4118_profile_excluded']
n=v['native'];assert n['setup_ns']==dict(slow=-3.191682,typical=-.549377,fast=.998914)
assert n['hold_ns']==dict(slow=.370623,typical=.260212,fast=.176)
assert(n['native_cells'],n['flops'])==(94742,8846) and not v['adopted']
assert abs(n['delta_vs_V22']['slow_max']*1000-352.600)<1e-8 and abs(n['delta_vs_V17']['slow_max']*1000-144.601)<1e-8
m=load(O/'pcie-integrity-v18-20261005/max4118-01/ready-finite.json')
for name,h in m['evidence'].items():check(R/name,h)
assert m['functional']['direct']==dict(passed=13,failed=0,skipped=0,original_parent_waitcode=None)
assert m['functional']['miter']==dict(passed=13,failed=0,skipped=0,owned_waitcode=0)
assert(m['functional']['maximum_encoded_bytes'],m['functional']['ring_dwords'])==(4118,2048)
t=load(O/'pcie-gen3-transmit-v4-repair-20261005/repair05-peer/review.json')
for name,h in t['inputs_rehashed'].items():check(name,h)
expected={'slow':dict(setup=-.306243,hold=.042155,recovery=.180606,removal=.205402),'typical':dict(setup=1.283555,hold=.072382,recovery=1.516654,removal=.177273),'fast':dict(setup=2.191549,hold=.097803,recovery=2.313462,removal=.159396)}
assert t['nominal_rc_cell_corner_slack_ns']==expected and not t['physical_acceptance'] and not t['qualified_rc']
assert t['canonical_binary_kernel_replay']['states']==3850 and t['canonical_binary_kernel_replay']['matched']==11680 and not t['canonical_binary_kernel_replay']['mismatches']
assert t['preserved_original_fault_controls']==10 and t['port_XML_cases_recounted']==3
assert t['unannotated_output_analysis']['reported']==150 and t['unannotated_output_analysis']['all150_input_pins_present_on_correct_extracted_clock_nets']
assert abs(t['nominal_prior_and_improvement']['delta_ns']['slow']['setup']*1000-295.519)<1e-9
assert abs(t['nominal_prior_and_improvement']['delta_ns']['slow']['hold']*1000+37.161)<1e-9
raw=t['SS_three_worst_setup_paths'][0]['raw_path'];assert '0.087569' in raw and '1.032121' in raw and '0.594511' in raw
p=load(O/'pcie-gen3-transmit-v4-repair-20261005/repair05-peer/package.json');assert p['member_count']==116
release=load(O/'pcie-gen3-transmit-v4-repair-20261005/repair05-peer/release.json');assert len(release['assets'])==3 and all(a['authenticated_roundtrip']and a['anonymous_roundtrip']for a in release['assets'])
a=load(O/'pcie-bias8-layout-wire-loaded-finite-20261006/ready-finite01.json')
for name,h in a['compact_evidence'].items():check(name,h)
for name,h in a['root_wave_inputs'].items():check(name,h)
assert a['future_second_stage_reference_experiment_excluded']
w=load(O/'pcie-bias8-wave-root-20261006/result.json');assert w['status']=='PASS_INDEPENDENT_BIAS8_RAW_TERMINAL_READBACK_FUNCTIONAL_FAIL_RETAINED'
assert len(w['capture']['all64_HBT_bounds_recomputed'])==64 and w['capture']['values']==6523869
r=load(O/'pcie-vco-v6-divider-bias8-v1-wire-v1-20261006/regeneration-diagnosis06.json')
slave=next(x for x in r['loops']if x['stage']=='SECOND'and x['latch']=='XS');early,late=slave['windows'][0],slave['windows'][-1]
assert round(early['hold_regen_differential_current_rms_a']*1000,2)==1.13 and round(late['hold_regen_differential_current_rms_a']*1000,2)==.40
assert round(early['hold_tail_a']*1000,2)==1.46 and round(late['hold_tail_a']*1000,2)==1.43
q=load(O/'pcie-vco-v6-divider-bias8-v1-wire-v1-20261006/charge-diagnosis06.json');assert q['captures'][1]['native_status']=='FAIL_NATIVE_LOADED_FEEDBACK_SCREEN'
replay=load(O/'pcie-vco-v6-divider-bias8-v1-wire-v1-20261006/review-06-01.json');assert replay['all455_device_screens_reproduced'] and replay['all_counts_measurements_reproduced'] and replay['no_native_rerun']
for scope in ['28 pass/7 fail','6 pass/3 fail','3 pass/0 fail','MAX4118 profile is excluded from V23','V11 remains the stable baseline','V23 is not adopted','V19–V24','not a valid 6 GHz divided output','Zero router DRC is not foundry DRC','manufacturer acceptance remain open']:
 assert scope in text,scope
out=dict(status='PASS_INDEPENDENT_DOC143_SAVED_FACT_AND_SCOPE_REVIEW',utc=datetime.datetime.now(datetime.UTC).isoformat(),document=pin(doc),inputs=inputs,method=pin(Path(__file__)),findings=[],verified=dict(V23_campaigns=[[28,7],[6,3],[3,0]],MAX_V18_only_direct13_miter13=True,TX_three_corners=expected,analog_full_window_function_failure_retained=True),scope='Read complete document; rehashed completed finite evidence and matched facts to independently saved control/native/raw-wave reviews, with explicit historical failures, unavailable direct-parent wait status, later-candidate exclusions, nominalRC/standalone/component limits. No new EDA, HDL tests, waveform numerical replay or archival run. Existing independent saved-byte reviews remain separately pinned.')
(B/'doc143-review-pll01.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status']);print(pin(B/'doc143-review-pll01.json'))
