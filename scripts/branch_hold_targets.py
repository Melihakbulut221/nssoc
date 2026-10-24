# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact native short-branch targets whose all-reachable setup margin is positive."""
import hashlib,json,copy,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RECIPE_SHA='12795513c5d9694eaae9daed4ca6b2c6209a42040c1ff8bdba9a23f249e8b31a'
PARENT_SUMMARY_SHA='aa87fe441e4b3680c84bb0d46f50ccb3fe744a031dbc81a4d96de0efc2b59a2c'
PARENT_PARTS_SHA='612de7f6659774b2b4d3211ae7e10a04df7d808d732f1404ce19a981b90b1586'
PARENT_GEOMETRY_SHA='d8ee55b0d9257ce8eb6e52fd74c832127e4197c914c07e731d60a0b9a35261cc'
PARENT_ODB_SHA='1e97e6c345d9529a7a40b9435a15b58382971d9c94d5f24ff18daaa3e381a747'
PROFILE='branch_hold_batch';COUNT=234;STAGE_COUNT=88;DIRECTORY='cloud-branch-hold-eco'
COMPLETE_STATUS='COMPLETE_BRANCH_HOLD_BATCH_ROUTED_NOMINAL_TIMING_EXPERIMENT_NOT_SIGNOFF'
MAX_DISPLACEMENT_UM=(1000,200)
def select(r):
    assert r['run']==38895551929 and r['summary_sha256']=='ad2f6bbe9b0c20249d323ab647bd9e869f2dacaf9035c9bf5fadc3f5bcdb9850'
    assert r['source_unchanged']and r['original_timing_reproduced']and len(r['rows'])==90
    assert len({x['branch_pin']for x in r['rows']})==90
    chosen=[]
    for x in r['rows']:
        assert x['matching_input_pins']==[x['branch_pin'].rsplit('/',1)[1]]
        assert x['through_hold_ns']['fast']<0
        good=all(v is not None and v>0 for v in x['all_reachable_setup_ns'].values())
        assert x['positive_setup_all_reachable_endpoints']==good
        if not good:continue
        instance,pin=x['branch_pin'].rsplit('/',1)
        assert instance==x['next_pin'].rsplit('/',1)[0]and x['sink_master'].startswith('sg13g2_')
        chosen.append(dict(x,native_pin=dict(kind='instance',instance=instance,pin=pin),delay_master='sg13g2_dlygate4sd1_1'if min(x['all_reachable_setup_ns'].values())<1.0 else'sg13g2_dlygate4sd3_1'))
    assert len(chosen)==88 and r['positive_all_reachable_branch_count']==88
    assert sum(x['delay_master']=='sg13g2_dlygate4sd1_1'for x in chosen)==7
    return chosen
raw=(ROOT/'docs/evidence/route146-all-reachable-branch-recipe-20261016.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==RECIPE_SHA
RECORD=json.loads(raw);TARGETS=select(RECORD)
SELECTION=dict(recipe_sha256=RECIPE_SHA,source_trace_run=38895551929,parent_candidate_run=38880596259,stage_added_cells=88,cumulative_added_cells=234,scope='88 exact short-only gate inputs have positive max-path slack through the input to every reachable endpoint at all3 original cell corners. Use sd1 at7 branches with less than1ns slow margin and sd3 elsewhere as an unproven sizing hypothesis. Two negative setup branches untouched. All original global timing/geometry gates remain required.')
def validate_measurements(text):
    assert hashlib.sha256(text.encode()).hexdigest()=='b14e8271541ef2e78859b8c3b30296691c67c3d648b0dc3afc5187b3455d9188'
    select(RECORD)
def validate_child(candidate,directory):
    assert candidate['profile']==PROFILE and candidate['buffer_count']==234 and candidate['stage_added_cells']==88 and candidate['parent_added_cells']==146
    assert candidate['target_selection']==SELECTION and candidate['parent_routed_timing_reproduced']
    p=candidate['parent_candidate'];assert p['run']==38880596259 and p['summary_sha256']==PARENT_SUMMARY_SHA and p['manifest_sha256']==PARENT_PARTS_SHA
    for n,d in [('parent-source-summary.json',PARENT_SUMMARY_SHA),('parent-geometry-summary.json',PARENT_GEOMETRY_SHA)]:assert hashlib.sha256((directory/n).read_bytes()).hexdigest()==d
    proof=json.loads((directory/'post-route-geometry.json').read_text());assert proof==candidate['post_route_geometry']
    assert proof['status']=='PASS_PARENT_CELLS_AND_DECLARED_DELAY_BRANCHES_AFTER_ROUTE'and proof['parent_odb_sha256']==PARENT_ODB_SHA
    assert proof['parent_instances']==113937 and proof['stage_added_cells']==88 and proof['instances']==114025 and proof['nets']==114097
    g=candidate['geometry'];assert g['stage_original_instances']==113937 and len(g['stage_changes'])==88
    assert [(x['sink'],x['sink_pin'],x['buffer_master'])for x in g['stage_changes']]==[(r['native_pin']['instance'],r['native_pin']['pin'],r['delay_master'])for r in TARGETS]
    return True
CHILD_FILES=('parent-source-summary.json','parent-geometry-summary.json','post-route-geometry.json')
def controls():
    for fault in ('missing','wrong_parent','negative_setup','wrong_pin'):
        r=copy.deepcopy(RECORD)
        if fault=='missing':r['rows'].pop()
        elif fault=='wrong_parent':r['run']=38894611105
        elif fault=='negative_setup':r['rows'][0]['all_reachable_setup_ns']['slow']=-1.0
        else:r['rows'][0]['matching_input_pins']=['WRONG']
        try:select(r)
        except AssertionError:pass
        else:raise AssertionError('Corrupt source recipe accepted '+fault)
    return dict(exact_native_branches=88,negative_controls=4,all_reachable_setup_checked=True,delay_fit_proven=False)
def verify_published():
    url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38895551929-1-route146-branch-margins/route146-branch-margins-38895551929-1.summary.json'
    with urllib.request.urlopen(url,timeout=120)as response:raw=response.read()
    assert hashlib.sha256(raw).hexdigest()==RECORD['summary_sha256'];source=json.loads(raw)
    assert source['rows']==RECORD['rows']and source['source_unchanged']and source['original_timing_reproduced']
    return dict(native_summary_verified=True,targets=88,all_reachable_endpoint_maxima_included=True)
if __name__=='__main__':print(json.dumps(dict(controls=controls(),published=verify_published())))
