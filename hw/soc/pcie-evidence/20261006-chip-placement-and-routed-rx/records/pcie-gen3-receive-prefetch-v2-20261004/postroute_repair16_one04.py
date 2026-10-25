# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual-SPEF-first RX16 mixed-RC experiment from exact closed RX14A."""
from pathlib import Path
import hashlib
import json
import os
import resource
import signal
import shutil
import subprocess
import time

R = Path.cwd()
B = R / 'hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004'
D = Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-drt-01')
X = Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-detailed-rc-01')
O = Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-one-repair-04')
A = R / 'hw/soc/tools/openroad-26Q2-1164/run-openroad'


def pin(path):
    p = Path(path)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


def interrupted(number, _frame):
    raise InterruptedError(f'Signal {number}')


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (int(2.5 * 1024**3),) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.sched_setaffinity(0, {8})
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT, signal.SIGTERM})


def identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    except FileNotFoundError:
        return None
    return dict(pid=pid, process_group=int(fields[2]), start_ticks=fields[19])


assert shutil.disk_usage('/dev/shm').free >= 1024**3


inputs = {}
for directory in (D, X):
    result = json.loads((directory / 'result.json').read_text())
    assert result['status'].startswith('COMPLETE_') and result['returncode'] == 0
    for path, expected in result['inputs'].items():
        assert pin(path) == expected, path
        inputs[path] = expected
    for name, expected in result['outputs'].items():
        path = directory / name
        assert pin(path) == expected, path
        inputs[str(path)] = expected
    inputs[str(directory / 'result.json')] = pin(directory / 'result.json')
assert (D / 'router-drc.rpt').stat().st_size == 0
assert pin(D / 'routed.v')['sha256'] == 'cc489bb50c225189126b36d173cf786a7837f1e9a0cebc8a200c2d7b7a191f91'
old_review = B / 'repair13-peer/review.json'
old = json.loads(old_review.read_text())
assert old['nominal_rc_cell_corner_slack_ns']['slow']['setup'] == -.441603
endpoints = [p['endpoint'] + '/D' for p in old['SS_three_worst_setup_paths']]
assert len(endpoints) == len(set(endpoints)) == 3
libs = [line for line in (D / 'route.tcl').read_text().splitlines() if line.startswith('read_liberty ')]
assert len(libs) == 3

