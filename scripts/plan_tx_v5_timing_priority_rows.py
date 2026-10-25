#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prioritize actual fast TX data legs on the original native row lattice."""
import json,math,re
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.optimize import linprog,milp,Bounds,LinearConstraint

def box(raw):return list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)))
def center(raw):
    a,b,c,d=box(raw);return ((a+c)/2,(b+d)/2)

def solve_rows(labels,fixed,edges,spacing,old,row_quantum=None,weights=None,length_ceiling=None):
    assert len(set(labels))==len(labels)and set(old)==set(labels)and set(fixed)<=set(labels)
    assert edges and all(a in old and b in old and a!=b and h>=0 for a,b,delta,h in edges)
    n=len(labels);m=len(edges);ix={s:i for i,s in enumerate(labels)}
    weights=[1.]*m if weights is None else list(weights)
    assert len(weights)==m and all(math.isfinite(w)and w>0 for w in weights)
    assert length_ceiling is None or (math.isfinite(length_ceiling)and length_ceiling>0)
    constraints=[];bounds=[]
    # Variables: native macro Y, each actual leg length, largest leg length.
    for j,(a,b,delta,h)in enumerate(edges):
        for sign in (-1,1):
            row=np.zeros(n+m+1);row[ix[a]]=sign;row[ix[b]]=-sign;row[n+j]=-1
            constraints.append(row);bounds.append(-h-sign*delta)
        row=np.zeros(n+m+1);row[n+j]=weights[j];row[-1]=-1;constraints.append(row);bounds.append(0)
    for a,b,gap in spacing:
        row=np.zeros(n+m+1);row[ix[a]]=1;row[ix[b]]=-1;constraints.append(row);bounds.append(-gap)
    limits=[(fixed[k],fixed[k])if k in fixed else(0.,max(old.values()))for k in labels]+[(0,length_ceiling)]*m+[(0,None)]
    A=np.array(constraints);rhs=np.array(bounds);phase=np.zeros(n);scale=1.
    if row_quantum is not None:
        assert row_quantum>0
        scale=float(row_quantum);phase=np.array([old[k]%scale for k in labels])
        rhs=rhs-A[:,:n]@phase;A[:,:n]*=scale
        limits[:n]=[(math.ceil((lo-phase[i])/scale-1e-9),
                     math.floor((hi-phase[i])/scale+1e-9))for i,(lo,hi)in enumerate(limits[:n])]
        assert all(lo<=hi for lo,hi in limits[:n])
    def optimize(objective,limits):
        if row_quantum is None:
            return linprog(objective,A_ub=A,b_ub=rhs,bounds=limits,method='highs')
        return milp(objective,integrality=np.array([1]*n+[0]*(m+1)),
                    bounds=Bounds([lo for lo,hi in limits],[np.inf if hi is None else hi for lo,hi in limits]),
                    constraints=LinearConstraint(A,-np.inf,rhs),
                    options=dict(mip_rel_gap=0.,time_limit=120.,presolve=False))
    def validate(solution,limits):
        assert solution.success and solution.x is not None
        assert np.max(A@solution.x-rhs)<1e-7
        for value,(lo,hi)in zip(solution.x,limits,strict=True):
            assert value>=lo-1e-7 and (hi is None or value<=hi+1e-7)
        if row_quantum is not None:
            assert np.max(np.abs(solution.x[:n]-np.round(solution.x[:n])))<1e-7
            assert solution.mip_gap==0.
    c=np.zeros(n+m+1);c[-1]=1.
    first=optimize(c,limits)
    assert first.success,('Minimax layout infeasible or optimum unproved',first.message)
    validate(first,limits)
    optimum=float(first.x[-1])
    # Second objective cannot trade a longer worst wire for lower total length.
    limits[-1]=(0,optimum+.001);c[:]=0;c[n:n+m]=weights
    second=optimize(c,limits)
    assert second.success,second.message
    validate(second,limits)
    if row_quantum is None:
        ys={k:round(round(float(second.x[ix[k]])/.005)*.005,6)for k in labels}
        for a,b,gap in spacing:ys[b]=max(ys[b],round(ys[a]+gap,6))
    else:
        assert all(abs(v-round(v))<1e-6 for v in second.x[:n])
        ys={k:round(float(phase[ix[k]])+scale*round(float(second.x[ix[k]])),6)for k in labels}
        assert all(abs((ys[k]-old[k])/scale-round((ys[k]-old[k])/scale))<1e-9 for k in labels)
    assert all(abs(ys[k]-v)<1e-8 for k,v in fixed.items())
    assert all(ys[b]-ys[a]>=gap-1e-8 for a,b,gap in spacing)
    lengths=[h+abs(ys[a]-ys[b]+delta)for a,b,delta,h in edges]
    assert max(w*l for w,l in zip(weights,lengths,strict=True))<=optimum+max(weights)*.02
    assert length_ceiling is None or max(lengths)<=length_ceiling+.02
    return ys,dict(first_objective_lower_bound_um=optimum,rounded_max_fixed_track_length_um=max(lengths),
                   rounded_max_weighted_fixed_track_length_um=max(w*l for w,l in zip(weights,lengths,strict=True)),
                   weights=weights,length_ceiling_um=length_ceiling,
                   rounded_sum_fixed_track_length_um=sum(lengths),
                   solver='scipy.optimize.linprog/HiGHS'if row_quantum is None else'scipy.optimize.milp/HiGHS',
                   first_mip_dual_bound=None if row_quantum is None else float(first.mip_dual_bound),
                   first_mip_gap=None if row_quantum is None else float(first.mip_gap),
                   second_mip_gap=None if row_quantum is None else float(second.mip_gap),
                   row_quantum_um=row_quantum,mip_presolve=False,independent_solution_residuals_checked=True,grid_um=.005,
                   lexicographic_objectives=['minimum maximum stride-weighted actual-leg length','minimum weighted total length at fixed maximum'])

