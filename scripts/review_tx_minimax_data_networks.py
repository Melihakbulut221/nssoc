#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual metal-component loading and pair resistance at native TX data bases."""
import hashlib,math
from collections import defaultdict
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

def pair_resistances(edges, source, targets):
    nodes={n for _,a,b,r in edges for n in (a,b)}
    assert source in nodes and set(targets)<=nodes
    assert all(math.isfinite(r) and r>0 and a!=b for _,a,b,r in edges)
    adjacency=defaultdict(set)
    for _,a,b,r in edges:adjacency[a].add(b);adjacency[b].add(a)
    seen={source};pending=[source]
    while pending:
        for n in adjacency[pending.pop()]-seen:seen.add(n);pending.append(n)
    assert seen==nodes,'Disconnected passive network'
    ordered=sorted(nodes-{source});index={n:i for i,n in enumerate(ordered)}
    rr=[];cc=[];vv=[]
    def add(a,b,g):
        if a!=source and b!=source:rr.append(index[a]);cc.append(index[b]);vv.append(g)
    for _,a,b,r in edges:
        g=1/r;add(a,a,g);add(b,b,g);add(a,b,-g);add(b,a,-g)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(ordered),)*2).tocsc()
    lu=splu(matrix);out=[]
    for target in targets:
        if target==source:out.append(dict(source=source,target=target,effective_resistance_ohm=0.,kcl_residual=0.));continue
        rhs=np.zeros(len(ordered));rhs[index[target]]=1.
        sol=lu.solve(rhs);error=float(abs(matrix@sol-rhs).max())
        assert error<1e-6,('Passive KCL residual',error)
        resistance=float(sol[index[target]]);assert math.isfinite(resistance)and resistance>0
        # One ampere injected into target, extracted through grounded source.
        out.append(dict(source=source,target=target,effective_resistance_ohm=resistance,kcl_residual=error))
    return out

def controls():
    def value(edges):return pair_resistances(edges,'a',['b'])[0]['effective_resistance_ohm']
    series=[('r1','a','m',2.),('r2','m','b',3.)]
    parallel=[('r1','a','b',2.),('r2','a','b',3.)]
    triangle=series+[('r3','a','b',5.)]
    assert abs(value(series)-5)<1e-12
    assert abs(value(parallel)-1.2)<1e-12
    assert abs(value(triangle)-2.5)<1e-12
    assert abs(value(triangle[:-1])-5)<1e-12
    assert value([('r1','a','b',1.)])!=value([('r1','a','b',2.)])
    for bad in ([('r','a','b',0.)],[('r','a','b',-1.)],
                [('r','a','b',float('nan'))],
                series+[('r3','x','y',2.)]):
        try:value(bad)
        except AssertionError:pass
        else:raise AssertionError('Malformed passive network accepted')
    return dict(series=True,parallel=True,loop=True,removed_parallel_branch_changes_result=True,
                changed_resistance_changes_result=True,zero_negative_nonfinite_disconnected_rejected=True)

