#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound physical hierarchy for the complete retimed CDR phase detector.

This is the real native PD/V-I hierarchy, not the recovered-clock loop.
"""
import copy, hashlib, json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'cdr_select_hybrid_tail_v2.spice':'4ea83a8d48cf38626234bb8530d9cca51eaa88c529369a37486a243e4614e4ba',
 'cdr_xor_core_hybrid_tail_v2.spice':'47dbcf055d732456f9b5c199e8deedd0a2fc402546c5c464ab315862bd70b660',
 'cdr_xor_hybrid_tail_v2.spice':'39d055605d72b6aa586b058c5492e17ae5bffe2dffc0942c07258dcb7137cddc',
 'cdr_retimed_parallel_pd_vi_v3.spice':'11c7f3e5b0c9a55f9c3adde71873b2d9947a4ec4cbfbfb65a6d53e53baf860ec',
 'rx_sampler_parallel_drive_v8.spice':'876bd1d55af65726ebfcb979d56036b83faccc691e3427f0fb09333d8100acc3',
 'cdr_sampled_compare_buffered_v4.spice':'8b9ade6650c8d5153f3d872660b04d8cac1970220a6fc5fc233ec05489bb2d7c',
 'cdr_vi_hbt_v1.spice':'9f13b4eeca782f34feb3a858937de871f61b2e7ab5a06ffc43ecfdfb5f5268ef'}
TYPES={
 'sampler':dict(top='nssoc_rx_sampler_local_order_layout_v9',devices=54,layer=67),
 'data':dict(top='nssoc_cdr_data_buffer_layout_v4',devices=14,layer=67),
 'select':dict(top='nssoc_cdr_select_hybrid_tail_layout_v2',devices=18,layer=67),
 'xor':dict(top='nssoc_cdr_xor_power_access_layout_v4',devices=59,layer=67),
 'vi':dict(top='nssoc_cdr_vi13_layout_v1',devices=26,layer=67),
 **{k:dict(top='nssoc_cdr_'+k[3:]+'_feedforward_layout_v1',devices=12,layer=67)for k in ('rc_retime','rc_data','rc_select')}}
def cells(text):
    result={};current=None
    for line in text.splitlines():
        f=line.lower().split()
        if not f or f[0].startswith('*'):continue
        if f[0]=='.subckt':
            assert current is None and f[1]not in result
            current=f[1];result[current]=dict(ports=f[2:],rows=[])
        elif f[0]=='.ends':assert current==f[1];current=None
        else:assert current is not None;result[current]['rows'].append(f)
    assert current is None
    return result

def build():
    definitions={}
    for name,sha in SOURCES.items():
        raw=(ROOT/'hw/soc/analog/pcie'/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==sha
        for key,value in cells(raw.decode()).items():
            assert key not in definitions;definitions[key]=value
    pd=definitions['nssoc_cdr_retimed_parallel_pd_vi_v3']
    cards={r[0]:r for r in pd['rows']};assert len(cards)==len(pd['rows'])==41
    nodes=[];consumed=[]
    def direct(instance,kind,model,aliases=None,formal=None):
        f=cards[instance];ports=definitions[model]['ports']if formal is None else formal
        assert f[-1]==model and len(f)==len(ports)+2
        mapping=dict(zip(ports,f[1:-1],strict=True));aliases=aliases or {}
        pins={aliases.get(k,k):v for k,v in mapping.items()if k!='wire_cref'}
        if 'wire_cref'in mapping:assert mapping['wire_cref']=='wire_cref'
        nodes.append(dict(tag=instance[1:],kind=kind,pins=pins,source_cards=[instance]));consumed.append(instance)
    aliases=dict(clkp='CLKP',clkn='CLKN',**{p:p.upper()for p in ('dp','dn','qp','qn','avdd','avss','sub','iref')})
    for instance in ('xsa','xsb','xsc','xsd'):direct(instance,'sampler','nssoc_rx_sampler_parallel_drive_v8',aliases)
    for instance in ('xda','xdc'):direct(instance,'data','nssoc_cdr_data_buffer_v4')
    for instance in ('xs0','xs1'):direct(instance,'select','nssoc_cdr_select_hybrid_tail_v2')
    for instance in ('xx','xy'):direct(instance,'xor','nssoc_cdr_xor_hybrid_tail_v2')
    direct('xvi','vi','nssoc_cdr_vi_hbt_v1')
    filters=[
      ('ac','rc_retime','aqp','aqn','cup','cun',['xracsp','xracgp','xcacp','xracsn','xracgn','xcacn']),
      ('bd','rc_retime','bqp','bqn','dup','dun',['xrbdsp','xrbdgp','xcbdp','xrbdsn','xrbdgn','xcbdn']),
      ('dfa','rc_data','aqp','aqn','uap','uan',['xrdasp','xrdagp','xcdap','xrdasn','xrdagn','xcdan']),
      ('dfc','rc_data','cqp','cqn','ucp','ucn',['xrdcsp','xrdcgp','xcdcp','xrdcsn','xrdcgn','xcdcn']),
      ('se','rc_select','dqp','dqn','usp','usn',['xrsesp','xrsegp','xcsep','xrsesn','xrsegn','xcsen'])]
    for tag,kind,ip,inn,op,on,names in filters:
        lengths,cap={'rc_retime':(('5.4u','12.6u'),'3.6u'),'rc_data':(('3.6u','21.6u'),'3.6u'),'rc_select':(('6u','8.6u'),'4.8u')}[kind]
        for half,(a,b)in enumerate(((ip,op),(inn,on))):
            r,g,c=[cards[n]for n in names[half*3:half*3+3]]
            assert r[1:5]==[a,b,'sub','rppd']and g[1:5]==[b,'avss','sub','rppd']and c[1:4]==[a,b,'cap_cmim']
            assert dict(x.split('=')for x in r[5:])==dict(w='1u',l=lengths[0],b='0',sw_et='1')
            assert dict(x.split('=')for x in g[5:])==dict(w='1u',l=lengths[1],b='0',sw_et='1')
            assert dict(x.split('=')for x in c[4:])==dict(w=cap,l=cap)
        nodes.append(dict(tag=tag,kind=kind,pins=dict(ip=ip,inn=inn,op=op,on=on,avss='avss',sub='sub'),source_cards=names));consumed+=names
    assert len(consumed)==len(set(consumed))==41 and set(consumed)==set(cards)
    assert len(nodes)==16 and len({n['tag']for n in nodes})==16
    assert Counter(n['kind']for n in nodes)==dict(sampler=4,data=2,select=2,xor=2,vi=1,rc_retime=2,rc_data=2,rc_select=1)
    ports=[p for p in pd['ports']if p!='wire_cref'];assert len(ports)==25
    nets=sorted({v for n in nodes for v in n['pins'].values()});assert set(ports)<=set(nets)and 'wire_cref'not in nets
    assert sum(TYPES[n['kind']]['devices']for n in nodes)==484
    return dict(nodes=nodes,ports=ports,nets=nets,types=TYPES,source_sha256=SOURCES,expected_devices=484,
                primitive_census=dict(npn13g2=116,sg13_lv_nmos=46,rppd=102,cap_cmim=11,ptap1=209),source_cards_consumed=41,
                full_phy_accepted=False,closed_loop=False,qualified_pex=False)

def verify(plan):
    assert plan==build(), 'Physical hierarchy differs from frozen native PD sources'
    return True

def controls():
    plan=build();verify(plan);faults=[]
    for case in ('missing_sampler','wrong_clock_polarity','wrong_vi_polarity','missing_rc','wrong_bias','synthetic_cref'):
        bad=copy.deepcopy(plan)
        if case=='missing_sampler':bad['nodes']=[n for n in bad['nodes']if n['tag']!='sa']
        elif case=='missing_rc':bad['nodes']=[n for n in bad['nodes']if n['tag']!='ac']
        elif case=='wrong_clock_polarity':next(n for n in bad['nodes']if n['tag']=='sb')['pins']['CLKP']='cp'
        elif case=='wrong_vi_polarity':next(n for n in bad['nodes']if n['tag']=='vi')['pins']['xp']='xn'
        elif case=='wrong_bias':next(n for n in bad['nodes']if n['tag']=='s0')['pins']['iref']='ibs1'
        else:bad['ports'].append('wire_cref')
        try:verify(bad)
        except AssertionError:faults.append(case)
        else:raise AssertionError('Accepted altered physical hierarchy')
    assert len(faults)==6
    return dict(status='PASS_EXACT_41_SOURCE_CARDS_16_PHYSICAL_MACROS_AND_SIX_BINDING_FAULTS',plan=plan,rejected=faults,layout_generated=False)
if __name__=='__main__': print(json.dumps(controls(),indent=2))
