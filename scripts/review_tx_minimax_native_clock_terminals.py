#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read actual resistor-connected clock bases and saved native edge brackets."""
import hashlib,json,math
from pathlib import Path
import numpy as np
def inspect(model,contract,t,values,start):
    raw=model.read_bytes();rows=[]
    for line in raw.decode().splitlines():
        line=line.strip().lower()
        if not line or line.startswith('*'):continue
        if line.startswith('+'):
            assert rows;rows[-1]+=line[1:].split()
        else:rows.append(line.split())
    assert rows[0][0]=='.subckt'and rows[-1][0]=='.ends'
    public=set(rows[0][2:]);assert len(public)==len(rows[0][2:])
    parent={}
    def find(n):
        assert n in parent,('Missing actual metal node',n)
        while parent[n]!=n:
            parent[n]=parent[parent[n]];n=parent[n]
        return n
    resistors=[];caps=[];hbt={}
    for row in rows[1:-1]:
        if row[0].startswith('r'):
            assert len(row)==4
            value=float(row[3]);assert math.isfinite(value)and value>0
            for n in row[1:3]:parent.setdefault(n,n)
            a,b=map(find,row[1:3]);parent[b]=a
            resistors.append(row)
        elif row[0].startswith('c'):
            assert len(row)==4
            value=float(row[3]);assert math.isfinite(value)and value>=0;caps.append(row)
        elif len(row)>5 and row[0].startswith('x')and row[5]=='npn13g2':
            hbt[row[0]]=row
    assert len(resistors)==116611 and len(caps)==77516 and len(hbt)==589
    def bound(n):return ('0'if n in ('avss','sub','wire_cref')else n)if n in public else 'xtree.'+n
    def voltage(n):
        assert 'v('+n+')'in values,('Unsaved native voltage',n)
        return values['v('+n+')']
    def edge_brackets(delta):
        idx=np.flatnonzero((delta[:-1]<=0)&(delta[1:]>0))
        fall=np.flatnonzero((delta[:-1]>=0)&(delta[1:]<0))
        return {sign:[(float(t[i]),float(t[i+1]))for i in ids if t[i]>=start]
                for sign,ids in ((1,idx),(-1,fall))}
    def pair_edges(pub,native,period):
        answer=[]
        for sign in (1,-1):
            p=pub[sign];q=native[sign];used=set();matched=[];unmatched=[]
            centers=np.array([(a+b)/2 for a,b in p])
            for a,b in q:
                if not len(centers):unmatched.append([a,b]);continue
                j=int(np.argmin(abs(centers-(a+b)/2)))
                # Diagnostic event association only; original signal acceptance is unchanged.
                if j in used or abs(centers[j]-(a+b)/2)>=period/2:
                    unmatched.append([a,b]);continue
                used.add(j);lo,hi=p[j]
                matched.append(dict(public_bracket_s=[lo,hi],native_bracket_s=[a,b],
                                    delay_interval_ps=[(a-hi)*1e12,(b-lo)*1e12]))
            answer.append(dict(polarity=sign,public_edges=len(p),native_edges=len(q),
                unmatched_public=len(p)-len(used),unmatched_native=unmatched,
                matched=matched))
        return answer
    clocks=[];total=0;active=t>=start;roots=[]
    for clock in contract['tree_plan']['clocks']:
        name=clock['name'];pins=[name+'p',name+'n']
        assert all(n in public for n in pins)
        targets=[find(n)for n in pins];assert targets[0]!=targets[1];roots+=targets
        groups=[];wire=[]
        for pin,root in zip(pins,targets,strict=True):
            group=[]
            for instance,row in hbt.items():
                if row[2] in parent and find(row[2])==root:
                    key='xtree.'+instance;assert key in contract['hbt']
                    base=bound(row[2]);assert contract['hbt'][key]['terminals'][1]==base
                    voltage(base);group.append(dict(device=key,node=base))
            assert len(group)==2,(pin,len(group));total+=len(group);groups.append(group)
            incident=reference=internal=cross=0.
            for row in caps:
                a,b=row[1:3];value=float(row[3]);inside=[n in parent and find(n)==root for n in (a,b)]
                if not any(inside):continue
                incident+=value
                if all(inside):internal+=value
                elif 'wire_cref'in (a,b):reference+=value
                else:cross+=value
            wire.append(dict(port=pin,component=root,incident_c_f=incident,
                wire_cref_c_f=reference,internal_component_c_f=internal,cross_component_c_f=cross))
        pd=voltage(pins[0])-voltage(pins[1]);pe=edge_brackets(pd);pairs=[]
        for pos in groups[0]:
            for neg in groups[1]:
                vp,vn=voltage(pos['node']),voltage(neg['node']);diff=vp-vn;cm=(vp+vn)/2
                pairs.append(dict(positive=pos,negative=neg,
                    native_diff_range_v=[float(diff[active].min()),float(diff[active].max())],
                    native_commonmode_range_v=[float(cm[active].min()),float(cm[active].max())],
                    event_brackets=pair_edges(pe,edge_brackets(diff),clock['period'])))
        clocks.append(dict(clock=clock,wire_components=wire,terminal_pairs=pairs))
    assert len(clocks)==31 and total==124 and len(set(roots))==62
    assert hashlib.sha256(model.read_bytes()).hexdigest()==hashlib.sha256(raw).hexdigest()
    return dict(status='COMPLETE_ACTUAL31_CLOCKS_124_NATIVE_SELECTOR_BASES_READ_ONLY',
        model_sha256=hashlib.sha256(raw).hexdigest(),clock_count=31,actual_selector_bases=124,
        clocks=clocks,accepted=False,full_phy_accepted=False,
        scope='Actual resistor-component membership, native saved voltage edge brackets and incident wire capacitance. Nearest same-polarity edge association is diagnostic only; it does not alter or qualify original bit-phase gates. R graph excludes intrinsic device paths. RF/substrate and analog device capacitances are not included in reported wire C.')
