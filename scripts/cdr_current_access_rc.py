#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-bound four-network wire RC census; no device simulation or acceptance."""
import ast,hashlib,heapq,math,shlex
from collections import Counter,defaultdict
from itertools import combinations
from pathlib import Path
np=None
coo_matrix=None
splu=None

def load_numeric_dependencies():
    global np,coo_matrix,splu
    import numpy as np
    from scipy.sparse import coo_matrix
    from scipy.sparse.linalg import splu
import build_pcie_local_vco_hybrid_v6 as parser

def require(ok,message):
    if not ok:raise AssertionError(message)

SOLVER_FUNCTION_SHA='5346f0aef7ee3ab8ad6b0d77a0a79ee8e54e7b5ec9585edf09e487d062008993'

def solve(edges,start,stop):
    assert start!=stop
    adj=defaultdict(set)
    for name,a,b,r in edges:
        assert a!=b and math.isfinite(r)and r>0
        adj[a].add(b);adj[b].add(a)
    seen={start};stack=[start]
    while stack:
        n=stack.pop()
        for v in adj[n]-seen:seen.add(v);stack.append(v)
    if stop not in seen:raise ValueError('Disconnected requested wire terminals')
    nodes=sorted(seen-{stop});idx={n:i for i,n in enumerate(nodes)}
    selected=[e for e in edges if e[1]in seen];ii=[];jj=[];vv=[]
    for name,a,b,r in selected:
        g=1/r
        for n in (a,b):
            if n!=stop:ii.append(idx[n]);jj.append(idx[n]);vv.append(g)
        if a!=stop and b!=stop:
            ii.extend((idx[a],idx[b]));jj.extend((idx[b],idx[a]));vv.extend((-g,-g))
    lap=coo_matrix((vv,(ii,jj)),shape=(len(nodes),len(nodes))).tocsc()
    rhs=np.zeros(len(nodes));rhs[idx[start]]=1.
    volts=splu(lap).solve(rhs);assert np.isfinite(volts).all()
    residual=float(np.max(np.abs(lap@volts-rhs)));assert residual<1e-7,('KCL residual',residual)
    v=dict(zip(nodes,volts,strict=True));v[stop]=0.;effective=float(v[start]);assert effective>0
    parts=[]
    for name,a,b,r in selected:
        current=float((v[a]-v[b])/r);contribution=r*current*current
        parts.append(dict(resistor=name,from_node=a,to_node=b,resistance_ohm=r,unit_injection_current_a=current,effective_R_contribution_ohm=contribution,sensitivity_dReff_dR=current*current))
    energy=sum(e['effective_R_contribution_ohm']for e in parts)
    assert abs(energy-effective)<=1e-7*max(1.,effective),('Unit-current energy identity',energy,effective)
    return dict(from_node=start,to_node=stop,effective_wire_R_ohm=effective,energy_sum_ohm=energy,kcl_residual_a=residual,nodes=len(seen),resistors=len(selected),dominant_edges=sorted(parts,key=lambda e:e['effective_R_contribution_ohm'],reverse=True)[:12])

def solver_source_guard(path):
    def body(text):
        nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=='solve']
        require(len(nodes)==1,'one immutable solver')
        n=nodes[0];return ''.join(text.splitlines(keepends=True)[n.lineno-1:n.end_lineno]).rstrip().encode()
    actual=body(Path(__file__).read_text());original=body(Path(path).read_text())
    require(actual==original and hashlib.sha256(actual).hexdigest()==SOLVER_FUNCTION_SHA,'original sparse solver bytes')
    return dict(sha256=SOLVER_FUNCTION_SHA,original_body_unchanged=True)

