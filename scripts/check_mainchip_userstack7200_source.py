#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/admission/metadata controls only; no native capsule or process."""
import ast,copy,hashlib,json,os
from pathlib import Path
import mainchip_userstack7200_admission as a
import cloud_mainchip_userstack7200_continue as c
from check_mainchip_userstack_native_source import check as original_controls
def validate_generated(program):
    original=(c.ROOT/c.FROZEN).read_text()
    before={n.name:ast.dump(n)for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)}
    after={n.name:ast.dump(n)for n in ast.parse(program).body if isinstance(n,ast.FunctionDef)}
    assert before.keys()==after.keys()and [n for n in before if before[n]!=after[n]]==['main']
    for text in ["assert 600<=budget<=7200",
      "assert len(raw)>len(prefix),'No observable native DRT progress after cross-runner restore'",
      "assert re.search(r'Completing\\s+\\d+%|Start \\d+(?:st|nd|rd|th) optimization iteration|Number of violations',appended),'No native optimization progress witness after restore'",
      "assert args.stage=='cross','Continuation controller cannot start a fresh native route'",
      "assert sha(Path(__file__))==r['controller_sha256']and sha(tcl)==r['route_script']['sha256'];r['sources_unchanged']=True"]:
        assert program.count(text)==1,text
    assert 'import gdb'not in program and 'ptrace'not in program
    assert 'start_probe('not in program and 'finish_probe('not in program
    return True
