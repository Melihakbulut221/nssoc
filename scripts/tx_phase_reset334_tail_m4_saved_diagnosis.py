#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current saved-capture diagnosis; frozen original measurements and native rows only."""
import ast,copy,json,types
import numpy as np
import tx_phase_reset334_saved_diagnosis as old
import tx_phase_reset334_tail_m4_transient_adapter as current
import tx_phase_reset334_tail_m4_saved_resources as resources
from cloud_tx_stream import read_streamed_wave
ROOT=old.ROOT
ORIGINAL='scripts/tx_phase_reset334_saved_diagnosis.py'
ORIGINAL_SHA='955430fe3719889dc195cc1b61d160e3882a6c5e0ffa23fa3b48ad4abb3f6a70'
TARGETS={'xdut.xd75':'PHASE__XM__XDATA','xdut.xd83':'PHASE__XM__XHOLD',
         'xdut.xd98':'PHASE__XS__XDATA','xdut.xd105':'PHASE__XS__XHOLD'}
EXTRA_PREFIXES=('PHASE__XRUN','PHASE__XCLK','PHASE__XRELEASE__XARM')
LEVEL_RES=('XLSP','XLSN','XLDP','XLDN','XLB','XLRP','XLRN','XSP','XSN','XDP','XDN')
SELECTOR_RES=('XBIAS','XRP','XRN','XBA','XBB')
def passive_source_names():
    result={p+'__'+n for p in EXTRA_PREFIXES for n in LEVEL_RES}
    result|={'PHASE__XRUN__'+n for n in ('XARM_P','XARM_N','XAND_SKEW')}
    result|={p+'__'+n for p in TARGETS.values()for n in SELECTOR_RES}
    assert len(result)==56
    return result
encode=current.encode
digest=current.digest

def analysis_program():
    text=(ROOT/ORIGINAL).read_text();assert digest(text)==ORIGINAL_SHA
    edits=[
      ("failed={n:r for n,r in h.items()if not r['passed']};assert len(failed)==17 and 'xdut.xd105'in failed",
       "failed={n:r for n,r in h.items()if not r['passed']};assert failed=={}"),
      ("original_failed_HBT_count=17,contract_hbt_roles=c['hbt']","original_failed_HBT_count=0,contract_hbt_roles=c['hbt']")]
    changed=text
    for before,after in edits:
        assert changed.count(before)==1;changed=changed.replace(before,after)
    reverse=changed
    for before,after in reversed(edits):
        assert reverse.count(after)==1;reverse=reverse.replace(after,before)
    assert reverse==text
    a={n.name:ast.dump(n,include_attributes=False)for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n,include_attributes=False)for n in ast.parse(changed).body if isinstance(n,ast.FunctionDef)}
    assert set(a)==set(b)and all(a[n]==b[n]for n in a if n!='analyze')
    node=next(n for n in ast.parse(changed).body if isinstance(n,ast.FunctionDef)and n.name=='analyze')
    ns=dict(vars(old),TARGETS=TARGETS)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<current-failed-set-only-analyze>','exec'),ns)
    return ns['analyze'],dict(original_sha256=ORIGINAL_SHA,generated_sha256=digest(changed),
      reversed_byte_exact=True,edits=[dict(before=a,after=b,count=1)for a,b in edits],
      unchanged_math_except_expected_failed_device_set=True)

