#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Minimax placement of the actual60 routed TX legs; geometry planning only."""
import json,math,re
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.optimize import linprog

def box(raw):return list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)))
def center(raw):
    a,b,c,d=box(raw);return ((a+c)/2,(b+d)/2)

def solve_rows(labels,fixed,edges,spacing,old):
    assert len(set(labels))==len(labels)and set(old)==set(labels)and set(fixed)<=set(labels)
    assert edges and all(a in old and b in old and a!=b and h>=0 for a,b,delta,h in edges)
    n=len(labels);m=len(edges);ix={s:i for i,s in enumerate(labels)}
    constraints=[];bounds=[]
    # Variables: native macro Y, each actual leg length, largest leg length.
    for j,(a,b,delta,h)in enumerate(edges):
        for sign in (-1,1):
            row=np.zeros(n+m+1);row[ix[a]]=sign;row[ix[b]]=-sign;row[n+j]=-1
            constraints.append(row);bounds.append(-h-sign*delta)
        row=np.zeros(n+m+1);row[n+j]=1;row[-1]=-1;constraints.append(row);bounds.append(0)
    for a,b,gap in spacing:
        row=np.zeros(n+m+1);row[ix[a]]=1;row[ix[b]]=-1;constraints.append(row);bounds.append(-gap)
    limits=[(fixed[k],fixed[k])if k in fixed else(0.,max(old.values()))for k in labels]+[(0,None)]*(m+1)
    c=np.zeros(n+m+1);c[-1]=1.
    first=linprog(c,A_ub=np.array(constraints),b_ub=np.array(bounds),bounds=limits,method='highs')
    assert first.success,('Minimax layout infeasible',first.message)
    optimum=float(first.x[-1])
    # Second objective cannot trade a longer worst wire for lower total length.
    limits[-1]=(0,optimum+.001);c[:]=0;c[n:n+m]=1
    second=linprog(c,A_ub=np.array(constraints),b_ub=np.array(bounds),bounds=limits,method='highs')
    assert second.success,second.message
    ys={k:round(round(float(second.x[ix[k]])/.005)*.005,6)for k in labels}
    for a,b,gap in spacing:ys[b]=max(ys[b],round(ys[a]+gap,6))
    assert all(abs(ys[k]-v)<1e-8 for k,v in fixed.items())
    assert all(ys[b]-ys[a]>=gap-1e-8 for a,b,gap in spacing)
    lengths=[h+abs(ys[a]-ys[b]+delta)for a,b,delta,h in edges]
    assert max(lengths)<=optimum+.02
    return ys,dict(first_objective_lower_bound_um=optimum,rounded_max_fixed_track_length_um=max(lengths),
                   rounded_sum_fixed_track_length_um=sum(lengths),solver='scipy.optimize.linprog/HiGHS',
                   grid_um=.005,lexicographic_objectives=['minimum maximum actual-leg length','minimum total length at fixed maximum'])

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
    assert allocate([('a',0,100),('b',10,20),('c',112,150)],[1,2])==dict(a=1,b=2,c=1)
    bad=[]
    for name,fn in [
        ('missing_endpoint',lambda:solve_rows(list(old),{},[('z','b',0,10)],[],old)),
        ('infeasible_separation',lambda:solve_rows(list(old),dict(a=0.,d=900.),[('a','d',0,10)],[('a','d',1000)],old)),
        ('overfull_channels',lambda:allocate([('a',0,100),('b',10,20)],[1]))]:
        try:fn()
        except AssertionError:bad.append(name)
        else:raise AssertionError('Accepted '+name)
    return dict(chain_exact_optimum=True,overlap_separation_and_disjoint_reuse=True,rejected=bad)

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
    ys,solver=solve_rows(labels,fixed,edges,spacing,old)
    # Native failed GDS showed two actual shorts where p16_11 stubs cross p8_7.
    # Preserve every other solved row; move this macro to its original600um
    # row lattice and regenerate all parent routes. This is a candidate repair,
    # not proof that all other same-layer interactions are absent.
    root=Path(__file__).resolve().parents[1]
    failure=json.loads((root/'docs/evidence/tx-v5-minimax-first-lvs-rejection-20261019.json').read_text())
    diagnosis=json.loads((root/'docs/evidence/tx-v5-minimax-native-short-diagnosis-20261019.json').read_text())
    assert failure['summary_sha256']=='25a1eb322fd590ba4b5ed12b0959adeb03a3ec77055b2adbd9a550d16cd87aa5'
    assert diagnosis['summary_sha256']=='29369447c9776fc3acc6409ac0271e10f32b155067d1e3a23a0f627faf0915fc'
    assert diagnosis['report']['original_source']['summary_sha256']==failure['summary_sha256']
    native=diagnosis['report']['native']
    assert {tuple(sorted({a['logical_net']for a in v}))for v in native['shorted_logical_groups'].values()}=={('p16_11n','p8_7p'),('p16_11p','sp8_7n')}
    assert not native['opened_logical_nets']
    assert ys==failure['report']['data_route_plan']['row_targets_um']
    before_row=ys['p8_7'];phase=old['p8_7']%600
    ys['p8_7']=phase+600*math.ceil((before_row-phase)/600)
    assert before_row==7808.605 and ys['p8_7']==8100.
    assert all(ys[k]==v for k,v in fixed.items())
    assert all(ys[b]-ys[a]>=gap-1e-8 for a,b,gap in spacing)
    collision_repair=dict(native_diagnosis_run=diagnosis['run'],summary_sha256=diagnosis['summary_sha256'],
        macro='p8_7',before_row_um=before_row,after_row_um=ys['p8_7'],
        other_solved_rows_unchanged=True,original_row_lattice_phase_um=phase,
        identified_short_pairs=[['p16_11n','p8_7p'],['p16_11p','sp8_7n']],
        native_verification_required=True)
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
    return dict(status='PLANNED_ALL60_LEG_MINIMAX_ROWS_AND_RAIL_AWARE_CHANNELS_NOT_PHYSICAL_OR_ELECTRICAL_ACCEPTANCE',
        row_targets_um=ys,original_rows_um=old,fixed_rows_um=fixed,track_x_um=tracks,track_inventory=track_inventory,
        collision_repair=collision_repair,routes=lengths,maximum_before_um=before,maximum_after_um=after,sum_before_um=sum(q['before_um']for q in lengths),
        sum_after_um=sum(q['after_um']for q in lengths),solver=solver,
        scope='All60 original intermacro legs planned together; fixed16leaf rows/final row, all macro X coordinates and minimum600um same-column separation. Child geometry, device cards, clocks, source bits, electrical gates unchanged. Original rail widths remain. Every regressed leg retained; actual GDS DRC/LVS and fresh RC/fullwave gates still required.')
