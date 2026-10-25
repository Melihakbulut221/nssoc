#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Same native rows and observed currents; no simulator or complete KCL claim."""
import json
from pathlib import Path
import numpy as np
import cdr_v58_saved_rows as old
ROOT=Path(__file__).resolve().parents[1]
CONTRACT='docs/evidence/cdr-v58-current-ledger-contract-20261025.json'
UI,START,STOP,STEP=old.UI,old.START,old.STOP,old.STEP
replay,cache=old.replay,old.cache
FAILED=(59,60,71,72,87,88,111,112)

def contract():
    return json.loads((ROOT/CONTRACT).read_text())

def name(record):
    return 'xpd.'+record['instance'].lower()

def voltage(node):
    assert node!='0'
    return 'v(xpd.'+node.lower()+')'

def current(record):
    if record['model']=='npn13g2':return '@q.'+name(record)+'.qnpn13g2[ic]'
    if record['model']=='sg13_lv_nmos':return '@n.'+name(record)+'.nsg13_lv_nmos[ids]'
    assert record['model']=='rppd'
    return None

def terms(record):
    return {p['terminal']:p for p in record['terminals']}

def terminal(record,key):
    return voltage(terms(record)[key]['node'])

def validate_contract(c,actual,bound):
    assert c['schema']=='nssoc-cdr-v58-observed-current-ledger-v1'
    assert c['original_run']==40108285374 and c['original_head']=='d92a3367a1013d1071125b753ec4f65ae4ec813b'
    assert c['original_capture_cases']==['nominal_early','nominal_late','hot_early']
    records=c['native_device_records'];by={d['native_id']:d for d in records}
    assert len(records)==len(by)==126
    assert c['model_census']==dict(sg13_lv_nmos=36,npn13g2=72,rppd=18)
    assert {k:sum(d['model']==k for d in records)for k in c['model_census']}==c['model_census']
    aa={d['native_id']:d for d in actual['device_records']}
    assert len(aa)==500
    for ident,d in by.items():
        assert aa[ident]==d,('Changed native ledger device',ident)
        b=bound['groups'][d['model']][name(d)]
        assert b['native_id']==ident and b['parameters']==d['parameters']
        assert b['nodes']==['xpd.'+t['node'].lower() for t in d['terminals']]
    def cluster(ident,t):return terms(by[ident])[t]['native_cluster']
    assert [(p['follower'],p['gain'],p['input_load'],p['pullup'],p['shunt'])for p in c['gain_paths']]==[
        (69,59,187,183,185),(70,60,188,182,184),(121,111,225,221,223),(124,112,226,220,222)]
    for p in c['gain_paths']:
        assert cluster(p['follower'],'E')==cluster(p['gain'],'B')==cluster(p['input_load'],'rppd_1')==p['input_cluster']
        assert cluster(p['gain'],'C')==cluster(p['pullup'],'rppd_2')==cluster(p['shunt'],'rppd_1')==p['collector_cluster']
        assert all(cluster(m,'D')==cluster(p['gain'],'E')for m in p['tail_mos'])
    assert [(p['holds'],p['bleed'],p['loads'])for p in c['hold_paths']]==[([71,72],198,[194,191]),([87,88],210,[205,202])]
    for p in c['hold_paths']:
        assert all(cluster(h,'E')==p['emitter_cluster'] for h in p['holds'])
        assert cluster(p['bleed'],'rppd_1')==p['emitter_cluster']
        for h,r in zip(p['holds'],p['loads'],strict=True):assert cluster(h,'C')==cluster(r,'rppd_2')
    assert c['gain_paths']==[{"sampler":"D","polarity":"p","follower":69,"gain":59,"input_load":187,"pullup":183,"shunt":185,"tail_mos":[1,2],"input_cluster":13,"collector_cluster":21},{"sampler":"D","polarity":"n","follower":70,"gain":60,"input_load":188,"pullup":182,"shunt":184,"tail_mos":[1,2],"input_cluster":15,"collector_cluster":22},{"sampler":"C","polarity":"p","follower":121,"gain":111,"input_load":225,"pullup":221,"shunt":223,"tail_mos":[30,31],"input_cluster":114,"collector_cluster":121},{"sampler":"C","polarity":"n","follower":124,"gain":112,"input_load":226,"pullup":220,"shunt":222,"tail_mos":[30,31],"input_cluster":116,"collector_cluster":122}]
    assert c['hold_paths']==[{"sampler":"B","holds":[71,72],"bleed":198,"loads":[194,191],"emitter_cluster":71},{"sampler":"A","holds":[87,88],"bleed":210,"loads":[205,202],"emitter_cluster":100}]
    assert c['clock_tails']==[{"sampler":"D","tail_cluster":28,"cn":[61,62],"cp":[64,65],"mos":[3,4,5,6]},{"sampler":"D","tail_cluster":31,"cn":[63,67],"cp":[66,68],"mos":[7,8,9,10]},{"sampler":"B","tail_cluster":60,"cp":[79,80],"cn":[83,84],"mos":[12,13,14,15]},{"sampler":"B","tail_cluster":63,"cp":[81,82],"cn":[85,86],"mos":[16,17,18,19]},{"sampler":"A","tail_cluster":89,"cn":[95,96],"cp":[99,100],"mos":[21,22,23,24]},{"sampler":"A","tail_cluster":92,"cn":[97,98],"cp":[101,102],"mos":[25,26,27,28]},{"sampler":"C","tail_cluster":127,"cn":[113,117],"cp":[114,120],"mos":[36,37,38,39]},{"sampler":"C","tail_cluster":124,"cn":[115,116],"cp":[118,119],"mos":[32,33,34,35]}]
    seen=set()
    for p in c['clock_tails']:
        assert len(p['cp'])==len(p['cn'])==2 and len(p['mos'])==4
        assert len(set(p['cp']+p['cn']+p['mos']))==8
        for side,base in [('cp',27),('cn',26)]:
            for i in p[side]:
                assert i not in seen;seen.add(i)
                assert by[i]['model']=='npn13g2' and by[i]['parameters']['nx']=='2'
                assert cluster(i,'B')==base and cluster(i,'E')==p['tail_cluster']
        for i in p['mos']:assert by[i]['model']=='sg13_lv_nmos'and cluster(i,'D')==p['tail_cluster']
    assert len(seen)==32
    assert c['observed_currents']==dict(npn13g2='native Ic only',sg13_lv_nmos='native Ids only',rppd=None)
    assert c['scope']==dict(new_simulation=False,derive_current_from_VBE=False,
        infer_rppd_current_from_drawn_L_over_W=False,complete_KCL_accepted=False,electrical_acceptance=False,phase_fitting=False)
    assert c['binding_sources']=={"physical":{"asset":672301614,"sha256":"c757b2d7416031b94f625591f8568a08ff61a60d62ec02c5822325083827515c"},"composition":{"asset":672354252,"sha256":"224a21ec8b8e5821d762050a4f99031399973c5b76d77142398cc66fd3fe85d8"}}
    assert c['limits']==dict(native_start_s=START,native_stop_s=STOP,native_maxstep_s=STEP,original_bits=256,reported_bits_per_sampler=255)
    assert c['unavailable']==["HBT Ib","HBT Ie","intrinsic rppd current","14662 internal extracted-wire node voltages","complete dynamic KCL"]
    w=c['original_wire_observability']
    assert w['counts']==dict(devices=500,R=24574,C=15694)
    assert w['wire_map_entries']==w['wire_unique_nodes']==15615 and w['saved_wire_nodes']==953 and w['missing_count']==14662
    return by

