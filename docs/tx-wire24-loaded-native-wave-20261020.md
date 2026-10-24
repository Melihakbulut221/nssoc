# TX wire24 loaded native waveform

Composition run 39343496964 passed with the exact new 28-route geometry.
Its native model contains 1674 devices, 116611 metal resistors and 77538 metal
capacitors. Six actual malformed-model controls, topology recovery for all
377 wire components and the 124 physical input-leg / 372 base-terminal
bindings passed. Complete source hashes and release addresses are in the
[composition receipt](evidence/tx-fast-wire24-composition-pass-20261020.json).

The loaded-wave workflow runs two independent hosted jobs: the nominal
candidate and an actual swapped leaf-select fault. Each first compares all
compact devices with the previous timing-priority candidate, using the
physical primitive model and local bounding box within named macros to
establish correspondence. It rejects removed devices, changed HBT parameters,
wrong terminals and exchanged physical identities. A failed comparison stops
before native transient simulation.

The builder changes only its two allowed model hashes and explanatory comment.
The clock adapter changes only the builder import. Source-delta checks preserve
all original stimulus, solver, signal, device, sample-phase and clock-fault
logic. Eleven native clock-reference macros remain, with the same external
modulation boundary; this is not yet recovered-clock/full-serial-PHY acceptance.

The wire model's new SHA-256 is
92797a39882e9ace4a11d393f44b5c1494540001723746254a871b3965f16dca.
The original 34 ns / 256-bit / three-phase test, all 604 HBT and 512 MOS
screens, 44 clock-corruption controls and complete native waveforms remain.
The old failed wave and the publication/download failures are preserved.
Native execution and output storage are cloud-only.

Passing composition alone does not pass this experiment. Read the actual
waveform gates, not merely the workflow status, before considering the change
electrically acceptable. PVT, recovered clocks, four-lane integration,
qualified RF/substrate extraction and final main-chip timing remain open.
