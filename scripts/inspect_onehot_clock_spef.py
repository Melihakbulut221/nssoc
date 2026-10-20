#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inspect selected immutable nominal SPEF clock networks, not qualified PEX."""
import json,math,re
from collections import defaultdict
import heapq
def number(s):
    v=float(s);assert math.isfinite(v)and v>=0
    return v
def parse(path,wanted):
    names={};selected={};current=None;section=None;inmap=False;units={};pin_none=False
    def expand(s):
        a,sep,b=s.partition(':')
        return names.get(a,a)+(sep+b if sep else '')
    with path.open()as f:
        for line in f:
            words=line.split()
            if not words or words[0].startswith('//'):continue
            token=words[0]
            if token=='*DESIGN_FLOW':pin_none='"PIN_CAP NONE"'in line
            if token in ('*C_UNIT','*R_UNIT'):
                factor={'*C_UNIT':{'F':1e12,'NF':1e3,'PF':1.,'FF':1e-3},'*R_UNIT':{'OHM':1.,'KOHM':1e3}}[token]
                assert len(words)==3 and words[2].upper()in factor
                units[token]=number(words[1])*factor[words[2].upper()];assert units[token]>0
            if token=='*NAME_MAP':inmap=True;continue
            if inmap and re.fullmatch(r'\*\d+',token):
                assert len(words)==2 and token not in names
                names[token]=words[1];continue
            if token=='*D_NET':
                inmap=False;assert current is None and len(words)==3 and len(units)==2 and pin_none
                name=expand(words[1]);current=dict(name=name,declared_cap_pf=number(words[2])*units['*C_UNIT'],connections=[],C=[],R=[])if name in wanted else False
                section=None;continue
            if token=='*END':
                assert current is not None
                if current:
                    assert current['name']not in selected
                    selected[current['name']]=current
                current=None;section=None;continue
            if current is None:continue
            if token in ('*CONN','*CAP','*RES'):section=token;continue
            if not current:continue
            if section=='*CONN':
                assert token in ('*I','*P')and len(words)>=3
                current['connections'].append(dict(node=expand(words[1]),direction=words[2],kind=token))
            elif section=='*CAP':
                assert words[0].isdigit()and len(words)in (3,4)
                current['C'].append(dict(nodes=[expand(x)for x in words[1:-1]],pf=number(words[-1])*units['*C_UNIT']))
            elif section=='*RES':
                assert words[0].isdigit()and len(words)==4
                current['R'].append(dict(nodes=[expand(words[1]),expand(words[2])],ohm=number(words[3])*units['*R_UNIT']))
    assert current is None and set(selected)==set(wanted)
    return selected
def review(net,geometry):
    expected={t['instance']+':'+t['pin']:t['direction'][0]for t in geometry['terminals']}
    connections=net['connections']
    assert len(connections)==len({x['node']for x in connections})
    assert {x['node']:x['direction']for x in connections}==expected,'Native ODB/SPEF clock pin identity differs'
    assert net['name']==geometry['net']
    total=sum(c['pf']for c in net['C'])
    assert abs(total-net['declared_cap_pf'])<=max(1e-8,1e-5*max(total,net['declared_cap_pf']))
    graph=defaultdict(dict)
    for r in net['R']:
        a,b=r['nodes'];assert a!=b
        value=min(r['ohm'],graph[a].get(b,math.inf))
        graph[a][b]=graph[b][a]=value
    assert graph and set(expected)<=set(graph)
    for c in net['C']:assert set(c['nodes'])&set(graph),'Capacitance has no node in selected net'
    driver=geometry['driver'].rsplit('/',1);driver=':'.join(driver)
    assert expected[driver]=='O'
    distance={driver:0.};queue=[(0.,driver)]
    while queue:
        cost,node=heapq.heappop(queue)
        if cost!=distance[node]:continue
        for other,weight in graph[node].items():
            nextcost=cost+weight
            if nextcost<distance.get(other,math.inf):
                distance[other]=nextcost;heapq.heappush(queue,(nextcost,other))
    assert set(distance)==set(graph),'Disconnected native resistor graph'
    paths={}
    for node in expected:
        if node==driver:continue
        paths[node]=distance[node]
    return dict(net=net['name'],driver=driver,declared_wire_cap_pf=net['declared_cap_pf'],serialized_wire_cap_pf=total,
      resistor_count=len(net['R']),resistor_nodes=len(graph),cap_entries=len(net['C']),
      coupling_entries=sum(len(c['nodes'])==2 for c in net['C']),
      lowest_series_resistance_path_ohm=paths,port_membership_exact=True,
      scope='Nominal exported wire RC. Shortest series-R path is an upper bound on effective R, never an STA delay. Pin capacitance excluded; no qualified RF/PEX claim.')