def rc_rows(text):
    rows=parser.statements(text)
    require(rows and rows[0][0].lower()=='.subckt'and rows[-1][0].lower()=='.ends','one subcircuit')
    require(not any(r[0].startswith('.')for r in rows[1:-1]),'no nested/directive records')
    require(len({r[0].lower()for r in rows[1:-1]})==len(rows)-2,'unique element names')
    original_lines={}
    for i,line in enumerate(text.splitlines(),1):
        if line.strip()and not line.lstrip().startswith(('*','+','.')):
            token=shlex.split(line)[0]
            original_lines.setdefault(token.lower(),[]).append(dict(line=i,text=line))
    out=[];excluded=[]
    for row in rows[1:-1]:
        kind=row[0][0].upper()
        if kind in ('R','C'):
            require(len(row)==4 and row[1].lower()!=row[2].lower(),'two distinct wire endpoints')
            value=parser.number(row[3]);f=float(value)
            require(math.isfinite(f)and(f>0 if kind=='R'else f>=0),'finite physical wire value')
            out.append(dict(id=row[0],kind=kind,nodes=row[1:3],value_si=f,value_token=row[3],canonical_value=str(value),source_statement=row,raw_source_lines=original_lines.get(row[0].lower(),[])))
        else:
            require(kind=='X','only intrinsic devices excluded')
            excluded.append(row)
    return out,excluded

def bind_wire_projection(model,wire,contract):
    composed,devices=rc_rows(model);raw,mims=rc_rows(wire);mapping=contract['wire_node_map']
    require(len(mapping)==len({v.lower()for v in mapping.values()}),'injective wire map')
    require(len(devices)==contract['counts']['devices'],'all composed intrinsic devices retained')
    expected=contract.get('native_extracted_mim_cards_projected_once',[])
    require(Counter(map(tuple,mims))==Counter(tuple(d['export'])for d in expected),'exact MIM cards separately projected')
    require(Counter(r['kind']for r in composed)=={k:contract['counts'][k]for k in ('R','C')},'global composed RC counts')
    require(len(raw)==len(composed),'global native/composed conservation')
    by={x['id'].lower():x for x in composed};result=[]
    for edge in raw:
        require(edge['id'].lower()in by,'native resistor/capacitor ID')
        c=by[edge['id'].lower()]
        require(all(n in mapping for n in edge['nodes']),'native wire endpoints mapped')
        nodes=[mapping[n]for n in edge['nodes']]
        require(nodes==c['nodes']and parser.number(edge['value_token'])==parser.number(c['value_token'])and edge['kind']==c['kind'],'exact wire edge projection')
        result.append(dict(edge,composed_nodes=nodes,composed_statement=c['source_statement'],composed_raw_source_lines=c['raw_source_lines']))
    require({n for e in raw for n in e['nodes']}==set(mapping),'whole raw node map')
    return result,dict(composed_intrinsic_devices=len(devices),native_extractor_mim_cards=len(mims),excluded_native_cards=mims,excluded_composed_device_names=[x[0]for x in devices],counts=dict(Counter(x['kind']for x in result)))

def connected_components(edges):
    adjacency=defaultdict(set)
    for e in edges:
        if e['kind']=='R':
            a,b=e['nodes'];adjacency[a].add(b);adjacency[b].add(a)
    groups=[];owner={}
    for start in sorted(adjacency):
        if start in owner:continue
        todo=[start];found={start}
        while todo:
            n=todo.pop()
            for m in adjacency[n]-found:found.add(m);todo.append(m)
        ident=len(groups);groups.append(found)
        for n in found:owner[n]=ident
    return groups,owner