def check():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=c.methods();program,labels=c.adapted_source();validate_generated(program)
    assert hashlib.sha256(program.encode()).hexdigest()==m['generated_controller_sha256'] and len(labels)==9
    old=ast.parse((c.ROOT/'scripts/cloud_mainchip_userstack_diagnostic.py').read_text())
    now=ast.parse(Path(c.__file__).read_text())
    for name in ('current_inputs','recheck_inputs','verify_no_progress_site'):
        one=next(n for n in old.body if isinstance(n,ast.FunctionDef)and n.name==name)
        two=next(n for n in now.body if isinstance(n,ast.FunctionDef)and n.name==name)
        assert ast.dump(one)==ast.dump(two),name
    oldbridge=ast.parse((c.ROOT/'scripts/mainchip_latest_userstack_bridge.py').read_text())
    newbridge=ast.parse(Path(a.__file__).read_text())
    one=next(n for n in oldbridge.body if isinstance(n,ast.FunctionDef)and n.name=='validate_current_rows')
    two=next(n for n in newbridge.body if isinstance(n,ast.FunctionDef)and n.name=='validate_current_rows')
    assert ast.dump(one)==ast.dump(two)
    original=original_controls();assert original['status']=='PASS39_SOURCE_BINDING_CONTROLS_NOT_NATIVE_ATTACH'
    release=a.api('releases/423280373');run=a.api('actions/runs/'+str(a.RUN));tag=a.api('git/ref/tags/'+release['tag_name'])
    assert a.transport_identity(run,release,tag)
    jobs=a.api('actions/runs/'+str(a.RUN)+'/jobs?per_page=100')['jobs']
    assert {x['id']for x in jobs}=={121128018929,121128110449}and all(x['conclusion']=='success'for x in jobs)
    raw=a.api('releases/assets/674649253',raw=True);outer=a.source_report(raw)
    assert len(a.selected_names(outer))==39
    rejected=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,TypeError):rejected.append(name)
        else:raise AssertionError('Accepted corruption: '+name)
    def setpath(obj,path,value):
        target=obj
        for key in path[:-1]:target=target[key]
        target[path[-1]]=value
    transports=[('run-id','run',['id'],1),('head','run',['head_sha'],'0'*40),
        ('attempt','run',['run_attempt'],2),('unfinished','run',['status'],'in_progress'),
        ('failed','run',['conclusion'],'failure'),('workflow','run',['path'],'unrelated.yml'),
        ('release-id','release',['id'],1),('release-tag','release',['tag_name'],'wrong'),
        ('draft','release',['draft'],True),('tag-type','tag',['object','type'],'tag'),
        ('tag-source','tag',['object','sha'],'0'*40)]
    for name,target,path,value in transports:
        x={'run':copy.deepcopy(run),'release':copy.deepcopy(release),'tag':copy.deepcopy(tag)}
        setpath(x[target],path,value);reject(name,lambda x=x:a.transport_identity(x['run'],x['release'],x['tag']))
    for name,key,value in [('asset-size','size',1),('asset-digest','digest','sha256:'+'0'*64)]:
        q=copy.deepcopy(release);asset=next(x for x in q['assets']if x['id']==674649253);asset[key]=value
        reject(name,lambda q=q:a.transport_identity(run,q,tag))
    badouter=[('outer-status',['status'],'PASS'),('outer-head',['source_head'],'0'*40),
        ('outer-run',['run_id'],'1'),('old-generated',['generated_program_sha256'],'0'*64),
        ('inner-digest',['inner_controller_result_sha256'],'0'*64),
        ('old-rejection-waived',['expected_rejection','original_no_log_progress_rejection_reproduced'],False),
        ('old-success-invented',['native_controller_outcome'],'PASS'),
        ('old-route-returned',['native_route_returned'],True),('old-route-complete',['routing_complete'],True),
        ('missing-image',['new_saved_process_images'],{}),('changed-outputs',['outputs'],{}),
        ('not-detached',['native_userstack_finished','target_detached_before_checkpoint'],False)]
    for name,path,value in badouter:
        q=copy.deepcopy(outer);setpath(q,path,value);reject(name,lambda q=q:a.validate_outer(q))
    reject('changed-summary-bytes',lambda:a.source_report(raw[:-1]+b' '))
    reject('truncated-summary',lambda:a.source_report(raw[:-1]))
    # Shape fixture, not the original inner member: its exact SHA remains mandatory
    # during native file restoration, which these source controls never perform.
    inner=dict(status='FAIL_OR_ERROR',native_process_saved=True,source_head=a.HEAD,run_id=a.RUN,stage='cross',
        route_complete=False,final_timing_complete=False,full_phy_accepted=False,controller_sha256=a.CONTROLLER,
        checkpointed_elf_sha256=a.ELF,image_id=a.IMAGE,checkpoint_images=outer['new_saved_process_images'],
        error=repr(AssertionError(a.NO_PROGRESS)),retained_timing_contract=dict(clock_periods_ns=[20,4,8,8],derating_percent=5),
        native_log=dict(single_entrypoint=True,sha256=outer['outputs']['work/native.log']),
        outputs={n:h for n,h in outer['outputs'].items()if n.startswith(('work/','checkpoints/'))})
    assert a.inner_fields(inner,outer)
    badinner=[('inner-status',['status'],'PASS'),('unsaved',['native_process_saved'],False),
        ('inner-head',['source_head'],'0'*40),('inner-run',['run_id'],1),
        ('inner-controller',['controller_sha256'],'0'*64),('inner-elf',['checkpointed_elf_sha256'],'0'*64),
        ('inner-image',['image_id'],'wrong'),('clock-relaxed',['retained_timing_contract','clock_periods_ns'],[20,4,8,9]),
        ('derating-relaxed',['retained_timing_contract','derating_percent'],0),('other-error',['error'],'different'),
        ('two-boots',['native_log','single_entrypoint'],False),('fabricated-history',['sources_unchanged'],True)]
    for name,path,value in badinner:
        q=copy.deepcopy(inner);setpath(q,path,value);reject(name,lambda q=q:a.inner_fields(q,outer))
    success=dict(sources_unchanged=True,active_drt_cross_runner_progress_proven=True,
        continuation=dict(group=c.GROUP,run=123,source_head='a'*40),retained_timing_contract=inner['retained_timing_contract'],
        unobserved_runtime_binding=dict(target_detached=True,gdb_attached=False,runtime_closure=a.capsule()['runtime_closure']),
        route_complete=False,status='SAVED_CROSS_RUNNER_ACTIVE_DRT_PROGRESS_REQUIRES_FURTHER_CONTINUATION_AND_SIGNOFF',
        native_process_saved=True,checkpoint_images=inner['checkpoint_images'])
    assert c.qualify_success(success,123,'a'*40)['routing_complete']is False
    complete=copy.deepcopy(success);complete.update(route_complete=True,status='COMPLETE_NATIVE_DRT_REQUIRES_ALL_POSTROUTE_PHYSICAL_RC_STA_GATES')
    assert c.qualify_success(complete,123,'a'*40)['routing_complete']is True
    badsuccess=[('changed-current-source',['sources_unchanged'],False),('cpu-only',['active_drt_cross_runner_progress_proven'],False),
        ('wrong-group',['continuation','group'],'wrong'),('wrong-new-run',['continuation','run'],1),
        ('wrong-new-head',['continuation','source_head'],'0'*40),('new-clock-relaxed',['retained_timing_contract','clock_periods_ns'],[21,4,8,8]),
        ('new-derating-relaxed',['retained_timing_contract','derating_percent'],0),('still-traced',['unobserved_runtime_binding','target_detached'],False),
        ('invented-status',['status'],'PASS'),('not-checkpointed',['native_process_saved'],False),
        ('no-new-images',['checkpoint_images'],{}),('completion-invented',['route_complete'],True),
        ('debugger-inserted',['unobserved_runtime_binding','gdb_attached'],True),
        ('runtime-closure-changed',['unobserved_runtime_binding','runtime_closure'],{})]
    for name,path,value in badsuccess:
        q=copy.deepcopy(success);setpath(q,path,value);reject(name,lambda q=q:c.qualify_success(q,123,'a'*40))
    for name,old,new in [
        ('budget-expanded','assert 600<=budget<=7200','assert 600<=budget<=13200'),
        ('no-log-waived','assert len(raw)>len(prefix)','assert True'),
        ('native-progress-waived',"assert re.search(r'Completing\\s+\\d+%|Start \\d+(?:st|nd|rd|th) optimization iteration|Number of violations',appended)","assert True"),
        ('cold-stage-allowed',"assert args.stage=='cross'","assert True"),
        ('source-check-waived',"and sha(tcl)==r['route_script']['sha256'];r['sources_unchanged']=True",";r['sources_unchanged']=True")]:
        assert program.count(old)==1;reject(name,lambda old=old,new=new:validate_generated(program.replace(old,new)))
    assert len(rejected)==58 and len(set(rejected))==58
    return dict(status='PASS58_EXACT_DIAGNOSTIC_ADMISSION_AND_ROUTE_SOURCE_CONTROLS_ONLY',
        original39=original,rejected=rejected,actual_prior_outer_summary_authenticated=True,
        original_inner_member_restored=False,inner_positive_scope='METADATA SHAPE FIXTURE ONLY',
        native_process_restored=False,chip_started=False,gdb_attached=False,archive_downloaded=False,
        exact_derivation_edits=labels,generated_controller_sha256=hashlib.sha256(program.encode()).hexdigest())
if __name__=='__main__':print(json.dumps(check(),indent=2))