def topology(c,payloads):
    assert set(payloads)=={'p','n'}
    groups={};passives={};ports={s['instance']:dict(zip(old.PORTS,s['actual_ports'],strict=True))for s in c['instances']}
    specs={s['instance']:s for s in c['instances']}
    def projection(instance,row,term):
        native=row['terminals'][term]['model_node'].lower()
        node=ports[instance].get(native.upper(),instance+'.'+native)
        assert node=='0'or 'v('+node+')'in c['vectors']
        return dict(node=node,**row['terminals'][term])
    requested=[(s['instance'],prefix)for s in c['instances']for prefix in TARGETS.values()]
    for inst,prefix in requested:
        roles=payloads[specs[inst]['variant']]['compact_roles']
        name=inst+'.xd'+str(roles[prefix+'__XT']['native_id'])
        names={n:c['hbt'][n]for n in c['hbt']if c['hbt'][n]['fixture_instance']==inst}
        group={}
        for leaf in ('XT','XREF','XSA','XSB','XAP','XAN','XBP','XBN'):
            src=prefix+'__'+leaf;r=roles[src]
            assert r['source_instance']==src and r['model']=='npn13G2'
            native=inst+'.xd'+str(r['native_id']);spec=names[native]
            assert spec['source_instance']==src and spec['native_id']==r['native_id']
            assert spec['terminals']==[projection(inst,r,t)['node']for t in ('C','B','E','S')]
            assert spec['nx']==r['parameters']['Nx']and r['parameters']['m']==1
            group[leaf]=dict(name=native,source_instance=src,terminals=r['terminals'])
        assert group['XT']['name']==name
        if inst=='xdut':assert TARGETS[name]==prefix
        def net(leaf,t):return group[leaf]['terminals'][t]['source_net']
        assert net('XT','C')==net('XSA','E')==net('XSB','E')==prefix+'__TAIL'
        assert net('XT','B')==net('XREF','C')==net('XREF','B')==prefix+'__REF'
        assert net('XT','E')==net('XREF','E')=='AVSS'
        assert net('XSA','B')=='PHASE__RUNP'and net('XSB','B')=='PHASE__RUNN'
        assert net('XSA','C')==net('XAP','E')==net('XAN','E')==prefix+'__EA'
        assert net('XSB','C')==net('XBP','E')==net('XBN','E')==prefix+'__EB'
        groups[name]=dict(source_prefix=prefix,devices=group,public_AVSS_node=ports[inst]['AVSS'])
    for spec in c['instances']:
        inst=spec['instance'];roles=payloads[spec['variant']]['compact_roles']
        prefixes=(*EXTRA_PREFIXES,*TARGETS.values())
        for src,r in roles.items():
            if r['model']!='rppd'or src.rsplit('__',1)[0]not in prefixes:continue
            assert r['source_instance']==src and set(r['terminals'])=={'rppd_1','rppd_2','rppd_sub'}
            passives[inst+':'+src]=dict(source_instance=src,native_id=r['native_id'],parameters=r['parameters'],
              terminals={t:projection(inst,r,t)for t in ('rppd_1','rppd_2','rppd_sub')})
    assert len(groups)==12 and set(TARGETS)<=set(groups)
    assert set(passives)=={s['instance']+':'+n for s in c['instances']for n in passive_source_names()}
    assert len(passives)==168
    return dict(target_groups=groups,passive_accesses=passives,
      voltage_drop_is_not_resistor_current=True,distributed_nodes_not_collapsed=True)

def frame_at(t,values,c,pairmap,row):
    row=int(row);assert 0<=row<len(t)
    return dict(row=row,time_s=float(t[row]),within_original_UI_window=bool(old.START<=t[row]<old.STOP),
      hbt={n:old.hbt_state(values,n,s,row)for n,s in c['hbt'].items()},
      pairs={n:old.pair_state(values,p,row)for n,p in pairmap.items()},
      resistor_thermal_states={n:old.voltage(values,n,row)for n in c['thermal_nodes']},
      native_fixture_currents_a={k:float(values[k][row])for k in c['vectors']if k.startswith('i(')})

def intervals(t,y,threshold=.4,start=old.START):
    assert t.ndim==y.ndim==1 and t.shape==y.shape and len(t)>=2
    assert np.isfinite(t).all()and np.isfinite(y).all()and np.all(np.diff(t)>0)
    active=np.flatnonzero(t>=start)
    if not len(active):return []
    mask=(t>=start)&(y<threshold);edges=np.diff(np.r_[False,mask,False].astype(int))
    result=[]
    def point(i):return dict(row=int(i),time_s=float(t[i]),value_v=float(y[i]))
    for a,b in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)-1,strict=True):
        result.append(dict(first=point(a),last=point(b),before=None if a==0 else point(a-1),
          after=None if b+1==len(t)else point(b+1),rows=int(b-a+1),threshold_v=threshold,active_start_s=start,
          left_censored=bool(a==active[0]),right_censored=bool(b==len(t)-1),
          boundary_rows_are_not_interpolated_crossings=True))
    return result

