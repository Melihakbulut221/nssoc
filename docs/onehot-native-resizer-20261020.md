# Native sizing and hold repair on the saved routed chip

The authoritative source is routed ODB bde963927da325e3f66c1c62d6f78f5db4c60b1344670ebabd04d3339c1a5850, 151022 instances, and its actual extracted nominal SPEF. Saved-route audit 39382009151 passed topology/fixed-clock conservation; setup and hold did not close. Counts slow/typical/fast are 9660/7027/3151 setup and 3/10/20 hold; two antenna nets remain.

The worst typical/fast setup path runs from PCIe retry replay_read_onehot[12] to pcie_tx_data_o[7]. Measured small buffers and a21oi_1 drive approximately 0.30–0.45 pF. Worst hold is pcie_rx_valid_i to FF1192852. These observations motivate native cell sizing and hold buffering across the actual violating endpoints instead of another fixed list of 32 manually selected cells.

The cloud workflow first restores the hash-bound native ODB, netlist, written SDC, SPEF and exact configuration. Nineteen native library/exclusion files are bound to the original IHP commit and Git blob identities. Native OpenROAD must reproduce all six original worst slacks within 1 ps before any repair. Four rejection controls check that comparison.

The setup search uses the pinned engine's native size-up moves, up to 40 iterations with eight repairs per pass, across 100 percent of failing endpoints. Pin swapping, cloning, buffer removal, down-sizing and last-gasp passes are disabled for this candidate. Hold repair follows with a 0.1 ns margin, at most 200 iterations and no permission to introduce setup violations. These are search bounds, not acceptance changes. Setup and hold checkpoints are preserved separately.

Clock-connected cells and twenty SRAM instances are protected from resizing. Only resized/new cells move during legalization. Independent native geometry checks preserve clock/SRAM placement and masters, clock pin nets, other unchanged-cell placements, PG, port geometry and NDRs. Full native Liberty equations, retained states, opaque macro interfaces and output equations are then compared, including an actual buffer-inversion negative control. The original fixed-clock geometry is independently checked.

A successful job only produces a candidate. Its optimizer parasitics after mutation are not signoff evidence. Fresh routing, DRC/antenna/connectivity, RC and all-corner setup/hold measurements remain mandatory; no full PHY, LVS or production claim is made. All computation and artifacts remain in GitHub Actions/releases, with the local workspace empty.

Primary implementation references: [pinned OpenROAD resizer Tcl](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/Resizer.tcl), [pinned native setup repair](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/RepairSetup.cc), and [LibreLane 3.0.5 timing repair](https://github.com/librelane/librelane/blob/3.0.5/librelane/scripts/openroad/rsz_timing_postgrt.tcl).
