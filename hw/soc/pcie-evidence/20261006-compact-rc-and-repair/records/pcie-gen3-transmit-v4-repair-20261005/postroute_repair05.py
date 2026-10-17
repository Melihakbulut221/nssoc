# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual-SPEF-first TX05 mixed-RC optimization from closed TX03; no signoff."""
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
B = R / 'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005'
D = Path('/dev/shm/nssoc-tx-path-v4-repair03-drt-01')
X = Path('/dev/shm/nssoc-tx-path-v4-repair03-detailed-rc-01')
O = Path('/dev/shm/nssoc-tx-path-v4-postroute-repair-05')
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
    os.sched_setaffinity(0, {4})
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
assert pin(D / 'routed.v')['sha256'] == '6a284e00cc05f36537fd2b0abfe2854cab433fb41f634989d947a3d987a00c97'
old_review = B / 'repair02-peer/review.json'
old = json.loads(old_review.read_text())
assert old['nominal_rc_cell_corner_slack_ns']['slow']['setup'] == -.390164
endpoints = [p['endpoint'] + '/D' for p in old['SS_three_worst_setup_paths']]
assert len(endpoints) == len(set(endpoints)) == 3
libs = [line for line in (D / 'route.tcl').read_text().splitlines() if line.startswith('read_liberty ')]
assert len(libs) == 3