def headroom(frame,groups,public_avss):
    out={}
    for target,g in groups.items():
        q={leaf:frame['hbt'][spec['name']]for leaf,spec in g['devices'].items()}
        c,b,e,_,ce,be,ic,icnx=q['XT']
        assert abs((c-e)-ce)<1e-15 and abs((b-e)-be)<1e-15
        ground=public_avss[target]
        out[target]=dict(tail_vce_v=ce,tail_collector_to_public_AVSS_v=c-ground,
          tail_emitter_to_public_AVSS_v=e-ground,tail_base_to_public_AVSS_v=b-ground,
          VCE_decomposition_residual_v=ce-((c-ground)-(e-ground)),
          local_reference_vbe_v=q['XREF'][5],tail_minus_reference_emitter_v=e-q['XREF'][2],
          tail_minus_reference_base_v=b-q['XREF'][1],native_tail_ic_a=ic,native_tail_ic_per_Nx_a=icnx,
          selector_steering={leaf:dict(base_v=q[leaf][1],emitter_v=q[leaf][2],collector_v=q[leaf][0],
            vbe_v=q[leaf][5],vce_v=q[leaf][4],native_ic_a=q[leaf][6],
            emitter_minus_tail_collector_v=q[leaf][2]-c)for leaf in ('XSA','XSB')},
          selector_base_differential_v=q['XSA'][1]-q['XSB'][1],
          steering_VCE_decomposition={leaf:dict(base_to_tail_emitter_v=q[leaf][1]-e,
            minus_steering_vbe_v=-q[leaf][5],wire_emitter_to_tail_collector_v=q[leaf][2]-c,
            reconstructed_tail_vce_v=(q[leaf][1]-e)-q[leaf][5]-(q[leaf][2]-c))for leaf in ('XSA','XSB')},
          local_reference_VBE_decomposition=dict(base_contact_drop_v=b-q['XREF'][1],reference_vbe_v=q['XREF'][5],
            reference_to_tail_emitter_v=q['XREF'][2]-e,reconstructed_tail_vbe_v=(b-q['XREF'][1])+q['XREF'][5]+(q['XREF'][2]-e)),
          collector_Ic_is_not_emitter_current=True,full_KCL_claimed=False)
    return out

def observe(case,result,screen,bindings,emit):
    c=old.contract_check((case/'contract.json').read_bytes(),result)
    assert c['binding_summary_sha256']==current.admission.BINDING_SHA
    assert all(s['model_sha256']==current.admission.MODELS[s['variant']]for s in c['instances'])
    topo=topology(c,bindings);pairmap=old.pairs(c)
    emit('diagnostic-probe-inventory.json',dict(contract_sha256=digest((case/'contract.json').read_bytes()),
      native_pair_nodes=pairmap,all_native_HBT_roles=c['hbt'],thermal_nodes=c['thermal_nodes'],
      added_source_bound_topology=topo,all_requested_probes_checked_before_review=True,
      original_limits=c['limits'],original_timing=c['timing'],original_first_fall_limit_s=old.UI/2))
    replay=screen.review_capture(case,c,0)
    assert old.canonical(replay)==old.canonical(result['review']),'Complete current original rejection not reproduced'
    emit('original-review-replay.json',dict(status='EXACT_CURRENT_ORIGINAL_REJECTION_REPRODUCED_BEFORE_DIAGNOSIS',
      original_complete_review=replay,actual_canonical_sha256=digest(old.canonical(replay)),
      recorded_canonical_sha256=digest(old.canonical(result['review'])),full_original_review_replays=1,
      original_acceptance=False,new_simulation=False,original_first_fall_limit_s=old.UI/2))
    t,values,proof=read_streamed_wave(case/'wave.raw',c['vectors'],old.STOP,old.STEP)
    assert proof==replay['capture']and proof['raw_sha256']==result['outputs']['work/wave.raw']
    prior=result['original17_HBT_rejection']['all17_original_failed_HBT_records']
    assert len(prior)==17 and set(TARGETS)<=set(prior)
    try:
        resource_plan=resources.plan(t,values,c,replay,list(prior),{},intervals)
        resource_plan['memory_admission']=resources.admit_memory(resource_plan,resources.mem_available())
    except resources.ResourceLimit as error:
        emit('diagnostic-resource-refusal.json',error.record);raise
    emit('diagnostic-resource-plan.json',resource_plan)
    analyze,derivation=analysis_program();d=analyze(t,values,c,replay)
    frames=d['frames'];active=np.flatnonzero(t>=old.START);previous={}
    def ensure(row):
        key=str(int(row))
        if key not in frames:frames[key]=frame_at(t,values,c,pairmap,row)
        assert frames[key]['row']==int(row)and frames[key]['time_s']==float(t[row])
        return key
    violations={}
    for name in prior:
        spec=c['hbt'][name];y=values['v('+spec['terminals'][0]+')']-values['v('+spec['terminals'][2]+')']
        row=int(active[np.argmin(y[active])]);value=float(y[row])
        assert value==replay['measurement']['hbt_safety'][name]['min_post_vce_v']
        previous[name]=dict(frame=ensure(row),current_min_post_vce_v=value,original_prior_record=prior[name],
          old_extremum_is_not_same_time_comparison=True)
        if name in TARGETS:
            v=intervals(t,y)
            for r in v:
                for label in ('first','last','before','after'):
                    if r[label]is not None:r[label]['frame']=ensure(r[label]['row'])
            violations[name]=v
    assert set(violations)==set(TARGETS)and all(v==[]for v in violations.values())
    resources.validate_frames(resource_plan,frames,t)
    for key,frame in frames.items():
        row=frame['row'];assert frame['time_s']==float(t[row])
        ground={n:old.voltage(values,g['public_AVSS_node'],row)for n,g in topo['target_groups'].items()}
        frame['tail_headroom']=headroom(frame,topo['target_groups'],ground)
        frame['passive_accesses']={n:dict(terminal_voltages_v={term:old.voltage(values,s['node'],row)for term,s in r['terminals'].items()},
          current_inferred=False)for n,r in topo['passive_accesses'].items()}
    d.update(status='DIAGNOSIS_ONLY_CURRENT_TAIL_M4_PHASE_REJECTION_REMAINS',source_bound_tail_topology=topo,
      current_capture_source=result['source_head'],current_capture_run=result['run_id'],
      current_capture_sha256=proof['raw_sha256'],current_model_hashes=result['current_RC_model_hashes'],
      original17_current_minimum_frames=previous,four_tail_violation_intervals=violations,observer_derivation=derivation,resource_plan=resource_plan,
      original17_rejection_preserved=True,prior_four_tail_rejection=result['prior_four_tail_rejection'],
      current_all318_numeric_safety_passed=True,global_crossings_are_neighbor_brackets_not_all_complete_state_frames=True,
      original_fixed_references_not_rephased=True,full_original_review_replays=1,engineering_change_authorized=False)
    return d