def topology(actual,planes,bound,requirements):
    clock=old.topology(actual,planes,bound,requirements)
    validate_contract(contract(),actual,bound)
    return clock

def selected_names(report,clock):
    names=set(old.selected_names(report,clock));c=contract()
    for d in c['native_device_records']:
        b=report['binding']['groups'][d['model']][name(d)]
        assert b['native_id']==d['native_id']
        names.update(voltage(t['node'])for t in d['terminals'])
        if current(d):names.add(current(d))
    assert names<=set(report['vectors'])
    return sorted(names)

def current_sum(d,records,ids):
    assert ids and len(ids)==len(set(ids))
    vectors=[current(records[i])for i in ids]
    assert None not in vectors and len(set(vectors))==len(vectors)
    return sum((d[v]for v in vectors),np.zeros_like(d[vectors[0]]))

def device_point(t,d,row,record):
    vv=[voltage(p['node'])for p in record['terminals']]
    cc=current(record);p=old.point(t,d,row,[*vv,*([cc]if cc else[])])
    p.update(native_id=record['native_id'],model=record['model'],native_current_vector=cc)
    if record['model']=='npn13g2':
        c,b,e=[float(d[terminal(record,k)][row])for k in ('C','B','E')]
        p.update(C_v=c,B_v=b,E_v=e,VCE_v=c-e,VBE_v=b-e,
                 Ic_a=float(d[cc][row]),nx=float(record['parameters']['nx']),
                 Ic_per_emitter_a=float(d[cc][row])/float(record['parameters']['nx']),other_terminal_currents_observed=False)
    elif record['model']=='sg13_lv_nmos':
        p.update(Ids_a=float(d[cc][row]),other_terminal_currents_observed=False)
    else:
        v1,v2=[float(d[terminal(record,k)][row])for k in ('rppd_1','rppd_2')]
        p.update(terminal_voltage_difference_v=v1-v2,current_a=None,
                 current_unavailable='Intrinsic rppd current was not saved; no drawn-L/W inference.')
    return p

