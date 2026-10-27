#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted exact-contact and complete-observer fixtures; no acquired waveform or simulator."""
import copy,json,tempfile,types
from pathlib import Path
from unittest import mock
import numpy as np
import cloud_tx_phase_reset334_tail_m4_stage_capture as controller
import tx_phase_reset334_tail_m4_stage_diagnosis as observer
import tx_phase_reset334_tail_m4_stage_pairs as pairs
import tx_phase_reset334_tail_m4_stage_resources as resources

def acquired_projection():
    spec,probe=pairs.descriptor()
    index=json.loads(observer.old.pin(pairs.ROOT/spec['prior_index']['path'],spec['prior_index']['sha256']))
    assert index['current_capture_sha256']==spec['capture_sha256']
    assert index['native_pair_nodes']==probe['native_pair_nodes']
    assert index['source_bound_tail_topology']==probe['added_source_bound_topology']
    instances=[]
    for instance,variant,physical in [('xdut','p','phase_l1_k0'),('xloadm','n','phase_l2_k0'),('xloadq','p','phase_l2_k1')]:
        q={name.split(':',1)[1]:value for name,value in spec['original_pairs'].items()if name.startswith(instance+':')}
        actual_ports=q['fixture_input']+q['master']+q['slave']+q['arm_external']+['fixture_avdd','0','fixture_sub','0']
        instances.append(dict(instance=instance,variant=variant,physical_role=physical,actual_ports=actual_ports,
          model_sha256=spec['model_sha256'][variant],probe_pairs={k:q[k]for k in ('run','release','native_clock','arm_conditioned')},
          oracle=dict(first_falls=[index['first_fall_windows'][instance+':first_fall_'+str(i)]['prescribed_event']for i in range(2)])))
    topology=copy.deepcopy(probe['added_source_bound_topology'])
    nodes={node for role in probe['all_native_HBT_roles'].values()for node in role['terminals']if node!='0'}
    nodes|={node for pair in spec['original_pairs'].values()for node in pair}
    nodes|={row['node']for passive in topology['passive_accesses'].values()for row in passive['terminals'].values()if row['node']!='0'}
    nodes|=set(probe['thermal_nodes'])
    vectors=sorted({'v('+node+')'for node in nodes}|{'@q.'+name+'.qnpn13g2[ic]'for name in probe['all_native_HBT_roles']})
    assert len(vectors)<4726
    vectors+=['v(synthetic_unused_'+str(i)+')'for i in range(4726-len(vectors))]
    c=dict(instances=instances,hbt=copy.deepcopy(probe['all_native_HBT_roles']),vectors=vectors,
      thermal_nodes=probe['thermal_nodes'],limits=probe['original_limits'],timing=probe['original_timing'],
      binding_summary_sha256=spec['binding_summary_sha256'])
    assert len(c['hbt'])==318 and len(c['thermal_nodes'])==390 and len(c['vectors'])==len(set(c['vectors']))==4726
    # The full acquired roles/pairs/topology are exact. Ports irrelevant to pairs and
    # missing unobserved vectors are explicit synthetic collaborators, not a recovered contract.
    return c,topology,spec,probe