def allocate(intervals,tracks):
    occupied={x:[]for x in tracks};answer={}
    for name,lo,hi in sorted(intervals,key=lambda z:(z[1],z[2],z[0])):
        assert lo<=hi and name not in answer
        available=[x for x in tracks if all(lo>=b+12 or hi<=a-12 for a,b in occupied[x])]
        assert available,('No legal signal channel remains',name,lo,hi)
        x=available[0];occupied[x].append((lo,hi));answer[name]=x
    return answer

def controls():
    old=dict(a=0.,b=200.,c=700.,d=900.)
    ys,r=solve_rows(list(old),dict(a=0.,d=900.),[('a','b',0.,10.),('b','c',0.,10.),('c','d',0.,10.)],[],old)
    assert abs(r['first_objective_lower_bound_um']-310)<1e-7
    assert abs(ys['b']-300)<.02 and abs(ys['c']-600)<.02
    yi,ri=solve_rows(list(old),dict(a=0.,d=900.),[('a','b',0.,10.),('b','c',0.,10.),('c','d',0.,10.)],[],old,row_quantum=100.)
    assert yi==dict(a=0.,b=300.,c=600.,d=900.)and abs(ri['first_objective_lower_bound_um']-310)<1e-7
    assert ri['first_mip_gap']==ri['second_mip_gap']==0.
    chain=[('a','b',0.,10.),('b','c',0.,10.),('c','d',0.,10.)]
    yw,rw=solve_rows(list(old),dict(a=0.,d=900.),chain,[],old,weights=[1.,2.,4.])
    assert abs(rw['first_objective_lower_bound_um']-930/(1+1/2+1/4))<1e-7
    assert abs(yw['b']-(930/(1+1/2+1/4)-10))<.02
    yl,rl=solve_rows(list(old),dict(a=0.,d=900.),chain,[],old,row_quantum=100.,weights=[1.,2.,4.],length_ceiling=700.)
    assert yl==dict(a=0.,b=600.,c=800.,d=900.)and abs(rl['first_objective_lower_bound_um']-610)<1e-7
    assert allocate([('a',0,100),('b',10,20),('c',112,150)],[1,2])==dict(a=1,b=2,c=1)
    bad=[]
    for name,fn in [
        ('missing_endpoint',lambda:solve_rows(list(old),{},[('z','b',0,10)],[],old)),
        ('infeasible_separation',lambda:solve_rows(list(old),dict(a=0.,d=900.),[('a','d',0,10)],[('a','d',1000)],old)),
        ('overfull_channels',lambda:allocate([('a',0,100),('b',10,20)],[1]))]:
        try:fn()
        except AssertionError:bad.append(name)
        else:raise AssertionError('Accepted '+name)
    return dict(chain_exact_optimum=True,integer_lattice_exact_optimum=True,weighted_chain_exact_optimum=True,weighted_lattice_exact_optimum=True,overlap_separation_and_disjoint_reuse=True,rejected=bad)

