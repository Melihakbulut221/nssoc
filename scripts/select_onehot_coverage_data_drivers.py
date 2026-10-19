#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Choose bounded setup ECO candidates from every reported path, screening measured hold overlap."""
import json,math,re
from select_onehot_critical_data_drivers import data_rows,CORNERS,controls as parser_controls
MASTER=re.compile(r'sg13g2_(?:buf|inv|and[234]|or[234]|nand[234]b?|nor[234]b?|xor2|xnor2|a21o|a21oi|a22oi|a221oi|o21ai|o21a|o211ai|a211oi|mux2)_[12]')
HOLD_SCREEN_NS=.2
LIMIT=128

def rows(path,kind):
    assert kind in ('min','max')
    text=path['native_report']
    assert text.count('Path Type: '+kind)==1
    # Same native column/launch boundary parser. This replacement affects only
    # parser dispatch; the original report, slack, clock and data never change.
    return data_rows(dict(path,native_report=text.replace('Path Type: '+kind,'Path Type: max')))

def select(report,actual):
    assert set(report['reports'])==set(CORNERS)
    assert set(actual)=={c+'-'+k for c in CORNERS for k in ('max','min')}
    blocked={};counts={};selected={}
    for corner in CORNERS:
        for kind in ('min','max'):
            ps=actual[corner+'-'+kind]['paths']
            assert len(ps)==report['reports'][corner][kind]['native_path_count']
            assert sorted(ps,key=lambda p:p['slack_ns'])[:12]==report['reports'][corner][kind]['worst_paths']
            counts[corner+'-'+kind]=len(ps)
        for index,p in enumerate(actual[corner+'-min']['paths']):
            assert math.isfinite(p['slack_ns'])
            if p['slack_ns']>HOLD_SCREEN_NS:continue
            for row in rows(p,'min'):
                key=(row['instance'],row['pin'])
                blocked.setdefault(key,[]).append(dict(corner=corner,path_index=index,endpoint=p['endpoint'],slack_ns=p['slack_ns']))
    screened={}
    for corner in CORNERS:
        for index,p in enumerate(actual[corner+'-max']['paths']):
            assert math.isfinite(p['slack_ns'])
            if p['slack_ns']>=0:continue
            assert p['native_status']=='VIOLATED'
            for row in rows(p,'max'):
                if not MASTER.fullmatch(row['master']) or row['pin'] not in ('X','Y'):continue
                if row['cap_pf']<.07 or row['slew_ns']<.5 or row['cell_delay_ns']<.5:continue
                if row['instance'].startswith(('clkbuf','clknet','nssoc_')):continue
                key=(row['instance'],row['pin'])
                if key in blocked:
                    screened[key]=blocked[key]
                    continue
                assert row['reported_fanout']>0
                t=selected.setdefault(key,dict(instance=row['instance'],pin=row['pin'],master=row['master'],reported_fanout=row['reported_fanout'],observations=[]))
                assert t['master']==row['master'] and t['reported_fanout']==row['reported_fanout']
                t['observations'].append(dict(corner=corner,path_index=index,startpoint=p['startpoint'],endpoint=p['endpoint'],path_slack_ns=p['slack_ns'],**row))
    ranked=sorted(selected.values(),key=lambda t:(-max(o['cell_delay_ns'] for o in t['observations']),-len({(o['corner'],o['endpoint']) for o in t['observations']}),t['instance'],t['pin']))
    assert ranked,'No eligible setup candidate; do not emit an empty successful ECO'
    targets=ranked[:LIMIT]
    return dict(targets=targets,path_sample_counts=counts,eligible_count=len(ranked),batch_limit=LIMIT,
        unselected_candidates=[dict(instance=t['instance'],pin=t['pin'],master=t['master']) for t in ranked[LIMIT:]],
        excluded_hold_overlap=[dict(instance=k[0],pin=k[1],observations=v) for k,v in sorted(screened.items())],
        hold_screen_ns=HOLD_SCREEN_NS,units=dict(cap='pF',time='ns'),
        selection_thresholds=dict(cap_pf=.07,slew_ns=.5,cell_delay_ns=.5),
        scope='All available native max/min report paths, not an exhaustive endpoint census. Bounded setup ECO on weak combinational DATA drivers, excluding observed hold paths <=0.2ns. This screen is not hold closure or proof of no new hold violations. All original clocks, cells and all-corner gates remain; fresh routing/RC/STA is mandatory.')

def controls():
    prior=parser_controls()
    def path(kind,gate,slack):
        text=f'''Startpoint: ff
Endpoint: end
Path Type: {kind}
 2 0.3 2.0 2.0 2.0 ^ clkbuf_fake/X (sg13g2_buf_1)
 2 0.3 2.0 2.0 4.0 ^ ff/Q (sg13g2_dfrbpq_1)
 2 0.3 2.0 2.0 6.0 ^ {gate}/Y (sg13g2_a22oi_1)
 6.0 data arrival time
 2 0.3 2.0 2.0 8.0 ^ capture/X (sg13g2_buf_1)
 6.0 data arrival time
'''
        return dict(startpoint='ff',endpoint='end',slack_ns=slack,native_status='VIOLATED' if slack<0 else 'MET',native_report=text)
    actual={};r=dict(reports={})
    for c in CORNERS:
        r['reports'][c]={}
        for kind,ps in [('max',[path('max','safe',-2),path('max','shared',-1)]),('min',[path('min','shared',.1)])]:
            actual[c+'-'+kind]=dict(paths=ps)
            r['reports'][c][kind]=dict(native_path_count=len(ps),worst_paths=sorted(ps,key=lambda p:p['slack_ns']))
    result=select(r,actual)
    assert [t['instance'] for t in result['targets']]==['safe']
    assert result['excluded_hold_overlap'][0]['instance']=='shared'
    bad=dict(actual);bad.pop(CORNERS[0]+'-min')
    try:select(r,bad)
    except AssertionError:pass
    else:raise AssertionError('Missing hold corner accepted')
    return dict(native_parser=prior,weak_a22oi_included=True,measured_near_hold_shared_driver_excluded=True,missing_hold_corner_rejected=True)
if __name__=='__main__':print(json.dumps(controls()))
