#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Admit the genuine completed saved-process route without rewriting its history."""
import ast,copy,hashlib,json,os
from pathlib import Path
from check_mainchip_route12_completed_source import GLOBAL
from cloud_mainchip_postroute_review import source_hash
ROOT=Path(__file__).resolve().parents[1]
RECEIPT='docs/evidence/mainchip-route12-completed-saved-source-20261025.json'
SNAPSHOT='docs/evidence/mainchip-route12-completed-wrapper-source-20261025.py'
METHOD='scripts/mainchip-saved-postroute-methods.json'
WRAPPER='scripts/cloud_mainchip_saved7200_next.py'
WRAPPER_SHA='b59e08eece9cf3ac35d13319959e7a2f7fde50d7a873d7aabb8b5a327905170c'
GENERATED='9c2b35b0c037541626e710dff6a7461ca47a6f95952616f2c660da14d253e280'
SPEC=dict(run=40199977397,attempt=1,group='mainchip-route12-saved7200-next',
 source_head='e291495bea09cfeb38df625c21f6697f90625749',controller_sha256=WRAPPER_SHA,
 summary_sha256='0f5123d3ea073c93b4e4733e778605e2108719053714b3cbe2f0062b65580c76',
 parts_sha256='7b01425b64943a52fa98bf069d9ead9bf6b0e0d0d1ddaf34db10664de7a36f72')
IMAGE='sha256:113cc2e5500e0152a2137336ae092c7caeccb5f8b95b17874fd649d097b8daf8'
def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def methods():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'
    m=json.loads((ROOT/METHOD).read_bytes())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    return m
def receipt():
    methods()
    return json.loads((ROOT/RECEIPT).read_bytes())
def generated_controller():
    # Execute only the actual source-derivation function, never the router/controller.
    src=(ROOT/SNAPSHOT).read_bytes();assert hashlib.sha256(src).hexdigest()==WRAPPER_SHA
    tree=ast.parse(src);functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='adapted_source']
    assert len(functions)==1
    ns=dict(ROOT=ROOT,FROZEN='scripts/cloud_mainchip_route12_drt_continuation.py',
        FROZEN_SHA='08b91df1a93d28c4acda1dbeae3b45e53af8393664ceaf71038808bdb0707eee',ast=ast,hashlib=hashlib)
    exec(compile(ast.Module(body=functions,type_ignores=[]),SNAPSHOT,'exec'),ns)
    code,edits=ns['adapted_source']()
    assert hashlib.sha256(code.encode()).hexdigest()==GENERATED and len(edits)==9
    return dict(sha256=GENERATED,exact_source_edits=edits,router_executed=False)
def validate(spec,live,r,image):
    pin=receipt();expected=pin['projection']
    assert spec==SPEC and image==IMAGE
    for k,v in pin['run'].items():assert live[k]==v,('live',k)
    for k,v in expected.items():
        if k not in ('native_inner_report','outputs'):assert type(r[k])is type(v)and r[k]==v,('wrapper',k)
    n=r['native_inner_report'];want=expected['native_inner_report']
    for k,v in want.items():
        if k=='global_source':
            for a,b in v.items():
                if b is not None:assert n[k][a]==b,('global',a)
        else:assert type(n[k])is type(v)and n[k]==v,('inner',k)
    assert all(n[k]==v for k,v in GLOBAL.items())
    assert not n.get('native_process_saved',False)and n['continuation']['native_process_saved']is False
    assert n['image_id']==image and n['native_log']['single_entrypoint']is True
    assert n['sources_unchanged']is True and r['historical_sources_unchanged_proven']is False
    assert r['old_scheduling_perturbation_retained']is True
    assert n['retained_timing_contract']['clock_periods_ns']==[20,4,8,8]
    assert n['retained_timing_contract']['derating_percent']==5
    counts=n['native_log']['completed_violation_counts']
    assert counts and all(type(x)is int and x>=0 for x in counts)and counts[-1]==0
    for p,h in expected['outputs'].items():assert r['outputs'][p]==h,p
    assert r['outputs']['inner-controller-result.json']==r['inner_controller_result_sha256']
    assert r['outputs']['work/detailed-route.odb']==n['routed_odb_sha256']
    return True