def add_reason(reasons,row,why):
    assert type(row)is int and row>=0
    reasons.setdefault(row,[]).append(why)

def target_rows(t,d,report,records,c):
    active=np.flatnonzero(t>=START);assert len(active)
    reasons={};extrema={}
    for ident in FAILED:
        r=records[ident];vc,vb,ve=[d[terminal(r,k)]for k in ('C','B','E')];ic=d[current(r)]
        rr=dict(max_abs_vce=int(np.argmax(abs(vc-ve))),max_abs_vbe=int(np.argmax(abs(vb-ve))),
                max_abs_ic_per_emitter=int(np.argmax(abs(ic))),
                min_active_vce=int(active[np.argmin((vc-ve)[active])]))
        q=report['device_checks'][name(r)]
        assert abs(float(vc[rr['max_abs_vce']]-ve[rr['max_abs_vce']]))==q['maximum_alltime_abs_vce_v']
        assert abs(float(vb[rr['max_abs_vbe']]-ve[rr['max_abs_vbe']]))==q['maximum_alltime_abs_vbe_v']
        assert abs(float(ic[rr['max_abs_ic_per_emitter']]))/float(r['parameters']['nx'])==q['maximum_alltime_abs_ic_per_emitter_a']
        assert float(vc[rr['min_active_vce']]-ve[rr['min_active_vce']])==q['minimum_active_vce_v']
        extrema[str(ident)]=rr
        for kind,row in rr.items():add_reason(reasons,row,dict(kind=kind,native_id=ident))
    bits=report['source_bits'];offset=report['data_offset_s']
    expected=dict(a=bits[1:],b=bits[1:]if offset<0 else bits[:-1],c=bits[:-1],d=bits[1:]if offset<0 else bits[:-1])
    phase={}
    for tag in 'abcd':
        vp='v('+report['binding']['aliases']['xpd.'+tag+'qp']+')';vn='v('+report['binding']['aliases']['xpd.'+tag+'qn']+')'
        candidates=[]
        for i,bit in enumerate(expected[tag],1):
            edge=START+(i+(0 if tag=='b'else .5))*UI
            when=edge+.3*UI
            bracket=old.bracket(t,d,when,[vp,vn])
            for p in bracket['rows']:
                margin=(2*bit-1)*(p['values'][vp]-p['values'][vn])
                candidates.append(dict(bit_index=i,expected_bit=bit,row=p['row'],signed_margin_v=margin,requested_s=when,bracket=bracket))
        assert len(expected[tag])==255 and {x['bit_index']for x in candidates}==set(range(1,256))
        worst=min(candidates,key=lambda x:x['signed_margin_v']);worst['examined_bits']=255;phase[tag]=worst
        for p in worst['bracket']['rows']:add_reason(reasons,p['row'],dict(kind='worst_fixed_0p3UI_native_bracket',sampler=tag,bit_index=worst['bit_index']))
    drops=[]
    for p in c['gain_paths']:
        f=terminal(records[p['follower']],'E');g=terminal(records[p['gain']],'B');r=terminal(records[p['input_load']],'rppd_1')
        for a,b,label in [(f,g,'follower_E_to_gain_B'),(f,r,'follower_E_to_input_load'),(r,g,'input_load_to_gain_B')]:
            delta=d[a]-d[b];row=int(active[np.argmax(abs(delta[active]))])
            item=dict(sampler=p['sampler'],polarity=p['polarity'],kind=label,
                from_vector=a,to_vector=b,row=row,time_s=float(t[row]),voltage_difference_v=float(delta[row]),
                same_logical_net=True,current_not_inferred=True)
            drops.append(item);add_reason(reasons,row,item)
    return reasons,extrema,phase,drops

