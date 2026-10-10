#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fix stream-completion ownership and prove exact native values across raw orders.

The frozen v1 actual native0 capture remains ERROR after its terminal future race.
Native write-all and run-FIFO have different, fully declared column orders. This
version preserves both raw bytes and compares every binary64 bit after only the
header-proven column permutation. No numeric sample, device, limit, deck or
measurement change. Reused functions execute in a private namespace.
"""

import hashlib
import inspect
from pathlib import Path
import shutil
import stat

import characterize_pcie_pll_loop_stream_v1 as previous

PREVIOUS_SHA = "b0a92554452c3334ba14f44f7c743cd29aee02d5f5fd3f8625cd6386b5afec6d"
previous.require(
    previous.n.common.sha(previous.__file__) == PREVIOUS_SHA, "Exact frozen stream v1"
)
namespace = dict(vars(previous))
namespace["__file__"] = __file__
namespace["__name__"] = __name__


def canonical_indices(columns):
    previous.require(
        columns[0] == "time" and len(columns) == len(set(columns)),
        "Exact unique native column identity",
    )
    ordered = ["time", *sorted(columns[1:])]
    return [columns.index(name) for name in ordered]


def guard(folder):
    """A successfully deleted published part consumes zero current disk bytes."""
    free = shutil.disk_usage("/dev/shm").free
    previous.require(free >= previous.FLOOR, "Shared 512 MiB floor")
    used = 0
    for path in folder.rglob("*"):
        try:
            info = path.stat()
        except FileNotFoundError:
            # Atomic metadata replacement/public-verified deletion can race us.
            continue
        if stat.S_ISREG(info.st_mode):
            used += info.st_size
    previous.require(used <= previous.CAP, "Own 50 MiB capture ceiling")
    return free, used


def verify_parent():
    previous.require(
        previous.n.common.sha(previous.__file__) == PREVIOUS_SHA,
        "Frozen v1 still unchanged",
    )
    return previous.verify_parent()


namespace.update(
    canonical_indices=canonical_indices, guard=guard, verify_parent=verify_parent
)
BRIDGES = {}


def derive(name, changes):
    """Exact source bridges fail closed if an expected statement changes."""
    original = inspect.getsource(getattr(previous, name))
    modified = original
    for old, new in changes:
        previous.require(modified.count(old) == 1, f"Unique {name} source bridge")
        modified = modified.replace(old, new)
    BRIDGES[name] = dict(
        original_sha256=hashlib.sha256(original.encode()).hexdigest(),
        modified_sha256=hashlib.sha256(modified.encode()).hexdigest(),
        exact_replacements=changes,
    )
    exec(compile(modified, __file__ + ":" + name, "exec"), namespace)
    return namespace[name]


native_wait = derive(
    "native_wait",
    [
        (
            "if future.done():\n                            code = owner.complete(process)",
            "if future.done():\n                            captured = future.result()\n                            code = owner.complete(process)",
        )
    ],
)
capture = derive(
    "capture",
    [
        (
            'width = len(meta["columns"]) * 8',
            'width = len(meta["columns"]) * 8\n    canonical = hashlib.sha256()\n    order = canonical_indices(meta["columns"])',
        ),
        (
            "payload = bytes(pending[: count * width])",
            'payload = bytes(pending[: count * width])\n                canonical.update(np.frombuffer(payload, "<u8").reshape(count, -1)[:, order].tobytes())',
        ),
        (
            'payload_sha256=ledger["payload_sha256"],',
            'payload_sha256=ledger["payload_sha256"],\n            canonical_payload_sha256=canonical.hexdigest(),\n            canonical_order="time then lexicographically sorted canonical native vector identities; binary64 bits unchanged",',
        ),
    ],
)
replay_original = derive(
    "replay_original",
    [
        (
            "whole, payload = hashlib.sha256(), hashlib.sha256()",
            "whole, payload = hashlib.sha256(), hashlib.sha256()\n    canonical = hashlib.sha256()",
        ),
        (
            'width = len(meta["columns"]) * 8',
            'width = len(meta["columns"]) * 8\n            order = canonical_indices(meta["columns"])',
        ),
        (
            "payload.update(body)",
            'payload.update(body)\n        canonical.update(np.frombuffer(body, "<u8").reshape(count, -1)[:, order].tobytes())',
        ),
        (
            "payload_sha256=payload.hexdigest(),",
            'payload_sha256=payload.hexdigest(),\n        canonical_payload_sha256=canonical.hexdigest(),\n        canonical_order="time then lexicographically sorted canonical native vector identities; binary64 bits unchanged",',
        ),
    ],
)
# Three occurrences are an explicit, counted contract-name update, not a broad
# unbounded replacement. Keep the actual native prerequisite semantics unchanged.
source = inspect.getsource(previous.run)
previous.require(
    source.count("original_payload_and_measurements_equal") == 3,
    "Three transport contract fields",
)
source = source.replace(
    "original_payload_and_measurements_equal", "original_values_and_measurements_equal"
)
previous.require(source.count('"payload_sha256",') == 1, "One exact equality field")
source = source.replace('"payload_sha256",', '"canonical_payload_sha256",')
BRIDGES["run"] = dict(
    original_sha256=hashlib.sha256(
        inspect.getsource(previous.run).encode()
    ).hexdigest(),
    modified_sha256=hashlib.sha256(source.encode()).hexdigest(),
    modifications="Three contract labels and one header-permutation payload comparison; all other code literal",
)
exec(compile(source, __file__ + ":run", "exec"), namespace)
run = namespace["run"]
main = derive("main", [])
# Export only needed aliases; never mutate the imported producer's globals.
Meter, measurements, settling = previous.Meter, previous.measurements, previous.settling
n, ROOT, ORIGINAL = previous.n, previous.ROOT, previous.ORIGINAL

if __name__ == "__main__":
    raise SystemExit(main())
