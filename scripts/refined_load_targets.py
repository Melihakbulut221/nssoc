#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact source-measured followup to the actual110buffer routed candidate."""
import copy,hashlib,json,os,sys,urllib.request
from pathlib import Path
import expanded_load_targets as previous
ROOT=Path(__file__).resolve().parents[1]
RECIPE_SHA='5b04799e41747fc0c732ae113b4df5909020e23d69165ff2c5f9030220af2a6c';REVIEW_SHA='735ffaebb2ddde2def6dd4adc49d2bf4555c7f3bddce83a783272fd79bcabe3e'
REVIEW_URL='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38858730197-1-expanded-driver-review/expanded-driver-review-38858730197-1.summary.json'
COUNT=141;EXTRA_COUNT=31
def digest(b):return hashlib.sha256(b).hexdigest()
def base_targets():return previous.base_targets()+previous.recipe()['targets']
def validate_rows(rows):
    base=base_targets();assert len(base)==110 and len(rows)==EXTRA_COUNT
    pins={r['pin']for r in base};instances={p.rsplit('/',1)[0]for p in pins};out=[]
    for r in rows:
        assert set(r)=={'pin','master','reported_fanout','selection'}
        inst,pin=r['pin'].rsplit('/',1);assert inst and pin in ('X','Y')and not any(c in r['pin']for c in '{}\n\r')
        assert r['pin']not in pins and inst not in instances
        assert r['master'].startswith('sg13g2_')and r['master'].endswith(('_1','_2'))and not any(k in r['master']for k in ('df','latch','dlygate','clk'))
        assert type(r['reported_fanout'])is int and r['reported_fanout']>=1
        assert r['selection']in ('negative_slow_setup_cap100fF_delay500ps','negative_fast_setup_cap50fF_delay300ps')
        pins.add(r['pin']);instances.add(inst);out.append((inst,r['master'],pin,r['reported_fanout']+1))
    return out
def recipe():
    raw=(ROOT/'docs/evidence/cloud-refined-load-targets-20261016.json').read_bytes();assert digest(raw)==RECIPE_SHA
    r=json.loads(raw);assert r['source_run']==38858730197 and r['summary_sha256']==REVIEW_SHA and r['parent_physical_run']==38843068297
    assert r['total_buffers']==COUNT and r['base_buffers']==110;validate_rows(r['targets']);return r

def verify_review(raw):
    assert digest(raw)==REVIEW_SHA
    r=json.loads(raw);assert r['status']=='COMPLETE_SOURCE_BOUND_SETUP_HOLD_DRIVER_DIAGNOSIS_NOT_REPAIR'and r['source_unchanged']
    assert r['unique_weak_loaded_outputs']==len(r['ranked_outputs'])==29
    assert len(r['negative_fast_setup_paths'])==3
    selected={}
    def stage(s):
        cols=s['native_line'].split();assert int(cols[0])==s['fanout']and float(cols[1])==s['cap_pf']and float(cols[3])==s['delay_ns']
        assert s['native_line'].endswith(s['pin']+' ('+s['master']+')')
    for row in r['ranked_outputs']:
        fanouts=set()
        for o in row['observations']:
            assert o['slack_ns']<0 and o['phase'].endswith('slow_max')
            s=o['stage'];stage(s);assert s['pin']==row['pin']and s['master']==row['master']and s['cap_pf']>=.1 and s['delay_ns']>=.5;fanouts.add(s['fanout'])
        assert len(fanouts)==1
        selected[row['pin']]=dict(pin=row['pin'],master=row['master'],reported_fanout=fanouts.pop(),selection='negative_slow_setup_cap100fF_delay500ps')
    for path in r['negative_fast_setup_paths']:
        m=path['metadata'];assert m['corner']=='fast'and m['path_type']=='max'and m['slack_ns']<0
        for s in path['stages']:
            stage(s)
            if s['master'].startswith('sg13g2_')and s['master'].endswith(('_1','_2'))and not any(k in s['master']for k in ('df','latch','dlygate','clk'))and s['cap_pf']>=.05 and s['delay_ns']>=.3:
                if s['pin']in selected:assert selected[s['pin']]['master']==s['master']and selected[s['pin']]['reported_fanout']==s['fanout']
                else:selected[s['pin']]=dict(pin=s['pin'],master=s['master'],reported_fanout=s['fanout'],selection='negative_fast_setup_cap50fF_delay300ps')
    assert list(selected.values())==recipe()['targets'];validate_rows(list(selected.values()))
    return dict(source_run=38858730197,summary_sha256=REVIEW_SHA,recipe_sha256=RECIPE_SHA,new_targets=EXTRA_COUNT,cumulative_buffers=COUNT,hold_safety_proven=False)

def validate_candidate(candidate,directory):
    directory=Path(directory);previous.verify_review((directory/'driver-review-summary.json').read_bytes());verify_review((directory/'refined-driver-review-summary.json').read_bytes())
    assert candidate['profile']=='refined_load_batch'and candidate['buffer_count']==COUNT
    assert candidate['target_selection']['refined_recipe_sha256']==RECIPE_SHA
    rows=base_targets()+recipe()['targets'];changes=candidate['geometry']['changes'];assert len(rows)==len(changes)==COUNT
    for row,c in zip(rows,changes,strict=True):
        inst,pin=row['pin'].rsplit('/',1);assert (c['driver'],c['driver_pin'],c['original_terminal_count'])==(inst,pin,row['reported_fanout']+1)and c['buffer_master']=='sg13g2_buf_16'
    proof=json.loads((directory/'post-route-geometry.json').read_text());assert proof==candidate['post_route_geometry']
    assert proof['status']=='PASS_ALL_CANDIDATE_CELLS_TOPOLOGY_PG_PORTS_NDR_PRESERVED_AFTER_ROUTE'
    assert proof['instances']==113791+COUNT and proof['nets']==113863+COUNT and proof['profile']=='refined_load_batch'
    assert all(proof[k]is True for k in ('all_candidate_cell_signatures_unchanged','all_net_memberships_unchanged','pg_ports_ndr_unchanged'))
    assert proof['routed_odb_sha256']==digest((directory/'routed.odb').read_bytes())

def controls():
    rows=recipe()['targets'];validate_rows(rows);cases=[]
    b=copy.deepcopy(rows);b.pop();cases.append(('missing',b))
    b=copy.deepcopy(rows);b[1]=copy.deepcopy(b[0]);cases.append(('duplicate',b))
    b=copy.deepcopy(rows);b[0]['pin']=base_targets()[0]['pin'];cases.append(('prior_overlap',b))
    for field,value in [('master','sg13g2_dfrbpq_1'),('reported_fanout',0),('selection','unmeasured'),('pin','bad\n/X')]:
        b=copy.deepcopy(rows);b[0][field]=value;cases.append((field,b))
    for name,b in cases:
        try:validate_rows(b)
        except (AssertionError,KeyError,ValueError):pass
        else:raise AssertionError('Accepted corrupt target '+name)
    return dict(new_targets=EXTRA_COUNT,total=COUNT,rejected=[n for n,b in cases],hold_safety_proven=False)
if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true';print(json.dumps(controls()))
    if '--verify-published'in sys.argv:
        with urllib.request.urlopen(REVIEW_URL,timeout=120)as response:raw=response.read()
        print(json.dumps(verify_review(raw)))
        try:verify_review(raw+b' ')
        except AssertionError:print('REJECTED_CHANGED_SOURCE_BYTES')
        else:raise AssertionError('Changed source accepted')