EXACT_WIDE_BASIS = {'/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair15-source/wide-paths-review.json': {'bytes': 4619803, 'sha256': 'a3d63898c13743a90234762ddbc13f7252d93ff4aaf8c391b3dd0684c69b3bb5'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair15-source/actual-paths01/result.json': {'bytes': 9763, 'sha256': 'ee0ea87614f4afa83e56707b9563baaeaae7607c7c6e02b4d2b108b593a9942e'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair15-source/actual-paths01/native.log': {'bytes': 1931560, 'sha256': '01060c5961ca34f5f4cd5629c158409596e5b97079394043bb6cc64b26fab8ad'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair14a-peer/publication-review.json': {'bytes': 4526, 'sha256': '72b7786c7df7453a0394f5539e097f8dc79faba0a2d0040917388846a03a7080'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair04-source/current-tool-help.log': {'bytes': 1778, 'sha256': '1ef7b473dc6d4ed63779517d0fafd417a98a29fccc0a2fdde24118f723aaef5a'}}
assert EXACT_WIDE_BASIS == {p: pin(p) for p in EXACT_WIDE_BASIS}
inputs.update(EXACT_WIDE_BASIS)
MARGIN_BASIS = {'/dev/shm/nssoc-rx-prefetch-v2-repair15-full-grt-rescreen-01/result.json': {'bytes': 14080, 'sha256': 'f256c88a2d9213f98791ca75ced7307b758d1ef664fa19bd8a359c0805ce09ef'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair15-source/active-checkpoint01.json': {'bytes': 1322, 'sha256': '1047c571e880300c0f4e200a15814ef6ed40c127c7f46e5e4771e022ed124736'}}
assert MARGIN_BASIS == {p: pin(p) for p in MARGIN_BASIS}
inputs.update(MARGIN_BASIS)
MIXED_RC_BASIS = {'/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/postroute_repair05.py': {'bytes': 14023, 'sha256': '53e84f2d5214f20df9829ff7402d687ecb57355181b99375dffa5483c0ab32b1'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair05-source/source-only-peer-rx.json': {'bytes': 1354, 'sha256': '9824c5085c459112a863c3f54bd1c567b96d236efa03c20461b854b9fe867e9a'}, '/dev/shm/nssoc-tx-path-v4-postroute-repair-05/result.json': {'bytes': 13785, 'sha256': 'b8864544bb5abee24a3713d9fb67e3bc0a6ce470b5bbff853afa34f2b4cb0503'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair15-source/explicit-rejection-review.json': {'bytes': 5602, 'sha256': '849397a24a2fe8d5bfdcdc0a04f9b49200142359c0606b0222230d1c2763bb7f'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair15-source/broad-v3-rejection-review.json': {'bytes': 5517, 'sha256': '1320d223c634c50a741181869318f3dd53fd3ddcbaf9ee88022bb7bc46a5b5d9'}}
assert MIXED_RC_BASIS == {p: pin(p) for p in MIXED_RC_BASIS}
inputs.update(MIXED_RC_BASIS)
DEBUG_FAILURE_BASIS = {'/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-mixed-01/result.json': {'bytes': 13524, 'sha256': '915d8179f301080bcac714aff45e2e3596091c611185c407084da9d8f5807a5a'}, '/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-mixed-01/native.log': {'bytes': 5761257, 'sha256': 'b6173ea852ab824ae94382d644f3beba4c528c58b09845ce0d1bbc3cf62966d0'}}
assert DEBUG_FAILURE_BASIS == {p: pin(p) for p in DEBUG_FAILURE_BASIS}
inputs.update(DEBUG_FAILURE_BASIS)
ONE_REPAIR_BASIS = {'/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-debug-03/result.json': {'bytes': 14738, 'sha256': '8a31acd25d11a5480cfc3060c641923c49b8b10c615968f56bed3078aecbe9ef'}, '/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-debug-03/native.log': {'bytes': 17981633, 'sha256': 'c55c953397ca449eff966da8af4fb25a691278c1e2f134d49eda4b2c81db711f'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair16-source/debug03-rejection-review.json': {'bytes': 7276, 'sha256': '49956b358d8708af059873e65c9a1bf2db3b7f0429d5558407432e5f3491a5fa'}}
assert ONE_REPAIR_BASIS == {p: pin(p) for p in ONE_REPAIR_BASIS}
inputs.update(ONE_REPAIR_BASIS)
lines = ['set_thread_count 1', 'define_corners slow typical fast', *libs,
         f'read_db {{{D / "routed.odb"}}}', f'read_sdc {{{D / "routed.sdc"}}}',
         'set_propagated_clock [all_clocks]',
         'set_wire_rc -signal -layer Metal2', 'set_wire_rc -clock -layer Metal4',
         'set_routing_layers -signal Metal2-Metal5 -clock Metal2-Metal5',
         'set_global_routing_layer_adjustment Metal2-Metal5 0.30']
lines += [f'read_spef -corner {corner} {{{X / "routed.spef"}}}' for corner in ('slow', 'typical', 'fast')]

def report(tag):
    result = [f'puts {tag}', 'report_worst_slack -max', 'report_worst_slack -min',
              'report_tns', 'report_check_types -max_slew -max_capacitance -violators']
    for corner in ('slow', 'typical', 'fast'):
        for direction, count in [('max', 100), ('min', 10)]:
            result += [f'puts {tag}_{corner}_{direction}',
                       f'report_checks -corner {corner} -path_delay {direction} -group_path_count {count} -fields {{slew cap fanout}} -digits 6']
    return result

lines += report('UNCHANGED_RX14A_ACTUAL_RC')
# Remove only copied signal geometry, never any existing cell/net or constraints.
lines += [f'write_verilog {{{O / "before_clear.v"}}}', 'set cleared_wire_count 0',
          'foreach net [[ord::get_db_block] getNets] {',
          '  if {[$net getSigType] in {POWER GROUND}} {continue}',
          '  set wire [$net getWire]',
          '  if {$wire != "NULL"} {odb::dbWire_destroy $wire; incr cleared_wire_count}',
          '  $net clearGuides', '}',
          'puts "REMOVED_CANDIDATE_SIGNAL_WIRES $cleared_wire_count"',
          f'write_verilog {{{O / "after_clear.v"}}}',
          f'set before_file [open {{{O / "before_clear.v"}}} r]',
          'set before_netlist [read $before_file]', 'close $before_file',
          f'set after_file [open {{{O / "after_clear.v"}}} r]',
          'set after_netlist [read $after_file]', 'close $after_file',
          'if {$before_netlist ne $after_netlist} {error "Signal-wire removal changed logical netlist"}',
          'puts EXACT_LOGICAL_NETLIST_UNCHANGED_AFTER_CLEAR',
          'detailed_placement', 'check_placement -verbose',
          f'global_route -congestion_iterations 100 -guide_file {{{O / "initial.guide"}}}',
          'estimate_parasitics -global_routing',
          'global_route -start_incremental']
lines += report('RX16ONE04_GRT_BEFORE_BROAD_REPAIR')
# Keep the initialized global-route topology for incremental edits, but start
# optimization from the actual unchanged baseline SPEF instead of optimistic
# fresh GRT estimates. Modified nets may receive GRT estimates during repair:
# this is explicitly a mixed-RC optimization experiment, never signoff timing.
lines += [f'read_spef -corner {corner} {{{X / "routed.spef"}}}' for corner in ('slow', 'typical', 'fast')]
lines += [f'report_worst_slack -max -digits 6 > {{{O / "reloaded-actual-worst.rpt"}}}',
          f'set worst_file [open {{{O / "reloaded-actual-worst.rpt"}}} r]',
          'set actual_worst [read $worst_file]', 'close $worst_file',
          'if {[string first "worst slack max -0.402478" $actual_worst] < 0} {error "Reloaded baseline actual RC differs"}',
          'puts EXACT_ACTUAL_BASELINE_RC_RESTORED_BEFORE_REPAIR']
lines += report('RX16ONE04_RELOADED_ACTUAL_RC_BEFORE_REPAIR')
# Optimization margins are stricter than zero slack; same original4ns timing model.
# Do not remove existing hold buffers or use a late unconstrained last-gasp pass.
lines += ['set_debug_level RSZ repair_setup 3', 'repair_timing -setup -sequence {clone sizeup buffer split} -repair_tns 100 -setup_margin 0.25 -max_repairs_per_pass 1 -skip_buffer_removal -skip_last_gasp',
          'repair_timing -hold -hold_margin 0.05',
          'detailed_placement', 'check_placement -verbose',
          f'global_route -end_incremental -congestion_iterations 100 -guide_file {{{O / "incremental.guide"}}}',
          f'write_verilog {{{O / "before_final_grt.v"}}}',
          'puts RX16ONE04_FRESH_FULL_GRT_FINAL',
          'foreach net [[ord::get_db_block] getNets] {',
          '  if {[$net getSigType] in {POWER GROUND}} {continue}',
          '  set wire [$net getWire]',
          '  if {$wire != "NULL"} {odb::dbWire_destroy $wire}',
          '  $net clearGuides', '}',
          f'global_route -congestion_iterations 100 -guide_file {{{O / "repaired.guide"}}}',
          'estimate_parasitics -global_routing']
lines += report('RX16ONE04_GRT_AFTER_BROAD_REPAIR_ESTIMATES_ONLY')
lines += [f'write_db {{{O / "repaired.odb"}}}', f'write_verilog {{{O / "repaired.v"}}}',
          f'write_sdc {{{O / "repaired.sdc"}}}', 'puts NATIVE_RX16ONE04_BROAD_CANDIDATE_COMPLETE']
O.mkdir()
tcl = O / 'repair.tcl'
tcl.write_text('\n'.join(lines) + '\n')
for path in [Path(__file__), old_review, tcl, A, R / 'hw/soc/tools/openroad-26Q2-1164/root/usr/bin/openroad']:
    inputs[str(path)] = pin(path)
record = dict(status='RUNNING_BROAD_RX16ONE04_CANDIDATE', inputs=inputs, cpu=8,
              elapsed_watchdog_seconds=None, qualified_rc=False,
              boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              minimum_shared_free_bytes=shutil.disk_usage('/dev/shm').free,
              physical_acceptance=False, scope='Copied closed RX14A baseline actual RC reported before edits. Exact netlist equality on signal wire/guide clear; fresh GRT topology then reload exact baseline SPEF/assert actual WNS before setup sequence clone,sizeup,buffer,split allTNS/0.25ns and guarded hold0.05ns; modified nets may use estimates; final fresh fullGRT. No original4ns IO/clock constraint edits, no allow_setup_violations, no healthy elapsed timeout. Mixed-RC optimization and final GRT estimates only; new graph proof,10faults,6ports,DRT and actual nominalRC mandatory before acceptance.')

def save():
    (O / 'result.json').write_text(json.dumps(record, indent=2) + '\n')


for s in (signal.SIGINT, signal.SIGTERM):
    signal.signal(s, interrupted)
process = None
owned_identity = None
done = False
save()
try:
    with (O / 'native.log').open('x') as log:
        mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})
        try:
            process = subprocess.Popen([str(A), '-exit', str(tcl)], stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, preexec_fn=limits)
            owned_identity = identity(process.pid)
            assert owned_identity is not None and owned_identity['process_group'] == process.pid
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        record['pid'] = process.pid
        record['owned_identity'] = owned_identity
        save()
        while process.poll() is None:
            assert identity(process.pid) == owned_identity
            free = shutil.disk_usage('/dev/shm').free
            record['minimum_shared_free_bytes'] = min(record['minimum_shared_free_bytes'], free)
            if free < 528 * 1024**2:
                raise RuntimeError('Shared scratch floor')
            time.sleep(.25)
        record['returncode'] = process.wait()
        assert record['returncode'] == 0
        terminal_free = shutil.disk_usage('/dev/shm').free
        record['minimum_shared_free_bytes'] = min(record['minimum_shared_free_bytes'], terminal_free)
        assert terminal_free >= 528 * 1024**2, 'Terminal shared scratch floor'
        done = True
    log = (O / 'native.log').read_text()
    assert 'NATIVE_RX16ONE04_BROAD_CANDIDATE_COMPLETE' in log
    assert 'EXACT_ACTUAL_BASELINE_RC_RESTORED_BEFORE_REPAIR' in log
    final_log = log.split('RX16ONE04_FRESH_FULL_GRT_FINAL\n',1)[1]
    assert not any(x in final_log for x in ('Missing route to pin', 'Fail to restore routing segments')), 'Incomplete final route context'
    assert pin(O / 'before_final_grt.v') == pin(O / 'repaired.v'), 'Final GRT changed logical netlist'
    assert inputs == {name: pin(name) for name in inputs}
    record['status'] = 'COMPLETE_CANDIDATE_REQUIRES_EQUIVALENCE_ROUTE_RC'
except BaseException as error:
    record.update(status='FAILED_RETAINED', error=repr(error))
    raise
finally:
    if process is not None and not done and process.poll() is None:
        if owned_identity is not None and identity(process.pid) == owned_identity:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + 2
            while process.poll() is None and time.monotonic() < deadline:
                time.sleep(.05)
            if process.poll() is None and identity(process.pid) == owned_identity:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        process.wait()
    record['outputs'] = {p.name: pin(p) for p in O.iterdir() if p.is_file() and p.name != 'result.json'}
    save()
