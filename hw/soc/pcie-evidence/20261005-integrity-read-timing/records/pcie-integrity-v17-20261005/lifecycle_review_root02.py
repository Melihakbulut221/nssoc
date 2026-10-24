# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Review the exact V17 continuation and exercise supersession on an owned child."""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time

R=Path.cwd()
B=R/'hw/soc/out/pcie-integrity-v17-20261005'
A=B.parent/'pcie-integrity-v16-20261005'
sys.path.insert(0,str(R/'scripts'))


def pin(path):
    path=Path(path)
    with path.open('rb') as f:
        return {'bytes':path.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}


freeze=json.loads((B/'continuation-review-freeze02.json').read_text())
for name,p in freeze.items():assert pin(B/name)==p
life_path=R/'scripts/characterize_pcie_clock_trim_stream_v2.py'
assert pin(life_path)['sha256']=='39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886'
spec=importlib.util.spec_from_file_location('peer_lifecycle',life_path)
life=importlib.util.module_from_spec(spec);spec.loader.exec_module(life)
old=ast.parse((A/'continue_after_controls_v2.py').read_text())
new=ast.parse((B/'continue_after_controls_v2.py').read_text())
funcs=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef)}
for name in ('stage','explicit_stop','verify_sources','pin'):
    assert funcs(old)[name]==funcs(new)[name],name
text=(B/'continue_after_controls_v2.py').read_text()
assert text.index("lifecycle=policy['lifecycle_peer']")<text.index("stage('supersede_v16'")
assert text.index("'39 passed, 2 deselected'")<text.index("stage('supersede_v16'")
assert "owner.check()\nexcept BaseException" in text
assert "if explicit_stop():record.update(status='CANCELLED_RETAINED'" in text
assert '39 passed, 2 deselected' in (B/'controls01.log').read_text()
source_peer=json.loads((B/'source-only-peer-rx.json').read_text())
assert source_peer['status'].startswith('PASS_V17_') and not source_peer['findings']
for name,p in json.loads((B/'source-freeze.json').read_text())['files'].items():assert pin(R/name)==p
guard_controls=json.loads((B/'identity-guard-controls02.json').read_text())
assert guard_controls['status']=='PASS_READ_ONLY_REAL_PROCESS_IDENTITY_GUARDS'
assert guard_controls['source']==pin(B/'supersede_v16_after_validation_v2.py')
assert guard_controls['guard_record']==pin(B/'supersession-identity-guards02.json')
guards=json.loads((B/'supersession-identity-guards02.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==guards['boot_id']
source=(B/'supersede_v16_after_validation_v2.py').read_text()
assert source.index("gate=json.loads((B/'lifecycle-peer-pin02.json')")<source.index("save()\nstop(")
tree=ast.parse(source)
methods=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('same','members','stop')]
assert len(methods)==3
record={'stops':[]}
ns={'Path':Path,'life':life,'guards':copy.deepcopy(guards),'hashlib':hashlib,
    'os':os,'signal':signal,'time':time,'record':record,
    'save':lambda:life.atomic(B/'root-owned-stop-control02.json',record)}
exec(compile(ast.Module(body=methods,type_ignores=[]),str(B/'supersede_v16_after_validation_v2.py'),'exec'),ns)
for expected in guards['jobs'].values():assert ns['same'](expected)
# Only this peer's newly created process receives a signal. Production V16,
# V17 and PLL processes are read-only during the review.
process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True)
checks=[]
try:
    time.sleep(.03)
    expected=life.process_identity(process.pid)
    raw=Path(f'/proc/{process.pid}/cmdline').read_bytes()
    expected.update(commandline_bytes=len(raw),commandline_sha256=hashlib.sha256(raw).hexdigest())
    assert expected['process_group']==process.pid
    bad_start={**expected,'start_ticks':str(int(expected['start_ticks'])+1)}
    bad_group={**expected,'process_group':expected['process_group']+1000000}
    bad_size={**expected,'commandline_bytes':expected['commandline_bytes']+1}
    bad_hash={**expected,'commandline_sha256':'0'*64}
    for name,bad in [('wrong_start',bad_start),('wrong_group',bad_group),('wrong_command_size',bad_size),('wrong_command_hash',bad_hash)]:
        try:
            ns['stop'](bad,bad['process_group'],'root-owned-negative')
        except AssertionError:
            pass
        else:
            raise AssertionError(name+' accepted')
        assert process.poll() is None and not record['stops']
        checks.append({'case':name,'result':'REFUSED_WITH_REAL_CHILD_STILL_ALIVE'})
    ns['guards']['boot_id']='wrong-boot'
    try:
        ns['stop'](expected,expected['process_group'],'root-owned-negative')
    except AssertionError:
        pass
    else:
        raise AssertionError('wrong boot accepted')
    assert process.poll() is None and not record['stops']
    checks.append({'case':'wrong_boot','result':'REFUSED_WITH_REAL_CHILD_STILL_ALIVE'})
    ns['guards']['boot_id']=guards['boot_id']
    ns['stop'](expected,expected['process_group'],'root-owned-valid-stop')
    assert process.wait(timeout=3)==-signal.SIGTERM
    assert len(record['stops'])==1 and not record['stops'][0]['remaining_exact_identities']
    checks.append({'case':'exact_owned_group','result':'ACTUAL_SIGTERM_AND_CLOSED'})
finally:
    if process.poll() is None:
        os.killpg(process.pid,signal.SIGKILL)
    process.wait(timeout=3)
for expected in guards['jobs'].values():assert ns['same'](expected)
out={'status':'PASS_V17_CONTINUATION_AND_GUARDED_SUPERSESSION_SOURCE_PEER',
     'findings':[],'method':pin(__file__),'reviewed_freeze':pin(B/'continuation-review-freeze02.json'),
     'reviewed_files':freeze,'source_peer':pin(B/'source-only-peer-rx.json'),
     'completed_controls':pin(B/'controls01.log'),
     'inherited_owner_stage_functions_identical':['pin','stage','verify_sources','explicit_stop'],
     'guard_controls':pin(B/'identity-guard-controls02.json'),
     'additional_real_owned_child_checks':checks,
     'owned_stop_receipt':pin(B/'root-owned-stop-control02.json'),
     'production_identities_read_only_and_still_matching':guards['jobs'],
     'review':['Every production signal gated by completed39selected controls, exact source/lifecycle peers, unchanged boot and PID/start/group/command bytes.',
               'Old idle V16 continuation stopped before its incomplete controls/probe. Incomplete V16 remains incomplete; this is author supersession of a validated compiler fix.',
               'Controller preserves tested ProcessOwner failure/cancellation handling and final cancellation check. No PLL identity appears among signal targets.',
               'Final policy02 may derive from frozen policy01 only by V2 method/status paths and this exact lifecycle peer binding. Native mapping/STA still use original limits.'],
     'scope':'Source review and six actual owned-child lifecycle checks only; no V16 production job stopped by reviewer and no native timing acceptance.'}
(B/'continuation-source-only-peer-root02.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['status'])
