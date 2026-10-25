#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Same-row diagnosis of rejected318-HBT capture; no simulator or gate changes."""
import hashlib,json,os
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/tx-phase-reset334-saved-diagnosis-methods.json'
RESULT='docs/evidence/tx-phase-reset334-first-loaded-rejected-result-20261025.json'
PORTS=['CLKP','CLKN','MP','MN','QP','QN','ARM_P','ARM_N','DIV_AVDD','AVSS','SUB','wire_cref']
UI,START,STOP,STEP=125e-12,2e-9,34e-9,.3125e-12
HBT_FIELDS=['collector_v','base_v','emitter_v','substrate_v','vce_v','vbe_v','native_ic_a','ic_per_emitter_a']
PAIR_FIELDS=['positive_v','negative_v','differential_v','common_mode_v']
def digest(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def pin(path,want):
    b=Path(path).read_bytes();assert digest(b)==want,str(path);return b

def bracket(t,at):
    assert t.ndim==1 and len(t)>=2 and np.isfinite(t).all()and np.all(np.diff(t)>0)
    assert np.isfinite(at)and t[0]<=at<=t[-1]
    i=int(np.searchsorted(t,at,side='left'))
    a,b=(i,i)if i<len(t)and t[i]==at else(i-1,i)
    assert 0<=a<=b<len(t)
    return dict(requested_s=float(at),rows=[a,b],times_s=[float(t[a]),float(t[b])],exact_native_row=a==b)
def crossing_rows(t,y,level):
    assert t.ndim==y.ndim==1 and t.shape==y.shape and len(t)>=2
    assert np.isfinite(t).all()and np.isfinite(y).all()and np.all(np.diff(t)>0)and np.isfinite(level)
    rising=(y[:-1]<=level)&(y[1:]>level);falling=(y[:-1]>=level)&(y[1:]<level)
    return [dict(rows=[int(i),int(i+1)],times_s=[float(t[i]),float(t[i+1])],
                 values_v=[float(y[i]),float(y[i+1])],direction='rising'if rising[i]else'falling')
            for i in np.flatnonzero(rising|falling)]
def voltage(values,node,row):
    if node=='0':return 0.
    value=float(values['v('+node+')'][row]);assert np.isfinite(value);return value

def hbt_state(values,name,spec,row):
    assert spec['nx']in(1,2,4)and len(spec['terminals'])==4
    c,b,e,s=[voltage(values,n,row)for n in spec['terminals']]
    ic=float(values['@q.'+name+'.qnpn13g2[ic]'][row]);assert np.isfinite(ic)
    return [c,b,e,s,c-e,b-e,ic,ic/spec['nx']]
def pair_state(values,pair,row):
    assert len(pair)==2 and pair[0]!=pair[1]
    p,n=[voltage(values,x,row)for x in pair];return[p,n,p-n,(p+n)/2]
def window_events(events,lo,hi,origin):
    assert np.isfinite([lo,hi,origin]).all()and lo<hi
    # Include any crossing bracket that overlaps the fixed window; do not fit a crossing time.
    return [dict(e,relative_to_prescribed_event_s=[e['times_s'][0]-origin,e['times_s'][1]-origin])
            for e in events if e['times_s'][0]<=hi and e['times_s'][1]>=lo]

def validate_crossing_frames(events,frames):
    for event in events:
        assert len(event['rows'])==len(event['times_s'])==len(event['frames'])==2
        assert event['rows'][1]==event['rows'][0]+1
        for row,at,key in zip(event['rows'],event['times_s'],event['frames'],strict=True):
            assert key==str(row)and frames[key]['row']==row and frames[key]['time_s']==at
    return True

def bind_crossing_frames(events,frame,frames):
    result=[dict(event,frames=[frame(row)for row in event['rows']])for event in events]
    validate_crossing_frames(result,frames)
    return result

def contract_check(raw,result):
    assert digest(raw)==result['outputs']['work/contract.json']
    c=json.loads(raw)
    assert c['schema']=='physical334-three-model-loaded-fixture-v1'
    assert c['variant']=='p'and c['initial_clock_high']is True
    assert c['timing']['UI_s']==UI and c['timing']['START_s']==START and c['timing']['STOP_s']==STOP
    assert c['timing']['maxstep_s']==STEP and c['limits']==dict(min_post_vce_v=.4,max_whole_abs_vce_v=1.6,
        max_whole_abs_vbe_v=1.,max_whole_abs_ic_per_emitter_a=.003,min_sign_margin_v=.1)
    assert c['hbt_count']==len(c['hbt'])==318 and c['resistor_thermal_count']==len(c['thermal_nodes'])==390
    assert len(c['vectors'])==len(set(c['vectors']))==4726 and len(set(c['thermal_nodes']))==390
    assert {s['instance']for s in c['instances']}=={'xdut','xloadm','xloadq'}and len(c['instances'])==3
    assert [(s['instance'],s['variant'],s['physical_role'])for s in c['instances']]==[
        ('xdut','p','phase_l1_k0'),('xloadm','n','phase_l2_k0'),('xloadq','p','phase_l2_k1')]
    for s in c['instances']:
        assert len(s['actual_ports'])==len(PORTS)and len(s['oracle']['first_falls'])==2
        assert s['oracle']['observed_phase_fit']is False and s['finite_body_contacts']==90 and s['body_node']!='0'
        assert set(s['probe_pairs'])=={'run','release','native_clock','arm_conditioned'}
        names={n:r for n,r in c['hbt'].items()if r['fixture_instance']==s['instance']}
        assert len(names)==106
        for n,r in names.items():
            assert n==s['instance']+'.xd'+str(r['native_id'])and r['physical_preset']==s['variant']
            assert r['source_instance'].startswith('PHASE__')and r['nx']in(1,2,4)
            assert len(r['terminals'])==4 and all(x=='0'or'v('+x+')'in c['vectors']for x in r['terminals'])
            assert '@q.'+n+'.qnpn13g2[ic]'in c['vectors']
    assert all('v('+n+')'in c['vectors']for n in c['thermal_nodes'])
    return c

def pairs(c):
    out={}
    for s in c['instances']:
        ports=dict(zip(PORTS,s['actual_ports'],strict=True))
        q=dict(fixture_input=[ports['CLKP'],ports['CLKN']],master=[ports['MP'],ports['MN']],
            slave=[ports['QP'],ports['QN']],arm_external=[ports['ARM_P'],ports['ARM_N']],**s['probe_pairs'])
        for key,pair in q.items():
            assert len(pair)==2 and pair[0]!=pair[1]
            assert all('v('+n+')'in c['vectors']for n in pair)
            out[s['instance']+':'+key]=pair
    assert len(out)==24
    return out

def analyze(t,values,c,original):
    assert len(t)==114525 and t[0]==0 and t[-1]==STOP and np.all(np.diff(t)>0)
    assert np.diff(t).max()<=STEP*1.00001 and set(values)==set(c['vectors'])
    assert all(len(v)==len(t)and np.isfinite(v).all()for v in values.values())
    h=original['measurement']['hbt_safety'];assert set(h)==set(c['hbt'])and len(h)==318
    failed={n:r for n,r in h.items()if not r['passed']};assert len(failed)==17 and 'xdut.xd105'in failed
    assert original['passed']is False and not original['errors']and not original['diagnostics']
    pairmap=pairs(c);frames={};pairvalues={}
    active=np.flatnonzero(t>=START);assert len(active)
    def frame(row):
        row=int(row);key=str(row)
        if key not in frames:
            assert 0<=row<len(t)
            frames[key]=dict(row=row,time_s=float(t[row]),
                within_original_UI_window=bool(START<=t[row]<STOP),
                hbt={n:hbt_state(values,n,s,row)for n,s in c['hbt'].items()},
                pairs={n:pair_state(values,p,row)for n,p in pairmap.items()},
                resistor_thermal_states={n:voltage(values,n,row)for n in c['thermal_nodes']},
                native_fixture_currents_a={k:float(values[k][row])for k in c['vectors']if k.startswith('i(')})
        return key
    ranges={};allcross={}
    for name,(p,n)in pairmap.items():
        y=values['v('+p+')']-values['v('+n+')'];pairvalues[name]=y
        rows=dict(whole_min=int(np.argmin(y)),whole_max=int(np.argmax(y)),
                  post_start_min=int(active[np.argmin(y[active])]),post_start_max=int(active[np.argmax(y[active])]))
        ranges[name]={key:dict(differential_v=float(y[row]),frame=frame(row))for key,row in rows.items()}
        instance,key=name.split(':',1)
        if key!='arm_external':
            old=original['measurement']['three_model_screens'][instance]['pair_ranges'][key]
            assert float(y.min())==old['minimum_v']and float(y.max())==old['maximum_v']
        allcross[name]={str(level):crossing_rows(t,y,level)for level in(-.1,0.,.1)}
    extrema={}
    for name in failed:
        s=c['hbt'][name]
        cv,bv,ev,_=[np.zeros_like(t)if n=='0'else values['v('+n+')']for n in s['terminals']]
        ce,be,ic=cv-ev,bv-ev,values['@q.'+name+'.qnpn13g2[ic]']/s['nx']
        targets=dict(min_post_vce_v=(int(active[np.argmin(ce[active])]),ce),
            max_whole_abs_vce_v=(int(np.argmax(abs(ce))),abs(ce)),
            max_whole_abs_vbe_v=(int(np.argmax(abs(be))),abs(be)),
            max_whole_abs_ic_per_emitter_a=(int(np.argmax(abs(ic))),abs(ic)))
        extrema[name]={}
        for metric,(row,y)in targets.items():
            assert float(y[row])==h[name][metric]
            extrema[name][metric]=dict(value=float(y[row]),frame=frame(row))
    requested=[];windows={}
    def sample(label,at):
        b=bracket(t,float(at));requested.append(dict(label=label,**b,frames=[frame(r)for r in dict.fromkeys(b['rows'])]))
    for i in range(256):sample('original_UI_center_'+str(i),START+(i+.5)*UI)
    for s in c['instances']:
        name=s['instance']
        for index,event in enumerate(s['oracle']['first_falls']):
            arm,fall=event['arm_s'],event['fall_s']
            for suffix,at in [('arm',arm),('arm_ramp_end',arm+c['timing']['clock_ramp_s']),
                ('fall',fall),('original_limit',fall+UI/2),('one_UI',fall+UI),('two_UI',fall+2*UI)]:
                sample(name+':first_fall_'+str(index)+':'+suffix,at)
            lo,hi=fall-UI,fall+2*UI
            windows[name+':first_fall_'+str(index)]=dict(prescribed_event=event,bounds_s=[lo,hi],
                pair_crossings={n:{level:bind_crossing_frames(window_events(events,lo,hi,fall),frame,frames)for level,events in levels.items()}
                    for n,levels in allcross.items()},original_limit_s=UI/2)
    for name,key in [('reset_assert','reset_assert_s'),('reset_release','reset_release_s')]:
        at=c['timing'][key]
        for suffix,dt in [('edge',0.),('ramp_end',c['timing']['clock_ramp_s']),('one_UI',UI)]:sample(name+':'+suffix,at+dt)
    role_groups={}
    for name,s in c['hbt'].items():
        role_groups.setdefault(s['fixture_instance']+':'+s['source_instance'].rsplit('__',1)[0],[]).append(name)
    return dict(status='DIAGNOSIS_ONLY_COMPLETE318_LOADED_REJECTION_REMAINS',accepted=False,
        original_rejection_reproduced=True,original_first_fall_limit_s=UI/2,observed_phase_fitted=False,
        diagnostic_crossings_interpolated=False,original_review_interpolation_unchanged=True,
        first_fall_crossing_frames_are_additional_native_observations=True,
        original_failed_HBT_count=17,contract_hbt_roles=c['hbt'],source_hierarchy_groups=role_groups,
        hbt_state_fields=HBT_FIELDS,pair_state_fields=PAIR_FIELDS,native_pair_nodes=pairmap,
        frames=frames,pair_extrema_both_signs=ranges,failed_hbt_same_row_extrema=extrema,
        requested_fixed_samples=requested,first_fall_windows=windows,native_pair_crossings=allcross,
        resistor_thermal_state_scope='All390 originally saved rppd .dt vector voltages; no inferred HBT thermal state or absolute temperature.',
        current_scope='Original native HBT Ic accessors, signed and per Nx; no full terminal KCL or conduction-only interpretation.',
        original_measurement=original['measurement'],causal_conclusion=False,circuit_edit_justified=False,
        new_simulation=False,process_resumed=False,all31_clock_tree_accepted=False,PLL_connected=False,full_PHY_accepted=False)

def observe_restored(case,method,emit):
    assert os.environ.get('GITHUB_ACTIONS')=='true'and method['readback_authorized']is True
    assert method['native_simulation_authorized']is False
    for path,h in method['protected_files'].items():pin(ROOT/path,h)
    closure=json.loads(pin(ROOT/method['original_method_path'],method['original_method_sha256']))
    for path,h in closure['protected'].items():pin(ROOT/path,h)
    source=json.loads(pin(ROOT/RESULT,method['source_summary_sha256']))
    assert source['run_id']==40178775666 and source['source_head']==method['original_source']
    assert source['status']=='REJECTED_PHYSICAL334_THREE_MODEL_ORIGINAL_LOADED_GATES'
    assert source['full_capture']and not source['native_process_saved']and source['sources_unchanged']
    assert source['native_exit_code']==0 and not source['electrical_screen_passed']
    for name in('bench.cir','contract.json','native.log','op.raw'):pin(case/name,source['outputs']['work/'+name])
    c=contract_check((case/'contract.json').read_bytes(),source)
    # Validate all requested pair endpoints before full review, alongside contract_check's HBT/thermal inventory.
    native_pairs=pairs(c)
    emit('diagnostic-probe-inventory.json',dict(contract_sha256=digest((case/'contract.json').read_bytes()),
        native_pair_nodes=native_pairs,all_native_HBT_roles=c['hbt'],thermal_nodes=c['thermal_nodes'],
        vector_count=len(c['vectors']),original_limits=c['limits'],original_timing=c['timing'],
        original_first_fall_limit_s=UI/2,all_requested_probes_checked_before_review=True))
    # Exact frozen reader function; no runtime restoration or simulator entrypoint.
    from tx_phase_reset334_transient_support import review_capture
    replay=review_capture(case,c,0)
    assert canonical(replay)==canonical(source['review']),'Original complete rejection not reproduced'
    emit('original-review-replay.json',dict(status='EXACT_ORIGINAL_PHASE318_REJECTION_REPRODUCED_BEFORE_DIAGNOSIS',
        actual_canonical_sha256=digest(canonical(replay).encode()),
        recorded_canonical_sha256=digest(canonical(source['review']).encode()),
        capture=replay['capture'],failed_hbt_count=sum(not h['passed']for h in replay['measurement']['hbt_safety'].values()),
        original_first_fall_limit_s=UI/2,original_acceptance=False,new_simulation=False,full_original_review_replays=1))
    from cloud_tx_stream import read_streamed_wave
    t,values,transport=read_streamed_wave(case/'wave.raw',c['vectors'],STOP,STEP)
    assert transport==replay['capture']and transport['raw_sha256']==method['raw_sha256']==source['outputs']['work/wave.raw']
    return analyze(t,values,c,replay)
