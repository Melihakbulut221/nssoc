#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind the passed334 physical model to exact schematic roles, without ideal net aliases."""
import copy,hashlib,json,re
from collections import Counter,defaultdict
from decimal import Decimal
import tx_phase_assert_offset_diagnostic as original
from build_tx_phase_async_preset_source import definitions,NAMES
from check_tx_phase_async_preset_source import PRIMITIVES
from pll_divider_load3p2_native import ORDER
SOURCE_SHA='3b4aa82387b5e532437dc592feceea699b4d283570751d6e983f0949fe7095f4'
MODELS={'p':'31c3eb5873f2d9d326d3c88fb535e73089fccf58edb9f52a7ebeea598c9774ae',
        'n':'72db7ac98099bfd470735d1b59bb171408973da3a01be175db46d2eb6ccb5611'}
PORTS=['CLKP','CLKN','MP','MN','QP','QN','ARM_P','ARM_N','DIV_AVDD','AVSS','SUB','wire_cref']
CENSUS=dict(npn13G2=106,rppd=130,cap_cmim=8,ptap1=90)
KIND={'npn13G2':'hbt','rppd':'resistor','cap_cmim':'capacitor'}
PROBES={
 'release':(('PHASE__XRELEASE__XS__XDN','C','PHASE__RELEASEDP'),('PHASE__XRELEASE__XS__XDP','C','PHASE__RELEASEDN')),
 'native_clock':(('PHASE__XCLK__XSP','rppd_2','PHASE__CKP'),('PHASE__XCLK__XSN','rppd_2','PHASE__CKN')),
 'arm_conditioned':(('PHASE__XRELEASE__XARM__XSP','rppd_2','PHASE__XRELEASE__ARMCP'),('PHASE__XRELEASE__XARM__XSN','rppd_2','PHASE__XRELEASE__ARMCN')),
 'run':(('PHASE__XRUN__XSP','rppd_2','PHASE__RUNP'),('PHASE__XRUN__XSN','rppd_2','PHASE__RUNN'))}
FLAGS=dict(physical_binding_qualified=False,postlayout_electrical_accepted=False,real_selector_load_accepted=False,
           reset_distribution_qualified=False,all31_clock_tree_accepted=False,PLL_connected=False,full_PHY_accepted=False)
def digest(b):return hashlib.sha256(b.encode()if isinstance(b,str)else b).hexdigest()
def scalar(word):
    m=re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([munpk]?)',word)
    assert m,word
    return Decimal(m[1])*{'':Decimal(1),'m':Decimal('1e-3'),'u':Decimal('1e-6'),'n':Decimal('1e-9'),'p':Decimal('1e-12'),'k':Decimal('1e3')}[m[2]]
def source_rows(text,sign):
    assert sign in ('p','n')and digest(text)==SOURCE_SHA
    original.source_check.validate(text)
    defs=definitions(text);records=[]
    def walk(name,nodes,path,stack=()):
        assert name not in stack
        sub=defs[name];assert len(nodes)==len(sub['ports'])
        ports=dict(zip((x.lower()for x in sub['ports']),nodes,strict=True))
        def net(n):return ports.get(n.lower(),path+'__'+n.upper())
        for card in sub['cards']:
            matches=[(model,n)for model,n in PRIMITIVES.items()if len(card)>n+1 and card[n+1]==model]
            if matches:
                assert len(matches)==1
                model,n=matches[0];params=dict(v.split('=',1)for v in card[n+2:])
                assert len(params)==len(card)-n-2
                records.append(dict(name=path+'__'+card[0].upper(),model=model,nets=[net(x)for x in card[1:n+1]],parameters=params))
            else:walk(card[-1],[net(x)for x in card[1:-1]],path+'__'+card[0].upper(),(*stack,name))
    walk(NAMES['parent'+sign],PORTS[:-1],'PHASE')
    assert len(records)==len({r['name']for r in records})==244
    assert Counter(r['model']for r in records)==Counter(npn13G2=106,rppd=130,cap_cmim=8)
    return records
def box(row,shift):
    m=re.fullmatch(r'\(([-\d.]+),([-\d.]+);([-\d.]+),([-\d.]+)\)',row['bbox_um']);assert m
    x0,y0,x1,y1=map(Decimal,m.groups());dx,dy=map(lambda v:Decimal(str(v)),shift)
    assert x0<x1 and y0<y1
    return [(x0+dx)*1000,(y0+dy)*1000,(x1+dx)*1000,(y1+dy)*1000]
