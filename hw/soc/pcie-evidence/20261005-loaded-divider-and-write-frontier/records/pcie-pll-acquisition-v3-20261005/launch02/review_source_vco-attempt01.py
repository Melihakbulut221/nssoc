# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-byte restart peer; no reviewed launcher/native execution."""
from pathlib import Path
import ast
import hashlib
import json
import os
import tarfile

B = Path(__file__).resolve().parent
ROOT = B.parents[4]
OLD = B.parent / 'launch01/launch_acquisition25.py'
P = B.parent / 'abrupt-stop-20261005'


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


policy = json.loads((B / 'policy.json').read_text())
assert pin(B / 'policy.json') == dict(bytes=2443, sha256='83b3e9b3af55e86536e9cb635a84dd9bbf3935fbaf7be2b2767d849ed6a7c8ab')
assert len(policy['pins']) == 10 and policy['pins'] == {p: pin(ROOT / p) for p in policy['pins']}
old = OLD.read_text()
new = (B / 'launch_acquisition25.py').read_text()
start = new.index('# Prior abruptly lost run is fully preserved, never resumed from initial OP.\n')
end = new.index("free=shutil.disk_usage('/dev/shm').free", start)
added = new[start:end]
inverse = (new[:start] + new[end:]).replace('nssoc-pll-acquisition-v3-step25-detached-02', 'nssoc-pll-acquisition-v3-step25-after-reboot-01').replace('pcie-pll-acquisition-v3-step25-detached02-20261005', 'pcie-pll-acquisition-v3-step25-after-reboot-20261005')
assert inverse == old
assert new.count('nssoc-pll-acquisition-v3-step25-detached-02') == 1
assert new.count('pcie-pll-acquisition-v3-step25-detached02-20261005') == 1
assert all(text in added for text in ["preservation['full_member_readback']", "preservation['all_originals_unchanged']",
                                    "oldrelease['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'", "len(oldrelease['assets'])==2",
                                    "observation['published_parts']==128", "not observation['solver_checkpoint_available']",
                                    "birth['start_ticks']", "'No duplicate native producer'"])
preservation = json.loads((P / 'preservation-validation.json').read_text())
archive = Path(preservation['archive']['path'])
assert pin(archive) == {k: preservation['archive'][k] for k in ['bytes', 'sha256']}
members = json.loads((P / 'members.json').read_text())
assert len(members) == preservation['archive']['members'] == 2466
seen = {}
with tarfile.open(archive, 'r|xz') as arc:
    for member in arc:
        assert member.isfile() and member.name not in seen
        seen[member.name] = dict(bytes=member.size, sha256=hashlib.file_digest(arc.extractfile(member), 'sha256').hexdigest())
assert seen == {n: {k: h[k] for k in ['bytes', 'sha256']} for n, h in members.items()}
release = json.loads((P / 'release01.json').read_text())
assert release['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS' and len(release['assets']) == 2
for row, asset in zip(release['files'], release['assets']):
    assert pin(row['path']) == {k: row[k] for k in ['bytes', 'sha256']} == {k: asset[k] for k in ['bytes', 'sha256']}
    assert asset['authenticated_roundtrip'] and asset['anonymous_roundtrip']
parts_file = P / 'reconciled-public-part-receipts.json'
assert pin(parts_file) == preservation['public_receipts']
parts = json.loads(parts_file.read_text())
assert parts['status'] == 'PASS_ALL128_IMMUTABLE_PART_RECEIPTS_BOUND_NOT_SOLVER_COMPLETION'
assert [p['index'] for p in parts['parts']] == list(range(128))
for part in parts['parts']:
    receipt = part['receipt']
    assert pin(receipt['path']) == {k: receipt[k] for k in ['bytes', 'sha256']}
    actual = json.loads(Path(receipt['path']).read_text())
    assert actual['status'] == 'PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'
    assert len(actual['assets']) == 1 and actual['assets'][0] == part['asset']
    assert part['asset']['authenticated_roundtrip'] and part['asset']['anonymous_roundtrip']
observation = json.loads((P / 'interruption-observation.json').read_text())
assert not observation['solver_checkpoint_available'] and not observation['native_terminal_record_available']
births = []
for birth in observation['missing_original_births']:
    p = Path('/proc') / str(birth['pid']) / 'stat'
    current = p.read_text().rsplit(')', 1)[1].split()[19] if p.exists() else None
    assert current != birth['start_ticks']
    births.append(dict(**birth, current_start_ticks=current))
producer = os.fsencode(str(ROOT / 'scripts/characterize_pcie_pll_acquisition_v3.py'))
live = []
for p in Path('/proc').iterdir():
    if p.name.isdigit():
        try:
            argv = (p / 'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, ProcessLookupError):
            continue
        if producer in argv:
            live.append(int(p.name))
assert not live
detach = (B / 'detach_launch.py').read_text()
tree = ast.parse(detach)
calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
popens = [n for n in calls if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
          and n.func.value.id == 'subprocess' and n.func.attr == 'Popen']
assert len(popens) == 1
kw = {k.arg: ast.dump(k.value, include_attributes=False) for k in popens[0].keywords}
assert kw['start_new_session'] == kw['close_fds'] == 'Constant(value=True)'
assert kw['stdin'] == "Attribute(value=Name(id='subprocess', ctx=Load()), attr='DEVNULL', ctx=Load())"
assert kw['stdout'] == "Name(id='log', ctx=Load())"
assert kw['stderr'] == "Attribute(value=Name(id='subprocess', ctx=Load()), attr='STDOUT', ctx=Load())"
assert not any(isinstance(n.func, ast.Attribute) and n.func.attr in {'wait', 'kill', 'killpg', 'terminate', 'send_signal'} for n in calls)
assert "(B/'launch-once.json').open('x')" in detach and "(B/'supervisor.log').open('x')" in detach
assert detach.index("(B/'launch-once.json').open('x')") < detach.index('subprocess.Popen')
assert "peer['policy']==pin(B/'policy.json')" in detach
assert not Path(policy['native_new_output']).exists() and not (B / 'launch-once.json').exists()
result = dict(status='PASS_SOURCE_ONLY_DETACHED_PLL_RESTART', policy=pin(B / 'policy.json'), findings=[],
              method=pin(Path(__file__)), policy_all10_pins_rehashed=True, whole_launcher_byte_inverse=True,
              additive_gate_text_sha256=hashlib.sha256(added.encode()).hexdigest(),
              prior_preservation_archive=pin(archive), all2466_members_rehashed=True,
              all128_saved_public_part_receipts_bound=True, prior_two_asset_public_receipt=pin(P / 'release01.json'),
              missing_original_births=births, live_exact_producer_argv=live,
              exclusive_launch_once_marker=True, detached_session_closed_stdin_file_logs=True,
              native539_physics_runtime_fixed_windows_thresholds_resources_unchanged=True,
              original1us_not_completed=True, no_initial_operating_point_resume=True,
              no_native_or_launcher_or_control_executed_by_peer=True,
              scope='Read-only source/full preserved archive/saved receipt review; fresh time0 start and later actual native progress remain to be verified by owner. Launcher narrative retains historical prior-run summaries; current808.935ns interruption is separately pinned.')
(B / 'source-peer-vco.json').write_text(json.dumps(result, indent=2) + '\n')
print(result['status'], pin(B / 'source-peer-vco.json'), flush=True)