def steering(t,d,records,c):
    reports=[]
    parent=old.crossings(t,d['v(cp)']-d['v(cn)'],START,STOP)
    for p in c['clock_tails']:
        cp=current_sum(d,records,p['cp']);cn=current_sum(d,records,p['cn'])
        mos=current_sum(d,records,p['mos']);difference=cp-cn
        events=old.crossings(t,difference,START,STOP)
        ids=[*p['cp'],*p['cn'],*p['mos']]
        bases=[]
        for ip in p['cp']:
            for inn in p['cn']:
                a,b=terminal(records[ip],'B'),terminal(records[inn],'B')
                edges=old.crossings(t,d[a]-d[b],START,STOP)
                bases.append(dict(cp_id=ip,cn_id=inn,native_base_vectors=[a,b],events=edges,
                    current_event_relations=[dict(current_index=i,
                        base_indices=[j for j,x in enumerate(edges)if x['right_s']>=e['left_s']-.5*UI and x['left_s']<=e['right_s']+.5*UI],
                        relations=[old.relation(x,e)for x in edges if x['right_s']>=e['left_s']-.5*UI and x['left_s']<=e['right_s']+.5*UI])
                        for i,e in enumerate(events)]))
        active=np.flatnonzero(t>=START);assert len(active)
        extreme={}
        selected=set()
        for label,signal in [('cp_sum_Ic_a',cp),('cn_sum_Ic_a',cn),('MOS_sum_Ids_a',mos),('differential_Ic_a',difference)]:
            rr=dict(minimum=int(active[np.argmin(signal[active])]),maximum=int(active[np.argmax(signal[active])]))
            extreme[label]={k:dict(row=i,time_s=float(t[i]),value_a=float(signal[i]))for k,i in rr.items()}
            selected.update(rr.values())
        # Exact row references deduplicate endpoints; no native event is discarded.
        for e in [*parent,*events,*[e for b in bases for e in b['events']]]:
            selected.update((e['left_row'],e['right_row']))
        frames=[dict(row=i,time_s=float(t[i]),cp_sum_Ic_a=float(cp[i]),cn_sum_Ic_a=float(cn[i]),
            MOS_sum_Ids_a=float(mos[i]),observed_Ic_minus_Ids_a=float(cp[i]+cn[i]-mos[i]),
            devices=[device_point(t,d,i,records[k])for k in ids])for i in sorted(selected)]
        reports.append(dict(native_topology=p,all_current_difference_crossings=events,
            all4_actual_base_access_crossings=bases,parent_clock_crossings=parent,
            exact_native_row_frames=frames,active_extrema=extreme,currents_are_native_saved_vectors=True,
            frame_rows=sorted(selected),no_crossing_implies_no_event_not_clock_acceptance=True,
            observed_Ic_minus_Ids_is_KCL_residual=False,
            excluded_terms=['HBT base and emitter currents','intrinsic dynamic charge currents','wire displacement currents','bleeder/other branch currents'],
            clock_acceptance=False))
    assert len(reports)==8
    return reports

