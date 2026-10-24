#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""A completed router for this exact repaired chip is required before RC/STA."""
import copy,re
INITIAL='13060f197d5e9f75368e9db1e104d7f30381e3ca4bfa4f9d10e7c4438a625fc5'
CONTINUATION='d033e54252166ab930a50e5d3039bee45ac114d6f5088a8316fb4fd8652c5ffc'
GLOBAL=dict(global_candidate_instance_count=153130,
 global_odb_sha256='6bf5a055467ffea2e4fb0059ffcac4293d939171b0e17af6e224aee13b41c00c',
 global_guides_sha256='4b22365ef87d0c5880fe2e27732e6be19644f24cbcc2d309862a841b80721efb',
 candidate_netlist_sha256='3a200ea79143bc3b723905495085c317083deac7cc6b10ad3033b186293d7030',
 source_sdc_sha256='19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597')
def validate(spec,live,r,image):
    assert set(spec)=={'run','attempt','group','source_head','controller_sha256','summary_sha256','parts_sha256'}
    assert type(spec['run'])is int and spec['run']>0 and spec['attempt']==1
    assert spec['group']in ('mainchip-repair-deep-drt-initial','mainchip-repair-deep-drt-cross')
    assert re.fullmatch('[0-9a-f]{40}',spec['source_head'])
    assert all(re.fullmatch('[0-9a-f]{64}',spec[k])for k in ('controller_sha256','summary_sha256','parts_sha256'))
    paths={'.github/workflows/mainchip-repair-deep-drt-cloud.yml':INITIAL,
      '.github/workflows/mainchip-repair-deep-drt-continuation-cloud.yml':CONTINUATION}
    assert live['path']in paths and spec['controller_sha256']==paths[live['path']]
    assert live['id']==spec['run']and live['run_attempt']==1
    assert live['head_sha']==spec['source_head']and live['head_branch']=='codex/complete-open-work'
    assert live['status']=='completed'and live['conclusion']=='success'
    assert r['source_head']==spec['source_head']and r['run_id']==spec['run']
    assert r['controller_sha256']==spec['controller_sha256']and spec['group'].endswith('-'+r['stage'])
    assert r['status']=='COMPLETE_NATIVE_DRT_REQUIRES_ALL_POSTROUTE_PHYSICAL_RC_STA_GATES'
    assert r['route_complete']and r['sources_unchanged']and not r.get('native_process_saved',False)
    assert r['image_id']==image and r['native_log']['single_entrypoint']
    assert all(r[k]==v for k,v in GLOBAL.items())
    assert r['global_source']['run']==39680690957
    assert r['global_source']['summary_sha256']=='925c5e31e3b55d483032ddfa7b494d6a2f8ac3b1bd4374fda382b9ffe5c59359'
    assert r['retained_timing_contract']['clock_periods_ns']==[20,4,8,8]
    assert r['retained_timing_contract']['derating_percent']==5
    assert re.fullmatch('[0-9a-f]{64}',r['routed_odb_sha256'])
    counts=r['native_log']['completed_violation_counts']
    assert counts and all(type(x)is int and x>=0 for x in counts)
    # Nonzero DRT counts remain a physical failure, not a reason to discard
    # useful genuine RC/STA measurements. The final gate requires zero.
    return True
def controls():
    spec=dict(run=19,attempt=1,group='mainchip-repair-deep-drt-cross',source_head='a'*40,
      controller_sha256=INITIAL,summary_sha256='1'*64,parts_sha256='2'*64)
    live=dict(id=19,run_attempt=1,head_sha='a'*40,head_branch='codex/complete-open-work',
      path='.github/workflows/mainchip-repair-deep-drt-cloud.yml',status='completed',conclusion='success')
    r=dict(source_head='a'*40,run_id=19,stage='cross',controller_sha256=INITIAL,
      status='COMPLETE_NATIVE_DRT_REQUIRES_ALL_POSTROUTE_PHYSICAL_RC_STA_GATES',
      route_complete=True,sources_unchanged=True,image_id='fixture-only',
      native_log=dict(single_entrypoint=True,completed_violation_counts=[5,0]),
      global_source=dict(run=39680690957,summary_sha256='925c5e31e3b55d483032ddfa7b494d6a2f8ac3b1bd4374fda382b9ffe5c59359'),
      retained_timing_contract=dict(clock_periods_ns=[20,4,8,8],derating_percent=5),
      routed_odb_sha256='3'*64,**GLOBAL)
    validate(spec,live,r,'fixture-only');faults=[]
    mutations=[('live-run','live','status','in_progress'),('failed-run','live','conclusion','failure'),
      ('wrong-source','live','head_sha','b'*40),('old-workflow','live','path','.github/workflows/mainchip-active-drt-cloud.yml'),
      ('old-group','spec','group','mainchip-active-drt-cross'),('incomplete-route','report','route_complete',False),
      ('saved-not-completed','report','native_process_saved',True),('different-image','report','image_id','wrong'),
      ('changed-source','report','sources_unchanged',False),('missing-native-log','report','native_log',{}),
      ('relaxed-clock','report','retained_timing_contract',dict(clock_periods_ns=[40,8,16,16],derating_percent=5)),
      ('relaxed-derate','report','retained_timing_contract',dict(clock_periods_ns=[20,4,8,8],derating_percent=0))]
    mutations += [('changed-'+k,'report',k,0 if isinstance(v,int)else'0'*64)for k,v in GLOBAL.items()]
    for label,which,key,value in mutations:
        a,b,c=copy.deepcopy((spec,live,r));{'spec':a,'live':b,'report':c}[which][key]=value
        try:validate(a,b,c,'fixture-only')
        except (AssertionError,KeyError):faults.append(label)
        else:raise AssertionError('Accepted '+label)
    assert len(faults)==17
    return dict(status='PASS_COMPLETED_REPAIRED_ROUTE_DESCRIPTOR_CONTROLS_NOT_NATIVE_PROOF',rejected=faults)
if __name__=='__main__':
    import json
    print(json.dumps(controls()))
