# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent small recovery review: observe death without weakening signals."""
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
R=Path.cwd();B=R/'hw/soc/out/pcie-integrity-v17-20261005'
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_clock_trim_stream_v2 as life


def pin(path):
    path=Path(path)
    with path.open('rb') as f:return {'bytes':path.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}


freeze=json.loads((B/'continuation-review-freeze03.json').read_text())
for p,q in freeze.items():assert pin(B/p)==q
oldtext=(B/'supersede_v16_after_validation_v2.py').read_text()
newtext=(B/'complete_v16_supersession_v3.py').read_text()
oldnodes={n.name:n for n in ast.parse(oldtext).body if isinstance(n,ast.FunctionDef)}
newnodes={n.name:n for n in ast.parse(newtext).body if isinstance(n,ast.FunctionDef)}
for name in ('same','members'):
    assert ast.dump(oldnodes[name],include_attributes=False)==ast.dump(newnodes[name],include_attributes=False)
expected=ast.get_source_segment(oldtext,oldnodes['stop'])
for before,after in [
    ("any(same(x) for x in row['members_before'])","any(alive(x) for x in row['members_before'])"),
    ("[x for x in row['members_before'] if same(x)]","[x for x in row['members_before'] if alive(x)]"),
    ("any(same(x) for x in remaining)","any(alive(x) for x in remaining)")]:expected=expected.replace(before,after)
assert ast.dump(ast.parse(expected).body[0],include_attributes=False)==ast.dump(newnodes['stop'],include_attributes=False)
assert not any(isinstance(n,ast.Attribute) and n.attr in ('kill','killpg','read_bytes') for n in ast.walk(newnodes['alive']))
prior_controller=(B/'continue_after_controls_v2.py').read_text()
expected_controller=prior_controller.replace('continuation-status02','continuation-status03').replace('continuation-policy02','continuation-policy03').replace('continuation-owner02','continuation-owner03').replace('lifecycle-peer-pin02','lifecycle-peer-pin03').replace("stage('supersede_v16',[sys.executable,str(B/'supersede_v16_after_validation_v2.py')])","stage('complete_supersession_v3',[sys.executable,str(B/'complete_v16_supersession_v3.py')])")
assert expected_controller==(B/'continue_after_controls_v3.py').read_text()
assert '39 passed, 2 deselected' in (B/'controls01.log').read_text()
for name,p in json.loads((B/'source-freeze.json').read_text())['files'].items():assert pin(R/name)==p
guards=json.loads((B/'supersession-identity-guards02.json').read_text())
record={'stops':[]}
ns={'Path':Path,'life':life,'guards':copy.deepcopy(guards),'hashlib':hashlib,'os':os,'signal':signal,'time':time,'record':record,'save':lambda:life.atomic(B/'root-owned-stop-control03.json',record)}
exec(compile(ast.Module(body=[newnodes[n] for n in ('same','alive','members','stop')],type_ignores=[]),str(B/'complete_v16_supersession_v3.py'),'exec'),ns)
prior=json.loads((B/'V16-supersession-receipt02.json').read_text())
closed=[e for row in prior['stops'] for e in row['members_before']]
assert len(closed)==7 and all(not ns['alive'](e) for e in closed)
assert ns['same'](guards['jobs']['incomplete_Icarus14_probe'])
assert json.loads((B/'continuation-status02.json').read_text())['status']=='FAILED_RETAINED'
p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True)
checks=[]
try:
    time.sleep(.03)
    expected=life.process_identity(p.pid);raw=Path(f'/proc/{p.pid}/cmdline').read_bytes()
    expected.update(commandline_bytes=len(raw),commandline_sha256=hashlib.sha256(raw).hexdigest())
    changed={**expected,'commandline_sha256':'0'*64}
    assert ns['alive'](changed)
    checks.append({'case':'observation_does_not_consult_commandline','result':'ACTUAL_OWNED_CHILD_LIVE'})
    try:ns['stop'](changed,expected['process_group'],'peer-wrong-command')
    except AssertionError:pass
    else:raise AssertionError('Wrong command accepted for signal')
    assert p.poll() is None and not record['stops']
    checks.append({'case':'signal_still_requires_exact_command','result':'REFUSED_CHILD_ALIVE'})
    ns['stop'](expected,expected['process_group'],'peer-exact-group')
    assert p.wait(timeout=3)==-signal.SIGTERM and not ns['alive'](expected)
    assert len(record['stops'])==1 and not record['stops'][0]['remaining_exact_identities']
    checks.append({'case':'actual_stop_and_observed_exit','result':'PASS_NO_COMMANDLINE_READ_IN_POLL'})
finally:
    if p.poll() is None:os.killpg(p.pid,signal.SIGKILL)
    p.wait(timeout=3)
assert all(not ns['alive'](e) for e in closed)
assert ns['same'](guards['jobs']['incomplete_Icarus14_probe'])
out={'status':'PASS_V17_V3_OBSERVATIONAL_EXIT_RACE_RECOVERY_PEER','findings':[],
     'method':pin(__file__),'reviewed_freeze':pin(B/'continuation-review-freeze03.json'),
     'reviewed_files':freeze,'guard_record':pin(B/'supersession-identity-guards02.json'),
     'prior_failure':pin(B/'continuation-status02.json'),'prior_partial_stop_receipt':pin(B/'V16-supersession-receipt02.json'),
     'source_peer':pin(B/'source-only-peer-rx.json'),'full_controls':pin(B/'controls01.log'),
     'prior_root_peer':pin(B/'continuation-source-only-peer-root02.json'),
     'same_and_members_identical_AST':True,'stop_changes_only_observational_polling':True,
     'controller_exact_path_and_first_recovery_stage_substitution':True,
     'already_closed_identities':len(closed),'only_remaining_signal_target':'original Icarus14 probe45372/start501497/group45372, exactboot andNULcmdline',
     'actual_new_owned_child_controls':checks,'toy_stop_receipt':pin(B/'root-owned-stop-control03.json'),
     'scope':'Prior V2failure retained. Strict signal identity unchanged; only death observation ignores transient commandline teardown. Production identities read-only during this peer. Finalpolicy03 may change only new03paths/pins/this exactpeer and prior-failure bindings; original native method/constraints unchanged. No native timing claim.'}
(B/'continuation-source-only-peer-root03.json').write_text(json.dumps(out,indent=2)+'\n')
print(out['status'])