def plan_candidate(record):
    assert record['total_devices']==1674 and len(record['placements'])==31 and len(record['signal_routes'])==60
    p=record['placements'];old={k:box(v['bbox_um'])[1]for k,v in p.items()}
    labels=sorted(p);fixed={k:y for k,y in old.items()if k.startswith('p16_')or k=='f'}
    assert len(fixed)==17
    spacing=[];columns=defaultdict(list)
    for k,v in p.items():columns[box(v['bbox_um'])[0]].append(k)
    assert len(columns)==5
    for col,tags in sorted(columns.items()):
        tags.sort(key=lambda k:(old[k],k))
        for a,b in zip(tags,tags[1:]):spacing.append((a,b,600.))
        assert all(box(p[k]['bbox_um'])[3]-old[k]<600 for k in tags)
    edges=[]
    for r in record['signal_routes']:
        (a,ap),(b,bp)=[s.split('.')for s in r['endpoints']]
        x0,y0=center(p[a]['ports'][ap]);x1,y1=center(p[b]['ports'][bp])
        assert abs(y0-r['y_um'][0])<1e-7 and abs(y1-r['y_um'][1])<1e-7
        h=abs(x0-r['x_um'])+abs(x1-r['x_um'])
        assert abs(h+abs(y1-y0)-r['centerline_length_um'])<1e-7
        edges.append((a,b,(y0-old[a])-(y1-old[b]),h))
    # Continuous Y placement produced native public and private conductor shorts.
    # Preserve every original row residue: horizontal crossings retain the original
    # local routing bands. Full native LVS/DRC still decide physical acceptance.
    root=Path(__file__).resolve().parents[1]
    prior=json.loads((root/'docs/evidence/tx-v5-minimax-physical-pass-20261019.json').read_text())
    assert prior['source_run']==39265712814 and prior['summary_sha256']=='5d81376ebdd2147693e30888276bf60a460aa5191c5454ae891b6516526b43d9'
    before_priority=prior['report']['layout']['signal_routes']
    assert len(before_priority)==len(edges)==60
    def stride(parent):
        if parent=='f':return 1
        if parent in ('a','b'):return 2
        m=re.fullmatch(r'p(4|8)_(\d+)',parent);assert m,parent
        return int(m[1])
    weights=[16/stride(r['endpoints'][1].split('.')[0])for r in record['signal_routes']]
    assert {w:weights.count(w)for w in set(weights)}=={2.:32,4.:16,8.:8,16.:4}
    # Bound the actual horizontal increase over every permitted rail-aware track.
    # This retains the original independent maximum-length gate after allocation.
    original_max=max(r['centerline_length_um']for r in record['signal_routes'])
    extra=[]
    for r,edge in zip(record['signal_routes'],edges,strict=True):
        (a,ap),(b,bp)=[v.split('.')for v in r['endpoints']]
        col=box(p[b]['bbox_um'])[0]
        right=max(box(bb)[2]for k in columns[col]for bb in p[k]['ports'].values())
        x0=center(p[a]['ports'][ap])[0];x1=center(p[b]['ports'][bp])[0]
        for offset in (40,52,64,76,88,100,112,172,184,220,232,244,256):
            track=right+offset;extra.append(abs(x0-track)+abs(x1-track)-edge[3])
    reserve=max(0.,max(extra))+.05
    ceiling=original_max*.8-reserve
    ys,solver=solve_rows(labels,fixed,edges,spacing,old,row_quantum=600.,weights=weights,length_ceiling=ceiling)
    row_lattice=dict(quantum_um=600.,original_residue_um={k:y%600. for k,y in old.items()},
        private_diagnosis_run=39263440258,
        private_diagnosis_summary_sha256='0c58408eee896a62dbf349ce3f2d8e8d79e02373ac7f52ebdc0c0a5e21edb154',
        identified_short_pairs=[['p16_8p','p8_0_qn'],['p16_8n','p8_0_qp']],
        all_macro_x_native_children_and_fixed_rows_unchanged=True,native_verification_required=True)
    routes=[];bycol=defaultdict(list)
    for r in record['signal_routes']:
        child,parent=[s.split('.')[0]for s in r['endpoints']]
        yy=[y+ys[k]-old[k]for y,k in zip(r['y_um'],(child,parent),strict=True)]
        bycol[box(p[parent]['bbox_um'])[0]].append((r['net'],min(yy),max(yy)))
        routes.append(dict(original=r,ys=yy,child=child,parent=parent))
    tracks={};track_inventory={}
    for col,intervals in sorted(bycol.items()):
        tags=columns[col];right=max(box(b)[2]for k in tags for b in p[k]['ports'].values())
        # Fixed physical rail widths: AVDD32 at right+140, SUB4 at right+200.
        # Adjacent AVSS64 at next column-40; final AVSS128 at right+340.
        possible=[round(right+o,6)for o in (40,52,64,76,88,100,112,172,184,220,232,244,256)]
        rail=[(right+140,32.),(right+200,4.)]
        if col<2800:rail.append((col+700-40,64.))
        else:rail.append((right+340,128.))
        assert all(all(abs(x-c)>=w/2+6 for c,w in rail)for x in possible)
        tracks.update(allocate(intervals,possible));track_inventory[str(col)]=possible
    assert len(tracks)==60
    lengths=[]
    for q in routes:
        r=q['original'];x=tracks[r['net']]
        (a,ap),(b,bp)=[s.split('.')for s in r['endpoints']]
        length=abs(center(p[a]['ports'][ap])[0]-x)+abs(center(p[b]['ports'][bp])[0]-x)+abs(q['ys'][1]-q['ys'][0])
        lengths.append(dict(net=r['net'],endpoints=r['endpoints'],x_um=x,y_um=q['ys'],
                            before_um=r['centerline_length_um'],after_um=length))
    before=max(q['before_um']for q in lengths);after=max(q['after_um']for q in lengths)
    assert after<before*.8,(before,after)
    prior_by={r['net']:r for r in before_priority};assert set(prior_by)=={r['net']for r in lengths}
    weighted=[];stage_metrics={}
    for q,w in zip(lengths,weights,strict=True):
        previous=prior_by[q['net']];assert previous['endpoints']==q['endpoints']
        q.update(weight=w,previous_minimax_um=previous['centerline_length_um'])
        weighted.append(dict(net=q['net'],before=previous['centerline_length_um']*w,after=q['after_um']*w))
        parent=q['endpoints'][1].split('.')[0];st=str(stride(parent))
        stage_metrics.setdefault(st,[]).append(q)
    priority=dict(maximum_weighted_before=max(x['before']for x in weighted),
        maximum_weighted_after=max(x['after']for x in weighted),
        stage_maxima={k:dict(before=max(x['previous_minimax_um']for x in v),after=max(x['after_um']for x in v))for k,v in stage_metrics.items()},
        regressed_legs=[q for q in lengths if q['after_um']>q['previous_minimax_um']+1e-7],
        original_maximum_ceiling_um=original_max*.8,
        physical_input_review_run=39301708644,
        meaning='16/receiver stride is a geometry priority proxy, not measured delay. Original clocks, bit phases and electrical gates remain unchanged; every regressed leg requires fresh full-wave testing.')
    assert priority['maximum_weighted_after']<priority['maximum_weighted_before']
    assert priority['stage_maxima']['1']['after']<priority['stage_maxima']['1']['before']
    return dict(status='PLANNED_ALL60_LEG_TIMING_PRIORITY_ROWS_AND_RAIL_AWARE_CHANNELS_NOT_PHYSICAL_OR_ELECTRICAL_ACCEPTANCE',
        timing_priority=priority,
        row_targets_um=ys,original_rows_um=old,fixed_rows_um=fixed,track_x_um=tracks,track_inventory=track_inventory,
        row_lattice=row_lattice,routes=lengths,maximum_before_um=before,maximum_after_um=after,sum_before_um=sum(q['before_um']for q in lengths),
        sum_after_um=sum(q['after_um']for q in lengths),solver=solver,
        scope='All60 original intermacro legs prioritized by receiver stride, with original16leaf/final fixed rows, macro X,600um separation/residues, children, devices, clocks and electrical gates preserved. Original global route ceiling remains; every regression against measured minimax routes is retained. DRC/LVS and fresh RC/fullwave must decide acceptance.')
