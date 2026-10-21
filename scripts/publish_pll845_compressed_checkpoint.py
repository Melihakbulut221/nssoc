#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Publish complete native checkpoints with bounded temporary compressed staging."""
import hashlib,json,os
from pathlib import Path
from cloud_streamed_native_archive import stream_pack
from cloud_pll845_compressed_disk import source_contract
from publish_cloud_results import result_tag
from migrate_outputs_to_cloud import publish
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pending_checkpoint(report,stage,run,attempt,native_outcome):
    owned=report.get('run_id')==run and report.get('run_attempt')==attempt and report.get('stage')==stage
    return owned and native_outcome=='success'and report.get('status')=='SAVED_ACTUAL_PHYSICAL845_ONE_US_PROCESS_NOT_FULL_CAPTURE_OR_ACCEPTANCE'and report.get('checkpoint_saved')is True
def controls():
    import copy
    r=dict(run_id='123',run_attempt='1',stage='initial',status='SAVED_ACTUAL_PHYSICAL845_ONE_US_PROCESS_NOT_FULL_CAPTURE_OR_ACCEPTANCE',checkpoint_saved=True)
    assert pending_checkpoint(r,'initial','123','1','success')
    for key,value in [('run_id','122'),('run_attempt','2'),('stage','continuation'),('status','FAIL'),('checkpoint_saved',False)]:
        wrong=copy.deepcopy(r);wrong[key]=value
        assert not pending_checkpoint(wrong,'initial','123','1','success')
    assert not pending_checkpoint(r,'initial','123','1','failure')
    return dict(only_owned_successful_saved_process_can_continue=True,rejected_cases=6)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    source_contract(Path(__file__).resolve().parents[1])
    stage=os.environ['CAPSULE_STAGE'];assert stage in ('initial','continuation')
    run=os.environ['GITHUB_RUN_ID'];attempt=os.environ['GITHUB_RUN_ATTEMPT'];outcome=os.environ['NATIVE_OUTCOME']
    group='pll845-native-acquisition-'+stage;stem=f'{group}-{run}-{attempt}';tag=result_tag(group,os.environ)
    root=Path('cloud-pll845-native-acquisition').resolve();root.mkdir(exist_ok=True)
    report_path=root/'result.json'
    if not report_path.exists():report_path.write_text('{"status":"FAIL_MISSING_REPORT","full_phy_accepted":false}\n')
    report=json.loads(report_path.read_text())
    owned=report.get('run_id')==run and report.get('run_attempt')==attempt and report.get('stage')==stage
    if not owned:
        (root/'unclaimed-source-report.json').write_bytes(report_path.read_bytes())
        report=dict(status='FAIL_BEFORE_CURRENT_NATIVE_REPORT',native_outcome=outcome,run_id=run,run_attempt=attempt,stage=stage,checkpoint_saved=False,full_phy_accepted=False,reason='Source report does not prove current native progress.')
        report_path.write_text(json.dumps(report,indent=2)+'\n')
    summary=Path(stem+'.summary.json');summary.write_bytes(report_path.read_bytes())
    manifest=stream_pack(root,stem,Path.cwd(),lambda p:publish(p,tag))
    parts=Path(stem+'.parts.json')
    # Publish the descriptor only after every native byte is hosted and verified.
    summary_receipt=publish(summary,tag);parts_receipt=publish(parts,tag)
    assert summary_receipt['sha256']==digest(summary)and parts_receipt['sha256']==digest(parts)
    checkpoint=dict(run=run,attempt=attempt,stage=stage,summary_sha256=digest(summary),parts_sha256=digest(parts))
    pending=pending_checkpoint(report,stage,run,attempt,outcome)
    with open(os.environ['GITHUB_OUTPUT'],'a')as f:
        f.write('pending='+str(pending).lower()+'\n')
        f.write('checkpoint='+json.dumps(checkpoint,separators=(',',':'))+'\n')
    print(json.dumps(dict(checkpoint=checkpoint,pending=pending,status=report.get('status'),native_source_retained=True,archive_staging_limit=manifest['part_limit_bytes'])))
if __name__=='__main__':
    import sys
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if '--controls'in sys.argv:print(json.dumps(controls()))
    else:main()
