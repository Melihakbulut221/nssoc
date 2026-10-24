# Native sizing and hold repair on the saved routed chip

The authoritative source is routed ODB bde963927da325e3f66c1c62d6f78f5db4c60b1344670ebabd04d3339c1a5850, 151022 instances, and its actual extracted nominal SPEF. Saved-route audit 39382009151 passed topology/fixed-clock conservation; setup and hold did not close. Counts slow/typical/fast are 9660/7027/3151 setup and 3/10/20 hold; two antenna nets remain.

The worst typical/fast setup path runs from PCIe retry replay_read_onehot[12] to pcie_tx_data_o[7]. Measured small buffers and a21oi_1 drive approximately 0.30–0.45 pF. Worst hold is pcie_rx_valid_i to FF1192852. These observations motivate native cell sizing and hold buffering across the actual violating endpoints instead of another fixed list of 32 manually selected cells.

The cloud workflow first restores the hash-bound native ODB, netlist, written SDC, SPEF and exact configuration. Nineteen native library/exclusion files are bound to the original IHP commit and Git blob identities. Native OpenROAD must reproduce all six original worst slacks within 1 ps before any repair. Four rejection controls check that comparison.

The setup search uses the pinned engine's native size-up moves, up to 40 iterations with eight repairs per pass, across 100 percent of failing endpoints. Pin swapping, cloning, buffer removal, down-sizing and last-gasp passes are disabled for this candidate. Hold repair follows with a 0.1 ns margin, at most 200 iterations and no permission to introduce setup violations. These are search bounds, not acceptance changes. Setup and hold checkpoints are preserved separately.

Clock-connected cells and twenty SRAM instances are protected from resizing. Only resized/new cells move during legalization. Independent native geometry checks preserve clock/SRAM placement and masters, clock pin nets, other unchanged-cell placements, PG, port geometry and NDRs. Full native Liberty equations, retained states, opaque macro interfaces and output equations are then compared, including an actual buffer-inversion negative control. The original fixed-clock geometry is independently checked.

A successful job only produces a candidate. Its optimizer parasitics after mutation are not signoff evidence. Fresh routing, DRC/antenna/connectivity, RC and all-corner setup/hold measurements remain mandatory; no full PHY, LVS or production claim is made. All computation and artifacts remain in GitHub Actions/releases, with the local workspace empty.

Primary implementation references: [pinned OpenROAD resizer Tcl](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/Resizer.tcl), [pinned native setup repair](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/RepairSetup.cc), and [LibreLane 3.0.5 timing repair](https://github.com/librelane/librelane/blob/3.0.5/librelane/scripts/openroad/rsz_timing_postgrt.tcl).

## First native execution and direct-object fix

Run 39385758586 reproduced all six source worst slacks with maximum difference 0.000000122 ns, then stopped before native optimization: a Yosys cell name containing backslashes did not map through STA's name-pattern lookup. The failure is preserved in evidence/onehot-native-resizer-name-rejection-20261020.json.

The corrected Tcl protects the actual ODB instance using setDoNotTouch, the same underlying flag used by the pinned Resizer::setDontTouch implementation. Original flags are recorded and restored. Clock nets remain protected through both repairs. Instance flags are restored before hold buffering so that clock-connected state elements' data inputs can receive a positive delay buffer. Geometry and clock-net checks remain independent; no timing limit is changed.


## Native routing callback crash and initialization correction

Run 39386565913 again reproduced the original routed baseline, then the pinned engine crashed at the first SizeUpMove. The stack is GlobalRouter::addDirtyNet -> GRouteDbCbk::inDbInstSwapMasterAfter -> dbInst::swapMaster. No candidate checkpoint was produced. The exact rejection remains in evidence/onehot-native-resizer-router-crash-20261020.json.

Inspection of the exact OpenROAD revision shows that IncrementalGRoute installs a callback without populating db_net_map_; addDirtyNet dereferences that map entry. The repair flow now writes and reloads the existing source guides, sets the original signal/clock layer ranges and 0.2 capacity adjustment, and performs an empty start/end incremental session to initialize native grid/net tables before optimization. It does not substitute placement RC or run a new global route over the whole chip.

Before editing any cell, the workflow compares full physical DEF before/after initialization (excluding only GCell grid bookkeeping), and requires literal identity of all six per-corner max/min worst-path reports. A changed-DEF negative control is retained. Native resizer callbacks own subsequent dirty-net updates; final route/RC/STA is still required. All added positive hold buffers must have VPWR/VGND connected to the actual existing supply nets; the independent geometry checker verifies those connections.

Primary evidence: [exact GlobalRouter implementation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/grt/src/GlobalRouter.cpp) and [exact incremental parasitic update implementation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/est/src/EstimateParasitics.cpp).


## 2026-10-20 native optimizer reached; explicit positive delay-cell allowlist
Run 39388037634 passed the exact physical DEF and six-report router initialization
identity gates. Native setup repair resized 214 cells; native hold repair retained
four buffers. It stopped at the added-master gate before legalization/proof.
The rejected run did not print the offending master, so its exact identity is
not claimed. Its summary asset 658641687 SHA256
bf646e76cc871e9f7f83fc9484e1fc30383327e2e42009d9fb2dce0de951e92d
and full archive 658641863 SHA256
16d6e6982a69e7b337eea7093978365e69c0e76addc12f1fdf058f5736997462
remain immutable cloud evidence.

The pinned typ Liberty SHA256
968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4
defines sg13g2_dlygate4sd1_1, sg13g2_dlygate4sd2_1 and
sg13g2_dlygate4sd3_1 as X=A, as it does the five ordinary buffer sizes.
The added-cell gates now explicitly accept only these eight positive cells.
Enabled/tri-state cells and arbitrary new logic remain rejected. Actual candidate
Boolean proof and inversion negative control remain mandatory. An unchecked
hold ODB/netlist is saved before acceptance gates and the error prints the exact
instance/master if a different cell is seen. Power, geometry and fixed-clock
checks remain mandatory.

The optimizer's estimated WNS changed from -15.804 to -9.457 ns for setup;
hold remained -0.513 ns. These are incremental estimates, not freshly routed
all-corner signoff. No timing closure, route acceptance, LVS or PHY acceptance
is claimed. All computations and durable results remain on GitHub.


## Standard-cell supply pins corrected from the pinned physical library
Run 39389233033 passed the added positive-cell gate, then stopped with
"Missing new buffer supply". The pinned SG13G2 LEF defines VDD/VSS pins on
the ordinary buffers and all three delay cells. The unchanged routed source
configuration defines SCL_POWER_PINS=[VDD], SCL_GROUND_PINS=[VSS], while
the actual chip nets are VPWR/VGND. New-instance hookup and independent geometry
inspection now require VDD -> VPWR and VSS -> VGND. Existing source geometry
and power routes remain protected. The unchecked hold checkpoint is retained.
This addresses an integration-script error, not remaining setup/hold violations.
