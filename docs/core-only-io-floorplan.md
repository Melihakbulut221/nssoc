# Core-only native pad-ring placement trial

This trial consumes the authenticated original mapped core port contract, generates its76signal and4supply pads, and uses unchanged pinned IHP IO LEF/GDS to place the ring. Native corners/fillers and a provisional4.0x3.2mm die are inherited from the existing placement method. Footprint checks, adjacent abstract power-rail abutment, negative missing-cell/wrong-rotation controls, and streamed GDS instance readback are retained.

This does not place the core or serial mailbox, route signals, or prove transistor LVS/DRC/ESD, power integrity, package suitability or timing. It is a current-release physical pad placement artifact for later whole-chip integration. The76signal pads include dedicated status/test access. No removed PCIe/Ethernet pads are reintroduced. All results must remain separate from the running core detailed-route trial.
