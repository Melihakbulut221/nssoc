# Replay write address predecode — 14 November 2026

## Why this candidate exists

The completed diode-legalized chip still fails timing. Slow corner has 539 setup violations, WNS -1.074318442 ns; fast corner has 115 hold violations, WNS -0.110754686 ns. The worst setup path starts at `retry.write_valid` and ends in `retry.bytes[25][5]`. A NAND3 contributes 1.356738 ns and `place31537` contributes 0.977058 ns. Earlier reports identified a different branch, `place31551`; sizing that single buffer cannot be assumed to repair the distributed write selection tree.

## Exact change

Experiment switch `SOC_PCIE_REPLAY_WRITE_PREDECODE` keeps the existing one-cycle acceptance-to-memory-write delay. The write data register is unchanged. Instead of registering a binary write address and decoding it after the register, it registers 16 low-address choices and a qualified high-address group vector. There are 10 high groups for the current 152-byte store, including the partial final group. Byte `i` writes on `write_group[i/16] && write_low[i%16]`.

The high groups are assigned immediately beside all five original `write_valid` assignments: reset, link loss, ordinary default clear and the two accepted-write cases. There is no separately rewritten capture predicate. This preserves writing the last byte of a malformed EOP even when the protocol logic reports an error. Low address and data registers remain unconditional; a cleared high group disables writing. The default build retains the original RTL.

The changed register encoding may reduce the long shared selection path. It adds registers and changes fanout distribution; synthesis, clock load, hold repair and real wires can erase the benefit. No speed improvement or timing closure has been measured for this candidate.

## Completed evidence

- [Full actual RTL proof](https://github.com/Melihakbulut221/nssoc/actions/runs/43613750120): 2x22 and 4x38 byte stores; 1,398 and 3,873 equivalence cells respectively, all proven, none unproven. Actual flattened module and mapped memory, no memory blackboxes. Uses `async2sync` and two-step induction, so it is not analog reset characterization.
- [Proof with physical replay options](https://github.com/Melihakbulut221/nssoc/actions/runs/43614451027): both sizes with `SOC_PCIE_REPLAY_AHEAD`, `SOC_PCIE_REPLAY_INBANK` and `SOC_PCIE_RESET_COPIES` enabled in both reference and candidate.
- [Simulation and factorization](https://github.com/Melihakbulut221/nssoc/actions/runs/43613400964): twelve 300,000-cycle comparisons against the original implementation, zero output differences. The four independent packet/replay scoreboards execute 19 tests, with no failure, error or skip. Six Boolean factorization proofs and six intentional wrong-address counterexamples also passed their expected verdicts.

The first full proof attempt used Ubuntu's older Yosys and failed to parse an existing sized cast. It was not a design counterexample. The successful proofs use the repository's pinned OSS CAD Suite 2026-08-04.

Machine-readable source, archive and log hashes are in [the functional receipt](evidence/replay-write-predecode-functional-20261114.json).

## Additional storage controls passed; physical adoption pending

[Stronger storage and compiled mutation validation](https://github.com/Melihakbulut221/nssoc/actions/runs/43614166666) passed: another twelve 300,000-cycle cases compare every actual byte write strobe and stored byte, including malformed frames. An intentionally wrong low-address select fails with a real strobe mismatch in all six seeds. Reversing only the opt-in edits recovers the original RTL byte-for-byte. All 19 independent packet tests passed again without skips.

The tested source and helpers are now integrated, with the switch **default off**. The experiment workflow is excluded. The full proof helper in the integration branch reproduces the physical replay option configuration; the earlier default-option source is pinned in the receipt.

[Identical-library mapping](https://github.com/Melihakbulut221/nssoc/actions/runs/43615106119) passed for both versions. Isolated replay cell counts are 5,900 baseline versus 5,898 predecode; sequential cells increase from 1,605 to 1,622. This is not a clock-load, area-of-chip or timing verdict. Direct write-control sink counts include mapper-created buffer trees and do not establish end-to-end path delay. The first reporting attempt rejected two zero-port Yosys `$scopeinfo` metadata records; the corrected analyzer explicitly checks that these have no connections, and still rejects every unknown hardware cell type. See [mapping receipt](evidence/replay-write-predecode-mapping-20261114.json).

Next measure the affected and newly exposed paths after physical implementation, then run coherent full-chip routing, extraction, original-clock all-corner timing and physical verification. Earlier routed/LVS passes do not apply to a new netlist. Full serial PHY and manufacturing qualification remain separate open requirements.
