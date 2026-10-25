#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""A completed router for this exact repaired chip is required before RC/STA."""
import copy,re
INITIAL='00ea591918771c60522a657e954b07b3a7d826dbb0b7fd70749aee49a3a81583'
CONTINUATION='08b91df1a93d28c4acda1dbeae3b45e53af8393664ceaf71038808bdb0707eee'
GLOBAL=dict(global_candidate_instance_count=153130,
 global_odb_sha256='2d3dfa6ed917fd0d06b20109f3044073f60bbe263f59d8f31ac4913e1a7a787a',
 global_guides_sha256='54ae78b49f70b05e007edc151c67c64a7eed4fd9a9ce0aed6d7898bb3286dcde',
 candidate_netlist_sha256='3c053c4cda51a001b926cce347b97de5c825cbff2082de550eeb9e31ff7fe5cd',
 source_sdc_sha256='19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597')
def validate(spec,live,r,image):
    assert set(spec)=={'run','attempt','group','source_head','controller_sha256','summary_sha256','parts_sha256'}
    assert type(spec['run'])is int and spec['run']>0 and spec['attempt']==1
    assert spec['group']in ('mainchip-route12-drt-initial','mainchip-route12-drt-cross')
    assert re.fullmatch('[0-9a-f]{40}',spec['source_head'])
    assert all(re.fullmatch('[0-9a-f]{64}',spec[k])for k in ('controller_sha256','summary_sha256','parts_sha256'))
    paths={'.github/workflows/mainchip-route12-drt-cloud.yml':INITIAL,
      '.github/workflows/mainchip-route12-drt-continuation-cloud.yml':CONTINUATION}
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
    assert r['global_source']['run']==39910632183
    assert r['global_source']['summary_sha256']=='0c7f6a86849d32ae853726ab448da0e4c2f71373956220c95c434657247e9d60'
    assert r['retained_timing_contract']['clock_periods_ns']==[20,4,8,8]
    assert r['retained_timing_contract']['derating_percent']==5
    assert re.fullmatch('[0-9a-f]{64}',r['routed_odb_sha256'])
    counts=r['native_log']['completed_violation_counts']
    assert counts and all(type(x)is int and x>=0 for x in counts)
    # Nonzero DRT counts remain a physical failure, not a reason to discard
    # useful genuine RC/STA measurements. The final gate requires zero.
    return True
def controls():
    spec=dict(run=19,attempt=1,group='mainchip-route12-drt-cross',source_head='a'*40,
      controller_sha256=INITIAL,summary_sha256='1'*64,parts_sha256='2'*64)
    live=dict(id=19,run_attempt=1,head_sha='a'*40,head_branch='codex/complete-open-work',
      path='.github/workflows/mainchip-route12-drt-cloud.yml',status='completed',conclusion='success')
    r=dict(source_head='a'*40,run_id=19,stage='cross',controller_sha256=INITIAL,
      status='COMPLETE_NATIVE_DRT_REQUIRES_ALL_POSTROUTE_PHYSICAL_RC_STA_GATES',
      route_complete=True,sources_unchanged=True,image_id='fixture-only',
      native_log=dict(single_entrypoint=True,completed_violation_counts=[5,0]),
      global_source=dict(run=39910632183,summary_sha256='0c7f6a86849d32ae853726ab448da0e4c2f71373956220c95c434657247e9d60'),
      retained_timing_contract=dict(clock_periods_ns=[20,4,8,8],derating_percent=5),
      routed_odb_sha256='3'*64,**GLOBAL)
    validate(spec,live,r,'fixture-only')
    s2,l2,r2=copy.deepcopy((spec,live,r));s2['controller_sha256']=r2['controller_sha256']=CONTINUATION
    l2['path']='.github/workflows/mainchip-route12-drt-continuation-cloud.yml'
    validate(s2,l2,r2,'fixture-only');faults=[]
    mutations=[('live-run','live','status','in_progress'),('failed-run','live','conclusion','failure'),
      ('wrong-source','live','head_sha','b'*40),('old-workflow','live','path','.github/workflows/mainchip-active-drt-cloud.yml'),
      ('old-group','spec','group','mainchip-active-drt-cross'),('incomplete-route','report','route_complete',False),
      ('saved-not-completed','report','native_process_saved',True),('different-image','report','image_id','wrong'),
      ('changed-source','report','sources_unchanged',False),('missing-native-log','report','native_log',{}),
      ('relaxed-clock','report','retained_timing_contract',dict(clock_periods_ns=[40,8,16,16],derating_percent=5)),
      ('relaxed-derate','report','retained_timing_contract',dict(clock_periods_ns=[20,4,8,8],derating_percent=0)),
      ('wrong-global-source','report','global_source',dict(run=39680690957,summary_sha256='0'*64)),
      ('negative-drc-count','report','native_log',dict(single_entrypoint=True,completed_violation_counts=[-1])),
      ('no-final-drc-count','report','native_log',dict(single_entrypoint=True,completed_violation_counts=[]))]
    mutations += [('changed-'+k,'report',k,0 if isinstance(v,int)else'0'*64)for k,v in GLOBAL.items()]
    for label,which,key,value in mutations:
        a,b,c=copy.deepcopy((spec,live,r));{'spec':a,'live':b,'report':c}[which][key]=value
        try:validate(a,b,c,'fixture-only')
        except (AssertionError,KeyError):faults.append(label)
        else:raise AssertionError('Accepted '+label)
    assert len(faults)==20
    return dict(status='PASS_ROUTE12_COMPLETED_DESCRIPTOR_CONTROLS_NOT_NATIVE_PROOF',rejected=faults)
if __name__=='__main__':
    import json
    print(json.dumps(controls()))