EXACT_WIDE_BASIS = {'/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair04-source/wide-paths-review01.json': {'bytes': 2143633, 'sha256': '554032f11bc2e07e6c9eb74128adcb6732b16ae85c791910ee5a90d4eff33240'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair04-source/actual-paths01/result.json': {'bytes': 9414, 'sha256': '0494f5342af6fdc61cebb56c1373112db6d18a3c498fe1f0332e19df3a4331b2'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair04-source/actual-paths01/native.log': {'bytes': 1990916, 'sha256': 'ec1f38c08ea4e7a052fd00388498120eda5a258b436cee1d7773a001909c96f9'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair03-peer/release.json': {'bytes': 3528, 'sha256': '531c2cd8dba1c6c20be0cabd9cf149bf87eff7c68de4f6fbc7bdc761da915c5c'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair04-source/current-tool-help.log': {'bytes': 1778, 'sha256': '1ef7b473dc6d4ed63779517d0fafd417a98a29fccc0a2fdde24118f723aaef5a'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/postroute_repair04.py': {'bytes': 10869, 'sha256': 'd4257d9b352db4463f0b12d198699ff0113e65c0d621af8d48fd52f2381ea123'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair04-source/broad-candidate-source-only-peer-rx.json': {'bytes': 9126, 'sha256': '08bd1f3ce10f7b5fa2516923f49e817ffb25331feae623d0cc124e7c562ecdff'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/postroute_repair15_v3.py': {'bytes': 12215, 'sha256': 'a75b1e33b3844781c76eb6791f84d8315cc07cbac2ae702314a2b80fdd3081ff'}, '/home/hasanmelih/Documents/ChatGPT/nnsoc/hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004/repair15-source/broad-candidate-v3-source-only-peer-vco.json': {'bytes': 20484, 'sha256': '5b16fb448e006731297023883748d8a4b13c1b2e195ff8f16d2238098850a692'}, '/dev/shm/nssoc-tx-path-v4-postroute-repair-04/result.json': {'bytes': 11801, 'sha256': 'c38c5bf7353c04bf310ad7d8880c0d27097b9b1adeeaaca9d33f708a4369e0fb'}, '/dev/shm/nssoc-tx-path-v4-postroute-repair-04/native.log': {'bytes': 6348862, 'sha256': '440bf54d888850558e8943efcfd7f135098a27343e01db7a412586e96e77f9c9'}}
assert EXACT_WIDE_BASIS == {p: pin(p) for p in EXACT_WIDE_BASIS}
inputs.update(EXACT_WIDE_BASIS)
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

lines += report('UNCHANGED_TX03_ACTUAL_RC')
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
lines += report('TX05_GRT_BEFORE_BROAD_REPAIR')
# Keep the initialized global-route topology for incremental edits, but start
# optimization from the actual unchanged baseline SPEF instead of optimistic
# fresh GRT estimates. Modified nets may receive GRT estimates during repair:
# this is explicitly a mixed-RC optimization experiment, never signoff timing.
lines += [f'read_spef -corner {corner} {{{X / "routed.spef"}}}' for corner in ('slow', 'typical', 'fast')]
lines += [f'report_worst_slack -max -digits 6 > {{{O / "reloaded-actual-worst.rpt"}}}',
          f'set worst_file [open {{{O / "reloaded-actual-worst.rpt"}}} r]',
          'set actual_worst [read $worst_file]', 'close $worst_file',
          'if {[string first "worst slack max -0.601762" $actual_worst] < 0} {error "Reloaded baseline actual RC differs"}',
          'puts EXACT_ACTUAL_BASELINE_RC_RESTORED_BEFORE_REPAIR']
lines += report('TX05_RELOADED_ACTUAL_RC_BEFORE_REPAIR')
# Optimization margins are stricter than zero slack; same original4ns timing model.
# Do not remove existing hold buffers or use a late unconstrained last-gasp pass.
lines += ['repair_timing -setup -sequence {clone sizeup buffer split} -repair_tns 100 -setup_margin 0.25 -max_repairs_per_pass 4 -skip_buffer_removal -skip_last_gasp',
          'repair_timing -hold -hold_margin 0.05',
          'detailed_placement', 'check_placement -verbose',
          f'global_route -end_incremental -congestion_iterations 100 -guide_file {{{O / "incremental.guide"}}}',
          f'write_verilog {{{O / "before_final_grt.v"}}}',
          'puts TX05_FRESH_FULL_GRT_FINAL',
          'foreach net [[ord::get_db_block] getNets] {',
          '  if {[$net getSigType] in {POWER GROUND}} {continue}',
          '  set wire [$net getWire]',
          '  if {$wire != "NULL"} {odb::dbWire_destroy $wire}',
          '  $net clearGuides', '}',
          f'global_route -congestion_iterations 100 -guide_file {{{O / "repaired.guide"}}}',
          'estimate_parasitics -global_routing']
lines += report('TX05_GRT_AFTER_BROAD_REPAIR_ESTIMATES_ONLY')
lines += [f'write_db {{{O / "repaired.odb"}}}', f'write_verilog {{{O / "repaired.v"}}}',
          f'write_sdc {{{O / "repaired.sdc"}}}', 'puts NATIVE_TX05_BROAD_CANDIDATE_COMPLETE']
O.mkdir()
tcl = O / 'repair.tcl'
tcl.write_text('\n'.join(lines) + '\n')
for path in [Path(__file__), old_review, tcl, A, R / 'hw/soc/tools/openroad-26Q2-1164/root/usr/bin/openroad']:
    inputs[str(path)] = pin(path)
record = dict(status='RUNNING_BROAD_TX05_CANDIDATE', inputs=inputs, cpu=4,
              elapsed_watchdog_seconds=None, qualified_rc=False,
              boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              minimum_shared_free_bytes=shutil.disk_usage('/dev/shm').free,
              physical_acceptance=False, scope='Copied closed TX03 baseline actual RC reported before edits. Exact netlist equality on signal wire/guide clear; fresh global-route topology then exact baseline SPEF reloaded and worstslack asserted before setup sequence clone,sizeup,buffer,split allTNS/0.25ns margin and guarded hold0.05ns. During optimization changed nets may use estimates. Final complete nonincremental GRT rescreen. No original4ns IO/clock constraint edits, no allow_setup_violations, no healthy elapsed timeout. Mixed-RC optimization and final GRT estimates only; new graph proof,10faults,3ports,DRT and actual nominalRC mandatory before acceptance.')

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
    assert 'NATIVE_TX05_BROAD_CANDIDATE_COMPLETE' in log
    assert 'EXACT_ACTUAL_BASELINE_RC_RESTORED_BEFORE_REPAIR' in log
    final_log = log.split('TX05_FRESH_FULL_GRT_FINAL\n', 1)[1]
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
