# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent read-only exact observer recovery source review; no launch."""
from pathlib import Path
import ast
import hashlib
import json
import os

C = Path(__file__).resolve().parent
B = C.parent
OLD = B / 'repair03-continuation01'


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


freeze = json.loads((C / 'source-freeze.json').read_text())
assert pin(C / 'source-freeze.json') == dict(bytes=8471, sha256='2c01b38789b040c503df849fc0291dfb59c83d4adba147132543d665a0129dcc')
assert len(freeze['inputs']) == 35
assert freeze['inputs'] == {p: pin(p) for p in freeze['inputs']}
new, old = (C / 'run.py').read_bytes(), (OLD / 'run.py').read_bytes()
assert new == old and hashlib.sha256(new).hexdigest() == '658728feab98e70f02276f97c97d2af8b0a413154bc21936c26aff7b46a07b27'
old_peer = OLD / 'source-only-peer-vco.json'
assert pin(old_peer) == dict(bytes=15814, sha256='4128f1cfe8d47c06760db7a5ed5e7e4a0b06be9aed9bdbcea20f87e50b361315')
m = json.loads((C / 'manifest.json').read_text())
om = json.loads((OLD / 'manifest.json').read_text())
assert m['inputs'] == {p: pin(p) for p in m['inputs']}
assert m['route_inputs'] == {p: pin(p) for p in m['route_inputs']}
assert len(m['route_inputs']) == 25
assert {k: v for k, v in m.items() if k not in {'utc', 'inputs', 'resume_from', 'fresh_receipt_directory'}} == {k: v for k, v in om.items() if k not in {'utc', 'inputs'}}
assert all(m['inputs'][p] == h for p, h in om['inputs'].items())
assert m['resume_from'] == str(OLD) and m['fresh_receipt_directory'] == str(C)
old_result = json.loads((OLD / 'result.json').read_text())
assert old_result['status'] == 'WAITING_EXISTING_EXACT_TX03_DRT01' and old_result['stages'] == []
assert not Path('/dev/shm/nssoc-tx-path-v4-repair03-detailed-rc-01').exists()
assert not (C / 'active-controller.json').exists() and not (C / 'result.json').exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == m['boot_id']


def observed(pid):
    p = Path('/proc') / str(pid)
    if not p.exists():
        return None
    try:
        s = (p / 'stat').read_text().rsplit(')', 1)[1].split()
        argv = (p / 'cmdline').read_bytes().split(b'\0')[:-1]
    except FileNotFoundError:
        return None
    return dict(pid=pid, start_ticks=s[19], state=s[0], process_group=int(s[2]),
                affinity=sorted(os.sched_getaffinity(pid)), argv=[v.decode() for v in argv])


gone = observed(82234)
assert gone is None or gone['start_ticks'] != '957118'
live = {}
for key in ['route_owner', 'route_native']:
    expected = m[key]
    actual = observed(expected['pid'])
    assert actual and actual['state'] != 'Z' and actual['start_ticks'] == expected['start_ticks']
    assert actual['affinity'] == [4] and ' '.join(actual['argv']) + ' ' == expected['command']
    live[key] = actual
launch = (C / 'launch_detached.py').read_text()
tree = ast.parse(launch)
calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
popens = [n for n in calls if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
          and n.func.value.id == 'subprocess' and n.func.attr == 'Popen']
assert len(popens) == 1
kw = {k.arg: ast.dump(k.value, include_attributes=False) for k in popens[0].keywords}
assert kw['start_new_session'] == 'Constant(value=True)' and kw['close_fds'] == 'Constant(value=True)'
assert kw['stdin'] == "Attribute(value=Name(id='subprocess', ctx=Load()), attr='DEVNULL', ctx=Load())"
assert kw['stdout'] == "Name(id='log', ctx=Load())"
assert kw['stderr'] == "Attribute(value=Name(id='subprocess', ctx=Load()), attr='STDOUT', ctx=Load())"
assert not any(isinstance(n.func, ast.Attribute) and n.func.attr in {'kill', 'killpg', 'terminate', 'send_signal'} for n in calls)
for literal in [".open('xb')", "m['boot_id']", "current['argv']==[s.encode() for s in cmd[3:]]",
                "current['affinity']==[4]", "'active-controller.tmp'", "temp.replace(B/'active-controller.json')"]:
    assert literal in launch
result = dict(status='PASS_EXACT_TX03_OBSERVER_RESUME_SOURCE', freeze=pin(C / 'source-freeze.json'), findings=[],
              method=pin(Path(__file__)), prior_independent_peer=pin(old_peer),
              all35_freeze_inputs_rehashed=True, manifest_inputs_rehashed=len(m['inputs']), route_inputs_rehashed=25,
              complete_controller_byte_equality=True, manifest_changes_only_receipt_directory_and_recovery_provenance=True,
              old_controller_observed=gone, exact_live_route=live, boot_id=boot,
              inherited_terminal_owner_and_resource_guards_unchanged=True,
              startup_deadline_only_seconds=5, healthy_route_elapsed_watchdog=None,
              detached_observer_only=True, stdin_closed_and_log_not_tool_pipe=True,
              no_existing_route_signal_calls=True, prior_dependent_stage_count=0,
              no_native_or_controller_launched_by_reviewer=True,
              caveat='Root must revalidate exact birth/argv/boot and confirm the new observer survives a later tool call; source review does not execute launch.')
(C / 'source-only-peer.json').write_text(json.dumps(result, indent=2) + '\n')
print(result['status'], pin(C / 'source-only-peer.json'), flush=True)