def contact_controls():
    c,topology,spec,probe=acquired_projection()
    actual,proof=pairs.bind(c,topology)
    assert len(actual)==36 and proof['original_pairs']==24 and proof['added_pairs']==12
    assert {name:actual[name]for name in spec['original_pairs']}==probe['native_pair_nodes']
    refused=[]
    def reject(label,change):
        cc,tt=copy.deepcopy(c),copy.deepcopy(topology)
        change(cc,tt)
        assert (cc,tt)!=(c,topology),label
        try:pairs.bind(cc,tt)
        except(AssertionError,KeyError):refused.append(label)
        else:raise AssertionError('Accepted stage contact mutation '+label)
    for name,entries in spec['endpoint_provenance'].items():
        for ordinal,entry in enumerate(entries):
            binding=entry['source_binding']
            if 'native'in binding:
                def change(cc,tt,b=binding):
                    cc['hbt'][b['native']]['terminals'][pairs.HBT_TERMS.index(b['terminal'])]='xdut.wrong_contact'
            else:
                def change(cc,tt,b=binding):
                    tt['passive_accesses']['xdut:'+b['source_instance']]['terminals'][b['terminal']]['node']='xdut.wrong_contact'
            reject(name+':endpoint_'+str(ordinal),change)
    name=next(iter(spec['added_pairs']));entry=spec['endpoint_provenance'][name][0]['source_binding']
    reject('wrong_source_role',lambda cc,tt:cc['hbt'][entry['native']].update(source_instance='PHASE__wrong'))
    reject('wrong_native_id',lambda cc,tt:cc['hbt'][entry['native']].update(native_id=9999))
    reject('wrong_parent_model',lambda cc,tt:cc['instances'][0].update(model_sha256='0'*64))
    reject('wrong_child_model',lambda cc,tt:cc['instances'][1].update(model_sha256='0'*64))
    reject('wrong_binding',lambda cc,tt:cc.update(binding_summary_sha256='0'*64))
    for name,pair in spec['added_pairs'].items():
        reject('missing_vector_'+name,lambda cc,tt,node=pair[0]:cc['vectors'].remove('v('+node+')'))
    for name in spec['added_pairs']:
        changed=copy.deepcopy(actual);changed[name]=list(reversed(changed[name]))
        assert changed!=actual
        try:pairs.check_pairmap(c,changed)
        except AssertionError:refused.append('reversed_polarity_'+name)
        else:raise AssertionError('Accepted reversed stage pair '+name)
    descriptor_path=pairs.ROOT/pairs.DESCRIPTOR
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder);path=root/pairs.DESCRIPTOR;path.parent.mkdir(parents=True)
        path.write_bytes(descriptor_path.read_bytes()+b' ')
        with mock.patch.object(pairs,'ROOT',root):
            try:pairs.descriptor()
            except AssertionError:refused.append('tampered_exact_descriptor')
            else:raise AssertionError('Accepted changed exact descriptor')
    _,native,_=controller.snapshot()
    for label,change in [('wrong_capture',lambda q:q['outputs'].__setitem__('work/wave.raw','0'*64)),
      ('wrong_current_models',lambda q:q['current_RC_model_hashes'].__setitem__('p','0'*64))]:
        q=copy.deepcopy(native);change(q);assert q!=native
        try:controller.validate_result(q)
        except AssertionError:refused.append(label)
        else:raise AssertionError('Accepted changed capture/model '+label)
    assert len(refused)==56,len(refused)
    return dict(positive=1,refusals=refused,actual_complete_acquired_roles=318,actual_complete_passive_records=168,
      original_pair_count=24,added_pair_count=12,endpoint_count=24,
      complete_acquired_contract_claimed=False,derived_observed_vector_names=2017,synthetic_unused_vectors=2709,
      synthetic_unused_vectors_and_unmeasured_ports_explicit=True,
      binding=proof)