def contains(rect,points):
    return bool(points)and all(rect[0]<=x<=rect[2]and rect[1]<=y<=rect[3]for x,y in points)
def bind(text,sign,geometry,planes,native,composition,model_text):
    canonical=source_rows(text,sign)
    assert geometry['preset_polarity']==sign and geometry['candidate_source_sha256']==SOURCE_SHA
    assert geometry['primitive_counts']==dict(hbt=106,rppd=130,cmim=8,physical_ptap=90)
    assert geometry['exactly243_other_compact_devices_unchanged']
    assert digest(model_text)==MODELS[sign]==composition['model_sha256']
    actual={r['name']:r for r in geometry['instances']}
    assert len(actual)==len(geometry['instances'])==334
    compact={k:v for k,v in actual.items()if v['kind']!='substrate_tap'}
    assert set(compact)=={r['name']for r in canonical}and len(compact)==244
    native_rows=native['modes']['lvs_flat']['devices']
    nd={int(r['id']):r for r in native_rows}
    assert len(nd)==len(native_rows)==334 and Counter(r['model']for r in native_rows)==Counter(CENSUS)
    byterm={(r['device'],r['terminal']):r for r in planes['rows']}
    assert len(byterm)==len(planes['rows'])==1010
    cb={r['native_id']:r for r in composition['bindings']}
    assert len(cb)==len(composition['bindings'])==334 and set(cb)==set(nd)
    expected_positive=dict(devices=334,wire_resistors=1347,wire_capacitors=2545,terminals=1010,wire_components=119,body_nodes=1,ports=PORTS)
    assert composition['positive']==expected_positive
    statements=[l.split()for l in model_text.splitlines()if l.strip()and not l.lstrip().startswith('*')]
    assert statements[0]==['.subckt','nssoc_tx_phase_reset334_'+sign+'_native_wire_v1',*PORTS]
    cards={r[0]:r for r in statements if r[0].startswith('XD')}
    assert len(cards)==334 and set(cards)=={'XD'+str(i)for i in nd}
    roles={};used=set();source_clusters=defaultdict(set);all_native_hbt={}
    for src in canonical:
        placed=compact[src['name']];model=src['model'];order=ORDER[model]
        assert placed['kind']==KIND[model]and placed['nets']==src['nets']
        assert placed['source_instance'].upper()==src['name'].split('__')[-1]
        rectangle=box(placed,geometry['origin_translation_um'])
        candidates=[]
        for did,nrow in nd.items():
            if nrow['model']!=model:continue
            anchors=[byterm[(did,t)]for t in order]
            assert all(a['model']==model for a in anchors)
            points=[a['point_dbu']for a in anchors if 'point_dbu'in a]
            if contains(rectangle,points):candidates.append(did)
        assert len(candidates)==1,(src['name'],candidates)
        did=candidates[0];assert did not in used;used.add(did);nrow=nd[did]
        if model=='npn13G2':
            nx=scalar(src['parameters']['Nx'])
            assert nx==placed['nx']==nrow['parameters']['Nx']and nrow['parameters']['m']==1
        else:
            for key,field in [('w','width_um'),('l','length_um')]:
                assert scalar(src['parameters'][key])*1000000==Decimal(str(placed[field]))
                assert abs(Decimal(str(nrow['parameters'][key]))-Decimal(str(placed[field])))<=Decimal('1e-10')
        binding=cb[did];assert binding['instance']=='XD'+str(did)
        bt={r['terminal']:r for r in binding['bindings']}
        assert len(bt)==len(binding['bindings'])==len(order)and set(bt)==set(order)
        row=dict(source_instance=src['name'],native_id=did,model=model,parameters=nrow['parameters'],terminals={})
        for term,logical in zip(order,src['nets'],strict=True):
            a=byterm[(did,term)];n=nrow['terminals'][term];b=bt[term]
            cluster=str(a['native_cluster']);assert cluster==str(n['cluster'])==str(b['native_cluster'])
            source_clusters[logical].add(cluster)
            assert a.get('reference_label')==b['reference']
            if b['reference']is None:assert b['node']=='BULK'and term in ('S','rppd_sub')
            else:assert composition['wire_node_map'][b['reference']]==b['node']
            index=order.index(term)+1
            assert cards[binding['instance']][index]==b['node']
            row['terminals'][term]=dict(source_net=logical,native_cluster=cluster,reference_label=b['reference'],model_node=b['node'],native_point_dbu=a.get('point_dbu'))
        roles[src['name']]=row
        if model=='npn13G2':all_native_hbt[did]=row
    assert len(used)==244 and all(nd[i]['model']=='ptap1'for i in set(nd)-used)
    assert len(all_native_hbt)==106 and set(all_native_hbt)=={i for i,r in nd.items()if r['model']=='npn13G2'}
    assert all(len(v)==1 for v in source_clusters.values())
    # The schematic substrate becomes the common finite-contact BODY, not an ideal short to the public SUB port.
    netmap={k:next(iter(v))for k,v in source_clusters.items()}
    assert len(set(netmap.values()))==len(netmap)
    public={p['name']:str(p['cluster'])for p in native['modes']['lvs_flat']['probes']}
    assert set(public)==set(PORTS[:-1])
    assert netmap['SUB']!=public['SUB']
    for name in PORTS[:-1]:
        if name!='SUB':assert netmap[name]==public[name]
    probes={}
    for label,pair in PROBES.items():
        legs=[]
        for instance,term,logical in pair:
            r=roles[instance];t=r['terminals'][term];assert t['source_net']==logical
            legs.append(dict(source_instance=instance,native_id=r['native_id'],terminal=term,**t))
        assert legs[0]['native_cluster']!=legs[1]['native_cluster']and legs[0]['model_node']!=legs[1]['model_node']
        probes[label]=legs
    return dict(status='SOURCE_TO_NATIVE334_ROLE_BINDING_REQUIRES_HOSTED_POSITIVE_PROOF',preset=sign,
                compact_roles=roles,hbt_roles=all_native_hbt,source_native_net_map=netmap,public_native_net_map=public,
                fixed_internal_probes=probes,original_phase_oracle_unchanged=True,
                no_distributed_nodes_collapsed_or_aliased=True,**FLAGS)

