#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Expose immutable native debugger diagnostics in cloud without local archives."""
import json,os
import cloud_tx_input_driver as physical
from run_cloud_tx_layout_repair import sha
ROOT=physical.ROOT;OUT=ROOT/'cloud-native-trap-report'
SOURCE={'run': 38904534884, 'group': 'native-cross-job-trap', 'root': 'cloud-native-cross-job-trap', 'bytes': 3637179, 'sha': '0a5627b5418b59358dbafcd6f751c28282e4135e556f2fbb78b8fb214a06bf43', 'summary': 'ff6b3c4c7b578cba83e6e8c54d982bb820dd3c33fc065154839acb49d619c127'}
assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
r=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],source=SOURCE)
try:
    physical.OUT=OUT;source,prior=physical.restore(SOURCE)
    assert prior['status']=='FAIL_OR_ERROR' and 'TimeoutExpired'in prior['error']
    names=['native-trap-gdb.log','stopped-kernel-status.log','restored-process-maps.txt','source-core-1.img-decoded.log','kernel-traps.log']
    logs={}
    for name in names:
        p=source/name;assert p.is_file()and sha(p)==prior['outputs'][name]
        text=p.read_text(errors='replace');assert len(text)<100000
        logs[name]=dict(sha256=sha(p),text=text)
    r.update(status='COMPLETE_IMMUTABLE_NATIVE_TRAP_LOG_REVIEW_NOT_ACCEPTANCE',logs=logs,source_error=prior['error'],destination_cpu=prior['destination_cpu'],ptrace_attachment=prior.get('ptrace_attachment'),retained_captures=prior['retained_captures'])
    assert all(sha(source/p)==v for p,v in prior['outputs'].items())
except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
finally:(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