def networks(edges,contract,anchors,geometry,targets):
    groups,owner=connected_components(edges);mapping=contract['wire_node_map']
    physical={a['label']:a for a in anchors['anchors']}
    require(len(physical)==len(anchors['anchors']),'unique physical anchors')
    devs={d['native_id']:d for d in contract['device_records']}
    geometry_groups={r['component']:r for r in geometry['wire_components']}
    selected={};selected_nodes={};assigned={}
    for target in targets:
        comp=target['component'];native=target['native_cluster'];terms=[]
        require(geometry_groups[comp]['native_cluster']==native,'actual geometry component/native identity')
        for expected in target['terminals']:
            d=devs[expected['id']];ts=[t for t in d['terminals']if t['terminal']==expected['terminal']]
            require(len(ts)==1,'unique target terminal');t=ts[0]
            require(d['model']==expected['model']and all(t[k]==expected[k]for k in ('node','anchor','native_net'))and t['native_cluster']==native,'current terminal identity')
            label=t['anchor'];require(label in physical,'target physical anchor present')
            a=physical[label];require(a['wire_component']==comp and a['native_cluster']==native,'physical anchor net identity')
            require(mapping[label]==t['node']and label in owner,'target finite wire terminal')
            terms.append(dict(device=d['native_id'],instance=d['instance'],model=d['model'],parameters=d['parameters'],**t,physical_anchor=a))
        ids={owner[t['anchor']]for t in terms};require(len(ids)==1,'disconnected target terminal')
        group=ids.pop();require(group not in selected,'distinct physical nets shorted')
        nodes=groups[group]
        actual={(d['native_id'],t['terminal'])for d in contract['device_records']for t in d['terminals']if t['anchor']in nodes}
        wanted={(t['id'],t['terminal'])for t in target['terminals']}
        require(actual==wanted,'complete target terminals / foreign boundary contact')
        # Prefixes are only a missing-fragment screen; true membership above uses R connectivity.
        hints={n for n in mapping if n.split('.')[0]in physical and physical[n.split('.')[0]]['wire_component']==comp}
        require(hints<=nodes,'disconnected named fragment of target network')
        require({physical[n]['wire_component']for n in nodes if n in physical}=={comp},'foreign physical anchor in R component')
        selected[group]=dict(component=comp,native_cluster=native,partition=target['partition'],terminals=terms,nodes=sorted(nodes),R=[],C=[])
        for n in nodes:require(n not in assigned,'overlapping networks');assigned[n]=comp
        selected_nodes[comp]=nodes
    global_classes=Counter();touching=[]
    for edge in edges:
        a,b=edge['nodes'];ca=assigned.get(a);cb=assigned.get(b)
        if edge['kind']=='R':
            require((ca is None)==(cb is None),'R boundary conservation')
            if ca is not None:require(ca==cb,'target nets shorted')
            category='target_R'if ca is not None else'other_R'
        else:
            category='target_intranetwork_C'if ca is not None and ca==cb else'target_to_target_C'if ca is not None and cb is not None else'target_boundary_C'if ca is not None or cb is not None else'other_C'
        global_classes[category]+=1
        if ca is not None or cb is not None:
            item=dict(edge,classification=category,endpoint_target_components=[ca,cb],endpoint_R_component_ids=[owner.get(a),owner.get(b)])
            touching.append(item)
            for group,net in selected.items():
                if net['component']in (ca,cb):net[edge['kind']].append(edge['id'])
    require(sum(v for k,v in global_classes.items()if k.endswith('_R'))==contract['counts']['R'],'all R conserved')
    require(sum(v for k,v in global_classes.items()if k.endswith('_C'))==contract['counts']['C'],'all C conserved')
    require(len({e['id'].lower()for e in touching})==len(touching),'incident C included globally once')
    return dict(networks=sorted(selected.values(),key=lambda x:x['component']),edges=touching,global_classification=dict(global_classes),global_R_components=len(groups),all_incident_edges_retained=True,cross_boundary_C_included_once=True,unselected_R_components_not_omitted_from_global_census=True)

