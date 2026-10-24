# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Four measured hold branches on the exact completed fifty-buffer candidate."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RECIPE_SHA='55046b17b57dc82eeecbd26783ac62241bde725fce3eab21f9f271dd9a76565b'
PARENT_SUMMARY_SHA='2567e3e86159187b5f6db0df8a1c2be663c3d66df9e20d4fc650f98fe9ad2db5'
PARENT_PARTS_SHA='cbf6cb0b3c6cb3962ff6d410739926146901f731229f2cb915d656bf786eafb5'
PARENT_GEOMETRY_SHA='ec70564bed59a2152c50ba626ef7be067b5a607232fb353c07482f9ea152733a'
PARENT_ODB_SHA='c1192b0a9ed8ea04f1c42372ad519d953e197683945b1174fc7756bbe137528e'
PROFILE='measured_hold_batch';COUNT=54;STAGE_COUNT=4
DIRECTORY='cloud-measured-hold-eco'
COMPLETE_STATUS='COMPLETE_MEASURED_HOLD_BATCH_ROUTED_NOMINAL_TIMING_EXPERIMENT_NOT_SIGNOFF'
MAX_DISPLACEMENT_UM=(1000,200)
def select(record):
    assert record['run']==38836226947 and record['candidate_run']==38824521607
    assert record['summary_sha256']=='9bd5d1a86cb83d83d8df5505e1a7cf47c1fc086ef45431274798083749709348'
    assert record['source_unchanged'] and record['candidate_routed_timing_reproduced']
    trace=record['trace'];assert len(trace['targets'])==96 and trace['requested_paths']==576
    assert trace['original_candidate_timing_reproduced'] and not trace['unconstrained_requests']
    targets=[row for row in trace['targets'] if all(v is not None and v>0 for v in row['setup_seconds'].values())]
    assert targets==record['positive_setup_hold_targets'] and len(targets)==4
    assert len({(r['native_pin']['instance'],r['native_pin']['pin']) for r in targets})==4
    for r in targets:
        assert r['native_pin']['kind']=='instance'
        assert r['native_pin']['pin'] in ('A_MEN','A_ADDR[5]')
        assert r['hold_seconds']['fast']<0 and all(v>0 for k,v in r['hold_seconds'].items() if k!='fast')
    return targets
raw=(ROOT/'docs/evidence/cloud-measured-load-hold-conflicts-20261016.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==RECIPE_SHA
RECORD=json.loads(raw);TARGETS=select(RECORD)
SELECTION=dict(recipe_sha256=RECIPE_SHA,source_trace_run=38836226947,parent_candidate_run=38824521607,stage_added_cells=4,cumulative_added_cells=54,scope='All four negative-hold targets having positive setup at every original cell corner in the exact fifty-buffer candidate. Other92hold targets still conflict with setup. No assumption that a delay cell closes timing.')
def validate_measurements(text):
    assert hashlib.sha256(text.encode()).hexdigest()=='b14e8271541ef2e78859b8c3b30296691c67c3d648b0dc3afc5187b3455d9188'
    select(RECORD)
def validate_child(candidate,directory):
    assert candidate['profile']==PROFILE and candidate['buffer_count']==54
    assert candidate['stage_added_cells']==4 and candidate['parent_added_cells']==50
    assert candidate['target_selection']==SELECTION and candidate['parent_routed_timing_reproduced']
    parent=candidate['parent_candidate']
    assert parent['run']==38824521607 and parent['summary_sha256']==PARENT_SUMMARY_SHA and parent['manifest_sha256']==PARENT_PARTS_SHA
    for name,digest in [('parent-source-summary.json',PARENT_SUMMARY_SHA),('parent-geometry-summary.json',PARENT_GEOMETRY_SHA)]:
        assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest
    proof=json.loads((directory/'post-route-geometry.json').read_text())
    assert proof==candidate['post_route_geometry'] and proof['status']=='PASS_PARENT_CELLS_AND_DECLARED_DELAY_BRANCHES_AFTER_ROUTE'
    assert proof['stage_added_cells']==4 and proof['parent_instances']==113841 and proof['instances']==113845 and proof['nets']==113917
    assert proof['parent_odb_sha256']==PARENT_ODB_SHA
    geometry=candidate['geometry'];assert geometry['stage_original_instances']==113841 and len(geometry['stage_changes'])==4
    assert [(x['sink'],x['sink_pin']) for x in geometry['stage_changes']]==[(r['native_pin']['instance'],r['native_pin']['pin']) for r in TARGETS]
    assert all(x['buffer_master']=='sg13g2_dlygate4sd3_1' for x in geometry['stage_changes'])
    return True
CHILD_FILES=('parent-source-summary.json','parent-geometry-summary.json','post-route-geometry.json')
def controls():
    import copy
    assert len(select(RECORD))==4
    for kind in ('missing','wrong_parent','negative_setup','wrong_mapping'):
        r=copy.deepcopy(RECORD)
        if kind=='missing':r['trace']['targets'].pop()
        elif kind=='wrong_parent':r['candidate_run']=38813118414
        elif kind=='negative_setup':
            target=next(x for x in r['trace']['targets'] if x['endpoint']==TARGETS[0]['endpoint']);target['setup_seconds']['slow']=-1e-9
        else:
            target=next(x for x in r['trace']['targets'] if x['endpoint']==TARGETS[0]['endpoint']);target['native_pin']['pin']='A_ADDR[4]'
        try:select(r)
        except AssertionError:pass
        else:raise AssertionError('Invalid target recipe accepted: '+kind)
    return dict(exact_measured_targets=4,negative_controls=4,unchanged_native_pin_names=True)
if __name__=='__main__':print(json.dumps(controls()))
