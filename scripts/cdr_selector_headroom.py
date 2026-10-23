#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Observe actual selector terminal bias/current without changing any electrical gate."""
import copy
import numpy as np
def summary(a):
    a=np.asarray(a,dtype=float)
    assert a.ndim==1 and len(a)>0 and np.isfinite(a).all()
    return dict(samples=len(a),minimum=float(a.min()),maximum=float(a.max()),
      mean=float(a.mean()),median=float(np.median(a)))
def duration_bounds(t,active,condition):
    dt=np.diff(t);eligible=active[:-1]&active[1:]
    left=condition[:-1];right=condition[1:]
    return dict(lower_s=float(dt[eligible&left&right].sum()),
      upper_s=float(dt[eligible&(left|right)].sum()),
      observed_interval_s=float(dt[eligible].sum()))
def observe(t,graph,members,v,w,edges,windows,ui,active):
    t=np.asarray(t);active=np.asarray(active)
    assert t.ndim==1 and len(t)>2 and np.isfinite(t).all()and np.all(np.diff(t)>0)
    assert active.dtype==bool and active.shape==t.shape and active.any()
    assert ui>0 and set(graph)=={'master','slave'}
    edges=np.asarray(edges);assert edges.ndim==1 and len(edges)>0 and np.isfinite(edges).all()
    rows=windows['rows'];assert len(rows)==len(edges)
    assert [r['bit_index']for r in rows]==list(range(1,len(edges)+1))
    assert all(r['original_edge_s']==e for r,e in zip(rows,edges,strict=True))
    assert all(r['matching_transitions']==1 for r in rows),'Ambiguous steering window'
    bad=np.array([r['signed_at_original_deadline_v']['slave_output']<.1 for r in rows])
    roles={}
    for latch,bank in graph.items():
        for side in ('track','hold'):
            names=bank[side+'_selectors']
            assert len(names)==len(set(names))==2
            for name in names:
                assert name in members and name not in roles
                roles[name]=(latch,side)
    assert len(roles)==8
    result={}
    for name,(latch,side)in roles.items():
        device=members[name];nx=device['nx'];assert np.isfinite(nx)and nx>0
        vc,vb,ve=[np.asarray(v(n))for n in device['nodes'][:3]]
        ic=np.asarray(w['@q.'+name+'.qnpn13g2[ic]'])
        assert all(a.shape==t.shape and np.isfinite(a).all()for a in (vc,vb,ve,ic))
        signals=dict(vbc_v=vb-vc,vce_v=vc-ve,vbe_v=vb-ve,ic_a=ic,ic_per_emitter_a=ic/nx)
        time_bias={str(level):duration_bounds(t,active,(vb-vc)>level)for level in (0.,.1,.2,.3)}
        phases=[]
        for phase in (-.25,-.1,0.,.1,.2,.3,.6):
            times=edges+phase*ui;assert times[0]>=t[0]and times[-1]<=t[-1]
            values={key:np.interp(times,t,val)for key,val in signals.items()}
            groups={}
            for label,selected in [('all',np.ones(len(edges),dtype=bool)),('original_slave_late',bad),('original_slave_not_late',~bad)]:
                groups[label]=dict(bits=int(selected.sum()),measurements={key:summary(val[selected])for key,val in values.items()}if selected.any()else {})
            phases.append(dict(original_phase_ui=phase,groups=groups))
        transitions=np.array([r['steering_transition_s']for r in rows])
        assert np.isfinite(transitions).all()and (transitions>=t[0]).all()and (transitions<=t[-1]).all()
        result[name]=dict(latch=latch,side=side,nx=nx,native_id=device.get('native_id'),
          native_terminal_nodes=device['nodes'][:3],
          full_active={key:summary(val[active])for key,val in signals.items()},
          positive_vbc_duration_bounds=time_bias,original_phase_observations=phases,
          at_unique_master_current_transition={key:summary(np.interp(transitions,t,val))for key,val in signals.items()})
    return dict(devices=result,actual_selectors=8,original_bits=len(edges),
      original_slave_deadline_late_bits=int(bad.sum()),original_slave_deadline_other_bits=int((~bad).sum()),
      original_deadline_ui=.3,full_native_rows=len(t),new_acceptance_gate=False,
      raw_or_clock_modified=False,
      scope='Native external B/C/E voltages and collector currents only. VBC markers are diagnostic, not acceptance limits or proof of stored charge/saturation causality. Fixed original phases and original output deadline classify observations; no edge realignment or ideal signal regeneration.')
def controls():
    t=np.linspace(0.,10.,101);active=t>=1
    graph={x:{y+'_selectors':[x+'_'+y+'0',x+'_'+y+'1']for y in ('track','hold')}for x in ('master','slave')}
    members={n:dict(nx=2,native_id=i,nodes=[n+'c',n+'b',n+'e','0'])for i,n in enumerate(n for b in graph.values()for ns in b.values()for n in ns)}
    nodes={};w={}
    for n,d in members.items():
        for key,value in zip(d['nodes'][:3],[1.,1.2,.3],strict=True):nodes[key]=np.full(len(t),value)
        w['@q.'+n+'.qnpn13g2[ic]']=np.full(len(t),.0015)
    edges=np.array([2.,3.,4.,5.])
    windows=dict(rows=[dict(bit_index=i+1,original_edge_s=float(e),matching_transitions=1,steering_transition_s=float(e+.1),
      signed_at_original_deadline_v=dict(slave_output=.05 if i%2 else .2))for i,e in enumerate(edges)])
    def run(tt=t,g=graph,m=members,ns=nodes,ww=w,win=windows):
        return observe(tt,g,m,ns.__getitem__,ww,edges,win,1.,active)
    before={k:a.copy()for k,a in nodes.items()}
    r=run();assert r['actual_selectors']==8 and r['original_slave_deadline_late_bits']==2
    for d in r['devices'].values():
        assert abs(d['full_active']['vbc_v']['mean']-.2)<1e-12
        assert abs(d['full_active']['ic_per_emitter_a']['mean']-.00075)<1e-12
        assert d['positive_vbc_duration_bounds']['0.1']['lower_s']==9.
    assert all(np.array_equal(a,nodes[k])for k,a in before.items())
    rejected=[]
    for label in ('duplicate-selector','missing-selector','zero-area','nan-base','inf-current','nonmonotonic-time','ambiguous-transition','changed-original-edge'):
        tt,g,m,ns,ww,win=copy.deepcopy((t,graph,members,nodes,w,windows))
        n=g['master']['track_selectors'][0]
        if label=='duplicate-selector':g['master']['track_selectors'][1]=n
        elif label=='missing-selector':del m[n]
        elif label=='zero-area':m[n]['nx']=0
        elif label=='nan-base':ns[m[n]['nodes'][1]][3]=float('nan')
        elif label=='inf-current':ww['@q.'+n+'.qnpn13g2[ic]'][3]=float('inf')
        elif label=='nonmonotonic-time':tt[5]=tt[4]
        elif label=='ambiguous-transition':win['rows'][0]['matching_transitions']=2
        else:win['rows'][0]['original_edge_s']+=.01
        try:run(tt,g,m,ns,ww,win)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted '+label)
    assert len(rejected)==8
    return dict(exact_voltage_current_fixture=True,original_arrays_unchanged=True,rejected=rejected,native_or_electrical_acceptance=False)