def actual_topology_controls(c,payloads):
    positive=topology(c,payloads);rejected=[]
    def refusal(label,change):
        cc,pp=copy.deepcopy(c),copy.deepcopy(payloads);change(cc,pp);assert (cc,pp)!=(c,payloads)
        try:topology(cc,pp)
        except(AssertionError,KeyError,ValueError):rejected.append(label)
        else:raise AssertionError('Accepted source topology mutation '+label)
    prefix=TARGETS['xdut.xd75']
    def role(pp,leaf):return pp['p']['compact_roles'][prefix+'__'+leaf]
    refusal('tail_native_ID',lambda cc,pp:role(pp,'XT').update(native_id=9999))
    refusal('tail_source_name',lambda cc,pp:role(pp,'XT').update(source_instance='wrong'))
    refusal('tail_collector_net',lambda cc,pp:role(pp,'XT')['terminals']['C'].update(source_net='AVSS'))
    refusal('steering_emitter_net',lambda cc,pp:role(pp,'XSA')['terminals']['E'].update(source_net='other_tail'))
    refusal('steering_base_polarity',lambda cc,pp:role(pp,'XSB')['terminals']['B'].update(source_net='PHASE__RUNP'))
    refusal('reference_emitter_net',lambda cc,pp:role(pp,'XREF')['terminals']['E'].update(source_net='SUB'))
    refusal('reference_collector_net',lambda cc,pp:role(pp,'XREF')['terminals']['C'].update(source_net='wrong_ref'))
    refusal('tail_model_alias',lambda cc,pp:role(pp,'XT')['terminals']['C'].update(model_node=role(pp,'XT')['terminals']['E']['model_node']))
    refusal('tail_finite_BODY_short',lambda cc,pp:role(pp,'XT')['terminals']['S'].update(model_node='AVSS'))
    refusal('tail_Nx',lambda cc,pp:cc['hbt']['xdut.xd75'].update(nx=2))
    refusal('missing_child_tail',lambda cc,pp:cc['hbt'].pop(positive['target_groups']['xloadq.xd75']['devices']['XT']['name']))
    refusal('missing_passive_skew',lambda cc,pp:pp['p']['compact_roles'].pop('PHASE__XRUN__XAND_SKEW'))
    node=positive['passive_accesses']['xdut:PHASE__XRUN__XAND_SKEW']['terminals']['rppd_1']['node']
    refusal('missing_passive_voltage',lambda cc,pp:cc['vectors'].remove('v('+node+')'))
    refusal('changed_passive_terminal',lambda cc,pp:pp['p']['compact_roles']['PHASE__XRUN__XAND_SKEW']['terminals']['rppd_1'].update(model_node='unrecorded_node'))
    assert len(rejected)==14
    return dict(target_groups=12,passive_accesses=168,rejected=rejected,
      real_restored_input_scope=True,source_node_aliasing_accepted=False)
