#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted admission/derivation controls. No Pya, GDS or engine execution."""
import copy,json,os,tempfile
from pathlib import Path
from unittest import mock
import cloud_tx_phase_reset244_avss18_physical as c
import tx_phase_reset244_avss18_baseline as b
FIXTURE='docs/evidence/tx-phase-reset244-avss18-physical-admission-fixtures-20261025.json'
def controls():
    c.methods()
    fixture=json.loads((c.ROOT/FIXTURE).read_text())
    result=json.loads((c.ROOT/c.SOURCE_RESULT).read_text());log=(c.ROOT/c.SOURCE_LOG).read_bytes()
    raw,prior=b.baseline()
    c.validate_source_proof(fixture['source_run'],fixture['source_job'],result,log)
    b.validate_run(fixture['physical_run'],fixture['physical_job']);b.validate(prior)
    b.validate_release(fixture['release'],fixture['ref']);b.validate_manifest(fixture['manifest'])
    rejected=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):rejected.append(name)
        else:raise AssertionError('Accepted admission fault '+name)
    for object_name,key,value in (
      ('source_run','head_sha','0'*40),('source_run','run_attempt',2),('source_run','conclusion','failure'),
      ('source_job','run_id',0),('source_job','name','other'),('source_job','status','in_progress'),
      ('physical_run','head_sha','0'*40),('physical_run','conclusion','failure'),('physical_run','run_attempt',2),
      ('physical_job','id',0),('physical_job','run_id',0),('physical_job','conclusion','failure')):
        x=copy.deepcopy(fixture);x[object_name][key]=value
        fn=(lambda x=x:c.validate_source_proof(x['source_run'],x['source_job'],result,log))if object_name.startswith('source_')else(lambda x=x:b.validate_run(x['physical_run'],x['physical_job']))
        reject(object_name+'.'+key,fn)
    for label,changed in (('log_truncated',log[:-1]),('log_byte_changed',b'!'+log[1:])):
        reject(label,lambda changed=changed:c.validate_source_proof(fixture['source_run'],fixture['source_job'],result,changed))
    for label,key,value in (('result_source','source_head','0'*40),('result_fault_omitted','faults',result['faults'][:-1]),
                            ('native_claim','native_geometry_proved',True),('electrical_claim','electrical_accepted',True)):
        changed=copy.deepcopy(result);changed[key]=value
        reject(label,lambda changed=changed:c.validate_source_proof(fixture['source_run'],fixture['source_job'],changed,log))
    for label,which,key,value in (
      ('release_source','release','target_commitish','0'*40),('release_id','release','id',0),
      ('release_tag','release','tag_name','other'),('draft_release','release','draft',True)):
        x=copy.deepcopy(fixture);x[which][key]=value
        reject(label,lambda x=x:b.validate_release(x['release'],x['ref']))
    x=copy.deepcopy(fixture);x['ref']['object']['sha']='0'*40
    reject('tag_source',lambda:b.validate_release(x['release'],x['ref']))
    x=copy.deepcopy(fixture);x['release']['assets'][0]['digest']='sha256:'+'0'*64
    reject('asset_digest',lambda:b.validate_release(x['release'],x['ref']))
    x=copy.deepcopy(fixture);x['release']['assets'].pop()
    reject('asset_missing',lambda:b.validate_release(x['release'],x['ref']))
    x=copy.deepcopy(fixture);x['release']['assets'][0]['size']+=1
    reject('asset_size',lambda:b.validate_release(x['release'],x['ref']))
    # Genuine prerequisite gate mutations from the full authenticated old physical result.
    changes=(
       ('source',lambda x:x.update(source_head='0'*40)),
       ('electrical_claim',lambda x:x.update(electrical_accepted=True)),
       ('omitted_output',lambda x:x['outputs'].pop(next(iter(x['outputs'])))),
       ('DRC_marker',lambda x:x['variants']['p']['steps']['drc']['measurement'].update(markers=1)),
       ('deep_devices',lambda x:x['variants']['p']['steps']['deep_lvs']['audit']['circuits'][0].update(layout_devices_recursive=333)),
       ('flat_simplified',lambda x:x['variants']['n']['steps']['flat_lvs']['audit']['circuits'][0].update(schematic_devices_recursive=333)),
       ('terminal_count',lambda x:x['variants']['p']['wires']['graph'].update(native_terminal_count=1009)),
       ('body_count',lambda x:x['variants']['n']['wires']['anchors']['counts'].update(body_terminals=325)),
       ('missing_fault',lambda x:x['variants']['p']['wires']['anchors']['negative_controls'].pop()),
       ('old_circuit',lambda x:x['variants']['n']['generation']['sole_device_dimension_delta'].update(new_L_um=32)))
    for name,change in changes:
        x=copy.deepcopy(prior);change(x);reject('physical_'+name,lambda x=x:b.validate(x))
    assert len(rejected)==36
    for name,key,value in (('format','format','wrong'),('stem','stem','other'),('root','source_directory','other'),
                           ('size','bytes',1),('whole_digest','sha256','0'*64),('parts','parts',[])):
        x=copy.deepcopy(fixture['manifest']);x[key]=value
        reject('manifest_'+name,lambda x=x:b.validate_manifest(x))
    assert len(rejected)==42
    # Exercise the actual derived authorization function without a native process.
    actual_auth=dict(native_generation_authorized=True,simulation_authorized=False,extraction_authorized=False)
    with mock.patch.object(Path,'read_text',return_value='ID=ubuntu\nVERSION_ID="22.04"\n'),mock.patch.dict(os.environ,{'ImageOS':'ubuntu22'}):
        c.authorize(actual_auth)
        for key,value in (('native_generation_authorized',False),('simulation_authorized',True),('extraction_authorized',True)):
            x=dict(actual_auth);x[key]=value;reject('authorization_'+key,lambda x=x:c.authorize(x))
    for label,text,image in (('wrong_os','ID=ubuntu\nVERSION_ID="24.04"\n','ubuntu24'),
                             ('wrong_distro','ID=debian\nVERSION_ID="22.04"\n','ubuntu22'),
                             ('wrong_image','ID=ubuntu\nVERSION_ID="22.04"\n','ubuntu24')):
        with mock.patch.object(Path,'read_text',return_value=text),mock.patch.dict(os.environ,{'ImageOS':image}):
            reject(label,lambda:c.authorize(actual_auth))
    # Every actual integration seam remains required by the reversible source contract.
    original=list(c.EDITS)
    for i in range(len(original)):
        with mock.patch.object(c,'EDITS',original[:i]+original[i+1:]):
            reject('omitted_native_seam_'+str(i),c.derive)
    with mock.patch.object(c,'EDITS',[(original[0][0]+'ambiguous',original[0][1]),*original[1:]]):
        reject('changed_native_seam_source',c.derive)
    assert len(rejected)==56
    archive=b.archive_controls();assert len(archive['rejected'])==13
    assert archive['inherited_parts_controls']['negative_controls']==6
    finalization=[]
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);path=root/'saved';path.write_bytes(b'immutable original')
        proof=dict(directory=str(root),inventory=dict(files={'saved':dict(bytes=path.stat().st_size,sha256=b.sha(path))}))
        good={'baseline_restoration':proof};c.finalize_baseline(good)
        assert good['original_baseline_byte_unchanged']
        for name in ('changed','extra','missing'):
            path.write_bytes(b'immutable original')
            if name=='changed':path.write_bytes(b'mutated')
            elif name=='extra':(root/'extra').write_bytes(b'extra')
            else:path.unlink()
            report=dict(status='RUNNING',baseline_restoration=proof)
            c.finalize_baseline(report)
            assert report['status']=='FAIL_OR_ERROR'and report['original_baseline_byte_unchanged']is False
            assert report['baseline_immutability_error']and report['baseline_immutability_traceback']
            assert json.loads(json.dumps(report))['original_baseline_byte_unchanged']is False
            finalization.append(dict(name=name,rejected_and_report_retained=True))
            if (root/'extra').exists():(root/'extra').unlink()
    assert len(finalization)==3
    return dict(status='PASS_AVSS18_ADMISSION56_ARCHIVE13_PART6_NO_NATIVE',
                positive_physical_and_source_prerequisites=True,authorization_positive_mock_only=True,
                rejected=rejected,archive=archive,baseline_finalization_faults=finalization,native_executed=False,
                actual_material_controls_require_hosted_Pya=True)
