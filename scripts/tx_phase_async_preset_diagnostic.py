#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Intrinsic finite-wave reset experiment; no RC, PLL or full-PHY acceptance."""
import hashlib,json,math,re
from collections import Counter
from pathlib import Path
import numpy as np
import build_tx_phase_async_preset_source as builder
import check_tx_phase_async_preset_source as source_check
import tx_phase31_source_mapping as mapping
from run_cloud_tx_mux4 import solver_options
ROOT=Path(__file__).resolve().parents[1]
SOURCE_SHA='2ce563119aedf629608b2c66a1f605f719f7a58765af77a965ae0a7e4598e4e6'
OBSERVER_RUN=40084454916
OBSERVER_ASSET=672131330
OBSERVER_SHA='9656bff3e87627c0529bdff52921f2d8278d48fe05cc76516b507200f9c67863'
OBSERVER_HEAD='f520b2511b9dd00c98c1bff5491e87d232f11d21'
UI=125e-12;START=2e-9;STOP=34e-9;STEP=.3125e-12;RISE=10e-12
ARM_RELEASE=1.75e-9;RESET_ASSERT=12.03125e-9;RESET_RELEASE=14.03125e-9
PROFILE='breakpoint_tight_trap'
LIMITS=dict(min_post_vce_v=.4,max_whole_abs_vce_v=1.6,max_whole_abs_vbe_v=1.,max_whole_abs_ic_per_emitter_a=.003,min_sign_margin_v=.1)
def digest(data):return hashlib.sha256(data.encode()if isinstance(data,str)else data).hexdigest()
def boundary(raw):
    assert digest(raw)==OBSERVER_SHA
    d=json.loads(raw)
    assert d['status']=='PASS_EXACT_FEEDBACK_DIAGNOSIS_ORIGINAL_ACQUISITION_REMAINS_REJECTED'
    assert d['source_head']==OBSERVER_HEAD and int(d['run_id'])==OBSERVER_RUN
    assert not d['acquisition_accepted']and not d['full_phy_accepted']and not d['native_activation_performed']
    r=d['stage_statistics']['div1_first_div2']
    assert [r['p_vector'],r['n_vector']]==['v(xloop.w_t398_c)','v(xloop.w_t389_c)']
    assert r['common_mode']['count']==r['voltage']['count']==3201410
    cm=r['common_mode']['median'];amp=min(-r['voltage']['minimum'],r['voltage']['maximum'])/2
    assert cm==2.2605958859271773 and amp==0.08531554498100902
    assert 0<cm-amp<cm+amp<2.5
    return dict(source_run=OBSERVER_RUN,source_head=OBSERVER_HEAD,summary_asset=OBSERVER_ASSET,summary_sha256=OBSERVER_SHA,
      pair='div1_first_div2',vectors=[r['p_vector'],r['n_vector']],common_mode_v=cm,single_ended_amplitude_v=amp,
      common_mode_field='stage_statistics.div1_first_div2.common_mode.median',
      amplitude_derivation='min(-stage_statistics.div1_first_div2.voltage.minimum, stage_statistics.div1_first_div2.voltage.maximum)/2',
      actual_median_period_s=r['zero_rising_period_s']['median'],nominal_test_frequency_hz=4e9,
      actual_PLL_waveform_replayed=False,stable_input_envelope_qualified=False,PLL_locked=False,
      arm_interface='Same documented high-CML fixture scalar levels; external test equipment, not a real reset driver')
