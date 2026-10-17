#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exact maxstep experiment with durable local parts, independent of network.

All numerical/native/meter/startup criteria are inherited from acquisition V4.
Only transport, local evidence storage and honest local/public status differ.
This is a fresh time-zero run; no incomplete stream is a solver checkpoint.
"""
import hashlib
import inspect
import json
from pathlib import Path

import characterize_pcie_pll_acquisition_v4 as previous
import durable_pcie_spool_v1 as local

PREVIOUS_SHA = '5e64b71eeb9f792b1a909ec354b3c69010b6f0983ec4f36323b2e0992c2b5503'
SPOOL_SHA = '3018034f18b19127a5c4785570370d942c08808985df3a9229c10865b17060a8'
require, n = previous.require, previous.n
BRIDGES = {}
_active_spool = None


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_parent():
    require(sha(previous.__file__) == PREVIOUS_SHA, 'Frozen acquisition V4')
    require(sha(local.__file__) == SPOOL_SHA, 'Frozen durable spool')
    return previous.verify_parent()


def bridge(source, replacements, name):
    original = source
    for before, after in replacements:
        require(source.count(before) == 1, 'Unique local capture bridge: ' + name)
        source = source.replace(before, after)
    BRIDGES[name] = dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),
                        modified_sha256=hashlib.sha256(source.encode()).hexdigest(),
                        exact_replacements=replacements)
    return source


def guard(folder):
    free, used = previous.namespace['guard'](folder)
    require(_active_spool is not None, 'One explicit local spool owner')
    _active_spool.check()
    return free, used


require(sha(previous.__file__) == PREVIOUS_SHA, 'Exact acquisition V4 source')
require(sha(local.__file__) == SPOOL_SHA, 'Exact local spool source')
namespace = dict(previous.namespace)
namespace.update(__file__=__file__, __name__=__name__, __doc__=__doc__,
                 previous=previous, verify_parent=verify_parent, local=local, guard=guard)
capture_source = bridge(previous.capture_source, [
    ('    (output / "header.bin").write_bytes(header)',
     '    (output / "header.bin").write_bytes(header)\n'
     '    publisher.metadata("header.bin", header)'),
    ('queue = life.PartQueue(', 'queue = local.PartQueue('),
    ('        (output / "trailer.bin").write_bytes(trailer)',
     '        (output / "trailer.bin").write_bytes(trailer)\n'
     '        publisher.metadata("trailer.bin", trailer)'),
    ('status="PASS_COMPLETE_CAPTURE",',
     'status="PASS_LOCAL_COMPLETE_CAPTURE",\n'
     '            local_spool=dict(path=str(publisher.root), manifest=local.pin(publisher.root / "parts.json")),\n'
     '            public_verified=False,'),
], 'capture')
exec(compile(capture_source, __file__ + ':capture', 'exec'), namespace)
capture = namespace['capture']

# Native device launch/FIFO/process ownership is unchanged. The added terminal
# checks close resource/cancellation windows without imposing elapsed limits.
native_wait_source = bridge(inspect.getsource(previous.namespace['native_wait']), [
    ('    fifo.unlink()\n    return captured',
     '    owner.check()\n    guard(folder)\n    fifo.unlink()\n    return captured'),
    ('native_and_publisher_groups_owned=True,',
     'native_group_owned=True, network_in_native_capture=False,'),
], 'native_wait')
exec(compile(native_wait_source, __file__ + ':native_wait', 'exec'), namespace)
native_wait = namespace['native_wait']

run_source = bridge(previous.run_source, [
    ('OwnedPublisherV3(owner)', '_active_spool'),
    ("paths += validated['paths']", "paths += validated['paths']\n"
     "    paths += [str(Path(local.__file__).resolve()), str(_active_spool.root / 'configuration.json') ]"),
    ('"PASS_NATIVE_STREAM_FINITE_SCREEN"\n            if captured',
     '"PASS_NATIVE_LOCAL_STREAM_FINITE_SCREEN"\n            if captured'),
    ('else "FAIL_NATIVE_STREAM_FINITE_SCREEN"',
     'else "FAIL_NATIVE_LOCAL_STREAM_FINITE_SCREEN"'),
], 'run')
exec(compile(run_source, __file__ + ':run', 'exec'), namespace)
_native_run = namespace['run']


def run(out, prefix, step, stop, reference, reference_sha, gate=None, gate_sha=None,
        *, spool_root):
    global _active_spool
    require(_active_spool is None, 'No concurrent local native producer')
    spool_root, out = Path(spool_root), Path(out)
    require(not spool_root.resolve().is_relative_to('/dev/shm')
            and spool_root.parent.stat().st_dev != Path('/dev/shm').stat().st_dev,
            'Durable spool must be outside RAM filesystem')
    spool = local.Spool(spool_root, prefix)
    _active_spool = spool
    namespace['_active_spool'] = spool
    original_error = None
    try:
        return _native_run(out, prefix, step, stop, reference, reference_sha, gate, gate_sha)
    except BaseException as error:
        original_error = error
        raise
    finally:
        try:
            result = json.loads((out / 'result.json').read_text())
            spool.terminal(result, native_root=out)
        except BaseException as retention_error:
            # Keep original failure and every local byte, including reservation.
            failure = dict(status='ERROR_LOCAL_TERMINAL_RETENTION',
                           original_error=repr(original_error), error=repr(retention_error))
            local.fresh_bytes(spool.root / 'terminal-retention-failure.json', local.encoded(failure))
            local.fsync_dir(spool.root)
            if original_error is None:
                raise
        finally:
            spool.close()
            _active_spool = None
            namespace['_active_spool'] = None


namespace['run'] = run
main_source = bridge(previous.main_source, [
    ('    parser.add_argument("--prefix", required=True)',
     '    parser.add_argument("--prefix", required=True)\n'
     '    parser.add_argument("--spool", type=Path, required=True)'),
    ('        args.prerequisites_sha,\n',
     '        args.prerequisites_sha,\n        spool_root=args.spool,\n'),
    ('"PASS_NATIVE_STREAM_FINITE_SCREEN" else 1',
     '"PASS_NATIVE_LOCAL_STREAM_FINITE_SCREEN" else 1'),
], 'main')
exec(compile(main_source, __file__ + ':main', 'exec'), namespace)
main = namespace['main']
stream_deck, Meter = previous.stream_deck, previous.Meter
measurements, acquisition = previous.measurements, previous.acquisition
startup_proof, prerequisites = previous.startup_proof, previous.prerequisites
TSTEP, TMAX, STOP = previous.TSTEP, previous.TMAX, previous.STOP

if __name__ == '__main__':
    raise SystemExit(main())
