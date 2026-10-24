# Actual TX clock-role parameter diagnosis

The original role proof 40102668052 remains rejected. Exact small-archive readback
40108734425 reproduced its log: original 124-input/372-base/64-driver/four-output
interface proof passed, then the new clock-role binder rejected at its fixed
`p['nx']==8.0` check. The log omitted the device ID and actual value.

The pinned tree assembler selects two Nx3 balanced prestages, 28 Nx1 balanced
prestages and final-drive-v10. The existing budget source changes all eighteen
nonreference HBTs of a prestage to its size. Balanced-v5 changes resistors and
explicitly preserves those HBT cards. The final canonical source has twelve
Nx3 data HBTs, four Nx6 selectors, two Nx8 tails and one Nx1 reference.

These source facts expose an incorrect universal expected value in the new
binder. They do not establish that the observed device is the intended selector
or that the physical database agrees. The original binder and failed result
therefore remain byte-identical.

The new observer restores the same qualified source archive (run40083738813)
and re-executes its original interface binder. It probes actual clock-port
polarity, identifies data/selector/tail/reference roles by native C/B/E
connectivity and macro geometry, and records all589 mux HBT IDs, full parameters,
native clusters and composed terminal records. Expected stage values are bound
to immutable canonical sources, child physical receipts and child schematic
hashes in the original topology report. It requires 719 mux emitter fingers,
records any mismatch, and reproduces the old assertion at its unchanged
source line31 before reporting diagnostic completion.

Source controls retain the original12 metadata and8 archive faults, plus16
catalog corruptions including the old blanket-Nx8 assumption, stage-specific
sizes, duplicate/missing roles, model changes and nonfinite parameters.
The manual-only template runs controls first. Actual database readback requires
its explicit boolean input and preserves complete small JSON in Actions logs
and an artifact. It creates no release/tag and runs no new extraction, solver,
transient, circuit sizing or geometry generation.

No binder repair, native-role acceptance, electrical/clock-tree/reset/PLL/PHY
acceptance follows from this source-only candidate. Native execution and
independent review of its complete actual device report are still required.
