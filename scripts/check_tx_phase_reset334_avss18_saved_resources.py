#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual resource-plan/writer fixtures with synthetic arrays and temporary JSON only."""
import copy,hashlib,json,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import tx_phase_reset334_avss18_saved_resources as r
import tx_phase_reset334_avss18_saved_diagnosis as d

def controls():
    positives=[];refused=[]
    def reject(name,fn,kind=r.ResourceLimit):
        try:fn()
        except kind:refused.append(name)
        else:raise AssertionError('Accepted resource corruption '+name)
    t=np.linspace(0.,34e-9,257)
    values={'v(p)':np.sin(t*2*np.pi/2e-9)*.2,'v(n)':np.zeros_like(t),
      'v(c)':.65+.2*np.sin(t*2*np.pi/4e-9),'v(b)':np.full_like(t,1.),
      'v(e)':np.full_like(t,.3),'v(s)':np.zeros_like(t),
      '@q.xt.qnpn13g2[ic]':np.full_like(t,.004)}
    c=dict(vectors=list(values),hbt={'xt':dict(terminals=['c','b','e','s'],nx=4)},
      instances=[dict(oracle=dict(first_falls=[dict(arm_s=4e-9,fall_s=5e-9),dict(arm_s=9e-9,fall_s=10e-9)]))],
      timing=dict(clock_ramp_s=5e-12,reset_assert_s=1e-9,reset_release_s=1.5e-9))
    replay=dict(measurement=dict(hbt_safety={'xt':dict(passed=False)}))
    def plan():return r.plan(t,values,c,replay,['xt'],{'xt':'synthetic'},d.intervals)
    with patch.object(r.old,'pairs',return_value={'synthetic':['p','n']}):
        p=plan()
        assert p['counts']['frames']==len(p['required_frame_rows'])<=len(t)
        assert p['counts']['tail_violation_intervals']>1 and p['counts']['first_fall_window_associations']>1
        assert p['counts']['crossings']==sum(len(r.old.crossing_rows(t,values['v(p)'],level))for level in (-.1,0.,.1))
        y=values['v(c)']-values['v(e)'];active=np.flatnonzero(t>=r.old.START)
        assert int(active[np.argmin(y[active])])in p['required_frame_rows']
        assert not p['subsampling_or_truncation']
        positives.append('actual_resource_plan_preserves_fixed_selectors_on_synthetic_arrays')
        for constant,label in [('MAX_FRAMES','frame_limit'),('MAX_CROSSINGS','crossing_limit'),
          ('MAX_WINDOW_ASSOCIATIONS','window_limit'),('MAX_INTERVALS','interval_limit')]:
            with patch.object(r,constant,1):reject(label,plan)
    memory=r.admit_memory(p,p['estimated_required_available_bytes'])
    assert memory['planning_estimate_bytes']==memory['available_bytes']
    positives.append('exact_available_memory_boundary')
    reject('insufficient_memory',lambda:r.admit_memory(p,p['estimated_required_available_bytes']-1))
    frames={str(i):dict(row=i,time_s=float(t[i]))for i in p['required_frame_rows']}
    assert r.validate_frames(p,frames,t)
    positives.append('exact_planned_native_row_and_time_binding')
    for label,change in [('missing_planned_frame',lambda q:q.pop(next(iter(q)))),
      ('wrong_frame_row',lambda q:q[next(iter(q))].update(row=-1)),
      ('wrong_frame_time',lambda q:q[next(iter(q))].update(time_s=-1.)),
      ('extra_frame',lambda q:q.update({'999999':dict(row=999999,time_s=0.)}))]:
        q=copy.deepcopy(frames);change(q)
        reject(label,lambda q=q:r.validate_frames(p,q,t),AssertionError)
    native_sizes={'wave.raw':4331024984,'contract.json':292922,'bench.cir':161509,'native.log':654512,'op.raw':185366}
    disk=r.input_budget(native_sizes,431354125,150927784)
    assert disk['combined_supported_disk_bound_bytes']<disk['required_free_disk_bytes']
    assert not disk['raw_or_input_archives_in_publication']
    positives.append('exact_recorded_OP_inventory_and_supported_native_file_disk_budget')
    q=dict(native_sizes);q['native.log']=1024**2+1
    reject('native_file_size_limit',lambda:r.input_budget(q,431354125,150927784))
    reject('wrong_current_OP_inventory_size',lambda:r.input_budget(native_sizes,431354126,150927784),AssertionError)
    reject('wrong_current_OP_archive_size',lambda:r.input_budget(native_sizes,431354125,150927785),AssertionError)
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);target=root/'witness.json';value=dict(values=[1.,2.,3.],complete=True)
        proof=r.write(target,value);raw=target.read_bytes()
        assert json.loads(raw)==value and proof['bytes']==len(raw)
        assert proof['sha256']==hashlib.sha256(raw).hexdigest()and proof['streamed_complete_JSON']
        positives.append('actual_streaming_JSON_complete_byte_and_digest_roundtrip')
        before=target.read_bytes()
        with patch.object(r,'MAX_JSON_BYTES',16):
            reject('single_JSON_limit',lambda:r.write(target,dict(values=list(range(40)))))
        assert target.read_bytes()==before and (root/'witness.json.incomplete').is_file()
        assert (root/'witness.json.incomplete').stat().st_size<=16
        positives.append('byte_limit_preserves_prior_complete_file_and_explicit_incomplete_fragment')
        with patch.object(r,'MAX_OUTPUT_BYTES',128),patch.object(r,'FAILURE_RESERVE_BYTES',32):
            reject('aggregate_output_limit',lambda:r.write(root/'other.json',dict(values=list(range(100)))))
        assert (root/'other.json.incomplete').is_file()
        reject('nonfinite_JSON',lambda:r.write(root/'nonfinite.json',dict(value=float('nan'))),ValueError)
        assert (root/'nonfinite.json.incomplete').is_file()and not(root/'nonfinite.json').exists()
        symlink=root/'link.json';symlink.symlink_to(target)
        reject('symlink_output',lambda:r.write(symlink,{}),AssertionError);symlink.unlink()
        failure=dict(status='INCOMPLETE_RESOURCE_REFUSAL',accepted=False,complete_diagnosis=False)
        r.write(root/'result.json',failure)
        assert json.loads((root/'result.json').read_bytes())==failure and target.read_bytes()==before
        positives.append('complete_failure_record_after_limits_without_truncating_prior_evidence')
    assert len(positives)==7 and len(refused)==16,(len(positives),len(refused))
    return dict(status='PASS_SAVED_DIAGNOSIS_RESOURCE_FIXTURES_ONLY',positives=positives,refused=refused,
      synthetic_arrays_only=True,native_waveform_read=False,no_observations_dropped_to_obtain_acceptance=True,
      full_JSON_streamed=True,complete_failure_record_required=True)
if __name__=='__main__':print(json.dumps(controls(),indent=2))
