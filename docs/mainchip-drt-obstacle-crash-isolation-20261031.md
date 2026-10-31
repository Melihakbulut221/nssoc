# Read-only mainchip observer crash isolation

This is a disabled, source-only diagnostic successor to source `00b46253e990983365db3b5f2b44a1233e20623e`. It does not authorize another native observation, routing, physical acceptance, RC or timing acceptance.

## Authentic failure

Run [41241933572](https://github.com/Melihakbulut221/nssoc/actions/runs/41241933572) exited with native OpenROAD return code **-11** after **972.822782791 seconds**, with `supervision_failure=null` and an actually requested **3600-second** deadline. The last memory sample recorded 1,518,232 KiB group RSS and 13,775,472 KiB host available memory. Cleanup reported no remaining processes.

The observer completed VGND and 143 of 373 endpoint nets. Its final durable phase checkpoint was VPWR `endpoint-iterm-pins`, with 65,536 completed items at 959.885429835 seconds. This is a 1024-item cadence checkpoint, **not the exact failing item**. The candidate diagnostic interval is zero-based indices 65,536 through 66,559.

Periodic stack samples repeatedly observed JSON serialization of special-via records in `feed`. The final partial stack ends inside the Python interpreter trampoline. Neither the serialization hotspot nor the periodic sampler is proven to have caused the native crash. The earlier run 41236517605 instead ended at its 1200-second elapsed limit; these outcomes remain distinct.

Complete terminal proof: commit `45168c775b2c91e58fd6cbfc0935777232d89202`, prefix `docs/evidence/mainchip-drt-obstacle-progress-terminal-41241933572/`, subtree `d24617f4f788d6333a400c854e6d84312c78e46f`: 68 files / 2,963,112 bytes, receipt SHA256 `ecdf889ccd473a418197a8c656165bba825576786340eb92dc3dfe19122e718c`. The repaired publication path retained all 50 catalogued derived outputs in release 430186433, including 42 nonempty assets; no native payload was acquired locally.

## Exact source audit

The pinned OpenROAD Python [container typemap](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/odb/src/swig/python/dbtypes.i#L42) materializes ITerm handles in a Python list. Those handles refer to the live database, which this observer never mutates and destroys only in its finalizer. The [geometry typemap](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/odb/src/swig/python/dbtypes.i#L162) allocates rectangle copies from the returned values; it does not expose references into the temporary returned vector. All pin geometry is immediately converted to Python primitive tuples and independently reconciled against every transformed MPin shape, retaining multiplicity. This audit does not establish a use-after-free cause. The typemap's non-owning rectangle flag is an allocation-lifetime observation, not evidence that it caused this low-RSS crash.

Python distinguishes [fatal-signal handling from the background traceback watchdog](https://docs.python.org/3.12/library/faulthandler.html). This successor removes the introduced periodic watchdog as an isolation variable. It enables fatal-only, current-thread diagnostics only when no existing handler is enabled; a pre-existing handler is left completely untouched. Only a handler installed by this scope is disabled during cleanup. Installation and restoration failures retain their original errors.

## Narrow diagnostic delta

The original phase and 1024-item progress records remain. The existing `trace.items` counter supplies the zero-based item ordinal without rewriting the ITerm iterator. Within the candidate VPWR interval only, six ordered records identify entry before identity calls, identity return, connectivity return, entry before complete pin geometry, completed pin geometry/feed, and item completion. The maximum is **6,144 operation records**. Actual instance/terminal identifiers reuse values already read by the original algorithm. An append-only JSONL journal and atomic latest cursor preserve partial failure evidence. No cursor value controls geometry, witness selection, record serialization, or acceptance.

The complete geometry/witness/hash AST is still compared to the immutable original after removing only declared telemetry statements. `all_pin_geometry` and `record` remain exactly equal to that baseline. Special-via serialization is deliberately unchanged; any later optimization requires its own equivalence proof.

The native budget remains 3600 seconds, the owned-container deadline 3900 seconds, group RSS 10 GiB, container memory 12 GiB, and host available memory reserve 2 GiB. Full failure publication and all input/source/topology/census gates remain unchanged. Electrical limits, including 20/4/8/8 ns plus 5%, are untouched.

The planned hosted source suite contains 57 methods: all prior archive/parser/physical-scope/resource/publication controls, replacement fatal-handler lifecycle coverage, bounded cursor refusal/partial-write tests, the exact production ITerm loop exercised against independent synthetic pin records, and a separate standard-library child process proving fatal-signal output. That synthetic process disables core files and carries no native project input. A source-control pass is not a native observation result. The source manifest and workflow keep native authority disabled until a separately reviewed activation.
