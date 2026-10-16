# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Five measured hold branches on the exact completed 141buffer candidate."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RECIPE_SHA='8eabcf9f3e0ace7ec6240474f1a5a0758c31f0350d559c5ef70a64b43572342b'
PARENT_SUMMARY_SHA='3786689b73b2a290f91b2cdf5414c08690f7e5a681eb8c240252b503ea38b725'
PARENT_PARTS_SHA='e3d5c7fde3593eefd7a0a3f7514c4735284aa67694f451b31482e8439a785390'
PARENT_GEOMETRY_SHA='1d1950bbd4f7c4d2b44c9debc0a8139d2acf5bbb8934d3222d3ea7cfbd9494f0'
PARENT_ODB_SHA='4e54050fab1ccb130d3d7484d85b428b17d050137173fe5604035c995b1a9fcc'
PROFILE='refined_hold_batch';COUNT=146;STAGE_COUNT=5
DIRECTORY='cloud-refined-hold-eco'
COMPLETE_STATUS='COMPLETE_REFINED_HOLD_BATCH_ROUTED_NOMINAL_TIMING_EXPERIMENT_NOT_SIGNOFF'
MAX_DISPLACEMENT_UM=(1000,200)
def select(record):
    assert record['run']==38874773944 and record['candidate_run']==38859276266
    assert record['summary_sha256']=='591e7d5c7e4ed189fd2c251af0eaa81998564e1d28ad5ababfeab2896573b33d'
    assert record['source_unchanged'] and record['candidate_routed_timing_reproduced']
    trace=record['trace'];assert len(trace['targets'])==91 and trace['requested_paths']==546
    assert trace['original_candidate_timing_reproduced'] and not trace['unconstrained_requests']
    targets=[row for row in trace['targets'] if all(v is not None and v>0 for v in row['setup_seconds'].values())]
    assert targets==record['positive_setup_hold_targets'] and len(targets)==5
    assert len({(r['native_pin']['instance'],r['native_pin']['pin']) for r in targets})==5
    for r in targets:
        assert r['native_pin']['kind']=='instance'
        assert r['native_pin']['pin'] in ('A_MEN','A_ADDR[5]')
        assert r['hold_seconds']['fast']<0 and all(v>0 for k,v in r['hold_seconds'].items() if k!='fast')
    assert record['delay_masters']==['sg13g2_dlygate4sd3_1','sg13g2_dlygate4sd3_1','sg13g2_dlygate4sd1_1','sg13g2_dlygate4sd3_1','sg13g2_dlygate4sd3_1']
    return [dict(r,delay_master=m)for r,m in zip(targets,record['delay_masters'],strict=True)]
raw=(ROOT/'docs/evidence/cloud-refined-load-hold-targets-20261016.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==RECIPE_SHA
RECORD=json.loads(raw);TARGETS=select(RECORD)
SELECTION=dict(recipe_sha256=RECIPE_SHA,source_trace_run=38874773944,parent_candidate_run=38859276266,stage_added_cells=5,cumulative_added_cells=146,scope='All five negative-hold targets having positive setup at every original cell corner in the exact 141buffer candidate. Other86hold targets still conflict with setup. No assumption that a delay cell closes timing.')
def validate_measurements(text):
    assert hashlib.sha256(text.encode()).hexdigest()=='b14e8271541ef2e78859b8c3b30296691c67c3d648b0dc3afc5187b3455d9188'
    select(RECORD)
def validate_child(candidate,directory):
    assert candidate['profile']==PROFILE and candidate['buffer_count']==146
    assert candidate['stage_added_cells']==5 and candidate['parent_added_cells']==141
    assert candidate['target_selection']==SELECTION and candidate['parent_routed_timing_reproduced']
    parent=candidate['parent_candidate']
    assert parent['run']==38859276266 and parent['summary_sha256']==PARENT_SUMMARY_SHA and parent['manifest_sha256']==PARENT_PARTS_SHA
    for name,digest in [('parent-source-summary.json',PARENT_SUMMARY_SHA),('parent-geometry-summary.json',PARENT_GEOMETRY_SHA)]:
        assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest
    proof=json.loads((directory/'post-route-geometry.json').read_text())
    assert proof==candidate['post_route_geometry'] and proof['status']=='PASS_PARENT_CELLS_AND_DECLARED_DELAY_BRANCHES_AFTER_ROUTE'
    assert proof['stage_added_cells']==5 and proof['parent_instances']==113932 and proof['instances']==113937 and proof['nets']==114009
    assert proof['parent_odb_sha256']==PARENT_ODB_SHA
    geometry=candidate['geometry'];assert geometry['stage_original_instances']==113932 and len(geometry['stage_changes'])==5
    assert [(x['sink'],x['sink_pin']) for x in geometry['stage_changes']]==[(r['native_pin']['instance'],r['native_pin']['pin']) for r in TARGETS]
    assert [x['buffer_master']for x in geometry['stage_changes']]==[r['delay_master']for r in TARGETS]
    return True
CHILD_FILES=('parent-source-summary.json','parent-geometry-summary.json','post-route-geometry.json')
def controls():
    import copy
    assert len(select(RECORD))==5
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
def verify_published():
    import urllib.request
    url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38874773944-1-eco-endpoint-compare/eco-endpoint-compare-38874773944-1.summary.json'
    with urllib.request.urlopen(url,timeout=120)as response:raw=response.read()
    assert hashlib.sha256(raw).hexdigest()==RECORD['summary_sha256']
    original=json.loads(raw);trace=original['hold_conflict_paths']
    assert original['candidate']['run']==RECORD['candidate_run'] and original['source_unchanged'] and original['candidate_routed_timing_reproduced']
    assert {k:trace[k]for k in RECORD['trace']}==RECORD['trace']
    return dict(original_endpoint_summary_verified=True,targets=5,delay_fit_proven=False)
if __name__=='__main__':print(json.dumps(dict(controls=controls(),published=verify_published())))