def inventory(text,sign):
    assert sign in ('p','n')and digest(text)==SOURCE_SHA
    source_check.validate(text)
    definitions=builder.definitions(text);top=builder.NAMES['parent'+sign];records=[]
    actual='clkp clkn mp mn qp qn armp armn avdd 0 0'.split()
    def walk(name,nodes,path,stack=()):
        assert name not in stack
        definition=definitions[name]
        assert len(nodes)==len(definition['ports'])
        ports=dict(zip((p.lower()for p in definition['ports']),nodes,strict=True))
        def node(n):return ports.get(n.lower(),path+'.'+n.lower())
        for r in definition['cards']:
            models=[(m,n)for m,n in source_check.PRIMITIVES.items()if len(r)>n+1 and r[n+1]==m]
            if models:
                assert len(models)==1
                model,n=models[0]
                records.append(dict(instance=path+'.'+r[0].lower(),model=model,nodes=[node(v)for v in r[1:n+1]],parameters=r[n+2:]))
            else:walk(r[-1],[node(v)for v in r[1:-1]],path+'.'+r[0].lower(),(*stack,name))
    walk(top,actual,'xdut')
    assert Counter(r['model']for r in records)==dict(npn13G2=106,rppd=127,cap_cmim=8)
    assert len({r['instance']for r in records})==len(records)==241 and sum(len(r['nodes'])for r in records)==821
    hbts={r['instance']:dict(terminals=r['nodes'],nx=int(r['parameters'][0].split('=')[1]))for r in records if r['model']=='npn13G2'}
    vectors={'v('+n+')'for r in records for n in r['nodes']if n!='0'}
    vectors|={'@q.'+name+'.qnpn13g2[ic]'for name in hbts}
    vectors|={'v('+r['instance']+'.dt)'for r in records if r['model']=='rppd'}
    vectors|={'i(vrail)','i(vclkp)','i(vclkn)','i(varmp)','i(varmn)'}
    return dict(top=top,ports=actual,devices=records,hbt=hbts,vectors=sorted(vectors),primitive_census=dict(npn13G2=106,rppd=127,cap_cmim=8))
def source_points(bound,initial_high,arm=False,invert=False):
    cm=bound['common_mode_v'];amplitude=bound['single_ended_amplitude_v']
    def level(v):return cm+(1 if v else-1)*amplitude*(-1 if invert else 1)
    if arm:
        values=[(ARM_RELEASE,1),(RESET_ASSERT,0),(RESET_RELEASE,1)];initial=0
    else:
        initial=int(initial_high)
        values=[(START+i*UI,initial^(i%2))for i in range(1,256)]
    points=[(0.,0.),(1e-9,level(initial))]
    old=initial
    for t,v in values:
        assert t>points[-1][0]
        points.extend(((t,level(old)),(t+RISE,level(v))));old=v
    points.append((STOP,level(old)))
    assert all(b[0]>a[0]for a,b in zip(points,points[1:]))
    return points
def expected(sign,initial_high):
    """Fixed source events only: no observed edge, delay, polarity or phase fit."""
    assert sign in ('p','n')and type(initial_high)is bool
    mp=int(sign=='p');qp=1;armed=False;released=False;clk=int(initial_high)
    history=[dict(t_s=0.,MP=mp,QP=qp,release=0)]
    events=[(ARM_RELEASE,'arm',1),(RESET_ASSERT,'arm',0),(RESET_RELEASE,'arm',1)]
    events +=[(START+i*UI,'clock',int(initial_high)^(i%2))for i in range(1,256)]
    first_falls=[];arm_start=None
    for t,kind,value in sorted(events):
        if kind=='arm':
            armed=bool(value)
            if not armed:released=False;mp=int(sign=='p');qp=1
            else:arm_start=t
        else:
            old=clk;clk=value
            if armed and old==1 and clk==0 and not released:
                released=True;first_falls.append(dict(arm_s=arm_start,fall_s=t))
            if released:
                if clk==0:mp=1-qp
                else:qp=mp
        history.append(dict(t_s=t,MP=mp,QP=qp,release=int(released)))
    assert len(first_falls)==2
    return dict(events=history,first_falls=first_falls,initial_master=int(sign=='p'),initial_slave=1,
      output_polarities_fixed=True,observed_phase_fit=False)
def at_events(t,events,key):
    times=np.asarray([e['t_s']for e in events]);values=np.asarray([e[key]for e in events])
    return values[np.searchsorted(times,t,side='right')-1]
