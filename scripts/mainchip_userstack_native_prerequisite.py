#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate actual harmless GDB qualification before any chip admission."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RUN=40174045028
HEAD='814d6ddbbc636022ae4df51f543cf7d192a0992c'
SHA='b4d97688a9f8b6062fbe847eb1bb7865d27abdb0c82eed395e9adb3ba66f7aff'
IDS=['positive-20','all-lwps','container-root','initialization-canary','debuginfod-canary','permission-canaries',
'wrong-starttime','wrong-executable','wrong-container','pid-replacement','already-traced','timeout-cleanup',
'namespace-drift','during-stop-rebind','error-finally-detach','leader-descendant','detach-unproved','partial-19',
'oversize-or-time','unknown-unwind','wrong-capsule','original-rejection','material-mutation','failure-publication']
def validate(r,run,jobs):
    assert run['id']==RUN and run['head_sha']==HEAD and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='success'
    assert run['path']=='.github/workflows/mainchip-userstack-fixture-cloud.yml'
    actual=[j for j in jobs['jobs']if j['name']=='harmless-fixture']
    assert len(actual)==1 and actual[0]['id']==121110808652 and actual[0]['conclusion']=='success'
    assert actual[0]['head_sha']==HEAD
    assert r['status']=='PASS_24_HARMLESS_USERSTACK_CONTROLS_ONLY'and r['sources_unchanged']is True
    assert [c['id']for c in r['controls']]==IDS
    assert r['controls'][0]['evidence']['samples']==20
    assert r['loaded_executable_binding_controls']['positive_spellings']==3
    assert len(r['loaded_executable_binding_controls']['rejected'])==8
    assert r['actual_pidfd_exit_rejected']is True
    assert r['gdb']['sha256']=='3832cc070ae1716e322105d3b39fb398695e5f031c9d39224cf227a8c2b889f6'
    assert r['complete_chip_admission_unexecuted']is True and r['live_container_binding_unexecuted']is True
    return True
def verify():
    raw=(ROOT/'docs/evidence/mainchip-userstack-fixture-native-result-20261025.json').read_bytes()
    assert len(raw)==9732 and hashlib.sha256(raw).hexdigest()==SHA
    def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
    r=json.loads(raw);run=api('actions/runs/'+str(RUN));jobs=api('actions/runs/'+str(RUN)+'/jobs?per_page=100')
    validate(r,run,jobs)
    return dict(run=RUN,source=HEAD,result_sha256=SHA,actual_controls=24,actual_samples=20,
        live_chip_binding_proven=False)
