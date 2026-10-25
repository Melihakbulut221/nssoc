#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Classify every pinned physical route, including both terminals of each MIM.

Source metadata and terminal ownership only; no geometric or electrical acceptance.
Scalar route records do not carry terminal names. AVSS assignment therefore requires
one unique actual source terminal on that device/net; no nearest-point inference.
"""
import copy,json
from collections import Counter,defaultdict
from tx_phase_reset334_loaded_binding import KIND,ORDER

SCALAR=frozenset(('actual_pin_um','device','escape_lane_um','escape_y_um','net','source_layer'))
MIM=frozenset(('device','minus_escape_um','minus_native_plate_um','minus_net',
    'plus_contact_outside_native_mim','plus_escape_um','plus_native_plate_um','plus_net'))
MODEL={kind:model for model,kind in KIND.items()}

class RouteMismatch(AssertionError):pass

def require(ok,code,**context):
    if not ok:raise RouteMismatch(json.dumps(dict(code=code,**context),sort_keys=True,allow_nan=False))

def inventory(g,terminals):
    instances=g['instances'];routes=g['routes']
    placed={x['name']:x for x in instances}
    require(len(placed)==len(instances)==334,'instance_census')
    require(Counter(x['kind'] for x in instances)==Counter(hbt=106,resistor=130,capacitor=8,substrate_tap=90),'instance_kinds')
    require(len(routes)==586,'route_census',observed=len(routes),expected=586)
    by_device=defaultdict(list);counts=Counter();selected=[]
    serialized=[json.dumps(x,sort_keys=True,allow_nan=False) for x in routes]
    require(len(set(serialized))==len(routes),'duplicate_route_record')
    for index,row in enumerate(routes):
        fields=frozenset(row)
        require(fields in (SCALAR,MIM),'unknown_route_schema',index=index,record=row)
        device=row['device']
        require(device in placed,'unknown_route_device',index=index,record=row)
        instance=placed[device];kind=instance['kind']
        require(kind in MODEL,'unsupported_routed_kind',index=index,record=row,kind=kind)
        model=MODEL[kind];order=ORDER[model];nets=instance['nets']
        require(len(order)==len(nets),'source_terminal_count',device=device,model=model,nets=nets)
        by_device[device].append(row)
        if fields==SCALAR:
            counts['scalar']+=1
            require(kind in ('hbt','resistor'),'scalar_kind',index=index,record=row,kind=kind)
            routed_order=order[:-1];routed_nets=nets[:-1]
            require(row['net'] in routed_nets,'scalar_source_net',index=index,record=row,source_nets=routed_nets)
            if row['net']=='AVSS':
                terms=[term for term,net in zip(routed_order,routed_nets,strict=True) if net=='AVSS']
                require(len(terms)==1,'ambiguous_AVSS_scalar_terminal',index=index,record=row,terms=terms)
                selected.append(dict(schema='scalar',source_instance=device,model=model,
                    terminal=terms[0],source_net='AVSS',route=copy.deepcopy(row)))
        else:
            counts['MIM']+=1
            require(kind=='capacitor','MIM_kind',index=index,record=row,kind=kind)
            require([row['plus_net'],row['minus_net']]==nets,'MIM_source_nets',index=index,record=row,source_nets=nets)
            require(row['plus_contact_outside_native_mim'] is True,'MIM_outside_contact',index=index,record=row)
            for side,term,net in zip(('plus','minus'),order,nets,strict=True):
                if net=='AVSS':
                    selected.append(dict(schema='MIM',selected_side=side,source_instance=device,model=model,
                        terminal=term,source_net='AVSS',route=copy.deepcopy(row)))
    require(counts==Counter(scalar=578,MIM=8),'route_schema_census',observed=dict(counts))
    compact={name:x for name,x in placed.items() if x['kind']!='substrate_tap'}
    require(set(by_device)==set(compact),'all_compact_devices_routed')
    for name,instance in compact.items():
        rows=by_device[name]
        if instance['kind']=='capacitor':
            require(len(rows)==1 and frozenset(rows[0])==MIM,'one_MIM_pair_per_device',device=name,records=rows)
        else:
            require(all(frozenset(x)==SCALAR for x in rows),'scalar_device_schemas',device=name,records=rows)
            require(Counter(x['net'] for x in rows)==Counter(instance['nets'][:-1]),'all_scalar_terminals_routed',device=name,records=rows,source_nets=instance['nets'][:-1])
    key=lambda x:(x['source_instance'],x['model'],x['terminal'],x['source_net'])
    expected=Counter(key(x) for x in selected);actual=Counter(key(x) for x in terminals)
    require(len(selected)==len(expected)==len(terminals)==len(actual)==85,'AVSS_terminal_census',routes=len(selected),terminals=len(terminals))
    require(expected==actual,'AVSS_terminal_owner_join',missing=list((expected-actual).elements()),extra=list((actual-expected).elements()))
    require(Counter(x['model'] for x in selected)==Counter(npn13G2=28,rppd=55,cap_cmim=2),'AVSS_model_census')
    mim=[x for x in selected if x['schema']=='MIM']
    require({(x['source_instance'],x['terminal'],x['selected_side']) for x in mim}==
        {('PHASE__XSEEDP','mim_btm','minus'),('PHASE__XSEEDN','mim_btm','minus')},'exact_AVSS_MIM_owners',records=mim)
    return dict(status='EXACT_PHYSICAL_ROUTE_SCHEMA_AND_SOURCE_TERMINAL_JOIN_ONLY',
        total_routes=586,scalar_routes=578,MIM_pair_routes=8,compact_devices=244,
        AVSS_scalar_routes=83,AVSS_MIM_terminal_routes=2,AVSS_terminal_routes=85,
        AVSS_routes=selected,all586_records_classified=True,all85_terminal_owners_matched=True,
        route_coordinates_preserved_in_original_generator_frame=True,
        RC_access_point_equivalence_inferred=False,new_geometry_or_simulation=False)

def controls(physical,terminals_by_sign,restored_terminal_owners=False):
    """Actual pinned physical metadata; source or restored terminal projections labelled."""
    positives={};rejected=[]
    for sign in ('p','n'):
        gen=physical['variants'][sign]['generation'];terms=terminals_by_sign[sign]
        positive=inventory(gen,terms)
        positives[sign]={k:v for k,v in positive.items() if k!='AVSS_routes'}
        scalar=next(i for i,x in enumerate(gen['routes']) if frozenset(x)==SCALAR and x['net']=='AVSS')
        mim=next(i for i,x in enumerate(gen['routes']) if frozenset(x)==MIM and x['device']=='PHASE__XSEEDP')
        tap=next(x['name'] for x in gen['instances'] if x['kind']=='substrate_tap')
        ts=next(i for i,x in enumerate(terms) if x['model']!='cap_cmim')
        tm=next(i for i,x in enumerate(terms) if x['source_instance']=='PHASE__XSEEDP')
        trials=[
            ('unknown_scalar_field',lambda q,t:q['routes'][scalar].update(unexpected=True)),
            ('missing_scalar_net',lambda q,t:q['routes'][scalar].pop('net')),
            ('wrong_scalar_net',lambda q,t:q['routes'][scalar].update(net='NOT_A_SOURCE_NET')),
            ('scalar_uses_MIM_device',lambda q,t:q['routes'][scalar].update(device='PHASE__XSEEDP')),
            ('missing_scalar_route',lambda q,t:q['routes'].pop(scalar)),
            ('duplicate_scalar_route',lambda q,t:q['routes'].append(copy.deepcopy(q['routes'][scalar]))),
            ('missing_MIM_pair',lambda q,t:q['routes'].pop(mim)),
            ('duplicate_MIM_pair',lambda q,t:q['routes'].append(copy.deepcopy(q['routes'][mim]))),
            ('swapped_MIM_nets',lambda q,t:q['routes'][mim].update(plus_net='AVSS',minus_net='MP')),
            ('wrong_MIM_minus_net',lambda q,t:q['routes'][mim].update(minus_net='SUB')),
            ('missing_MIM_plate',lambda q,t:q['routes'][mim].pop('minus_native_plate_um')),
            ('MIM_contact_flag',lambda q,t:q['routes'][mim].update(plus_contact_outside_native_mim=False)),
            ('unsupported_tap_route',lambda q,t:q['routes'][scalar].update(device=tap)),
            ('duplicate_route_replaces_another',lambda q,t:q['routes'].__setitem__((scalar+1)%len(q['routes']),copy.deepcopy(q['routes'][scalar]))),
            ('missing_scalar_terminal',lambda q,t:t.pop(ts)),
            ('missing_MIM_terminal',lambda q,t:t.pop(tm)),
            ('duplicate_terminal',lambda q,t:t.append(copy.deepcopy(t[ts]))),
            ('wrong_terminal_owner',lambda q,t:t[ts].update(source_instance='PHASE__NOT_REAL')),
            ('wrong_MIM_terminal',lambda q,t:t[tm].update(terminal='mim_top')),
            ('AVSS_as_SUB_terminal',lambda q,t:t[tm].update(source_net='SUB'))]
        assert len(trials)==20
        for label,mutate in trials:
            q=copy.deepcopy(gen);t=copy.deepcopy(terms);mutate(q,t)
            assert q!=gen or t!=terms
            try:inventory(q,t)
            except RouteMismatch as error:
                witness=json.loads(str(error));assert witness['code']
                rejected.append(dict(case=sign+':'+label,refusal=witness))
            else:raise AssertionError('Accepted route schema/owner fault '+sign+':'+label)
    assert len(rejected)==40
    return dict(status='PASS_PINNED_PHYSICAL_ROUTE_SCHEMA_CONTROLS_ONLY',positives=positives,rejected=rejected,
        restored_terminal_owners_exercised=restored_terminal_owners,
        source_terminal_fixture=not restored_terminal_owners,new_geometry_or_simulation=False)