def verify_archive(spec,r,folder):
    pin=receipt()['projection'];folder=Path(folder)
    assert source_hash(WRAPPER,spec['source_head'])==WRAPPER_SHA
    derivation=generated_controller()
    selected=('inner-controller-result.json','current-inputs-before.json','current-inputs-after.json',
        'no-gdb-runtime-result.json','work/detailed-route.odb','work/detailed-route.drc',
        'work/native.log','work/boots.log','work/before-guide-read.odb','work/drt-done')
    for p in selected:
        f=folder/p;assert f.is_file()and not f.is_symlink()and sha(f)==pin['outputs'][p],p
    inner=json.loads((folder/'inner-controller-result.json').read_bytes())
    assert inner==r['native_inner_report']and inner['controller_sha256']==GENERATED
    assert json.loads((folder/'current-inputs-after.json').read_bytes())==r['current_inputs_after']
    runtime=json.loads((folder/'no-gdb-runtime-result.json').read_bytes())
    assert runtime==inner['unobserved_runtime_binding']
    assert runtime['gdb_attached']is False and runtime['target_detached']is True
    return dict(actual_inner_and_runtime_verified=True,derivation=derivation,
        current_inputs_unchanged=True,historical_sources_unchanged_proven=False,
        old_scheduling_perturbation_retained=True)
def controls():
    base=receipt();r=base['projection'];live=base['run'];validate(SPEC,live,r,IMAGE)
    faults=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,KeyError,TypeError,ValueError):faults.append(name)
        else:raise AssertionError('Accepted altered completed source: '+name)
    for key,value in [('run',40199977398),('attempt',2),('group','mainchip-route12-drt-cross'),
            ('source_head','a'*40),('controller_sha256',GENERATED),('summary_sha256','0'*64),('parts_sha256','0'*64)]:
        q=copy.deepcopy(SPEC);q[key]=value;reject('descriptor-'+key,lambda q=q:validate(q,live,r,IMAGE))
    for key,value in [('status','in_progress'),('conclusion','failure'),('path','.github/workflows/mainchip-route12-drt-cloud.yml'),
            ('head_branch','codex/complete-open-work'),('head_sha','a'*40),('run_attempt',2),('id',1)]:
        q=copy.deepcopy(live);q[key]=value;reject('live-'+key,lambda q=q:validate(SPEC,q,r,IMAGE))
    for key,value in [('routing_complete',False),('continuation_accepted',False),('native_route_returned',False),
            ('gdb_attached',True),('cold_restart',True),('historical_sources_unchanged_proven',True),
            ('old_scheduling_perturbation_retained',False),('new_saved_process_images',{'saved':True}),
            ('generated_program_sha256','0'*64),('inner_controller_result_sha256','0'*64),('full_phy_accepted',True)]:
        q=copy.deepcopy(r);q[key]=value;reject('wrapper-'+key,lambda q=q:validate(SPEC,live,q,IMAGE))
    for key,value in [('route_complete',False),('sources_unchanged',False),('controller_sha256',WRAPPER_SHA),
            ('image_id','wrong'),('source_head','a'*40),('routed_odb_sha256','0'*64),
            ('global_odb_sha256','0'*64),('candidate_netlist_sha256','0'*64),
            ('source_sdc_sha256','0'*64),('global_candidate_instance_count',1),('native_process_saved',True),
            ('retained_timing_contract',dict(clock_periods_ns=[40,8,16,16],derating_percent=0))]:
        q=copy.deepcopy(r);q['native_inner_report'][key]=value;reject('inner-'+key,lambda q=q:validate(SPEC,live,q,IMAGE))
    for name in ('work/detailed-route.odb','work/native.log','inner-controller-result.json','current-inputs-after.json'):
        q=copy.deepcopy(r);q['outputs'][name]='0'*64;reject('payload-'+name,lambda q=q:validate(SPEC,live,q,IMAGE))
    assert len(faults)==41 and len(set(faults))==41
    return dict(status='PASS_COMPLETED_SAVED_ROUTE_ADMISSION_41_REFUSALS_NOT_NATIVE_SIGNOFF',
        positive='Authenticated critical-field projection only; real archive/runtime is checked separately by native stage',
        generated_controller=generated_controller(),rejected=faults,native_executed=False)