def observer_controls():
    c,topology,spec,probe=acquired_projection()
    pairmap,_=pairs.bind(c,topology)
    t=np.linspace(0.,34e-9,114525)
    base=np.full_like(t,1.3);zero=np.zeros_like(t)
    values={name:base for name in c['vectors']}
    for name,role in c['hbt'].items():
        for terminal,node in zip(pairs.HBT_TERMS,role['terminals'],strict=True):
            if node!='0':values['v('+node+')']=np.full_like(t,{'C':1.4,'B':.95,'E':.4,'S':0.}[terminal])
        values['@q.'+name+'.qnpn13g2[ic]']=np.full_like(t,.001)
    for name in c['thermal_nodes']:values['v('+name+')']=zero
    for index,(name,(p,n))in enumerate(pairmap.items()):
        # Distinct phase and extrema, repeated exact zero plateaus on an added pair.
        y=.26*np.sin(2*np.pi*(t/(1.7e-9+index*1e-11)+index/13.))
        values['v('+p+')']=1.3+y/2;values['v('+n+')']=1.3-y/2
    added=next(iter(spec['added_pairs']));p,n=pairmap[added]
    at=int(np.searchsorted(t,c['instances'][0]['oracle']['first_falls'][0]['fall_s']))
    values['v('+p+')'][at:at+8]=1.3+np.array([-.1,0.,0.,.1,.1,0.,0.,-.1])/2
    values['v('+n+')'][at:at+8]=1.3-np.array([-.1,0.,0.,.1,.1,0.,0.,-.1])/2
    # Keep the four known tail intervals empty in this synthetic selector fixture.
    for name in observer.TARGETS:
        terms=c['hbt'][name]['terminals']
        values['v('+terms[0]+')']=np.full_like(t,1.1)
        values['v('+terms[2]+')']=np.full_like(t,.4)
    active=np.flatnonzero(t>=observer.old.START)
    hbt={}
    for name,role in c['hbt'].items():
        cv,bv,ev,_=[zero if node=='0'else values['v('+node+')']for node in role['terminals']]
        hbt[name]=dict(passed=True,min_post_vce_v=float(np.min((cv-ev)[active])))
    screens={}
    for name,(p,n)in observer.old.pairs(c).items():
        instance,key=name.split(':',1)
        y=values['v('+p+')']-values['v('+n+')']
        screens.setdefault(instance,dict(pair_ranges={}))['pair_ranges'][key]=dict(minimum_v=float(y.min()),maximum_v=float(y.max()))
    replay=dict(passed=False,errors=[],diagnostics=[],measurement=dict(hbt_safety=hbt,three_model_screens=screens),
      capture=dict(raw_sha256=spec['capture_sha256'],synthetic_array_fixture_only=True))
    _,native,_=controller.snapshot()
    result=copy.deepcopy(native);result['review']=replay
    prior=list(result['original17_HBT_rejection']['all17_original_failed_HBT_records'])
    assert len(prior)==17
    emitted={};calls=[]
    def emit(name,value):
        assert name not in emitted;emitted[name]=value
    def review(case,contract,code):
        assert contract is c and code==0;calls.append('original_review');return copy.deepcopy(replay)
    screen=types.SimpleNamespace(review_capture=review)
    with tempfile.TemporaryDirectory()as folder:
        case=Path(folder);(case/'contract.json').write_text(json.dumps(c))
        with mock.patch.object(observer.old,'contract_check',return_value=c),             mock.patch.object(observer,'topology',return_value=topology),             mock.patch.object(observer,'read_streamed_wave',return_value=(t,values,replay['capture'])),             mock.patch.object(resources,'mem_available',return_value=32*1024**3):
            diagnosis=observer.observe(case,result,screen,{'explicit_synthetic_payload_collaborator':True},emit)
    assert calls==['original_review']
    assert len(diagnosis['native_pair_nodes'])==36 and diagnosis['original_measurement']==replay['measurement']
    assert diagnosis['four_tail_violation_intervals']=={name:[]for name in observer.TARGETS}
    assert diagnosis['source_bound_stage_pairs']['added_pairs']==12
    assert len(diagnosis['first_fall_windows'])==6 and len(diagnosis['requested_fixed_samples'])==298
    assert all(len(frame['pairs'])==36 and len(frame['hbt'])==318 and len(frame['resistor_thermal_states'])==390
      and len(frame['passive_accesses'])==168 and len(frame['tail_headroom'])==12 for frame in diagnosis['frames'].values())
    full_plan=diagnosis['resource_plan']
    assert resources.validate_frames(full_plan,diagnosis['frames'],t)
    old_plan=resources.plan(t,values,c,replay,prior,{},observer.intervals)
    assert set(old_plan['required_frame_rows'])<=set(full_plan['required_frame_rows'])
    assert set(full_plan['required_frame_rows'])-set(old_plan['required_frame_rows'])
    baseline,_=observer.analysis_program()
    baseline=baseline(t,values,c,replay)
    assert {name:diagnosis['pair_extrema_both_signs'][name]for name in spec['original_pairs']}==baseline['pair_extrema_both_signs']
    assert {name:diagnosis['native_pair_crossings'][name]for name in spec['original_pairs']}==baseline['native_pair_crossings']
    assert diagnosis['requested_fixed_samples']==baseline['requested_fixed_samples']
    for name,window in baseline['first_fall_windows'].items():
        now=diagnosis['first_fall_windows'][name]
        assert all(now[k]==window[k]for k in ('prescribed_event','bounds_s','original_limit_s'))
        assert {pair:now['pair_crossings'][pair]for pair in spec['original_pairs']}==window['pair_crossings']
    for key,frame in baseline['frames'].items():
        current=copy.deepcopy(diagnosis['frames'][key])
        current['pairs']={name:current['pairs'][name]for name in spec['original_pairs']}
        current.pop('tail_headroom');current.pop('passive_accesses')
        assert current==frame
    # Exact plateau departures: no interpolation, and equality itself is not a crossing.
    events=diagnosis['native_pair_crossings'][added]['0.0']
    chosen=[e for e in events if at<=e['rows'][0]<at+7]
    assert [(e['rows'],e['direction'])for e in chosen]==[([at+2,at+3],'rising'),([at+6,at+7],'falling')]
    refused=[]
    def reject(label,fn,kind=AssertionError):
        try:fn()
        except kind:refused.append(label)
        else:raise AssertionError('Accepted stage selector mutation '+label)
    reject('old24_plan_with_expanded_frames',lambda:resources.validate_frames(old_plan,diagnosis['frames'],t))
    for label,change in [('missing_frame',lambda q:q.pop(next(iter(q)))),
      ('wrong_frame_time',lambda q:q[next(iter(q))].update(time_s=-1.)),
      ('wrong_frame_row',lambda q:q[next(iter(q))].update(row=-1)),
      ('extra_frame',lambda q:q.update({'999999':dict(row=999999,time_s=0.)}))]:
        frames=copy.deepcopy(diagnosis['frames']);change(frames)
        reject(label,lambda frames=frames:resources.validate_frames(full_plan,frames,t))
    short=dict(pairmap);short.pop(added)
    reject('omitted_added_pair_in_plan',lambda:resources.plan(t,values,c,replay,prior,{},observer.intervals,pairmap=short))
    with mock.patch.object(resources,'MAX_FRAMES',len(full_plan['required_frame_rows'])-1):
        reject('expanded_frame_limit',lambda:resources.plan(t,values,c,replay,prior,{},observer.intervals,pairmap=pairmap),resources.ResourceLimit)
    with mock.patch.object(resources,'MAX_CROSSINGS',full_plan['counts']['crossings']-1):
        reject('expanded_crossing_limit',lambda:resources.plan(t,values,c,replay,prior,{},observer.intervals,pairmap=pairmap),resources.ResourceLimit)
    analyze,_=observer.analysis_program(pairmap)
    # Exact old guard would try to find internal diagnostic names in acceptance pair_ranges.
    ns=dict(analyze.__globals__,DIAGNOSTIC_PAIR_NAMES=set())
    old_guard=types.FunctionType(analyze.__code__,ns)
    try:old_guard(t,values,c,replay)
    except KeyError as error:
        assert error.args==(added.split(':',1)[1],)
        frames=[];tb=error.__traceback__
        while tb is not None:frames.append(tb.tb_frame.f_code);tb=tb.tb_next
        assert old_guard.__code__ in frames
        refused.append('original_acceptance_range_guard_not_applicable_to_added_diagnostic_pairs')
    else:raise AssertionError('Old original-only range guard unexpectedly accepted added pairs')
    assert len(refused)==9
    return dict(positive=1,refusals=refused,actual_complete_observer_called=True,original_review_calls=1,
      frame_count=len(diagnosis['frames']),expanded_counts=full_plan['counts'],original24_plan_counts=old_plan['counts'],
      original24_numeric_observations_and_frames_exact=True,all_six_prescribed_windows_and298_samples_exact=True,
      exact_zero_plateau_departures=True,all318_HBT_and390_thermal_states_and168_passives_per_frame=True,
      synthetic_arrays_and_contract_transport_collaborators_only=True,acquired_waveform_read=False,
      native_numerical_review_executed=False,source_capture_electrical_acceptance=False)

def controls():
    contacts=contact_controls();selection=observer_controls()
    return dict(status='PASS_SOURCE_BOUND36_PAIR_OBSERVER_SYNTHETIC_CONTROLS_ONLY',
      positive=2,refusals=len(contacts['refusals'])+len(selection['refusals']),
      contacts=contacts,selection=selection,raw_capture_or_archive_accessed=False,
      new_simulation=False,physical_cause_established=False)
