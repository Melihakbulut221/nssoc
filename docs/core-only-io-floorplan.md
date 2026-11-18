# Core-only native pad-ring placement trial

This trial consumes the authenticated original mapped core port contract, generates its76signal and4supply pads, and uses unchanged pinned IHP IO LEF/GDS to place the ring. Native corners/fillers and a provisional4.0x3.2mm die are inherited from the existing placement method. Footprint checks, adjacent abstract power-rail abutment, negative missing-cell/wrong-rotation controls, and streamed GDS instance readback are retained.

This does not place the core or serial mailbox, route signals, or prove transistor LVS/DRC/ESD, power integrity, package suitability or timing. It is a current-release physical pad placement artifact for later whole-chip integration. The76signal pads include dedicated status/test access. No removed PCIe/Ethernet pads are reintroduced. All results must remain separate from the running core detailed-route trial.

Verified result: run44262963332/source3e3ee37fb0c610ccd3e24ee9be8885c465d63c46 completed successfully. All9 archived output hashes and protected tracked sources were independently checked. 296 native instances, 1184 abstract rail contacts, missing-cell/wrong-rotation negative controls and producer GDS readback passed within this narrow scope. Evidence: docs/evidence/core-only-io-floorplan-20261118.json. The produced GDS contains the I/O ring only, not an integrated routed chip.