def native_locations(texts,nodes):
    result={n:dict(raw_node=n,coordinates=[],records=[])for n in sorted(nodes)};headers={};unknown=[]
    base_scale=None
    for filename,text in texts:
        parsed=[];scales=[]
        for i,line in enumerate(text.splitlines(),1):
            if not line.strip()or line.lstrip().startswith('#'):continue
            tokens=shlex.split(line);parsed.append((i,line,tokens))
            if tokens[0]=='scale':
                require(len(tokens)==4,'native scale fields');scales.append(tokens[1:])
        require(len(scales)<=1,'unique native scale')
        if not filename.endswith('.res.ext'):base_scale=scales[0]if scales else['1','1','1']
        scale=scales[0]if scales else base_scale
        headers[filename]=dict(scale_tokens=scale,scale_origin='file'if scales else'parent_ext'if filename.endswith('.res.ext')else'format_default',header=text.splitlines()[:12])
        for i,line,t in parsed:
            matched=set(t)&set(result)
            for name in matched:result[name]['records'].append(dict(file=filename,line=i,text=line,tokens=t))
            if t[0]in ('node','rnode')and len(t)>=7 and t[1]in result:
                x,y=int(t[4]),int(t[5]);kind=t[0]
                layer=None if kind=='rnode'and t[6]=='0'else t[6]
                result[t[1]]['coordinates'].append(dict(file=filename,line=i,kind=kind,raw_xy=[x,y],scale_tokens=scale,type_token=t[6],layer=layer,layer_is_unknown=layer is None,coordinate_semantics='point within native node, not an edge route or Manhattan length',coordinate_transform_to_layout_not_asserted=True))
    for n,record in result.items():
        record['has_exact_node_coordinate_record']=bool(record['coordinates'])
        if not record['coordinates']:unknown.append(n)
    return dict(nodes=result,headers=headers,unresolved_coordinate_nodes=unknown,all_requested_nodes_retained=True,no_guessed_layers=True,format_references=['https://github.com/RTimothyEdwards/magic/blob/master/doc/man/ext.5','https://github.com/RTimothyEdwards/magic/blob/master/resis/ResPrint.c'])

def shortest_path(edges,start,stop):
    graph=defaultdict(list)
    for ident,a,b,r in edges:graph[a].append((b,r,ident));graph[b].append((a,r,ident))
    distances={start:0.};previous={};heap=[(0.,start)]
    while heap:
        value,n=heapq.heappop(heap)
        if value!=distances[n]:continue
        if n==stop:break
        for m,r,ident in graph[n]:
            candidate=value+r
            if candidate<distances.get(m,float('inf')):distances[m]=candidate;previous[m]=(n,ident);heapq.heappush(heap,(candidate,m))
    require(stop in distances,'disconnected path')
    path=[];n=stop
    while n!=start:n,ident=previous[n];path.append(ident)
    return dict(edges=list(reversed(path)),series_path_resistance_ohm=distances[stop],physical_route_length_not_inferred=True)

def evaluate(census):
    load_numeric_dependencies()
    by={e['id']:e for e in census['edges']};evaluations=[]
    for net in census['networks']:
        edges=[(name,*by[name]['nodes'],by[name]['value_si'])for name in net['R']]
        for a,b in combinations(sorted(t['anchor']for t in net['terminals']),2):
            result=solve(edges,a,b);reverse=solve(edges,b,a)
            require(math.isclose(result['effective_wire_R_ohm'],reverse['effective_wire_R_ohm'],rel_tol=1e-8,abs_tol=1e-10),'reciprocity')
            path=shortest_path(edges,a,b)
            require(result['effective_wire_R_ohm']<=path['series_path_resistance_ohm']+1e-7,'effective R bounded by actual path')
            evaluations.append(dict(component=net['component'],native_cluster=net['native_cluster'],solution=result,reverse_effective_R_ohm=reverse['effective_wire_R_ohm'],actual_graph_path=path))
    return dict(evaluations=evaluations,scope='Unchanged wire R network, one ampere mathematical injection and all other terminals floating. Not actual device current, multi-terminal operating point, EM, RF or timing. Capacitors and nonlinear intrinsic devices are excluded from this DC metric.',accepted=False,causality_proven=False)