def inspect(model,contract,groups):
    raw=model.read_bytes();rows=[]
    for line in raw.decode().splitlines():
        line=line.strip().lower()
        if not line or line.startswith('*'):continue
        if line.startswith('+'):assert rows;rows[-1]+=line[1:].split()
        else:rows.append(line.split())
    assert rows[0][0]=='.subckt'and rows[-1][0]=='.ends'
    ports=set(rows[0][2:]);parent={};res=[];caps=[];hbt={};native_res=[]
    def find(n):
        assert n in parent,('Missing metal node',n)
        while n!=parent[n]:parent[n]=parent[parent[n]];n=parent[n]
        return n
    for row in rows[1:-1]:
        if row[0].startswith('r'):
            assert len(row)==4
            a,b=row[1:3];value=float(row[3]);assert math.isfinite(value)and value>0 and a!=b
            for n in (a,b):parent.setdefault(n,n)
            parent[find(b)]=find(a);res.append((row[0],a,b,value))
        elif row[0].startswith('c'):
            assert len(row)==4
            value=float(row[3]);assert math.isfinite(value)and value>=0
            caps.append((row[0],row[1],row[2],value))
        elif row[0].startswith('x'):
            if len(row)>5 and row[5]=='npn13g2':hbt[row[0]]=row
            elif len(row)>4 and row[4]=='rppd':native_res.append(row)
    assert len(res)==116611 and len(caps)==77516 and len(hbt)==589
    def bound(n):return ('0'if n in ('avss','sub','wire_cref')else n)if n in ports else 'xtree.'+n
    by_component=defaultdict(list)
    for item in res:by_component[find(item[1])].append(item)
    capacitance=defaultdict(lambda:dict(incident_c_f=0.,wire_cref_c_f=0.,internal_component_c_f=0.,cross_component_c_f=0.))
    for _,a,b,v in caps:
        ra=find(a)if a in parent else None;rb=find(b)if b in parent else None
        for root in {ra,rb}-{None}:
            c=capacitance[root];c['incident_c_f']+=v
            c['internal_component_c_f'if ra==rb else'wire_cref_c_f'if'wire_cref'in(a,b)else'cross_component_c_f']+=v
    bases=defaultdict(list);collectors=defaultdict(list)
    for name,row in hbt.items():
        key='xtree.'+name;dev=contract['hbt'][key]
        assert dev['terminals']==[bound(n)for n in row[1:5]]
        for i,table in ((1,collectors),(2,bases)):
            table[find(row[i])].append(dict(device=key,node=row[i],native_node=bound(row[i]),nx=dev['nx']))
    boundaries=defaultdict(list)
    for row in native_res:
        a,b=row[1:3]
        for n,other in ((a,b),(b,a)):
            boundaries[find(n)].append(dict(device='xtree.'+row[0],node=n,other_node=other,
                other_component=find(other),native_card=' '.join(row)))
    lookup={g['label']:g for g in groups};assert len(lookup)==62
    result=[];intermacro=0;external=0;allroots=[];actual_bases=0
    for leg,targets in sorted(contract['interface_probes'].items()):
        assert leg[-1]in 'pn'
        rawtargets=[n.removeprefix('xtree.')for n in targets]
        roots={find(n)for n in rawtargets};assert len(roots)==1
        root=next(iter(roots));allroots.append(root)
        actual=bases[root];actual_bases+=len(actual)
        assert {bound(n)for n in rawtargets}=={d['native_node']for d in actual}
        assert len(actual)==3,(leg,actual)
        label=leg[:-1];g=lookup[label]
        row=dict(leg=leg,component=root,wire_nodes=len({n for _,a,b,r in by_component[root]for n in (a,b)}),
                 wire_resistors=len(by_component[root]),wire_capacitance=capacitance[root],
                 sinks=actual,original_sample_min_margin_v=g['minimum_signed_margin_v'],
                 original_wrong_sign_samples=g['total_wrong_sign'],resistor_boundaries=boundaries[root])
        if label.startswith('d'):
            assert leg in ports;external+=1
            row['origin']='external_cmos_frontend'
            row['metal_pair_resistance']=pair_resistances(by_component[root],leg,rawtargets)
        else:
            intermacro+=1
            candidates=[b for b in boundaries[root]if len(collectors[b['other_component']])==6]
            assert len(candidates)==1,(leg,candidates,[(b,len(collectors[b['other_component']]))for b in boundaries[root]])
            source=candidates[0];driver=source['other_component']
            row.update(origin='actual_upstream_native_rppd_output_series_resistor',
                driver_series_resistor=source,driver_collectors=collectors[driver],
                driver_wire_capacitance=capacitance[driver],
                metal_pair_resistance=pair_resistances(by_component[root],source['node'],rawtargets),
                driver_metal_pair_resistance=pair_resistances(by_component[driver],source['other_node'],[d['node']for d in collectors[driver]]))
        result.append(row)
    assert len(result)==124 and len(set(allroots))==124 and intermacro==60 and external==64 and actual_bases==372
    assert hashlib.sha256(model.read_bytes()).digest()==hashlib.sha256(raw).digest()
    return dict(status='COMPLETE_ACTUAL124_DATA_LEGS_372_BASES_WIRE_LOAD_AND_METAL_PAIR_RESISTANCE',
        model_sha256=hashlib.sha256(raw).hexdigest(),intermacro_legs=intermacro,external_legs=external,
        native_bases=actual_bases,legs=result,accepted=False,full_phy_accepted=False,
        scope='Metal-only passive effective resistance from each actual output resistor terminal to its native receiving bases, plus output collector branches. Native rppd cards retained, not replaced by linear resistors. Wire C includes reference and cross-net coupling separately; no sumR*C timing estimate or intrinsic/body/RF capacitance claim. Original sample metrics copied from the independently reproduced failed full-wave review, not redefined.')