def diagnose(t,d,report,clock,requirements):
    c=contract();records={r['native_id']:r for r in c['native_device_records']}
    names=selected_names(report,clock)
    old.validate_rows(t,{n:d[n]for n in names},names)
    assert len(report['source_bits'])==256 and not report['devices_passed']and not report['data_passed']and not report['vi']['passed']
    reasons,extrema,phase,drops=target_rows(t,d,report,records,c)
    frames=[dict(row=i,time_s=float(t[i]),reasons=why,
        devices=[device_point(t,d,i,records[k])for k in sorted(records)])
        for i,why in sorted(reasons.items())]
    return dict(status='DIAGNOSTIC_ONLY_SAME_ROW_OBSERVED_CURRENT_LEDGER_ORIGINAL_REJECTION',
        contract_schema=c['schema'],native_device_census=c['model_census'],
        exact_failed_extremum_rows=extrema,worst_fixed_0p3UI_native_brackets=phase,
        actual_same_net_voltage_drop_extrema=drops,common_native_row_frames=frames,
        all8_parallel_clock_current_steering=steering(t,d,records,c),
        unsaved_observables=c['unavailable'],wire_observability=c['original_wire_observability'],
        full_original_measurements_reproduced_first=True,original_electrical_rejection_preserved=True,
        interpolation=False,event_filtering=False,phase_fitting=False,
        current_inferred_from_VBE=False,intrinsic_resistor_current_inferred=False,
        new_simulation=False,complete_KCL_accepted=False,cdr_accepted=False,full_phy_accepted=False)

def compact_index(ledger):
    assert ledger['original_electrical_rejection_preserved']and not ledger['cdr_accepted']
    frames={x['row']:x for x in ledger['common_native_row_frames']}
    failed={}
    for ident,extrema in ledger['exact_failed_extremum_rows'].items():
        failed[ident]={kind:next(d for d in frames[row]['devices']if d['native_id']==int(ident))
                       for kind,row in extrema.items()}
    clocks=[]
    for item in ledger['all8_parallel_clock_current_steering']:
        byrow={x['row']:x for x in item['exact_native_row_frames']}
        critical=sorted({x['row']for values in item['active_extrema'].values()for x in values.values()})
        clocks.append(dict(native_topology=item['native_topology'],
            current_difference_crossing_count=len(item['all_current_difference_crossings']),
            base_access_crossing_counts=[dict(cp_id=x['cp_id'],cn_id=x['cn_id'],count=len(x['events']))
                for x in item['all4_actual_base_access_crossings']],
            parent_crossings=len(item['parent_clock_crossings']),native_frame_count=len(byrow),
            active_extrema=item['active_extrema'],exact_extreme_frames=[byrow[i]for i in critical],
            full_events_retained_in_diagnosis=True,clock_acceptance=False))
    return dict(status=ledger['status'],native_device_census=ledger['native_device_census'],
        exact_failed_device_extrema=failed,worst_fixed_0p3UI_native_brackets=ledger['worst_fixed_0p3UI_native_brackets'],
        actual_same_net_voltage_drop_extrema=ledger['actual_same_net_voltage_drop_extrema'],
        observed_clock_tail_summaries=clocks,unsaved_observables=ledger['unsaved_observables'],
        original_electrical_rejection_preserved=True,complete_KCL_accepted=False,
        new_simulation=False,cdr_accepted=False,full_phy_accepted=False)
