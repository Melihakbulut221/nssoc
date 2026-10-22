#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Publish only verified ordinary native bytes; incomplete/failed reports cannot resume."""
import json,os
from pathlib import Path
import cloud_pll845_sparse_io as storage
import cloud_logical_native_archive as logical
import cloud_streamed_native_archive as archive
import cloud_pll845_sparse_disk as disk
from publish_pll845_compressed_checkpoint import pending_checkpoint,controls as original_controls
from publish_cloud_results import result_tag
from migrate_outputs_to_cloud import publish
COMPLETE='COMPLETE_NATIVE845_PROCESS_REQUIRES_ORDINARY_FULL_CAPTURE_READER'
def ready(report,stage,run,attempt,outcome):
    owned=report.get('run_id')==run and report.get('run_attempt')==attempt and report.get('stage')==stage
    return bool(owned and outcome=='success'and report.get('status')==COMPLETE
        and report.get('native_complete')is True and report.get('native_exitcode')==0
        and report.get('full_capture')is False and report.get('full_capture_reader_pending')is True
        and report.get('prior_payload_unchanged')is True and report.get('protected_inputs_unchanged')is True
        and report.get('checkpoint_saved')is False and report.get('diagnostics')==[])
def controls():
    import copy
    r=dict(run_id='123',run_attempt='1',stage='initial',status=COMPLETE,native_complete=True,
        native_exitcode=0,full_capture=False,full_capture_reader_pending=True,
        prior_payload_unchanged=True,protected_inputs_unchanged=True,checkpoint_saved=False,diagnostics=[])
    assert ready(r,'initial','123','1','success')
    rejected=[]
    for key,value in [('run_id','124'),('run_attempt','2'),('stage','continuation'),('status','FAIL'),
        ('native_complete',False),('native_exitcode',1),('full_capture',True),
        ('full_capture_reader_pending',False),('prior_payload_unchanged',False),
        ('protected_inputs_unchanged',False),('checkpoint_saved',True),('diagnostics',['warning'])]:
        bad=copy.deepcopy(r);bad[key]=value
        assert not ready(bad,'initial','123','1','success');rejected.append(key)
    assert not ready(r,'initial','123','1','failure')
    return dict(original_pending=original_controls(),rejected_reader_claims=rejected+['failed-native-step'])
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    root=Path.cwd();disk.source_contract(root)
    stage=os.environ['CAPSULE_STAGE'];assert stage in ('initial','continuation')
    run=os.environ['GITHUB_RUN_ID'];attempt=os.environ['GITHUB_RUN_ATTEMPT'];outcome=os.environ['NATIVE_OUTCOME']
    group='pll845-native-acquisition-'+stage;stem=group+'-'+run+'-'+attempt;tag=result_tag(group,os.environ)
    out=root/'cloud-pll845-native-acquisition';out.mkdir(exist_ok=True)
    path=out/'result.json'
    if not path.exists():path.write_text('{"status":"FAIL_MISSING_REPORT","full_phy_accepted":false}\n')
    report=json.loads(path.read_text())
    owned=report.get('run_id')==run and report.get('run_attempt')==attempt and report.get('stage')==stage
    if not owned:
        (out/'unclaimed-source-report.json').write_bytes(path.read_bytes())
        report=dict(status='FAIL_BEFORE_CURRENT_NATIVE_REPORT',run_id=run,run_attempt=attempt,stage=stage,
            checkpoint_saved=False,full_capture=False,full_phy_accepted=False,native_outcome=outcome)
    pending=pending_checkpoint(report,stage,run,attempt,outcome)
    completed=ready(report,stage,run,attempt,outcome)
    assert storage.native_stopped(),'Never archive a live native process'
    normal=owned and report.get('logical_archive_valid')is not False and (out/storage.STATE).exists()
    if normal:
        methods=disk.source_contract(root)[1]
        assert report['method_hashes']==methods
        assert report['controller_sha256']==methods[disk.CONTROLLER]
        current=report['logical_storage_proof'];storage.sparse.source_contract(current)
        assert (out/storage.RAW).stat().st_size==current['bytes']
        assert current['sha256']==report['outputs'][storage.RAW]
        if pending:assert current==report['checkpoint_prefix']
        if completed:assert current==report['logical_capture']
        assert storage.state(out)['checkpoint']==report['source_checkpoint']
        member=storage.logical_member(out)
    else:
        # Keep every byte of a failed physical working file, explicitly labelled
        # unusable as a native waveform. Preserve its immutable source descriptor.
        pending=completed=False
        raw=out/storage.RAW
        if raw.exists():
            failure=raw.with_name(raw.name+'.sparse-working.NOT-A-WAVEFORM')
            assert not failure.exists();raw.rename(failure)
            report['failed_sparse_working_file']=str(failure.relative_to(out))
        report.update(status='FAIL_UNQUALIFIED_NATIVE_STORAGE_EVIDENCE',checkpoint_saved=False,
            full_capture=False,full_phy_accepted=False,native_outcome=outcome)
    path.write_text(json.dumps(report,indent=2)+'\n')
    summary=root/(stem+'.summary.json');summary.write_bytes(path.read_bytes())
    try:
        if normal:
            manifest=logical.stream_pack(out,stem,root,lambda p:publish(p,tag),member,storage.native_stopped)
            proof=manifest['verification']['logical_members'][storage.RAW]
            assert {k:proof[k]for k in storage.FIELDS}==current
        else:
            manifest=archive.stream_pack(out,stem,root,lambda p:publish(p,tag))
        parts=root/(stem+'.parts.json')
        # No ready/pending output until every archive byte and both descriptors
        # have a verified hosted identity.
        sr=publish(summary,tag);pr=publish(parts,tag)
        assert sr['sha256']==archive.sha(summary)and pr['sha256']==archive.sha(parts)
        descriptor=dict(run=run,attempt=attempt,stage=stage,summary_sha256=sr['sha256'],parts_sha256=pr['sha256'])
        with open(os.environ['GITHUB_OUTPUT'],'a')as f:
            f.write('pending='+str(pending).lower()+'\n')
            f.write('reader_ready='+str(completed).lower()+'\n')
            f.write('checkpoint='+json.dumps(descriptor,separators=(',',':'))+'\n')
        print(json.dumps(dict(status=report['status'],checkpoint=descriptor,pending=pending,
            reader_ready=completed,full_capture_accepted=False,original_source_retained=True)),flush=True)
    except BaseException as error:
        failure=root/(stem+'.publication-failure.json')
        failure.write_text(json.dumps(dict(error=repr(error),pending=False,reader_ready=False,
            summary=report,source_files_retained=True),indent=2)+'\n')
        publish(failure,tag)
        raise
if __name__=='__main__':
    import sys
    if '--controls'in sys.argv:print(json.dumps(controls()))
    else:main()