def controls(case):
    """Mutate the actual authenticated positive inputs; caller preserves its exact source receipt."""
    positive=bind(**case);sign=case['sign']
    def native_first(d):return d['native']['modes']['lvs_flat']['devices'][0]
    def source_first(d):return next(r for r in d['geometry']['instances']if r['kind']=='hbt')
    faults=[
      ('wrong-preset',lambda d:d.update(sign='n'if sign=='p'else'p')),
      ('moved-physical-instance',lambda d:source_first(d).update(bbox_um='(90000,90000;90010,90010)')),
      ('wrong-origin-translation',lambda d:d['geometry'].update(origin_translation_um=[100000,100000])),
      ('wrong-source-terminal',lambda d:source_first(d)['nets'].__setitem__(0,'WRONG_NET')),
      ('wrong-source-Nx',lambda d:source_first(d).update(nx=99)),
      ('wrong-native-Nx',lambda d:native_first(d)['parameters'].update(Nx=99)),
      ('missing-native-body-contact',lambda d:d['native']['modes']['lvs_flat']['devices'].pop()),
      ('wrong-native-terminal-cluster',lambda d:native_first(d)['terminals']['C'].update(cluster='999999')),
      ('missing-native-terminal-anchor',lambda d:d['planes']['rows'].pop(0)),
      ('wrong-anchor-model',lambda d:d['planes']['rows'][0].update(model='rppd')),
      ('foreign-anchor-point',lambda d:d['planes']['rows'][0].update(point_dbu=[90000000,90000000])),
      ('wrong-anchor-reference',lambda d:d['planes']['rows'][0].update(reference_label='P_CLKP')),
      ('duplicate-composed-device',lambda d:d['composition']['bindings'].append(copy.deepcopy(d['composition']['bindings'][0]))),
      ('wrong-composed-native-cluster',lambda d:d['composition']['bindings'][0]['bindings'][0].update(native_cluster='999999')),
      ('wrong-composed-node',lambda d:d['composition']['bindings'][0]['bindings'][0].update(node='CLKN')),
      ('wrong-reference-node-map',lambda d:d['composition']['wire_node_map'].update(A0000='CLKN')),
      ('wrong-model-hash',lambda d:d['composition'].update(model_sha256='0'*64)),
      ('changed-model-byte',lambda d:d.update(model_text=d['model_text']+'\n* unexpected change\n')),
      ('wrong-RC-census',lambda d:d['composition']['positive'].update(wire_resistors=1346)),
      ('duplicate-public-role',lambda d:d['native']['modes']['lvs_flat']['probes'][0].update(name='NOT_A_PORT')),
    ]
    rejected=[]
    for name,edit in faults:
        modified=copy.deepcopy(case);edit(modified)
        try:bind(**modified)
        except(AssertionError,KeyError,ValueError):rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    assert len(rejected)==20
    return dict(positive=positive,negative_controls=rejected,controls_passed=True,**FLAGS)
