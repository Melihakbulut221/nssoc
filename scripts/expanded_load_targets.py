#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound next load experiment; diagnostic absence never proves hold safety."""
import copy,hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROFILE='expanded_load_batch'
RECIPE_SHA='8e998b9f304aedc02e22a8f3aa171c6b6c4b0d0e187650c3bf59581e436e37ee'
REVIEW_SHA='a7b7c9ec447475af9dc7dc5e2a08f7552a4aab2b0404471166edef331244eea8'
REVIEW_URL='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38839736674-1-setup-hold-driver-review/setup-hold-driver-review-38839736674-1.summary.json'
EXTRA_FILES=('driver-review-summary.json','post-route-geometry.json')
ALLOWED={'sg13g2_a22oi_1','sg13g2_and3_1','sg13g2_and4_1','sg13g2_buf_1','sg13g2_buf_2','sg13g2_nand2b_1','sg13g2_nand3b_1','sg13g2_nand4_1','sg13g2_xor2_1'}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def base_targets():
    raw=(ROOT/'docs/evidence/cloud-routed-high-load-targets-20261016.json').read_bytes()
    assert digest(raw)=='7f6572696f303fda18383f7d0def5c8e583c15b9cd7cf821dc4c7aa6170341de'
    return json.loads(raw)['selection']['targets']
def validate_rows(rows,base):
    assert len(rows)==60 and len(base)==50
    pins=set();instances=set();old={r['pin'] for r in base}
    for r in rows:
        assert set(r)=={'pin','master','reported_fanout'}
        inst,pin=r['pin'].rsplit('/',1)
        assert inst and pin in ('X','Y') and not any(c in r['pin'] for c in '{}\n\r')
        assert r['master'] in ALLOWED
        assert type(r['reported_fanout']) is int and r['reported_fanout']>=1
        assert r['pin'] not in old|pins and inst not in instances
        pins.add(r['pin']);instances.add(inst)
    assert not instances&{r['pin'].rsplit('/',1)[0] for r in base}
    return [(r['pin'].rsplit('/',1)[0],r['master'],r['pin'].rsplit('/',1)[1],r['reported_fanout']+1) for r in rows]
def recipe():
    raw=(ROOT/'docs/evidence/cloud-expanded-load-targets-20261016.json').read_bytes()
    assert digest(raw)==RECIPE_SHA
    data=json.loads(raw)
    assert data['source_run']==38839736674 and data['source_head']=='dfc9db682d460dd5f497964baefde3a2736780c0'
    assert data['summary_sha256']==REVIEW_SHA and data['parent_physical_run']==38824521607
    assert data['parent_summary_sha256']=='2567e3e86159187b5f6db0df8a1c2be663c3d66df9e20d4fc650f98fe9ad2db5'
    validate_rows(data['targets'],base_targets());return data

def verify_review(raw):
    assert digest(raw)==REVIEW_SHA,'Changed source diagnosis'
    source=json.loads(raw);data=recipe()
    assert source['status']=='COMPLETE_SOURCE_BOUND_SETUP_HOLD_DRIVER_DIAGNOSIS_NOT_REPAIR'
    assert source['source_head']==data['source_head'] and source['source_unchanged']
    assert source['unique_weak_loaded_outputs']==len(source['ranked_outputs'])==60
    derived=[]
    for r in source['ranked_outputs']:
        assert r['requires_native_odb_pin_resolution'] is True and r['observations']
        fanouts=set()
        for o in r['observations']:
            stage=o['stage'];assert o['phase']=='slow_max' and o['slack_ns']<0
            assert stage['pin']==r['pin'] and stage['master']==r['master']
            assert stage['cap_pf']>=.1 and stage['delay_ns']>=.5
            values=stage['native_line'].split()
            assert int(values[0])==stage['fanout'] and float(values[1])==stage['cap_pf'] and float(values[3])==stage['delay_ns']
            assert stage['native_line'].endswith(r['pin']+' ('+r['master']+')')
            fanouts.add(stage['fanout'])
        assert len(fanouts)==1
        derived.append(dict(pin=r['pin'],master=r['master'],reported_fanout=fanouts.pop()))
    assert derived==data['targets'];validate_rows(derived,base_targets())
    return {'source_run':38839736674,'summary_sha256':REVIEW_SHA,'recipe_sha256':RECIPE_SHA,'new_targets':60,'cumulative_buffers':110,'hold_safety_proven':False}

def validate_candidate(candidate,directory):
    directory=Path(directory);verify_review((directory/'driver-review-summary.json').read_bytes())
    assert candidate['profile']==PROFILE and candidate['buffer_count']==110
    selection=candidate['target_selection'];assert selection['extra_recipe_sha256']==RECIPE_SHA and selection['driver_review_sha256']==REVIEW_SHA
    allrows=base_targets()+recipe()['targets'];changes=candidate['geometry']['changes']
    assert len(changes)==110
    for row,change in zip(allrows,changes):
        inst,pin=row['pin'].rsplit('/',1)
        assert (change['driver'],change['driver_pin'],change['original_terminal_count'])==(inst,pin,row['reported_fanout']+1)
        assert change['buffer_master']=='sg13g2_buf_16'
    proof=json.loads((directory/'post-route-geometry.json').read_text())
    assert proof==candidate['post_route_geometry']
    assert proof['status']=='PASS_ALL_CANDIDATE_CELLS_TOPOLOGY_PG_PORTS_NDR_PRESERVED_AFTER_ROUTE'
    assert proof['instances']==113901 and proof['nets']==113973 and proof['profile']==PROFILE
    for key in ('all_candidate_cell_signatures_unchanged','all_net_memberships_unchanged','pg_ports_ndr_unchanged'):
        assert proof[key] is True
    assert proof['routed_odb_sha256']==digest((directory/'routed.odb').read_bytes())

def controls():
    rows=recipe()['targets'];base=base_targets();assert len(validate_rows(rows,base))==60
    cases=[]
    bad=copy.deepcopy(rows);bad.pop();cases.append(('missing_target',bad))
    bad=copy.deepcopy(rows);bad[1]=copy.deepcopy(bad[0]);cases.append(('duplicate_target',bad))
    bad=copy.deepcopy(rows);bad[0]['pin']=base[0]['pin'];cases.append(('old_target_overlap',bad))
    bad=copy.deepcopy(rows);bad[0]['master']='sg13g2_dfrbp_1';cases.append(('sequential_master',bad))
    bad=copy.deepcopy(rows);bad[0]['reported_fanout']=0;cases.append(('zero_fanout',bad))
    bad=copy.deepcopy(rows);bad[0]['pin']='bad\n/X';cases.append(('unsafe_native_name',bad))
    rejected=[]
    for name,bad in cases:
        try:validate_rows(bad,base)
        except (AssertionError,KeyError,ValueError):rejected.append(name)
        else:raise AssertionError('Accepted altered targets: '+name)
    return {'targets':60,'cumulative':110,'rejected':rejected,'hold_safety_proven':False}
if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true';print(json.dumps(controls()))