def prepare(text,bound,sign,initial_high,model_path,model_dir,osdi):
    assert type(initial_high)is bool
    for p in (model_path,model_dir,osdi):assert not any(x in str(p)for x in ('"','\n','\r','\x00'))
    assert not any(ch.isspace()for ch in str(osdi)), 'Native pre_osdi path must be an unquoted single token'
    inv=inventory(text,sign);oracle=expected(sign,initial_high)
    lines=['NSSOC intrinsic241 real-reset/first-fall diagnostic; not physical or PLL acceptance',
      *[f'.lib "{Path(model_dir)/("corner"+kind+".lib")}" {corner}'for kind,corner in [('HBT','hbt_typ'),('RES','res_typ'),('CAP','cap_typ')]],
      f'.include "{model_path}"','.temp 27',solver_options(PROFILE),'Vrail avdd 0 PWL(0 0 1n 2.5)']
    for name,arm,invert in [('clkp',False,False),('clkn',False,True),('armp',True,False),('armn',True,True)]:
        pts=source_points(bound,initial_high,arm,invert)
        lines.append('V'+name+' '+name+' 0 PWL('+' '.join(f'{t:.16g} {v:.16g}'for t,v in pts)+')')
    lines +=['Xdut '+' '.join(inv['ports'])+' '+inv['top'],f'.tran {STEP:.16g} {STOP:.16g} 0 {STEP:.16g}',
      '.control',f'pre_osdi {osdi}','set filetype=binary','set numdgt=16','save '+' '.join(inv['vectors']),
      'op','write op.raw all','run wave.raw','echo NSSOC_SOLVER_OPTIONS_BEGIN','option',
      'echo NSSOC_NATIVE_MINBREAK $minbreak','echo NSSOC_SOLVER_OPTIONS_END','quit','.endc','.end']
    deck='\n'.join(lines)+'\n'
    assert len([l for l in lines if l.startswith('V')])==5
    assert not re.search(r'(?im)^\s*(?:\.ic\b|\.nodeset\b|alter\b)|\buic\b',deck)
    assert not any(l.startswith(('B','E','G','I','R','C'))for l in lines[1:])
    return deck,dict(schema='intrinsic241-preset-diagnostic-v1',variant=sign,initial_clock_high=initial_high,
      boundary=bound,source_sha256=SOURCE_SHA,deck_sha256=digest(deck),**inv,oracle=oracle,
      timing=dict(UI_s=UI,START_s=START,STOP_s=STOP,maxstep_s=STEP,clock_ramp_s=RISE,arm_release_s=ARM_RELEASE,
       reset_assert_s=RESET_ASSERT,reset_release_s=RESET_RELEASE),limits=LIMITS,
      no_ideal_internal_sources=True,initial_state_forced=False,layout_RC_included=False,PLL_connected=False,full_PHY_accepted=False)
def crossings(t,v,rising=True):
    idx=np.flatnonzero((v[:-1]<=0)&(v[1:]>0)if rising else(v[:-1]>=0)&(v[1:]<0))
    return t[idx]+(t[idx+1]-t[idx])*(-v[idx])/(v[idx+1]-v[idx])
def signal_review(t,signals,contract):
    assert set(signals)=={'MP','QP','release','clock'}
    assert all(len(v)==len(t)and np.isfinite(v).all()for v in signals.values())
    samples=START+(np.arange(256)+.5)*UI
    result={}
    for name in ('MP','QP','release'):
        exp=2*at_events(samples,contract['oracle']['events'],name)-1
        measured=np.interp(samples,t,signals[name]);margin=measured*exp
        result[name]=dict(fixed_original_UI_centers=256,minimum_signed_margin_v=float(margin.min()),
          wrong_sign_samples=int((margin<=0).sum()),margin_violations=int((margin<LIMITS['min_sign_margin_v']).sum()),
          rising_s=crossings(t,signals[name]).tolist(),falling_s=crossings(t,signals[name],False).tolist())
    reset_mask=(t>=RESET_ASSERT+UI)&(t<RESET_RELEASE)
    assert reset_mask.any()
    preset={}
    for name,sign in [('MP',1 if contract['variant']=='p'else-1),('QP',1),('release',-1)]:
        m=sign*signals[name][reset_mask]
        preset[name]=dict(minimum_signed_margin_v=float(m.min()),wrong_sign_samples=int((m<=0).sum()))
    # First-fall timing is compared to predefined fixture events. These are
    # diagnostic limits only; never slide the measurement windows onto a DUT edge.
    rel_edges=crossings(t,signals['release']);releases=[]
    for record in contract['oracle']['first_falls']:
        arm=record['arm_s'];fall=record['fall_s']
        upper=RESET_ASSERT if arm==ARM_RELEASE else STOP
        observed=rel_edges[(rel_edges>=arm)&(rel_edges<upper)]
        releases.append(dict(**record,observed_release_edges_s=observed.tolist(),
          exactly_one=bool(len(observed)==1),
          before_first_fall=bool((observed<fall).any()),
          signed_delay_s=float(observed[0]-fall)if len(observed)==1 else None,
          within_original_UI_center=bool(len(observed)==1 and 0<=observed[0]-fall<=UI/2)))
    fixed=all(r['wrong_sign_samples']==0 and r['margin_violations']==0 for r in result.values())
    held=all(r['minimum_signed_margin_v']>=LIMITS['min_sign_margin_v']for r in preset.values())
    first=all(r['exactly_one']and not r['before_first_fall']and r['within_original_UI_center']for r in releases)
    return dict(fixed_phase_samples=result,asynchronous_preset_during_running=preset,first_fall_releases=releases,
      fixed_phase_and_margin_passed=fixed,preset_passed=held,first_fall_passed=first,
      diagnostic_signal_screen_passed=fixed and held and first,observed_phase_fitted=False,
      production_startup_or_recovery_removal_qualified=False)
