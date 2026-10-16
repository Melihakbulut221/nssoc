#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read exact failed CRIU logs in cloud; never rerun a process to guess its error."""
import json,os
from pathlib import Path
import cloud_tx_input_driver as physical
from run_cloud_tx_layout_repair import sha
ROOT=physical.ROOT;OUT=ROOT/'cloud-checkpoint-restore-diagnosis'
SOURCE=dict(run=38888180478,group='checkpoint-state-probe',root='cloud-checkpoint-state-probe',bytes=2374573,sha='77c7ef4ba07cc545b0bde16e209a475a62746462802c444942d1f5e26330c714',summary='54565d942dd6c273a4787fb3beca157aa000e0b7e9cb5e0de25c16dc196151a3')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,simulator_checkpoint_proven=False)
    try:
        physical.OUT=OUT;source,prior=physical.restore(SOURCE)
        assert prior['status']=='FAIL_OR_ERROR' and prior['error']=="RuntimeError('Default-directory restore failed')"
        logs={}
        for name in ['kernel.log','criu-version.log','docker-version.log','kernel-capabilities.log','restore.log','restore-native-log.log']:
            p=source/name;assert sha(p)==prior['outputs'][name] and p.stat().st_size<100000
            logs[name]=dict(sha256=sha(p),text=p.read_text(errors='strict'))
        result.update(status='COMPLETE_EXACT_FAILED_CHECKPOINT_DIAGNOSIS_NOT_RESTORE_ACCEPTANCE',logs=logs,original_error=prior['error'],checkpoint_prefix=prior['checkpoint_prefix'],criu_build=prior['criu_build'])
        for name,row in logs.items():print(name+'\n'+row['text'],flush=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
