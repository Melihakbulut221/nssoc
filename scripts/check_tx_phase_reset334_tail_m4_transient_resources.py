#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted fixtures for exact early resource and always-preservation template programs."""
import ast,contextlib,copy,datetime,hashlib,io,json,os,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import cloud_tx_phase_reset334_tail_m4_transient as c
TEMPLATE='.github/workflow-templates/tx-phase-reset334-tail-m4-transient-cloud.yml'
NAME='native-resource-before-dependencies.json'

def program(text,step,marker):
    head='      - name: '+step+'\n'
    assert text.count(head)==1
    block=text.split(head,1)[1].split('      - ',1)[0]
    begin="          python3 - <<'"+marker+"'\n"
    assert block.count(begin)==1
    body=block.split(begin,1)[1].split('          '+marker+'\n',1)[0]
    assert all(line.startswith('          ')for line in body.splitlines())
    value='\n'.join(line[10:]for line in body.splitlines())+'\n';ast.parse(value)
    return value

def controls():
    m=c.methods();assert m['source_controls_authorized']is True
    text=(c.ROOT/TEMPLATE).read_text()
    observe=program(text,'Record native runner resources before dependency installation','RESOURCE')
    preserve=program(text,'Preserve complete result including rejected capture or partial process','PY')
    assert text.index('  exact318-p-high-native:')<text.index('      - name: Record native runner resources')
    assert text.index('      - name: Passed source controls and read-only exact reserved release')<text.index('      - name: Record native runner resources')<text.index('      - name: Install original pinned portable runtime')
    env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY='Melihakbulut221/nssoc',GITHUB_RUN_ID='17',
      GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40,PROOF_STAGE='initial',ImageOS='ubuntu24',
      ImageVersion='synthetic-image',ImageRelease='synthetic-release',RUNNER_OS='Linux',RUNNER_ARCH='X64',RUNNER_NAME='synthetic-runner')
    positives=[];rejected=[];cwd=Path.cwd()
    try:
        with tempfile.TemporaryDirectory(prefix='tail-m4-resource-fixtures-')as folder:
            base=Path(folder);os.chdir(base);temporary=base/'temp';temporary.mkdir()
            env['RUNNER_TEMP']=str(temporary)
            original_read=Path.read_text
            def read(path,*args,**kw):
                if str(path)=='/proc/meminfo':return 'MemTotal: 16384000 kB\nMemAvailable: 12000000 kB\nMemFree: 10000000 kB\nOther: 9 kB\n'
                return original_read(path,*args,**kw)
            saved=None
            for free in (80*1024**3,8*1024**3):
                with mock.patch.dict(os.environ,env),mock.patch.object(Path,'read_text',read),\
                  mock.patch('shutil.disk_usage',return_value=SimpleNamespace(total=100*1024**3,used=100*1024**3-free,free=free)),\
                  mock.patch.object(os,'cpu_count',return_value=8),mock.patch.object(os,'sched_getaffinity',return_value={2,4}),\
                  contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(observe,'actual-native-resource-program','exec'),{})
                path=temporary/NAME;saved=path.read_bytes();r=json.loads(saved)
                assert r['disk']['free_bytes']==free and r['disk']['total_bytes']==100*1024**3
                assert r['ram_bytes']==dict(MemTotal=16384000*1024,MemAvailable=12000000*1024,MemFree=10000000*1024)
                assert r['cpu']==dict(logical_count=8,available_affinity=[2,4])
                assert r['runner']=={k:env[k]for k in ('ImageOS','ImageVersion','ImageRelease','RUNNER_OS','RUNNER_ARCH','RUNNER_NAME')}
                assert datetime.datetime.fromisoformat(r['observed_at_utc']).utcoffset()==datetime.timedelta(0)
                assert r['original_guards_unchanged']==dict(prelaunch_free_bytes=72*1024**3,checkpoint_reserve_bytes=20*1024**3)
                assert not r['provisioning_performed']and not r['cleanup_performed']and not r['resource_guarantee']
                assert not(base/'cloud-tx-phase-reset334-tail-m4-transient-native-initial-p-initial-high').exists()
                positives.append('actual_observation_above_guard'if free>72*1024**3 else'actual_observation_below_guard_without_relaxing_later_guard')
                path.unlink()
            group='cloud-tx-phase-reset334-tail-m4-transient-native-initial-p-initial-high';root=base/group;root.mkdir()
            native=dict(status='REJECTED_PHYSICAL334_THREE_MODEL_ORIGINAL_LOADED_GATES',full_capture=True,
                electrical_screen_passed=False,original17_HBT_rejection=True,outputs={'native.log':'b'*64})
            (root/'result.json').write_text(json.dumps(native));(temporary/NAME).write_bytes(saved)
            def run_preserve():
                with mock.patch.dict(os.environ,env),contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(preserve,'actual-native-failure-preservation-program','exec'),{})
            run_preserve();actual=json.loads((root/'result.json').read_bytes())
            assert(root/NAME).read_bytes()==saved and actual['outputs']==dict(native['outputs'],**{NAME:hashlib.sha256(saved).hexdigest()})
            assert {k:actual[k]for k in native if k!='outputs'}=={k:v for k,v in native.items()if k!='outputs'}
            assert actual['early_resources']==dict(status='OBSERVED_BEFORE_DEPENDENCIES',path=NAME,sha256=hashlib.sha256(saved).hexdigest())
            positives.append('actual_failed_native_result_inventory_and_observation_preserved')
            (root/NAME).unlink();(root/'result.json').unlink();(temporary/NAME).unlink()
            run_preserve();actual=json.loads((root/'result.json').read_bytes())
            assert actual['status']=='FAIL_MISSING_NATIVE_RESULT'and actual['early_resources']['status']=='NOT_RECORDED'
            assert not(root/NAME).exists()and not actual['electrical_screen_passed']
            positives.append('actual_preflight_failure_preserved_without_fabricated_observation')
            for label,field,value in [('wrong_source','source_head','b'*40),('wrong_run','run_id',18),
                ('wrong_attempt','run_attempt',2),('wrong_stage','stage','cross'),('symlink_observation',None,None)]:
                (root/'result.json').write_text(json.dumps(native));payload=json.loads(saved)
                if field:payload[field]=value
                path=temporary/NAME;path.write_text(json.dumps(payload))
                if field is None:
                    target=temporary/'linked-source.json';path.rename(target);path.symlink_to(target)
                try:run_preserve()
                except AssertionError:rejected.append(label)
                else:raise AssertionError('Accepted '+label)
                assert json.loads((root/'result.json').read_bytes())==native and not(root/NAME).exists()
                path.unlink()
    finally:os.chdir(cwd)
    assert len(positives)==4 and len(rejected)==5
    return dict(status='PASS_ACTUAL_RESOURCE_PROGRAM_FIXTURES_ONLY',positive_cases=positives,rejected=rejected,
      actual_template_programs_executed=True,measured_resource_inputs_are_synthetic=True,
      native_executed=False,provisioning_performed=False)
if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