def hbt_screen(t,c,b,e,ic,nx):
    assert nx in (1,2,4)and len(t)==len(c)==len(b)==len(e)==len(ic)
    assert np.isfinite(np.column_stack([t,c,b,e,ic])).all()
    ce=c-e;be=b-e;active=t>=START
    assert active.any()
    row=dict(min_post_vce_v=float(ce[active].min()),max_whole_abs_vce_v=float(abs(ce).max()),
      max_whole_abs_vbe_v=float(abs(be).max()),max_whole_abs_ic_per_emitter_a=float(abs(ic/nx).max()))
    row['passed']=row['min_post_vce_v']>=.4 and row['max_whole_abs_vce_v']<=1.6 and row['max_whole_abs_vbe_v']<=1 and row['max_whole_abs_ic_per_emitter_a']<=.003
    return row
def review(t,values,contract):
    assert len(t)>100 and t[0]==0 and abs(t[-1]-STOP)<1e-18 and np.all(np.diff(t)>0)
    assert np.diff(t).max()<=STEP*1.00001
    assert set(values)==set(contract['vectors'])and all(len(v)==len(t)and np.isfinite(v).all()for v in values.values())
    def v(n):return np.zeros_like(t)if n=='0'else values['v('+n+')']
    active=t>=START;devices={}
    for name,h in contract['hbt'].items():
        c,b,e,s=[v(n)for n in h['terminals']]
        devices[name]=hbt_screen(t,c,b,e,values['@q.'+name+'.qnpn13g2[ic]'],h['nx'])
    assert len(devices)==106
    sig=signal_review(t,dict(MP=v('mp')-v('mn'),QP=v('qp')-v('qn'),
      release=v('xdut.releasedp')-v('xdut.releasedn'),clock=v('clkp')-v('clkn')),contract)
    pairs={name:dict(minimum_v=float((v(p)-v(n)).min()),maximum_v=float((v(p)-v(n)).max()),
       minimum_common_mode_v=float(((v(p)+v(n))/2).min()),maximum_common_mode_v=float(((v(p)+v(n))/2).max()))
      for name,p,n in [('fixture_clock','clkp','clkn'),('native_clock','xdut.ckp','xdut.ckn'),
       ('arm_conditioned','xdut.xrelease.armcp','xdut.xrelease.armcn'),('release','xdut.releasedp','xdut.releasedn'),
       ('run','xdut.runp','xdut.runn'),('master','mp','mn'),('slave','qp','qn')]}
    safe=all(r['passed']for r in devices.values())
    return dict(all106_HBT_safety_passed=safe,hbt_safety=devices,signals=sig,pair_ranges=pairs,
      diagnostic_screen_passed=safe and sig['diagnostic_signal_screen_passed'],all31_clock_tree_accepted=False,
      loaded_selector_interface_accepted=False,new_layout_qualified=False,PLL_connected=False,full_PHY_accepted=False)
